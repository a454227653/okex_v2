import asyncio

from core.config.base_config import BaseConfig, json_config
from core.rpc.constant import *
from core.rpc.rabbit_mq import RabbitMq
from core.rpc.rpc_class import *
from core.task import *
from core.utils import logger, tools
import traceback, inspect


class RpcServer(RabbitMq):

	def __init__(self, rpc: Rpc, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
		self._rpc = rpc
		self._rpc_methods = rpc.get_rpc_method()
		self._queue_durable = config.get('rpc.server.queue_durable', True)
		self._msg_presistent = config.get('rpc.server.msg_presistent', True)
		self._max_retry = config.get('rpc.server.max_retry', 10)
		self._prefetch_count = config.get('rpc.server.prefetch_count', 10)
		self._server_name = rpc.server_name if rpc.server_name is not None else self._rpc.__class__.__name__
		self._server_channels = rpc.server_channels
		self._server_id = rpc.server_id or tools.get_uuid4()
		self._queue = '{s}_server:{id}'.format(s=self._server_name, id=self._server_id if rpc.mode == 'broadcast' else 0)
		self._exchange_pub = 'rpc_client'
		self._exchange_sub = 'rpc_server'
		super(RpcServer, self).__init__(config, task_center)
		self._cnt = 0
		logger.info(SERVER_STARTED_INFP.format(s=self._server_name, m=[m for m in self._rpc_methods.keys()]), caller=self)

	async def _bind(self, reconnect=False):
		if not reconnect:
			await self._channel.exchange_declare(exchange_name=self._exchange_sub, type_name="topic")
			await self._channel.exchange_declare(exchange_name=self._exchange_pub, type_name="topic")
		# exclusive=false 时允许多个服务端绑定同一队列, 均摊负载, exclusive=true 时服务器为广播模式, 一个请求会触发所有服务器响应
		await self._channel.queue_declare(queue_name=self._queue, auto_delete=True, durable=self._queue_durable, exclusive=self._rpc.mode=='broadcast')
		for server_channnel in self._server_channels:
			routing_key_sub = '{s}.{c}'.format(s=self._server_name, c=server_channnel)
			await self._channel.queue_bind(queue_name=self._queue, exchange_name=self._exchange_sub, routing_key=routing_key_sub)
		# 异步最大并发数, 有 n 个未确认的 callback 在异步运行时, 队列不会再向 consumer 投递消息
		await self._channel.basic_qos(prefetch_count=self._prefetch_count)
		await self._channel.basic_consume(callback=self._on_request, queue_name=self._queue, no_ack=False)

	async def _on_request(self, channel, body, envelope, properties):
		BaseTask(self._call_back, channel, body, envelope, properties).attach2loop()

	async def _call_back(self, channel, body, envelope, properties):
		try:
			self._cnt += 1
			request = self.uzip(body)
			method = request.get('m', envelope.routing_key.split('.')[1])
			correlation_id, rounting_key_reply = properties.correlation_id, properties.reply_to
			if method not in self._rpc_methods:
				raise Exception('Rpc server recieve request on invalid method: {m}'.format(m=[method]), request)
			pro = {
				'correlation_id' : correlation_id
				, 'delivery_mode': 2 if self._msg_presistent else 1		#消息持久化
			}
			args, kwargs = request.get('args', []), request.get('kwargs', {})
			func = self._rpc_methods[method]
			if inspect.iscoroutinefunction(func):
				res = await func(*args, **kwargs)
			else:
				res = func(*args, **kwargs)
			if rounting_key_reply is not None:
				await channel.basic_publish(payload=self.zip(res), exchange_name=self._exchange_pub, routing_key=rounting_key_reply, properties=pro)
			logger.debug("Rpc server receive request: {d}, cnt = {c}, aply method = {m}, reply res = {r}:".format(d=request, c=[str(self._cnt)], m=[method], r=['no_reply' if rounting_key_reply is None else res]), caller=self)
			await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)
		except Exception as e:
			e.trace = "\n"+"".join(traceback.format_tb(e.__traceback__))
			msg = "Rpc server callback error, correlation_id = {c}:{t}{e}".format(c=[correlation_id], t=e.trace, e=e)
			logger.error(msg, caller=self)
			await self._log_error(msg)
			await channel.basic_publish(payload=self.zip(e), exchange_name=self._exchange_pub, routing_key=rounting_key_reply, properties=pro)
			await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)


class RpcClient(RabbitMq):
	def __init__(self, rpc, client_id = None, hello_server = True, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
		self._queue_durable = config.get('rpc.client.queue_durable', False)
		self._msg_presistent = config.get('rpc.client.msg_presistent', False)
		self._time_out = config.get('rpc.client.time_out', 1000)  # ms
		self._prefetch_count = config.get('rpc.client.prefetch_count', 10)
		if isinstance(rpc, Rpc):
			self._server_name = rpc.server_name or rpc.__class__.__name__
			self._client_id = rpc.server_id
		elif isinstance(rpc, str):
			self._server_name = rpc
			self._client_id = client_id or tools.get_uuid4()
		else:
			raise IOError('rpc type invalid: ', rpc)
		self._rpc_methods = []
		self._queue = "{s}_client:{u}".format(s=self._server_name, u=self._client_id)
		self._exchange_pub = 'rpc_server'
		self._exchange_sub = 'rpc_client'
		self._routing_key_sub = '{s}.{id}'.format(s=self._server_name, id=self._client_id)
		self._reply_tmp = {}  # 请求结果缓存 eg. { correlation_id: response}
		self._request_tmp = set()  # 请求id缓存
		self.rt = 0
		super(RpcClient, self).__init__(config, task_center)
		if hello_server:
			self.hello_server()

	def hello_server(self):
		try:
			self._rpc_methods = [m for m in self.request({})]
			logger.info(SERVER_CONNECTED_INFP.format(s=self._server_name, m=[m for m in self._rpc_methods]), caller=self)
		except Exception as e:
			raise IOError('Rpc server {s} not found'.format(s=[self._server_name]))

	async def _bind(self, reconnect=False):
		# 每个客户端维持一条 exclusive 的队列用于订阅服务端发布的回复, 队列名为 {服务类名:uuuid},
		# 默认关闭持久化, 消息丢失客户端自己重新请求
		# 订阅 routing_key 为 {类名.uuuid}
		await self._channel.queue_declare(queue_name=self._queue, auto_delete=True, exclusive=True, durable=self._queue_durable)
		await self._channel.queue_bind(queue_name=self._queue, exchange_name=self._exchange_sub, routing_key=self._routing_key_sub)
		await self._channel.basic_qos(prefetch_count=self._prefetch_count)
		await self._channel.basic_consume(callback=self._on_reply, queue_name=self._queue, no_ack=True)

	async def request_async(self, request, server_name=None, server_channel='default', method='get_rpc', no_reply = False):
		start_time = tools.get_now_ts13()
		if 'm' not in request:
			request['m'] = method
		await self._check_connection()
		correlation_id = tools.get_uuid4()
		self._request_tmp.add(correlation_id)
		pro = {}
		pro['correlation_id'] = correlation_id
		pro['delivery_mode'] = 2 if self._msg_presistent else 1
		pro['reply_to'] = None if no_reply else self._routing_key_sub
		body = self.zip(request)
		server_name = server_name if server_name else self._server_name
		routing_key = '{s}.{c}'.format(s=server_name, c=server_channel)
		await self._channel.basic_publish(payload=body, exchange_name=self._exchange_pub, routing_key=routing_key, properties=pro)
		logger.debug('Rpc client send a request: {r}, correlation_id = {c}'.format(c=[correlation_id] , r=request), caller=self)
		if no_reply:
			return
		# 等待服务端回复
		await self.block(correlation_id, start_time)
		reply = self._reply_tmp.pop(correlation_id)
		rt = tools.get_now_ts13() - start_time
		self.rt = self.rt*0.9 + rt*0.1
		if isinstance(reply, BaseException):
			msg = "Rpc client request error, correlation_id = {c}, rt = {t}ms: {b}{e}".format(t=rt, c=[correlation_id], b=reply.trace, e=reply)
			logger.error(msg, caller=self)
			await self._log_error(msg)
		else:
			logger.debug("Rpc client request reply: {r}, correlation_id = {c}, rt = {t}ms, correlation_id tmp size = {s}".format(r=reply, t=rt, c=[correlation_id], s=[len(self._reply_tmp)]), caller=self)
		return reply

	def request(self, request, server_name=None, server_channel='default', method='get_rpc', no_reply=False):
		return BaseTask(self.request_async, request, server_name, server_channel, method, no_reply).run_once()

	async def _on_reply(self, channel, body, envelope, properties):
		BaseTask(self._call_back, channel, body, envelope, properties).attach2loop()

	async def _call_back(self, channel, body, envelope, properties):
		correlation_id = properties.correlation_id
		if correlation_id not in self._request_tmp:
			return
		reply = self.uzip(body)
		self._reply_tmp[correlation_id] = reply

	async def block(self, correlation_id, start_time):
		# await asyncio.sleep(100)
		while correlation_id not in self._reply_tmp:
			await asyncio.sleep(0.0001)
			if (tools.get_now_ts13() - start_time) > self._time_out:
				self._request_tmp.remove(correlation_id)
				msg = "Rpc client request time out! correlation_id={c}".format(c=[correlation_id])
				await self._log_error(msg)
				raise TimeoutError(msg)
		self._request_tmp.remove(correlation_id)
		# logger.debug("block run {i} times".format(i=str(i)), caller=self)