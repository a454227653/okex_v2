"""
BaseWebSocket.py
created by Yan on 2023/5/4 21:21;
"""

import json
import aiohttp
import hmac
import base64

from core.config import *
from core.task import *
from core.utils import logger
from core.utils.tools import *

class Websocket:
    """Websocket connection.
    """

    def __init__(self, config : MainConfig = config, task_center : TaskCenter = task_center):
        """Initialize."""
        self._proxy = config.MarketServer.WebSockets.proxy
        self._check_conn_interval = config.MarketServer.WebSockets.check_conn_interval
        # self._connected_callback = connected_callback or self._default_connected_callback
        # self._process_callback = process_callback or self._default_process_callback
        # self._process_binary_callback = process_binary_callback or self._default_process_binary_callback
        self._ws = None  # Websocket connection object.
        self._task_center = task_center

        LoopTask(self._check_connection, loop_interval=self._check_conn_interval).register(self._task_center)
        BaseTask(self._connect).attach2loop()

    async def _connected_callback(self):
        logger.info('websockets connected', self._url , caller = self)
        pass

    async def _process_callback(self, data):
        logger.info('websockets received msg:', data, caller=self)
        pass

    async def _process_binary_callback(self, data):
        logger.info('websockets received msg:', data, caller=self)
        pass

    @property
    def ws(self):
        return self._ws

    async def close(self):
        await self._ws.close()

    async def ping(self, message: bytes = b"") -> None:
        await self._ws.ping(message)

    async def pong(self, message: bytes = b"") -> None:
        await self._ws.pong(message)

    async def _connect(self) -> None:
        logger.debug("url:", self._url, caller=self)
        proxy = config.proxy
        session = aiohttp.ClientSession()
        try:
            self._ws = await session.ws_connect(self._url, proxy=proxy)
        except aiohttp.ClientConnectorError:
            logger.error("connect to Websocket server error! url:", self._url, caller=self)
            return
        if self._connected_callback:
            BaseTask(self._connected_callback).attach2loop()
        BaseTask(self._receive).attach2loop()

    @async_method_locker("Websocket.reconnect.locker", False, 30)
    async def reconnect(self) -> None:
        """Re-connect to Websocket server."""
        logger.warn("reconnecting to Websocket server right now!", caller=self)
        await self.close()
        await self._connect()

    async def _receive(self):
        """Receive stream message from Websocket connection."""
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if self._process_callback:
                    try:
                        data = json.loads(msg.data)
                    except:
                        data = msg.data
                    BaseTask(self._process_callback, data).attach2loop()
            elif msg.type == aiohttp.WSMsgType.BINARY:
                if self._process_binary_callback:
                    BaseTask(self._process_binary_callback, msg.data).attach2loop()
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.warn("receive event CLOSED:", msg, caller=self)
                BaseTask(self.reconnect).attach2loop()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("receive event ERROR:", msg, caller=self)
            else:
                logger.warn("unhandled msg:", msg, caller=self)

    async def _check_connection(self, *args, **kwargs) -> None:
        """Check Websocket connection, if connection closed, re-connect immediately."""
        if not self.ws:
            logger.warn("Websocket connection not connected yet!", caller=self)
            return
        if self.ws.closed:
            BaseTask(self.reconnect).attach2loop()

    async def send(self, data) -> bool:
        """ Send message to Websocket server.

        Args:
            data: Message content, must be dict or string.

        Returns:
            If send successfully, return True, otherwise return False.
        """
        if not self.ws:
            logger.warn("Websocket connection not connected yet!", caller=self)
            return False
        if isinstance(data, dict):
            await self.ws.send_json(data)
        elif isinstance(data, str):
            await self.ws.send_str(data)
        else:
            logger.error("send message failed:", data, caller=self)
            return False
        logger.debug("send message:", data, caller=self)
        return True

class OKEX_Websocket(Websocket):
    def __init__(self, config : MainConfig = config, task_center : TaskCenter = task_center):
        self._platform_config = config.MarketServer.Platforms.OKEX_MARKET_WEBSOCKETS
        self._config = config
        self._access_key = self._platform_config.access_key
        self._secret_key = self._platform_config.secret_key
        self._pass_word = self._platform_config.pass_word
        super().__init__(config, task_center)

    async def _connected_callback(self):
        timestamp = get_now_ts13()/1000
        message = str(timestamp) + "GET" + "/users/self/verify"
        mac = hmac.new(bytes(self._secret_key, encoding="utf8"), bytes(message, encoding="utf8"), digestmod="sha256")
        d = mac.digest()
        signature = base64.b64encode(d).decode()
        data = {
            "op": "login",
            "args": [{"apiKey":self._access_key, "passphrase":self._pass_word, "timestamp":timestamp, "sign":signature}]
        }
        await self._ws.send(data)

    async def _process_callback(self, msg):
        """Process binary message that received from websocket.

        Args:
            raw: Binary message received from websocket.
        """
        # print(msg)
        if msg == "pong":
            return
        logger.debug("msg:", msg, caller=self)
        # Authorization message received.
        if msg.get("event"):
            if msg.get("event") == "error":
                e = logger.Error("Websocket connection authorized failed: {}".format(msg))
                logger.error(e, caller=self)
                BaseTask(self._error_callback, {"ws error": e}).attach2loop()
                BaseTask(self._init_callback, False).attach2loop()
                return

            if msg.get("event") == "login":
                logger.debug("Websocket connection authorized successfully.", caller=self)

                """
                # Fetch orders from server. (open + partially filled)
                order_infos, error = await self._rest_api.get_open_orders(self._symbol)
                if error:
                    e = Error("get open orders error: {}".format(error))
                    SingleTask.run(self._error_callback, e)
                    SingleTask.run(self._init_callback, False)
                    return
                if len(order_infos["data"]) > 100:
                    logger.warn("order length too long! (more than 100)", caller=self)

                for info in order_infos["data"]:
                    self._update_order(info)
                """

                # Subscribe order channel.
                data = {
                    "op": "subscribe",
                    "args": self._subscribe_channel
                }
                await self._ws.send(data)
                return

            # Subscribe response message received.
            if msg.get("event") == "subscribe":
                logger.info("subscribe :", msg, caller=self)
                if self.hold:
                    # 订阅多个频道成功 只运行一次
                    self.hold = False
                    BaseTask(self._init_callback, True).attach2loop()
            else:
                e = logger.Error("subscribe event error: {}".format(msg))
                BaseTask(self._error_callback, {"subscribe error": e}).attach2loop()
                BaseTask(self._init_callback, False).attach2loop()
                return
        # Order update message received.
        elif msg.get("arg"):
            if msg["arg"]["channel"] == "orders":
                self._update_order(msg["data"][0])
            if msg["arg"]["channel"] == "balance_and_position":
                self._update_account(msg["data"][0]["balData"])
                self._update_positions(msg["data"][0]["posData"])


