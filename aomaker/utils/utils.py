import json
import os
import sys
from json import JSONDecodeError
from typing import Text, List, Dict
from urllib.parse import unquote
from configparser import ConfigParser

import yaml

from aomaker._log import logger


def dump_yaml(testcase, yaml_file):
    """ dump HAR entries to yaml
    """

    with open(yaml_file, "w", encoding="utf-8") as outfile:
        yaml.dump(
            testcase, outfile, allow_unicode=True, default_flow_style=False, sort_keys=False
        )


def load_yaml(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        yaml_testcase = yaml.safe_load(f)
    return yaml_testcase


def load_har_log_entries(file_path):
    """ load HAR file and return log entries list

    Args:
        file_path (str)

    Returns:
        list: entries
            [
                {
                    "request": {},
                    "response": {}
                },
                {
                    "request": {},
                    "response": {}
                }
            ]

    """
    with open(file_path, mode="rb") as f:
        try:
            content_json = json.load(f)
            return content_json["log"]["entries"]
        except (TypeError, JSONDecodeError) as ex:
            logger.error(f"failed to load HAR file {file_path}: {ex}")
            sys.exit(1)
        except KeyError:
            logger.error(f"log entries not found in HAR file: {content_json}")
            sys.exit(1)


def ensure_file_path(path: Text, file_type='HAR') -> Text:
    if file_type == 'HAR':
        if not path or not path.endswith(f".har"):
            logger.error("没有指定HAR文件！")
            sys.exit(1)
    elif file_type == 'YAML':
        if not path:
            with open(path, mode='w', encoding='utf-8') as f:
                yaml.dump('', f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        if not (path.endswith(".yaml") or path.endswith(".yml")):
            logger.error("没有指定YAML文件！")
            sys.exit(1)

    path = ensure_path_sep(path)
    # if not os.path.isfile(path):
    #     logger.error(f"{file_type} file not exists: {path}")
    #     sys.exit(1)

    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)

    return path


def ensure_path_sep(path: Text) -> Text:
    """ ensure compatibility with different path separators of Linux and Windows
    """
    if "/" in path:
        # windows
        path = os.sep.join(path.split("/"))

    elif "\\" in path:
        # linux
        path = os.sep.join(path.split("\\"))

    elif ":" in path:
        # mac
        path = os.sep.join(path.split(":"))

    return path


def convert_list_to_dict(origin_list):
    """ convert HAR data list to mapping

    Args:
        origin_list (list)
            [
                {"name": "v", "value": "1"},
                {"name": "w", "value": "2"}
            ]

    Returns:
        dict:
            {"v": "1", "w": "2"}

    """
    return {item["name"]: item.get("value") for item in origin_list}


def convert_x_www_form_urlencoded_to_dict(post_data):
    """ convert x_www_form_urlencoded data to dict

    Args:
        post_data (str): a=1&b=2

    Returns:
        dict: {"a":1, "b":2}

    """
    if isinstance(post_data, str):
        converted_dict = {}
        for k_v in post_data.split("&"):
            try:
                key, value = k_v.split("=")
            except ValueError:
                raise Exception(
                    "Invalid x_www_form_urlencoded data format: {}".format(post_data)
                )
            converted_dict[key] = unquote(value)
        return converted_dict
    else:
        return post_data


def distinct_req(req_data_list: List[Dict]) -> List[Dict]:
    """remove duplicates req"""
    new_req_data_list = []
    api_list = []
    for req in req_data_list:
        dic = dict()
        # req = req.dict()
        dic['class_name'] = req['class_name']
        dic['method_name'] = req['method_name']
        if dic not in api_list:
            api_list.append(dic)
            new_req_data_list.append(req)
    return new_req_data_list


def handle_class_method_name(api_action_dict: dict, action_fields: str, req_data_dic: dict):
    for k, v in api_action_dict.items():
        if isinstance(v, str):
            if v in action_fields:
                req_data_dic['class_name'] = k
                req_data_dic['method_name'] = __handle_action_field(action_fields)
        elif isinstance(v, list):
            for i in v:
                if i in action_fields:
                    req_data_dic['class_name'] = k
                    req_data_dic['method_name'] = __handle_action_field(action_fields)


def __handle_action_field(field: str):
    for index, s in enumerate(field):
        if s.isupper():
            if index == 0:
                field = field.replace(s, f'{s.lower()}')
            field = field.replace(s, f'_{s.lower()}')
    return field


class HandleIni(ConfigParser):
    def __init__(self, filenames):
        super().__init__()
        self.read(filenames=filenames, encoding='utf-8')
