# 用于下载symbol的K线数据直到最近
#

symbol='BTC-USDT'
start_date = '2023-05-11 21:00:00'
batch = 10

from recycle_bin.kernel import OkexV5
from core.utils.tools import *
from recycle_bin.kernel.data import KLineData
from recycle_bin.kernel import EventKlineUpdate
from core.task import *
start_ts = date2ts10(start_date)
okex = OkexV5(symbol=symbol)


ts = start_ts
i=0
while(ts<get_now_ts10()):
	res = okex.get_market_candles(bar='1m', after=ts+batch*60, before=ts-60, request_history=True)
	print('down load: from', ts102date(ts), 'to' ,ts102date(ts+batch*60-60))
	ts += batch*60
	for k in res:
		time.sleep(1.0)
		kline = KLineData(k)
		event = EventKlineUpdate()
		task = BaseTask(event.publish, kline)
		task.run_once()
		print(k)