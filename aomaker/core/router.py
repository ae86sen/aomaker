# --coding:utf-8--
from typing import TypeVar
import re

from .base_model import EndpointConfig, HTTPMethod

T = TypeVar('T')


class APIRouter:

    def __init__(self, prefix: str = "", common_route: str = ""):
        self.prefix = prefix.lstrip("/")
        self.common_route = common_route.lstrip("/").rstrip("/")

    def route(self, path: str, method: str, **kwargs):
        method_upper = method.upper()

        def decorator(cls):
            full_path = f"{self.prefix}/{path.lstrip('/')}"
            route_params = re.findall(r'{(\w+)}', full_path)
            endpoint_config = EndpointConfig(
                route=full_path,
                method=method_upper,
                route_params=route_params,
                common_route=self.common_route
            )

            setattr(cls, '_endpoint_config', endpoint_config)
            return cls

        return decorator

    def get(self, path: str, **kwargs):
        return self.route(path, HTTPMethod.GET, **kwargs)

    def post(self, path: str, **kwargs):
        return self.route(path, HTTPMethod.POST, **kwargs)

    def put(self, path: str, **kwargs):
        return self.route(path, HTTPMethod.PUT, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.route(path, HTTPMethod.DELETE, **kwargs)
