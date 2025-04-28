# --coding:utf-8--
from __future__ import annotations
from typing import TypeVar, TYPE_CHECKING, Optional, Type, Any
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from uuid import UUID

from attrs import has, define, field
from cattrs import Converter as CattrsConverter

if TYPE_CHECKING:
    from .api_object import BaseAPIObject
from .base_model import ContentType, EndpointConfig, HTTPMethod, ParametersT, PreparedRequest, RequestBodyT
from .request_builder import JSONRequestBuilder, FormURLEncodedRequestBuilder, MultipartFormDataRequestBuilder, \
    RequestBuilder,TextPlainRequestBuilder

REQUEST_BUILDERS = {
    ContentType.JSON: JSONRequestBuilder,
    ContentType.FORM: FormURLEncodedRequestBuilder,
    ContentType.MULTIPART: MultipartFormDataRequestBuilder,
    ContentType.TEXT: TextPlainRequestBuilder
}

T = TypeVar('T')

cattrs_converter = CattrsConverter()


# ===== 结构化钩子（将原始数据转换为对象）=====

# datetime 结构化钩子
def datetime_structure_hook(value, _type):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    elif isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)
    else:
        raise ValueError(f"无法将 {value} 转换为 datetime")


# date 结构化钩子
def date_structure_hook(value, _type):
    if isinstance(value, str):
        return date.fromisoformat(value)
    else:
        raise ValueError(f"无法将 {value} 转换为 date")


# time 结构化钩子
def time_structure_hook(value, _type):
    if isinstance(value, str):
        return time.fromisoformat(value)
    else:
        raise ValueError(f"无法将 {value} 转换为 time")


# 注册结构化钩子
cattrs_converter.register_structure_hook(datetime, datetime_structure_hook)
cattrs_converter.register_structure_hook(date, date_structure_hook)
cattrs_converter.register_structure_hook(time, time_structure_hook)
cattrs_converter.register_structure_hook(UUID, lambda value, _: UUID(value))
cattrs_converter.register_structure_hook(Decimal, lambda value, _: Decimal(str(value)))
cattrs_converter.register_structure_hook(Enum, lambda value, cls: cls(value))

# ===== 反结构化钩子（将对象转换为可序列化数据）=====

# 注册反结构化钩子
cattrs_converter.register_unstructure_hook(
    datetime,
    lambda dt: dt.isoformat() if dt else None
)
cattrs_converter.register_unstructure_hook(
    date,
    lambda d: d.isoformat() if d else None
)
cattrs_converter.register_unstructure_hook(
    time,
    lambda t: t.isoformat() if t else None
)
cattrs_converter.register_unstructure_hook(
    UUID,
    lambda uuid_obj: str(uuid_obj) if uuid_obj else None
)
cattrs_converter.register_unstructure_hook(
    Decimal,
    lambda dec: str(dec) if dec else None
)
cattrs_converter.register_unstructure_hook(
    Enum,
    lambda enum_obj: enum_obj.value if enum_obj else None
)


@define
class RequestConverter:
    api_object: BaseAPIObject = field(default=None)
    _converter: CattrsConverter = field(default=cattrs_converter)

    def convert(self) -> dict:
        request_data = self.prepare()
        builder = self.get_request_builder()
        req = builder.build_request(request_data)
        unstructured_req = self._serialize_data(req)
        return unstructured_req

    def unstructure(self, data: Any) -> Any:
        """结构化数据 -> 原始数据"""
        return self._converter.unstructure(data)

    def structure(self, data: Any, type_: Type[T]) -> Any:
        """原始数据 -> 结构化数据"""
        return self._converter.structure(data, type_)

    def get_request_builder(self) -> RequestBuilder:
        builder_class = REQUEST_BUILDERS.get(self.content_type)
        if not builder_class:
            raise ValueError(f"Unsupported content type: {self.content_type}")
        return builder_class()

    @property
    def base_url(self) -> str:
        return self.api_object.base_url

    @property
    def content_type(self) -> ContentType:
        return self.api_object.content_type

    @property
    def endpoint_config(self) -> EndpointConfig:
        return self.api_object.endpoint_config

    @property
    def route(self) -> str:
        route = self._replace_route_params(self.endpoint_config.route).lstrip("/")
        return route

    def post_prepare(self, prepared_data: PreparedRequest) -> PreparedRequest:
        """子类可重写此方法对最终请求数据进行调整"""
        return prepared_data

    def prepare(self) -> PreparedRequest:
        request_data = {
            "method": self.endpoint_config.method.value,
            "url": self.prepare_url(),
            "headers": self.prepare_headers(),
            "params": self.prepare_params(),  # 结构化对象
            "request_body": self.prepare_request_body(),  # 结构化对象
            "files": self.prepare_files() if self.content_type == ContentType.MULTIPART else None,
        }

        unstructured_request_data = self._serialize_data(request_data)
        prepared_request_data = PreparedRequest(**unstructured_request_data)
        return self.post_prepare(prepared_request_data)

    def prepare_url(self) -> str:
        base_url = self.base_url
        return f"{base_url}/{self.route}"

    def prepare_method(self) -> HTTPMethod:
        method = self.endpoint_config.method.value
        return method

    def prepare_headers(self) -> dict:
        return self.api_object.headers or {}

    def prepare_params(self) -> Optional[ParametersT]:
        return self.api_object.query_params

    def prepare_request_body(self) -> Optional[RequestBodyT]:
        return self.api_object.request_body

    def prepare_files(self) -> dict:
        if hasattr(self.api_object, 'files') and self.api_object.files:
            return self.api_object.files
        return {}

    def _replace_route_params(self, route: str) -> str:
        # 路由参数替换
        for path_param in (self.endpoint_config.route_params or []):
            if hasattr(self.api_object.path_params, path_param):
                value = getattr(self.api_object.path_params, path_param)
                route = route.replace(f"{{{path_param}}}", str(value))
            else:
                raise ValueError(f"Missing required route parameter: {path_param}")
        return route

    def _serialize_data(self, data):
        """统一解构 + 清理空值"""
        unstructured = self.unstructure(data)
        return self._remove_nones(unstructured)

    def _remove_nones(self, obj):
        if isinstance(obj, dict):
            return {k: self._remove_nones(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._remove_nones(v) for v in obj if v is not None]
        elif has(obj):  # Check if it's an attrs class
            return self._remove_nones(self.unstructure(obj))
        else:
            return obj
