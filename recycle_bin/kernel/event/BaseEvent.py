"""
BaseEvent.py
created by Yan on 2023/4/18 20:02;
"""
import json
import zlib
from core.task import *
from core.utils.tools import *
from recycle_bin.kernel import EventCenter, event_center
from recycle_bin.kernel.data import KLineData
from core.utils import logger


class BaseEvent():
	"""
	一个 BaseEvent 定义了一组消息通信规则, 包括
	_name, 全局唯一事件名, 命名规则: {EVENT类名}.{self._queue}
	_queue, 消息处理队列名, 命名规则: {exchange}.{routing_key}.{_multi=True 时自定义回调名}
	_routing_key, 队列的接收规则, e.g. {platform}.{symbol}.*
	_pre_fetch_count, 队列允许累积未确认消息数
	_multi, False: 队列绑定单个回调; True: 队列绑定回调 list, list 中的所有回调都会被异步执行
	_callback, 回调接口
	_publish_exchange, 获取消息发布 exchange 接口, 默认为 _exchange
	_publish_routing_key, 获取消息发布 routing_key 接口, 默认为 _routing_key
	_no_ack, 消费者无需发送确认信息
	_requeue, _no_ack=False 时, 发送 nack 后消息是否重新进入队列
	消息生产者: 重写 self._publish_exchange, self._publish_routing_key, 一般与发布的消息内容相关
	消息消费者: 重写 self._callback, 设置 _exchange, _routing_key, _queue, _multi
			   若需要队列上绑定多个回调, 设置 _multi = True
	"""

	def __init__(self, name=None, exchange=None, queue=None, routing_key=None, pre_fetch_count=1, multi=False, callback=None, no_ack=None, requeue=None):
		"""
		除了_data _pub_ts字段以外都不允许被更新
		"""
		self._name = name
		self._exchange = exchange
		self._queue = queue
		self._routing_key = routing_key
		self._pre_fetch_count = pre_fetch_count
		self._multi = multi
		self._callback = callback or self._callback
		self._no_ack = no_ack or False
		self._requeue = requeue or False

	def name(self): return self._name

	def multi(self): return self._multi

	def exchange(self): return self._exchange

	def routing_key(self): return self._routing_key

	def queue(self): return self._queue

	def pre_fetch_count(self): return self._pre_fetch_count

	def no_ack(self): return self._no_ack

	def dumps(self, data):
		d = {
			"n": self._name,
			"d": data,
			"t": get_now_ts13()
		}
		s = json.dumps(d)
		b = zlib.compress(s.encode("utf8"))
		return b

	def loads(self, b):
		b = zlib.decompress(b)
		d = json.loads(b.decode("utf8"))
		data = d.get("d")
		pub_ts = d.get("t")
		return data, pub_ts

	def subscribe(self, event_center : EventCenter = event_center):
		BaseTask(event_center.subscribe, self).attach2loop()

	async def publish(self, data, event_center : EventCenter = event_center):
		"""
		data 必须是 json 格式
		"""
		BaseTask(event_center.publish, self, self._publish_exchange(data), self._publish_routing_key(data), data).attach2loop()

	def __str__(self):
		info = "EVENT: name={n}, exchange={e}, queue={q}, routing_key={r}".format(
			e=self._exchange, q=self._queue, r=self._routing_key, n=self._name)
		return info

	def __repr__(self):
		return str(self)

	async def callback(self, channel, body, envelope, properties):
		data, pub_ts = self.loads(body)
		try:
			await self._callback(data)
			if not self._no_ack:
				await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)
		except:
			logger.error("event callback error! body:", data, caller=self)
			if not self._no_ack:
				await channel.basic_client_nack(delivery_tag=envelope.delivery_tag, multiple=False, requeue=self._requeue)
			return


	async def _callback(self, data):
		"""
		主要回调接口, data 是原始数据, e.g. KLineData
		"""
		pass

	def _publish_exchange(self, data):
		return self._exchange

	def _publish_routing_key(self, data):
		return self._routing_key


class EventMsg(BaseEvent):
	def __init__(self, queue, routing_key):
		exchange = "msg"
		routing_key = routing_key
		queue = queue
		name = "EVENT_MSG.{q}".format(q=queue)
		super(EventMsg, self).__init__(name, exchange, queue, routing_key, multi=False, no_ack=True)

	async def _callback(self, data):
		print("EventMsg callback:", data)


class EventKlineUpdate(BaseEvent):
	def __init__(self):
		exchange = "kline"
		routing_key = "*.*" # platform.symbol
		queue = "{ex}.update".format(ex=exchange)
		name = "EVENT_KLINE.{q}".format(q=queue)
		super(EventKlineUpdate, self).__init__(name, exchange, queue, routing_key, multi=False, no_ack=False, requeue=True)

	async def _callback(self, data):
		logger.debug("EventKlineUpdate:", data, caller=self)
		kline = KLineData(data)
		kline.dump()

	def _publish_routing_key(self, data):
		return "{p}.{s}".format(p=data.get('platform'), s=data.get('symbol'))

	async def publish(self, data: KLineData, event_center : EventCenter = event_center):
		data = data.to_json()
		BaseTask(event_center.publish, self, self._publish_exchange(data), self._publish_routing_key(data), data).attach2loop()
