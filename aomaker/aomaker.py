# --coding:utf-8--
import os
from typing import List, Dict, Callable, Text
from functools import wraps

import yaml
from jsonpath import jsonpath
from genson import SchemaBuilder

from aomaker.cache import Cache
from aomaker.log import logger
from aomaker.path import BASEDIR
from aomaker.exceptions import FileNotFound, YamlKeyError


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

            cache = Cache()
            # 1.先判断是否调用过依赖
            if not cache.get(var_name):

                # 2.调用依赖
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
                else:
                    # 不同类下的接口
                    depend_api_name = dependent_api.__name__
                    logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
                    res = dependent_api(*out_args, **out_kwargs)
                # 3.存储响应结果
                cache.set(var_name, res)

                logger.info(f"==========存储全局变量{var_name}完成==========")
                logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>结束==========")
            else:
                logger.info(f"==========<{api_name}>前置依赖已被调用过，本次不再调用,依赖参数{var_name}直接从cache表中读取==========")
            r = func(*args, **kwargs)
            return r

        return wrapper

    return decorator


def async_api(cycle_func: Callable, jsonpath_expr: Text, expr_index=0, *out_args, **out_kwargs):
    """
    异步接口装饰器
    目标接口请求完成后，根据jsonpath表达式从其响应结果中提取异步任务id，
    然后将异步任务id传给轮询函数

    :param cycle_func: 轮询函数
    :param jsonpath_expr: 异步任务id提取表达式
    :param expr_index: jsonpath提取索引，默认为0
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            r = func(*args, **kwargs)
            logger.info(f"==========后置异步接口断言开始<{func.__name__}>: 轮询函数<{cycle_func.__name__}>==========")
            try:
                job_id = jsonpath(r, jsonpath_expr)[expr_index]
            except TypeError as te:
                logger.error(f"响应异常，异步任务id提取失败\n响应：{r}")
                raise te
            except IndexError as ie:
                logger.error(f"索引异常，异步任务id提取失败\n索引：{expr_index}\n响应：{r}")
                raise ie
            cycle_func(job_id, *out_args, **out_kwargs)
            logger.info(f"==========后置异步接口断言结束<{func.__name__}>==========")
            return r

        return wrapper

    return decorator


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


if __name__ == '__main__':
    x = data_maker('aomaker/data/api_data/job.yaml', 'job', 'submit_job')
    print(x)
