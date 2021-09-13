import requests
import yaml
from loguru import logger


def __parse_swagger(parm):
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


def swagger_to_yaml(parm):
    data = __parse_swagger(parm)
    with open('swagger.yaml', mode='w', encoding='utf-8') as f:
        f.write(yaml.safe_dump(data, sort_keys=False))


def main_swagger2yaml(parm):
    swagger_to_yaml(parm)
