"""
test.py
created by Yan on 2023/5/17 17:00;
"""


from service import *
from core.rpc.rpc_server import RpcClient

client = RpcClient(service)

res = client.request({'m':'load', 'args':['aa.json']})

print(res.get())
