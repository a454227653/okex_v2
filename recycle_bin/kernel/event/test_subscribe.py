"""
test_subscribe.py
created by Yan on 2023/5/5 20:53;
"""

from core.task import *
from recycle_bin.kernel import EventKlineUpdate, EventMsg


event_msg = EventMsg(queue='msg_test', routing_key='*.*')
event_msg.subscribe()

event_kline_update = EventKlineUpdate()
event_kline_update.subscribe()

task_center.start()




# event_center.