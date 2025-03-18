# --coding:utf-8--
from abc import ABC, abstractmethod

from .base_model import JSONRequest, FormURLEncodedRequest, MultipartFormDataRequest, BaseHTTPRequest, \
    PreparedRequest, TextPlainRequest


class RequestBuilder(ABC):
    @abstractmethod
    def build_request(self, prepared_request: PreparedRequest) -> BaseHTTPRequest:
        pass


class JSONRequestBuilder(RequestBuilder):
    def build_request(self, prepared_request: PreparedRequest) -> JSONRequest:
        return JSONRequest(
            url=prepared_request.url,
            method=prepared_request.method,
            headers=prepared_request.headers,
            params=prepared_request.params,
            json=prepared_request.request_body
        )


class FormURLEncodedRequestBuilder(RequestBuilder):
    def build_request(self, prepared_request: PreparedRequest) -> FormURLEncodedRequest:
        return FormURLEncodedRequest(url=prepared_request.url,
                                     method=prepared_request.method,
                                     headers=prepared_request.headers,
                                     params=prepared_request.params,
                                     data=prepared_request.request_body
                                     )


class MultipartFormDataRequestBuilder(RequestBuilder):
    def build_request(self, prepared_request: PreparedRequest) -> MultipartFormDataRequest:
        return MultipartFormDataRequest(
            url=prepared_request.url,
            method=prepared_request.method,
            headers=prepared_request.headers,
            params=prepared_request.params,
            data=prepared_request.request_body,
            files=prepared_request.files
        )

class TextPlainRequestBuilder(RequestBuilder):
    def build_request(self, prepared_request: PreparedRequest) -> TextPlainRequest:
        return TextPlainRequest(
            url=prepared_request.url,
            method=prepared_request.method,
            headers=prepared_request.headers,
            params=prepared_request.params,
            data=prepared_request.request_body
        )