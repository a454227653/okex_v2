class DataFormat:
    _schema = None

    def __init__(self, schema):
        self._schema = schema

    def forward(self, data):
        result = {}
        for key, type in self._schema:
            if key in data:
                result.update(key, self._format(data[key], type))
        return result

    def __format(self, value, type):
        return value
