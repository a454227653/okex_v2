import pymongo

from recycle_bin.utils import *
from recycle_bin.Logger import Logger


class KBar():
    schema = ['platform', 'symbol', 'ts', 'bar', 'date', 'start_p', 'max_p', 'min_p', 'end_p', 'left_vol', 'right_vol', 'confirm']
    """
    ts: 起始10位时间戳, 数据库中作为 unique index
    bar: 时间跨度, 单位分钟, bar==1 是为 base_kbar, 是数据库存储或远端通信的最小单位, 数据库中作为 index
    date: ts 对应日期, 便于 debug 设置的字段
    start_p, max_p, min_p, end_p: 核心数据字段
    left_vol, right_vol: 左右侧计价成交量, 例如对 BTC-USDT, 左侧计价为 BTC 计价, 右侧计价为 USDT 计价
    confirm: 有效数据分钟数, 对已完结的 base_kbar 来说, confirm=1, 对已完结的其它 kabr 来说, confirm=bar; 原则上保证数据库的强一致性,落库数据必须完全 confirm, 未 confirm 的 kbar 由实时服务维护
    """
    def __init__(self, data):
        self.feed_data(data)
        self.logger = Logger(database_name='KBar', collection_name=self.symbol)

    def to_json(self):
        return {k: self.__getattribute__(k) for k in self.schema}

    def feed_data(self, data):
        for key in self.schema:
            if key in data.keys():
                self.__setattr__(key, data.get(key))
            else:
                self.__setattr__(key, None)
        self.check_value()

    def check_value(self):
        """
        创建任意 kbar 必须满足约束
        """
        assert self.confirm <= self.bar
        assert self.confirm >= 0
        assert self.min_p <= self.max_p
        assert date2ts(self.date) == self.ts
        assert (self.ts//60)%self.bar == 0

    def get_end_ts(self):
        """
        kbar有效数据最晚ts, 对于未完全 confirm 的 kbar, 最晚 ts 由 confirm 值确定
        """
        if self.confirm == self.bar:
            return self.ts + self.bar * 60 - 1
        else:
            assert self.confirm < self.bar

    def is_confirm(self):
        return self.confirm == self.bar

    def ts_inside(self, timestamp):
        """
        timestamp 是否在当前kbar中
        """
        return timestamp >= self.ts and timestamp <= self.get_end_ts()

    def dump(self, check_confirm=False):
        """
        存储kbar
        check_confirm=true 时，落盘 confirm=0 的 kbar 会引发中断
        """
        if self.bar == 1 and not self.is_confirm():
            if check_confirm:
                raise IOError('KBar dump failed, cannot dump unconfirmed base KBar.')
            else:
                return
        data = self.to_json()
        self.logger.collection.update_one({'ts': data.get('ts')}, {'$set': data}, upsert=True)
        return

    def lazy_load(self, ts, bar):
        """
        查询kbar数据
        """
        data = self.logger.collection.find_one({'ts':ts, 'bar':bar})
        return data

    def load(self, ts, bar):
        """
        加载任意维度kbar, db中没有对应kbar时，若 <ts, bar> 合法，尝试从base_kbar聚合加载
        """
        data = self.lazy_load(ts, bar)
        if data is not None:
            self.feed_data(data)
            return
        confirm = 0
        while(confirm<bar):
            return

    def find_max_bar(self, ts):
        """
        查找ts下bar最大的数据
        """
        return self.logger.collection.find_one({'ts':ts}).sort('bar', pymongo.DESCENDING)

    def merge(self, kbar):
        """
        合并 kbar, 适用于以下两种情况:
        更新最新数据(实时服务): 当前 kbar 未完全 confirm, 且输入 kbar 必须是 base_kbar
        聚合历史数据(离线落盘): 当前 kbar 必须完全 confirm, 且输入 kbar 是当前 kbar 的严格后继
        """
        # assert self.
        assert kbar.ts == self.get_end_ts() + 1
        self.bar = self.bar + kbar.confirm
        self.max_p = max(self.max_p, kbar.max_p)
        self.min_p = max(self.min_p, kbar.min_p)
        self.end_p = kbar.end_p