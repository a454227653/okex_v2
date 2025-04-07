"""
rabbit.py
created by Yan on 2023/5/14 21:05;
"""
from core.task import *
from core.utils import logger, tools
import aioamqp, asyncio, zlib
from core.config.base_config import json_config, BaseConfig
import pickle, os
from core.data.data_base import MongoDBLocal
class RabbitMq():
	def __init__(self, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
		self._host = config.get('rpc.rabbit_mq.host')
		self._port = config.get('rpc.rabbit_mq.port')
		self._username = config.get('rpc.rabbit_mq.username')
		self._password = config.get('rpc.rabbit_mq.password')
		self._check_connection_interval = config.get('rpc.rabbit_mq.check_connection_interval')
		self._channel_ack = config.get('rpc.rabbit_mq.publish_ack')
		self._task_center = task_center
		self._connected = False
		self._protocol = None
		self._channel = None
		self._log_file = os.path.dirname(os.path.abspath(__file__)) + '/log/{d}.log'.format(d=tools.get_now_date().split(' ')[0])

		# Create MQ connection.
		asyncio.get_event_loop().run_until_complete(self.connect())
		# 任务中心提交 mq 链接维持任务
		self._check_task = LoopTask(self._check_connection, loop_interval=self._check_connection_interval).register(self._task_center)

	async def connect(self, reconnect=False):
		logger.debug("host: {h}, port: {p}".format(h=self._host, p=self._port), caller=self)
		if self._connected:
			return

		try:
			transport, protocol = await aioamqp.connect(host=self._host, port=self._port, login=self._username,
														password=self._password, login_method="PLAIN")
		except Exception as e:
			e = "connection error: {e}".format(e=e)
			logger.error(e, caller=self)
			await self._log_error(e)
			return
		finally:
			if self._connected:
				return
		channel = await protocol.channel()
		if self._channel_ack and not channel.publisher_confirms:
			await channel.confirm_select()
		self._protocol = protocol
		self._channel = channel
		self._connected = True
		logger.debug("RabbitMq connected!", caller=self)

		await self._bind(reconnect)


	async def _bind(self, reconnect=False):
		pass

	async def _check_connection(self, *args, **kwargs):
		if self._connected and self._channel and self._channel.is_open:
			return
		msg = "CONNECTION LOSE! START RECONNECT RIGHT NOW!"
		logger.error(msg, caller=self)
		await self._log_error(msg)
		self._connected = False
		self._protocol = None
		self._channel = None
		BaseTask(self.connect, reconnect=True).attach2loop()

	def zip(self, request):
		data = pickle.dumps(request)
		b = zlib.compress(data)
		return b

	def uzip(self, b):
		data = zlib.decompress(b)
		request = pickle.loads(data)
		return request

	def stop(self):
		self._task_center.unregister(self._check_task)
		BaseTask(self._protocol.close).run_once()
		logger.debug("RabbitMq disconnected!", caller=self)

	def start(self):
		self._task_center.start()

	async def _log_error(self, msg):
		if not isinstance(msg,Exception):
			msg = Exception(msg)
		await MongoDBLocal.error.async_dump(msg,self)
		# with open(self._log_file, 'a') as file:
		# 	file.write('\n{t} {m}'.format(t=[tools.get_now_date()], m=msg))

