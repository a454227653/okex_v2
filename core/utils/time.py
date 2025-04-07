from datetime import datetime
from zoneinfo import ZoneInfo

# 时间数据落盘过程如下
# 1. 转换为上海时间（UTC+8）
# 2. 去掉时区信息
# 3. 数据落盘

def get_now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)

def get_now_string():
    return get_now().__str__()

def get_now_time():
    return get_now().time()

def get_now_date():
    return get_now().date()

def get_now_ts10():
    return int(get_now().timestamp())

def get_now_ts13():
    return int(get_now().timestamp()*1000)

def datetime_from_str(date_str: str):
    date_formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f'
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError("unsupport time string format：{}".format(date_str))


aa = datetime_from_str('2025-02-12 22:34:08')
print(aa)