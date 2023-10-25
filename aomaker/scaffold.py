import os
import sys

from aomaker._constants import DataBase as DB
from aomaker._log import logger


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
        logger.error(
            f"项目目录：{project_name} 已存在, 请重新设置一个目录名称."
        )
        return 1
    elif os.path.isfile(project_name):
        logger.error(
            f"项目目录：{project_name} 存在同名文件，请重新设置一个目录名称"
        )
        return 1

    def create_folder(path):
        os.makedirs(path)
        msg = f"创建目录: {path}"
        logger.info(msg)

    def create_file(path, file_content=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        msg = f"创建文件: {path}"
        logger.info(msg)

    def create_table(db_object, table_name: str):
        table_attr = get_table_attribute(table_name)
        key = table_attr.get('key')
        value = table_attr.get('value')
        worker = table_attr.get('worker')
        api_info = table_attr.get('api_info')
        if worker is not None:
            sql = f"""create table {table_name}({key} text,{value} text,{worker} text,{api_info} text);"""
        else:
            sql = f"""create table {table_name}({key} text,{value} text);"""
        db_object.execute_sql(sql)
        if table_name != "cache":
            sql2 = f"""create unique index {table_name}_{key}_uindex on {table_name} ({key});"""
            db_object.execute_sql(sql2)
        msg = f"创建数据表：{table_name}"
        logger.info(msg)

    def get_table_attribute(table_name: str):
        tables_attr = {
            DB.CACHE_TABLE: {'key': DB.CACHE_VAR_NAME, 'value': DB.CACHE_RESPONSE, 'worker': DB.CACHE_WORKER,
                             'api_info': DB.CACHE_API_INFO},
            DB.CONFIG_TABLE: {'key': DB.CONFIG_KEY, 'value': DB.CONFIG_VALUE},
            DB.SCHEMA_TABLE: {'key': DB.SCHEMA_API_NAME, 'value': DB.SCHEMA_SCHEMA}
        }
        return tables_attr.get(table_name)

    logger.info("---------------------开始创建脚手架---------------------")
    create_folder(project_name)
    create_folder(os.path.join(project_name, "yamlcase"))
    create_folder(os.path.join(project_name, "apis"))
    create_file(os.path.join(project_name, "apis", "__init__.py"))
    demo_api_content = """from aomaker.base.base_api import BaseApi


class DemoApi(BaseApi):
    
    def demo_get(self):
        \"""this is a demo get api\"""
        http_data = {
            'api_path': '/test',
            'method': 'get',
            'params': {'name': 'aomaker'}
        }
        response = self.send_http(http_data)
        return response
    
    def demo_post(self):
        \"""this is a demo post api\"""
        body = {
            'name': 'aomaker',
            'version': 'v2'
        }
        http_data = {
            'api_path': '/test',
            'method': 'get',
            'params': {'name': 'aomaker'},
            'data': body
        }
        response = self.send_http(http_data)
        return response
    """
    create_file(os.path.join(project_name, "apis", "demo.py"), demo_api_content)
    testcase_path = os.path.join(project_name, "testcases")
    create_folder(testcase_path)
    create_file(os.path.join(testcase_path, "__init__.py"))
    create_folder(os.path.join(testcase_path, "test_api"))
    create_file(os.path.join(os.path.join(testcase_path, "test_api"), "__init__.py"))
    create_folder(os.path.join(testcase_path, "test_scenario"))
    create_file(os.path.join(os.path.join(testcase_path, "test_scenario"), "__init__.py"))
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
    create_file(os.path.join(project_name, "conf", "aomaker.yaml"), "")
    utils_config_content = """wechat: 
    webhook:
    """
    create_file(os.path.join(project_name, "conf", "utils.yaml"), utils_config_content)
    conftest_content = """"""
    create_file(os.path.join(project_name, "conftest.py"), conftest_content)
    run_content = """\"""测试任务运行说明

================================单进程启动================================
启动函数：run()
参数: 接收一个列表，pytest和arun支持的所有参数
Example：
run(["-s","-m demo","-e testing"])

================================多线程启动================================
启动函数：threads_run()           
参数：
    根据传入参数类型不同，启动不同的多线程分配模式
    list: dist-mark模式
    str：dist-file模式
    dict：dist-suite模式
多线程分配模式：
    1.dist-mark: 根据mark标记来分配线程，每个mark标记的线程独立运行
        example：
            threads_run(["-m demo1","-m demo2","-m demo3"])
            将启动三个子线程，分别执行标记为demo1,demo2,demo3的case
    2.dist-file: 根据测试文件来分配线程，每个文件下的case由独立线程运行
        example：
            threads_run({"path":"testcases/test_api"})
            testcases/test_api目录下有多少个测试文件，就启动多少个子线程来运行
    3.dist-suite: 根据测试套件来分配线程，每个套件下的case由独立的线程运行
        example：
            threads_run("testcases/test_api")
            testcases/test_api目录下有多少个测试套件，就启动多少个子线程来运行
            
================================多进程启动================================
****注意：windows下暂时不支持，linux和mac支持****
启动函数：processes_run()           
参数：
    根据传入参数类型不同，启动不同的多线程分配模式
    list: dist-mark模式
    str：dist-file模式
    dict：dist-suite模式
多线程分配模式：
    同多进程
=========================================================================
\"""
from aomaker.runner import run, processes_run, threads_run

from login import Login

if __name__ == '__main__':
    run(['-m demo'], login=Login())"""
    create_file(os.path.join(project_name, "run.py"), run_content)
    pytest_ini_content = """[pytest]
markers =
    smoke: smoke test
    regress: regress test
    """
    create_file(os.path.join(project_name, "pytest.ini"), pytest_ini_content)
    login_content = """from requests import request

from aomaker.fixture import BaseLogin


class Login(BaseLogin):

    def login(self) -> dict:
        resp_login = {}
        return resp_login

    def make_headers(self, resp_login:dict) -> dict:
        headers = {
            'Cookie': f'csrftoken=aomakerniubility'}
        return headers
    """
    create_file(os.path.join(project_name, "login.py"), login_content)
    create_file(os.path.join(project_name, "hooks.py"), "")
    data_path = os.path.join(project_name, "data")
    create_folder(data_path)
    create_folder(os.path.join(data_path, "api_data"))
    create_folder(os.path.join(data_path, "scenario_data"))
    create_folder(os.path.join(project_name, "reports"))
    create_folder(os.path.join(project_name, "logs"))
    db_dir_path = os.path.join(project_name, "database")
    create_folder(db_dir_path)
    from aomaker.database.sqlite import SQLiteDB
    db_file_path = os.path.join(db_dir_path, DB.DB_NAME)
    db = SQLiteDB(db_path=db_file_path)
    create_table(db, DB.CONFIG_TABLE)
    create_table(db, DB.CACHE_TABLE)
    create_table(db, DB.SCHEMA_TABLE)
    logger.info("---------------------脚手架创建完成---------------------")

    return 0


def main_scaffold(args):
    ExtraArgument.create_venv = args.create_venv
    sys.exit(create_scaffold(args.project_name))


if __name__ == '__main__':
    create_scaffold('FFFF')
