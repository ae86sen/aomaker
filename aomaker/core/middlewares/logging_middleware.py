# --coding:utf-8--
import json
import traceback
from json import JSONDecodeError
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from jinja2 import Template
import allure
from emoji import emojize

from aomaker.log import logger,aomaker_logger
from .middlewares import RequestType, CallNext, ResponseType, register_middleware



TEMPLATE = """
{{tag}}
{{emoji_api}} <API>: {{caller_name}} {{doc}}
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
    caller_name: str = "TODO" # todo: 增加调用API名
    doc: str = "" # todo: 获取API注释
    success: bool = False
    error: Optional[Dict[str, Any]] = None


@register_middleware
def structured_logging_middleware(request: RequestType, call_next: CallNext) -> ResponseType:
    """支持多输出的结构化日志中间件"""
    log_data = LogData(request=request)
    response = None

    try:
        # 执行请求
        response = call_next(request)

        # 收集响应信息
        log_data.response = _parse_response(response)
        log_data.success = True

    except Exception as e:
        log_data.error = _parse_exception(e)
        raise
    finally:
        # 无论成功与否都记录日志
        _process_log_outputs(log_data, request, response)

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
    content_type = response.headers.get("Content-Type", "")

    if "application/json" in content_type:
        try:
            return response.json()
        except JSONDecodeError:
            return response.text
    elif content_type.startswith("text/"):
        return response.text
    return "(binary data)"

def _parse_exception(e: Exception) -> Dict[str, Any]:
    """解析异常信息"""
    return {
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc()
    }

def _process_log_outputs(log_data: LogData, request: RequestType, response: Optional[ResponseType]):
    """处理三路输出"""
    log_current_level = aomaker_logger.get_level()

    # 填充模板变量
    render_data = {
        "tag": "=" * 100,
        "emoji_api": emojize(":A_button_(blood_type):"),
        "emoji_req": emojize(":rocket:"),
        "emoji_rep": emojize(":check_mark_button:"),
        **log_data.request,
        **log_data.response,
        "caller_name": log_data.caller_name,
        "doc": log_data.doc,
        "log_level": log_current_level
    }
    # 渲染模板
    formatted_log = Template(TEMPLATE).render(render_data)

    # 控制台输出（根据日志级别）
    if log_current_level == 10:
        logger.debug(formatted_log)
    else:
        logger.info(formatted_log)

    # Allure 附件输出
    _attach_allure_report(log_data, request, response)

def _attach_allure_report(log_data: LogData, request: RequestType, response: Optional[ResponseType]):
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
            "body": log_data.response["response_body"]
        }

    try:
        allure.attach(
            json.dumps(allure_info, indent=2, ensure_ascii=False),
            name=f"{log_data.caller_name} Log",
            attachment_type=allure.attachment_type.JSON
        )
    except Exception as e:
        logger.warning(f"Allure附件生成失败: {str(e)}")
