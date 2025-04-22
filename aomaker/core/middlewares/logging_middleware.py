# --coding:utf-8--
import json
import traceback
from json import JSONDecodeError
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from jinja2 import Template
import allure
from emoji import emojize

from aomaker.log import logger, aomaker_logger
from .registry import RequestType, CallNext, ResponseType, middleware

TEMPLATE = """
{{tag}}
{{emoji_api}} <API>: {{class_name}} {{class_doc}}
{{emoji_req}} <Request>
     URL: {{url}}
{% if method -%}
{% raw %}     Method: {%endraw%}{{method}}
{% endif -%}
{% if log_level==10 -%}
{% raw %}     Headers: {%endraw%}{{headers}}
{% endif -%}
{% if params -%}
{% raw %}     Request Params: {%endraw%}{{params}}
{% endif -%}
{% if data -%}
{% raw %}     Request Data: {%endraw%}{{data}}
{% endif -%}
{% if json -%}
{% raw %}     Request Json: {%endraw%}{{json}}
{% endif -%}
{{emoji_rep}} <Response>
{% if log_level==10 -%}
{% raw %}     Status Code: {%endraw%}{{status_code}}
{% endif -%}
{% raw %}     Response Body: {%endraw%}{{response_body}}
{% if elapsed -%}
    {% raw %}     Elapsed: {%endraw%}{{elapsed}}s
{% endif -%}
{{tag}}
"""


@dataclass
class LogData:
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    class_name: str = field(default="")
    class_doc: str = field(default="")
    success: bool = False
    error: Optional[Dict[str, Any]] = None


@middleware(name="logging_middleware", priority=900)
def structured_logging_middleware(request: RequestType, call_next: CallNext) -> ResponseType:
    """支持多输出的结构化日志中间件"""
    api_meta = request.get("_api_meta", {})
    is_streaming = api_meta.get("is_streaming", False)
    
    log_data = LogData(request=request, class_name=api_meta.get("class_name",""), class_doc=api_meta.get("class_doc",""))
    response = None

    try:
        response = call_next(request)
        
        # 处理流式响应和普通响应的日志记录差异
        if is_streaming:
            log_data.response = {
                "status_code": response.status_code,
                "elapsed": response.elapsed.total_seconds() if response.elapsed else None,
                "response_body": "[流式响应] 内容将分块传输，无法预先记录" 
            }
        else:
            log_data.response = _parse_response(response)
            
        log_data.success = True

    except Exception as e:
        log_data.error = _parse_exception(e)
        raise
    finally:
        _process_log_outputs(log_data, request, response, is_streaming)

    return response


def _parse_response(response: ResponseType) -> Dict[str, Any]:
    """解析响应数据"""
    return {
        "status_code": response.status_code,
        "elapsed": response.elapsed.total_seconds() if response.elapsed else None,
        "response_body": _parse_response_body(response)
    }


def _parse_response_body(response: ResponseType) -> Any:
    """自动解析响应体"""
    if not response.content:
        logger.warning("该接口response内容为空")
        return None

    try:
        return response.json()
    except JSONDecodeError:
        logger.warning("该接口response内容无法解析为JSON格式，已返回text")
        return response.text


def _parse_exception(e: Exception) -> Dict[str, Any]:
    """解析异常信息"""
    return {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc()
    }


def _process_log_outputs(log_data: LogData, request: RequestType, response: Optional[ResponseType], is_streaming: bool = False):
    """处理三路输出"""
    log_current_level = aomaker_logger.get_level()

    render_data = {
        "tag": "=" * 100,
        "emoji_api": emojize(":A_button_(blood_type):"),
        "emoji_req": emojize(":rocket:"),
        "emoji_rep": emojize(":check_mark_button:" if not is_streaming else ":down_arrow:"),
        **log_data.request,
        **log_data.response,
        "class_name": log_data.class_name,
        "class_doc": log_data.class_doc,
        "log_level": log_current_level
    }

    formatted_log = Template(TEMPLATE).render(render_data)

    # 控制台输出（根据日志级别）
    if log_current_level == 10:
        logger.debug(formatted_log)
    else:
        logger.info(formatted_log)

    _attach_allure_report(log_data, request, response, is_streaming)


def _attach_allure_report(log_data: LogData, request: RequestType, response: Optional[ResponseType], is_streaming: bool = False):
    """生成Allure附件"""
    allure_info = {
        "request": {
            "url": request["url"],
            "method": request.get("method"),
            "params": request.get("params"),
            "data": request.get("data"),
            "json": request.get("json")
        }
    }

    if response is not None:
        allure_info["response"] = {
            "status_code": response.status_code,
            "body": "[流式响应]" if is_streaming else log_data.response.get("response_body")
        }

    try:
        allure.attach(
            json.dumps(allure_info, indent=2, ensure_ascii=False),
            name=f"{log_data.class_name}",
            attachment_type=allure.attachment_type.JSON
        )
    except Exception as e:
        logger.warning(f"Allure附件生成失败: {str(e)}")
