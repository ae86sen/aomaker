# --coding:utf-8--
from attrs import define, field, has
from aomaker.cache import config, cache
from typing import Union, Type, TYPE_CHECKING, Generic, Optional, List

from aomaker.schema_manager import SchemaManager
from jsonschema_extractor import extract_jsonschema
from jsonschema import validate

from .base_model import EndpointConfig, ContentType, RequestBodyT, ResponseT, ParametersT, AoResponse

from .converters import RequestConverter
from .http_client import HTTPClient

# from .middlewares.logging_middleware import logging_middleware
_FIELD_TO_VALIDATE = ("path_params", "query_params", "request_body", "response")


@define(kw_only=True)
class BaseAPIObject(Generic[ResponseT]):
    base_url: str = field(factory=lambda: config.get("host").rstrip("/"))
    headers: dict = field(factory=lambda: cache.get("headers"))
    path_params: Optional[ParametersT] = field(default=None)
    query_params: Optional[ParametersT] = field(default=None)
    request_body: Optional[RequestBodyT] = field(default=None)
    response: Optional[Type[ResponseT]] = field(default=None)

    endpoint_id: Optional[str] = field(default=None)
    endpoint_config: EndpointConfig = field(default=None)
    content_type: ContentType = field(default=ContentType.JSON)
    http_client: HTTPClient = field(default=None)
    converter: Union[RequestConverter, Type[RequestConverter]] = field(default=None)
    enable_schema_validation: bool = field(default=True)

    def __attrs_post_init__(self):
        self._validate_field_is_attrs()
        if self.endpoint_config is None:
            self.endpoint_config = getattr(self.__class__, '_endpoint_config', None)
            if self.endpoint_config is None:
                raise ValueError("endpoint_config is not set in the class or instance.")
        if self.http_client is None:
            self.http_client = HTTPClient()
        if self.converter is None:
            self.converter = RequestConverter(api_object=self)
        elif isinstance(self.converter, type):
            self.converter = self.converter(api_object=self)

    def _validate_field_is_attrs(self):
        for field_name in _FIELD_TO_VALIDATE:
            field_ = getattr(self, field_name)
            if field_ is not None and not has(field_):
                raise TypeError(f"{field_name} must be an attrs instance")

    @property
    def class_name(self):
        return self.__class__.__name__

    @property
    def class_doc(self):
        return self.__class__.__doc__ or ""

    def send(self) -> AoResponse[ResponseT]:
        req = self.converter.convert()

        req["_api_meta"] = {
            "class_name": self.class_name,
            "class_doc": self.class_doc.strip()
        }

        raw_response = self.http_client.send_request(request=req)
        response_data = raw_response.json()

        if self.enable_schema_validation:
            # 获取schema
            schema_manager = SchemaManager()
            existing_schema = schema_manager.get_schema(self)

            if not existing_schema and self.response:
                # 自动生成并存储
                new_schema = extract_jsonschema(self.response)
                schema_manager.save_schema(self, new_schema)
                existing_schema = new_schema

            # 执行校验
            if existing_schema:
                validate(instance=response_data, schema=existing_schema)

        response_model: ResponseT = self.converter.structure(response_data, self.response)
        return AoResponse(raw_response, response_model)
