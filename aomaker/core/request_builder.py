# --coding:utf-8--
from abc import ABC, abstractmethod

from .base_model import JSONRequest, FormURLEncodedRequest, MultipartFormDataRequest, BaseHTTPRequest,HTTPMethod


class RequestBuilder(ABC):
    @abstractmethod
    def build_request(self, *, url: str, method: str, headers: dict, params: dict = None,
                      request_body: dict = None) -> BaseHTTPRequest:
        pass


class JSONRequestBuilder(RequestBuilder):
    def build_request(self, *, url: str, method: HTTPMethod, headers: dict, params: dict = None,
                      request_body: dict = None) -> JSONRequest:
        return JSONRequest(
            url=url,
            method=method,
            headers=headers,
            params=params,
            json=request_body
        )


class FormURLEncodedRequestBuilder(RequestBuilder):
    def build_request(self, *, url: str, method: HTTPMethod, headers: dict, params: dict = None,
                      request_body: dict = None) -> FormURLEncodedRequest:
        return FormURLEncodedRequest(
            url=url,
            method=method,
            headers=headers,
            params=params,
            data=request_body
        )


class MultipartFormDataRequestBuilder(RequestBuilder):
    def build_request(self, *, url: str, method: HTTPMethod, headers: dict, params: dict = None,
                      request_body: dict = None, files=None) -> MultipartFormDataRequest:
        return MultipartFormDataRequest(
            url=url,
            method=method,
            headers=headers,
            params=params,
            data=request_body,
            files=files
        )
