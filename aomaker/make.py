import os
import subprocess
import sys

import jinja2
import yaml
from loguru import logger

from aomaker.swagger2yaml import main_swagger2yaml
from aomaker.template import Template as Temp


def _create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        with open(f'{dir_path}/__init__.py', mode='w', encoding='utf-8') as f:
            f.write('')


def create_api_dir(workspace):
    # 创建api目录
    api_dir = os.path.join(workspace, 'apis')
    _create_dir(api_dir)
    return api_dir


def create_service_api_dir(workspace):
    # 创建service目录
    service_dir: str = os.path.join(workspace, 'service')
    _create_dir(service_dir)
    # 创建service_api目录
    service_api_dir = os.path.join(service_dir, 'service_api')
    _create_dir(service_api_dir)
    return service_api_dir


def create_api_file(yaml_data, temp, api_dir):
    for key, value in yaml_data.items():
        data = {
            "class_name": key,
            "func_list": value,
        }
        content = temp.render(data)
        with open(f'{api_dir}/{key}.py', mode='w', encoding='utf-8') as f:
            f.write(content)


def make_api_file(parm, style):
    """
    通过swagger生成api和ao文件
    :param parm: swagger's url or json file
    :param style: qingcloud or restful,default restful
    :return:
    """
    main_swagger2yaml(parm, style)
    yaml_path = 'swagger.yaml'
    yaml_data = yaml.safe_load(open(yaml_path, mode='r', encoding='utf-8'))
    # 创建api目录
    workspace = os.getcwd()
    api_dir = create_api_dir(workspace)
    # 生成api文件
    create_api_file(yaml_data, Temp.TEMP_HPC_API, api_dir)
    # 创建service目录
    # 创建service_api目录
    service_api_dir = create_service_api_dir(workspace)
    # 生成service_api文件
    create_api_file(yaml_data, Temp.TEMP_HPC_AO, service_api_dir)


def make_api_file_from_yaml(req_data_list: list):
    """
    通过testcase_yaml生成api和ao文件以及追加api类没有的方法
    args:
        'req_data_list': [
                {'class_name': 'cluster',
                 'method_name': 'list',
                 'request': {'url': 'https://aomaker.com', 'method': 'POST', 'data': {'params': ''},
                    'method': 'GET'}
                    },
                 {'class_name': 'job',
                 'method_name': 'list',
                 'request': {'url': 'https://aomaker.com', 'method': 'POST', 'data': {'params': ''},
                    'method': 'GET'}
                    }
                 ]
    """
    def convert_ao_to_the_same_class(ao_li, filed):
        """
        args:
            ao_li = [
                    {"country": "China", "name": "Ace"},
                    {"country": "China", "name": "Ale"},
                    {"country": "USA", "name": "Jhon"},
                    {"country": "China", "name": "Lee"},
                    {"country": "USA", "name": "Mark"},
                    {"country": "UK", "name": "Bruce"},
                    ]
            filed = "country"
        return:
                    {
                    "China": [{"country": "China", "name": "Ace"},
                              {"country": "China", "name": "Ale"}, {"country": "China", "name": "Lee"}],
                    "USA": [{"country": "USA", "name": "Jhon"}, {"country": "USA", "name": "Mark"}],
                    "UK": [{"country": "UK", "name": "Bruce"}, ]
                    }
        """
        new_dic = {}
        country_list = set([i.get(filed) for i in ao_li])
        for i in country_list:
            new_dic[f'{i}'] = []
        for i in ao_li:
            key = i.get(filed)
            new_dic[key].append(i)
        return new_dic
    req_data_dic = convert_ao_to_the_same_class(req_data_list, "class_name")
    # 1.create api folder
    workspace = os.getcwd()
    api_dir = create_api_dir(workspace)
    # 2.create api definition file
    for module_name, req_data_list in req_data_dic.items():
        data = {
            "module_name": module_name,
            "ao_list": req_data_list
        }
        # 判断是否存在该模块，模块中是否存在该类，该类中是否存在该方法，如果存在该方法，在data中删除该条
        # 如果不存在，将追加模板渲染进去
        if os.path.exists(f'{api_dir}/{module_name}.py'):
            # TODO: 类名不一定都是一个单词，有可能是多个单词组成
            class_name = module_name.capitalize()
            exec(f'from apis.{module_name} import Define{class_name}')
            class_type = locals()[f"Define{class_name}"]
            for req_data_list in req_data_list:
                if not hasattr(class_type, f'api_{req_data_list["method_name"]}'):
                    content = Temp.TEMP_ADDITIONAL_API.render(req_data_list)
                    with open(f'{api_dir}/{module_name}.py', mode='a', encoding='utf-8') as f:
                        f.write(content)
                        logger.info(f'make apis/{module_name}.py successfully!')
        else:
            content = Temp.TEMP_HAR_API.render(data)
            # print(content)
            with open(f'{api_dir}/{module_name}.py', mode='w', encoding='utf-8') as f:
                f.write(content)
                logger.info(f'make apis/{module_name}.py successfully!')
    # 3.create ao folder
    # 创建service_api目录
    service_api_dir = create_service_api_dir(workspace)
    # 4.create ao file
    for module_name, req_data_list in req_data_dic.items():
        data = {
            "module_name": module_name,
            "ao_list": req_data_list
        }
        # 判断是否存在该模块，模块中是否存在该类，该类中是否存在该方法，如果存在该方法，在data中删除该条
        # 如果不存在，将追加模板渲染进去
        if os.path.exists(f'{service_api_dir}/{module_name}.py'):
            class_name = module_name.capitalize()
            exec(f'from service.service_api.{module_name} import {class_name}')
            class_type = locals()[class_name]
            for req_data_list in req_data_list:
                if not hasattr(class_type, f'{req_data_list["method_name"]}'):
                    content = Temp.TEMP_ADDITIONAL_AO.render(req_data_list)
                    with open(f'{service_api_dir}/{module_name}.py', mode='a', encoding='utf-8') as f:
                        f.write(content)
                        logger.info(f'make service_api/{module_name}.py successfully!')
        else:
            content = Temp.TEMP_HAR_AO.render(data)
            # print(content)
            with open(f'{service_api_dir}/{module_name}.py', mode='w', encoding='utf-8') as f:
                f.write(content)
                logger.info(f'make service_api/{module_name}.py successfully!')


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
    """
    通过标准restful风格的swagger生成api和ao文件
    :param parm: swagger's url or json file
    :return:
    """
    main_swagger2yaml(parm)
    yaml_path = 'swagger.yaml'
    yaml_data = yaml.safe_load(open(yaml_path, mode='r', encoding='utf-8'))
    # 创建api目录
    workspace = os.getcwd()
    api_dir = create_api_dir(workspace)
    # 生成api文件
    _parse_yaml_data(api_dir, Temp.TEMP_RESTFUL_API, yaml_data)
    # 创建service目录
    # 创建service_api目录
    service_api_dir = create_service_api_dir(workspace)
    # 生成service_api文件
    _parse_yaml_data(service_api_dir, Temp.TEMP_RESTFUL_AO, yaml_data)


def main_make(param, style='restful'):
    try:
        if style == 'restful':
            make_api_file_restful(param)
        elif style == 'qingcloud':
            make_api_file(param, style)
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


