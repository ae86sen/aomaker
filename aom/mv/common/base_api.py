
    import os
import requests
from loguru import logger

from common.handle_path import CONF_DIR
from common.utils import Utils


class BaseApi:
    util = Utils()
    conf_path = os.path.join(CONF_DIR, 'config.yaml')
    apis_conf_path = os.path.join(CONF_DIR, 'apis.yaml')
    # 配置文件数据
    conf_data = util.handle_yaml(conf_path)
    apis_conf_data = util.handle_yaml(apis_conf_path)
    host = conf_data['env']['host']
    account = conf_data['login_account']

    def send_http(self, data: dict):
        """
        发送http请求
        :param data: 请求数据
        :return:
        """
        try:
            self.__api_log(**data)
            response = requests.request(**data)
            logger.info(f"响应结果为：{response.status_code}")
        except Exception as e:
            logger.error(f'发送请求失败，请求参数为：{data}')
            logger.exception(f'发生的错误为：{e}')
            raise e
        else:
            return response

    @staticmethod
    def template(source_data: str, data: dict):
        """
        替换数据
        :param source_data: 源数据
        :param data: 替换内容，如{data:new_data}
        :return:
        """

        return Utils.handle_template(source_data, data)

    @staticmethod
    def get_resp_json(response):
        """
        将response解析为json
        :param response:
        :return:
        """
        try:
            result = response.json()
        except Exception as e:
            logger.error('解析响应结果为json失败，请检查')
            raise e
        else:
            return result

    @staticmethod
    def __api_log(method, url, headers=None, params=None, json=None, data=None):
        logger.info(f"请求方式：{method}")
        logger.info(f"请求地址：{url}")
        logger.info(f"请求头：{headers}")
        logger.info(f"请求参数：{params}")
        logger.info(f"请求体：{json}")
        logger.info(f"请求表单数据：{data}")
    