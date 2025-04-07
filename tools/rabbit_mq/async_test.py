
from core.task import *
from core.utils import logger
import aioamqp, asyncio, zlib, json, time
from core.config.ConfigDef import *
import uuid

async def block():
    # while correlation_id not in self._reply_tmp:
    #     time.sleep(0.01)
    await asyncio.sleep(15)

async def con():
    transport, protocol = await aioamqp.connect(host='localhost', port='5672', login='liwan', password='199361', login_method="PLAIN")
    channel = await protocol.channel()
    return channel

channel = BaseTask(con).run_once()


res = 'Hello!'
reply_tmp = {}
request_tmp=set()

async def request_async(data):
    # await self._check_connection()
    correlation_id = uuid.uuid4().__str__()
    request_tmp.add(correlation_id)
    data = json.dumps({'data': data})
    b = zlib.compress(data.encode("utf8"))
    await channel.basic_publish(payload=b, exchange_name='rpc_server', routing_key='test_class.1',properties={'correlation_id': correlation_id})
    # await channel.basic_publish(payload=b, exchange_name='rpc_client', routing_key='test_class.reply', properties={"correlation_id" : correlation_id})
    # await self.block(correlation_id)

for i in range(1000):
    BaseTask(request_async, res).run_once()
    time.sleep(0.1)