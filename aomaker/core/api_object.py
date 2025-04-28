# --coding:utf-8--
import json
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
    http_client: Union[HTTPClient, Type[HTTPClient]] = field(default=None)
    converter: Union[RequestConverter, Type[RequestConverter]] = field(default=None)
    enable_schema_validation: bool = field(default=True)

    def __attrs_post_init__(self):
        self.base_url = self.base_url.rstrip("/")
        self._validate_field_is_attrs()
        if self.endpoint_config is None:
            self.endpoint_config = getattr(self.__class__, '_endpoint_config', None)
            if self.endpoint_config is None:
                raise ValueError("endpoint_config is not set in the class or instance.")
        if self.http_client is None:
            self.http_client = get_http_client(default_client=HTTPClient)
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
        return self.send(*args, **kwargs)

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
        """
        处理 HTTP 响应
        """
        if stream or self.response is None:
            parsed = None
        else:
            parsed = self._parse_response(cached_response)
        return AoResponse(
            cached_response=cached_response,
            response_model=parsed,
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
            message = format_validation_error(error)
            raise AssertionError(message) from None

def format_validation_error(error: ValidationError) -> str:
    path = ".".join(map(str, error.absolute_path)) if error.absolute_path else "root"
    instance_repr = json.dumps(error.instance, ensure_ascii=False, default=str)
    max_repr_len = 50
    if len(instance_repr) > max_repr_len:
        instance_repr = instance_repr[:max_repr_len] + "..."

    validator = error.validator
    validator_value = error.validator_value
    instance = error.instance
    message = error.message

    if validator == "required":
        missing_fields = "', '".join(validator_value)
        if message and "'" in message:
             missing_field = message.split("'")[1]
             return f"字段 '{path}.{missing_field}' 是必需的，但未提供。"
        else:
             return f"路径 '{path}' 缺少必需字段: '{missing_fields}'."

    elif validator == "type":
        expected_type = validator_value
        if isinstance(expected_type, list):
             expected_type = " 或 ".join(expected_type)
        return f"字段 '{path}' 类型应为 '{expected_type}'，实际值为: {instance_repr} (类型: {type(instance).__name__})."

    elif validator == "minLength":
        min_len = validator_value
        return f"字段 '{path}' 长度至少应为 {min_len}，实际值为: {instance_repr} (长度: {len(instance)})."

    elif validator == "maxLength":
        max_len = validator_value
        return f"字段 '{path}' 长度最多应为 {max_len}，实际值为: {instance_repr} (长度: {len(instance)})."

    elif validator == "minimum":
        minimum = validator_value
        return f"字段 '{path}' 的值必须不小于 {minimum}，实际值为: {instance_repr}."

    elif validator == "maximum":
        maximum = validator_value
        return f"字段 '{path}' 的值必须不大于 {maximum}，实际值为: {instance_repr}."

    elif validator == "pattern":
        pattern = validator_value
        return f"字段 '{path}' 需要匹配模式 '{pattern}'，实际值为: {instance_repr}."

    elif validator == "enum":
        allowed_values = ", ".join(map(lambda v: json.dumps(v, ensure_ascii=False), validator_value))
        return f"字段 '{path}' 的值必须是 [{allowed_values}] 中的一个，实际值为: {instance_repr}."

    elif validator == "uniqueItems":
        return f"字段 '{path}' 中的元素必须唯一，实际值为: {instance_repr}."

    elif validator == "format":
        expected_format = validator_value
        return f"字段 '{path}' 应为 '{expected_format}' 格式，实际值为: {instance_repr}."

    elif validator == "minItems":
        min_items = validator_value
        actual_count = len(instance) if isinstance(instance, list) else 'N/A'
        return f"字段 '{path}' (数组) 至少应包含 {min_items} 个元素，实际包含 {actual_count} 个: {instance_repr}."

    elif validator == "maxItems":
        max_items = validator_value
        actual_count = len(instance) if isinstance(instance, list) else 'N/A'
        return f"字段 '{path}' (数组) 最多应包含 {max_items} 个元素，实际包含 {actual_count} 个: {instance_repr}."

    elif validator == "minProperties":
        min_props = validator_value
        actual_count = len(instance) if isinstance(instance, dict) else 'N/A'
        return f"字段 '{path}' (对象) 至少应包含 {min_props} 个属性，实际包含 {actual_count} 个: {instance_repr}."

    elif validator == "maxProperties":
        max_props = validator_value
        actual_count = len(instance) if isinstance(instance, dict) else 'N/A'
        return f"字段 '{path}' (对象) 最多应包含 {max_props} 个属性，实际包含 {actual_count} 个: {instance_repr}."

    elif validator == "multipleOf":
        multiple = validator_value
        return f"字段 '{path}' 的值必须是 {multiple} 的倍数，实际值为: {instance_repr}."

    elif validator == "const":
        const_value = json.dumps(validator_value, ensure_ascii=False)
        return f"字段 '{path}' 的值必须恒等于 {const_value}，实际值为: {instance_repr}."

    elif validator == "not":
        return f"字段 '{path}' 不应满足 'not' 条件指定的模式。实际值为: {instance_repr}. (原始信息: {message})"

    elif validator == "oneOf" or validator == "anyOf":
         sub_errors_str = ""
         if error.context:
              sub_errors_str = "\n  - ".join([format_validation_error(sub_error) for sub_error in error.context])
         return f"字段 '{path}' 未能满足 '{validator}' 条件。最接近的匹配错误: {message}. (实际值: {instance_repr}).\n  可能的子错误:\n  - {sub_errors_str}"

    return f"字段 '{path}' 校验失败 ({validator}): {message}. 实际值为: {instance_repr}."
