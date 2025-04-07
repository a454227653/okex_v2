# 用于下载symbol的K线数据直到最近
#

symbol = 'BTC-USDT'
start_date = '2023-05-23 20:40:00'
batch = 10

from core.rpc.rpc_server import RpcClient
from core.utils.tools import *
from services.data_service.data_def import KLineData
from services.data_service.data_service import service as data_service
from services.market_service.plat.okex.okex_reset import OkexV5

start_ts = date2ts10(start_date)
okex = OkexV5(symbol=symbol)

client = RpcClient(data_service)

ts = start_ts
i = 0
while (ts < get_now_ts10()):
    res = okex.get_market_candles(bar='1m', after=ts + batch * 60, before=ts - 60, request_history=True)
    print('down load: from', ts102date(ts), 'to', ts102date(ts + batch * 60 - 60))
    ts += batch * 60
    for k in res:
        time.sleep(1.0)
        kline = KLineData(k)
        kline.dump(client)
        print(k)
