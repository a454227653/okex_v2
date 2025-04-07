"""
base_data.py
created by Yan on 2023/6/16 20:57;
"""
from core.task.BaseTask import BaseTask


class BaseData():
	# 数据库的存储 schema
	schema = []
	# 数据库索引字段,
	# 允许多个索引, 字段组合,
	# eg: [[(A, -1), (B, 1)],[(A, -1)], [(B, 1)]]
	# 建立了三个索引, 1: A-1_B1, A-1, B1
	index_def = []
	# 数据库索引是否唯一, unique 长度需要与索引数量对齐
	unique = []

	def __init__(self, data, db_name, path=None):
		assert len(self.index_def) == len(self.unique)
		self.feed_data(data)
		self.db_name = db_name
		self.path = path

	def to_json(self, filter_none=True):
		res = {}
		for k in self.schema:
			v = self.__getattribute__(k)
			if v is None and filter_none:
				continue
			res[k] = v
		return res

	def feed_data(self, data):
		for key in self.schema:
			if key in data.keys():
				self.__setattr__(key, data.get(key))
			else:
				self.__setattr__(key, None)

	def check_value(self):
		# 数据落盘前必须先校验, 严禁脏数据落盘, 维持 db 强一致性
		pass

	def check_none(self, values):
		for v in values:
			if v is None:
				return False
		return True

	def get_cond(self, cond: list):
		if cond is None or len(cond) == 0:
			cond = [k[0] for k in self.index_def[0]]
		return {k: self.__getattribute__(k) for k in cond}

	def dump(self, client):
		BaseTask(self.dump_async, client).run_once()

	async def dump_async(self, client):
		request = {
			'm': 'dump_bd',
			'kwargs': {
				'data': self
			}
		}
		await client.request_async(request, server_name='mongodb')

	def update(self, client, cond=None):
		BaseTask(self.update_async, client, cond).run_once()

	async def update_async(self, client, cond=None):
		request = {
			'm': 'update_bd',
			'kwargs': {
				'data': self,
				'cond': cond
			}
		}
		await client.request_async(request, server_name='mongodb')


class LogData(BaseData):
	schema = [
		'name'
		, 'id'
		, 'tag'
		, 'ts'
		, 'date'
		, 'data'
		, 'pt'
	]

	index_def = [[('tag', -1), ('pt', -1), ('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('name')
		super().__init__(data, db_name='log', path=path)


class TaskData(BaseData):
	# 离线调度的实例
	schema = [
		'task_name'
		, 'interval'  # 调度周期, hour, day, month, 为 None 时不自动调度
		, 'dep_tasks'  # 上游依赖任务列表
		, 'max_retry_nums'  # 最大重试次数
		, 'max_instance_nums'  # 保留实例记录个数
		, 'max_parallel_num'  # 允许并行 n 个实例, 为 0 时不会被调度
		, 'task_create_ts'
		, 'task_update_ts'
		, 'task_create_date'  # 创建时间
		, 'task_update_date'  # 更新时间
		, 'code_path'  # 任务脚本路径
		, 'code_type'  # python, bash
		, 'para'  # 启动参数
	]

	index_def = [[('task_name', -1), ('task_update_ts', -1)]]
	unique = [True]

	def __init__(self, data):
		super().__init__(data, db_name='pipline', path='tasks')

	async def register_async(self, client):
		request = {
			'm': 'register_task'
			, 'kwargs': {
				'data': self
			}
		}
		await client.request_async(request, server_name='mongodb')

	async def update_async(self, client):
		request = {
			'm': 'update_task'
			, 'kwargs': {
				'data': self
			}
		}
		await client.request_async(request, server_name='mongodb')

	async def run_async(self, client, pts):
		request = {
			'm': 'run_task'
			, 'kwargs': {
				'data': self
				, 'pts': pts
			}
		}
		await client.request_async(request, server_name='mongodb')


class InstanceData(BaseData):
	# 离线调度的实例
	schema = TaskData.schema + [
		'id'  # 自动调度实例 id = {pt} , 手动生成实例 id={pt}-{create_ts}
		, 'pt'  # YYYYMMDDHH
		, 'status'  # 实例状态, init: 上游未就绪, ready: 等待调度, running: 运行中, failed: 失败, suspend: 挂起
		, 'dep_instance'  #
		, 'instance_create_ts'
		, 'instance_create_date'  # 实例创建时间
		, 'instance_start_date'  # 实例开始运行时间
		, 'instance_update_date'  # 实例状态更新时间
		, 'retry_nums'  # 自动重试次数
		, 'code'  # 脚本代码
		, 'log'  # 运行日志
	]

	index_def = [[('pt', -1), ('instance_create_ts', -1)], [('status', 1)], [('id', 1)]]
	unique = [True, False, True]
	code_tmp = None

	def __init__(self, data, task_data: TaskData = None):
		if task_data is not None:
			data.update(task_data.to_json())
		path = data.get('task_name')
		super().__init__(data, db_name='pipline', path=path)

	async def create_async(self, client, is_auto=True):
		request = {
			'm': 'create_instance'
			, 'kwargs': {
				'data': self,
				'is_auto': is_auto
			}
		}
		await client.request_async(request, server_name='mongodb')

	async def update_async(self, client):
		request = {
			'm': 'update_instance'
			, 'kwargs': {
				'data': self,
			}
		}
		await client.request_async(request, server_name='mongodb')

	async def submit_instance(self, client):
		request = {
			'm': 'run_instance'
			, 'kwargs': {
				'data': self,
			}
		}
		await client.request_async(request, server_name='pipline')