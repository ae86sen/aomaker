# --coding:utf-8--
import os

# 项目根目录
BASEDIR = os.path.dirname(os.getcwd())
# BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 配置文件的路径
CONF_DIR = os.path.join(BASEDIR, "conf")
# 用例数据的目录
DATA_DIR = os.path.join(BASEDIR, "data")
# 日志文件目录
LOG_DIR = os.path.join(BASEDIR, "logs")
# 测试报告的路
REPORT_DIR = os.path.join(BASEDIR, "reports")
# 测试用例模块所在的目录
CASE_DIR = os.path.join(BASEDIR, "testcases")
# DB目录
DB_DIR = os.path.join(BASEDIR, "database")