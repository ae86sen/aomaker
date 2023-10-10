import keyword
import requests
import yaml

from aomaker._log import logger


def __parse_definitions(data_definitions: dict):
    """解析swagger中的definitions"""
    dic = {}
    for key, value in data_definitions.items():
        properties = {}
        properties_dic = value.get('properties')
        if properties_dic:
            for k, v in properties_dic.items():
                items = v.get('items')
                if items:
                    ref = items.get('$ref')
                    if ref:
                        definition_key = ref.split('/')[-1]
                        properties[k] = {'$ref': definition_key}
                else:
                    properties[k] = ''
        dic[key] = properties
    for value in dic.values():
        for k, v in value.items():
            if isinstance(v, dict):
                ref = v.get('$ref')
                if ref:
                    value[k] = dic[ref]
    return dic


def _parse_swagger_restful(parm):
    """解析swagger"""
    if parm.startswith('http'):
        try:
            res = requests.request('get', parm).json()
        except Exception as e:
            logger.error('request failed!')
            raise e
        data_path = res.get('paths')
        data_definitions = res.get('definitions')
    elif parm.endswith('.json') and not parm.startswith('http'):
        yaml_data = yaml.safe_load(open(parm, mode='r', encoding='utf-8'))
        data_path = yaml_data.get('paths')
        data_definitions = yaml_data.get('definitions')
    else:
        logger.error("the parameters must be url or json file path")
        raise TypeError
    req_properties = __parse_definitions(data_definitions)
    # print(req_properties)
    final_data = {}
    for path, value in data_path.items():
        # print(path)
        key = path.split('/')
        if key[-1] == '':
            del key[-1]
        if keyword.iskeyword(key[-1]):
            key[-1] = key[-1].replace(key[-1], f'{key[-1]}_')
        path = path[1:]
        method_list = list(value.keys())
        restful_method = ['post', 'get', 'delete', 'put', 'head', 'options', 'trace', 'connect']
        for method in method_list:
            if method not in restful_method:
                continue
            if len(method_list) > 1:
                api_name: str = f'{key[-1]}_{method}'
            else:
                api_name: str = key[-1]  # API名称
            module_name = key[1]  # 模块名称
            for i in api_name:
                if i.isupper():
                    api_name = api_name.replace(i, f'_{i.lower()}')
            if api_name.startswith('{'):
                api_name = f'{method}_{key[-2]}_by_{key[-1].replace("{", "").replace("}", "")}'
            if not final_data.get(module_name):  # 如果模块名不存在，新建该键
                final_data[module_name] = {}
            final_data[module_name].update({api_name: {}})
            api = final_data[module_name].get(api_name)
            description = value[method].get('description')
            summary = value[method].get('summary')
            if summary:
                api['summary'] = summary
            if description:
                api['description'] = description
            api['method'] = method
            api['path'] = path
            api['req_params'] = {}
            # 处理parameters中的参数：查询参数、请求体
            parameters = value[method].get('parameters')
            if parameters:
                req_params = {}
                for i in parameters:
                    # TODO:参数位置有四种：path,query,body,header
                    location = i.get('in')
                    param = {i.get('name'): ''}
                    if location == 'path':
                        req_params['path'] = {}
                        req_params['path'].update(param)
                    elif location == 'query':
                        req_params['query'] = {}
                        req_params['query'].update(param)
                    elif location == 'body':
                        schema: dict = i.get('schema')
                        ref: str = schema.get('$ref')
                        definition_key = ref.split('/')[-1]
                        req_params['body'] = {}
                        req_params['body'].update({i.get('name'): req_properties[definition_key]})
                    elif location == 'header':
                        req_params['header'] = {}
                        req_params['header'].update(param)
                api['req_params'].update(req_params)
    return final_data


def _parse_swagger(parm):
    if parm.startswith('http'):
        try:
            res = requests.request('get', parm).json()
        except Exception as e:
            logger.error('request failed!')
            raise e
        data_path = res.get('paths')
    elif parm.endswith('.json') and not parm.startswith('http'):
        yaml_data = yaml.safe_load(open(parm, mode='r', encoding='utf-8'))
        data_path = yaml_data.get('paths')
    else:
        logger.error("the parameters must be url or json file path")
        raise TypeError
    final_data = {}
    for path, value in data_path.items():
        key = path.split('/')
        module_name = key[1]  # 模块名称
        api_name: str = key[-1]  # api名称
        for i in api_name:
            if i.isupper():
                api_name = api_name.replace(i, f'_{i.lower()}')
        if api_name.startswith('{'):
            api_name = f'get_{key[-2]}_by_{api_name.strip("{}")}'
        if not final_data.get(module_name):  # 如果模块名不存在，新建该键
            final_data[module_name] = {}
        method = list(value.keys())[0]
        final_data[module_name].update({api_name: {}})
        api = final_data[module_name].get(api_name)
        description = value[method].get('description')
        summary = value[method].get('summary')
        if summary:
            api['summary'] = summary
        if description:
            api['description'] = description
        path = path[1:]
        api['method'] = method
        api['path'] = path
        api['parameters'] = {}
        api['body'] = {}
        params = {}
        body = {}
        # 处理parameters中的参数：查询参数、请求体
        parameters = value[method].get('parameters')
        if parameters:
            for i in parameters:
                if i.get('in') == 'query':
                    params[i['name']] = ''
                if i.get('in') == 'body':
                    schema: dict = i.get('schema')
                    try:
                        properties = schema.get('properties')
                        body_name_list = list(properties.keys())
                    except Exception:
                        pass
                    else:
                        body = {key: '' for key in body_name_list}
                    # print(body)
                if i.get("$ref"):
                    name = i.get("$ref")
                    param_name = name.split('/')[-1]
                    params[param_name] = ''
            api['parameters'].update(params)
        api['body'].update(body)
    return final_data


def swagger_to_yaml(parm, extra_args='restful'):
    if extra_args == 'restful':
        data = _parse_swagger_restful(parm)
    else:
        data = _parse_swagger(parm)
    with open('swagger.yaml', mode='w', encoding='utf-8') as f:
        f.write(yaml.safe_dump(data, sort_keys=False))


def main_swagger2yaml(parm, style='restful'):
    swagger_to_yaml(parm, style)
