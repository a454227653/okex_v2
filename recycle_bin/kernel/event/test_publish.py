"""
test_publish.py
created by Yan on 2023/5/9 21:50;
"""


from recycle_bin.kernel import event_center
from core.task import *
from recycle_bin.kernel import EventMsg


event_msg = EventMsg(queue='msg_test', routing_key='msg.1')
# event_msg.publish(event_center, 'hello')
task = BaseTask(event_msg.publish, event_center, 'hello')
task.attach2loop()
task.run_once()