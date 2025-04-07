"""
test_request.py
created by Yan on 2023/6/13 19:47;
"""


from core.rpc.rpc_server import RpcClient
from services.data_service.base_data import InstanceData, TaskData
from core.task.BaseTask import BaseTask
import os, asyncio
#
# path = os.path.dirname(os.path.abspath(__file__))
# code_path = path+'/pipline/bash/test_bash.sh'
# with open(code_path, 'r') as file:
# 	code = file.read()
#
#
tmp = {
	'task_name' : 'test_python'
	, 'interval' : 'hour'
	, 'dep_tasks' : None
	, 'code_path': '/pipline/python/test_python.py'
	, 'code_type': 'python'
}
task = TaskData(tmp)

rpc_client = RpcClient('aaa', hello_server=False)
BaseTask(task.register_async, rpc_client).run_once()
# res = rpc_client.request(request = {}, server_name='mongodb')

# request = {
# 	'm': 'run_task',
# 	'kwargs': {
# 		'task': 'test_python',
# 		'pts': ['20230617']
# 	}
# }

# rpc_client.request(request=request)
