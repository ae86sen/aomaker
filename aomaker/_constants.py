# --coding:utf-8--

PROJECT_ROOT_FILE = ".aomaker"


# database
class DataBase:
    DB_DIR_NAME = "database"
    DB_NAME = "aomaker.db"
    CONFIG_TABLE = 'config'
    CACHE_TABLE = 'cache'
    SCHEMA_TABLE = 'schema'
    STATS_TABLE = 'statistics'
    CACHE_VAR_NAME = 'var_name'
    CACHE_RESPONSE = 'response'
    CACHE_WORKER = 'worker'
    CACHE_API_INFO = 'api_info'
    CONFIG_KEY = 'conf_name'
    CONFIG_VALUE = 'value'
    SCHEMA_API_NAME = 'api_name'
    SCHEMA_SCHEMA = 'schema'
    STATS_PACKAGE = 'package'
    STATS_API_NAME = 'api_name'


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
