# --coding:utf-8--
import os
from typing import List, Dict, Text
from functools import wraps

import yaml
import click
from jsonpath import jsonpath
from genson import SchemaBuilder

from aomaker.path import BASEDIR
from aomaker.exceptions import FileNotFound, YamlKeyError
from aomaker.hook_manager import cli_hook, session_hook



def command(name, **out_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from aomaker.cli import main, OptionHandler
            cmd = main.get_command(None, 'run')
            option_handler = OptionHandler()
            option_handler.add_option(name, **out_kwargs)
            cmd.params.append(click.Option(option_handler.options.pop("name"), **option_handler.options))
            new_name = name.replace("-", "")
            cli_hook.register(func, new_name)

        return wrapper

    return decorator


def hook(func):
    @wraps(func)
    def wrapper():
        session_hook.register(func)

    return wrapper


def data_maker(file_path: str, class_name: str, method_name: str) -> List[Dict]:
    """
    从测试数据文件中读取文件，构造数据驱动的列表参数
    :param file_path: 测试数据文件（相对路径，相对项目根目录）
    :param class_name: 类名
    :param method_name: 方法名
    :return:
            eg:
            [{"name":"zz"},{"name":"yy"},...]
    """
    yaml_path = os.path.join(BASEDIR, file_path)
    if not os.path.exists(yaml_path):
        raise FileNotFound(yaml_path)
    class_data = _load_yaml(yaml_path).get(class_name)
    if class_data is None:
        raise YamlKeyError(file_path, class_name)
    method_data = class_data.get(method_name)
    if method_data is None:
        raise YamlKeyError(file_path, method_name)
    return method_data


def genson(data):
    """
    生成jsonschema
    :param data: json格式数据
    :return: jsonschema
    """
    builder = SchemaBuilder()
    builder.add_object(data)
    to_schema = builder.to_schema()
    return to_schema


def _extract_by_jsonpath(source: Text, jsonpath_expr: Text, index: int):
    target = jsonpath(source, jsonpath_expr)[index]
    return target



def _load_yaml(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        yaml_testcase = yaml.safe_load(f)
    return yaml_testcase



if __name__ == '__main__':
    x = data_maker('aomaker/data/api_data/job.yaml', 'job', 'submit_job')
    print(x)
