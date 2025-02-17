# --coding:utf-8--
from functools import partial
from typing import List, Any

import requests

from .middlewares.middlewares import middlewares_registry, MiddlewareCallable, RequestType, ResponseType

class CachedResponse:
    def __init__(self, raw_response: requests.Response):
        self._raw = raw_response
        self._cached_json = None

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def json(self, **kwargs) -> Any:
        if self._cached_json is None:
            self._cached_json = self._raw.json(**kwargs)
        return self._cached_json


class HTTPClient:
    def __init__(self, middlewares: List[MiddlewareCallable] = None):
        self.session = requests.Session()
        self.middlewares = middlewares_registry.copy()
        if middlewares:
            self.middlewares.extend(middlewares)

    def send_request(self, request: RequestType, **kwargs) -> ResponseType:
        merged_request = {**request, **kwargs}

        def send(req: RequestType) -> ResponseType:
            req.pop("_api_meta")
            raw_response = self.session.request(**req)
            return CachedResponse(raw_response)

        call_next = send
        for middleware in reversed(self.middlewares):
            call_next = partial(middleware, call_next=call_next)

        return call_next(merged_request)

