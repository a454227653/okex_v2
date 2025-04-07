import pymongo

class Logger():

    def __init__(self, client='mongodb://localhost:27017/', database_name='KBar', collection_name='BTC-USDT'):
        self.client = client
        self.mongo = pymongo.MongoClient(client)
        self.database_name = database_name
        self.database = self.mongo.get_database(self.database_name)
        self.collection_name = collection_name
        self.__getattribute__('init_' + database_name)()
        self.collection = self.database.get_collection(self.collection_name)

    def init_KBar(self):
        if self.collection_name not in self.database.list_collection_names():
            self.database.create_collection(self.collection_name)
            self.database.get_collection(self.collection_name).create_index([('ts', -1), ('date', -1), ('bar', 1)], unique=True)

    def init_Factor(self):
        if self.collection_name not in self.database.list_collection_names():
            self.database.create_collection(self.collection_name)
            self.database.get_collection(self.collection_name).create_index([('ts', -1), ('date', -1)], unique=True)


