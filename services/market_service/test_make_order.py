from okx.websocket.WsUtils import getServerTime

from core.rpc.rpc_server import RpcClient
from core.utils import tools
from services.data_service.data_def import OrderData

tmp = {
    'platform': 'OKEX'
    , 'req_id': tools.get_uuid4_short()
    , 'req_ts': int(getServerTime())
    , 'symbol': 'BTC-USDT'
    , 'mode': 'cash'
    , 'side': 'buy'
    , 'type': 'limit'
    , 'p': 27000
    , 'left_vol': 100 / 22000
    # , 'target_ccy': 'base_ccy'
    # , 'tp_trigger_p': 28000
    # , 'tp_trigger_type': 'last'
    # , 'tp_order_p': -1
}

# tmp2 = {
#     'platform': 'OKEX'
#     , 'req_id': tools.get_uuid4_short()
#     , 'req_ts': int(getServerTime())
#     , 'symbol': 'BTC-USDT'
#     , 'mode': 'cash'
#     , 'side': 'buy'
#     , 'type': 'limit'
#     , 'p': 27040
#     , 'left_vol': 100 / 22000
#     , 'target_ccy': 'base_ccy'
#     # , 'tp_trigger_p': 28000
#     # , 'tp_trigger_type': 'last'
#     # , 'tp_order_p': -1
# }

order1 = OrderData(tmp)
# order2 = OrderData(tmp2)
client = RpcClient('OKEX_FAKE_PRIVATE')

client.request({'m': 'make_orders', 'kwargs': {'orders': [order1], 'expTime': None}})
