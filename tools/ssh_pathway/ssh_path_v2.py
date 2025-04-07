"""
ssh_path_v2.py;
created by Y on 2023/2/26;
基础架构-SSH端口映射v2: 为所有端口映射维持一条SSH链接
"""

import asyncio
import asyncssh
import json
import logging
import sys

async def setup_tunnel(tunnel, ssh_config, logger, connect):
	local_port, remote_port, direction, name = tunnel['local_port'], tunnel['remote_port'], tunnel['direction'], tunnel['name']
	if direction == 'local':
		listener = await connect.forward_local_port('',  local_port, 'localhost', remote_port)
	elif direction == 'remote':
		listener = await connect.forward_remote_port('', remote_port, 'localhost', local_port)
	logger.info('New %s ssh tunnel %s established, listening on port %s...'%(direction,name,listener.get_port()))
	return listener


async def maintain_tunnels(ssh_config, config_path, logger):
	active_listeners = []
	reconnect_times = 0 #重连次数
	while(True):
		tunnels = []
		try:
			connect = await asyncssh.connect(ssh_config['ssh_host']
			                                 , username=ssh_config["ssh_username"]
			                                 , client_keys=ssh_config['client_keys']
			                                 , compression_algs='zlib@openssh.com'
			                                 , keepalive_interval=10
			                                 , keepalive_count_max=3)
			logger.info('SSH connection to %s established...'%(ssh_config["ssh_username"]+'@'+ssh_config['ssh_host']))
			while(True):
				# 检查连接是在线， 否则重连
				result = await connect.run('ls /yan')
				if result.exit_status != 0:
					logger.error('Checking request failed:' + result.stderr)
					connect.close()
					break

				update_info = False
				with open(config_path, 'r') as f:
					new_tunnels = json.load(f)['tunnels']

				# 关闭不再需要的隧道
				for listener, tunnel in zip(active_listeners, tunnels):
					if tunnel not in new_tunnels:
						listener.close()
						logger.info('Tunnel %s closed, listening on port %s...'%(tunnel['name'], listener.get_port()))
						tunnels.remove(tunnel)
						update_info = True

				# 新建新配置中的隧道
				for tunnel in new_tunnels:
					if tunnel not in tunnels:
						listener = await setup_tunnel(tunnel, ssh_config, logger, connect)
						active_listeners.append(listener)
						tunnels.append(tunnel)
						update_info = True

				if update_info:
					logger.info('Alive tunnels: '+ str([t['name'] for t in tunnels]))
				await asyncio.sleep(10)  # 等待后重读配置文件
		except (OSError, asyncssh.Error, asyncssh.ChannelListenError, BaseException, AssertionError) as exc:
			logging.error(exc)
			reconnect_times += 1
			logger.error('SSH connection closed, will retry for %s times...' % (str(reconnect_times)))
			await asyncio.sleep(1)


async def main(logger, config_path="ssh_config_v2.json"):
	with open(config_path, 'r') as f:
		ssh_config = json.load(f)
	ssh_config['client_keys'] = [asyncssh.read_private_key(ssh_config['ssh_key_path'])]
	await maintain_tunnels(ssh_config, config_path, logger)

if __name__ == "__main__":
	logging.basicConfig(format="%(asctime)s:%(levelname)s:%(funcName)s-%(message)s", level=logging.INFO)
	# 全局logger级别
	logging.getLogger().setLevel(logging.ERROR)
	logger = logging.getLogger(__name__)
	# 本脚本logger 级别
	logger.setLevel(logging.INFO)

	config_path = sys.argv[1] if len(sys.argv) > 1 else "ssh_config_v3.json"
	try:
		asyncio.run(main(logger, config_path))
	except (OSError, asyncssh.Error, asyncssh.ChannelListenError, BaseException) as exc:
		logger.error(exc)