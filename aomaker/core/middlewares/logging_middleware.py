# --coding:utf-8--
from json.decoder import JSONDecodeError
from loguru import logger

from .middlewares import RequestType, CallNext, ResponseType


def logging_middleware(request: RequestType, call_next: CallNext) -> ResponseType:
    # 请求前处理
    # 可以在这里记录请求的相关信息
    request_info = {
        "method": request.get("method"),
        "url": request.get("url"),
        "headers": request.get("headers"),
        "params": request.get("params"),
        "data": request.get("data"),
        "json": request.get("json"),
    }
    # 调用下一个中间件或发送请求
    response = call_next(request)

    # 响应后处理
    # 记录响应的相关信息
    try:
        response_body = response.json()
    except JSONDecodeError:
        response_body = response.text

    response_info = {
        "status_code": response.status_code,
        "headers": response.headers,
        "body": response_body,
        "elapsed": response.elapsed.total_seconds(),
    }

    # 合并请求和响应的信息
    log_info = {
        "request": request_info,
        "response": response_info,
    }

    # 将信息格式化并打印在一条日志中
    log_entry = f"""
======== 请求开始 ========
请求方法: {request_info['method']}
请求URL: {request_info['url']}
请求参数: {request_info['params']}
请求数据: {request_info['data']}
请求JSON: {request_info['json']}
-------- 响应 --------
状态码: {response_info['status_code']}
响应体: {response_info['body']}
请求耗时: {response_info['elapsed']} 秒
======== 请求结束 ========
"""
    logger.info(log_entry)

    return response
