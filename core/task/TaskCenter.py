"""
TaskCenter.py
created by Yan on 2023/4/18 20:21;
"""
import asyncio
from core.utils import logger
from core.config.base_config import BaseConfig, json_config
from core.task.BaseTask import BaseTask


class TaskCenter(object):
    """
    同步或异步任务调度中心,
    调度单位为 BaseTask 对象,
    每轮心跳周期, 异步执行注册列表中的所有 BaseTask 对象, 并将超出生命周期的 task 对象移出调度队列
    """
    def __init__(self, config : BaseConfig = json_config):
        self._count = 0  # 心跳计数
        self._interval = config.get('TaskCenter.heartbeat_interval', 0.5)  # 心跳间隔, 单位秒
        self._print_interval = config.get('TaskCenter.print_interval', 120)  # 日志打印心跳间隔
        self._tasks = {}  # 任务队列, {task_id : BaseTask}

    def main_loop(self):
        """
        任务中心主循环, 每次心跳向全局 event_loop 绑定所有待执行任务
        """
        self._count += 1

        if self._print_interval > 0:
            if self._count % self._print_interval == 0:
                logger.info("heartbeat count:", self._count, ", task nums:", len(self._tasks), caller=self)

        # 拉起下一轮循环
        asyncio.get_event_loop().call_later(self._interval, self.main_loop)

        # 提交异步任务
        completed_task_temp = []
        for task_id, task in self._tasks.items():
            if task.get_loop_cnt() == 0:
                completed_task_temp.append(task_id)
                continue
            task.attach2loop(self._count)

        # 删除已执行完毕的 task 对象
        for task_id in completed_task_temp:
            self.unregister(task_id)

    def register(self, task : BaseTask):
        task_id = task.get_task_id()
        self._tasks[task_id] = task
        return task_id

    def unregister(self, task_id):
        if task_id in self._tasks:
            self._tasks.pop(task_id)

    def count(self):
        return self._count

    def start(self):
        """
        启动任务中心
        """
        loop = asyncio.get_event_loop()
        loop.call_later(0.5, self.main_loop)
        loop.run_forever()

task_center = TaskCenter(json_config)