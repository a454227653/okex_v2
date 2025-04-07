"""
okex_ws.py
created by Yan on 2023/5/18 15:34;
"""

import asyncio, base64, hmac, json, os, traceback
from okx.websocket.WsUtils import getServerTime
from core.config.base_config import BaseConfig, json_config
from core.rpc.rpc_server import RpcClient, rpc
from core.task import TaskCenter, task_center, BaseTask, LoopTask
from core.utils import logger
from services.data_service.data_def import *
from services.data_service.data_service import LogData
from services.constant import *
from services.market_service.plat.web_sockets import WebSocket


class OkexWs(WebSocket):
    _platform_tag = 'OKEX_PUBLIC_TEST'

    def __init__(self, platform_tag=None, server_name=None, is_cheif_worker = True, config: BaseConfig = json_config, task_center: TaskCenter = task_center):
        self._platform_tag = platform_tag or self._platform_tag
        self.server_name = server_name or self._platform_tag
        self._rpc_client = RpcClient(self.server_name, self.server_id, hello_server=False)
        self._platform_config = config.get('MarketServer.Platforms.{p}'.format(p=self._platform_tag))
        self._platform = self._platform_config.get('platform')
        self._host = self._platform_config.get('host')
        self._access_key = self._platform_config.get('access_key')
        self._secret_key = self._platform_config.get('secret_key')
        self._passphrase = self._platform_config.get('pass_word')
        self._is_cheif_worker = is_cheif_worker
        self._channel_map = {}
        self._tag = self._platform_config.get('tag')
        self._platform_rt = 0
        self._account_tmp = {}  # 持仓表 e.g. {{uid}.{ccy}: account_detail}
        self._order_tmp = {}  # 挂单表 e.g. {req_id : order_detail}
        self._tmp_file = './tmp/{p}.json'.format(p=self._platform_tag)
        if os.path.exists(self._tmp_file):
            with open(self._tmp_file, 'r') as f:
                self._order_tmp = json.load(f)
        super(OkexWs, self).__init__(host=self._host, config=json_config, task_center=task_center)
        LoopTask(self._log_report, loop_interval=60).register(task_center)

    async def _log_report(self, type='monitor', msg=None):
        # 监控/报错日志
        ts = tools.get_now_ts13()
        if type == 'monitor':
            data = {'data_server_rt': int(self._rpc_client.rt), 'platform_rt': int(self._platform_rt)}
        elif type == 'error':
            data = {'e': msg.args[0], 'trace_back': "\n"+"".join(traceback.format_tb(msg.__traceback__))}
        else:
            data = msg
        tmp = {
            'name': self.server_name
            , 'id': self.server_id
            , 'tag': type
            , 'ts': ts
            , 'date': tools.ts132date(ts)
            , 'data': data
            , 'pt': tools.ts132pt(ts)
        }
        base_data = LogData(tmp)
        await self._publish_message(base_data, symbol=self.server_name, msg_type=type, detail=self.server_id)
        logger.info('OkexWs report log: {d}'.format(d=tmp), caller=self)
        await base_data.dump_async(self._rpc_client)

    async def _on_connected_callback(self):
        """
        连接成功后执行登录okex回调
        """
        ts = int(getServerTime()) / 1000  # 目前用服务端 13 位时间戳签名
        message = str(ts) + "GET" + "/users/self/verify"
        mac = hmac.new(bytes(self._secret_key, encoding="utf8"), bytes(message, encoding="utf8"), digestmod="sha256")
        d = mac.digest()
        signature = base64.b64encode(d).decode()
        data = {
            "op": "login",
            "args": [{"apiKey": self._access_key, "passphrase": self._passphrase, "timestamp": ts, "sign": signature}]
        }
        await self.send(data)

    async def _on_receive_data_callback(self, data):
        # logger.debug('OkexWs receive message: ', data, caller = self)
        if 'event' in data:  # 登录, 订阅, 取消订阅, pong 消息
            event = data.get('event')
            if event == 'login':  # 登录成功
                logger.info('OkexWs connection authorized successfully.', caller=self)
                await self._update_subscribe()
            elif event == 'subscribe':  # 订阅成功
                logger.info('OkexWs receive subscribe: ', data, caller=self)
                channel = data.get('arg')
                self._channel_map[self._get_channle_id(channel)] = channel
            elif event == 'unsubscribe':  # 取消订阅成功
                logger.info('OkexWs receive unsubscribe: ', data, caller=self)
                channel = data.get('arg')
                self._channel_map.pop(self._get_channle_id(channel))
            elif event == 'error':  # 远端报错
                msg = 'OkexWs receive error: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(msg, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
            else:
                msg = 'unhandled event: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
        elif 'op' in data and 'data' in data:  # 交易相关
            op = data.get('op')
            if op in ['order', 'batch-orders']:  # 下单成功
                BaseTask(self._on_make_order_callback, data).attach2loop()
            elif op == ['cancel-order', 'batch-cancel-orders']:  # 退单成功
                BaseTask(self._on_cancel_order_callback, data).attach2loop()
            else:
                msg = 'unhandled op type: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()
        elif 'arg' in data and 'data' in data:  # 行情数据
            data_type = data.get('arg').get('channel')
            if data_type[0:6] == 'candle' or data_type[0:17] == 'mark-price-candle':  # k线推送
                BaseTask(self._on_candle_callback, data).attach2loop()
            elif data_type == 'trades':  # 成交推送
                BaseTask(self._on_trades_callback, data).attach2loop()
            elif data_type == 'mark-price': # 标记价格更新
                BaseTask(self._on_mark_price_callback, data).attach2loop()
            elif data_type == 'status':  # 交易所状态推送
                BaseTask(self._on_status_callback, data).attach2loop()
            elif data_type == 'orders':  # 下单成交通知
                BaseTask(self._on_order_update_callback, data).attach2loop()
            elif data_type == 'account':  # 账户资产更新
                BaseTask(self._on_account_update_callback, data).attach2loop()
            else:
                msg = 'unhandled market data: {d}'.format(d=data)
                e = IOError(msg)
                logger.error(e, caller=self)
                BaseTask(self._log_report, type='error', msg=e).attach2loop()

    async def _on_candle_callback(self, data):
        arg = data.get('arg')
        data_type = arg.get('channel')
        data = data.get('data')[0]
        confirm = int(data[-1])
        if confirm != 1:
            return
        symbol = arg.get('instId')
        if data_type[0:17] == 'mark-price-candle':
            symbol = symbol + '-MP'
            left_vol = None
            right_vol = None
        else:
            left_vol = float(data[5]) / (100 if symbol[-4:]=='SWAP' else 1) #SWAP 交易单位为张, okex 每张 0.01 ccy
            right_vol = float(data[7])
        bar = arg.get('channel')[-2:]
        confirm = bar_map.get(bar)
        tmp = {
            'platform': self._platform
            , 'symbol': symbol
            , 'ts': int(data[0])
            , 'bar': bar
            , 'date': tools.ts132date(int(data[0]))
            , 'start_p': float(data[1])
            , 'max_p': float(data[2])
            , 'min_p': float(data[3])
            , 'end_p': float(data[4])
            , 'left_vol': left_vol
            , 'right_vol': right_vol
            , 'confirm': confirm
            , 'pt': tools.ts132pt(int(data[0]))
        }
        base_data = KLineData(tmp)
        await self._publish_message(data=base_data, symbol=base_data.symbol, msg_type='kline', detail=bar)
        logger.debug('OkexWs dump KLineData: ', tmp, caller=self)
        await base_data.dump_async(self._rpc_client)

    async def _on_trades_callback(self, data):
        arg = data.get('arg')
        data = data.get('data')[0]
        symbol = arg.get('instId')
        left_vol = tools.str2float(data.get('sz')) / (100 if symbol[-4:]=='SWAP' else 1) #SWAP 交易单位为张, okex 每张 0.01 ccy
        right_vol = left_vol * tools.str2float(data.get('sz'))
        ts = int(data.get('ts'))
        tmp = {
            'platform': self._platform
            , 'symbol': arg.get('instId')
            , 'ts': ts
            , 'date': tools.ts132date(ts)
            , 'trade_id': int(data.get('tradeId'))
            , 'p': tools.str2float(data.get('px'))
            , 'left_vol': left_vol
            , 'right_vol': right_vol
            , 'side': data.get('side')
            , 'pt': tools.ts132pt(ts)
        }
        base_data = TradeData(tmp)
        await self._publish_message(data=base_data, symbol=base_data.symbol, msg_type='trade', detail='update')
        logger.debug('OkexWs dump TradeData: ', tmp, caller=self)
        await base_data.dump_async(self._rpc_client)

    async def _on_mark_price_callback(self, data):
        arg = data.get('arg')
        data = data.get('data')[0]
        symbol = arg.get('instId')+'-MP'
        ts = int(data.get('ts'))
        tmp = {
            'platform': self._platform
            , 'symbol': symbol
            , 'ts': ts
            , 'date': tools.ts132date(ts)
            , 'mp': data.get('markPx')
            , 'pt': tools.ts132pt(ts)
        }
        base_data = MarkPriceData(tmp)
        await self._publish_message(data=base_data, symbol=symbol, msg_type='price', detail='update')

    async def _on_status_callback(self, data):
        data = data.get('data')[0]
        pre_ts = tools.str2int(data.get('preOpenBegin'))
        ts = int(data.get('ts'))
        tmp = {
            'platform': self._platform
            , 'title': data.get('title')
            , 'state': data.get('state')
            , 'ts': ts
            , 'date': tools.ts132date(ts)
            , 'begin_ts' : int(data.get('begin'))
            , 'end_ts' : int(data.get('end'))
            , 'begin_date': tools.ts132date(int(data.get('begin')))
            , 'end_date': tools.ts132date(int(data.get('end')))
            , 'pre_ts': pre_ts
            , 'pre_date': tools.ts132date(pre_ts)
            , 'ref' : data.get('href')
            , 'serviceType': int(data.get('serviceType'))
            , 'maintType': int(data.get('maintType'))
            , 'env': int(data.get('env'))
            , 'pt': tools.ts132pt(ts)
        }
        base_data = PlatformStatusData(tmp)
        await self._publish_message(data=base_data, symbol='default', msg_type='status', detail='update')
        logger.info('OkexWs receive new status = {s}'.format(s=tmp), caller=self)
        await base_data.update_async(self._rpc_client)

    async def _on_order_update_callback(self, msg):
        # 下单成交更新
        logger.debug('OkexWs reveive OrderData: {m}'.format(m=msg))
        arg = msg.get('arg')
        data_list = msg.get('data')
        for data in data_list:
            req_id = data.get('clOrdId')
            t_ts = tools.str2int(data.get('fillTime'))
            t_p = tools.str2float(data.get('fillPx'))
            t_left_vol = tools.str2float(data.get('fillSz'))
            t_right_vol = tools.cal_right_vol(p=t_p, vol=t_left_vol)
            a_p = tools.str2float(data.get('avgPx'))
            a_left_vol = tools.str2float(data.get('accFillSz'))
            a_right_vol = tools.cal_right_vol(p=a_p, vol=a_left_vol)
            p = tools.str2float(data.get('px'))
            left_vol = tools.str2float(data.get('sz'))
            right_vol = tools.cal_right_vol(p=p, vol=left_vol)
            order_id = tools.str2int(data.get('ordId'))
            order_ts = tools.str2int(data.get('cTime'))
            order_date = tools.ts132date(order_ts)
            update_ts = tools.str2int(data.get('uTime'))
            update_date = tools.ts132date(update_ts)
            state = data.get('state')
            tmp = {
                'platform': self._platform
                , 'req_id' : req_id
                , 'uid': tools.str2int(arg.get('uid'))
                , 'symbol': arg.get('instId')
                , 'symbol_type': data.get('instType')
                , 't_id': tools.str2int(data.get('tradeId'))
                , 't_ts': t_ts
                , 't_date': tools.ts132date(t_ts)
                , 't_p': t_p
                , 't_left_vol': t_left_vol
                , 't_right_vol': t_right_vol
                , 't_fee': tools.str2float(data.get('fillFee'))
                , 't_type': data.get('execType')
                , 'a_p': a_p
                , 'a_left_vol': a_left_vol
                , 'a_right_vol': a_right_vol
                , 'a_fee': tools.str2float(data.get('fee'))

                , 'mode': data.get('tdMode')
                , 'ccy': data.get('ccy')
                , 'order_id': order_id
                , 'algo_tag': data.get('tag')
                , 'side': data.get('side')
                , 'pos_side': data.get('posSide')
                , 'type': data.get('ordType')
                , 'p': p
                , 'left_vol': left_vol
                , 'right_vol': right_vol
                , 'state': state
                , 'order_ts': order_ts
                , 'order_date': order_date
                , 'update_ts': update_ts
                , 'update_date': update_date
                , 'lv': tools.str2float(data.get('lever'))
                , 'tp_trigger_p': tools.str2float(data.get('tpTriggerPx'))
                , 'tp_trigger_type': tools.str2float(data.get('tpTriggerPxType'))
                , 'tp_order_p': tools.str2float(data.get('tpOrdPx'))
                , 'sl_trigger_p': tools.str2float(data.get('slTriggerPx'))
                , 'sl_trigger_type': tools.str2float(data.get('slTriggerPxType'))
                , 'sl_order_p': tools.str2float(data.get('slOrdPx'))
                , 'reduce_only': data.get('reduceOnly') == 'true'
                , 'target_ccy': data.get('tgtCcy')
                , 'amend': data.get('amendSource')
                , 'quick_mgn_type': data.get('quickMgnType')
                , 'pt': tools.ts132pt(update_ts)
            }
            if req_id is not None:
                if req_id in self._order_tmp:
                    # OkexWs 实例自身的下单
                    self._order_tmp[req_id].update(tmp)
                    await self._on_order_tmp_update(req_id)
                    tmp = self._order_tmp[req_id]
                    if state in ['filled', 'canceled']:
                        self._order_tmp.pop(req_id)
                    with open(self._tmp_file, 'w') as f:
                        json.dump(self._order_tmp, f, indent=4)
                else:
                    # 有 req_id 但不在订单表里, 可能是其它 OkexWs 下的单, 不重复落盘
                    return
            else:
                # 没有 req_id, 非 OkexWs 下单, 应当由唯一一个指定的 OkexWs 落盘数据
                if not self._is_cheif_worker:
                    return
                tmp['req_id'] = None
                tmp['req_ts'] = None
                tmp['req_date'] = None
            await OrderData(tmp).dump_async(self._rpc_client)
            logger.debug('OkexWs dump OrderData: ', tmp, caller=self)

    async def _on_make_order_callback(self, msg):
        logger.debug('OkexWs reveive make_order: {m}'.format(m=msg))
        # 下单成功, 通过websocket接口下单才会触发回调, 其余下单方式没有req_id
        code = msg.get('code')
        req_id = msg.get('id')
        if req_id not in self._order_tmp:
            return
        if code != '0':
            self._order_tmp.pop(req_id)
            raise Exception('OkexWs make_order failed: {m}'.format(m=msg))
        else:
            logger.debug('OkexWs make order request success: {r}'.format(r=req_id))

    async def _on_order_tmp_update(self, req_id):
        order = OrderData(self._order_tmp[req_id])
        msg_type = 'order'
        symbol = order.symbol
        if order.order_ts == order.update_ts and order.state =='live':
            detail = 'open'
        elif order.state == 'live':
            detail = 'update'
        else:
            detail = order.state
        await self._publish_message(data=order, symbol=symbol, msg_type=msg_type, detail=detail)

    async def _publish_message(self, data:BaseData, symbol, msg_type, detail):
        channel = '{p}.{s}.{m}.{d}'.format(p=self._platform, s=symbol, m=msg_type, d=detail)
        await self._rpc_client.request_async(
            request={'kwargs': {'data': data, 'platform': self._platform, 'symbol': symbol, 'msg_type': msg_type, 'detail': detail}}
            , server_name=STRATEGY
            , server_channel=channel
            , method = 'forward'
            , no_reply = True
        )
        logger.debug('OkexWs publish message: symbol={s}, msg_type={m}, detail={d}, data={data}'.format(s=[symbol], m=[msg_type], d=[detail], data=data.to_json()), caller=self)


    async def _on_account_update_callback(self, data):
        # 账户资产更新
        ccy = data.get('arg').get('ccy')
        uid = data.get('arg').get('uid')
        tmp = {'platform': self._platform, 'ccy': ccy, 'uid': tools.str2int(uid)}
        tasks = []
        for detail in data.get('data')[0].get('details'):
            ts = tools.str2int(detail.get('uTime'))
            detail_tmp = {
                'ts': ts
                , 'date': tools.ts132date(detail.get('uTime'))
                , 'eq': tools.str2float(detail.get('eq'))
                , 'feature_eq': tools.str2float(detail.get('upl'))
                , 'vol': tools.str2float(detail.get('cashBal'))
                , 'free_vol': tools.str2float(detail.get('availBal'))
                , 'frozen_vol': tools.str2float(detail.get('frozenBal'))
                , 'mgn_ratio': tools.str2float(detail.get('mgnRatio'))
                , 'pt': tools.ts132pt(ts)
            }
            index = '{u}.{c}'.format(u=uid, c=ccy)
            detail_tmp.update(tmp)
            if index in self._account_tmp and self._account_tmp.get(index).get('ts') == ts:
                return
            logger.debug('{p} account update: {d}'.format(p=self._platform, d=detail_tmp), caller=self)
            self._account_tmp[index] = detail_tmp
            base_data = AccountData(detail_tmp)
            BaseTask(self._publish_message, base_data, 'default', 'account', 'update').attach2loop()
            tasks.append(base_data.update_async(self._rpc_client))
        await asyncio.gather(*tasks)

    async def _on_cancel_order_callback(self, data):
        pass

    async def _get_channels(self):
        # todo. 获取配置中心的 channles
        return self._platform_config.get("channels")

    def _get_channle_id(self, channle):
        tmp = [v for v in list(channle.values())]
        tmp.sort()
        return ".".join(tmp)

    async def _subscribe(self, channles):
        data = {
            "op": "subscribe",
            "args": channles
        }
        await self.send(data)

    async def _ubsubscribe(self, channles):
        data = {
            "op": "unsubscribe",
            "args": channles
        }
        await self.send(data)

    async def _update_subscribe(self):
        channels = await self._get_channels()
        subscribe = []
        unsubscribe = []

        new_channel_map = {self._get_channle_id(c): c for c in channels}
        for channel_id in new_channel_map:
            if channel_id not in self._channel_map:
                subscribe.append(new_channel_map[channel_id])

        for channel_id in self._channel_map:
            if channel_id not in new_channel_map:
                unsubscribe.append(self._channel_map[channel_id])

        if len(subscribe) > 0:
            await self._subscribe(subscribe)
        if len(unsubscribe) > 0:
            await self._ubsubscribe(unsubscribe)

    @rpc
    async def make_order(self, order: OrderData, expTime=None):
        req_ts = order.req_ts
        req_id = order.req_id
        self._order_tmp[req_id] = {'req_ts': req_ts, 'req_date': tools.ts132date(req_ts)}
        ordr_data = order.to_order_json()
        data = {
            "id": req_id,
            "op": "order",
            "args": [ordr_data],
        }
        if expTime is not None:
            data['expTime'] = expTime
        BaseTask(self.send, data).attach2loop()

    @rpc
    async def make_orders(self, orders: list[OrderData], expTime=None):
        for order in orders:
            req_ts = order.req_ts
            req_id = order.req_id
            self._order_tmp[req_id] = {'req_ts': req_ts, 'req_date': tools.ts132date(req_ts)}
            order_data = order.to_order_json()
            data = {
                "id": req_id,
                "op": "order",
                "args": [order_data],
            }
            if expTime is not None:
                data['expTime'] = expTime
            BaseTask(self.send, data).attach2loop()