# --coding:utf-8--
import sys

# debug使用
sys.path.insert(0, 'D:\\项目列表\\aomaker')
from aomaker import path


# database
class DataBase:
    DB_NAME = "aomaker.db"
    CONFIG_TABLE = 'config'
    CACHE_TABLE = 'cache'
    SCHEMA_TABLE = 'schema'
    CACHE_VAR_NAME = 'var_name'
    CACHE_RESPONSE = 'response'
    CONFIG_KEY = 'key'
    CONFIG_VALUE = 'value'
    SCHEMA_API_NAME = 'api_name'
    SCHEMA_SCHEMA = 'schema'


# log
class Log:
    LOG_NAME = "log.log"
    DEFAULT_LEVEL = "debug"


# config
class Conf:
    CONF_NAME = "config.yaml"
    UTILS_CONF_NAME = "utils.yaml"
    CURRENT_ENV_KEY = 'env'
    CONF_DIR = "conf/"


# allure
class Allure:
    JSON_DIR = "reports/json"
    HTML_DIR = "reports/html"
