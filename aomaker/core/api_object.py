# --coding:utf-8--
from typing import Union, Type, Generic, Optional

from jsonschema_extractor import extract_jsonschema
from jsonschema import validate, ValidationError
from jsonschema.exceptions import best_match
from attrs import define, field, has

from aomaker.storage import config, schema
from .base_model import EndpointConfig, ContentType, RequestBodyT, ResponseT, ParametersT, AoResponse
from .converters import RequestConverter
from .http_client import get_http_client, HTTPClient

# from .middlewares.logging_middleware import logging_middleware
_FIELD_TO_VALIDATE = ("path_params", "query_params", "request_body", "response")


@define(kw_only=True)
class BaseAPIObject(Generic[ResponseT]):
    base_url: str = field(factory=lambda: config.get("host").rstrip("/"))
    headers: dict = field(factory=dict)
    path_params: Optional[ParametersT] = field(default=None)
    query_params: Optional[ParametersT] = field(default=None)
    request_body: Optional[RequestBodyT] = field(default=None)
    response: Optional[Type[ResponseT]] = field(default=None)

    endpoint_id: Optional[str] = field(default=None)
    endpoint_config: EndpointConfig = field(default=None)
    content_type: ContentType = field(default=ContentType.JSON)
    http_client: Union[HTTPClient, Type[HTTPClient]] = field(default=HTTPClient)
    converter: Union[RequestConverter, Type[RequestConverter]] = field(default=None)
    enable_schema_validation: bool = field(default=True)

    def __attrs_post_init__(self):
        self._validate_field_is_attrs()
        if self.endpoint_config is None:
            self.endpoint_config = getattr(self.__class__, '_endpoint_config', None)
            if self.endpoint_config is None:
                raise ValueError("endpoint_config is not set in the class or instance.")
        self.http_client = get_http_client(default_client=self.http_client)
        if self.converter is None:
            self.converter = RequestConverter(api_object=self)
        elif isinstance(self.converter, type):
            self.converter = self.converter(api_object=self)

    def _validate_field_is_attrs(self):
        for field_name in _FIELD_TO_VALIDATE:
            field_ = getattr(self, field_name)
            if field_ is not None and not has(field_):
                raise TypeError(f"{field_name} must be an attrs instance")

    def __call__(self, *args, **kwargs):
        self.send(*args, **kwargs)

    @property
    def class_name(self):
        return self.__class__.__name__

    @property
    def class_doc(self):
        return self.__class__.__doc__ or ""

    def send(self, override_headers: bool = False) -> AoResponse[ResponseT]:
        req = self.converter.convert()

        req["_api_meta"] = {
            "class_name": self.class_name,
            "class_doc": self.class_doc.strip()
        }

        raw_response = self.http_client.send_request(request=req, override_headers=override_headers)
        response_data = raw_response.json()

        if self.enable_schema_validation:

            existing_schema = schema.get_schema(self)

            if not existing_schema and self.response:
                new_schema = extract_jsonschema(self.response)
                schema.save_schema(self, new_schema)
                existing_schema = new_schema

            if existing_schema:
                self.schema_validate(instance=response_data, schema=existing_schema)

        response_model: ResponseT = self.converter.structure(response_data, self.response)
        return AoResponse(raw_response, response_model)

    def schema_validate(self, instance, schema):
        try:
            validate(instance=instance, schema=schema)
        except ValidationError as e:
            if e.context:
                best_error = best_match(e.context)
                if best_error is not None:
                    message = best_error.message
                    error_path = best_error.absolute_path
                else:
                    message = e.message
                    error_path = e.absolute_path
            else:
                message = e.message
                error_path = e.absolute_path

            error_path_str = ".".join(map(str, error_path)) if error_path else "root"

            raise AssertionError(f"{message} (path: {error_path_str})") from None
