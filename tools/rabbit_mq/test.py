import pika, json, zlib
credentials = pika.PlainCredentials('liwan', '199361')
connection_param = pika.ConnectionParameters(
    host = '127.0.0.1'
    , port = 5673
    , credentials= credentials
)
connection = pika.BlockingConnection(connection_param)
channel = connection.channel()
# channel.queue_declare(queue='hello')

res = 'Hello World!'

for i in range(10):
    channel.basic_publish(exchange='routing', routing_key='test.2', body=res)
# channel.queue_delete(queue='hello')
