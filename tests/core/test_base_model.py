import pytest
from attrs import asdict
from attrs.exceptions import FrozenInstanceError
from unittest.mock import Mock

from aomaker.core.base_model import (
    HTTPMethod,
    ContentType,
    BaseHTTPRequest,
    JSONRequest,
    FormURLEncodedRequest,
    MultipartFormDataRequest,
    TextPlainRequest,
    EndpointConfig,
    PreparedRequest,
    AoResponse,
)

# 1. 枚举测试
def test_http_method_enum():
    assert HTTPMethod.GET.value == "GET"
    assert HTTPMethod.POST.value == "POST"
    assert HTTPMethod.PUT.value == "PUT"
    assert HTTPMethod.DELETE.value == "DELETE"
    assert HTTPMethod.PATCH.value == "PATCH"


def test_content_type_enum():
    assert ContentType.JSON.value == "application/json"
    assert ContentType.FORM.value == "application/x-www-form-urlencoded"
    assert ContentType.MULTIPART.value == "multipart/form-data"
    assert ContentType.TEXT.value == "text/plain"

# 2. 请求模型默认值测试
def test_default_base_http_request():
    req = BaseHTTPRequest()
    assert req.url == ""
    assert req.method == ""
    assert req.headers == {}
    assert req.params is None


def test_default_json_request():
    req = JSONRequest()
    assert isinstance(req, BaseHTTPRequest)
    assert req.json == {}


def test_default_form_urlencoded_request():
    req = FormURLEncodedRequest()
    assert isinstance(req, BaseHTTPRequest)
    assert req.data == {}


def test_default_multipart_form_data_request():
    req = MultipartFormDataRequest()
    assert isinstance(req, BaseHTTPRequest)
    assert req.files == {}
    assert req.data == {}


def test_default_text_plain_request():
    req = TextPlainRequest()
    assert isinstance(req, BaseHTTPRequest)
    assert req.data == ""

# 3. 请求模型自定义参数测试
def test_custom_json_request_fields():
    headers = {"h": "v"}
    params = {"p": 1}
    body = {"a": 1}
    req = JSONRequest(url="/api", method="POST", headers=headers, params=params, json=body)
    assert req.url == "/api"
    assert req.method == "POST"
    assert req.headers == headers
    assert req.params == params
    assert req.json == body


def test_custom_form_urlencoded_request_fields():
    data = {"x": "y"}
    req = FormURLEncodedRequest(url="/u", method="PUT", headers={"h": "v"}, data=data)
    assert req.data == data


def test_custom_multipart_form_data_request_fields():
    files = {"f": b"bytes"}
    data = {"k": "v"}
    req = MultipartFormDataRequest(url="/m", method="PATCH", headers={"h": "v"}, files=files, data=data)
    assert req.files == files
    assert req.data == data


def test_custom_text_plain_request_fields():
    text = "hello"
    req = TextPlainRequest(url="/t", method="DELETE", headers={"h": "v"}, data=text)
    assert req.data == text

# 4. EndpointConfig 测试
def test_endpoint_config_default():
    cfg = EndpointConfig()
    assert cfg.route == ""
    assert cfg.method == ""
    assert cfg.route_params is None


def test_endpoint_config_custom():
    cfg = EndpointConfig(route="/test", method=HTTPMethod.DELETE, route_params=["id"])
    assert cfg.route == "/test"
    assert cfg.method == HTTPMethod.DELETE
    assert cfg.route_params == ["id"]

# 5. PreparedRequest 测试
def test_prepared_request_init_and_immutable():
    pr = PreparedRequest(method="POST", url="/u", headers={"h": "v"})
    assert pr.method == "POST"
    assert pr.url == "/u"
    assert pr.headers == {"h": "v"}
    assert pr.params is None
    assert pr.request_body is None
    assert pr.files is None

    with pytest.raises(FrozenInstanceError):
        pr.method = "GET"

# 6. AoResponse 流处理测试
def make_fake_response(data, method_name):
    """
    创建一个模拟 raw_response，迭代方法(method_name)返回 data 列表，并记录 close 调用
    """
    raw = Mock()
    setattr(raw, method_name, Mock(return_value=data))
    raw.close = Mock()
    fake_cached = Mock()
    fake_cached.raw_response = raw
    return raw, fake_cached


def test_process_stream_not_stream():
    raw, fake_cached = make_fake_response([], 'iter_lines')
    ao = AoResponse(cached_response=fake_cached)
    ao.is_stream = False
    with pytest.raises(ValueError):
        ao.process_stream()


def test_process_stream_no_callback():
    raw, fake_cached = make_fake_response([], 'iter_content')
    ao = AoResponse(cached_response=fake_cached, is_stream=True)
    result = ao.process_stream()
    assert result is ao
    raw.close.assert_not_called()


def test_process_stream_lines():
    data = [b'l1', b'', b'l2']
    raw, fake_cached = make_fake_response(data, 'iter_lines')
    ao = AoResponse(cached_response=fake_cached, is_stream=True)
    called = []
    result = ao.process_stream(stream_mode='lines', callback=called.append)
    assert result is ao
    assert called == [b'l1', b'l2']
    raw.close.assert_called_once()


def test_process_stream_json():
    data = [{'a': 1}, None, {'b': 2}]
    raw, fake_cached = make_fake_response(data, 'iter_json')
    ao = AoResponse(cached_response=fake_cached, is_stream=True)
    called = []
    result = ao.process_stream(stream_mode='json', callback=called.append)
    assert called == [{'a': 1}, {'b': 2}]
    raw.close.assert_called_once()


def test_process_stream_content():
    data = [b'c1', b'', b'c2']
    raw, fake_cached = make_fake_response(data, 'iter_content')
    ao = AoResponse(cached_response=fake_cached, is_stream=True)
    called = []
    result = ao.process_stream(stream_mode=None, callback=called.append)
    assert called == [b'c1', b'c2']
    raw.close.assert_called_once()

# 7. attrs 序列化测试
def test_attrs_asdict():
    req = JSONRequest(url='/u', method='GET', headers={'h': 'v'}, params={'p': 3}, json={'j': 4})
    d = asdict(req)
    assert d == {'url': '/u', 'method': 'GET', 'headers': {'h': 'v'}, 'params': {'p': 3}, 'json': {'j': 4}} 