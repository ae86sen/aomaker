# --coding:utf-8--
from attrs import define, field
from functools import partial
from typing import List, Any, Callable, Dict
import requests

from .middlewares.middlewares import middlewares_registry, MiddlewareCallable, RequestType, ResponseType



class HTTPClient:
    def __init__(self, middlewares: List[MiddlewareCallable] = None):
        self.session = requests.Session()
        # 合并全局中间件和实例中间件
        self.middlewares = middlewares_registry.copy()
        if middlewares:
            self.middlewares.extend(middlewares)

    def send_request(self, request: RequestType, **kwargs) -> ResponseType:
        # 合并请求参数
        merged_request = {**request, **kwargs}

        def send(req: RequestType) -> ResponseType:
            return self.session.request(**req)

        # 正向遍历中间件列表，构造调用链
        call_next = send
        for middleware in reversed(self.middlewares):  # 注意此处仍需反向
            call_next = partial(middleware, call_next=call_next)

        return call_next(merged_request)

