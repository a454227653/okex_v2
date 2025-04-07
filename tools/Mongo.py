import pymongo

mongo = pymongo.MongoClient('mongodb://localhost:27018/')

db = mongo.get_database('KBar')
collec = db.get_collection('BTC-USDT')

print(collec.index_information())