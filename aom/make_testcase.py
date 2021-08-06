import os
import sys

import jinja2
import yaml

__TEMPLATE__ = jinja2.Template(
    """import os

import pytest
import yaml

from service.service_api.{{api}} import {{api | capitalize}}
from common.base_api import BaseApi
from common.handle_path import DATA_DIR

case_data_path = os.path.join(DATA_DIR, '{{api}}_datas.yaml')
datas = yaml.safe_load(open(case_data_path, encoding='utf-8'))


class Test{{api | capitalize}}({{api | capitalize}}):
    {% for case in case_list %}
    @pytest.mark.parametrize('data', datas['{{api}}']['{{case}}'])
    def test_{{case}}(self, data):
        res = self.case_{{case}}(data['variables'])
        assert res['ret_code'] == data['expected']
    {% endfor %}
"""
)

from loguru import logger


def make_testcase_file(data_file):
    yaml_data = yaml.safe_load(open(data_file, mode='r', encoding='utf-8'))
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
    content = __TEMPLATE__.render(data)
    with open(f'{testcase_api_dir}/test_{api}.py', mode='w', encoding='utf-8') as f:
        f.write(content)


def main_make_case(data_file):
    try:
        make_testcase_file(data_file)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


def init_make_case_parser(subparsers):
    """ make api testcase: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "a2case", help="api object to testcase.",
    )
    parser.add_argument(
        "data_path", type=str, nargs="?", help="testcase data path"
    )

    return parser

# main_make_case('job_datas.yaml')
