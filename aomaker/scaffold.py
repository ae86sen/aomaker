import os
import sys

# debug使用
sys.path.insert(0, 'D:\\项目列表\\aomaker')
from aomaker.extension.database.sqlite import SQLiteDB
from aomaker._constants import DataBase as DB


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
        print(
            f"项目目录：{project_name} 已存在, 请重新设置一个目录名称."
        )
        return 1
    elif os.path.isfile(project_name):
        print(
            f"项目目录：{project_name} 存在同名文件，请重新设置一个目录名称"
        )
        return 1

    def create_folder(path):
        os.makedirs(path)
        msg = f"创建目录: {path}"
        print(msg)

    def create_file(path, file_content=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        msg = f"创建文件: {path}"
        print(msg)

    def create_table(db_object: SQLiteDB, table_name: str):
        table_attr = get_table_attribute(table_name)
        key = table_attr.get('key')
        value = table_attr.get('value')
        sql = f"""create table {table_name}({key} text,{value} text);"""
        sql2 = f"""create unique index {table_name}_{key}_uindex on {table_name} ({key});"""
        db_object.execute_sql(sql)
        db_object.execute_sql(sql2)
        msg = f"创建数据表：{table_name}"
        print(msg)

    def get_table_attribute(table_name: str):
        tables_attr = {
            DB.CACHE_TABLE: {'key': DB.CACHE_VAR_NAME, 'value': DB.CACHE_RESPONSE},
            DB.CONFIG_TABLE: {'key': DB.CONFIG_KEY, 'value': DB.CONFIG_VALUE},
            DB.SCHEMA_TABLE: {'key': DB.SCHEMA_API_NAME, 'value': DB.SCHEMA_SCHEMA}
        }
        return tables_attr.get(table_name)

    print("---------------------开始创建脚手架---------------------")
    create_folder(project_name)
    create_folder(os.path.join(project_name, "flow2yaml"))
    create_folder(os.path.join(project_name, "apis"))
    create_file(os.path.join(project_name, "apis", "__init__.py"))
    demo_api_content = """from aomaker.base.base_api import BaseApi


class DemoApi(BaseApi):
    
    def demo_get(self):
        \"""this is a demo get api\"""
        http_data = {
            'api_path': '/test'
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
            'api_path': '/test'
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
  zone: 'asia'
  user_id: 'usr-xasdasd'
  
release:
  host: 'https://release.aomaker.com'
  account:
    user: 'aomaker'
    pwd: '123456'
  zone: 'eu'
  user_id: 'usr-jaskdda'
"""
    create_file(os.path.join(project_name, "conf", "config.yaml"), config_content)
    conftest_content = """"""
    create_file(os.path.join(project_name, "conftest.py"), conftest_content)
    run_content = """from aomaker import runner
    
    runner.main()
    runner.threads_main()
    runner.process_main()
    """
    create_file(os.path.join(project_name, "run.py"), run_content)
    pytest_ini_content = """[pytest]
markers =
    smoke: smoke test
    regress: regress test
    """
    create_file(os.path.join(project_name, "pytest.ini"), pytest_ini_content)
    data_path = os.path.join(project_name, "data")
    create_folder(data_path)
    create_folder(os.path.join(data_path, "api_data"))
    create_folder(os.path.join(data_path, "scenario_data"))
    create_folder(os.path.join(project_name, "reports"))
    create_folder(os.path.join(project_name, "logs"))
    db_dir_path = os.path.join(project_name, "database")
    create_folder(db_dir_path)
    db_file_path = os.path.join(db_dir_path, DB.DB_NAME)
    db = SQLiteDB(db_path=db_file_path)
    create_table(db, DB.CONFIG_TABLE)
    create_table(db, DB.CACHE_TABLE)
    create_table(db, DB.SCHEMA_TABLE)
    print("---------------------脚手架创建完成---------------------")

    return 0


def main_scaffold(args):
    ExtraArgument.create_venv = args.create_venv
    sys.exit(create_scaffold(args.project_name))


if __name__ == '__main__':
    create_scaffold('tttttttt')
