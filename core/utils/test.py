from datetime import datetime
from zoneinfo import ZoneInfo
shanghai_time = datetime.now(ZoneInfo("Asia/Shanghai"))
print("上海时间:", shanghai_time)
naive_time = shanghai_time.replace(tzinfo=None)
print("天真时间:", naive_time)