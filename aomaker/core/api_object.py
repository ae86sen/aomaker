# --coding:utf-8--
from typing import Union, Type, Generic, Optional, Dict, Any

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
    base_url: str = field(factory=lambda: config.get("base_url").rstrip("/"))
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

    def send(self, 
            override_headers: bool = False,
            stream: bool = False, 
            **request_kwargs) -> AoResponse[ResponseT]:
        """
        发送请求并返回响应
        
        Args:
            override_headers: 是否覆盖默认请求头
            stream: 是否使用流式响应
            **request_kwargs: 其他请求参数
            
        Returns:
            AoResponse[ResponseT]: 包含原始响应对象和解析后的响应模型
        """
        req = self._prepare_request(stream)
        
        cached_response = self.http_client.send_request(
            request=req, 
            override_headers=override_headers, 
            **request_kwargs
        )
        
        return self._handle_response(cached_response, stream)
    
    def _handle_response(self, cached_response, stream: bool = False) -> AoResponse[ResponseT]:
        """处理HTTP响应"""
        return AoResponse(
            cached_response=cached_response,
            response_model=self._parse_response(cached_response) if not stream else None,
            is_stream=stream
        )
    
    def _prepare_request(self, is_stream: bool) -> Dict[str, Any]:
        """准备请求数据"""
        req = self.converter.convert()
        req["_api_meta"] = {
            "class_name": self.class_name,
            "class_doc": self.class_doc.strip(),
            "is_streaming": is_stream
        }
        
        if is_stream:
            req["stream"] = True
            
        return req
    
    def _parse_response(self, cached_response) -> ResponseT:
        """解析响应数据"""
        response_data = cached_response.json()
        
        if self.enable_schema_validation and self.response:
            self._validate_response_schema(response_data)
            
        return self.converter.structure(response_data, self.response)
    
    def _validate_response_schema(self, response_data):
        """验证响应数据符合schema"""
        # 获取或更新schema
        schema_name = self.response.__name__
        existing_schema = schema.get_schema(schema_name)
        current_schema = extract_jsonschema(self.response)
        
        # 更新schema缓存
        if not existing_schema or current_schema != existing_schema:
            schema.save_schema(schema_name, current_schema)
            existing_schema = current_schema
            
        # 验证
        self.schema_validate(response_data, existing_schema)
            
    def schema_validate(self, instance, schema):
        """简化的schema验证方法"""
        try:
            validate(instance=instance, schema=schema)
        except ValidationError as e:
            error = best_match(e.context) if e.context else e
            path = ".".join(map(str, error.absolute_path)) if error.absolute_path else "root"
            message = f"{error.message} (path: {path})"
            raise AssertionError(message) from None