# --coding:utf-8--
import json
import os
import importlib
from typing import List, Dict, Callable, Text, Tuple, Union
from functools import wraps
from dataclasses import dataclass as dc, field

import yaml
import click
from jsonpath import jsonpath
from genson import SchemaBuilder

from aomaker.cache import cache
from aomaker.log import logger
from aomaker.path import BASEDIR
from aomaker.exceptions import FileNotFound, YamlKeyError, JsonPathExtractFailed
from aomaker.hook_manager import _cli_hook, _session_hook
from aomaker.models import ExecuteAsyncJobCondition


def dependence(dependent_api: Callable or str, var_name: Text, imp_module=None, *out_args, **out_kwargs):
    """
    接口依赖调用装饰器，
    会在目标接口调用前，先去调用其前置依赖接口，然后存储依赖接口的完整响应结果到cache表中，key为var_name
    若var_name已存在，将不会再调用该依赖接口

    :param dependent_api: 接口依赖，直接传入接口对象；若依赖接口是同一个类下的方法，需要传入字符串：类名.方法名
    :param var_name: 依赖的参数名
    :param imp_module: 若依赖接口是同一个类下的方法，需要导入模块
    :param out_args: 依赖接口需要的参数
    :param out_kwargs: 依赖接口需要的参数
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_name = func.__name__
            if not cache.get(var_name):
                dependence_res, depend_api_info = _call_dependence(dependent_api, api_name, imp_module=imp_module,
                                                                   *out_args, **out_kwargs)
                depend_api_name = depend_api_info.get("name")
                cache.set(var_name, dependence_res, api_info=depend_api_info)

                logger.info(f"==========存储全局变量{var_name}完成==========")
                logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>结束==========")
            else:
                logger.info(
                    f"==========<{api_name}>前置依赖已被调用过，本次不再调用,依赖参数{var_name}直接从cache表中读取==========")
            r = func(*args, **kwargs)
            return r

        return wrapper

    return decorator


def async_api(cycle_func: Callable, jsonpath_expr: Union[Text, List], expr_index=0, condition: Dict = None, *out_args,
              **out_kwargs):
    """
    异步接口装饰器
    目标接口请求完成后，根据jsonpath表达式从其响应结果中提取异步任务id，
    然后将异步任务id传给轮询函数

    :param cycle_func: 轮询函数
    :param jsonpath_expr: 异步任务id提取表达式
    :param expr_index: jsonpath提取索引，默认为0
    :param condition: 是否执行轮询函数的条件，默认执行。如果传了condition，那么当满足condition时执行cycle_func，不满足不执行。
            example：
                condition = {"expr":"ret_code","expected_value":0}
                当返回值中的ret_code == 0时，会去执行cycle_func进行异步任务检查，反之不执行。
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            is_execute = _is_execute_cycle_func(resp, condition=condition)
            if is_execute:
                job_id = _handle_jsonpath_extract(resp, jsonpath_expr, expr_index=expr_index)
                if job_id is None:
                    if condition is None:
                        raise JsonPathExtractFailed(res=resp, jsonpath_expr=jsonpath_expr)
                    return resp

                logger.info(
                    f"==========后置异步接口断言开始<{func.__name__}>: 轮询函数<{cycle_func.__name__}>==========")
                cycle_func(job_id, *out_args, **out_kwargs)
                logger.info(f"==========后置异步接口断言结束<{func.__name__}>==========")
            else:
                logger.info(f"==========后置异步接口不满足执行条件，不执行<{func.__name__}>==========")
            return resp

        return wrapper

    return decorator


def update(var_name: Text, *out_args, **out_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            api_name = func.__name__
            if cache.get(var_name):
                logger.info(f"==========cache变量<{var_name}>开始更新==========")
                api_info = cache.get(var_name, select_field="api_info")
                dependence_res = _call_dependence_for_update(api_info, *out_args, **out_kwargs)
                cache.update(var_name, dependence_res)
                logger.info(f"==========<{api_name}>cache更新<{api_info.get('name')}>结束==========")
            return resp

        return wrapper

    return decorator


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
            _cli_hook.register(func, new_name)

        return wrapper

    return decorator


def hook(func):
    @wraps(func)
    def wrapper():
        _session_hook.register(func)

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


def dataclass(cls):
    @property
    def all_fields(self):
        return self.__dict__

    cls.all_fields = all_fields

    for field_name, field_type in cls.__annotations__.items():
        if field_name not in cls.__dict__:
            # 跳过必须字段
            continue
        if field_type is list:
            default_value = getattr(cls, field_name, [])
            if default_value is not None:
                setattr(cls, field_name, field(default_factory=lambda: list(default_value)))
        elif field_type is dict:
            default_value = getattr(cls, field_name, {})
            if default_value is not None:
                setattr(cls, field_name, field(default_factory=lambda: dict(default_value)))
    return dc(cls)


def _call_dependence(dependent_api: Callable or Text, api_name: Text, imp_module, *out_args,
                     **out_kwargs) -> Tuple:
    if isinstance(dependent_api, str):
        # 同一个类下的接口
        class_, method_ = _parse_dependent_api(dependent_api)
        try:
            exec(f'from {imp_module} import {class_}')
        except ModuleNotFoundError as mne:
            logger.error(f"导入模块{imp_module}未找到，请确保imp_module传入参数正确")
            raise mne
        except ImportError as ie:
            logger.error(f"导入ao对象错误：{class_}，请确保dependence传入参数正确")
            raise ie
        except SyntaxError as se:
            logger.error(f"dependence传入imp_module参数错误，imp_module={imp_module} ")
            raise se
        depend_api_name = eval(f"{class_}.{method_}.__name__")
        logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
        try:
            res = eval(f'{class_}.{method_}(*{out_args},**{out_kwargs})')
        except TypeError as te:
            logger.error(f"dependence参数传递错误，错误参数：{dependent_api}")
            raise te
        depend_api_info = {"name": method_, "module": imp_module, "ao": class_.lower()}
    else:
        # 不同类下的接口
        depend_api_name = dependent_api.__name__
        logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
        res = dependent_api(*out_args, **out_kwargs)
        depend_api_info = {"name": depend_api_name, "module": _get_module_name_by_method_obj(dependent_api),
                           "ao": type(dependent_api.__self__).__name__.lower()}
    return res, depend_api_info


def _call_dependence_for_update(api_info: Dict, *out_args, **out_kwargs) -> Dict:
    api_name = api_info.get("name")
    api_module = api_info.get("module")
    module = importlib.import_module(api_module)
    try:
        ao = getattr(module, api_info.get("ao"))
    except AttributeError as e:
        logger.error(f"在{api_module}中未找到ao对象<{api_info.get('ao')}>！")
        raise e
    res = getattr(ao, api_name)(*out_args, **out_kwargs)
    return res


def _extract_by_jsonpath(source: Text, jsonpath_expr: Text, index: int):
    target = jsonpath(source, jsonpath_expr)[index]
    return target


def _parse_dependent_api(dependent_api):
    try:
        class_, method_ = dependent_api.split('.')
    except ValueError as ve:
        logger.error(f"dependence参数传递错误，错误参数：{dependent_api}")
        raise ve
    else:
        return class_, method_


def _load_yaml(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        yaml_testcase = yaml.safe_load(f)
    return yaml_testcase


def _get_module_name_by_method_obj(method_obj) -> Text:
    """
    return: x.y.z
    """
    module_name = method_obj.__module__
    module_path = importlib.import_module(module_name).__file__
    cur_dir = os.path.abspath('.')
    rel_path = os.path.relpath(module_path, cur_dir)
    module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
    return module_name


def _handle_jsonpath_extract(resp, jsonpath_expr, expr_index=0):
    if isinstance(jsonpath_expr, str):
        jsonpath_expr = [jsonpath_expr]

    for expr in jsonpath_expr:
        extract_res = jsonpath(resp, expr)
        if extract_res:
            return extract_res[expr_index]

    # raise JsonPathExtractFailed(res=resp, jsonpath_expr=jsonpath_expr)


def _is_execute_cycle_func(res, condition=None) -> bool:
    if condition is None:
        return True
    data = ExecuteAsyncJobCondition(**condition)
    expr = data.expr
    expected_value = data.expected_value
    res = jsonpath(res, expr)
    if res is False:
        raise JsonPathExtractFailed(res=res, jsonpath_expr=expr)
    if res[0] == expected_value:
        return True
    return False


if __name__ == '__main__':
    x = data_maker('aomaker/data/api_data/job.yaml', 'job', 'submit_job')
    print(x)
