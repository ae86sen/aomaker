import pytest
from aomaker.core.request_builder import (
    JSONRequestBuilder,
    FormURLEncodedRequestBuilder,
    MultipartFormDataRequestBuilder,
    TextPlainRequestBuilder,
)
from aomaker.core.base_model import (
    PreparedRequest,
    JSONRequest,
    FormURLEncodedRequest,
    MultipartFormDataRequest,
    TextPlainRequest,
)


def test_json_request_builder_full_fields():
    """测试 JSONRequestBuilder 使用完整字段构造请求"""
    pr = PreparedRequest(
        method="POST",
        url="/api/json",
        headers={"h": "v"},
        params={"p": 1},
        request_body={"a": 1},
        files={"f": "ignored"},
    )
    builder = JSONRequestBuilder()
    req = builder.build_request(pr)
    # 验证返回类型和字段映射
    assert isinstance(req, JSONRequest)
    assert req.method == "POST"
    assert req.url == "/api/json"
    assert req.headers == {"h": "v"}
    assert req.params == {"p": 1}
    assert req.json == {"a": 1}


def test_json_request_builder_with_none_body():
    """测试 JSONRequestBuilder 当 request_body 为 None 时，json 字段为 None"""
    pr = PreparedRequest(
        method="GET",
        url="/api/json_none",
        headers={},
        params=None,
        request_body=None,
        files=None,
    )
    builder = JSONRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, JSONRequest)
    assert req.params is None
    assert req.json is None


def test_form_urlencoded_builder_full_fields():
    """测试 FormURLEncodedRequestBuilder 使用完整字段构造请求"""
    pr = PreparedRequest(
        method="PUT",
        url="/api/form",
        headers={"h2": "v2"},
        params={"q": "test"},
        request_body={"field": "value"},
        files=None,
    )
    builder = FormURLEncodedRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, FormURLEncodedRequest)
    assert req.method == "PUT"
    assert req.url == "/api/form"
    assert req.headers == {"h2": "v2"}
    assert req.params == {"q": "test"}
    assert req.data == {"field": "value"}


def test_form_urlencoded_builder_with_none_body():
    """测试 FormURLEncodedRequestBuilder 当 request_body 为 None 时，data 字段为 None"""
    pr = PreparedRequest(
        method="POST",
        url="/api/form_none",
        headers={},
        params=None,
        request_body=None,
        files=None,
    )
    builder = FormURLEncodedRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, FormURLEncodedRequest)
    assert req.data is None


def test_multipart_form_data_builder_full_fields():
    """测试 MultipartFormDataRequestBuilder 使用完整字段构造请求"""
    pr = PreparedRequest(
        method="PATCH",
        url="/api/multipart",
        headers={"h3": "v3"},
        params={"page": 2},
        request_body={"key": "val"},
        files={"file1": b"bytes_val"},
    )
    builder = MultipartFormDataRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, MultipartFormDataRequest)
    assert req.method == "PATCH"
    assert req.url == "/api/multipart"
    assert req.headers == {"h3": "v3"}
    assert req.params == {"page": 2}
    assert req.data == {"key": "val"}
    assert req.files == {"file1": b"bytes_val"}


def test_multipart_form_data_builder_with_none_fields():
    """测试 MultipartFormDataRequestBuilder 当 request_body 和 files 为 None 时，字段为 None"""
    pr = PreparedRequest(
        method="DELETE",
        url="/api/multipart_none",
        headers={},
        params=None,
        request_body=None,
        files=None,
    )
    builder = MultipartFormDataRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, MultipartFormDataRequest)
    assert req.data is None
    assert req.files is None


def test_text_plain_builder_full_fields():
    """测试 TextPlainRequestBuilder 使用完整字段构造请求"""
    pr = PreparedRequest(
        method="DELETE",
        url="/api/text",
        headers={"h4": "v4"},
        params={"flag": True},
        request_body="plain text body",
        files=None,
    )
    builder = TextPlainRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, TextPlainRequest)
    assert req.method == "DELETE"
    assert req.url == "/api/text"
    assert req.headers == {"h4": "v4"}
    assert req.params == {"flag": True}
    assert req.data == "plain text body"


def test_text_plain_builder_with_none_body():
    """测试 TextPlainRequestBuilder 当 request_body 为 None 时，data 字段为 None"""
    pr = PreparedRequest(
        method="GET",
        url="/api/text_none",
        headers={},
        params=None,
        request_body=None,
        files=None,
    )
    builder = TextPlainRequestBuilder()
    req = builder.build_request(pr)
    assert isinstance(req, TextPlainRequest)
    assert req.data is None


@pytest.mark.parametrize("builder", [
    JSONRequestBuilder(),
    FormURLEncodedRequestBuilder(),
    MultipartFormDataRequestBuilder(),
    TextPlainRequestBuilder(),
])
def test_builder_with_invalid_input_raises_attribute_error(builder):
    """测试当传入非 PreparedRequest 时，抛出 AttributeError"""
    with pytest.raises(AttributeError):
        builder.build_request(None) 