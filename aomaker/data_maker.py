import os
import sys

from aomaker.utils import load_yaml


def data_maker(class_name, method_name, file_path, model='scenario'):
    workspace = os.getcwd()
    data_path = os.path.join(workspace, 'data')
    api_data_path = os.path.join(data_path, 'api_data')
    scenario_data_path = os.path.join(data_path, 'scenario_data')
    real_path = api_data_path if model == 'api' else scenario_data_path
    yaml_path = os.path.join(real_path, file_path)
    if os.path.exists(yaml_path):
        print(f'{yaml_path} 不存在！')
        sys.exit(1)
    data = load_yaml(yaml_path).get(class_name).get(method_name)
    return data
