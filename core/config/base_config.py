import json
import os

class BaseConfig():
	def __init__(self, path='./config.json'):
		with open(path, 'r') as file:
			self._data = json.load(file)

	def get(self, key=None, default=None):
		"""
		获取配置字段, 多层 key 用 '.' 分割, 例如 'TaskCenter.heartbeat_interval'
		"""
		if key is None:
			return self._data
		key_list = key.split('.')
		res = self._find(key_list, self._data)
		return res if res is not None else default

	def _find(self, key_list, data):
		if len(key_list)<=1:
			return data.get(key_list[0])
		else:
			return self._find(key_list[1:], data.get(key_list[0]))


path = os.path.split(os.path.abspath(__file__))[0]
json_config = BaseConfig(os.path.join(path, 'config.json'))

print(json_config.get('DataBase.main_db_name'))