# --coding:utf-8--
import re

from .base_model import EndpointConfig, HTTPMethod


class APIRouter:

    def route(self, path: str, method: HTTPMethod, **kwargs):

        def decorator(cls):
            route_params = re.findall(r'{(\w+)}', path)
            endpoint_config = EndpointConfig(
                route=path,
                method=method,
                route_params=route_params,
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

    def patch(self, path: str, **kwargs):
        return self.route(path, HTTPMethod.PATCH, **kwargs)


router = APIRouter()