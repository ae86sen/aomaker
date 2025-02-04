# --coding:utf-8--
from attrs import define, field, has
from aomaker.cache import config, cache
from typing import Union, Type, TYPE_CHECKING, Generic, Optional, List

from .base_model import EndpointConfig, ContentType, _RequestBody_T, _Response_T, _Parameters_T

from .converters import BaseConverter
from .http_client import HTTPClient


# from .middlewares.logging_middleware import logging_middleware
_FIELD_TO_VALIDATE = ("path_params", "query_params", "request_body", "response")
@define(kw_only=True)
class BaseAPIObject:
    base_url: str = field(factory=lambda: config.get("host").rstrip("/"))
    headers: dict = field(factory=lambda: cache.get("headers"))
    path_params: Optional[_Parameters_T] = field(default=None)
    query_params: Optional[_Parameters_T] = field(default=None)
    request_body: Optional[_RequestBody_T] = field(default=None)
    response: Optional[_Response_T] = field(default=None)

    endpoint_config: EndpointConfig = field(default=None)
    content_type: ContentType = field(default=ContentType.JSON)
    http_client: HTTPClient = field(default=None)
    converter: Union[BaseConverter, Type[BaseConverter]] = field(default=None)

    def __attrs_post_init__(self):
        self._validate_field_is_attrs()
        if self.endpoint_config is None:
            self.endpoint_config = getattr(self.__class__, '_endpoint_config', None)
            if self.endpoint_config is None:
                raise ValueError("endpoint_config is not set in the class or instance.")
        if self.http_client is None:
            self.http_client = HTTPClient()
        if self.converter is None:
            self.converter = BaseConverter(api_object=self)
        elif isinstance(self.converter, type):
            self.converter = self.converter(api_object=self)

    def _validate_field_is_attrs(self):
        for field_name in _FIELD_TO_VALIDATE:
            field_ = getattr(self, field_name)
            if field_ is not None and not has(field_):
                raise TypeError(f"{field_name} must be an attrs instance")

    def send(self):
        req = self.converter.convert()
        res = self.http_client.send_request(request=req)
        return res
