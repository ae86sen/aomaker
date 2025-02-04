# --coding:utf-8--
from __future__ import annotations
from attrs import define, field
from enum import Enum
from typing import Dict, List, Any, Optional, TypeVar


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


_Parameters_T = TypeVar("_Parameters_T", bound=type)
_RequestBody_T = TypeVar("_RequestBody_T", bound=type)
_Response_T = TypeVar("_Response_T", bound=type)
