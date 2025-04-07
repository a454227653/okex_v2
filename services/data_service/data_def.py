"""
data_def.py
created by Yan on 2023/4/25 15:28;
"""

from core.utils import tools
from services.data_service.base_data import BaseData


class KLineData(BaseData):
	schema = ['platform', 'symbol', 'ts', 'bar', 'date', 'start_p', 'max_p', 'min_p', 'end_p', 'left_vol', 'right_vol', 'confirm', 'pt']
	index_def = [[('pt', -1), ('bar', -1), ('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('platform')+'/'+data.get('symbol')
		self.platform = data.get('platform')
		self.symbol = data.get('symbol')
		super().__init__(data, db_name='kline', path = path)


class TradeData(BaseData):
	schema = ['platform', 'symbol', 'ts', 'date', 'trade_id', 'p', 'left_vol', 'right_vol', 'side', 'pt']
	index_def = [[('pt', -1)], [('trade_id', -1)]]
	unique = [False, True]

	def __init__(self, data):
		path = data.get('platform') + '/' + data.get('symbol')
		super().__init__(data, db_name='trade', path=path)


class OrderData(BaseData):
	schema = [
		'platform'
		, 'req_id'  #clOrdId, 随机uuuid， 用于挂单
		, 'uid'
		, 'order_id'  # ordId ,订单id, 交易所提供的订单 id
		, 'algo_tag'  # tag, 用作策略tag
		, 't_id'  # 最新成交id

		, 'req_ts'  # id, 发起订单请求时的13位时间戳
		, 'req_date'
		, 'order_ts'  # 服务端下单时间
		, 'order_date'
		, 'update_ts'  # 订单更新时间
		, 'update_date'
		, 't_ts'  # 最新成交时间
		, 't_date'  # 最新成交日期

		, 'symbol'  # instId
		, 'symbol_type'  # instType
		, 'mode'  # 交易模式， 保证金模式: isolated 逐仓，cross 全仓; 非保证金模式： cash 现金
		, 'ccy'  # 保证金币种，仅适用于单币种保证金账户下的全仓杠杆订单
		, 'side'  # side, 订单方向
		, 'pos_side'  # 持仓方向
		, 'type' # 订单类型， market：市价单，limit：限价单，post_only：只做maker单，fok：全部成交或立即取消，ioc：立即成交并取消剩余, optimal_limit_ioc：市价委托立即成交并取消剩余（仅适用交割、永续）
		, 'state'  # 委托状态,canceled:撤单成功,live:等待成交,partially_filled:部分成交,filled:完全成交
		, 'lv'  # 杠杆倍数 [0.01, 125]

		, 'p'  # 委托价格
		, 'left_vol'  # 委托数量
		, 'right_vol'  # 委托右侧计价
		, 't_p'  # 最新成交价
		, 't_left_vol'
		, 't_right_vol'
		, 't_fee'  # 最新手续费
		, 't_type'  # maker or taker
		, 'a_p'  # 累积成交均价
		, 'a_left_vol'  # 累积成交量
		, 'a_right_vol'
		, 'a_fee'  # 累计手续费

		, 'tp_trigger_p' # 止盈触发价
		, 'tp_trigger_type' #止盈触发类型 last：最新价格，index：指数价格，mark：标记价格
		, 'tp_order_p' #止盈下单价格， 止盈委托价格为-1时，执行市价止盈
		, 'sl_trigger_p'
		, 'sl_trigger_type'
		, 'sl_order_p'
		, 'reduce_only'  #	是否只减仓，true 或 false，默认false,仅适用于币币杠杆，以及买卖模式下的交割/永续, 仅适用于单币种保证金模式和跨币种保证金模式
		, 'target_ccy'  #币币市价单委托数量sz的单位,base_ccy: 交易货币 ；quote_ccy：计价货币,仅适用于币币市价订单,默认买单为quote_ccy，卖单为base_ccy
		, 'amend'  #是否禁止币币市价改单，true 或 false，默认false, 为true时，余额不足时，系统不会改单，下单会失败，仅适用于币币市价单
		, 'quick_mgn_type'  #一键借币类型，仅适用于杠杆逐仓的一键借币模式：manual：手动，auto_borrow： 自动借币，auto_repay： 自动还币,默认是manual：手动
		, 'pt'
	]

	index_def = [[('pt', -1), ('algo_tag', -1), ('update_ts', -1), ('order_id', -1)]]
	unique = [True]

	def __init__(self, data):
		path = '/'.join([data.get('platform'), data.get('symbol')])
		super().__init__(data, db_name='order', path=path)

	def check_value(self):
		assert self.check_none([self.symbol, self.mode, self.side, self.type, self.left_vol])

	def to_order_json(self):
		tmp = {
			'clOrdId' : self.req_id
			, 'instId': self.symbol
			, 'tdMode': self.mode
			, 'ccy' : self.ccy
			, 'tag' : self.algo_tag
			, 'side' : self.side
			, 'posSide' : self.pos_side
			, 'ordType' : self.type
			, 'sz' : self.left_vol
			, 'px' : self.p
			, 'reduceOnly' : self.reduce_only
			, 'tgtCcy' : self.target_ccy
			, 'banAmend' : self.amend
			, 'quickMgnType' : self.quick_mgn_type
			, 'tpTriggerPx' :self.tp_trigger_p
			, 'tpTriggerPxType' : self.tp_trigger_type
			, 'tpOrdPx' : self.tp_order_p
			, 'slTriggerPx' : self.sl_trigger_p
			, 'slTriggerPxType' : self.sl_trigger_type
			, 'slOrdPx' : self.sl_order_p
		}
		return tools.filter_none(tmp)


class AccountData(BaseData):
	schema = [
		'platform'
		, 'ccy'
		, 'uid'
		, 'ts'   #更新时间
		, 'date'
		, 'eq'   #总权益
		, 'feature_eq' #未平仓权益
		, 'vol'  #总量
		, 'free_vol' #可用总量
		, 'frozen_vol' #冻结总量
		, 'mgn_ratio' #保证金率
		, 'pt'
	]
	index_def = [[('pt', -1), ('ccy', -1), ('uid', -1), ('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('platform')
		super().__init__(data, db_name='account', path=path)


class MarkPriceData(BaseData):
	schema = [
		'platform'
		, 'symbol'
		, 'ts'
		, 'date'
		, 'mp'
		, 'pt'
	]
	index_def = [[('pt', -1), ('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = '/'.join([data.get('platform'), data.get('symbol')])
		super().__init__(data, db_name='price', path=path)

class PlatformStatusData(BaseData):
	schema = [
		'platform'
		, 'title' #标题
		, 'state' #系统的状态，scheduled:等待中 ; ongoing:进行中 ; pre_open:预开放；completed:已完成 canceled: 已取消当维护时间过长，会存在预开放时间，一般持续10分钟左右。
		, 'ts'   #推送时间
		, 'date'
		, 'begin_ts'  #开始时间
		, 'end_ts'    #结束时间
		, 'start_date'
		, 'end_date'
		, 'pre_ts'    #预开放开始的时间，开放撤单、Post Only 下单和资金转入功能的时间
		, 'pre_date'
		, 'ref'   # 外部链接
		, 'serviceType' # 服务类型， 0：WebSocket ; 5：交易服务；6：大宗交易；7：策略交易；8：交易服务 (按账户分批次)；9：交易服务 (按产品分批次)；99：其他（如：停止部分产品交易）
		, 'maintType'  #维护类型。1：计划维护；2：临时维护；3：系统故障
		, 'env'  #环境。1：实盘，2：模拟盘
		, 'pt'
	]

	index_def = [[('pt', -1), ('ts', -1)]]
	unique = [True]

	def __init__(self, data):
		path = data.get('platform')
		super().__init__(data, db_name='inform', path=path)


