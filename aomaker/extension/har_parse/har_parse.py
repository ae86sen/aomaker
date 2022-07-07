import json
import os
import sys
from json import JSONDecodeError

import urllib.parse as urlparse

from aomaker.field import API, EXCLUDE_HEADER
from aomaker.utils import utils
from aomaker.log import logger


class HarParser:
    def __init__(
            self,
            har_file_path,
            yaml_file_path,
            filter_str=None,
            exclude_str=None,
            save_response=True,
            save_headers=False
    ):
        self.har_file_path = utils.ensure_file_path(har_file_path)
        self.yaml_file_path = utils.ensure_file_path(yaml_file_path, file_type='YAML')
        self.filter_str = filter_str
        self.exclude_str = exclude_str or ""
        self.exclude_request_header = EXCLUDE_HEADER
        self.save_response = save_response
        self.save_headers = save_headers

    @staticmethod
    def __make_request_url(req_data_dict, entry_json):
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
        # ParseResult(scheme='https', netloc='console.shanhe.com', path='/portal_api/', params='',
        # query='action=cluster/list', fragment='')
        parsed_object = urlparse.urlparse(url)
        # host = parsed_object.scheme + "://" + parsed_object.netloc
        path = parsed_object.path
        req_data_dict["class_name"] = ''
        req_data_dict["method_name"] = ''
        if '?' in url:
            req_data_dict['params'] = request_params
            # 处理请求参数是action的情况
            action_fields = request_params.get('action')
            if action_fields and path == '/api':
                utils.handle_class_method_name(API, action_fields, req_data_dict)

        req_data_dict["request"].update({"url_path": path})

    def __make_request_headers(self, req_data_dict, entry_json):
        """ parse HAR entry request headers, and make teststep headers.
            header in IGNORE_REQUEST_HEADERS will be ignored.

        Args:
            entry_json (dict):
                {
                    "request": {
                        "headers": [
                            {"name": "Host", "value": "aomaker.top"},
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "User-Agent", "value": "iOS/10.3"}
                        ],
                    },
                    "response": {}
                }

        Returns:
            {
                "request": {
                    headers: {"Content-Type": "application/json"}
            }

        """
        teststep_headers = {}
        for header in entry_json["request"].get("headers", []):
            if header["name"] == "cookie" or header["name"].startswith(":"):
                continue
            if header["name"] in self.exclude_request_header:
                continue
            teststep_headers[header["name"]] = header["value"]

        if teststep_headers:
            req_data_dict["request"]["headers"] = teststep_headers

    @staticmethod
    def __make_request_method(req_data_dict, entry_json):
        """ parse HAR entry request method, and make ao_params method.
        """
        method = entry_json["request"].get("method")
        if not method:
            logger.exception("method missed in request.")
            sys.exit(1)

        req_data_dict["request"]["method"] = method

    @staticmethod
    def __make_request_data(req_data_dict, entry_json):
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

    @staticmethod
    def __make_response_content(resp_data_dict, entry_json):
        response = entry_json["response"].get("content")
        if not response:
            logger.exception("response content missed.")
            sys.exit(1)
        try:
            resp_data_dict["response"] = json.loads(response.get('text'))
        except JSONDecodeError:
            # logger.error(f'convert response to dict failed! \n'
            #              f'response content: {response.get("text")}')
            resp_data_dict["response"] = None

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
        if self.save_headers:
            self.__make_request_headers(req_data_dict, entry_json)
        self.__make_request_data(req_data_dict, entry_json)
        if self.save_response:
            self.__make_response_content(req_data_dict, entry_json)

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
        testcase = {
            "testcase_class_name": "",
            "description": "",
            "testcase_name": "",
            "steps": []
        }
        req_data_list = self._prepare_req_data_list()
        for req in req_data_list:
            req_dic = dict()
            req_dic['class_name'] = req.get('class_name')
            req_dic['method_name'] = req.get('method_name')
            req_dic['request'] = req.get('request')
            if self.save_response:
                # print(req.get('response'))
                req_dic['response'] = req.get('response')
            testcase['steps'].append(req_dic)
        return testcase

    def har2yaml_testcase(self):
        logger.info(f"Start to generate YAML testcases from {self.har_file_path}")
        testcase = self._make_testcase()
        # 生成yaml文件
        workspace = os.getcwd()
        flow2yaml_dir = os.path.join(workspace, 'flow2yaml')
        file_path = os.path.join(flow2yaml_dir, self.yaml_file_path)
        if not os.path.exists(file_path):
            utils.dump_yaml(testcase, file_path)
        else:
            print(f"{file_path} exists!")

# har = HarParser('../../console.shanhe.com2.har', 'har_yaml.yaml', filter_str='action', save_response=False)
# har.har2yaml_testcase()
