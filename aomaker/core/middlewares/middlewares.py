# --coding:utf-8--
from typing import Callable, Dict, Any, TypeVar


RequestType = Dict[str, Any]
ResponseType = TypeVar('ResponseType')

CallNext = Callable[[RequestType], ResponseType]
MiddlewareCallable = Callable[[RequestType, CallNext], ResponseType]

middlewares_registry = []


def register_middleware(middleware_func):
    print("Registering middleware")
    middlewares_registry.append(middleware_func)
    return middleware_func


# @register_middleware



