
from core.rpc.rpc_server import RpcServer, RpcClient
from core.task import *
import time, asyncio

rpc = RpcClient('test_server')

# channel = BaseTask(rpc.connect).run_once()
# res = BaseTask(rpc.request_async, '116', channel).run_once()

time.sleep(3)


async def req():
	tasks = [rpc.request_async({'args':[i]}, method='copy') for i in range(10)]
	res = await asyncio.gather(*tasks)
	print(res)
#
BaseTask(req).run_once()
# for i in range(10):
# 	rpc.request({'args':[i]}, method='copy')
# for i in range(1000):
#     res = rpc.request('clinet_1 {i}'.format(i=str(i)))
#     print(res)
#     time.sleep(0.1)

