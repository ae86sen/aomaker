import os
import sys
import re

import yaml

from aomaker.swagger2yaml import main_swagger2yaml
from aomaker.template import Template as Temp
from aomaker._log import logger

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
        for ao in req_data_list:
            dependent_api = ao.get('dependent_api')
            if dependent_api is not None:
                for dep in dependent_api:
                    module: str = dep.get('module')
                    api: str = dep.get('api')
                    extract: str = dep.get('extract')
                    api_params: dict = dep.get('api_params')
                    _, mod = module.split('.')
                    dep['module'] = f"from {module} import {mod}"
                    if api_params is None:
                        decorator = f"@dependence({mod}.{api},'{extract}')"
                    else:
                        params_list = [f"{key}='{value}'" for key, value in api_params.items()]
                        params_str = ",".join(params_list)
                        decorator = f"@dependence({mod}.{api},'{extract}', {params_str})"
                    dep['decorator'] = decorator
        # 判断是否存在该模块，模块中是否存在该类，该类中是否存在该方法，如果存在该方法，在data中删除该条
        # 如果不存在，将追加模板渲染进去
        if os.path.exists(f'{api_dir}/{module_name}.py'):
            # TODO: 类名不一定都是一个单词，有可能是多个单词组成
            class_name = module_name.capitalize()
            # 获取当前工程根目录
            project_root_path = os.getcwd()
            if project_root_path not in sys.path:
                # 将当前工程根目录加到导包路径中
                sys.path.insert(0, project_root_path)
            exec(f'from apis.{module_name} import {class_name}')
            class_type = locals()[f"{class_name}"]
            for req_data in req_data_list:
                if not hasattr(class_type, f'{req_data["method_name"]}'):
                    content = Temp.TEMP_ADDITIONAL_API.render(req_data)
                    with open(f'{api_dir}/{module_name}.py', mode='a', encoding='utf-8') as f:
                        f.write(content)
                        logger.info(f'生成 apis/{module_name}.py 成功!')
        else:
            content = Temp.TEMP_HAR_API.render(data)
            with open(f'{api_dir}/{module_name}.py', mode='w', encoding='utf-8') as f:
                f.write(content)
                logger.info(f'生成 apis/{module_name}.py 成功!')


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
