# --coding:utf-8--
from .middlewares import ResponseType, CallNext, RequestType, register_middleware


@register_middleware
def test_middleware(request: RequestType, call_next: CallNext) -> ResponseType:
    request_info = {
        "method": request.get("method"),
    }

    response = call_next(request)
    print("测试前来一个mw:", request_info)
    return response
