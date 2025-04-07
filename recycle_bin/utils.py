from datetime import datetime

def ts132date(timestamp):
	dt = datetime.fromtimestamp(timestamp/1000)
	return dt.strftime("%Y-%m-%d %H:%M:%S")

def ts102date(timestamp):
	dt = datetime.fromtimestamp(timestamp)
	return dt.strftime("%Y-%m-%d %H:%M:%S")

def date2ts(date):
	return int(datetime.timestamp(datetime.strptime(date, '%Y-%m-%d %H:%M:%S')))

def get_now_date():
	return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_now_ts():
	return int(datetime.now().timestamp())