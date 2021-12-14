import os
import sys

from loguru import logger

from aomaker import utils
from aomaker.template import Template as Temp


def make_testcase_file(data_file):
    yaml_data = utils.load_yaml(data_file)
    # 创建testcase目录
    workspace = os.getcwd()
    testcase_dir = os.path.join(workspace, 'testcases')
    testcase_api_dir = os.path.join(testcase_dir, 'test_api')
    if not os.path.exists(testcase_dir):
        os.mkdir(testcase_dir)
        with open(f'{testcase_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')
    if not os.path.exists(testcase_api_dir):
        os.mkdir(testcase_api_dir)
        with open(f'{testcase_api_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')
    # 生成api文件
    # print(yaml_data.keys())
    api = list(yaml_data.keys())[0]
    case_list = list(yaml_data[api].keys())
    data = {
        "api": api,
        "case_list": case_list
    }
    content = Temp.TEMP_API_CASE.render(data)
    with open(f'{testcase_api_dir}/test_{api}.py', mode='w', encoding='utf-8') as f:
        f.write(content)


def main_make_case(data_file):
    try:
        make_testcase_file(data_file)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


def init_make_case_parser(subparsers):
    """ make api testcases: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "mcase", help="make testcases by api object.",
    )
    parser.add_argument(
        "data_path", type=str, nargs="?", help="testcases data path"
    )

    return parser


# main_make_case('job_datas.yaml')
