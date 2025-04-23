# tests/core/test_api_object.py
import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import Optional, Type
from attrs import define, field, has
from jsonschema import ValidationError
import re

from aomaker.core.api_object import BaseAPIObject
from aomaker.core.base_model import EndpointConfig, ContentType, AoResponse
from aomaker.core.http_client import HTTPClient
from aomaker.core.converters import RequestConverter

# --- 准备一些模拟数据和类 ---

@define
class DummyParams:
    param1: str = field(default="value1")

@define
class DummyRequestBody:
    data: int = field(default=123)

@define
class DummyResponse:
    result: str = field(default="ok")
    code: int = field(default=0)


# 模拟的 EndpointConfig
MOCK_ENDPOINT_CONFIG = EndpointConfig(route="/test/endpoint", method="POST")

# 模拟的 HTTPClient
class MockHTTPClient(HTTPClient):
    def __init__(self, *args, **kwargs):
        self.send_request = MagicMock()

# 模拟的 RequestConverter
class MockRequestConverter(RequestConverter):
    def __init__(self, api_object=None, *args, **kwargs):
        self.api_object = api_object
        self.convert = MagicMock(return_value={})
        self.structure = MagicMock()


# --- 测试开始 ---

# 标记模块，方便分组运行
pytestmark = pytest.mark.core

# Helper fixture to mock config.get consistently
@pytest.fixture(autouse=True)
def mock_config_get(monkeypatch):
    """Mocks config.get to handle base_url and run_mode."""
    config_values = {
        "base_url": "http://mock-base-url/",
        "run_mode": "main", # Provide a default valid run_mode
        "headers": {}, # Provide default headers if needed by get_http_client
    }
    mock_get = MagicMock(side_effect=lambda key, default=None: config_values.get(key, default))
    monkeypatch.setattr("aomaker.storage.config.get", mock_get)
    cache_values = {
        "headers": {} # Mock cache get for headers
    }
    mock_cache_get = MagicMock(side_effect=lambda key, default=None: cache_values.get(key, default))
    monkeypatch.setattr("aomaker.storage.cache.get", mock_cache_get)

    return mock_get # Return the mock if tests need to assert calls on it


# 测试 BaseAPIObject 的初始化
class TestBaseAPIObjectInit:

    @pytest.fixture(autouse=True)
    def mock_client(self, monkeypatch):
        """ Mock only the http_client retrieval for this class """
        # Mock get_http_client
        self.mock_http_client_instance = MockHTTPClient()
        mock_get_http_client = MagicMock(return_value=self.mock_http_client_instance)
        monkeypatch.setattr("aomaker.core.api_object.get_http_client", mock_get_http_client)
        self.mock_get_http_client = mock_get_http_client


    def test_init_defaults(self, mock_config_get): # Inject the shared mock
        """测试默认初始化"""
        class MyAPI(BaseAPIObject[DummyResponse]):
            _endpoint_config = MOCK_ENDPOINT_CONFIG # 类属性设置

        api = MyAPI()

        assert api.base_url == "http://mock-base-url" # 检查末尾斜杠是否被移除
        assert api.headers == {}
        assert api.path_params is None
        assert api.query_params is None
        assert api.request_body is None
        assert api.response is None # Default value for the field is None
        assert api.endpoint_id is None
        assert api.endpoint_config == MOCK_ENDPOINT_CONFIG
        assert api.content_type == ContentType.JSON
        assert api.http_client == self.mock_http_client_instance
        assert isinstance(api.converter, RequestConverter)
        assert api.enable_schema_validation is True

        mock_config_get.assert_any_call("base_url")
        self.mock_get_http_client.assert_called_once_with(default_client=HTTPClient)

    def test_init_with_values(self):
        """测试传入自定义值进行初始化"""
        custom_headers = {"X-Test": "value"}
        path_params = DummyParams()
        query_params = DummyParams(param1="query_val")
        request_body = DummyRequestBody(data=456)
        response_model = DummyResponse

        mock_converter_instance = MockRequestConverter()


        mock_client_instance = MockHTTPClient()

        api = BaseAPIObject[response_model](
            base_url="http://custom-url/", 
            headers=custom_headers,
            path_params=path_params,
            query_params=query_params,
            request_body=request_body,
            response=response_model, # 传入响应模型类型
            endpoint_config=MOCK_ENDPOINT_CONFIG, # 实例属性优先于类属性
            content_type=ContentType.FORM,
            http_client=mock_client_instance, # 传入客户端实例
            converter=mock_converter_instance, # 传入转换器实例
            enable_schema_validation=False
        )

        assert api.base_url == "http://custom-url" # Check rstrip happened
        assert api.headers == custom_headers
        assert api.path_params == path_params
        assert api.query_params == query_params
        assert api.request_body == request_body
        assert api.response == response_model
        assert api.endpoint_config == MOCK_ENDPOINT_CONFIG
        assert api.content_type == ContentType.FORM
        assert api.http_client == mock_client_instance
        assert api.converter is mock_converter_instance # Check instance equality
        assert api.enable_schema_validation is False

    def test_init_missing_endpoint_config(self):
        """测试缺少 endpoint_config 时抛出 ValueError"""
        with pytest.raises(ValueError, match="endpoint_config is not set"):
            with patch('aomaker.core.api_object.get_http_client', return_value=MockHTTPClient()):
                 BaseAPIObject()


    def test_init_endpoint_config_from_class(self):
        """测试从类属性获取 endpoint_config"""
        with patch('aomaker.core.api_object.get_http_client', return_value=MockHTTPClient()):
            class APIWithClassConfig(BaseAPIObject):
                _endpoint_config = MOCK_ENDPOINT_CONFIG
            api = APIWithClassConfig()
            assert api.endpoint_config == MOCK_ENDPOINT_CONFIG

    def test_init_converter_instance(self):
        """测试传入自定义 converter 实例"""
        custom_converter_instance = MockRequestConverter(api_object=None)

        with patch('aomaker.core.api_object.get_http_client', return_value=MockHTTPClient()):
            class MyAPI(BaseAPIObject):
                 _endpoint_config = MOCK_ENDPOINT_CONFIG

            api = MyAPI(converter=custom_converter_instance)
            assert api.converter is custom_converter_instance


# 测试字段类型校验
class TestFieldValidation:

    @pytest.fixture
    def api_instance(self, monkeypatch):
        """提供一个基本的API实例, mocking dependencies."""
        monkeypatch.setattr("aomaker.core.api_object.get_http_client", MagicMock(return_value=MockHTTPClient()))
        class MyAPI(BaseAPIObject):
            _endpoint_config = MOCK_ENDPOINT_CONFIG
        return MyAPI()


    @pytest.mark.parametrize("field_name", [
        "path_params",
        "query_params",
        "request_body",
    ])
    def test_validate_attrs_instance_ok(self, api_instance, field_name):
        """测试字段是 attrs 实例时通过校验 (校验发生在post_init)"""
        valid_value = DummyRequestBody() if field_name == "request_body" else DummyParams()
        setattr(api_instance, field_name, valid_value)
        try:
            api_instance._validate_field_is_attrs()
        except TypeError:
            pytest.fail(f"Field {field_name} with attrs instance raised TypeError unexpectedly.")


    @pytest.mark.parametrize("field_name, invalid_value", [
        ("path_params", {"key": "value"}), # dict 不是 attrs 实例
        ("query_params", [1, 2, 3]),       # list 不是 attrs 实例
        ("request_body", "plain string"), # str 不是 attrs 实例
    ])
    def test_validate_non_attrs_instance_fail(self, field_name, invalid_value, monkeypatch):
        """测试字段不是 attrs 实例时抛出 TypeError"""
        # Mock http client for initialization attempt
        monkeypatch.setattr("aomaker.core.api_object.get_http_client", MagicMock(return_value=MockHTTPClient()))
        # 尝试使用非 attrs 实例初始化
        kwargs = {
            "endpoint_config": MOCK_ENDPOINT_CONFIG,
            field_name: invalid_value
        }
        # 因为校验发生在 __attrs_post_init__，所以在初始化时就应该报错
        with pytest.raises(TypeError, match=f"{field_name} must be an attrs instance"):
            BaseAPIObject(**kwargs) # type: ignore

    def test_validate_response_field_is_type_or_none(self, monkeypatch):
        """测试 response 字段允许是类型或 None"""
        monkeypatch.setattr("aomaker.core.api_object.get_http_client", MagicMock(return_value=MockHTTPClient()))

        class MyAPI(BaseAPIObject[DummyResponse]): # 指定了泛型
            _endpoint_config = MOCK_ENDPOINT_CONFIG

        try:
            # 1. 初始化时不提供 response，默认为 None (field default is None)
            api1 = MyAPI() # Uses default response=None
            api1._validate_field_is_attrs() # Should pass validation

            # 2. 初始化时提供 response 类型
            api2 = MyAPI(response=DummyResponse) # Pass the type
            api2._validate_field_is_attrs() # Should pass validation


        except TypeError:
            pytest.fail("Response field validation failed unexpectedly.")


# 测试属性访问器
class TestProperties:
    @pytest.fixture(autouse=True)
    def mock_properties_deps(self, monkeypatch):
         monkeypatch.setattr("aomaker.core.api_object.get_http_client", MagicMock(return_value=MockHTTPClient()))

    class APIDocTest(BaseAPIObject):
        """This is a test docstring."""
        _endpoint_config = MOCK_ENDPOINT_CONFIG

    class APINoDocTest(BaseAPIObject):
        _endpoint_config = MOCK_ENDPOINT_CONFIG

    def test_class_name(self):
        api = self.APIDocTest()
        assert api.class_name == "APIDocTest"

        api_no_doc = self.APINoDocTest()
        assert api_no_doc.class_name == "APINoDocTest"

    def test_class_doc(self):
        api = self.APIDocTest()
        assert api.class_doc == "This is a test docstring."

        api_no_doc = self.APINoDocTest()
        assert api_no_doc.class_doc == "" # 没有 docstring 时返回空字符串


# 测试发送逻辑
class TestSendLogic:

    @pytest.fixture
    def api_instance(self, monkeypatch, mock_config_get) -> BaseAPIObject[DummyResponse]: # Inject shared config mock
        """提供一个配置好的 API 实例，并 mock 依赖"""

        mock_schema_value = {"type": "object", "properties": {"result": {"type": "string"}, "code": {"type": "integer"}}, "required": ["result", "code"]}
        self.mock_extract_schema = MagicMock(return_value=mock_schema_value)
        monkeypatch.setattr("aomaker.core.api_object.extract_jsonschema", self.mock_extract_schema)

        mock_schema_storage = MagicMock()
        mock_schema_storage.get_schema.return_value = None 
        mock_schema_storage.save_schema = MagicMock()
        monkeypatch.setattr("aomaker.core.api_object.schema", mock_schema_storage)
        self.mock_schema_storage = mock_schema_storage


        self.mock_validate = MagicMock() # 默认验证通过
        monkeypatch.setattr("aomaker.core.api_object.validate", self.mock_validate)



        self.mock_http_client = MockHTTPClient()
        self.mock_converter = MockRequestConverter() 

        monkeypatch.setattr("aomaker.core.api_object.get_http_client", MagicMock(return_value=self.mock_http_client))


        class MySendAPI(BaseAPIObject[DummyResponse]):
            _endpoint_config = MOCK_ENDPOINT_CONFIG
            response: Optional[Type[DummyResponse]] = field(default=DummyResponse) # 设置响应模型


        api = MySendAPI(
             http_client=self.mock_http_client, # Pass instance
             converter=self.mock_converter      # Pass instance
        )
        self.mock_converter.api_object = api
        api.response = DummyResponse

        return api

    def test_send_successful_no_stream(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试成功发送请求 (非流式)"""
        # 准备 mock 返回值
        mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST", "json": {"data": 1}} # Removed _api_meta for simplicity, tested separately
        api_instance.converter.convert.return_value = mock_prepared_request # type: ignore

        mock_response_json = {"result": "success", "code": 200}
        mock_cached_response = MagicMock(spec=['json', 'status_code', 'headers', 'text', 'content']) # Add spec
        mock_cached_response.json.return_value = mock_response_json
        mock_cached_response.status_code = 200
        api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore

        expected_response_model = DummyResponse(result="success", code=200)
        api_instance.converter.structure.return_value = expected_response_model # type: ignore

        # 调用 send
        ao_response = api_instance.send(override_headers=True, timeout=10)

        # 验证调用顺序和参数
        api_instance.converter.convert.assert_called_once() # type: ignore

        call_args, call_kwargs = api_instance.http_client.send_request.call_args # type: ignore
        sent_request = call_kwargs.get('request') or (call_args[0] if call_args else None) # Get the request dict

        assert sent_request is not None
        assert "_api_meta" in sent_request
        assert sent_request["_api_meta"]["class_name"] == "MySendAPI"
        assert sent_request["_api_meta"]["is_streaming"] is False

        api_instance.http_client.send_request.assert_called_once_with( # type: ignore
            request=sent_request, # Check the actual dict passed
            override_headers=True,
            timeout=10 # 检查额外参数是否传递
        )
        mock_cached_response.json.assert_called_once()
        api_instance.converter.structure.assert_called_once_with(mock_response_json, DummyResponse) # type: ignore

        # 验证 schema 校验 (默认启用)
        self.mock_schema_storage.get_schema.assert_called_once_with("DummyResponse")
        self.mock_extract_schema.assert_called_once_with(DummyResponse)
        # 因为 get_schema 返回 None，所以应该保存
        self.mock_schema_storage.save_schema.assert_called_once_with("DummyResponse", self.mock_extract_schema.return_value)
        self.mock_validate.assert_called_once_with(instance=mock_response_json, schema=self.mock_extract_schema.return_value)


        # 验证返回的 AoResponse
        assert isinstance(ao_response, AoResponse)
        assert ao_response.cached_response == mock_cached_response
        assert ao_response.response_model == expected_response_model
        assert ao_response.is_stream is False

    def test_send_successful_stream(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试成功发送请求 (流式)"""
         # 准备 mock 返回值
        mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST", "json": {"data": 1}}
        api_instance.converter.convert.return_value = mock_prepared_request # type: ignore

        mock_cached_response = MagicMock(spec=['json', 'status_code', 'headers', 'text', 'content', 'iter_content']) # Added spec
        mock_cached_response.json.side_effect = Exception("Should not call json() on stream")
        mock_cached_response.status_code = 200
        api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore

        ao_response = api_instance.send(stream=True)

        # 验证调用
        api_instance.converter.convert.assert_called_once() # type: ignore
        call_args, call_kwargs = api_instance.http_client.send_request.call_args # type: ignore
        actual_request_sent = call_kwargs.get('request') or (call_args[0] if call_args else None)

        assert actual_request_sent is not None
        assert actual_request_sent.get("stream") is True
        assert "_api_meta" in actual_request_sent
        assert actual_request_sent["_api_meta"]["is_streaming"] is True

        api_instance.http_client.send_request.assert_called_once() # type: ignore
        mock_cached_response.json.assert_not_called() # 不应调用 json()
        api_instance.converter.structure.assert_not_called() # type: ignore # 不应调用 structure()

        # 验证 schema 校验未执行
        self.mock_schema_storage.get_schema.assert_not_called()
        self.mock_extract_schema.assert_not_called()
        self.mock_schema_storage.save_schema.assert_not_called()
        self.mock_validate.assert_not_called()

        # 验证返回的 AoResponse
        assert isinstance(ao_response, AoResponse)
        assert ao_response.cached_response == mock_cached_response
        assert ao_response.response_model is None # 流式响应模型为 None
        assert ao_response.is_stream is True

    def test_send_call_dunder(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试 __call__ 方法等同于调用 send"""
        # 使用 patch 监控 send 方法
        with patch.object(api_instance, 'send', wraps=api_instance.send) as mock_send:
             # 准备 mock 返回值 (同 test_send_successful_no_stream)
            mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST"}
            api_instance.converter.convert.return_value = mock_prepared_request # type: ignore
            mock_cached_response = MagicMock(spec=['json', 'status_code'])
            mock_cached_response.json.return_value = {"result": "called", "code": 0}
            mock_cached_response.status_code = 200
            api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore
            expected_response_model = DummyResponse(result="called", code=0)
            api_instance.converter.structure.return_value = expected_response_model # type: ignore

            # 调用 __call__
            ao_response = api_instance(override_headers=True, stream=False)

            # 验证 send 被调用
            mock_send.assert_called_once_with(override_headers=True, stream=False)
            call_args, call_kwargs = mock_send.call_args
            assert call_args == ()
            assert call_kwargs == {'override_headers': True, 'stream': False}

            # 验证返回结果一致
            assert ao_response.response_model == expected_response_model

    def test_send_schema_validation_disabled(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试禁用 schema 验证时跳过校验"""
        api_instance.enable_schema_validation = False # 禁用验证

        # 准备 mock 返回值
        mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST"}
        api_instance.converter.convert.return_value = mock_prepared_request # type: ignore
        mock_response_json = {"result": "no-validate", "code": 1}
        mock_cached_response = MagicMock(spec=['json', 'status_code'])
        mock_cached_response.json.return_value = mock_response_json
        mock_cached_response.status_code = 200
        api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore
        expected_response_model = DummyResponse(result="no-validate", code=1)
        api_instance.converter.structure.return_value = expected_response_model # type: ignore

        # 调用 send
        ao_response = api_instance.send()

        # 验证调用（除了 schema 相关）
        api_instance.converter.convert.assert_called_once() # type: ignore
        api_instance.http_client.send_request.assert_called_once() # type: ignore
        mock_cached_response.json.assert_called_once()
        api_instance.converter.structure.assert_called_once_with(mock_response_json, DummyResponse) # type: ignore

        self.mock_schema_storage.get_schema.assert_not_called()
        self.mock_extract_schema.assert_not_called()
        self.mock_schema_storage.save_schema.assert_not_called()
        self.mock_validate.assert_not_called()

        # 验证结果
        assert ao_response.response_model == expected_response_model

    def test_send_no_response_model_defined(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试 API 对象没有定义 response 模型时跳过解析和校验"""
        api_instance.response = None # 显式设为 None

        # 准备 mock 返回值
        mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST"}
        api_instance.converter.convert.return_value = mock_prepared_request # type: ignore
        mock_response_json = {"message": "raw data"}
        mock_cached_response = MagicMock(spec=['json', 'status_code'])
        mock_cached_response.json.return_value = mock_response_json # 即使有 json，也不解析
        mock_cached_response.status_code = 200
        api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore

        # 调用 send
        ao_response = api_instance.send()

        # 验证调用
        api_instance.converter.convert.assert_called_once() # type: ignore
        api_instance.http_client.send_request.assert_called_once() # type: ignore
        mock_cached_response.json.assert_not_called()


        api_instance.converter.structure.assert_not_called() # type: ignore
        self.mock_schema_storage.get_schema.assert_not_called()
        self.mock_extract_schema.assert_not_called()
        self.mock_schema_storage.save_schema.assert_not_called()
        self.mock_validate.assert_not_called()

        # 验证结果
        assert ao_response.cached_response == mock_cached_response
        assert ao_response.response_model is None
        assert ao_response.is_stream is False

    def test_send_schema_validation_fails(self, api_instance: BaseAPIObject[DummyResponse], monkeypatch):
        """测试 schema 验证失败时抛出 AssertionError"""
        mock_existing_schema = {"type": "object", "properties": {"result": {"type": "string"}, "code": {"type": "integer"}}, "required": ["result", "code"]}
        self.mock_schema_storage.get_schema.return_value = mock_existing_schema

        validation_error = ValidationError(
            "Invalid type for 'code'", 
            validator='type',
            path=['code'],
            schema_path=['properties', 'code', 'type'],
            instance='not-an-int',
            schema={'type': 'integer'},
            validator_value='integer'
        )
        mock_validate_fail = MagicMock(side_effect=validation_error)
        monkeypatch.setattr("aomaker.core.api_object.validate", mock_validate_fail)

        # 准备 mock 返回值
        mock_prepared_request = {"url": "http://test.com/test/endpoint", "method": "POST"}
        api_instance.converter.convert.return_value = mock_prepared_request # type: ignore
        mock_response_json = {"result": "fail", "code": "not-an-int"}
        mock_cached_response = MagicMock(spec=['json', 'status_code'])
        mock_cached_response.json.return_value = mock_response_json
        mock_cached_response.status_code = 200
        api_instance.http_client.send_request.return_value = mock_cached_response # type: ignore

        expected_error_message = '字段 \'code\' 类型应为 \'integer\'，实际值为: "not-an-int" (类型: str).'
        with pytest.raises(AssertionError, match=re.escape(expected_error_message)):
             api_instance.send()

        api_instance.converter.convert.assert_called_once() # type: ignore
        api_instance.http_client.send_request.assert_called_once() # type: ignore
        mock_cached_response.json.assert_called_once()
        self.mock_schema_storage.get_schema.assert_called_once_with("DummyResponse") # type: ignore
        self.mock_extract_schema.assert_called_once_with(DummyResponse)
        self.mock_schema_storage.save_schema.assert_not_called()
        mock_validate_fail.assert_called_once_with(instance=mock_response_json, schema=mock_existing_schema)
        api_instance.converter.structure.assert_not_called() # type: ignore


    def test_send_prepare_request_meta_info(self, api_instance: BaseAPIObject[DummyResponse]):
        """测试 _prepare_request 是否正确添加元信息"""

        send_request_spy = MagicMock(return_value=MagicMock(spec=['json', 'status_code']))
        api_instance.http_client.send_request = send_request_spy # type: ignore
        api_instance.converter.structure = MagicMock() # type: ignore

        # --- Case 1: No Stream ---
        api_instance.send(stream=False)
        send_request_spy.assert_called_once()
        call_args, call_kwargs = send_request_spy.call_args
        prepared_req_no_stream = call_kwargs.get('request') or call_args[0]

        assert prepared_req_no_stream is not None
        meta_no_stream = prepared_req_no_stream.get("_api_meta")

        assert meta_no_stream is not None
        assert meta_no_stream.get("class_name") == "MySendAPI"
        assert meta_no_stream.get("class_doc") == api_instance.class_doc
        assert meta_no_stream.get("is_streaming") is False
        assert prepared_req_no_stream.get("stream") is None # stream key should not be present

        send_request_spy.reset_mock()
        api_instance.converter.convert.reset_mock() # type: ignore

         # --- Case 2: Stream ---
        api_instance.send(stream=True)
        send_request_spy.assert_called_once()
        call_args_stream, call_kwargs_stream = send_request_spy.call_args
        prepared_req_stream = call_kwargs_stream.get('request') or call_args_stream[0]


        assert prepared_req_stream is not None
        meta_stream = prepared_req_stream.get("_api_meta")

        assert meta_stream is not None
        assert meta_stream.get("class_name") == "MySendAPI"
        assert meta_stream.get("class_doc") == api_instance.class_doc
        assert meta_stream.get("is_streaming") is True
        assert prepared_req_stream.get("stream") is True
