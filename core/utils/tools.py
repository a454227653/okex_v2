"""
tools.py
created by Yan on 2023/4/18 20:27;
"""

import asyncio
import datetime
import decimal
import functools
import time
import uuid


def ts132date(timestamp):
	if timestamp is None:
		return None
	if isinstance(timestamp, str):
		timestamp = int(timestamp)
	dt = datetime.datetime.fromtimestamp(timestamp / 1000)
	return dt.strftime("%Y-%m-%d %H:%M:%S")


def ts102date(timestamp):
	if timestamp is None:
		return None
	if isinstance(timestamp, str):
		timestamp = int(timestamp)
	dt = datetime.datetime.fromtimestamp(timestamp)
	return dt.strftime("%Y-%m-%d %H:%M:%S")

def ts132pt(timestamp):
	if timestamp is None:
		return None
	if isinstance(timestamp, str):
		timestamp = int(timestamp)
	dt = datetime.datetime.fromtimestamp(timestamp / 1000)
	return int(dt.strftime("%Y%m%d%H"))

def ts102pt(timestamp):
	if timestamp is None:
		return None
	if isinstance(timestamp, str):
		timestamp = int(timestamp)
	dt = datetime.datetime.fromtimestamp(timestamp)
	return int(dt.strftime("%Y%m%d%H"))

def get_now_pt():
	return ts102pt(get_now_ts10())

interval_map= {'hour': 3600000, 'day': 86400000}
def get_prev_pt(pt, interval='hour', offset=1):
	ts = int(datetime.datetime.timestamp(datetime.datetime.strptime(pt, "%Y%m%d%H"))*1000)
	ts -= interval_map[interval] * offset
	return ts132pt(ts)

def date2ts10(date):
	if date is None:
		return None
	return int(datetime.datetime.timestamp(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')))


def date2ts13(date):
	if date is None:
		return None
	return int(datetime.datetime.timestamp(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')) * 1000)


def get_now_date():
	return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_now_time():
	return datetime.datetime.now()

def get_now_ts10():
	return int(datetime.datetime.now().timestamp())


def get_now_ts13():
	return int(datetime.datetime.now().timestamp() * 1000)


def get_cur_timestamp():
	"""Get current timestamp(second)."""
	ts = int(time.time())
	return ts


def get_cur_timestamp_ms():
	"""Get current timestamp(millisecond)."""
	ts = int(time.time() * 1000)
	return ts


def get_datetime_str(utc=None, fmt="%Y-%m-%d %H:%M:%S"):
	"""Get date time string, year + month + day + hour + minute + second.

	Args:
		utc: 8, is utc+8, -8, is utc-8, default is None
		fmt: Date format, default is `%Y-%m-%d %H:%M:%S`.

	Returns:
		str_dt: Date time string.
	"""
	today = datetime.datetime.today()
	if utc:
		today += datetime.timedelta(hours=utc)
	str_dt = today.strftime(fmt)
	return str_dt


def get_date_str(fmt="%Y%m%d", delta_days=0):
	"""Get date string, year + month + day.

	Args:
		fmt: Date format, default is `%Y%m%d`.
		delta_days: Delta days for currently, default is 0.

	Returns:
		str_d: Date string.
	"""
	day = datetime.datetime.today()
	if delta_days:
		day += datetime.timedelta(days=delta_days)
	str_d = day.strftime(fmt)
	return str_d


def ts_to_datetime_str(ts=None, fmt="%Y-%m-%d %H:%M:%S"):
	"""Convert timestamp to date time string.

	Args:
		ts: Timestamp, millisecond.
		fmt: Date time format, default is `%Y-%m-%d %H:%M:%S`.

	Returns:
		Date time string.
	"""
	if not ts:
		ts = get_cur_timestamp()
	dt = datetime.datetime.fromtimestamp(int(ts))
	return dt.strftime(fmt)


def datetime_str_to_ts(dt_str, fmt="%Y-%m-%d %H:%M:%S"):
	"""Convert date time string to timestamp.

	Args:
		dt_str: Date time string.
		fmt: Date time format, default is `%Y-%m-%d %H:%M:%S`.

	Returns:
		ts: Timestamp, millisecond.
	"""
	ts = int(time.mktime(datetime.datetime.strptime(dt_str, fmt).timetuple()))
	return ts


def get_utc_time():
	"""Get current UTC time."""
	utc_t = datetime.datetime.utcnow()
	return utc_t


def utctime_str_to_ts(utctime_str, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
	"""Convert UTC time string to timestamp(second).

	Args:
		utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
		fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

	Returns:
		timestamp: Timestamp(second).
	"""
	dt = datetime.datetime.strptime(utctime_str, fmt)
	timestamp = int(dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).timestamp())
	return timestamp


def utctime_str_to_ms(utctime_str, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
	"""Convert UTC time string to timestamp(millisecond).

	Args:
		utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
		fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

	Returns:
		timestamp: Timestamp(millisecond).
	"""
	dt = datetime.datetime.strptime(utctime_str, fmt)
	timestamp = int(dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).timestamp() * 1000)
	return timestamp


def get_utctime_str(fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
	"""Get current UTC time string.

	Args:
		fmt: UTC time format, e.g. `%Y-%m-%dT%H:%M:%S.%fZ`.

	Returns:
		utctime_str: UTC time string, e.g. `2019-03-04T09:14:27.806Z`.
	"""
	utctime = get_utc_time()
	utctime_str = utctime.strftime(fmt)
	return utctime_str


def get_uuid1():
	"""Generate a UUID based on the host ID and current time

	Returns:
		s: UUID1 string.
	"""
	uid1 = uuid.uuid1()
	s = str(uid1)
	return s


def get_uuid3(str_in):
	"""Generate a UUID using an MD5 hash of a namespace UUID and a name

	Args:
		str_in: Input string.

	Returns:
		s: UUID3 string.
	"""
	uid3 = uuid.uuid3(uuid.NAMESPACE_DNS, str_in)
	s = str(uid3)
	return s


def get_uuid4():
	"""Generate a random UUID.

	Returns:
		s: UUID5 string.
	"""
	uid4 = uuid.uuid4()
	s = str(uid4)
	return s

def get_uuid4_short():
	"""Generate a random UUID.

	Returns:
		s: UUID5 string.
	"""
	uid4 = uuid.uuid4()
	s = ''.join(str(uid4).split('-'))
	return s


def get_uuid5(str_in):
	"""Generate a UUID using a SHA-1 hash of a namespace UUID and a name

	Args:
		str_in: Input string.

	Returns:
		s: UUID5 string.
	"""
	uid5 = uuid.uuid5(uuid.NAMESPACE_DNS, str_in)
	s = str(uid5)
	return s


def float_to_str(f, p=20):
	"""Convert the given float to a string, without resorting to scientific notation.

	Args:
		f: Float params.
		p: Precision length.

	Returns:
		s: String format data.
	"""
	if type(f) == str:
		f = float(f)
	ctx = decimal.Context(p)
	d1 = ctx.create_decimal(repr(f))
	s = format(d1, 'f')
	return s

def str2float(s, default=None):
	if s is None or len(s)==0:
		return default
	else:
		return float(s)

def str2int(s, default=None):
	if s is None or len(s)==0:
		return default
	else:
		return int(s)

def cal_right_vol(p, vol):
	if p is None:
		return None
	else:
		return p * vol

def filter_none(data):
	if isinstance(data, map) or isinstance(data ,dict):
		res = {}
		for k in data:
			if data[k] is not None:
				res[k] = data[k]
		return res
	elif isinstance(data, list):
		res = []
		for v in data:
			if v is not None:
				res.append(v)
		return res
	else:
		return data


METHOD_LOCKERS = {}

def async_method_locker(name, wait=True, timeout=1):
	""" In order to share memory between any asynchronous coroutine methods, we should use locker to lock our method,
		so that we can avoid some un-prediction actions.

	Args:
		name: Locker name.
		wait: If waiting to be executed when the locker is locked? if True, waiting until to be executed, else return
			immediately (do not execute).
		timeout: Timeout time to be locked, default is 1s.

	NOTE:
		This decorator must to be used on `async method`.
	"""
	assert isinstance(name, str)

	def decorating_function(method):
		global METHOD_LOCKERS
		locker = METHOD_LOCKERS.get(name)
		if not locker:
			locker = asyncio.Lock()
			METHOD_LOCKERS[name] = locker

		@functools.wraps(method)
		async def wrapper(*args, **kwargs):
			if not wait and locker.locked():
				return
			try:
				await locker.acquire()
				return await asyncio.wait_for(method(*args, **kwargs), timeout)
			# return await method(*args, **kwargs)
			finally:
				locker.release()

		return wrapper

	return decorating_function