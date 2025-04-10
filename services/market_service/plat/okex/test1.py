import os
from pymongo import MongoClient
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = f"D:\jwl_v2_wry\data_root\MongoDBLocal\okex_market"



dbs = os.listdir(project_root)
for db in dbs:
    zscss, ext = db.split('.')
    print(zscss)
    # 连接 MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["okex_market"]
    collection = db[f'{zscss}']
    
    # 查询 TradeID 并排序
    trades = collection.find({}, {"tradeId": 1, "_id": 0}).sort("tradeId", 1)
    
    # 遍历 TradeID，检查连续性
    missing_trade_ids = []
    prev_trade_id = None
    count = 0
    file_name = f"{zscss}trade_ids.txt"
    for trade in trades:
        current_trade_id = int(trade["tradeId"])
        if prev_trade_id is not None and current_trade_id != prev_trade_id + 1:
            missing_trade_ids.extend(range(prev_trade_id + 1, current_trade_id))
            count += 1
            with open(file_name, "a") as file:  # 以追加模式 ('a') 打开文件
                file.write(
                    f"{count}Times TradeID*****{prev_trade_id}: {current_trade_id}----{current_trade_id - prev_trade_id}\n")  # 写入新的 TradeID
        prev_trade_id = current_trade_id
    
    # 输出缺失的 TradeID
    print("缺失的 TradeID:", missing_trade_ids)
    print("缺失的 TradeID:", len(missing_trade_ids))
    print(count)