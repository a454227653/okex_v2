import base64
import hmac
import json
import sys
from urllib.parse import urljoin

import requests

from core.utils.tools import *


class OkexV5:
    """OKEX Spot REST API client."""

    def __init__(self
                 , symbol='BTC-USDT'
                 , access_key='65705655-5e9f-448d-9555-cbdb37a3bddd'
                 , secret_key='C4EF02DBCD80176A83DE5E7CCEEBD7E8'
                 , passphrase='Qq_199361'
                 , host="http://www.okex.com"):
        self.symbol = symbol
        self._host = host
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase
        self._max_retry = 100

    def request(self, method, uri, params=None, body=None, headers=None, auth=False):
        """Initiate network request
       @param method: request method, GET / POST / DELETE / PUT
       @param uri: request uri
       @param params: dict, request query params
       @param body: dict, request body
       @param headers: request http header
       @param auth: boolean, add permission verification or not
       """
        if params:
            query = "&".join(
                ["{}={}".format(k, params[k]) for k in sorted(params.keys())]
            )
            uri += "?" + query
        url = urljoin(self._host, uri)

        if auth:
            timestamp = (
                    str(time.time()).split(".")[0]
                    + "."
                    + str(time.time()).split(".")[1][:3]
            )
            if body:
                body = json.dumps(body)
            else:
                body = ""
            message = str(timestamp) + str.upper(method) + uri + str(body)
            mac = hmac.new(
                bytes(self._secret_key, encoding="utf8"),
                bytes(message, encoding="utf-8"),
                digestmod="sha256",
            )
            d = mac.digest()
            sign = base64.b64encode(d)

            if not headers:
                headers = {}
            headers["Content-Type"] = "application/json"
            headers["OK-ACCESS-KEY"] = self._access_key
            headers["OK-ACCESS-SIGN"] = sign
            headers["OK-ACCESS-TIMESTAMP"] = str(timestamp)
            headers["OK-ACCESS-PASSPHRASE"] = self._passphrase
        retry = 0
        proxies = {"http": "127.0.0.1:2046",
                   "https": "127.0.0.1:2046"}
        while (retry < self._max_retry):
            try:
                if retry > 0:
                    print('retry ' + str(retry))
                result = requests.request(
                    method, url, data=body, headers=headers, timeout=10, proxies=proxies
                ).json()
                if result.get("code") and result.get("code") == "0":
                    return result, None
                else:
                    return None, result
            except Exception as e:
                time.sleep(1)
                retry += 1
                print('===================request failed info===================')
                print('method:', method)
                print('url:', url)
                print('body', body)
                print('headers', headers)
                print('error', e)
                print('===================end===================================')
        sys.exit('reuqest failed')

    def build_params(self, keys, values):
        assert len(keys) == len(values)
        res = {}
        for i in range(len(keys)):
            if values[i] is not None:
                res[keys[i]] = values[i]
        return res

    def get_exchange_info(self):
        """Obtain trading rules and trading pair information."""
        uri = "/api/v5/public/instruments"
        params = {"instType": "SPOT", "instId": self.symbol}
        success, error = self.request(method="GET", uri=uri, params=params, auth=True)
        return success, error

    def get_orderbook(self):
        """
       Get orderbook data.
       """
        uri = "/api/v5/market/books"
        params = {"instId": self.symbol, "sz": 5}
        success, error = self.request(method="GET", uri=uri, params=params)
        return success, error

    def get_trade(self):
        """
       Get trade data.
       """
        uri = "/api/v5/market/trades"
        params = {"instId": self.symbol, "limit": 1}
        success, error = self.request(method="GET", uri=uri, params=params)
        return success, error

    def get_kline(self, interval):
        """
       Get kline data.
       :param interval: kline period.
       """
        if str(interval).endswith("h") or str(interval).endswith("d"):
            interval = str(interval).upper()
        uri = "/api/v5/market/candles"
        params = {"instId": self.symbol, "bar": interval, "limit": 200}
        success, error = self.request(method="GET", uri=uri, params=params)
        return success, error

    def get_asset(self, currency):
        """
       获取现货持仓，多个币种用逗号分隔
       :param currency: e.g. ["USDT,BTC"]
       """
        params = {"ccy": currency}
        result = self.request(
            "GET", "/api/v5/account/balance", params=params, auth=True
        )
        return result

    def get_order_status(self, order_no):
        """Get order status.
       @param order_no: order id.
       """
        uri = "/api/v5/trade/order"
        params = {"instId": self.symbol, "ordId": order_no}
        success, error = self.request(method="GET", uri=uri, params=params, auth=True)
        return success, error

    def buy(self, price, quantity, order_type=None):
        """
       Open buy order.
       :param price:order price
       :param quantity:order quantity
       :param order_type:order type, "LIMIT" or "MARKET"
       :return:order id and None, otherwise None and error information
       """
        uri = "/api/v5/trade/order"
        data = {"instId": self.symbol, "tdMode": "cash", "side": "buy"}
        if order_type == "POST_ONLY":
            data["ordType"] = "post_only"
            data["px"] = price
            data["sz"] = quantity
        elif order_type == "MARKET":
            data["ordType"] = "market"
            data["sz"] = quantity
        else:
            data["ordType"] = "limit"
            data["px"] = price
            data["sz"] = quantity
        success, error = self.request(method="POST", uri=uri, body=data, auth=True)
        if error:
            return None, error
        return success["data"][0]["ordId"], error

    def sell(self, price, quantity, order_type=None):
        """
       Close sell order.
       :param price:order price
       :param quantity:order quantity
       :param order_type:order type, "LIMIT" or "MARKET"
       :return:order id and None, otherwise None and error information
       """
        uri = "/api/v5/trade/order"
        data = {"instId": self.symbol, "tdMode": "cash", "side": "sell", "sz": quantity}
        if order_type == "POST_ONLY":
            data["ordType"] = "post_only"
            data["px"] = price
            data["sz"] = quantity
        elif order_type == "MARKET":
            data["ordType"] = "market"
            data["sz"] = quantity
        else:
            data["ordType"] = "limit"
            data["px"] = price
            data["sz"] = quantity
        success, error = self.request(method="POST", uri=uri, body=data, auth=True)
        if error:
            return None, error
        return success["data"][0]["ordId"], error

    def revoke_order(self, order_no):
        """Cancel an order.
       @param order_no: order id
       """
        uri = "/api/v5/trade/cancel-order"
        data = {"instId": self.symbol, "ordId": order_no}
        _, error = self.request(method="POST", uri=uri, body=data, auth=True)
        if error:
            return order_no, error
        else:
            return order_no, None

    def revoke_orders(self, order_nos):
        """
       Cancel mutilple orders by order ids.
       @param order_nos :order list
       """
        success, error = [], []
        for order_id in order_nos:
            _, e = self.revoke_order(order_id)
            if e:
                error.append((order_id, e))
            else:
                success.append(order_id)
        return success, error

    def get_open_orders(self):
        """Get all unfilled orders.
        * NOTE: up to 100 orders
        """
        uri = "/api/v5/trade/orders-pending"
        params = {"instType": "SPOT", "instId": self.symbol}
        success, error = self.request(method="GET", uri=uri, params=params, auth=True)
        if error:
            return None, error
        else:
            order_ids = []
            if success.get("data"):
                for order_info in success["data"]:
                    order_ids.append(order_info["ordId"])
            return order_ids, None

    def get_market_candles(self, instId=None, bar=None, after=None, before=None, limit=None, request_history=False):
        """请求品类的当前k线图.
        instId: 产品ID，如BTC-USD-190927-5000-C
        bar: 时间粒度，默认值1m,如 [1m/3m/5m/15m/30m/1H/2H/4H],香港时间开盘价k线：[6H/12H/1D/2D/3D/1W/1M/3M],UTC时间开盘价k线：[/6Hutc/12Hutc/1Dutc/2Dutc/3Dutc/1Wutc/1Mutc/3Mutc]
        after: 请求此时间戳之前（更旧的数据）的分页内容，传的值为对应接口的ts
        before: 请求此时间戳之后（更新的数据）的分页内容，传的值为对应接口的ts
        limit: 分页返回的结果集数量，最大为300，不填默认返回100条

        return: [ts, 开盘价， 最高价， 最低价， 收盘价， vol, volCcy, volCcyQuote, confirm]
        vol： 交易量左侧计价
        volCcyQuote： 交易量右侧计价
        confirm: string, 0=K线未完结， 1=K线已完结
        """
        uri = "/api/v5/market/history-candles" if request_history else "/api/v5/market/candles"
        instId = self.symbol if instId is None else instId
        if str(bar).endswith("h") or str(bar).endswith("d") or str(bar).endswith("w"):
            bar = str(bar).upper()
        after = after * 1000 if after is not None else after
        before = before * 1000 if before is not None else before
        params = self.build_params(['instId', 'bar', 'after', 'before', 'limit'], [instId, bar, after, before, limit])
        success, error = self.request(method="GET", uri=uri, params=params)
        if error:
            return None, error
        else:
            return [{
                'platform': 'OKEX'
                , 'symbol': self.symbol
                , 'ts': int(data[0])
                , 'bar': 60
                , 'date': ts132date(int(data[0]))
                , 'start_p': float(data[1])
                , 'max_p': float(data[2])
                , 'min_p': float(data[3])
                , 'end_p': float(data[4])
                , 'left_vol': float(data[5])
                , 'right_vol': float(data[7])
                , 'confirm': 60
            } for data in success.get('data', [])]

    def web_socket_login(self, op, args):
        op = 'login'
        args = [{

        }]
