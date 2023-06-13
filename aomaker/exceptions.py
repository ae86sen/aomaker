# --coding:utf-8--
class AoMakerException(Exception):
    pass


class NotFoundError(AoMakerException):
    pass


class FileNotFound(FileNotFoundError, AoMakerException):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f'文件未找到：{self.path}，请确保该文件存在'


class SchemaNotFound(NotFoundError):
    def __init__(self, api_name):
        self.api_name = api_name

    def __str__(self):
        return f'jsonschema未找到:{self.api_name}，请确保该api的jsonschema存在'


class ConfKeyError(AoMakerException):
    def __init__(self, key_name):
        self.key_name = key_name

    def __str__(self):
        return f'config.yaml配置文件中未找到key:{self.key_name}，请确保该key存在'


class YamlKeyError(AoMakerException):
    def __init__(self, file_path, key_name):
        self.file_path = file_path
        self.key_name = key_name

    def __str__(self):
        return f'测试数据文件（{self.file_path}）中未找到key:{self.key_name}，请确保该key存在'


class LoginError(AoMakerException):
    def __str__(self):
        return "用例启动函数run未传入Login对象"


class HttpRequestError(AoMakerException):
    def __init__(self, status_code):
        self.status_code = status_code

    def __str__(self):
        return f'请求失败，状态码：{self.status_code}'


class JsonPathExtractFailed(AoMakerException):
    def __init__(self, res, jsonpath_expr):
        self.res = res
        self.jsonpath_expr = jsonpath_expr

    def __str__(self):
        return f'依赖数据提取失败\n 提取表达式：{self.jsonpath_expr}\n 数据源：{self.res}'