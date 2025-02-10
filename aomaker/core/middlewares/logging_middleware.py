# --coding:utf-8--
import json
import time
import traceback
from json.decoder import JSONDecodeError
from loguru import logger

from .middlewares import RequestType, CallNext, ResponseType,register_middleware

@register_middleware
def logging_middleware(request: RequestType, call_next: CallNext) -> ResponseType:


    log_data = {
        "request": {
            "method": request.get("method"),
            "url": request.get("url"),
            "headers": request.get("headers", {}),
            "params": request.get("params", {}),
            "data": request.get("data"),
            "json": request.get("json"),
        },
        "response": None,
        "error": None,
        "duration": None
    }

    start_time = time.time()
    try:
        response = call_next(request)
    except Exception as e:
        log_data["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        log_data["duration"] = time.time() - start_time
        logger.error(json.dumps(log_data))
        raise

    log_data["duration"] = time.time() - start_time

    # 记录响应信息
    response_info = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "elapsed": response.elapsed.total_seconds() if response.elapsed else None
    }

    # 解析响应体
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            response_info["body"] = response.json()
        except JSONDecodeError:
            response_info["body"] = response.text
    elif content_type.startswith("text/"):
        response_info["body"] = response.text
    else:
        response_info["body"] = "(binary data)"

    log_data["response"] = response_info
    logger.info(json.dumps(log_data))

    return response
