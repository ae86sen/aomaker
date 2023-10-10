# --coding:utf-8--
import inspect
import json

import allure
import requests
from requests import sessions
from json.decoder import JSONDecodeError
from emoji import emojize
from jinja2 import Template
from dataclasses import is_dataclass

from aomaker.log import logger, aomaker_logger
from aomaker.cache import Config, Cache, schema
from aomaker._aomaker import genson
from aomaker.exceptions import HttpRequestError
from aomaker.aomaker import AoMakerRetry
from aomaker.path import API_DIR

template = """
{{tag}}
{{emoji_api}} <API>: {{caller_name}} {{doc}}
{{emoji_req}} <Request>
     URL: {{url}}
{% if method -%}
{% raw %}     Method: {%endraw%}{{method}}
{% endif -%}
{% if headers -%}
{% raw %}     Headers: {%endraw%}{{headers}}
{% endif -%}
{% if request_params -%}
{% raw %}     Request Params: {%endraw%}{{request_params}}
{% endif -%}
{% if request_data -%}
{% raw %}     Request Data: {%endraw%}{{request_data}}
{% endif -%}
{% if request_json -%}
{% raw %}     Request Json: {%endraw%}{{request_json}}
{% endif -%}
{{emoji_rep}} <Response>
{% if status_code -%}
{% raw %}     Status Code: {%endraw%}{{status_code}}
{% endif -%}
{% raw %}     Response Body: {%endraw%}{{response_body}}
{% if elapsed -%}
    {% raw %}     Elapsed: {%endraw%}{{elapsed}}s
{% endif -%}
{{tag}}
"""


def _render_template(template_str, data):
    temp = Template(template_str)
    return temp.render(data)


def response_callback(payload: dict):
    def inner(response: requests.models.Response, *args, **kwargs):
        api_caller = _get_api_frame()
        caller_class_obj = api_caller.f_locals['self']
        caller_of_class = caller_class_obj.__class__.__name__
        caller_of_method = api_caller.f_code.co_name
        caller_name = f"{caller_of_class}.{caller_of_method}"
        doc = caller_class_obj.__class__.__dict__[caller_of_method].__doc__
        doc = doc.split("\n")[0].strip() if doc else ""
        caller_name = f"{caller_name} {doc}"

        print_info, allure_info, std_logger = _handle_print_info(payload, response, caller_name)

        if response.status_code >= 400:
            logger.error(_render_template(template, print_info))
            raise HttpRequestError(str(response.status_code))
        else:
            try:
                resp_body = response.json()
            except JSONDecodeError as msg:
                logger.warning(f"【warning】请求响应解析为json格式失败，尝试转换为text.错误信息：{msg}")
                resp_body = response.text
            else:
                setattr(response, "json_data", resp_body)

            # info['response_body'] = resp_body
            print_info['response_body'] = resp_body
            allure_info['response_body'] = resp_body
            print_info = _render_template(template, print_info)
            std_logger(print_info)

            to_schema = genson(resp_body)
            schema.set(caller_of_method, to_schema)
            logger.debug(f'接口{caller_name}的响应jsonschema已保存到schema表中')

            try:
                allure.attach(json.dumps(allure_info, indent=2, separators=(',', ':'), ensure_ascii=False),
                              name=caller_name,
                              attachment_type=allure.attachment_type.JSON)
            except Exception:
                pass

    return inner


def _get_api_frame():
    current_frame = inspect.currentframe()
    outer_frames = inspect.getouterframes(current_frame)
    for frame_info in outer_frames[8:]:
        frame = frame_info.frame
        filename = frame_info.filename
        if API_DIR in filename:
            return frame


def _handle_print_info(request_payload, response, caller_name):
    url = request_payload.get('url')
    params = request_payload.get('params')
    req_data = request_payload.get("data")
    req_json = request_payload.get("json")

    info = {
        "caller_name": caller_name,
        "url": url,
        "request_params": params,
        "request_data": req_data,
        "request_json": req_json,
        "response_body": None
    }
    allure_info = {
        "url": url,
    }

    if params:
        allure_info['request_params'] = params
    if req_data:
        allure_info['request_data'] = req_data
    if req_json:
        allure_info['request_json'] = req_json
    log_current_level = aomaker_logger.get_level()
    std_logger = logger.info
    if log_current_level == 10:
        info.update({
            "method": request_payload.get('method'),
            "headers": request_payload.get('headers'),
            "status_code": response.status_code,
            "elapsed": response.elapsed.total_seconds(),
        })
        std_logger = logger.debug
    print_info = {"tag": "=" * 100,
                  "emoji_api": emojize(":A_button_(blood_type):"),
                  "emoji_req": emojize(":rocket:"),
                  "emoji_rep": emojize(":check_mark_button:"),
                  **info}
    return print_info, allure_info, std_logger


class BaseApi:
    IS_HTTP_RETRY = False
    HTTP_RETRY_COUNTS = 3
    HTTP_RETRY_INTERVAL = 2  # 单位：s

    def __init__(self):
        self.cache = Cache()
        self.config = Config().get_all()
        self._host = self.config.get('host')
        self._headers = self.cache.get('headers')
        self._response_callback = response_callback

    def send_http(self, http_data):
        response = self._send_http(http_data)
        res = getattr(response, "json_data")
        return res

    def _send_http(self, http_data):
        if is_dataclass(http_data):
            http_data = http_data.all_fields
            dic = {}
            for k, v in http_data.items():
                if v is not None:
                    dic[k] = v
            http_data = dic

        new_headers = http_data.get("headers")
        payload = self._payload_schema(**http_data)

        if new_headers:
            headers = self._headers
            headers.update(new_headers)
            payload["headers"] = headers

        hooks = self.get_response_hook(payload)
        response = self.request(**payload, hooks=hooks)
        return response

    def request(self, method, url, **kwargs):

        def session_request():
            with sessions.Session() as session:
                return session.request(method=method, url=url, **kwargs)

        if self.IS_HTTP_RETRY:
            for attempt in AoMakerRetry(counts=self.HTTP_RETRY_COUNTS, interval=self.HTTP_RETRY_INTERVAL,
                                        exception_type=HttpRequestError):
                with attempt:
                    return session_request()
        else:
            return session_request()

    def get_response_hook(self, payload: dict) -> dict:

        return {"response": self._response_callback(payload)}

    def _payload_schema(self, **kwargs):
        api_path = kwargs.get('api_path', '')
        method = kwargs.get('method')
        payload = {
            'url': self._host + api_path,
            'method': method,
            'headers': self._headers,
            'cookies': kwargs.get('cookies'),
            'auth': kwargs.get('auth'),
            'params': kwargs.get('params'),
            'data': kwargs.get('data'),
            'json': kwargs.get('json'),
            'files': kwargs.get('files')
        }

        return payload
