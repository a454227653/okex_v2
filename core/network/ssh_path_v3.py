"""
ssh_path_v3.py;
created by Y on 2023/3/31;
基础架构-SSH端口映射v3: 为每组端口映射维持单独的SSH链接
总机运行配置：ssh_config_master.json
分机运行配置：ssh_config_slave.json
"""

import asyncio
import asyncssh
import json
import logging
import sys


async def create_tunnel(ssh_config, ssh_connection_map, logger):
	ssh_host = ssh_config.get('ssh_host', None)
	ssh_username = ssh_config.get('ssh_username', None)
	ssh_client_keys = ssh_config.get('client_keys', None)
	ssh_compression_algs = ssh_config.get('compression_algs', 'zlib@openssh.com')
	keepalive_interval = ssh_config.get('keepalive_interval', 30)
	keepalive_count_max = ssh_config.get('keepalive_count_max', 3)
	local_port = ssh_config.get('local_port', 2046)
	local_host = ssh_config.get('local_host', 'localhost')
	remote_port = ssh_config.get('remote_port', 2046)
	remote_host = ssh_config.get('remote_host', 'localhost')
	direction = ssh_config.get('direction', 'local')
	connection_name = ssh_config.get('name', 'default')
	try:
		connection = await asyncssh.connect(host=ssh_host
		                                    , username=ssh_username
		                                    , client_keys=ssh_client_keys
		                                    , compression_algs=ssh_compression_algs
		                                    , keepalive_interval=keepalive_interval
		                                    , keepalive_count_max=keepalive_count_max)
		if direction == 'local':
			listener = await connection.forward_local_port('', local_port, remote_host, remote_port)
		elif direction == 'remote':
			listener = await connection.forward_remote_port('', remote_port, local_host, local_port)
	except (BaseException, asyncssh.ChannelListenError, AssertionError) as e:
		logger.error(e)
		logger.info('SSH connection %s: create connection failed, will retry latter...' % (connection_name))
	connection.set_extra_info(listen_port=local_port if direction == 'local' else remote_port)
	connection.set_extra_info(connection_name=connection_name)
	connection.set_extra_info(direction=direction)
	ssh_connection_map[connection_name] = (connection, listener)
	logger.info('SSH connection %s: %s port forward established, listening on port %s...' % (
	connection_name, direction, listener.get_port()))


async def close_tunnel(connection_name, ssh_connection_map, logger):
	connection, listener=ssh_connection_map.pop(connection_name)
	listener.close()
	connection.close()
	logger.info('SSH connection %s: connection disabled' % (connection_name))


async def check_alive_tunnel(connection, listener, ssh_connection_map, logger):
	connection_name = connection.get_extra_info('connection_name')
	listen_port = connection.get_extra_info('listen_port')
	if listener.get_port() != listen_port:
		logger.info('SSH connection %s: listener on port %s is lost, will try reconnect...' % (
		connection_name, str(listen_port)))
		await close_tunnel(connection_name, ssh_connection_map, logger)
	try:
		# 这里为了节省信道, 执行的 ‘ls /media‘ 命令一般会返回空字符串
		# 可以在服务器上新建空目录来防止 ’/media‘ 被写入内容， ’ls xxx‘ 检测不到目录时, check_alive会失败
		result = await connection.run('ls /media', check=True, timeout=5)
		logger.debug('SSH connection %s is alive'% (connection_name))
	except (asyncssh.ChannelOpenError, asyncssh.ProcessError, asyncssh.TimeoutError) as e:
		logger.error(e)
		logger.info('SSH connection %s: connection check alive failed, will try reconnect...' % (connection_name))
		await close_tunnel(connection_name, ssh_connection_map, logger)


async def ssh_path_loop(ssh_config_list, ssh_connection_map, logger):
	connect_nums_before = len(ssh_connection_map)
	# 关闭失效通道

	tasks = [check_alive_tunnel(v[0], v[1], ssh_connection_map, logger) for k, v in ssh_connection_map.items()]
	await asyncio.gather(*tasks, return_exceptions=True)
	connect_nums_after_ckeck = len(ssh_connection_map)
	update = connect_nums_before != connect_nums_after_ckeck

	# 新建在配置中的通道
	tasks = []
	for ssh_config in ssh_config_list:
		connection_name = ssh_config.get('name', 'default')
		if connection_name not in ssh_connection_map:
			tasks.append(create_tunnel(ssh_config, ssh_connection_map, logger))
	await asyncio.gather(*tasks, return_exceptions=True)
	connect_nums_after_create = len(ssh_connection_map)
	update = update or connect_nums_after_ckeck != connect_nums_after_create

	# 关闭不在配置中的通道
	tasks = []
	ssh_config_list_connection_names = set([ssh_config['name'] for ssh_config in ssh_config_list])
	for connection_name, connection in ssh_connection_map.items():
		if connection_name not in ssh_config_list_connection_names:
			tasks.append(close_tunnel(connection_name, ssh_connection_map, logger))
	await asyncio.gather(*tasks, return_exceptions=True)
	connect_nums_after_create = len(ssh_connection_map)
	update = update or connect_nums_after_create != connect_nums_after_ckeck

	# 一轮 loop 还健在的链接
	if update:
		logger.info("Alive connections: " + str([k for k in ssh_connection_map]))


def process_config(key_map, config_path="ssh_config_master.json"):
	with open(config_path, 'r') as f:
		config = json.load(f)
	default_config = config.get('default_config', {})
	tunnels = config.get('tunnels', [])
	for term in tunnels:
		term.update(default_config)
	for config in tunnels:
		if 'ssh_key_path' in config:
			ssh_key_path = config.get('ssh_key_path')
			if ssh_key_path in key_map:
				config['client_keys'] = key_map[ssh_key_path]
			else:
				client_keys = [asyncssh.read_private_key(ssh_key_path)]
				key_map[ssh_key_path] = client_keys
				config['client_keys'] = client_keys
	return tunnels


async def main(logger, config_path):
	key_map = {}
	ssh_connection_map = {}
	break_cnt = 0
	while (True):
		ssh_config_list = process_config(key_map, config_path)
		try:
			await ssh_path_loop(ssh_config_list, ssh_connection_map, logger)
			await asyncio.sleep(10)
		except (OSError, AssertionError, asyncssh.ChannelListenError) as e:
			logger.error(e)
			logger.info("ssh_path_loop breaked for %s times, will retry latter..." % (str(break_cnt)))
			await asyncio.sleep(1)


if __name__ == "__main__":
	logging.basicConfig(format="%(asctime)s:%(levelname)s:%(funcName)s-%(message)s", level=logging.INFO)
	# 全局logger级别
	logging.getLogger().setLevel(logging.ERROR)
	# 本脚本logger 级别
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)

	config_path = sys.argv[1] if len(sys.argv)>1 else "ssh_config_master.json"
	asyncio.run(main(logger, config_path))
