import requests


def __parse_swagger(swagger_url):
    res = requests.request('get', swagger_url).json()
    data_path = res.get('paths')
    final_data = {}
    for path, value in data_path.items():
        key = path.split('/')
        module_name = key[1]  # 模块名称
        api_name: str = key[-1]  # api名称
        if api_name.startswith('{'):
            api_name = f'get_{key[-2]}_by_{api_name.strip("{}")}'
        if not final_data.get(module_name):  # 如果模块名不存在，新建该键
            final_data[module_name] = {}
        method = list(value.keys())[0]
        description = value[method]['description']
        final_data[module_name].update({api_name: {}})
        api = final_data[module_name].get(api_name)
        path = path[1:]
        api['method'] = method
        api['description'] = description
        api['path'] = path
        api['parameters'] = {}
        api['body'] = {}
        params = {}
        body = {}
        # 处理parameters中的参数：查询参数、请求体
        for i in value[method]['parameters']:
            # print(i.keys())
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


def swagger_to_yaml(swagger_url, file_name):
    data = __parse_swagger(swagger_url)
    with open(f'{file_name}.yaml', mode='w', encoding='utf-8') as f:
        f.write(yaml.safe_dump(data, sort_keys=False))


if __name__ == '__main__':
    import yaml
    swagger_url = 'http://10.105.21.113:8889/api/swagger.json'
    swagger_to_yaml(swagger_url,'swagger')