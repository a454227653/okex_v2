import aiohttp
import json

from core.config.base_config import BaseConfig, json_config
from core.rpc.rpc_server import Rpc, rpc
from core.task import task_center, TaskCenter, BaseTask, LoopTask
from core.utils import logger
from core.utils.tools import async_method_locker


class WebSocket(Rpc):
    def __init__(self, host, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
        """Initialize."""
        self._host = host
        self._check_conn_interval = config.get('MarketServer.WebSockets.check_conn_interval')
        self._proxy = config.get('MarketServer.WebSockets.proxy')
        self._task_center = task_center
        self.ws = None  # Websocket connection object.
        super(WebSocket, self).__init__()
        BaseTask(self._connect).attach2loop()
        LoopTask(self._check_connection, loop_interval=self._check_conn_interval).register(self._task_center)

    async def close(self):
        await self.ws.close()

    async def ping(self, message: bytes = b"") -> None:
        if isinstance(message, str):
            message = message.encode('utf-8')
        await self.ws.ping(message)

    async def pong(self, message: bytes = b"") -> None:
        if isinstance(message, str):
            message = message.encode('utf-8')
        await self.ws.pong(message)

    async def _connect(self) -> None:
        self.ws = 'trying'
        logger.debug("url:", self._host, caller=self)
        session = aiohttp.ClientSession()
        try:
            self.ws = await session.ws_connect(self._host,proxy=self._proxy)
        except Exception as e:
            self.ws = None
            logger.error("connect to Websocket server error: ", e, caller=self)
            return
        BaseTask(self._on_connected_callback).attach2loop()
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
                try:
                    data = json.loads(msg.data)
                except:
                    data = msg.data
                BaseTask(self._on_receive_data_callback, data).attach2loop()
            elif msg.type == aiohttp.WSMsgType.BINARY:
                BaseTask(self._on_receive_binary_callback, msg.data).attach2loop()
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.warn("receive event CLOSED:", msg, caller=self)
                BaseTask(self.reconnect).attach2loop()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error("receive event ERROR:", msg, caller=self)
            else:
                logger.warn("unhandled msg:", msg, caller=self)

    async def _check_connection(self):
        if self.ws == 'trying':
            return
        if not self.ws:
            logger.info("Websocket try connecting!", caller=self)
            BaseTask(self._connect).attach2loop()
            return
        if self.ws.closed:
            BaseTask(self.reconnect).attach2loop()
            return
        BaseTask(self.ping, 'ping').attach2loop()

    @rpc
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

    def start(self):
        self._task_center.start()

    def _on_connected_callback(self):
        pass

    def _on_receive_data_callback(self):
        pass

    def _on_receive_binary_callback(self):
        pass
