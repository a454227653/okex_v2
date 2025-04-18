"""
base_data.py
created by Yan on 2025/1/11 21:59;
"""
import pymongo
from core.data.data_table import BaseTable
from core.config.base_config import *
from core.utils import logger
from core.utils.logger import debug


class DataBase:
    root_path = None
    root_name = None
    root_client = None
    db_config = None
    # 计算项目根目录（假设你的项目根目录和当前脚本有固定的层级关系）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
    data_root = os.path.join(project_root, "data_root/")
    schema_path = os.path.join(project_root, "data_root/schema/")
    
    # data_root = '../../data_root/'
    # schema_path = '../../data_root/schema/'

    def __init__(self, name):
        log_lv = json_config.get('DataBase.log_lv')
        logger.set_log_lv(log_lv)
        self.root_name = json_config.get('DataBase.main_db_name')
        self.root_path = self.data_root + name
        self.db_config = json_config.get('DataBase.{m}'.format(m=self.root_name))
        self.connect()
        self._set_table()

    def connect(self):
        server = self.db_config.get('server')
        username = self.db_config.get('username', None)
        password = self.db_config.get('password', None)
        if username and password:
            self.root_client = pymongo.MongoClient(server, username=username, password=password)
        else:
            self.root_client = pymongo.MongoClient(server)
        logger.info("db_config:", self.db_config, caller=self)

    def _set_table(self):
        dbs = os.listdir(self.root_path)
        for db in dbs:
            db_path = os.path.join(self.root_path, db)
            tables = os.listdir(db_path)
            for table in tables:
                table_path = os.path.join(db_path, table)
                if os.path.isfile(table_path):
                    file, ext = table.split('.')
                    if ext == 'json5':
                        self.__setattr__(file, BaseTable.creat_table(table_path, self))

    def get_table(self, table_name):
        return self.__getattribute__(table_name)

    # 增删改查
    # 增删改查
    async def dumps(self, db: str, table: str, data: list):
        try:
            self.root_client[db][table].insert_many(data)
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)
            
    async def dump(self, db: str, table: str, data: dict | list):
        try:
            self.root_client[db][table].insert_one(data)
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)

    async def delete(self, db_name: str, path: str, condition: dict = {}):
        try:
            self.root_client[db_name][path].delete_many(condition)
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)

    async def update(self, db: str, table: str, old: dict, new: dict):
        try:
            self.root_client[db][table].update_one(old, {"$set": new}, upsert=True)
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)

    async def find(self, db: str, table: str, condition: dict):
        try:
            res = self.root_client[db][table].find(condition)
            data = list(res)
            return data
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)
            
    async def find_one(self, db: str, table: str, condition):
        try:
            res = self.root_client[db][table].find_one(sort=[condition])
            return res
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            await self.error.async_dump(e, self)


MongoDBLocal = DataBase('MongoDBLocal')
print(MongoDBLocal)
