# --coding:utf-8--
from __future__ import annotations
from enum import Enum
from typing import Dict, List, Any, Optional, TypeVar, Generic, Callable, Union, Iterator

from attrs import define, field

from aomaker.core.http_client import CachedResponse

class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ContentType(str, Enum):
    JSON = "application/json"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"


@define
class BaseHTTPRequest:
    url: str = field(default="")
    method: str = field(default="")
    headers: Dict[str, str] = field(factory=dict)
    params: Optional[Dict[str, Any]] = field(default=None)


@define
class JSONRequest(BaseHTTPRequest):
    json: Optional[Dict[str, Any]] = field(factory=dict)


@define
class FormURLEncodedRequest(BaseHTTPRequest):
    data: Optional[Dict[str, str]] = field(factory=dict)


@define
class MultipartFormDataRequest(BaseHTTPRequest):
    files: Optional[Dict[str, Any]] = field(factory=dict)
    data: Optional[Dict[str, str]] = field(factory=dict)


@define
class TextPlainRequest(BaseHTTPRequest):
    data: str = field(default="")


@define
class EndpointConfig:
    route: str = field(default="")
    method: HTTPMethod = field(default="")
    route_params: List[str] = field(factory=list)


@define(frozen=True)
class PreparedRequest:
    method: str
    url: str
    headers: dict
    params: Optional[dict] = field(default=None)
    request_body: Optional[Union[dict, str]] = field(default=None)
    files: Optional[dict] = field(default=None)


ParametersT = TypeVar("ParametersT", bound=type)
RequestBodyT = TypeVar("RequestBodyT", bound=type)
ResponseT = TypeVar("ResponseT")


@define
class AoResponse(Generic[ResponseT]):
    cached_response: CachedResponse = field()
    response_model: Optional[ResponseT] = field(default=None)
    is_stream: bool = field(default=False)

    def process_stream(self, 
                      stream_mode: Optional[str]=None, 
                      chunk_size: int = 512,
                      decode_unicode: bool = True,
                      callback: Optional[Callable] = None) -> "AoResponse[ResponseT]":
        """
        处理流式响应
        
        Args:
            stream_mode: 流处理模式，可选值：None(原始流)、'lines'、'json'
            chunk_size: 流式处理时每个数据块的大小
            decode_unicode: 是否解码流式响应
            callback: 回调函数，用于处理每个数据块
            
        Returns:
            AoResponse[ResponseT]: 返回自身，支持链式调用
        """
        if not self.is_stream:
            raise ValueError("这不是一个流式响应")
            
        if not callback:
            return self  # 没有回调函数，不处理流
        
        try:
            if stream_mode == 'lines':
                self._process_stream_lines(chunk_size, decode_unicode, callback)
            elif stream_mode == 'json':
                self._process_stream_json(chunk_size, decode_unicode, callback)
            else:
                self._process_stream_content(chunk_size, decode_unicode, callback)
        finally:
            self.cached_response.raw_response.close()
            
        return self  # 返回自身以支持链式调用
    
    def _process_stream_lines(self, chunk_size, decode_unicode, callback):
        for line in self.cached_response.raw_response.iter_lines(chunk_size=chunk_size, decode_unicode=decode_unicode):
            if line:
                callback(line)
    
    def _process_stream_json(self, chunk_size, decode_unicode, callback):
        for json_obj in self.cached_response.raw_response.iter_json(chunk_size=chunk_size, decode_unicode=decode_unicode):
            if json_obj:
                callback(json_obj)
    
    def _process_stream_content(self, chunk_size, decode_unicode, callback):
        for chunk in self.cached_response.raw_response.iter_content(chunk_size=chunk_size, decode_unicode=decode_unicode):
            if chunk:
                callback(chunk)

    def first(self) -> Optional[ResponseT]:
        ...

    def filter(self, condition: Callable[[ResponseT], bool]) -> "AoResponse[ResponseT]":
        ...

    def exists(self) -> bool:
        ...
