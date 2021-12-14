import json
import os
import subprocess
import sys
from json import JSONDecodeError
from typing import Text, Dict, List

import black
import yaml
from jinja2 import Template, DebugUndefined
from loguru import logger
import urllib.parse as urlparse
from urllib.parse import unquote
from aomaker.make import make_api_file_from_yaml
import utils


class HarParser:
    def __init__(self, har_file_path, filter_str=None, exclude_str=None, platform='pc'):
        self.har_file_path = utils.ensure_file_path(har_file_path)
        self.filter_str = filter_str
        self.exclude_str = exclude_str or ""
        self.platform = platform

    def __make_request_url(self, req_data_dict, entry_json):
        """ parse HAR entry request url and queryString, and make teststep url and params

        Args:
            entry_json (dict):
                {
                    "request": {
                        "url": "https://aomaker.top/home?v=1&w=2",
                        "queryString": [
                            {"name": "v", "value": "1"},
                            {"name": "w", "value": "2"}
                        ],
                    },
                    "response": {}
                }

        Returns:
            {
                "name: "/home",
                "request": {
                    "url":
                        "host": "https://aomaker.top",
                        "path": "/home"
                    "params": {"v": "1", "w": "2"}
                }
            }

        """
        request_params = utils.convert_list_to_dict(
            entry_json["request"].get("queryString", [])
        )

        url = entry_json["request"].get("url")
        if not url:
            logger.exception("url missed in request.")
            sys.exit(1)
        # ParseResult(scheme='https', netloc='console.shanhe.com', path='/portal_api/', params='', query='action=cluster/list', fragment='')
        parsed_object = urlparse.urlparse(url)
        # host = parsed_object.scheme + "://" + parsed_object.netloc
        path = parsed_object.path
        if self.platform == 'pc':
            action: str = request_params.get('action')
            action_list = action.split('/')
            class_name = action_list[0]
            method_name = action_list[-1]
            for i in method_name:
                if i.isupper():
                    method_name = method_name.replace(i, f'_{i.lower()}')
            # TODO：class_name和method_name不一定是cluster/list这种形式
            req_data_dict["class_name"] = class_name
            req_data_dict["method_name"] = method_name
        # check whether query string is in url
        req_data_dict["request"].update({"url_path": path})
        if request_params:
            # parsed_object = parsed_object._replace(query="")
            # TODO: check path whether is api gate
            req_data_dict["request"]["params"] = request_params
        # parsed_object.params

    def __make_request_method(self, req_data_dict, entry_json):
        """ parse HAR entry request method, and make ao_params method.
        """
        method = entry_json["request"].get("method")
        if not method:
            logger.exception("method missed in request.")
            sys.exit(1)

        req_data_dict["request"]["method"] = method

    def __make_request_data(self, req_data_dict, entry_json):
        """ parse HAR entry request data, and make teststep request data

        Args:
            entry_json (dict):
                {
                    "request": {
                        "method": "POST",
                        "postData": {
                            "mimeType": "application/x-www-form-urlencoded; charset=utf-8",
                            "params": [
                                {"name": "a", "value": 1},
                                {"name": "b", "value": "2"}
                            }
                        },
                    },
                    "response": {...}
                }


        Returns:
            {
                "request": {
                    "method": "POST",
                    "data": {"v": "1", "w": "2"}
                }
            }

        """
        method = entry_json["request"].get("method")
        if method in ["POST", "PUT", "PATCH"]:
            postData = entry_json["request"].get("postData", {})
            mimeType = postData.get("mimeType")

            # Note that text and params fields are mutually exclusive.
            if "text" in postData:
                post_data = postData.get("text")
            else:
                params = postData.get("params", [])
                post_data = utils.convert_list_to_dict(params)

            request_data_key = "data"
            if not mimeType:
                pass
            elif mimeType.startswith("application/json"):
                try:
                    post_data = json.loads(post_data)
                    request_data_key = "json"
                except JSONDecodeError:
                    pass
            elif mimeType.startswith("application/x-www-form-urlencoded"):
                post_data = utils.convert_x_www_form_urlencoded_to_dict(post_data)
            else:
                pass

            req_data_dict["request"][request_data_key] = post_data

    def __make_response_content(self, resp_data_dict, entry_json):
        response = entry_json["response"].get("content")
        if not response:
            logger.exception("response content missed.")
            sys.exit(1)
        resp_data_dict["response"] = response.get('text')

    def _prepare_req_data(self, entry_json):
        """ extract info from entry dict and make req_data

        Args:
            entry_json (dict):
                {
                    "request": {
                        "method": "POST",
                        "url": "https://httprunner.top/api/v1/Account/Login",
                        "headers": [],
                        "queryString": [],
                        "postData": {},
                    },
                    "response": {
                        "status": 200,
                        "headers": [],
                        "content": {}
                    }
                }

        """
        req_data_dict = {"class_name": "", "method_name": "", "request": {}, "response": ""}

        self.__make_request_url(req_data_dict, entry_json)
        self.__make_request_method(req_data_dict, entry_json)
        # self.__make_request_cookies(ao_params_dict, entry_json)
        # self.__make_request_headers(ao_params_dict, entry_json)
        self.__make_request_data(req_data_dict, entry_json)
        self.__make_response_content(req_data_dict, entry_json)
        # self._make_validate(ao_params_dict, entry_json)
        # print(req_data_dict)
        try:
            json_params = req_data_dict.get('request').get('data').get('params')
            if json_params:
                req_data_dict['request']['data']['params'] = json.loads(json_params)
        except AttributeError:
            pass
        else:
            if json_params:
                req_data_dict['request']['data']['params'] = json.loads(json_params)
        return req_data_dict

    def _prepare_req_data_list(self):
        """ make req_data list.
            req_data list are parsed from HAR log entries list.
        """

        def is_exclude(url, exclude_str):
            exclude_str_list = exclude_str.split("|")
            for exclude_str in exclude_str_list:
                if exclude_str and exclude_str in url:
                    return True
            return False

        req_data_list = []
        log_entries = utils.load_har_log_entries(self.har_file_path)
        for entry_json in log_entries:
            url = entry_json["request"].get("url")
            if self.filter_str and self.filter_str not in url:
                continue

            if is_exclude(url, self.exclude_str):
                continue

            req_data_list.append(self._prepare_req_data(entry_json))

        return req_data_list

    def _make_testcase(self):
        logger.info("Extract info from HAR file and prepare for testcases.")
        testcase = {"name": "", "steps": []}
        req_data_list = self._prepare_req_data_list()
        for req in req_data_list:
            req_dic = {}
            req_dic['class_name'] = req.get('class_name')
            req_dic['method_name'] = req.get('method_name')
            req_dic['request'] = req.get('request')
            req_dic['response'] = eval(req.get('response'))
            # data = req['request'].get('data')
            # if data:
            #     req_dic['req_data'] = data
            testcase['steps'].append(req_dic)
        return testcase

    def har2yaml_testcase(self):
        logger.info(f"Start to generate YAML testcases from {self.har_file_path}")
        harfile = os.path.splitext(self.har_file_path)[0]
        testcase = self._make_testcase()

        # 生成yaml文件
        print(testcase)
        output_testcase_file = f"{harfile}.yaml"
        utils.dump_yaml(testcase, output_testcase_file)


har = HarParser('ehpc_user.har', filter_str='action')
# har.fill_ao_by_testcase()

# har.gen_yaml_testcase()
