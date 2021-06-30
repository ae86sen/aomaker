import os

import jinja2
import yaml

__TEMPLATE__ = jinja2.Template(
    """
import json
from common.base_api import BaseApi


class {{ class_name | title}}(BaseApi):
    {% for func,v in func_list.items() %}
    def {{func}}(self):
        \"""{{v.description}}""\"
        payload = {
            'url': self.host + '/portal_api/',
            'method': '{{v.method}}',
            'headers': getattr(self, 'headers'),
            'params': {'action': '{{v.path}}'},
            {% if v.method != 'get'%}
            'data': {
                'params': {{v.body}}
            }
            {% endif %}
        }
        response = self.send_http(payload)
        return response
    {% endfor %}   
"""
)


def make_api_file():
    yaml_data = yaml.safe_load(open('./conf/swagger.yaml', mode='r', encoding='utf-8'))
    # 创建api目录
    workspace = os.getcwd()
    api_dir = os.path.join(workspace, 'api')
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

# yaml_data = yaml.safe_load(open('./conf/swagger.yaml', mode='r', encoding='utf-8'))
# # print(yaml_data)
# for key, value in yaml_data.items():
#     data = {
#         "class_name": key,
#         "func_list": value,
#     }
#     content = __TEMPLATE__.render(data)
#     with open(f'{key}.py', mode='w', encoding='utf-8') as f:
#         f.write(content)
make_api_file()