"""
test_subscribe.py
created by Yan on 2023/4/25 20:50;
"""

from core.config import config
from recycle_bin.kernel.database import MongoDBClient

db = MongoDBClient(config, db_name='test')
# db.dump('usdt/kbar',{'1':1, '2':2})
db.dump('usdt/ks',{'1':1, '2':2})

