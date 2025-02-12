# --coding:utf-8--
from attrs import define, field
from functools import partial
from typing import List, Any, Callable, Dict
import requests

from .middlewares.middlewares import middlewares_registry, MiddlewareCallable, RequestType, ResponseType

class CachedResponse:
    """代理模式实现缓存，避免继承"""
    def __init__(self, raw_response: requests.Response):
        self._raw = raw_response
        self._cached_json = None

    def __getattr__(self, name):
        """代理所有未定义属性到原始响应对象"""
        return getattr(self._raw, name)

    def json(self, **kwargs) -> Any:
        """带缓存的 JSON 解析"""
        if self._cached_json is None:
            self._cached_json = self._raw.json(**kwargs)
        return self._cached_json


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
            raw_response = self.session.request(**req)
            return CachedResponse(raw_response)

        # 正向遍历中间件列表，构造调用链
        call_next = send
        for middleware in reversed(self.middlewares):
            call_next = partial(middleware, call_next=call_next)

        return call_next(merged_request)

