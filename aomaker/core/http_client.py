# --coding:utf-8--
from functools import partial
from typing import List, Any, Type
from contextlib import contextmanager
from copy import deepcopy

import requests

from aomaker.storage import cache

from .middlewares.registry import MiddlewareCallable, RequestType, ResponseType, registry, init_middlewares


class CachedResponse:
    def __init__(self, raw_response: requests.Response):
        self.raw_response = raw_response
        self._cached_json = None

    def __getattr__(self, name):
        return getattr(self.raw_response, name)

    def json(self, **kwargs) -> Any:
        if self._cached_json is None:
            self._cached_json = self.raw_response.json(**kwargs)
        return self._cached_json  


class HTTPClient:
    def __init__(self, middlewares: List[MiddlewareCallable] = None):
        self.session = requests.Session()
        init_middlewares()
        self.middlewares = registry.active_middlewares
        if middlewares:
            self.middlewares.extend(middlewares)

    def send_request(self, request: RequestType, override_headers: bool = False, **kwargs) -> ResponseType:
        if override_headers:
            final_headers = request.get("headers", {})
        else:
            final_headers = {**self.session.headers, **request.get("headers", {})}

        merged_request = {**request, **kwargs, "headers": final_headers}

        def send(req: RequestType) -> ResponseType:
            req.pop("_api_meta")
            raw_response = self.session.request(**req)
            return CachedResponse(raw_response)

        call_next = send
        for middleware in reversed(self.middlewares):
            call_next = partial(middleware, call_next=call_next)

        return call_next(merged_request)

    @contextmanager
    def headers_override_scope(self, headers: dict):
        """上下文管理器：临时完全替换请求头"""
        original_headers = deepcopy(self.session.headers)
        try:
            self.session.headers.clear()
            self.session.headers.update(headers)
            yield
        finally:
            self.session.headers = original_headers


def get_http_client(default_client: Type[HTTPClient]) -> HTTPClient:
    if not hasattr(get_http_client, "client"):
        get_http_client.client = default_client()
        headers = cache.get("headers")
        get_http_client.client.session.headers.update(headers)
    return get_http_client.client
