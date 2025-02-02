# --coding:utf-8--
from attrs import define, field
from aomaker.cache import config, cache
from typing import Union, Type, TYPE_CHECKING

from .base_model import EndpointConfig, BaseResponseModel, BaseRequestModel, ContentType, Parameters

from .converters import BaseConverter
from .http_client import HTTPClient
# from .middlewares.logging_middleware import logging_middleware
import v2.middlewares as mw

@define(kw_only=True)
class BaseAPIObject:
    base_url: str = field(default=config.get("host").rstrip("/"))
    headers: dict = field(default=cache.get("headers"))
    # params: dict = field(default=None)
    path_params: Parameters = field(default=None)
    query_params: Parameters = field(default=None)

    endpoint_config: EndpointConfig = field(default=None)
    request_model: BaseRequestModel = field(default=None)
    response_model: BaseResponseModel = field(default=None)
    content_type: ContentType = field(default=ContentType.JSON)
    http_client: HTTPClient = field(default=None)
    converter: Union[BaseConverter, Type[BaseConverter]] = field(default=None)

    def __attrs_post_init__(self):
        if self.endpoint_config is None:
            self.endpoint_config = getattr(self.__class__, '_endpoint_config', None)
            if self.endpoint_config is None:
                raise ValueError("endpoint_config is not set in the class or instance.")
        if self.http_client is None:
            self.http_client = HTTPClient(middlewares=[mw.logging_middleware.logging_middleware])
        if self.converter is None:
            self.converter = BaseConverter(api_object=self)
        elif isinstance(self.converter, type):
            self.converter = self.converter(api_object=self)

    def send(self):
        req = self.converter.convert()
        res = self.http_client.send_request(request=req)
        return res
