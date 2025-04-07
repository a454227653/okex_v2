"""
data_service.py
created by Yan on 2023/5/16 21:34;
"""

import pymongo

from core.config.base_config import *
from core.rpc.rpc_server import *
from core.task.BaseTask import BaseTask, LoopTask
from core.task.TaskCenter import TaskCenter, task_center
from core.utils import logger
from services.constant import *
from services.data_service.base_data import BaseData, LogData, TaskData, InstanceData


class MongoDBService(Rpc):
	mode = BROADCAST
	server_name = 'mongodb'

	def __init__(self, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
		main_db_name = config.get('DataBase.main_db_name')
		self.server = config.get('DataBase.{m}.server'.format(m=main_db_name))
		self.username = config.get('DataBase.{m}.username'.format(m=main_db_name), None)
		self.password = config.get('DataBase.{m}.password'.format(m=main_db_name), None)
		self._task_center = task_center
		self.connect()
		self._pt = 0
		super(MongoDBService, self).__init__()
		self._rpc_client = RpcClient(rpc=self.server_name, client_id=self.server_id, hello_server=False)
		LoopTask(self.pipline_update_loop, loop_interval=20).register(self._task_center)
		# LoopTask(self.pipline_submit_loop, loop_interval=120).register(self._task_center)

	def connect(self):
		if self.username and self.password:
			self.client = pymongo.MongoClient(self.server, username=self.username, password=self.password)
		else:
			self.client = pymongo.MongoClient(self.server)
		logger.debug("database server:", self.server, caller=self)

	def as_error(self, e):
		self.connect()
		logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
		ts = tools.get_now_ts13()
		tmp = {
			'name': self.server_name
			, 'id': self.server_id
			, 'tag': 'error'
			, 'ts': ts
			, 'date': tools.ts132date(ts)
			, 'data': {'e': e.args[0], 'trace_back': "\n" + "".join(traceback.format_tb(e.__traceback__))}
			, 'pt': tools.ts132pt(ts)
		}
		base_data = LogData(tmp)
		BaseTask(self.dump_bd, base_data).attach2loop()
		raise e

	async def check_path(self, data: BaseData):
		# BaseData 任何落盘操作前必须调用
		try:
			data.check_value()
			if data.path not in self.client[data.db_name].list_collection_names():
				self.client[data.db_name].create_collection(data.path)
				for index, unique in zip(data.index_def, data.unique):
					self.client[data.db_name].get_collection(data.path).create_index(index, unique=unique)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def dump_bd(self, data: BaseData):
		await self.check_path(data)
		await self.dump(data.db_name, data.path, data.to_json(filter_none=False))

	@rpc
	async def dump_bds(self, data: list):
		if len(data) == 0:
			return
		await self.check_path(data[0])
		for d in data:
			d.check_value()
		self.dump(data[0].db_name, data.path[0], [d.to_json(filter_none=False) for d in data])

	@rpc
	async def update_bd(self, data: BaseData, cond=None):
		await self.check_path(data)
		await self.update(data.db_name, data.path, data.get_cond(cond), data.to_json(filter_none=False))

	@rpc
	async def find_bd(self, data: BaseData):
		res = await self.load(data.db_name, data.path, data.to_json(filter_none=False))
		if len(res) == 0:
			return []
		else:
			return [data.__class__(d) for d in res]

	@rpc
	async def clear_bd(self, data: BaseData):
		if data.path in self.client[data.db_name].list_collection_names():
			await self.del_all(data.db_name, data.path)

	@rpc
	async def dump(self, db_name: str, path: str, data_dir: dir):
		"""
		新增一条数据，字典格式
		"""
		try:
			self.client[db_name][path].insert_one(data_dir)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def dumps(self, db_name: str, path: str, data_list: list):
		"""
		批量新增数据，列表格式
		"""
		try:
			self.client[db_name][path].insert_many(data_list)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def update(self, db_name: str, path: str, old: dir, new: dir):
		"""
		修改数据，old为条件，new为新数据
		"""
		try:
			self.client[db_name][path].update_one(old, {"$set": new}, upsert=True)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def del_all(self, db_name: str, path: str):
		"""
		清空整个集合
		"""
		try:
			self.client[db_name][path].delete_many({})
		except Exception as e:
			self.as_error(e)

	@rpc
	async def load(self, db_name: str, path: str, condition: map):
		"""
		获取集合数据
		"""
		try:
			res = self.client[db_name][path].find(condition)
			data = list(res)
			return data
		except Exception as e:
			self.as_error(e)

	@rpc
	async def del_many(self, db_name: str, path: str, condition: map):
		"""
		删除一条记录
		"""
		try:
			self.client[db_name][path].delete_many(condition)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def find_task(self, task_name=None):
		"""
		查找任务名下最新记录
		"""
		if task_name is None:
			# 查找所有 task 的最新记录
			cond = [
				{'$sort': {'task_update_ts': -1}},
				{'$group': {'_id': '$task_name', 'max_record': {'$first': '$$ROOT'}}}
			]
		else:
			# 查找单个
			cond = [
				{"$match": {"task_name": task_name}},
				{"$sort": {"task_update_ts": -1}},
				{"$limit": 1}
			]
		try:
			result = self.client['pipline']['tasks'].aggregate(cond)
			if task_name is None:
				res = []
				for d in result:
					if 'max_record' in d:
						d = d.get('max_record')
					task = TaskData(d)
					res.append(task)
				return res
			else:
				return TaskData(result.next()) if result.alive else None
		except Exception as e:
			self.as_error(e)

	@rpc
	async def register_task(self, data: TaskData):
		try:
			task = await self.find_task(data.task_name)
			if task is not None:
				raise IOError('DataService register failed, task_name {t} already exists'.format(t=[data.task_name]))
			ts = tools.get_now_ts13()
			date = tools.ts132date(ts)
			data.task_create_ts = ts
			data.task_create_date = date
			data.task_update_ts = ts
			data.task_update_date = date
			if data.code_path is None:
				post_fix_map = {'python': 'py', 'bash': 'sh'}
				data.code_path = '/pipline/{t}/{n}.{p}'.format(t=data.code_type, n=data.task_name, p=post_fix_map[data.code_type])
			data.dep_tasks = data.dep_tasks or []
			data.max_retry_nums = data.max_retry_nums or 0
			data.max_instance_nums = data.max_instance_nums or 100
			data.max_parallel_num = data.max_parallel_num or 1
			data.para = data.para or {'pt': '$.pt'}
			logger.debug('DataService register new task: {d}'.format(d=data.to_json()), caller=self)
			self.client[data.db_name][data.path].insert_one(data.to_json())
		except Exception as e:
			self.as_error(e)

	@rpc
	async def update_task(self, data: TaskData):
		ts = tools.get_now_ts13()
		data.task_update_ts = ts
		data.task_update_date = tools.ts132date(ts)
		try:
			task = await self.find_task(data.task_name)
			if task is not None:
				json_data = task.to_json()
				json_data.update(data.to_json())
			self.client[data.db_name][data.path].insert_one(json_data)
			logger.debug('DataService update task: {d}'.format(d=json_data), caller=self)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def delete_task(self, task_name):
		await self.del_many(db_name='pipline', path='tasks', condition={'task_name': task_name})
		await self.del_all(db_name='pipline', path=task_name)
		logger.debug('DataService delete task: {d}'.format(d=task_name), caller=self)

	@rpc
	async def run_task(self, task, pts, is_rerun=True):
		try:
			# task 存在且 interval != None
			if isinstance(task, str):
				task_name = task
			elif isinstance(task, TaskData):
				task_name = task.task_name
			else:
				raise Exception('DataService run task failed, invalid type of task input: {t}'.format(t=task))
			task_data = await self.find_task(task_name)
			if task_data is None:
				raise Exception('DataService run task failed, there is no task named {t}'.format(t=task_name))
			if task_data.interval is None:
				raise Exception('DataService run task failed, task interval is None: {t}'.format(t=task_data.to_json()))

			# pts 解析
			if isinstance(pts, str):
				pts_spl = pts.split('-')
				if len(pts_spl)==2:
					if int(pts_spl[0])>int(pts_spl):
						raise Exception('DataService run task failed, invalid value of pts: {p}'.format(p=pts))
					if task.interval == 'hour':
						pts = [pt for pt in range(int(pts_spl[0]), int(pts_spl[1])+1)]
					elif task.interval == 'day':
						pts = [pt*100 for pt in range(int(pts_spl[0])//100, int(pts_spl[1])//100+1)]
					else:
						raise Exception('DataService run task failed, task interval is invalid: {t}'.format(t=task_data.to_json()))
				elif len(pts_spl)==1:
					pts = [int(pts_spl[0])]
				else:
					raise Exception('DataService run task failed, invalid value of pts: {p}'.format(p=pts))
			elif isinstance(pts, int):
				pts = [pts]
			else:
				raise Exception('DataService run task failed, invalid type of pts: {p}'.format(p=pts))

			# 读取通用字段
			ts = tools.get_now_ts13()
			code_path = os.path.dirname(os.path.abspath(__file__)) + task_data.code_path
			with open(code_path, 'r') as file:
				code = file.read()
			for pt in pts:
				if is_rerun:
					ins_id = '{pt}.{ts}'.format(pt=pt, ts=ts)
					status = 'ready'
					dep_instance = []
				else:
					if len(await self.find_instance(task_name, cond={'id': pt}))>0:
						continue
					ins_id = pt
					status = 'init'
					dep_instance = []
					for dep_task_name, offset_str in task_data.dep_tasks:
						offset_str_spl = offset_str.split('-')
						interval = offset_str_spl[0][1:]
						if len(offset_str_spl) == 2:
							offsets = [i for i in range(int(offset_str_spl[0][0]), int(offset_str_spl[1][0]) + 1)]
						elif len(offset_str_spl) == 1:
							offsets = [int(offset_str_spl[0][0])]
						else:
							raise Exception('DataService run task failed, invalid dep_tasks: {p}'.format(task_data.dep_tasks))
						for offset in offsets:
							dep_instance.append((dep_task_name, tools.get_prev_pt(pt, interval, offset)))
				instance_data = {
					'id': ins_id
					, 'pt': pt
					, 'status': status
					, 'dep_instance': dep_instance
					, 'instance_create_ts': ts
					, 'instance_create_date': tools.ts132date(ts)
					, 'instance_start_date': None
					, 'instance_update_date': None
					, 'retry_nums': None
					, 'code': code
					, 'log': None
				}
				instance_data.update(task_data.to_json())
				self.client['pipline'][task_data.task_name].insert_one(instance_data)
		except Exception as e:
			self.as_error(e)


	@rpc
	async def update_instance(self, data: InstanceData):
		data.update_date = tools.get_now_date()
		try:
			instance_data = await self.find_instance(data.task_name, cond={'id': data.id})
			if len(instance_data) > 0:
				json_data = instance_data[0].to_json()
				json_data.update(data.to_json())
			else:
				json_data = data.to_json()
			self.client[data.db_name][data.path].update_one({'id': data.id}, {"$set": json_data}, upsert=True)
		except Exception as e:
			self.as_error(e)

	@rpc
	async def find_instance(self, task_name, cond):
		cond = [
			{"$match": cond},
			{"$sort": {"ins_id": 1}}
		]
		try:
			result = self.client['pipline'][task_name].aggregate(cond)
			res = []
			for data in result:
				res.append(InstanceData(data))
			return res
		except Exception as e:
			self.as_error(e)

	async def pipline_update_loop(self):
		pt = tools.get_now_pt()
		tasks = await self.find_task()
		start_hour = pt > self._pt
		start_day = (pt // 100) > (self._pt // 100)
		task_nums = 0
		stop_task_nums = 0
		hour_task_nums = 0
		day_task_nums = 0
		new_instance_nums = 0
		for task in tasks:
			task_nums += 1
			if task.interval is None:
				stop_task_nums += 1
				continue
			elif task.interval == 'hour':
				hour_task_nums += 1
				if start_hour:
					BaseTask(self.run_task, task, pt, False).attach2loop()
					new_instance_nums += 1
			elif task.interval == 'day':
				day_task_nums += 1
				if start_day:
					BaseTask(self.run_task, task, pt, False).attach2loop()
					new_instance_nums += 1
			else:
				continue
		self._pt = pt
		logger.info('DataService create instances, pt={pt}, task_nums={n1}, stop_task_nums={n2}, hour_task_nums={n3}, day_task_nums={n4}, new_instance_nums={n5}'.format(pt=[pt], n1=[task_nums], n2=[stop_task_nums], n3=[hour_task_nums],
																																										 n4=[day_task_nums], n5=[new_instance_nums]), caller=self)

	async def pipline_submit_loop(self):
		tasks = self.client['pipline'].list_collection_names()
		for task_name in tasks:
			BaseTask(self.submit_task, task_name).attach2loop()

	async def submit_task(self, task_name):
		task_data = await self.find_task(task_name)
		init_instances = await self.find_instance(task_name, cond={'status': 'init'})
		for init_instance in init_instances:
			BaseTask(self.check_instance_ready, init_instance).attach2loop()
		running_instance = await self.find_instance(task_name, cond={'status': 'running'})
		running_instance_nums = len(running_instance)
		ready_instance = await self.find_instance(task_name, cond={'status': 'ready'})
		for instance in ready_instance:
			if running_instance_nums >= task_data.max_parallel_num:
				return
			BaseTask(instance.submit_instance, self._rpc_client).attach2loop()
			running_instance_nums += 1

	async def check_instance_ready(self, instance):
		if instance.status != 'init':
			return
		for dep_task_name, dep_pt in instance.dep_instance:
			res = await self.find_instance(dep_task_name, dep_pt)
			if len(res) == 0 or res[0].status != 'success':
				return
		instance.status = 'ready'
		await self.update_instance(instance)


mongodb = MongoDBService()
if __name__ == "__main__":
	server = RpcServer(mongodb)
	server.start()
