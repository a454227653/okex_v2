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
        self._platform_config = config.get('MarketServer.Platforms.{p}'.format(p=self._platform_tag))
        self._platform = self._platform_config.get('platform')
        self._host = self._platform_config.get('host')
        self._is_cheif_worker = is_cheif_worker
        self._channel_map = {}
        self._tag = self._platform_config.get('tag')
        self._platform_rt = 0
        self._account_tmp = {}  # 持仓表 e.g. {{uid}.{ccy}: account_detail}
        self._order_tmp = {}  # 挂单表 e.g. {req_id : order_detail}
        self._tmp_file = './tmp/{p}.json'.format(p=self._platform_tag)
        if os.path.exists(self._tmp_file):
            with open(self._tmp_file, 'r') as f:
                self._order_tmp = json.load(f)
        self._count = 0
        self._count1 = 0
        # 计算项目根目录（假设你的项目根目录和当前脚本有固定的层级关系）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
        data_root = os.path.join(project_root, "data_root/MongoDBLocal/okex_market/")
        tables = os.listdir(data_root)
        self._data_tem = {}
        for i,table in enumerate(tables):
            coin_name,ext = table.split('.')
            self._data_tem[coin_name] = []
        #定义每个币值临时存放最小数量，默认100
        self._min_tem_num = config.get('MarketServer.Platforms.{p}.min_temp_num'.format(p=self._platform_tag),100)
        #定义ttl检查时间间隔,默认0.5s一次
        self._ttl_tem = config.get('MarketServer.Platforms.{p}.ttl_temp'.format(p=self._platform_tag), 1)
        super(OkexWs, self).__init__(host=self._host, config=json_config, task_center=task_center)
        LoopTask(self._ttl_and_num_datainsert, loop_interval=self._ttl_tem).register(task_center)
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
                BaseTask(MongoDBLocal.error.async_dump, e, self).attach2loop()
            else:
                msg = 'unhandled event: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(MongoDBLocal.error.async_dump, e, self).attach2loop()
        elif 'arg' in data and 'data' in data:  # 行情数据
            data_type = data.get('arg').get('channel')
            if data_type == 'trades-all':  # 成交推送
                BaseTask(self._on_tradesall_callback, data).attach2loop()
            else:
                msg = 'unhandled market data: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(MongoDBLocal.error.async_dump, e, self).attach2loop()
    
    async def _on_tradesall_callback(self, data):
        arg = data.get('arg')
        str_db = arg['instId'] + '@' + arg['channel']
        data = data.get('data')[0]
        self._count +=1
        data['ts'] = datetime.fromtimestamp(int(data['ts']) / 1000, tz=timezone.utc)
        if len(self._data_tem[str_db]) < self._min_tem_num:
            self._data_tem[str_db].append(data)
            self._data_tem[str_db].append(data)
            self._data_tem[str_db].append(data)
            self._data_tem[str_db].append(data)
            self._data_tem[str_db].append(data)
            self._data_tem[str_db].append(data)
        
    async def _ttl_and_num_datainsert(self):
        self._count1 += 1
        dums_count = 0
        for key,data_table_tmp in self._data_tem.items():
            if len(data_table_tmp)>=self._min_tem_num:
                await MongoDBLocal.dumps('okex_market', key, data_table_tmp)
                dums_count += 1
                
        logger.info('count : ', self._count,' **count1 : ', self._count1, ' **dums_count: ', dums_count,caller=self)

from core.config.base_config import json_config
import logging

logging.getLogger().setLevel(logging.INFO)
platform_tags = ['OKEX_BUSINESS']
if __name__ == "__main__":
    for tag in platform_tags:
        okws = OkexWs(tag, config=json_config)
    
    okws._task_center.start()
