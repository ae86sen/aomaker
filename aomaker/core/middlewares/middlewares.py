# --coding:utf-8--
from typing import Callable, Dict, Any, TypeVar, Optional


RequestType = Dict[str, Any]
ResponseType = TypeVar('ResponseType')

CallNext = Callable[[RequestType], ResponseType]
MiddlewareCallable = Callable[[RequestType, CallNext], ResponseType]

middlewares_registry = []



def register_middleware(middleware: Optional[MiddlewareCallable] = None, *, global_registry: bool = True):

    def decorator(func: MiddlewareCallable) -> MiddlewareCallable:
        if global_registry:
            middlewares_registry.append(func)
        return func

    if middleware is None:
        return decorator
    else:
        return decorator(middleware)



