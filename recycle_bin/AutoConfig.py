"""
AutoConfig.py
created by Yan on 2023/4/25 20:08;
"""
import json

class BaseConfigFactory():
	@staticmethod
	def dict_repr(obj):
		if isinstance(obj, (int, float, str, bool, type(None))):
			return obj
		if isinstance(obj, list):
			return [BaseConfigFactory.dict_repr(item) for item in obj]
		if isinstance(obj, dict):
			return {key: BaseConfigFactory.dict_repr(value) for key, value in obj.items()}
		return {attr: BaseConfigFactory.dict_repr(getattr(obj, attr)) for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("__")}

	@staticmethod
	def get_config(path='./config.json'):
		with open(path, 'r') as file:
			data = json.load(file)
		return BaseConfigFactory.create_class_from_dict(data)

	@staticmethod
	def create_class_from_dict(data):
		# 创建一个新的类
		new_class = type("NewClass", (object,), {})

		# 为新类添加一个 __repr__ 方法
		def repr_method(self):
			return json.dumps(BaseConfigFactory.dict_repr(self), indent=2, sort_keys=True, ensure_ascii=False)

		setattr(new_class, "__repr__", repr_method)

		# 将字典中的键值对转换为类属性
		for key, value in data.items():
			if isinstance(value, dict):
				setattr(new_class, key, BaseConfigFactory.create_class_from_dict(value))
			elif isinstance(value, list):
				setattr(new_class, key, BaseConfigFactory.process_list(value))
			else:
				setattr(new_class, key, value)

		# 返回类的实例
		return new_class()

	@staticmethod
	def process_list(data_list):
		processed_list = []
		for item in data_list:
			if isinstance(item, dict):
				processed_list.append(BaseConfigFactory.create_class_from_dict(item))
			elif isinstance(item, list):
				processed_list.append(BaseConfigFactory.process_list(item))
			else:
				processed_list.append(item)
		return processed_list