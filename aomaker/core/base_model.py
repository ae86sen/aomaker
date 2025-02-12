# --coding:utf-8--
from __future__ import annotations
import requests
from attrs import define, field
from enum import Enum
from typing import Dict, List, Any, Optional, TypeVar, Generic,Callable


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
    params: Dict[str, Any] = field(default=None)
    data: Optional[Dict[str, Any]] = field(default=None)
    json: Optional[Dict[str, Any]] = field(default=None)
    files: Optional[Dict[str, Any]] = field(default=None)


@define
class JSONRequest(BaseHTTPRequest):
    json: Dict[str, Any] = field(factory=dict)


@define
class FormURLEncodedRequest(BaseHTTPRequest):
    data: Dict[str, str] = field(factory=dict)


@define
class MultipartFormDataRequest(BaseHTTPRequest):
    files: Dict[str, Any] = field(factory=dict)
    data: Dict[str, str] = field(factory=dict)


@define
class EndpointConfig:
    route: str = field(default="")
    method: HTTPMethod = field(default="")
    route_params: List[str] = field(default=None)
    backend_prefix: Optional[str] = field(default=None)
    frontend_prefix: Optional[str] = field(default=None)


@define(frozen=True)
class PreparedRequest:
    method: str
    url: str
    headers: dict
    params: Optional[dict] = field(default=None)
    request_body: Optional[dict] = field(default=None)
    files: Optional[dict] = field(default=None)


ParametersT = TypeVar("ParametersT", bound=type)
RequestBodyT = TypeVar("RequestBodyT", bound=type)
ResponseT = TypeVar("ResponseT")


@define
class AoResponse(Generic[ResponseT]):
    raw_response: requests.Response = field()
    response_model: ResponseT = field()

    def first(self) -> Optional[ResponseT]:
        ...

    def filter(self, condition: Callable[[ResponseT], bool]) -> "AoResponse[ResponseT]":
        ...

    def exists(self) -> bool:
        ...
