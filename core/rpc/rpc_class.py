"""
test.py
created by Yan on 2023/5/15 17:50;
"""

from core.utils import logger, tools

def rpc(x):
	x._tag = 'rpc'
	return x

class Rpc:
	rpc_methods = {}
	mode = 'competition'  # competition: 多个同名 server 竞争消费队列消; broadcast: 订阅模式, 每个 server 订阅各自频道的消息
	# 服务监听 routing_key 为 {server_name}.{server_channel}
	server_name = None   #默认为继承 Rpc 的类名
	server_id = None     #Rpc 实例的全局唯一id, rpcServer 在广播模式下会沿用此 id
	server_channels = ['default'] #用于同一server_name 订阅不同频道

	def __init__(self):
		self.server_id = tools.get_uuid4()

	def get_rpc_method(self):
		attributes = [getattr(self.__class__, func) for func in dir(self.__class__)]
		for attr in attributes:
			if '_tag' in dir(attr) and attr._tag == 'rpc':
				self.rpc_methods[attr.__name__] = self.__getattribute__(attr.__name__)
		return self.rpc_methods

	@rpc
	def get_rpc(self):
		return [m for m in self.rpc_methods]

# class rpc_test(Rpc):
#
# 	@rpc
# 	def compute_plus(self, x, y):
# 		return x+y
#
# 	@rpc
# 	def compute_mul(self, x, y):
# 		return x/y


# t = rpc_test()
# rpc_methods = t.get_rpc()
# print(rpc_methods)
# args = [1, 2]
# kwargs = {'x':1, 'y':2}
# res = rpc_methods['compute_mul'](x=1, y=2)
# print(res)
# res = rpc_methods['compute_mul'](**kwargs)
# print(res)
# res = rpc_methods['compute_mul'](*args)
# print(res)

