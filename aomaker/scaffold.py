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
from common.handle_assert import HandleAssert


class BaseApi:
    util = Utils()
    
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
    
    @staticmethod
    def assert_equal(ex, re):
        \"""
        断言相等
        :param ex:预期结果
        :param re:实际结果
        :return:
        \"""
        return HandleAssert.eq(ex, re)

    @staticmethod
    def assert_contains(content, target):
        \"""
        断言包含
        :param content: 文本内容
        :param target: 目标文本
        :return:
        \"""
        return HandleAssert.contains(content, target)
    """
    create_file(os.path.join(project_name, "common", "base_api.py"), base_api_content)
    handle_path_content = """import os

# 项目根目录
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
# 自定义fixture目录
FIXTURE_DIR = os.path.join(BASEDIR, "fixtures")
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
    mysql_content = """import os

import pymysql
from loguru import logger

from common.handle_path import CONF_DIR
from common.base_api import BaseApi


class HandleMysql:
    def __init__(self, **kwargs):
        # 连接到数据库
        try:
            self.con = pymysql.connect(charset="utf8", **kwargs)
        except Exception as e:
            logger.error(f'数据库连接失败，连接参数：{kwargs}')
            raise e
        else:
            # 创建一个游标
            self.cur = self.con.cursor()

    def get_one(self, sql):
        \"""获取查询到的第一条数据\"""
        self.con.commit()
        self.cur.execute(sql)
        return self.cur.fetchone()

    def get_all(self, sql):
        \"""获取sql语句查询到的所有数据\"""
        self.con.commit()
        self.cur.execute(sql)
        return self.cur.fetchall()

    def count(self, sql):
        \"""获取sql语句查询到的数量\"""
        self.con.commit()
        res = self.cur.execute(sql)
        return res

    def close(self):
        # 关闭游标对象
        self.cur.close()
        # 断开连接
        self.con.close()
    """
    create_file(os.path.join(project_name, "common", "handle_mysql.py"), mysql_content)
    assert_content = """from loguru import logger


class HandleAssert:

    @staticmethod
    def eq(ex, re):
        \"""
        断言相等
        :param ex: 预期结果
        :param re: 实际结果
        :return:
        \"""
        try:
            assert str(ex) == str(re)
        except AssertionError as e:
            logger.error(f"eq断言失败，预期结果：{ex}，实际结果：{re}")
            logger.error("用例失败！")
            raise e

    @staticmethod
    def contains(content, target):
        \"""
        断言包含
        :param content: 文本内容
        :param target: 目标文本
        :return:
        \"""
        try:
            assert str(content) in str(target)
        except AssertionError as e:
            logger.error(f"contains断言失败，目标文本{target}包含 文本{content}")
            raise e
    """
    create_file(os.path.join(project_name, "common", "handle_assert.py"), assert_content)
    create_folder(os.path.join(project_name, "apis"))
    # TODO: check
    create_file(os.path.join(project_name, "apis", "__init__.py"))
    demo_api_content = """import json
    
from common.base_api import BaseApi


class DefineDemo(BaseApi):
    
    def demo(self, body):
        \"""this is a demo api\"""
        payload = {
            'url': getattr(self, 'host') + '/demo/',
            'method': 'post',
            'headers': getattr(self, 'headers'),
            'data': {json.dumps(body)},
            
        }
        response = self.send_http(payload)
        return response
    """
    create_file(os.path.join(project_name, "apis", "demo.py"), demo_api_content)
    create_folder(os.path.join(project_name, "service"))
    create_file(os.path.join(project_name, "service", "__init__.py"))
    params_pool_content = """import threading

from jsonpath import jsonpath
from loguru import logger

from common.base_api import BaseApi


class ParamsPool(BaseApi):
    \"""
    set global common params
    \"""
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(ParamsPool, '_instance'):
            with cls._instance_lock:
                if not hasattr(ParamsPool, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance

    def init_common_params(self):
        setattr(self, 'name', 'test')
    """
    create_file(os.path.join(project_name, "service", "params_pool.py"), params_pool_content)
    func_pool_content = """from common.base_api import BaseApi


class FuncPool(BaseApi):
    \"""
    common function of help to make api params
    \"""
    
    def demo_func(self):
        pass

    """
    create_file(os.path.join(project_name, "service", "func_pool.py"), func_pool_content)
    create_folder(os.path.join(project_name, "cases"))
    create_file(os.path.join(project_name, "cases", "__init__.py"))
    testcase_path = os.path.join(project_name, "testcases")
    create_folder(testcase_path)
    create_file(os.path.join(testcase_path, "__init__.py"))
    create_folder(os.path.join(testcase_path, "test_api"))
    create_file(os.path.join(os.path.join(testcase_path, "test_api"), "__init__.py"))
    create_folder(os.path.join(testcase_path, "test_scenario"))
    create_file(os.path.join(os.path.join(testcase_path, "test_scenario"), "__init__.py"))
    create_folder(os.path.join(project_name, "fixtures"))
    create_file(os.path.join(project_name, "fixtures", "__init__.py"))
    fixture_env_content = """import os

import pytest
import yaml

from common.handle_path import CONF_DIR


@pytest.fixture(scope="session")
def conf():
    config_path = os.path.join(CONF_DIR, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)
    return config


@pytest.fixture(scope="session")
def env_vars(conf):
    class Env:
        config = conf
        env = config['env']
        host = config[env]["host"]
        account = config[env]["account"]
    return Env()
    """
    create_file(os.path.join(project_name, "fixtures", "fixture_env.py"), fixture_env_content)
    fixture_login_content = """import pytest
from loguru import logger
from requests import request

from common.base_api import BaseApi
from service.params_pool import ParamsPool


@pytest.fixture(scope='session')
def login(env_vars):
    logger.info('******************************开始配置全局前置条件******************************')
    host = env_vars.host
    account = env_vars.account
    setattr(BaseApi, 'host', host)
    setattr(BaseApi, 'account', account)

    resp_login = 1
    return resp_login


@pytest.fixture(scope='session', autouse=True)
def handle_headers(login):
    resp_login = login
    headers = {'Cookie': "cookie"}
    setattr(BaseApi, 'headers', headers)
    logger.info(f'设置全局请求头:{headers}')

@pytest.fixture(scope='session', autouse=True)
def make_params():
    logger.info('开始生成公共参数')
    pp = ParamsPool()
    pp.init_common_params()
    logger.info('******************************全局前置条件配置完成******************************')
    """
    create_file(os.path.join(project_name, "fixtures", "fixture_login.py"), fixture_login_content)
    create_folder(os.path.join(project_name, "conf"))
    config_content = """env: test
test:
  host: 'https://test.aomaker.com'
  account:
    user: 'aomaker'
    pwd: '123456'

release:
  host: 'https://release.aomaker.com'
  account:
    user: 'aomaker'
    pwd: '123456'
"""
    create_file(os.path.join(project_name, "conf", "config.yaml"), config_content)
    conftest_content = """import os
from loguru import logger
from common.handle_path import FIXTURE_DIR

for root, _, files in os.walk(FIXTURE_DIR):
    for file in files:
        if os.path.isfile(os.path.join(root, file)):
            if file.startswith("fixture_") and file.endswith(".py"):
                _fixture_name, _ = os.path.splitext(file)
                try:
                    exec(f"from fixtures.{_fixture_name} import *")
                    logger.info(f"导入fixture:{_fixture_name}成功")
                except:
                    pass
    """
    create_file(os.path.join(project_name, "conftest.py"), conftest_content)
    run_content = """import pytest
pytest.main(['-s', '-m demo'])
    """
    create_file(os.path.join(project_name, "run.py"), run_content)
    pytest_ini_content = """[pytest]
markers =
    smoke: smoke test
    regress: regress test
    """
    create_file(os.path.join(project_name, "pytest.ini"), pytest_ini_content)
    create_folder(os.path.join(project_name, "data"))
    datas_content = """job:
  submit_hpc_job:
    - title: '验证提交hpc作业-共享队列-sleep'
      variables:
        cmd_line_type: 'input'  # select
        cmd_line: 'sleep 10'
        name: 'sleep_auto'
        core_limit: 5
        software: ''
        queue_type: 'share_queue'
      expected: {"ret_code": 0}
    - title: '验证提交hpc作业-共享队列-普通脚本'
      variables:
        cmd_line_type: 'select'  # select
        input_file: 'work.sh'
        stdout_redirect_path: ''
        stderr_redirect_path: ''
        name: 'script_auto'
        core_limit: 5
        software: ''
        queue_type: 'share_queue'
      expected: {"ret_code": 0}
    """
    create_file(os.path.join(project_name, "data", "job_datas.yaml"), datas_content)
    datas_content = """hpc_smoke:
  - title: 'hpc冒烟用例'
    step:
      create_hpc_cluster:
        cluster_name: 'auto_hpc'
      add_nodes:
        cluster_type: 'hpc'
        node_role: 'login'
      submit_hpc_job:
        'cmd_line_type': 'input'
        'cmd_line': 'sleep 10'
        'name': 'sleep_auto'
        'core_limit': 5
        'software': ''
        'queue_type': 'share_queue'
      
ehpc_smoke:
  - title: 'ehpc冒烟用例'
    step:
      create_ehpc_cluster:
        cluster_name: 'auto_hpc'
      add_nodes:
        login:
          cluster_type: 'ehpc'
          node_role: 'login'
        compute:
          cluster_type: 'ehpc'
          node_role: 'compute'
      submit_ehpc_job:
        'cmd_line_type': 'input'
        'cmd_line': 'sleep 10'
        'name': 'sleep_auto'
        'core_limit': 5
        'software': ''
        'queue_type': 'share_queue'
    """
    create_file(os.path.join(project_name, "data", "case_datas.yaml"), datas_content)
    create_folder(os.path.join(project_name, "report"))

    return 0


def main_scaffold(args):
    ExtraArgument.create_venv = args.create_venv
    sys.exit(create_scaffold(args.project_name))
