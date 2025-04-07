"""
test_subscribe.py
created by Yan on 2023/4/19 16:50;
"""

from core.task.BaseTask import *
import time

async def func1(a=1, b=2):
	await func2(a, b)
	await block()
	print('func1 test:', a+b)

async def block():
	time.sleep(4)

async def func2(a=1, b=2):
	print('func2 test:', a+b)

async def func3(a=1, b=2):
	print('func3 test:', a+b)

async def func4(a=1, b=2):
	print('func4 test:', a+b)

task = BaseTask(func1)
task.run_once()
# task1 = LoopTask(func1, loop_interval=2, a=1, b=2)
# # task1.attach2loop(5)
# task1.run_once()
#
#
# task2 = DelayTask(func2, delay=0, a=1, b=2)
# # task2.attach2loop()
# task2.run_once()

# task3 = LimitedTask(func3, loop_cnt=5, a=1, b=2)
# task4 = BaseTask(func4, a=1, b=2)
#
# task_center = TaskCenter(config)
#
# task_center.register(task1)
# task_center.register(task2)
# task_center.register(task3)
# task4.attach2loop()
# task_center.start()




