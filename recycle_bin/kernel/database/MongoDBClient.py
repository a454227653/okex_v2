"""
MongoDBClient.py
created by Yan on 2023/4/25 15:42;
"""

import pymongo
from core.utils import logger
from core.config import *


class MongoDBClient():
	def __init__(self, config : MainConfig = config):
		self.server = config.DataBase.main_db.server
		self.username = config.DataBase.main_db.username
		self.password = config.DataBase.main_db.password
		self.connect()


	def connect(self):
		if self.username and self.password:
			self.client = pymongo.MongoClient(self.server, username=self.username, password=self.password)
		else:
			self.client = pymongo.MongoClient(self.server)
		logger.debug("database server:", self.server, caller=self)


	def dump(self, db_name:str, path: str, data_dir: dir):
		"""
		新增一条数据，字典格式
		"""
		try:
			self.client[db_name][path].insert_one(data_dir)
		except Exception as e:
			logger.error("mongo_up_error : ", e, caller=self)
			# Ding.send_text(f"mongo_up_error : {e}")
			self.connect()

	def dumps(self, db_name:str, path: str, data_list: list):
		"""
		批量新增数据，列表格式
		"""
		try:
			self.client[db_name][path].insert_many(data_list)
		except Exception as e:
			logger.error("mongo_ups_error : ", e, caller=self)
			# Ding.send_text(f"mongo_ups_error : {e}")
			self.connect()

	def update(self, db_name:str, path: str, old: dir, new: dir):
		"""
		修改数据，old为条件，new为新数据
		"""
		try:
			self.client[db_name][path].update_one(old, {"$set": new})
		except Exception as e:
			logger.error("mongo_update_error : ", e, caller=self)
			# Ding.send_text(f"mongo_update_error : {e}")
			self.connect()

	def del_all(self, db_name:str, path: str):
		"""
		清空整个集合
		"""
		try:
			self.client[db_name][path].delete_many({})
		except Exception as e:
			logger.error("mongo_del_all_error : ", e, caller=self)
			# Ding.send_text(f"mongo_del_all_error : {e}")
			self.connect()

	def load(self, db_name:str, path: str):
		"""
		获取集合数据
		"""
		try:
			res = self.client[db_name][path].find({}, {"_id": 0})
			# data = ([ r for r in res])
			data = list(res)
		except Exception as e:
			print("load db None")
			logger.error("mongo_load_error : ", e, caller=self)
			# Ding.send_text(f"mongo_load_error : {e}")
			return False, e
		return data, None if data else "is none"

mongo_client = MongoDBClient(config)