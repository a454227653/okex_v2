"""
MarketServer.py
created by Yan on 2023/4/29 17:00;
"""
from core.config import *
from core.utils import logger
import aiohttp
from core.task import *

class MarKetServer():
	platform_key = None

	def __init__(self, config: MainConfig):
		self.config = config.Platforms.get(self.platform_key, {})


	async def _on_connected(self):
		pass

	async def _connect(self):
		"""
		链接
		"""
		logger.debug("url:", self._url, caller=self)
		proxy = config.proxy
		session = aiohttp.ClientSession()
		try:
			self._ws = await session.ws_connect(self._url, proxy=proxy)
		except aiohttp.ClientConnectorError:
			logger.error("connect to Websocket server error! url:", self._url, caller=self)
			return
		if self._on_connected:
			BaseTask(self._on_connected()).attach2loop()
		BaseTask(self._receive).attach2loop()

	def process(self, msg):
		pass
