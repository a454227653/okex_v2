from recycle_bin.kernel import KBar
from recycle_bin.utils import *
start_date = '2020-01-01 10:00:00'



kbar = KBar(symbol='BTC-USDT', ts=date2ts(start_date), bar=1)
print(kbar.to_json())