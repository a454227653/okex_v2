
from core.rpc.rpc_server import RpcServer, RpcClient
from core.task import *
import time, asyncio

rpc = RpcClient(['test_server', 'BTC-USDT.kline_update'])

# channel = BaseTask(rpc.connect).run_once()
# res = BaseTask(rpc.request_async, '116', channel).run_once()

time.sleep(3)


for i in range(100):
	time.sleep(0.05)
	res = rpc.request({'args':[-i]}, method='copy', no_reply=True)
	print(res)

# async def wait():
# 	for i in range()
# for i in range(10):
# 	rpc.request({'args':[i]}, method='copy')
# for i in range(1000):
#     res = rpc.request('clinet_1 {i}'.format(i=str(i)))
#     print(res)
#     time.sleep(0.1)

