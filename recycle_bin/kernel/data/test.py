"""
test_subscribe.py
created by Yan on 2023/4/26 16:44;
"""

data = {'platform': 'OKEX', 'symbol': 'BTC-USDT', 'ts': 1577813940, 'bar': 1, 'date': '2020-01-01 01:39:00', 'start_p': 129.25, 'max_p': 129.29, 'min_p': 129.0, 'end_p': 129.29, 'left_vol': 2067.565196, 'right_vol': 267315.504191, 'confirm': 1}
# kk = KLineData(data)
#
# kk.dump()

# mongo_client.dump('kline', 'OKEX/BTC-USDT', data)
mongo_client.client['kline'].drop_collection('OKEX/BTC-USDT')
# mongo_client.del_all('kline', 'OKEX/BTC-USDT')
# res = mongo_client.client['kline']['OKEX/BTC-USDT'].list_indexes()
#
# for ind in res:
# 	print(ind)
