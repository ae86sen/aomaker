import pytest
import json
from unittest.mock import patch, MagicMock, call
from datetime import timedelta
from json import JSONDecodeError
import allure

from aomaker.core.middlewares.logging_middleware import structured_logging_middleware

# --- Helper Classes ---

class MockResponse:
    def __init__(self, status_code=200, content=b'', text='', elapsed=None):
        self.status_code = status_code
        self.content = content
        self.text = text or content.decode('utf-8', errors='ignore')
        self.elapsed = elapsed or timedelta(0)
        self.json = MagicMock()
        if content:
            try:
                decoded_content = content.decode('utf-8')
                self.json.return_value = json.loads(decoded_content)
            except (UnicodeDecodeError, JSONDecodeError):
                self.json.side_effect = JSONDecodeError("Mock decode error", "doc", 0)
        else:
             self.json.side_effect = JSONDecodeError("Mock decode error on empty", "doc", 0)


# --- Fixtures ---

@pytest.fixture
def mock_logger():
    """Mocks the logger used within the middleware."""
    with patch('aomaker.core.middlewares.logging_middleware.logger') as mock_log:
        yield mock_log

@pytest.fixture
def mock_get_level():
    """Mocks the function determining the current log level."""
    with patch('aomaker.core.middlewares.logging_middleware.aomaker_logger.get_level') as mock_level:
        mock_level.return_value = 20
        yield mock_level

@pytest.fixture
def mock_allure_attach():
    """Mocks allure.attach function."""
    with patch('aomaker.core.middlewares.logging_middleware.allure.attach') as mock_attach:
            yield mock_attach

@pytest.fixture
def mock_traceback():
    """Mocks the traceback module."""
    with patch('aomaker.core.middlewares.logging_middleware.traceback') as mock_tb:
        yield mock_tb

# --- Test Cases ---

def test_log_success_json_response(mock_logger, mock_get_level, mock_allure_attach):
    """测试：成功请求，JSON响应，INFO级别日志"""
    mock_get_level.return_value = 20 # INFO level
    mock_response = MockResponse(
        status_code=200,
        content=b'{"message": "success", "data": [1, 2]}',
        elapsed=timedelta(seconds=0.5)
    )
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/api",
        "method": "POST",
        "params": {"q": "test"},
        "json": {"user": "admin"},
        "_api_meta": {"class_name": "TestAPI", "class_doc": "A test API"}
    }

    # Call the middleware
    response = structured_logging_middleware(request_data, mock_call_next)

    # Assertions
    assert response is mock_response
    mock_call_next.assert_called_once_with(request_data)
    mock_get_level.assert_called_once()

    # Check logger call (INFO level)
    mock_logger.info.assert_called_once()
    mock_logger.debug.assert_not_called()
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>: TestAPI A test API" in log_output
    assert "URL: http://test.com/api" in log_output
    assert "Method: POST" in log_output
    assert "Request Params: {'q': 'test'}" in log_output
    assert "Request Json: {'user': 'admin'}" in log_output
    assert "Headers:" not in log_output # INFO level doesn't log headers
    assert "Status Code: 200" not in log_output # INFO level doesn't log status code
    assert "Response Body: {'message': 'success', 'data': [1, 2]}" in log_output
    assert "Elapsed: 0.5s" in log_output

    # Check allure attach
    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "TestAPI"
    assert allure_kwargs['attachment_type'] == allure.attachment_type.JSON
    allure_json_content = json.loads(allure_args[0])
    assert allure_json_content['request']['url'] == "http://test.com/api"
    assert allure_json_content['request']['method'] == "POST"
    assert allure_json_content['request']['params'] == {"q": "test"}
    assert allure_json_content['request']['json'] == {"user": "admin"}
    assert allure_json_content['response']['status_code'] == 200
    assert allure_json_content['response']['body'] == {"message": "success", "data": [1, 2]}

def test_log_success_text_response(mock_logger, mock_get_level, mock_allure_attach):
    """测试：成功请求，Text响应，INFO级别日志，检查warning"""
    mock_get_level.return_value = 20 # INFO level
    mock_response = MockResponse(
        status_code=201,
        content=b'OK',
        elapsed=timedelta(seconds=0.1)
    )
    mock_response.json.side_effect = JSONDecodeError("msg", "doc", 0)
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/create",
        "method": "PUT",
        "data": "raw data",
        "_api_meta": {"class_name": "CreateAPI", "class_doc": ""}
    }

    response = structured_logging_middleware(request_data, mock_call_next)

    assert response is mock_response
    mock_call_next.assert_called_once_with(request_data)

    mock_logger.info.assert_called_once()
    mock_logger.warning.assert_called_once_with(
        "该接口response内容无法解析为JSON格式，已返回text"
    )
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>: CreateAPI" in log_output
    assert "Request Data: raw data" in log_output
    assert "Response Body: OK" in log_output 
    assert "Elapsed: 0.1s" in log_output

    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "CreateAPI"
    allure_json_content = json.loads(allure_args[0])
    assert allure_json_content['request']['data'] == "raw data"
    assert allure_json_content['response']['status_code'] == 201
    assert allure_json_content['response']['body'] == "OK"

def test_log_success_empty_response(mock_logger, mock_get_level, mock_allure_attach):
    """测试：成功请求，空响应体，INFO级别日志，检查warning"""
    mock_get_level.return_value = 20 # INFO level
    mock_response = MockResponse(
        status_code=204,
        content=b'', # Empty content
        elapsed=timedelta(seconds=0.05)
    )
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/delete",
        "method": "DELETE",
        "_api_meta": {"class_name": "DeleteAPI"}
    }

    response = structured_logging_middleware(request_data, mock_call_next)

    assert response is mock_response
    mock_call_next.assert_called_once_with(request_data)

    mock_logger.info.assert_called_once()
    mock_logger.warning.assert_called_once_with("该接口response内容为空")
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>: DeleteAPI" in log_output
    assert "Response Body: None" in log_output
    assert "Elapsed: 0.05s" in log_output

    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "DeleteAPI"
    allure_json_content = json.loads(allure_args[0])
    assert allure_json_content['response']['status_code'] == 204
    assert allure_json_content['response']['body'] is None

def test_log_success_streaming_response(mock_logger, mock_get_level, mock_allure_attach):
    """测试：成功请求，流式响应，INFO级别日志"""
    mock_get_level.return_value = 20 # INFO level
    mock_response = MockResponse(
        status_code=200,
        content=b'stream data',
        elapsed=timedelta(seconds=1.2)
    )
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/stream",
        "method": "GET",
        "_api_meta": {"class_name": "StreamAPI", "is_streaming": True}
    }

    response = structured_logging_middleware(request_data, mock_call_next)

    assert response is mock_response
    mock_call_next.assert_called_once_with(request_data)

    mock_logger.info.assert_called_once()
    mock_logger.warning.assert_not_called()
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>: StreamAPI" in log_output
    assert "Response Body: [流式响应] 内容将分块传输，无法预先记录" in log_output
    assert "Elapsed: 1.2s" in log_output

    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "StreamAPI"
    allure_json_content = json.loads(allure_args[0])
    assert "response" in allure_json_content
    assert allure_json_content['response']['status_code'] == 200
    assert allure_json_content['response']['body'] == "[流式响应]"

def test_log_exception_raised(mock_logger, mock_get_level, mock_allure_attach, mock_traceback):
    """测试：call_next 抛出异常，INFO级别日志"""
    mock_get_level.return_value = 20 # INFO level
    mock_exception = ValueError("Something went wrong")
    mock_call_next = MagicMock(side_effect=mock_exception)
    mock_traceback.format_exc.return_value = "Traceback details"
    request_data = {
        "url": "http://test.com/error",
        "method": "POST",
        "_api_meta": {"class_name": "ErrorAPI"}
    }

    with pytest.raises(ValueError, match="Something went wrong"):
        structured_logging_middleware(request_data, mock_call_next)


    mock_call_next.assert_called_once_with(request_data)
    mock_traceback.format_exc.assert_called_once()


    mock_logger.info.assert_called_once()
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>: ErrorAPI" in log_output
    assert "<Response>" in log_output 
    assert "Response Body:" in log_output 
    assert "Traceback details" not in log_output

 
    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "ErrorAPI"
    allure_json_content = json.loads(allure_args[0])
    assert "request" in allure_json_content
    assert "response" not in allure_json_content 


def test_log_debug_level(mock_logger, mock_get_level, mock_allure_attach):
    """测试：成功请求，JSON响应，DEBUG级别日志"""
    mock_get_level.return_value = 10 # DEBUG level
    mock_response = MockResponse(status_code=200, content=b'{"data": true}')
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/debug",
        "method": "GET",
        "headers": {"X-Test": "debug"},
        "_api_meta": {"class_name": "DebugAPI"}
    }

    structured_logging_middleware(request_data, mock_call_next)

    mock_logger.debug.assert_called_once()
    mock_logger.info.assert_not_called()
    log_output = mock_logger.debug.call_args[0][0]

    assert "Headers: {'X-Test': 'debug'}" in log_output
    assert "Status Code: 200" in log_output
    assert "<API>: DebugAPI" in log_output
    assert "URL: http://test.com/debug" in log_output
    assert "Response Body: {'data': True}" in log_output

    mock_allure_attach.assert_called_once()

def test_log_missing_api_meta(mock_logger, mock_get_level, mock_allure_attach):
    """测试：请求数据中缺少 _api_meta"""
    mock_get_level.return_value = 20
    mock_response = MockResponse(status_code=200, content=b'{}')
    mock_call_next = MagicMock(return_value=mock_response)
    request_data = {
        "url": "http://test.com/no_meta",
        "method": "GET",
        # No _api_meta key
    }

    structured_logging_middleware(request_data, mock_call_next)

    mock_logger.info.assert_called_once()
    log_output = mock_logger.info.call_args[0][0]
    assert "<API>:  " in log_output 

    mock_allure_attach.assert_called_once()
    allure_args, allure_kwargs = mock_allure_attach.call_args
    assert allure_kwargs['name'] == "" 

def test_log_allure_attach_fails(mock_logger, mock_get_level, mock_allure_attach):
    """测试：allure.attach 抛出异常时，记录警告且不影响中间件"""
    mock_get_level.return_value = 20
    mock_response = MockResponse(status_code=200, content=b'{}')
    mock_call_next = MagicMock(return_value=mock_response)
    mock_allure_attach.side_effect = Exception("Allure error")
    request_data = {
        "url": "http://test.com/allure_fail",
        "method": "GET",
        "_api_meta": {"class_name": "AllureFailAPI"}
    }

    response = structured_logging_middleware(request_data, mock_call_next)

    assert response is mock_response
    mock_logger.info.assert_called_once()
    mock_allure_attach.assert_called_once()
    mock_logger.warning.assert_called_once_with("Allure附件生成失败: Allure error") 