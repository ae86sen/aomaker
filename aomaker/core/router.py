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
            # 原始路径处理
            original_path = path.strip("/")

            # 执行路径替换（如果有配置）
            if self.backend_prefix and self.frontend_prefix:
                # 确保 backend_prefix 出现在路径开头
                if original_path.startswith(f"{self.backend_prefix}/"):
                    replaced_path = original_path.replace(
                        f"{self.backend_prefix}/",
                        f"{self.frontend_prefix}/",
                        1  # 仅替换第一个匹配项
                    )
                else:
                    # 如果路径不匹配 backend_prefix，保持原路径（或抛出警告）
                    replaced_path = original_path
            else:
                # 未配置替换时，直接使用原路径
                replaced_path = original_path

            # 构建完整前端路径（确保以斜杠开头）
            frontend_full_path = f"/{replaced_path}"

            # 提取路径参数
            route_params = re.findall(r'{(\w+)}', frontend_full_path)

            # 存储配置
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
