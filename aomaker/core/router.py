# --coding:utf-8--
from typing import TypeVar, Optional
import re

from .base_model import EndpointConfig, HTTPMethod

T = TypeVar('T')


class APIRouter:

    def __init__(self, backend_prefix: Optional[str] = None, frontend_prefix: Optional[str] = None):
        self.backend_prefix = backend_prefix.strip("/") if backend_prefix else None
        self.frontend_prefix = frontend_prefix.strip("/") if frontend_prefix else None

    def route(self, path: str, method: HTTPMethod, **kwargs):
        def decorator(cls):
            original_path = path.strip("/")

            if self.backend_prefix and self.frontend_prefix:
                if original_path.startswith(f"{self.backend_prefix}/"):
                    replaced_path = original_path.replace(
                        f"{self.backend_prefix}/",
                        f"{self.frontend_prefix}/",
                        1  # 仅替换第一个匹配项
                    )
                else:
                    replaced_path = original_path
            else:
                replaced_path = original_path

            frontend_full_path = f"/{replaced_path}"

            route_params = re.findall(r'{(\w+)}', frontend_full_path)

            endpoint_config = EndpointConfig(
                route=frontend_full_path,
                method=method,
                route_params=route_params,
                backend_prefix=self.backend_prefix,
                frontend_prefix=self.frontend_prefix,
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
