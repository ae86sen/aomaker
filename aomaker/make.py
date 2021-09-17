import os
import sys

import jinja2
import yaml
from loguru import logger

from aomaker.swagger2yaml import main_swagger2yaml

__TEMPLATE_API__ = jinja2.Template(
    """import json
from common.base_api import BaseApi


class Define{{ class_name | title}}(BaseApi):
    {% for func,v in func_list.items() %}
    {% if v.method != 'get'%}def api_{{func}}(self, body):{% else %}def api_{{func}}(self):{% endif %}
        \"""{{v.description}}""\"
        payload = {
            'url': f'{getattr(self, "host")}{getattr(self, "base_path")}',
            'method': '{{v.method}}',
            'headers': getattr(self, 'headers'),
            'params': {'action': '{{v.path}}'},
            {% if v.method != 'get'%}'data': {
                'params': json.dumps(body)
            }{% endif %}
        }
        response = self.send_http(payload)
        return response{% endfor %}   
"""
)

__TEMPLATE_SERVICE__ = jinja2.Template(
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

__RESTFUL_TEMPLATE_API__ = jinja2.Template(
    """from common.base_api import BaseApi


class Define{{ class_name}}(BaseApi):
    {% for func,v in func_list.items() %}
    def api_{{func}}(self, req_params):
        \"""{{v.summary}}""\"
        payload = {
            'url': f'{getattr(self, "host")}{getattr(self, "base_path")}',
            'method': 'POST',
            'headers': getattr(self, 'headers'),
            'parameters': req_params.get('query'),
            'json': req_params.get('body')
        }
        header_params = req_params.get('header')
        if header_params:
            payload['headers'].update(header_params)
        {% if v.var %}path_params = req_params.get('path')
        payload['headers']['X-Path'] = f'{{v.path}}'{% else %}payload['headers']['X-Path'] = '{{v.path}}'{% endif %}
        payload['headers']['X-Method'] = '{{v.method}}'
        response = self.send_http(payload)
        return response
        {% endfor %}   
"""
)

__RESTFUL_TEMPLATE_SERVICE__ = jinja2.Template(
    """import threading
from apis.{{ module_name }} import Define{{ class_name }}


class {{ class_name }}(Define{{ class_name}}):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr({{ class_name }}, '_instance'):
            with cls._instance_lock:
                if not hasattr({{ class_name }}, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance    
    {% for func,v in func_list.items() %}
    def {{func}}(self):
        \"""{{v.summary}}""\"
        req_params = {{v.req_params}}
        res = self.get_resp_json(self.api_{{ func }}(req_params))
        return res
    {% endfor %}   
"""
)


def make_api_file(parm):
    main_swagger2yaml(parm)
    yaml_path = 'swagger.yaml'
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
        content = __TEMPLATE_API__.render(data)
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
        content = __TEMPLATE_SERVICE__.render(data)
        with open(f'{service_api_dir}/{key}.py', mode='w', encoding='utf-8') as f:
            f.write(content)


def _parse_yaml_data(dir, template, yaml_data):
    def change_cap(s: str):
        x = [i.capitalize() for i in s.split('_')]
        cap = ''.join(x)
        return cap

    for key, value in yaml_data.items():
        data = {
            "class_name": key.capitalize(),
            "func_list": value,
        }
        for k, v in list(value.items()):
            # 处理方法名中有-的情况
            if '-' in k:
                new_key = k.replace('-', '_')
                value[new_key] = value.pop(k)
            # 处理方法名中有{}的情况
            if '{' in k:
                new_key = k.replace('{', '').replace('}', '')
                value[new_key] = value.pop(k)
            # 处理方法中的path有{}变量的情况
            path = v.get('path')
            if '{' in path:
                import re
                # 将{}中的内容提取出来，放到data['var']中
                var: list = re.findall(r'[{](.*?)[}]', path)
                for i in var:
                    path = path.replace(f'{i}', f'path_params["{i}"]', 1)
                v['path'] = path
                v['var'] = ', '.join(var)
        # 处理key(模块)中有-或_的情况
        if '-' in key:
            key = key.replace('-', '_')
            data['class_name'] = change_cap(key)
        elif '_' in key:
            data['class_name'] = change_cap(key)
        data['module_name'] = key
        content = template.render(data)
        with open(f'{dir}/{key}.py', mode='w', encoding='utf-8') as f:
            f.write(content)


def make_api_file_restful(parm):
    main_swagger2yaml(parm)
    yaml_path = 'swagger.yaml'
    yaml_data = yaml.safe_load(open(yaml_path, mode='r', encoding='utf-8'))
    # 创建api目录
    workspace = os.getcwd()
    api_dir = os.path.join(workspace, 'apis')
    if not os.path.exists(api_dir):
        os.mkdir(api_dir)
        with open(f'{api_dir}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')

    # 生成api文件
    _parse_yaml_data(api_dir, __RESTFUL_TEMPLATE_API__, yaml_data)
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
    _parse_yaml_data(service_api_dir, __RESTFUL_TEMPLATE_SERVICE__, yaml_data)


def main_make(param, style='restful'):
    try:
        if style == 'restful':
            make_api_file_restful(param)
        elif style == 'qingcloud':
            make_api_file(param)
        else:
            print('Currently, only two styles(restful and qingcloud) are supported!please input correct style!')
            sys.exit(1)
    except Exception as e:
        logger.error(e)
        raise e
        sys.exit(1)


def init_make_parser(subparsers):
    """ make api object: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "make", help="Convert swagger to Api object.",
    )
    parser.add_argument(
        "-s", "--style", dest="style", type=str, nargs="?",
        help="set template style of swagger.default template: restful."
    )
    parser.add_argument(
        "param", type=str, nargs="?",
        help="The parameters must be swagger url or json file path.\n"
             "if param is swagger url,it should be like http://xxxx/api/swagger.json;\n"
             "if param is json file path,it should be like 'xx/xxx.json'"
    )
    return parser

# main_make('swagger.yaml')
