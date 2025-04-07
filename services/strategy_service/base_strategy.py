"""
base_strategy.py
created by Yan on 2023/5/22 15:10;
"""
from core.rpc.rpc_server import Rpc, rpc, RpcServer
from core.config.base_config import BaseConfig, json_config
from core.utils import logger, tools
from services.constant import *
from core.task.TaskCenter import TaskCenter, task_center, BaseTask
from services.data_service.data_service import BaseData

class BaseStrategy(Rpc):
	mode = BROADCAST
	server_name = STRATEGY
	server_channels = ['default', '*.*.order.#', '*.*.kline.#', '*.*.trade.#', '*.*.orderbook.#']
	platform_server = 'OKEX_FAKE_PRIVATE'
	symbol = BTC_USDT
	positions = {}
	order_tmp = {}
	enable_order_tmp =True

	def __init__(self, config : BaseConfig = json_config, task_center: TaskCenter = task_center):
		self.name = 'test_strategy'
		self._task_center = task_center

	@rpc
	async def forward(self, data: BaseData, platform, symbol, msg_type, detail):
		if msg_type == 'order':
			BaseTask(self._on_order_update_callback, data, platform, symbol, detail).attach2loop()
		elif msg_type == 'kline':
			BaseTask(self._on_kline_update_callback, data, platform, symbol, detail).attach2loop()
		elif msg_type == 'trade':
			BaseTask(self._on_trade_update_callback, data, platform, symbol, detail).attach2loop()
		elif msg_type == 'orderbook':
			BaseTask(self._on_orderbook_update_callback, data, platform, symbol, detail).attach2loop()
		else:
			logger('Unhandle msg type: {m}'.format(m=msg_type), caller=self)


	async def _on_kline_update_callback(self, data: BaseData, platform, symbol, detail):
		logger.debug('kline_update_callback receive msg: {m}'.format(m=data.to_json()))

	async def _on_trade_update_callback(self, data: BaseData, platform, symbol, detail):
		logger.debug('trade_update_callback receive msg: {m}'.format(m=data.to_json()))

	async def _on_order_update_callback(self, data: BaseData, platform, symbol, detail):
		logger.debug('order_update_callback receive msg: {m}'.format(m=data.to_json()))
		if self.enable_order_tmp:
			await self._update_order_tmp(data, detail);


	async def _update_order_tmp(self, data, detail):
		req_id = data.req_id
		if detail == 'open':
			self.order_tmp[req_id] = data.to_json()
		if req_id not in self.order_tmp:
			return
		if detail == 'update':
			self.order_tmp[req_id].update(data.to_json())
		elif detail in ['filled', 'canceled']:
			self.order_tmp.pop(req_id)
		else:
			logger.error('unhandle order detail: {d}'.format(d=detail), data, caller=self)
		logger.debug('Strategy order_tmp update: ', self.order_tmp, caller=self)

test_stra = BaseStrategy()
server = RpcServer(test_stra)
server.start()

