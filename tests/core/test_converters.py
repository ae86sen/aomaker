import pytest
from datetime import datetime, date, time, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from unittest.mock import Mock
from typing import Optional
from unittest.mock import patch

from attrs import define, field
from cattrs import Converter

# Assuming converters.py is in aomaker.core
from aomaker.core.converters import (
    cattrs_converter,
    datetime_structure_hook,
    date_structure_hook,
    time_structure_hook,
    RequestConverter,
)
from aomaker.core.base_model import ContentType, EndpointConfig, HTTPMethod, ParametersT, PreparedRequest, RequestBodyT
from aomaker.core.request_builder import JSONRequestBuilder, FormURLEncodedRequestBuilder, MultipartFormDataRequestBuilder, TextPlainRequestBuilder # Need these

# --- Test Data ---

class SampleEnum(Enum):
    VALUE_A = "a"
    VALUE_B = "b"

@define
class NestedModel:
    id: int
    value: str | None = None

@define
class ComplexModel:
    name: str
    timestamp: datetime | None = None
    items: list[NestedModel] | None = None
    flag: bool | None = True
    maybe_present: str | None = None


# --- Tests for Structure Hooks ---

def test_datetime_structure_hook_iso():
    """测试 datetime 结构化钩子 - ISO 格式字符串"""
    dt_str = "2023-10-27T10:30:00+08:00"
    expected_dt = datetime.fromisoformat(dt_str)
    assert datetime_structure_hook(dt_str, datetime) == expected_dt

def test_datetime_structure_hook_timestamp():
    """测试 datetime 结构化钩子 - 时间戳"""
    ts = 1666866600  # Represents 2022-10-27 10:30:00 UTC
    expected_dt = datetime.utcfromtimestamp(ts) # Hook produces naive datetime
    # Hook creates naive datetime from UTC timestamp
    structured_dt = datetime_structure_hook(ts, datetime)
    assert structured_dt == expected_dt

def test_datetime_structure_hook_invalid():
    """测试 datetime 结构化钩子 - 无效输入"""
    with pytest.raises(ValueError, match="无法将"):
        datetime_structure_hook([1, 2, 3], datetime)

def test_date_structure_hook_iso():
    """测试 date 结构化钩子 - ISO 格式字符串"""
    date_str = "2023-10-27"
    expected_date = date.fromisoformat(date_str)
    assert date_structure_hook(date_str, date) == expected_date

def test_date_structure_hook_invalid():
    """测试 date 结构化钩子 - 无效输入"""
    with pytest.raises(ValueError, match="无法将"):
        date_structure_hook(12345, date)

def test_time_structure_hook_iso():
    """测试 time 结构化钩子 - ISO 格式字符串"""
    time_str = "10:30:00"
    expected_time = time.fromisoformat(time_str)
    assert time_structure_hook(time_str, time) == expected_time

def test_time_structure_hook_invalid():
    """测试 time 结构化钩子 - 无效输入"""
    with pytest.raises(ValueError, match="无法将"):
        time_structure_hook(object(), time)

def test_cattrs_structure_uuid():
    """测试 cattrs 对 UUID 的结构化"""
    uuid_obj = uuid4()
    uuid_str = str(uuid_obj)
    assert cattrs_converter.structure(uuid_str, UUID) == uuid_obj

def test_cattrs_structure_decimal():
    """测试 cattrs 对 Decimal 的结构化"""
    dec_str = "123.45"
    expected_dec = Decimal(dec_str)
    assert cattrs_converter.structure(dec_str, Decimal) == expected_dec
    assert cattrs_converter.structure(123.45, Decimal) == expected_dec # From float
    assert cattrs_converter.structure(123, Decimal) == Decimal("123") # From int

def test_cattrs_structure_enum():
    """测试 cattrs 对 Enum 的结构化"""
    assert cattrs_converter.structure("a", SampleEnum) == SampleEnum.VALUE_A
    with pytest.raises(Exception): # cattrs raises different exceptions
         cattrs_converter.structure("c", SampleEnum)


# --- Tests for Unstructure Hooks ---

def test_cattrs_unstructure_datetime():
    """测试 cattrs 对 datetime 的反结构化"""
    dt = datetime(2023, 10, 27, 10, 30, 0, tzinfo=timezone.utc)
    assert cattrs_converter.unstructure(dt) == "2023-10-27T10:30:00+00:00"
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[datetime])) is None

def test_cattrs_unstructure_date():
    """测试 cattrs 对 date 的反结构化"""
    d = date(2023, 10, 27)
    assert cattrs_converter.unstructure(d) == "2023-10-27"
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[date])) is None

def test_cattrs_unstructure_time():
    """测试 cattrs 对 time 的反结构化"""
    t = time(10, 30, 0)
    assert cattrs_converter.unstructure(t) == "10:30:00"
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[time])) is None

def test_cattrs_unstructure_uuid():
    """测试 cattrs 对 UUID 的反结构化"""
    uuid_obj = uuid4()
    assert cattrs_converter.unstructure(uuid_obj) == str(uuid_obj)
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[UUID])) is None

def test_cattrs_unstructure_decimal():
    """测试 cattrs 对 Decimal 的反结构化"""
    dec = Decimal("123.45")
    assert cattrs_converter.unstructure(dec) == "123.45"
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[Decimal])) is None

def test_cattrs_unstructure_enum():
    """测试 cattrs 对 Enum 的反结构化"""
    assert cattrs_converter.unstructure(SampleEnum.VALUE_A) == "a"
    assert cattrs_converter.unstructure(None, cattrs_converter.get_unstructure_hook(Optional[SampleEnum])) is None


# --- Tests for _remove_nones ---

def test_remove_nones_simple_dict():
    """测试 _remove_nones - 简单字典"""
    data = {"a": 1, "b": None, "c": "hello"}
    expected = {"a": 1, "c": "hello"}
    # Need RequestConverter instance to call _remove_nones
    converter = RequestConverter()
    assert converter._remove_nones(data) == expected

def test_remove_nones_nested_dict():
    """测试 _remove_nones - 嵌套字典"""
    data = {"a": 1, "b": {"x": 10, "y": None}, "c": None, "d": {"z": None}}
    expected = {"a": 1, "b": {"x": 10}, "d": {}}
    converter = RequestConverter()
    assert converter._remove_nones(data) == expected

def test_remove_nones_list():
    """测试 _remove_nones - 列表"""
    data = [1, None, "hello", {"a": 1, "b": None}, None, [2, None, 3]]
    expected = [1, "hello", {"a": 1}, [2, 3]]
    converter = RequestConverter()
    assert converter._remove_nones(data) == expected

def test_remove_nones_attrs_object_unstructured():
    """测试 _remove_nones - 已反结构化的 attrs 对象字典"""
    # Simulate the dict after cattrs.unstructure
    unstructured_data = {
        'name': 'test',
        'timestamp': None, # Explicit None from unstructure
        'items': [{'id': 1, 'value': None}, {'id': 2, 'value': 'present'}],
        'flag': True,
        'maybe_present': None
    }
    expected = {
        'name': 'test',
        'items': [{'id': 1}, {'id': 2, 'value': 'present'}],
        'flag': True,
    }
    converter = RequestConverter()
    assert converter._remove_nones(unstructured_data) == expected

def test_remove_nones_empty():
    """测试 _remove_nones - 空输入"""
    converter = RequestConverter()
    assert converter._remove_nones({}) == {}
    assert converter._remove_nones([]) == []
    assert converter._remove_nones(None) is None
    assert converter._remove_nones("") == ""


@define
class MockAPIObject:
    base_url: str = "http://test.com"
    content_type: ContentType = ContentType.JSON
    endpoint_config: EndpointConfig = field(default=EndpointConfig(method=HTTPMethod.GET, route="/ping", route_params=[]))
    headers: dict | None = None
    query_params: ParametersT | None = None
    path_params: dict | None = None # Simple dict for testing _replace_route_params directly
    request_body: RequestBodyT | None = None
    files: dict | None = None

    def __attrs_post_init__(self):
        # 模拟 BaseAPIObject 的行为
        self.base_url = self.base_url.rstrip("/")


@pytest.mark.parametrize(
    "content_type, expected_builder",
    [
        (ContentType.JSON, JSONRequestBuilder),
        (ContentType.FORM, FormURLEncodedRequestBuilder),
        (ContentType.MULTIPART, MultipartFormDataRequestBuilder),
        (ContentType.TEXT, TextPlainRequestBuilder),
    ]
)
def test_get_request_builder_supported(content_type, expected_builder):
    """测试 get_request_builder - 支持的 ContentType"""
    mock_api = MockAPIObject(content_type=content_type)
    converter = RequestConverter(api_object=mock_api)
    builder = converter.get_request_builder()
    assert isinstance(builder, expected_builder)

def test_get_request_builder_unsupported():
    """测试 get_request_builder - 不支持的 ContentType"""
    # Create a dummy content type for testing
    class UnsupportedContentType(Enum):
        YAML = "application/yaml"

    # Temporarily add this to REQUEST_BUILDERS or mock ContentType enum if necessary
    # For now, assume it's not in REQUEST_BUILDERS
    mock_api = MockAPIObject(content_type=UnsupportedContentType.YAML)
    converter = RequestConverter(api_object=mock_api)
    with pytest.raises(ValueError, match="Unsupported content type"):
        converter.get_request_builder()


@define
class PathParamsModel:
    user_id: int
    item_id: str

def test_replace_route_params_success():
    """测试 _replace_route_params - 成功替换"""
    endpoint_config = EndpointConfig(
        method=HTTPMethod.GET,
        route="/users/{user_id}/items/{item_id}",
        route_params=["user_id", "item_id"]
    )
    path_params_obj = PathParamsModel(user_id=123, item_id="abc")
    # Update MockAPIObject definition or instance to include path_params
    mock_api = MockAPIObject(endpoint_config=endpoint_config)
    mock_api.path_params = path_params_obj # Assign directly for this test
    converter = RequestConverter(api_object=mock_api)
    # Access the internal method directly for focused testing
    replaced_route = converter._replace_route_params(converter.endpoint_config.route)
    assert replaced_route == "/users/123/items/abc"

def test_replace_route_params_no_params():
    """测试 _replace_route_params - 路由无参数"""
    endpoint_config = EndpointConfig(
        method=HTTPMethod.GET,
        route="/status",
        route_params=[]
    )
    # Path params obj can be anything or None if no route params expected
    mock_api = MockAPIObject(endpoint_config=endpoint_config, path_params=None)
    converter = RequestConverter(api_object=mock_api)
    replaced_route = converter._replace_route_params(converter.endpoint_config.route)
    assert replaced_route == "/status"

def test_replace_route_params_missing_param():
    """测试 _replace_route_params - 缺少路径参数"""
    endpoint_config = EndpointConfig(
        method=HTTPMethod.GET,
        route="/users/{user_id}/items/{item_id}",
        route_params=["user_id", "item_id"]
    )
    # Missing item_id in the path params object
    @define
    class IncompletePathParams:
        user_id: int
    path_params_obj = IncompletePathParams(user_id=123)
    mock_api = MockAPIObject(endpoint_config=endpoint_config)
    mock_api.path_params = path_params_obj
    converter = RequestConverter(api_object=mock_api)
    with pytest.raises(ValueError, match="Missing required route parameter: item_id"):
        converter._replace_route_params(converter.endpoint_config.route)

def test_replace_route_params_attribute_error_on_none():
    """测试 _replace_route_params - path_params 为 None 但路由需要参数"""
    endpoint_config = EndpointConfig(
        method=HTTPMethod.GET,
        route="/users/{user_id}",
        route_params=["user_id"]
    )
    mock_api = MockAPIObject(endpoint_config=endpoint_config, path_params=None) # path_params is None
    converter = RequestConverter(api_object=mock_api)
    # getattr(None, 'user_id') raises AttributeError, caught and re-raised
    with pytest.raises(ValueError, match="Missing required route parameter: user_id"):
         converter._replace_route_params(converter.endpoint_config.route)


# Next: Tests for prepare_url, prepare_headers, prepare_params, etc. 

@pytest.mark.parametrize(
    "base_url, route_in_config, expected_path",
    [
        ("http://test.com", "/users", "http://test.com/users"),
        ("http://test.com/", "/users", "http://test.com/users"), # Base trailing slash
        ("http://test.com", "users", "http://test.com/users"),   # Route missing leading slash
        ("http://test.com/", "users", "http://test.com/users"),  # Both variations
        ("http://test.com/api/v1", "/users", "http://test.com/api/v1/users"), # Base with path
        ("http://test.com/api/v1/", "/users", "http://test.com/api/v1/users"),
        ("http://test.com/api/v1", "users", "http://test.com/api/v1/users"),
        ("http://test.com/api/v1/", "users", "http://test.com/api/v1/users"),
        ("http://test.com", "/users/{user_id}", "http://test.com/users/123"), # With path param replacement
    ]
)
def test_prepare_url(base_url, route_in_config, expected_path):
    """测试 prepare_url - 不同 base_url 和 route 格式"""
    endpoint_config = EndpointConfig(method=HTTPMethod.GET, route=route_in_config, route_params=[])
    path_params_obj = None
    if "{user_id}" in route_in_config:
         endpoint_config.route_params=["user_id"]
         @define
         class P: user_id: int = 123
         path_params_obj = P()

    mock_api = MockAPIObject(base_url=base_url, endpoint_config=endpoint_config)
    # Need to set path_params on the mock_api instance if needed for route replacement
    if path_params_obj:
        mock_api.path_params = path_params_obj

    converter = RequestConverter(api_object=mock_api)
    # prepare_url relies on the 'route' property which does the replacement
    assert converter.prepare_url() == expected_path


def test_prepare_headers():
    """测试 prepare_headers"""
    headers_dict = {"X-API-Key": "12345", "Accept": "application/json"}
    # Case 1: Headers are set
    mock_api_with_headers = MockAPIObject(headers=headers_dict)
    converter_with = RequestConverter(api_object=mock_api_with_headers)
    assert converter_with.prepare_headers() == headers_dict

    # Case 2: Headers are None
    mock_api_no_headers = MockAPIObject(headers=None)
    converter_without = RequestConverter(api_object=mock_api_no_headers)
    assert converter_without.prepare_headers() == {} # Should return empty dict

@define
class SampleQueryParams:
    page: int = 1
    size: int | None = None

def test_prepare_params():
    """测试 prepare_params"""
    params_obj = SampleQueryParams(page=2, size=20)
    # Case 1: Query params object is set
    mock_api_with_params = MockAPIObject(query_params=params_obj)
    converter_with = RequestConverter(api_object=mock_api_with_params)
    assert converter_with.prepare_params() == params_obj

    # Case 2: Query params is None
    mock_api_no_params = MockAPIObject(query_params=None)
    converter_without = RequestConverter(api_object=mock_api_no_params)
    assert converter_without.prepare_params() is None

@define
class SampleRequestBody:
    username: str
    password: str | None = None

def test_prepare_request_body():
    """测试 prepare_request_body"""
    body_obj = SampleRequestBody(username="testuser", password="123")
    # Case 1: Request body object is set
    mock_api_with_body = MockAPIObject(request_body=body_obj)
    converter_with = RequestConverter(api_object=mock_api_with_body)
    assert converter_with.prepare_request_body() == body_obj

    # Case 2: Request body is None
    mock_api_no_body = MockAPIObject(request_body=None)
    converter_without = RequestConverter(api_object=mock_api_no_body)
    assert converter_without.prepare_request_body() is None

def test_prepare_files():
    """测试 prepare_files (仅 multipart 时相关)"""
    files_dict = {"file1": ("report.txt", b"content"), "image": ("logo.png", b"pngdata", "image/png")}

    # Case 1: ContentType is MULTIPART and files are set
    # Need to ensure MockAPIObject has 'files' attribute
    # Modify MockAPIObject or set attribute directly
    mock_api_with_files = MockAPIObject(content_type=ContentType.MULTIPART)
    mock_api_with_files.files = files_dict
    converter_with = RequestConverter(api_object=mock_api_with_files)
    assert converter_with.prepare_files() == files_dict

    # Case 2: ContentType is MULTIPART but files is None (or missing)
    mock_api_no_files = MockAPIObject(content_type=ContentType.MULTIPART)
    mock_api_no_files.files = None
    converter_without = RequestConverter(api_object=mock_api_no_files)
    assert converter_without.prepare_files() == {}

    # Case 3: ContentType is MULTIPART but files attribute is missing
    @define
    class MockApiWithoutFiles:
        content_type: ContentType = ContentType.MULTIPART
        # No 'files' attribute
        base_url: str = "http://test.com"
        endpoint_config: EndpointConfig = field(default=EndpointConfig(method=HTTPMethod.GET, route="/ping", route_params=[]))
        headers: dict | None = None
        query_params: ParametersT | None = None
        path_params: dict | None = None
        request_body: RequestBodyT | None = None

    mock_api_missing_files_attr = MockApiWithoutFiles()
    converter_missing = RequestConverter(api_object=mock_api_missing_files_attr)
    assert converter_missing.prepare_files() == {}

    # Case 4: ContentType is NOT MULTIPART (files attribute should be ignored by prepare_files)
    mock_api_json_with_files = MockAPIObject(content_type=ContentType.JSON)
    mock_api_json_with_files.files = files_dict
    converter_json = RequestConverter(api_object=mock_api_json_with_files)
    assert converter_json.prepare_files() == files_dict


def test_prepare_method():
    """测试 prepare_method"""
    mock_api_get = MockAPIObject(endpoint_config=EndpointConfig(method=HTTPMethod.GET, route="/"))
    converter_get = RequestConverter(api_object=mock_api_get)
    # The actual implementation returns the method string value
    assert converter_get.prepare_method() == HTTPMethod.GET.value

    mock_api_post = MockAPIObject(endpoint_config=EndpointConfig(method=HTTPMethod.POST, route="/"))
    converter_post = RequestConverter(api_object=mock_api_post)
    assert converter_post.prepare_method() == HTTPMethod.POST.value

# --- Test prepare method (Integration) ---

@define
class FullPathParams:
    entity_id: str

@define
class FullQueryParams:
    search: str | None = None
    limit: int = 10
    active: bool = True
    created_after: date | None = None

@define
class FullRequestBody:
    name: str
    tags: list[str]
    description: str | None = None
    config: dict | None = None

def test_prepare_integration_json():
    """测试 prepare 方法 - JSON 类型集成测试"""
    path_params = FullPathParams(entity_id="ent-123")
    query_params = FullQueryParams(search="keyword", created_after=None) # created_after is None
    request_body = FullRequestBody(name="Test Item", description=None, tags=["a", "b"]) # description is None
    headers = {"X-Custom-Header": "Value1"}
    endpoint = EndpointConfig(
        method=HTTPMethod.POST,
        route="/entities/{entity_id}/items",
        route_params=["entity_id"]
    )

    mock_api = MockAPIObject(
        base_url="https://api.example.com/v2/",
        content_type=ContentType.JSON,
        endpoint_config=endpoint,
        headers=headers,
        query_params=query_params,
        path_params=path_params,
        request_body=request_body
    )
    mock_api.path_params = path_params

    converter = RequestConverter(api_object=mock_api)
    prepared_request = converter.prepare()

    expected_url = "https://api.example.com/v2/entities/ent-123/items"
    expected_params = {"search": "keyword", "limit": 10, "active": True} # created_after=None removed
    expected_body = {"name": "Test Item", "tags": ["a", "b"]} # description=None removed, config=None removed

    assert isinstance(prepared_request, PreparedRequest)
    assert prepared_request.method == HTTPMethod.POST.value
    assert prepared_request.url == expected_url
    assert prepared_request.headers == headers # Headers are passed as is initially
    assert prepared_request.params == expected_params
    assert prepared_request.request_body == expected_body
    assert prepared_request.files is None # JSON type has no files processed

def test_prepare_integration_form():
    """测试 prepare 方法 - FORM 类型集成测试"""
    query_params = FullQueryParams(limit=5, active=False) # search=None, created_after=None
    request_body = FullRequestBody(name="Form Item", tags=["tag1"]) # description=None, config=None
    headers = {"Accept": "text/plain"}
    endpoint = EndpointConfig(method=HTTPMethod.PUT, route="/submit")

    mock_api = MockAPIObject(
        base_url="http://form.example.com",
        content_type=ContentType.FORM,
        endpoint_config=endpoint,
        headers=headers,
        query_params=query_params,
        request_body=request_body,
        path_params=None # No path params in this route
    )

    converter = RequestConverter(api_object=mock_api)
    prepared_request = converter.prepare()

    expected_url = "http://form.example.com/submit"
    expected_params = {"limit": 5, "active": False} # search=None, created_after=None removed
    expected_body = {"name": "Form Item", "tags": ["tag1"]} # description=None, config=None removed

    assert prepared_request.method == HTTPMethod.PUT.value
    assert prepared_request.url == expected_url
    assert prepared_request.headers == headers
    assert prepared_request.params == expected_params
    assert prepared_request.request_body == expected_body
    assert prepared_request.files is None

def test_prepare_integration_multipart():
    """测试 prepare 方法 - MULTIPART 类型集成测试"""
    request_body = FullRequestBody(name="Multipart Data", tags=["file"]) # description=None, config=None
    files_dict = {"attachment": ["data.bin", b"binarystuff"]}
    endpoint = EndpointConfig(method=HTTPMethod.POST, route="/upload")

    mock_api = MockAPIObject(
        base_url="http://files.example.com",
        content_type=ContentType.MULTIPART,
        endpoint_config=endpoint,
        request_body=request_body,
        path_params=None,
        query_params=None,
        headers=None,
        # files attribute needs to be set for multipart
    )
    mock_api.files = files_dict # Set files attribute

    converter = RequestConverter(api_object=mock_api)
    prepared_request = converter.prepare()

    expected_url = "http://files.example.com/upload"
    expected_body = {"name": "Multipart Data", "tags": ["file"]}
    expected_files = files_dict # Files dict should be passed through

    assert prepared_request.method == HTTPMethod.POST.value
    assert prepared_request.url == expected_url
    assert prepared_request.headers == {} # Default empty dict if None
    assert prepared_request.params is None # query_params was None
    assert prepared_request.request_body == expected_body
    assert prepared_request.files == expected_files # Check files

def test_prepare_integration_minimal():
    """测试 prepare 方法 - 最少参数情况"""
    endpoint = EndpointConfig(method=HTTPMethod.GET, route="/health")
    mock_api = MockAPIObject(
        base_url="http://minimal.com",
        content_type=ContentType.TEXT, # Example: Text content type
        endpoint_config=endpoint,
        headers=None,
        query_params=None,
        path_params=None,
        request_body=None,
    )

    converter = RequestConverter(api_object=mock_api)
    prepared_request = converter.prepare()

    expected_url = "http://minimal.com/health"

    assert prepared_request.method == HTTPMethod.GET.value
    assert prepared_request.url == expected_url
    assert prepared_request.headers == {}
    assert prepared_request.params is None
    assert prepared_request.request_body is None
    assert prepared_request.files is None

# --- Test post_prepare hook ---

def test_post_prepare_default():
    """测试默认 post_prepare 钩子不修改数据"""
    mock_api = MockAPIObject()
    converter = RequestConverter(api_object=mock_api)
    initial_prepared = PreparedRequest(method="GET", url="http://test.com/ping", headers={"test": "test"})
    final_prepared = converter.post_prepare(initial_prepared)
    assert final_prepared is initial_prepared

class CustomHeaderConverter(RequestConverter):
    """自定义 Converter，通过 post_prepare 添加 Header"""
    def post_prepare(self, prepared_data: PreparedRequest) -> PreparedRequest:
        # Ensure headers is a dict
        if prepared_data.headers is None:
            prepared_data.headers = {}
        prepared_data.headers["X-Added-By-Hook"] = "Hooked"
        return prepared_data

def test_post_prepare_custom_hook():
    """测试自定义 post_prepare 钩子修改数据"""
    endpoint = EndpointConfig(method=HTTPMethod.GET, route="/data")
    mock_api = MockAPIObject(
        base_url="http://hook.test",
        endpoint_config=endpoint,
        headers={"Existing": "Header"} # Start with existing headers
    )
    # Use the custom converter
    converter = CustomHeaderConverter(api_object=mock_api)
    # Call prepare() to trigger the whole process including post_prepare
    prepared_request = converter.prepare()

    # Check if the hook added the header
    expected_headers = {"Existing": "Header", "X-Added-By-Hook": "Hooked"}
    assert prepared_request.headers == expected_headers


# --- Test convert method (Higher Level Integration) ---

def test_convert_flow(monkeypatch):
    """测试 convert 方法的整体流程"""
    # Setup a basic API object
    endpoint = EndpointConfig(method=HTTPMethod.POST, route="/echo")
    request_body = {"message": "hello"} # Simple dict body for this test
    mock_api = MockAPIObject(
        base_url="http://convert.test",
        endpoint_config=endpoint,
        request_body=request_body,
        content_type=ContentType.JSON # Use JSON for simplicity
    )

    mock_api.path_params = None

    converter = RequestConverter(api_object=mock_api)

   
    mock_builder_instance = Mock(spec=JSONRequestBuilder) # Mock the builder instance
    built_request_dict = {"final_method": "POST", "final_url": "http://convert.test/echo", "json_payload": {"message": "hello"}}
    mock_builder_instance.build_request.return_value = built_request_dict
    monkeypatch.setattr(
        RequestConverter,
        "get_request_builder",
        lambda self: mock_builder_instance
    )

    final_result = converter.convert()


    mock_builder_instance.build_request.assert_called_once()

    prepared_request_expected = converter.prepare() # Call prepare again to get expected input
    mock_builder_instance.build_request.assert_called_once_with(prepared_request_expected)

    expected_final_result = converter._serialize_data(built_request_dict)
    assert final_result == expected_final_result
    assert final_result == built_request_dict

class ConvertModifyConverter(RequestConverter):
    """自定义 Converter，在 convert 流程中通过 post_prepare 修改数据"""
    def post_prepare(self, prepared_data: PreparedRequest) -> PreparedRequest:
        # 确保 headers 是字典，即使原始为 None
        if prepared_data.headers is None:
            prepared_data.headers = {}
        prepared_data.headers["X-Modified-By-PostPrepare"] = "yes"
        return prepared_data

def test_convert_with_post_prepare_modification(monkeypatch):
    """测试 convert 流程中，自定义 post_prepare 钩子是否生效"""
    # Setup
    endpoint = EndpointConfig(method=HTTPMethod.GET, route="/status")
    mock_api = MockAPIObject(
        base_url="http://postprepare.test",
        endpoint_config=endpoint
    )
    # 使用自定义的 Converter
    converter = ConvertModifyConverter(api_object=mock_api)

    # Mock Builder
    mock_builder_instance = Mock(spec=JSONRequestBuilder) # Can use any builder spec
    def mock_build_request(prep_req):
        # 确保 headers 存在于字典中
        unstructured_prep = converter.unstructure(prep_req)
        if "headers" not in unstructured_prep:
             unstructured_prep["headers"] = {}
        return unstructured_prep # 返回反结构化后的字典

    mock_builder_instance.build_request.side_effect = mock_build_request

    monkeypatch.setattr(
        ConvertModifyConverter, # 在特定子类上打桩
        "get_request_builder",
        lambda self: mock_builder_instance
    )

    # Execute convert
    final_result = converter.convert()

    # Assert
    assert isinstance(final_result, dict)
    assert "headers" in final_result
    assert "X-Modified-By-PostPrepare" in final_result.get("headers", {}), \
        "Header added by post_prepare was not found in the final converted result"
    assert final_result["headers"]["X-Modified-By-PostPrepare"] == "yes" 