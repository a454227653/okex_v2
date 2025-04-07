"""
test2.py
created by Yan on 2023/5/22 17:50;
"""

from core.task.BaseTask import *
import time


async def wait(x):
	n = 0
	print('start:', x)
	for i in range(1000000):
		n+=1
	print('end:', x)


async def sleep(x):
	print('start:', x)
	await asyncio.sleep(1)
	print('end:', x)

for i in range(5):
	BaseTask(wait, i).attach2loop()

asyncio.get_event_loop().run_forever()