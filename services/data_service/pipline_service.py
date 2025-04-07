import logging, prefect
from core.rpc.rpc_server import *
from core.config.base_config import *
from core.utils import logger
from services.constant import *
from services.data_service.data_service import InstanceData, LogData

logging.getLogger().setLevel(logging.INFO)


class PiplineService(Rpc):
	mode = COMPETITION
	server_name = 'pipline'

	def __init__(self, config : BaseConfig = json_config):
		self._rpc_client = RpcClient(self.server_name, hello_server=False)
		super(PiplineService, self).__init__()

	async def _log_report(self, type='monitor', msg=None):
		# 监控/报错日志
		ts = tools.get_now_ts13()
		if type == 'monitor':
			data = {}
		elif type == 'error':
			data = {'e': msg.args[0], 'trace_back': "\n" + "".join(traceback.format_tb(msg.__traceback__))}
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

	@prefect.task
	async def _before_run(self, instance: InstanceData):
		pre_logger = prefect.get_run_logger()
		para = instance.para
		new_para = {}
		for key in para:
			value = para[key]
			if value[0:2]=='$.':
				new_para[key] = instance.__getattribute__(value[2:])
			else:
				new_para[key] = value
		instance.para = new_para
		instance.status = 'running'
		instance.instance_start_date = tools.get_now_date()
		instance.retry_nums = 0 if instance.retry_nums is None else instance.retry_nums+1
		flow_run_id = str(prefect.context.get_run_context().task_run.dict().get('flow_run_id'))
		instance.log = 'http://127.0.0.1:4200/flow-runs/flow-run/{id}'.format(id=flow_run_id)
		pre_logger.info('Pipline service instance starting: {i}'.format(i=instance.to_json()))
		await instance.update_async(self._rpc_client)
		return instance

	@prefect.task
	async def _after_run(self, e, instance: InstanceData):
		pre_logger = prefect.get_run_logger()
		instance.status = 'failed' if isinstance(e, BaseException) else 'success'
		pre_logger.info('Pipline service instance {s}: {i}'.format(s=instance.status, i=instance.to_json()))
		if instance.status == 'failed' and instance.retry_nums < instance.max_retry_nums:
			instance.status = 'ready'
		await instance.update_async(self._rpc_client)
		if isinstance(e, BaseException):
			raise e

	@prefect.task
	async def _python_run(self, instance):
		pre_logger = prefect.get_run_logger()
		para = instance.para
		para['logger']=pre_logger
		pre_logger.info('Pipline service instance running: {i}'.format(i=instance.to_json()))
		try:
			exec(instance.code, para)
			return None
		except Exception as e:
			return e

	@prefect.task
	async def _bash_run(self, instance):
		pre_logger = prefect.get_run_logger()
		para = instance.para
		para['logger']=pre_logger
		pre_logger.info('Pipline service instance running: {i}'.format(i=instance.to_json()))
		import subprocess
		try:
			result = subprocess.run(instance.code, shell=True, capture_output=True, text=True)
			pre_logger.info(result.stdout)
			if result.returncode !=0:
				return Exception(result.stderr)
			else:
				return result
		except Exception as e:
			return e

	@rpc
	async def run_instance(self, instance: InstanceData):
		if instance.code_type == 'python':
			_run = self._python_run
		elif instance.code_type == 'bash':
			_run = self._bash_run
		else:
			e = IOError('PiplineService receive instance with invalid code type: {t}'.format(t=instance.to_json()))
			logger.error(e, caller=self)
			await self._log_report(type='error', msg=e)
			return

		@prefect.flow(name=instance.task_name, flow_run_name=instance.id, task_runner=prefect.task_runners.SequentialTaskRunner())
		async def _instance_flow(instance):
			instance = await self._before_run(self, instance)
			succ = await _run(self, instance)
			res = await self._after_run(self, succ, instance)

		BaseTask(_instance_flow, instance).attach2loop()


pipline = PiplineService()
if __name__ == "__main__":
	server = RpcServer(pipline)
	server.start()