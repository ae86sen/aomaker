# --coding:utf-8--
import inspect

import allure
import requests

from aomaker.log import logger
from aomaker.cache import Config, Cache, Schema


def request(func):
    def wrapper(*args, **kwargs):
        conf = Config()
        cache = Cache()
        logger.info('-------------- Request -----------------')
        # print(args, kwargs)
        payload = args[1]
        method = payload.get('method')
        host = conf.get("host")
        api_path = payload.get('api_path', '')
        headers = cache.get("headers")
        params = payload.get("params")
        data = payload.get("data")
        json = payload.get("json")

        logger.debug(f"请求地址 =====> {host + api_path}")
        logger.debug(f"请求方法 =====> {method}")
        if headers:
            logger.debug(f"请求头 =====> {headers}")

        if params:
            logger.debug(f"请求参数 =====> {params}")
        if data:
            logger.debug(f"请求体[data] =====> {data}")
        if json:
            logger.debug(f"请求体[json] =====> {json}")

        # running function
        response = func(*args, **kwargs)

        logger.info("-------------- Response ----------------")
        if response.status_code < 400:
            logger.info(f"请求成功,状态码：{str(response.status_code)}")
        else:
            logger.warning(f"请求失败,状态码：{str(response.status_code)}")
            raise ValueError("请求失败")
        duration = response.elapsed.total_seconds()
        logger.debug(f"请求耗时 =====> {duration}s")

        api_name = inspect.stack()[1][3]
        try:
            resp = response.json()
            logger.debug(f"请求响应 =====> {resp}")
        except json.decoder.JSONDecodeError as msg:
            logger.debug(f"[warning]: failed to convert res to json, try to convert to text")
            logger.trace(f"[warning]: {msg} \n")
            logger.debug(f"[type]: text      [time]: {duration}\n")
            logger.debug(f"[response]:\n {response.text} \n")
            resp = response.text
        else:
            # 保存响应schema
            schema = Schema()
            to_schema = _genson(resp)
            schema.set(api_name, to_schema)
            logger.info(f'接口{api_name}的响应jsonschema已保存到schema表中')

        req_resp_info = f"""
        <request>\n
        url: {host + api_path}\n
        method: {method}\n
        headers: {headers}\n
        params: {params}\n
        data: {data}\n
        json: {json}

        ----------------------------------------------------------------------------

        <response>
        {resp}

        ----------------------------------------------------------------------------

        <duration>
        {duration}s
        """
        try:
            allure.attach(req_resp_info, name=f"{api_name} req&res", attachment_type=allure.attachment_type.TEXT)
        except Exception:
            pass
        return resp

    return wrapper





class BaseApi:

    def __init__(self):
        self.cache = Cache()
        self.config = Config().get_all()
        self._host = self.config.get('host')
        self._headers = self.cache.get('headers')

    @request
    def send_http(self, http_data: dict):
        """
        发送http请求
        :return:
        """
        payload = self._payload_schema(**http_data)
        response = requests.request(**payload)
        # do something

        return response

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