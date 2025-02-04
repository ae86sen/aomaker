# --coding:utf-8--
from attrs import define, field
from functools import partial
from typing import List, Any, Callable, Dict
import requests

from .middlewares.middlewares import middlewares_registry, MiddlewareCallable, RequestType, ResponseType


# MiddlewareCallable = Callable[[Dict[str, Any], Any], Any]


class HTTPClient:
    def __init__(self, middlewares: List[MiddlewareCallable] = None):
        self.session = requests.Session()
        self.middlewares = middlewares_registry.copy()
        if middlewares:
            self.middlewares.extend(middlewares)

    def send_request(self, request: RequestType, **kwargs) -> ResponseType:
        def send(req: RequestType) -> ResponseType:
            return self.session.request(**req, **kwargs)

        call_next = send
        for middleware in reversed(self.middlewares):
            call_next = partial(middleware, call_next=call_next)

        response = call_next(request)
        return response
