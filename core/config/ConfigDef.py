"""
ConfigDef.py
created by Yan on 2023/4/25 17:36;
"""
import json
import os

class MainConfig():
	def __init__(self, path='./config.json'):
		with open(path, 'r') as file:
			data = json.load(file)
		self._data = data
		self.Global = GlobalConfig(data.get('Global', {}))
		self.TaskCenter = TaskCenterConfig(data.get('TaskCenter', {}))
		self.Rpc = RpcConfig(data.get('Rpc', {}))
		self.EventCenter = EventCenterConfig(data.get('EventCenter', {}))
		self.DataBase = DataBaseConfig(data.get('DateBase', {}))
		self.MarketServer = MarketServerConfig(data.get('MarketServer', {}))

	def __repr__(self):
		return json.dumps(self._data, indent=2, sort_keys=True, ensure_ascii=False)

	def get(self, key, default_value=None):
		return self._data.get(key, default_value)



class GlobalConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.env = data.get('env', 'production')


class TaskCenterConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.heartbeat_interval = data.get('heartbeat_interval', 1)
		self.print_interval = data.get('print_interval', 5)

class RpcConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.RabbitMq = RabbitMqConfig(data.get('RabbitMq',{}))

class RabbitMqConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.host = data.get('host', 'localhost')
		self.port = data.get('port', 5673)
		self.username = data.get('username', 'liwan')
		self.password = data.get('password', '199361')
		self.check_connection_interval = data.get('check_connection_interval', 5)
		self.channel_ack = data.get('channel_ack', False)

class ServicesConfig(MainConfig):
	def __int__(self, data):
		self._data = data


class EventCenterConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.host = data.get('host', 'localhost')
		self.port = data.get('port', 5673)
		self.username = data.get('username', 'liwan')
		self.password = data.get('password', '199361')
		self.exchanges = data.get('exchanges', ['kline'])
		self.check_connection_interval = data.get('check_connection_interval', 5)
		self.channel_ack = data.get('channle_ack', False)
		self.EventDef = EventDefConfig(data.get('EventDef', {}))


class EventDefConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.EVENT_KLINE = EventConfig(data.get('EVENT_KLINE', {}))
		self.EVENT_MSG = EventConfig(data.get('EVENT_MSG', {}))

class EventConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.server_id = data.get('server_id', 0)
		self.exchange = data.get('exchange', None)
		self.queue = data.get('queue', None)
		self.routing_key = data.get('routing_key', None)

class DataBaseConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.main_db_name = data.get('main_db_name', 'MongoDB')
		self.MongoDB = dbConfig(data.get('MongoDB', {}))
		self.MongoDBTest = dbConfig(data.get('MongoDBTest', {}))
		self.main_db = dbConfig(data.get(self.main_db_name, {}))

class dbConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.server = data.get('server', 'mongodb://local_host:27017')
		self.username = data.get('username', None)
		self.password = data.get('password', None)

class MarketServerConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.WebSockets = WebsocketsConfig(data.get("WebSockets"))
		self.Platforms = PlatformsConfig(data.get('Platforms'))

class WebsocketsConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.proxy = data.get("proxy", None)
		self.check_conn_interval = data.get("check_conn_interval", 10)

class PlatformsConfig(MainConfig):
	def __init__(self, data):
		self._data = data
		self.OKEX_MARKET_RESET = PlatformConifg(data.get('OKEX_MARKET_RESET', {}), tag='OKEX_MARKET_WEBSOCKETS')
		self.OKEX_MARKET_WEBSOCKETS = PlatformConifg(data.get('OKEX_MARKET_WEBSOCKETS', {}), tag='OKEX_MARKET_WEBSOCKETS')

class PlatformConifg(MainConfig):
	def __init__(self, data, tag):
		self._data = data
		self.platform = data.get('platform', tag)
		self.access_key = data.get('access_key', None)
		self.secret_key = data.get('secret_key', None)
		self.pass_word = data.get('pass_word', None)
		self.host = data.get('pass_word', None)
		self.tag = data.get('tag', None)





path = os.path.split(os.path.abspath(__file__))[0]
config = MainConfig(os.path.join(path, 'config.json'))