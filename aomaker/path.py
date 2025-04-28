# --coding:utf-8--
import os

from aomaker._constants import Log

# 项目根目录
BASEDIR = os.getcwd()
# BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 配置文件的路径
CONF_DIR = os.path.join(BASEDIR, "conf")
# API目录
API_DIR = os.path.join(BASEDIR, "apis")
# 用例数据的目录
DATA_DIR = os.path.join(BASEDIR, "data")
# 日志文件目录
LOG_DIR = os.path.join(BASEDIR, "logs")
# 日志文件目录
LOG_FILE_path = os.path.join(LOG_DIR, Log.LOG_NAME)
# 测试报告的路
REPORT_DIR = os.path.join(BASEDIR, "reports")
# allure json目录
ALLURE_JSON_DIR = os.path.join(REPORT_DIR, "json")
# 测试用例模块所在的目录
CASE_DIR = os.path.join(BASEDIR, "testcases")
# DB目录
DB_DIR = os.path.join(BASEDIR, "database")
# pytest.ini文件路径
PYTEST_INI_DIR = os.path.join(BASEDIR, "pytest.ini")
# aomaker html路径
AOMAKER_HTML = os.path.join(REPORT_DIR, "aomaker.html")

AOMAKER_YAML_PATH = os.path.join(CONF_DIR, "aomaker.yaml")

DIST_STRATEGY_PATH = os.path.join(CONF_DIR, "dist_strategy.yaml")

MIDDLEWARES_DIR = os.path.join(BASEDIR, "middlewares")
MIDDLEWARE_CONFIG_PATH = os.path.join(MIDDLEWARES_DIR, "middlewares.yaml")