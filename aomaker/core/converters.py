# --coding:utf-8--
from __future__ import annotations
from attrs import has, asdict, define, field
from cattr import unstructure
from typing import Dict, List, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import BaseAPIObject
from .base_model import ContentType, EndpointConfig,HTTPMethod
from .request_builder import JSONRequestBuilder, FormURLEncodedRequestBuilder, MultipartFormDataRequestBuilder, \
    RequestBuilder

REQUEST_BUILDERS = {
    ContentType.JSON: JSONRequestBuilder,
    ContentType.FORM: FormURLEncodedRequestBuilder,
    ContentType.MULTIPART: MultipartFormDataRequestBuilder,
}


# converter = Converter()

@define
class BaseConverter:
    api_object: BaseAPIObject = field(default=None)

    def convert(self) -> dict:
        request_data = self.prepare()
        builder = self.get_request_builder()
        req = builder.build_request(**request_data)
        unstructure_req = unstructure(req)
        return unstructure_req

    def get_request_builder(self) -> RequestBuilder:
        builder_class = REQUEST_BUILDERS.get(self.content_type)
        if not builder_class:
            raise ValueError(f"Unsupported content type: {self.content_type}")
        return builder_class()

    @property
    def base_url(self)->str:
        return self.api_object.base_url

    @property
    def content_type(self)->ContentType:
        return self.api_object.content_type

    @property
    def endpoint_config(self)->EndpointConfig:
        return self.api_object.endpoint_config

    @property
    def route(self) -> str:
        route = self.endpoint_config.route
        # 替换路由参数
        for param in self.endpoint_config.route_params:
            if hasattr(self.api_object, param):
                value = getattr(self.api_object, param)
                route = route.replace(f"{{{param}}}", str(value))
            else:
                raise ValueError(f"Missing required route parameter: {param}")

        return route

    def prepare(self) -> dict:
        url = self.prepare_url()
        method = self.prepare_method()
        headers = self.prepare_headers()
        params = self.prepare_params().get("query")
        request_body = self.prepare_request_body()

        request_data = {
            "url": url,
            "method": method,
            "headers": headers,
            "params": params,
            "request_body": request_body,
        }

        # 如果是 Multipart 请求，需要添加 files
        if self.content_type == ContentType.MULTIPART:
            files = self.prepare_files()
            request_data["files"] = files

        return request_data

    def prepare_url(self) -> str:
        base_url = self.base_url
        common_route = self.endpoint_config.common_route
        url = f"{base_url}/{common_route}/{self.route}" if common_route else f"{base_url}/{self.route}"
        return url

    def prepare_method(self) -> HTTPMethod:
        method = self.endpoint_config.method
        return method

    def prepare_headers(self) -> dict:
        return self.api_object.headers or {}

    def prepare_params(self) -> dict:
        params = dict()
        if self.api_object.path_params:
            path_params = unstructure(self.api_object.path_params)
            params["path"] = path_params
        if self.api_object.query_params:
            query_params = unstructure(self.api_object.query_params)
            params["query"] = query_params
        return params

    def prepare_request_body(self) -> dict:
        if not self.api_object.request_model:
            return {}
        request_body = unstructure(self.api_object.request_model)
        request_body = self._remove_nones(request_body)
        return request_body

    def prepare_files(self) -> dict:
        if hasattr(self.api_object, 'files') and self.api_object.files:
            return self.api_object.files
        return {}

    def _remove_nones(self, obj):
        if isinstance(obj, dict):
            return {k: self._remove_nones(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._remove_nones(v) for v in obj if v is not None]
        elif has(obj):  # Check if it's an attrs class
            return self._remove_nones(asdict(obj))
        else:
            return obj
