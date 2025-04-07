"""
data_service.py
created by Yan on 2023/5/17 16:26;
"""


from core.rpc.rpc_server import *
from core.config import *


import json
import os
from core.utils import logger

class ConfigService(Rpc):
	path = os.path.split(os.path.abspath(__file__))[0] + '/leo'

	def __init__(self):
		super(ConfigService, self).__init__()

	@rpc
	async def load(self, config_name):
		path = os.path.join(self.path, config_name)
		if not os.path.isfile(path):
			e = FileNotFoundError('Config file [{f}] not found, avaliable config list: {l}'.format(f=config_name, l=os.listdir(self.path)))
			logger.error(e, caller=self)
			raise e
		return BaseConfig(os.path.join(path))

	@rpc
	async def dump(self, config_file, config_name):
		path = os.path.join(self.path, config_name)
		if os.path.isfile(path):
			e = FileExistsError('Config file [{f}] already exist, avaliable config list: {l}'.format(f=config_name, l=os.listdir(self.path)))
			logger.error(e, caller=self)
			raise e
		with open(path, 'w') as file:
			json.dump(config_file, file, indent=2)
		return 0

	@rpc
	async def update(self, config_file, config_name):
		path = os.path.join(self.path, config_name)
		with open(path, 'w') as file:
			json.dump(config_file, file, indent=2)
		return 0

	@rpc
	async def remove(self, config_name):
		path = os.path.join(self.path, config_name)
		os.remove(path)
		return 0


service = ConfigService()
if __name__ == "__main__":
	server = RpcServer(service)
	server.start()