"""
BaseTask.py
created by Yan on 2023/4/19 16:30;
"""

import asyncio
import inspect
from core.utils import tools

class BaseTask():
	"""
	仅执行一次
	关于异步任务触发的说明:
	1. attach2loop 方法将任务加入全局的 envent_loop, 延迟为协成调度级别, 适用于需要立即执行的任务
	2. register 方法将任务注册到任务中心, 延迟为任务中心心跳级别, 适用于需要延时, 定时或周期触发的任务
	3. run_once 和 run_forever 会启动单独的事件循环, 一般用作测试任务
	"""
	def __init__(self, func, *args, **kwargs):
		self._func = func
		self._args = args
		self._kwargs = kwargs
		self._task_id = tools.get_uuid1()
		self._loop = asyncio.get_event_loop()
		self._loop_cnt = 1

	def attach2loop(self, heartbeat_count=0):
		"""
		回调 func 加入 event_loop
		"""
		asyncio.get_event_loop().create_task(self._func(*self._args, **self._kwargs))
		self._loop_cnt -= 1

	def run_once(self):
		"""
		启动一次 event_loop
		"""
		res = self._loop.run_until_complete(self._func(*self._args, **self._kwargs))
		return res

	def run_forever(self):
		self._loop.run_forever()

	def get_task_id(self):
		return self._task_id

	def get_loop_cnt(self):
		return self._loop_cnt

	def register(self, task_center):
		task_center.register(self)


class LoopTask(BaseTask):
	"""
	每隔 loop_interval 次心跳执行一次
	"""
	def __init__(self, func, *args, **kwargs):
		self._loop_interval = kwargs.pop('loop_interval') if 'loop_interval' in kwargs else 1
		super().__init__(func, *args, **kwargs)

	def attach2loop(self, heartbeat_count=0):
		if heartbeat_count % self._loop_interval != 0:
			return
		self._loop.create_task(self._func(*self._args, **self._kwargs))


class DelayTask(BaseTask):
	"""
	延迟执行一次
	"""
	def __init__(self, func, *args, **kwargs):
		self._delay = kwargs.pop('delay') if 'delay' in kwargs else 0
		super().__init__(func, *args, **kwargs)

	def attach2loop(self, heartbeat_count=0):
		if not inspect.iscoroutinefunction(self._func):
			self._loop.call_later(self._delay, self._func, *self._args)
		else:
			def foo(f, *args, **kwargs):
				asyncio.get_event_loop().create_task(f(*args, **kwargs))
			self._loop.call_later(self._delay, foo, self._func, *self._args)
		self._loop_cnt -= 1


class LimitedTask(BaseTask):
	"""
	执行n次
	"""
	def __init__(self, func, *args, **kwargs):
		loop_cnt = kwargs.pop('loop_cnt') if 'loop_cnt' in kwargs else 1
		super().__init__(func, *args, **kwargs)
		self._loop_cnt = loop_cnt

class ParalleTask():
	def __init__(self, task_list):
		self._tasks = task_list

	async def run_once(self):
		res = await asyncio.gather(*self._tasks, return_exceptions=True)
		print(res)
		return res




