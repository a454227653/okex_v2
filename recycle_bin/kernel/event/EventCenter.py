"""
event.py
created by Yan on 2023/4/18 20:02;
"""

from core.utils.tools import async_method_locker
from core.utils import logger
from core.task import *
from core.config import *
import aioamqp, asyncio

class EventCenter:
    """event center.
    """

    def __init__(self, config : MainConfig = config, task_center : TaskCenter = task_center):
        self._host = config.EventCenter.host
        self._port = config.EventCenter.port
        self._username = config.EventCenter.username
        self._password = config.EventCenter.password
        self._check_connection_interval = config.EventCenter.check_connection_interval
        self._exchanges = config.EventCenter.exchanges
        self._channel_ack = config.EventCenter.channel_ack
        self._task_center = task_center
        self._protocol = None
        self._channel = None  # Connection channel.
        self._connected = False  # If connect success.
        self._subscribers = []  # e.g. `[event1, event2, ....]`
        self._event_handler = {}  # e.g. `{"exchange:routing_key": [callback_function, ...]}`

        # 任务中心提交 mq 链接维持任务
        LoopTask(self._check_connection, loop_interval=self._check_connection_interval).register(self._task_center)

        # Create MQ connection.
        asyncio.get_event_loop().run_until_complete(self.connect())

    @async_method_locker("event.subscribe")
    async def subscribe(self, event):
        """
        event : BaseEvent
        """
        logger.info("NAME:", event.name(), "EXCHANGE:", event.exchange(), "QUEUE:", event.queue(), "ROUTING_KEY:",
                    event.routing_key(), caller=self)
        self._subscribers.append(event)

    async def publish(self, event, exchange, routing_key, data):
        """Publish a event.

        Args:
            event: A event to publish.
        """
        if not self._connected:
            logger.warn("RabbitMQ not ready right now!", caller=self)
            return
        data = event.dumps(data)
        await self._channel.basic_publish(payload=data, exchange_name=exchange, routing_key=routing_key)

    async def connect(self, reconnect=False):
        """Connect to RabbitMQ server and create default exchange.

        Args:
            reconnect: If this invoke is a re-connection ?
        """
        logger.debug("host:", self._host, "port:", self._port, caller=self)
        if self._connected:
            return

        # Create a connection.
        try:
            transport, protocol = await aioamqp.connect(host=self._host, port=self._port, login=self._username,
                                                        password=self._password, login_method="PLAIN")
        except Exception as e:
            logger.error("connection error:", e, caller=self)
            return
        finally:
            if self._connected:
                return
        channel = await protocol.channel()
        if self._channel_ack and not channel.publisher_confirms:
            channel.confirm_select()
        self._protocol = protocol
        self._channel = channel
        self._connected = True
        logger.debug("Rabbitmq initialize success!", caller=self)

        # Create exchanges.
        for name in self._exchanges:
            await self._channel.exchange_declare(exchange_name=name, type_name="topic")
        logger.debug("create default exchanges success!", caller=self)

        if reconnect:
            self._bind_and_consume()
        else:
            # Maybe we should waiting for all modules to be initialized successfully.
            asyncio.get_event_loop().call_later(5, self._bind_and_consume)

    def _bind_and_consume(self):
        async def do_them():
            for event in self._subscribers:
                await self._initialize(event)
        BaseTask(do_them).attach2loop()

    async def _initialize(self, event):
        if event.queue():
            await self._channel.queue_declare(queue_name=event.queue(), auto_delete=True)
            queue_name = event.queue()
        else:
            result = await self._channel.queue_declare(exclusive=True)
            queue_name = result["queue"]
        await self._channel.queue_bind(queue_name=queue_name, exchange_name=event.exchange(), routing_key=event.routing_key())
        await self._channel.basic_qos(prefetch_count=event.pre_fetch_count())
        if event.callback:
            # 回调是绑定队列的, channel+routing_key 决定路由到哪个队列, 进而调用某个回调
            if not event.multi():
                # queue 绑定单个回调, 只有最先绑定的回调会生效
                await self._channel.basic_consume(callback=event.callback, queue_name=queue_name, no_ack=False)
                logger.debug("queue with single callback:", queue_name, caller=self)
            else:
                # queue 绑定多个回调, exchange+routing_key 下的所有回调会被异步执行
                await self._channel.basic_consume(self._on_consume_event_msg, queue_name=queue_name, no_ack=False)
                logger.debug("queue with multi callback:", queue_name, caller=self)
                self._add_event_handler(event)

    async def _on_consume_event_msg(self, channel, body, envelope, properties):
        try:
            key = "{exchange}:{routing_key}".format(exchange=envelope.exchange_name, routing_key=envelope.routing_key)
            funcs = self._event_handler[key]
            for func in funcs:
                BaseTask(func, channel, body, envelope, properties).attach2loop()
        except:
            logger.error("event handle error! body:", body, caller=self)
            return
        finally:
            await self._channel.basic_client_ack(delivery_tag=envelope.delivery_tag)  # response ack

    def _add_event_handler(self, event):
        key = "{exchange}:{routing_key}".format(exchange=event.exchange(), routing_key=event.routing_key())
        if key in self._event_handler:
            self._event_handler[key].append(event.callback)
        else:
            self._event_handler[key] = [event.callback]
        logger.debug("event handlers:", self._event_handler.keys(), caller=self)

    async def _check_connection(self, *args, **kwargs):
        if self._connected and self._channel and self._channel.is_open:
            return
        logger.error("CONNECTION LOSE! START RECONNECT RIGHT NOW!", caller=self)
        self._connected = False
        self._protocol = None
        self._channel = None
        self._event_handler = {}
        BaseTask(self.connect, reconnect=True).attach2loop()

#default
event_center = EventCenter(config, task_center)