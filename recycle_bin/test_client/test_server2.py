"""
test_server2.py
created by Yan on 2023/5/15 17:21;
"""


from core.rpc.rpc_server import *
import time

class test_server(Rpc):
	mode = 'broadcast'
	@rpc
	async def copy(self, x):
		return x

	@rpc
	def plus(self, x, y):
		return x+y

	@rpc
	def mul(self, x=None, y=None):
		return x*y


server = test_server()
rpc = RpcServer(server)
rpc.start()