"""
BaseData.py
created by Yan on 2023/4/25 15:28;
"""
from core.utils.tools import *

class BaseData():
	# 数据库的存储 schema
	schema = []
	# 数据库索引字段,
	# 允许多个索引, 字段组合,
	# eg: [[(A, -1), (B, 1)],[(A, -1)], [(B, 1)]]
	# 建立了三个索引, 1: A-1_B1, A-1, B1
	index_def = []
	# 数据库索引是否唯一, unique 长度需要与索引数量对齐
	unique = []
	# 数据库客户端
	_db_client = None
	def __init__(self, data, db_name, path = None, _db_client = mongo_client):
		assert len(self.index_def) == len(self.unique)
		self.feed_data(data)
		self._db_name = db_name
		self._path = path
		self._db_client = _db_client

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
		pass

	def dump(self):
		if self._path not in self._db_client.client[self._db_name].list_collection_names():
			self._db_client.client[self._db_name].create_collection(self._path)
			for index, unique in zip(self.index_def, self.unique):
				self._db_client.client[self._db_name].get_collection(self._path).create_index(index, unique=unique)
		self._db_client.dump(self._db_name, self._path, self.to_json())


class KLineData(BaseData):
	schema = ['platform', 'symbol', 'ts', 'bar', 'date', 'start_p', 'max_p', 'min_p', 'end_p', 'left_vol', 'right_vol', 'confirm']
	index_def = [[('ts', -1), ('bar', 1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('platform')+'/'+data.get('symbol')
		self.platform = data.get('platform')
		self.symbol = data.get('symbol')
		super().__init__(data, 'kline', path)

	def check_value(self):
		assert self.confirm <= self.bar
		assert self.confirm >= 0
		assert self.min_p <= self.max_p
		assert date2ts13(self.date) == self.ts
		assert (self.ts // 60000) % self.bar == 0


class OrderBookData(BaseData):
	schema = ['platform', 'symbol', 'ts', 'date', 'price', 'left_vol', 'right_vol', ]
	index_def = [[('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('platform') + '/' + data.get('symbol')
		super().__init__(data, 'order_book', path)

	def check_value(self):
		assert datetime_str_to_ts(self.date) == self.ts
		assert self.ts > 9999999999