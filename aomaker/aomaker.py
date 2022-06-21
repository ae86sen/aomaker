# --coding:utf-8--
from functools import wraps
from typing import Callable, Text

from jsonpath import jsonpath

from aomaker.cache import Cache
from aomaker.log import logger


def dependence(dependent_api: Callable, var_name: Text, *out_args, **out_kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_name = func.__name__
            depend_api_name = dependent_api.__name__
            cache = Cache()
            # 1.先判断是否调用过依赖
            if not cache.get(var_name):
                logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>执行==========")
                # 2.调用依赖
                res = dependent_api(*out_args, **out_kwargs)
                # 3.存储响应结果
                cache.set(var_name, res)

                logger.info(f"==========存储全局变量{var_name}完成==========")
            logger.info(f"==========<{api_name}>前置依赖<{depend_api_name}>结束==========")
            r = func(*args, **kwargs)
            return r

        return wrapper

    return decorator


def async_api(cycle_func: Callable, jsonpath_expr: Text, expr_index=0):
    """
    异步接口装饰器
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
            except IndexError as ie:
                logger.error(f"异步任务id提取失败")
                raise ie
            cycle_func(job_id)
            logger.info(f"==========后置异步接口断言结束<{func.__name__}>==========")
            return r

        return wrapper

    return decorator


def _extract_by_jsonpath(source: Text, jsonpath_expr: Text, index: int):
    target = jsonpath(source, jsonpath_expr)[index]
    return target