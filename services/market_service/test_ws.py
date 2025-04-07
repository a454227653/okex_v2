"""
test.py
created by Yan on 2023/5/18 15:09;
"""

from core.config.base_config import json_config
from core.rpc.rpc_server import RpcServer
from services.market_service.plat.okex.okex_ws import OkexWs
import logging


logging.getLogger().setLevel(logging.DEBUG)
platform_tags = ['OKEX_PUBLIC_TEST', 'OKEX_FAKE_PRIVATE']
if __name__ == "__main__":
    for tag in platform_tags:
        okws = OkexWs(tag, config=json_config)
        server = RpcServer(okws)
    server.start()
