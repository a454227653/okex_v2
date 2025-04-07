"""
Constant.py
created by Yan on 2023/4/29 17:48;
"""

bar_set = {
	'1m' : 1,
	'5m' : 5,
	'15m' : 15,
	'30m' : 30,
	'1h' : 60,
	'4h' : 240,
	'1d' : 1440,
	'7d' : 1440*7,
	'30d' : 1440*30,
	'360d' : 1440*30*12
}

bars = [x for x in bar_set.keys()]

print(bars)