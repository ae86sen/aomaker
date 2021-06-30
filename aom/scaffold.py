import os
import sys

from loguru import logger


class ExtraArgument:
    create_venv = False


def init_parser_scaffold(subparsers):
    sub_parser_scaffold = subparsers.add_parser(
        "startproject", help="Create a new project with template structure."
    )
    sub_parser_scaffold.add_argument(
        "project_name", type=str, nargs="?", help="Specify new project name."
    )
    sub_parser_scaffold.add_argument(
        "-venv",
        dest="create_venv",
        action="store_true",
        help="Create virtual environment in the project and install aomaker.",
    )
    return sub_parser_scaffold


def create_scaffold(project_name):
    """ Create scaffold with specified project name.
    """
    if os.path.isdir(project_name):
        logger.warning(
            f"Project folder {project_name} exists, please specify a new project name."
        )
        return 1
    elif os.path.isfile(project_name):
        logger.warning(
            f"Project name {project_name} conflicts with existed file, please specify a new one."
        )
        return 1

    logger.info(f"Create new project: {project_name}")
    print(f"Project root dir: {os.path.join(os.getcwd(), project_name)}\n")

    def create_folder(path):
        os.makedirs(path)
        msg = f"Created folder: {path}"
        print(msg)

    def create_file(path, file_content=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        msg = f"Created file: {path}"
        print(msg)

    create_folder(project_name)
    create_folder(os.path.join(project_name, "common"))
    create_file(os.path.join(project_name, "common", "__init__.py"))
    base_api_content = """import os
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
        \"""
        发送http请求
        :param data: 请求数据
        :return:
        \"""
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
        \"""
        替换数据
        :param source_data: 源数据
        :param data: 替换内容，如{data:new_data}
        :return:
        \"""

        return Utils.handle_template(source_data, data)

    @staticmethod
    def get_resp_json(response):
        \"""
        将response解析为json
        :param response:
        :return:
        \"""
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
    """
    create_file(os.path.join(project_name, "common", "base_api.py"), base_api_content)
    handle_path_content = """import os

BASEDIR = os.path.dirname(os.path.dirname(__file__))
# 配置文件的路径
CONF_DIR = os.path.join(BASEDIR, "conf")
CONFIG_DIR = os.path.join(CONF_DIR, 'config.yaml')
# 用例数据的目录
DATA_DIR = os.path.join(BASEDIR, "data")
# 日志文件目录
LOG_DIR = os.path.join(BASEDIR, "log")
# 测试报告的路
REPORT_DIR = os.path.join(BASEDIR, "reports")
# 测试用例模块所在的目录
CASE_DIR = os.path.join(BASEDIR, "testcases")
    """
    create_file(os.path.join(project_name, "common", "handle_path.py"), handle_path_content)
    utils_content = """from string import Template
from faker import Faker
import yaml
from loguru import logger


class Utils:
    @classmethod
    def handle_yaml(cls, file_name):
        try:
            yaml_data = yaml.safe_load(open(file_name, encoding='utf-8'))
        except Exception as e:
            logger.error(f'yaml文件读取失败，文件名称：{file_name}')
            raise e
        else:
            return yaml_data

    @classmethod
    def handle_template(cls, source_data, replace_data: dict, ):
        \"""
        替换文本变量
        :param source_data:
        :param replace_data:
        :return:
        \"""
        res = Template(str(source_data)).safe_substitute(**replace_data)
        return yaml.safe_load(res)

    @classmethod
    def handle_random_phone(cls):
        \"""
        生成随机手机号
        :return:
        \"""
        fake = Faker(locale='zh_CN')
        phone_number = fake.phone_number()
        return phone_number
    """
    create_file(os.path.join(project_name, "common", "utils.py"), utils_content)
    wrapper_content = """from loguru import logger


def api_call(func):
    \"""
    接口调用记录
    :param func: 装饰的函数
    :return:
    \"""

    def inner(*args, **kwargs):
        logger.info(f"开始调用接口：{func.__name__}")
        res = func(*args, **kwargs)
        logger.info(f"结束调用接口：{func.__name__}")
        return res

    return inner
    """
    create_file(os.path.join(project_name, "common", "wrapper.py"), wrapper_content)
    create_folder(os.path.join(project_name, "apis"))
    # TODO: check
    create_file(os.path.join(project_name, "apis", "__init__.py"))
    create_folder(os.path.join(project_name, "cases"))
    create_file(os.path.join(project_name, "cases", "__init__.py"))
    create_folder(os.path.join(project_name, "testcases"))
    create_file(os.path.join(project_name, "testcases", "__init__.py"))
    create_folder(os.path.join(project_name, "conf"))
    create_folder(os.path.join(project_name, "data"))

    return 0


def main_scaffold(args):
    ExtraArgument.create_venv = args.create_venv
    sys.exit(create_scaffold(args.project_name))
