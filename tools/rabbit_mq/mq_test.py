"""
mq_test.py.py
created by Yan on 2023/4/23 21:24;
"""
import pika
from pika.exchange_type import ExchangeType

credentials = pika.PlainCredentials('liwan', '199361')
connection_param = pika.ConnectionParameters(
    host = '127.0.0.1'
    , port = 5673
    , credentials= credentials
)
connection = pika.BlockingConnection(connection_param)
channel = connection.channel()

channel.exchange_declare(exchange='routing', exchange_type='topic')

queue = channel.queue_declare(queue='hello', exclusive=False)
queue_name = queue.method.queue


channel.queue_bind(exchange='routing', queue=queue_name, routing_key='test.1')
channel.queue_bind(exchange='routing', queue=queue_name, routing_key='test.2')

print(' [*] Waiting for logs. To exit press CTRL+C')

def callback1(ch, method, properties, body):
    print("callback1 [x] %r" % body)


channel.basic_consume(
    queue=queue_name, on_message_callback=callback1, auto_ack=False)


channel.start_consuming()