import os
import sys

import jinja2
import yaml

__TEMPLATE__ = jinja2.Template(
    """import json
from common.base_api import BaseApi


class Define{{ class_name | title}}(BaseApi):
    {% for func,v in func_list.items() %}
    {% if v.method != 'get'%}
    def api_{{func}}(self, body):{% else %}
    def api_{{func}}(self):{% endif %}
        \"""{{v.description}}""\"
        payload = {
            'url': getattr(self, 'host') + '/portal_api/',
            'method': '{{v.method}}',
            'headers': getattr(self, 'headers'),
            'params': {'action': '{{v.path}}'},
            {% if v.method != 'get'%}
            'data': {
                'params': json.dumps(body)
            }
            {% endif %}
        }
        response = self.send_http(payload)
        return response
    {% endfor %}   
"""
)

__TEMPLATE2__ = jinja2.Template(
    """import threading
from apis.{{ class_name }} import Define{{ class_name | title}}


class {{ class_name | title}}(Define{{ class_name | title}}):
    _instance_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not hasattr({{ class_name | title}}, '_instance'):
            with cls._instance_lock:
                if not hasattr({{ class_name | title}}, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance    
    {% for func,v in func_list.items() %}
    def {{func}}(self):{% if v.method != 'get'%}
        body = {{ v.body }}
        res = self.get_resp_json(self.api_{{ func }}(body)){% else %}
        res = self.get_resp_json(self.api_{{ func }}()){% endif %}
        return res
    {% endfor %}   
"""
)

from loguru import logger


def make_api_file(yaml_path):
    yaml_data = yaml.safe_load(open(yaml_path, mode='r', encoding='utf-8'))
    # 创建api目录
    workspace = os.getcwd()
    api_dir = os.path.join(workspace, 'apis')
    if not os.path.exists(api_dir):
        os.mkdir(api_dir)
        with open(f'{api_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')
    # 生成api文件
    for key, value in yaml_data.items():
        data = {
            "class_name": key,
            "func_list": value,
        }
        content = __TEMPLATE__.render(data)
        with open(f'{api_dir}/{key}.py', mode='w', encoding='utf-8') as f:
            f.write(content)
    # 创建service目录
    service_dir: str = os.path.join(workspace, 'service')
    if not os.path.exists(service_dir):
        os.mkdir(service_dir)
        with open(f'{service_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')
    # 创建service_api目录
    service_api_dir = os.path.join(service_dir, 'service_api')
    if not os.path.exists(service_api_dir):
        os.mkdir(service_api_dir)
        with open(f'{service_api_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')
    # 生成service_api文件
    for key, value in yaml_data.items():
        data = {
            "class_name": key,
            "func_list": value,
        }
        content = __TEMPLATE2__.render(data)
        with open(f'{service_api_dir}/{key}.py', mode='w', encoding='utf-8') as f:
            f.write(content)


# def make_service_api_file(yaml_path):
#     yaml_data = yaml.safe_load(open(yaml_path, mode='r', encoding='utf-8'))
#     # 创建service目录
#     workspace = os.getcwd()
#     service_dir = os.path.join(workspace, 'service')
#     print(service_dir)
#     if not os.path.exists(service_dir):
#         os.mkdir(service_dir)
#         with open(f'{service_dir}/__init__.py', mode='w', encoding='utf-8') as f:
#             f.write('')
#     # 创建service_api目录
#     service_api_dir = os.path.join(service_dir, 'service_api')
#     if not os.path.exists(service_api_dir):
#         os.mkdir(service_api_dir)
#         with open(f'{service_api_dir}/__init__.py', mode='w', encoding='utf-8') as f:
#             f.write('')
#     # 生成service_api文件
#     for key, value in yaml_data.items():
#         data = {
#             "class_name": key,
#             "func_list": value,
#         }
#         content = __TEMPLATE2__.render(data)
#         with open(f'{service_api_dir}/{key}.py', mode='w', encoding='utf-8') as f:
#             f.write(content)


def main_make(yaml_path):
    try:
        make_api_file(yaml_path)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


def init_make_parser(subparsers):
    """ make api object: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "make", help="Convert YAML of API definition to Api object.",
    )
    parser.add_argument(
        "yaml_path", type=str, nargs="?", help="Specify YAML of API definition file path"
    )

    return parser


# main_make('swagger.yaml')
