"""
okex_ws.py
created by Yan on 2023/5/18 15:34;
"""

import asyncio, json, os, traceback

from core.config.base_config import BaseConfig, json_config
# from core.rpc.rpc_server import RpcClient, rpc
from core.task import TaskCenter, task_center, BaseTask, LoopTask
from core.utils import logger

from services.market_service.plat.web_sockets import WebSocket

from core.data.data_base import MongoDBLocal
from datetime import datetime
from datetime import timezone


class OkexWs(WebSocket):
    _platform_tag = 'OKEX_PUBLIC_TEST'
    
    def __init__(self, platform_tag=None, server_name=None, is_cheif_worker=True, config: BaseConfig = json_config,
                 task_center: TaskCenter = task_center):
        self._platform_tag = platform_tag or self._platform_tag
        self.server_name = server_name or self._platform_tag
        # self._rpc_client = RpcClient(self.server_name, self.server_id, hello_server=False)
        self._platform_config = config.get('MarketServer.Platforms.{p}'.format(p=self._platform_tag))
        self._platform = self._platform_config.get('platform')
        self._host = self._platform_config.get('host')
        # self._access_key = self._platform_config.get('access_key')
        # self._secret_key = self._platform_config.get('secret_key')
        # self._passphrase = self._platform_config.get('pass_word')
        self._is_cheif_worker = is_cheif_worker
        self._channel_map = {}
        self._tag = self._platform_config.get('tag')
        self._platform_rt = 0
        self._account_tmp = {}  # 持仓表 e.g. {{uid}.{ccy}: account_detail}
        self._order_tmp = {}  # 挂单表 e.g. {req_id : order_detail}
        self._tmp_file = './tmp/{p}.json'.format(p=self._platform_tag)
        self._count = 0
        if os.path.exists(self._tmp_file):
            with open(self._tmp_file, 'r') as f:
                self._order_tmp = json.load(f)
        super(OkexWs, self).__init__(host=self._host, config=json_config, task_center=task_center)
        LoopTask(self._log_report, loop_interval=60).register(task_center)
    
    async def _log_report(self, type='monitor', msg=None):
        # 监控/报错日志
        if type == 'monitor':
            data = {'type': 'monitor', 'data_server_rt':0,
                    'platform_rt':0}
        elif type == 'error':
            data = {'type': 'error', 'e': msg.args[0],
                    'trace_back': "\n" + "".join(traceback.format_tb(msg.__traceback__))}
        else:
            data = msg
        logger.info('OkexWs report log: {d}'.format(d=data), caller=self)
        await MongoDBLocal.log.async_dump(data, self)
    
    async def _on_connected_callback(self):
        """
        连接成功后执行订阅全部交易频道
        """
        data = {
            "op": "subscribe",
            "args": self._platform_config.get('channels')
        }
        await self.send(data)
    
    async def _on_receive_data_callback(self, data):
        # logger.debug('OkexWs receive message: ', data, caller = self)
        if 'event' in data:  # 登录, 订阅, 取消订阅, pong 消息
            event = data.get('event')
            if event == 'subscribe':  # 订阅成功
                logger.info('OkexWs receive subscribe: ', data, caller=self)
            elif event == 'error':  # 远端报错
                msg = 'OkexWs receive error: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(msg, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
            else:
                msg = 'unhandled event: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
        elif 'arg' in data and 'data' in data:  # 行情数据
            data_type = data.get('arg').get('channel')
            if data_type == 'trades-all':  # 成交推送
                BaseTask(self._on_tradesall_callback, data).attach2loop()
            else:
                msg = 'unhandled market data: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
    
    async def _on_tradesall_callback(self, data):
        arg = data.get('arg')
        str_db = arg['instId'] + '@' + arg['channel']
        data = data.get('data')[0]
        self._count +=1
        logger.info('count : ', self._count, caller=self)
        # file_name = "trade_ids.txt"
        # with open(file_name, "a") as file:  # 以追加模式 ('a') 打开文件
        #     file.write(f"{self._count}\n")
        #     file.flush()
        #data['ts'] = datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc)
        #logger.debug('OkexWs dump TradeData: ', data, caller=self)
        #await MongoDBLocal.dump('okex_market', str_db, data)


from core.config.base_config import json_config
import logging

logging.getLogger().setLevel(logging.INFO)
platform_tags = ['OKEX_BUSINESS']
if __name__ == "__main__":
    for tag in platform_tags:
        okws = OkexWs(tag, config=json_config)
    
    okws._task_center.start()
