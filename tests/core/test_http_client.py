"""
对 aomaker.core.http_client 模块进行单元测试。
"""
import pytest
from aomaker.core.http_client import HTTPClient, CachedResponse, get_http_client
from aomaker.core.middlewares.registry import registry
from aomaker.storage import cache

class DummyResponse:
    """模拟原始的 HTTP 响应对象"""
    def __init__(self):
        self.json_call_count = 0
        self.status_code = 200
        self.elapsed = 0.0
        self.headers = {}
        self.url = 'http://example.com'
        self.history = []
        self.encoding = 'utf-8'
        self.reason = 'OK'
        self.content = b'{"data": "value"}'
        self.raw = b'{"data": "value"}'

    def json(self, **kwargs):
        # 每次调用统计次数
        self.json_call_count += 1
        return {"data": "value"}


class FakeSession:
    """模拟 requests.Session 对象"""
    def __init__(self):
        self.headers = {}
        self.last_request_kwargs = None

    def request(self, **kwargs):
        # 记录传入的请求参数并返回模拟响应
        self.last_request_kwargs = kwargs
        return DummyResponse()


class ErrorSession:
    """用于测试 send_request 异常处理"""
    def __init__(self):
        self.headers = {}

    def request(self, **kwargs):
        raise ValueError("模拟请求错误")


@pytest.fixture(autouse=True)
def clear_middlewares_and_client(monkeypatch):
    """每个测试自动清空中间件和可复用的单例客户端"""
    # 清空活动中间件
    registry.active_middlewares = []
    # 清理单例
    if hasattr(get_http_client, 'client'):
        delattr(get_http_client, 'client')
    yield


def test_send_request_merges_headers_default():
    client = HTTPClient()
    fake_session = FakeSession()
    fake_session.headers = {'Session-Header': 'S'}
    client.session = fake_session
    request = {'method': 'GET', 'url': 'http://example.com', 'headers': {'Req-Header': 'R'}, '_api_meta': {}}

    response = client.send_request(request)
    print(f"[DEBUG] Response: {response}")

    # 验证返回类型
    assert isinstance(response, CachedResponse)
    # 验证合并 headers
    sent = fake_session.last_request_kwargs
    assert sent['method'] == 'GET'
    assert sent['url'] == 'http://example.com'
    assert sent['headers'] == {'Session-Header': 'S', 'Req-Header': 'R'}


def test_send_request_override_headers_true():
    client = HTTPClient()
    fake_session = FakeSession()
    fake_session.headers = {'Should-Not': 'Appear'}
    client.session = fake_session
    request = {'method': 'POST', 'url': 'http://test', 'headers': {'Only': 'Here'}, '_api_meta': {}}

    response = client.send_request(request, override_headers=True)
    sent = fake_session.last_request_kwargs
    # 验证仅保留传入的 headers
    assert sent['headers'] == {'Only': 'Here'}


def test_send_request_raises_exception():
    client = HTTPClient()
    client.session = ErrorSession()
    request = {'method': 'DELETE', 'url': 'http://fail', '_api_meta': {}}

    with pytest.raises(ValueError) as exc_info:
        client.send_request(request)
    assert '模拟请求错误' in str(exc_info.value)


def test_cached_response_json_and_attribute():
    dummy = DummyResponse()
    dummy.status_code = 404
    cached = CachedResponse(dummy)

    # 测试属性透传
    assert cached.status_code == 404
    # 第一次调用 json
    data1 = cached.json()
    # 第二次调用 json，应该复用缓存
    data2 = cached.json()
    assert data1 == data2
    assert dummy.json_call_count == 1


def test_headers_override_scope_restores_original():
    client = HTTPClient()
    fake_session = FakeSession()
    fake_session.headers = {'A': '1', 'B': '2'}
    client.session = fake_session

    original = fake_session.headers.copy()
    with client.headers_override_scope({'X': 'Y'}):
        assert client.session.headers == {'X': 'Y'}
    # 离开上下文后恢复原始 headers
    assert client.session.headers == original


def test_get_http_client_singleton_and_cache_update(monkeypatch):
    # 模拟 cache.get 返回特定 headers
    monkeypatch.setattr(cache, 'get', lambda key: {'X-Cache': 'CACHED'})

    client1 = get_http_client(HTTPClient)
    client2 = get_http_client(HTTPClient)
    # 验证单例返回
    assert client1 is client2
    # 验证从 cache 更新 headers
    assert client1.session.headers.get('X-Cache') == 'CACHED' 