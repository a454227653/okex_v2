import os
import json5

from core.utils import logger
from core.utils import time
from core.task.BaseTask import BaseTask
from core.data.data_format import DataFormat


class BaseTable:
    _db_name = None
    _table_path = None
    _table_name = None
    _table_info = None
    _table_type = None
    _table_setting = {}
    _table_schema = {}
    _root = None
    _root_client = None
    _formater = None


    @staticmethod
    def creat_table(table_path, root):
        storage_map = {
            'default': DefaultTable,
            'time_series': TimeSeries,
            'error': Error,
            'log': Log
        }
        with open(table_path, "r", encoding="utf-8") as f:
            table_info = json5.load(f)
        table_type = table_info.get('table_type', 'default')
        table_class = storage_map[table_type]
        return table_class(table_path, table_info, root)

    def __init__(self, table_path, table_info, root):
        db_path, table_name = os.path.split(table_path)
        self._table_path = table_path
        self._db_name = db_path.split(os.sep)[-1]
        self._table_name = table_name.split('.')[0]
        self._table_info = table_info
        self._table_type = table_info.get('table_type', 'default')
        self._table_setting = table_info.get('table_setting', {})
        self._root = root
        self._root_client = root.root_client
        self._formater = DataFormat(self._table_schema)

        table_schema = self._table_info['table_schema']
        if isinstance(table_schema, str):
            with open(self._root.schema_path + table_schema + '.json5', "r", encoding="utf-8") as f:
                self._table_schema = json5.load(f)
        self._create_table()

    def _create_table(self):
        pass

    def _format_data(self, data: dict):
        return self._formater.forward(data)

    async def async_dumps(self, data:list):
        await self._root.dumps(self._db_name, self._table_name, data)
        
    async def async_dump(self, data:dict):
        await self._root.dump(self._db_name, self._table_name, self._format_data(data))

    async def async_delete(self, condition:dict):
        await self._root.delete(self._db_name, self._table_name, condition)

    async def async_update(self, condition:dict, data:dict):
        await self._root.update(self._db_name, self._table_name, condition, self._format_data(data))

    async def async_find(self, condition:dict):
        return await self._root.find(self._db_name, self._table_name, condition)
    
    async def async_find_one(self, condition):
        return await self._root.find_one(self._db_name, self._table_name, condition)

    def dumps(self, *args, **kwargs):
        BaseTask(self.async_dumps, *args, **kwargs).run_once()
        
    def dump(self, *args, **kwargs):
        BaseTask(self.async_dump, *args, **kwargs).run_once()

    def delete(self, *args, **kwargs):
        BaseTask(self.async_delete, *args, **kwargs).run_once()

    def update(self, *args, **kwargs):
        BaseTask(self.async_update, *args, **kwargs).run_once()

    def find(self, *args, **kwargs):
        BaseTask(self.async_find, *args, **kwargs).run_once()
        
    def find_one(self, *args, **kwargs):
        BaseTask(self.async_find_one, *args, **kwargs).run_once()


class DefaultTable(BaseTable):
    def _create_table(self):
        try:
            if self._table_name not in self._root_client[self._db_name].list_collection_names():
                table = self._root_client[self._db_name].create_collection(self._table_name)
                index_def = self._table_setting.get('index_def', [])
                unique = self._table_setting.get('unique', [])
                for index, unique in zip(index_def, unique):
                    table.create_index(index, unique=unique)
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            self._root.as_error(e)


class TimeSeries(BaseTable):
    def _create_table(self):
        try:
            db = self._root_client[self._db_name]
            if self._table_name not in db.list_collection_names():
                db.create_collection(
                    self._table_name,
                    timeseries=self._table_setting.get('timeseries'),
                    expireAfterSeconds=self._table_setting.get('expireAfterSeconds', 3600 * 24 * 7)
                )
        except Exception as e:
            logger.error("{s} error:".format(s=self.__class__.__name__), e, caller=self)
            self._root.as_error(e, self)


class Error(TimeSeries):
    async def async_dump(self, e, object=None):
        server_name = object.server_name if hasattr(object, 'server_name') else object.__class__.__name__
        server_id = object.server_id if hasattr(object, 'server_id') else 0
        trace_back = "".join(logger.traceback.format_tb(e.__traceback__))
        tmp = {
            'server_name': server_name
            , 'log_type': 'error'
            , 'server_id': server_id
            , 'ts': time.get_now()
            , 'info': e.args[0]
            , 'trace_back': trace_back
        }
        await self._root.dump(self._db_name, self._table_name, tmp)


class Log(TimeSeries):
    async def async_dump(self, info, object=None):
        server_name = object.server_name if hasattr(object, 'server_name') else object.__class__.__name__
        server_id = object.server_id if hasattr(object, 'server_id') else 0
        tmp = {
            'server_name': server_name
            , 'log_type': 'error'
            , 'server_id': server_id
            , 'ts': time.get_now()
            , 'info': info
            , 'trace_back': None
        }
        await self._root.dump(self._db_name, self._table_name, tmp)
