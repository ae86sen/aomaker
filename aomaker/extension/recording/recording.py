import json
import os
from json import JSONDecodeError

import yaml
from mitmproxy import http, ctx, flowfilter

from aomaker.field import API, EXCLUDE_HEADER, EXCLUDE_SUFFIX
from aomaker.utils import utils


def ensure_file_name(file_name: str):
    if not (file_name.endswith(".yaml") or file_name.endswith(".yml")):
        file_name = file_name + ".yaml"
    return file_name


class Record:
    def __init__(self, file_name, filter_str=None, save_headers=False, save_response=True):
        self.filter = filter_str
        self.file_name = ensure_file_name(file_name)
        self.steps = []
        self.save_headers = save_headers
        self.save_response = save_response
        self.yaml_dic = {
            'testcase_class_name': '',
            'description': '',
            'testcase_name': ''
        }
        self.exclude_suffix = EXCLUDE_SUFFIX
        self.exclude_request_header = EXCLUDE_HEADER

    def response(self, flow: http.HTTPFlow):
        if "|" in self.filter:
            filter_str = self.filter.split("|")
            conditions = [flowfilter.match(fs, flow) for fs in filter_str]
        else:
            conditions = [flowfilter.match(self.filter, flow)]
        if all(conditions):
            # if self.filter in flow.request.url:
            if self.flow_filter(flow):
                return
            flow_dic = dict()
            # request
            headers = self.handle_headers(flow.request.headers.fields)
            content_type = headers.get('Content-Type')
            method = flow.request.method
            path = flow.request.path
            path_components = flow.request.path_components
            query_fields = flow.request.query.fields
            flow_dic['class_name'] = ''
            flow_dic['method_name'] = ''
            flow_dic['request'] = {
                'api_path': self.handle_path(path_components),
                'method': method
            }
            # 处理url中有请求参数的情况
            if '?' in path:
                query_fields = self.handle_query(query_fields)
                flow_dic['request']['params'] = query_fields
                # 处理请求参数是action的情况
                action_fields = query_fields.get('action')
                if action_fields and flow_dic['request']['api_path'] == '/api/':
                    utils.handle_class_method_name(API, action_fields, flow_dic)
                    # self.handle_class_method_name(API, action_fields, flow_dic)
            if content_type:
                if 'application/x-www-form-urlencoded' in content_type:
                    urlencoded_form_data = self.handle_urlencoded_form(flow.request.urlencoded_form.fields)
                    flow_dic['request']['data'] = urlencoded_form_data
                elif 'application/json' in content_type:
                    flow_dic['request']['json'] = json.loads(flow.request.text)
            if self.save_headers:
                flow_dic['request']['headers'] = headers
            if self.save_response:
                response = flow.response.content
                try:
                    response = json.loads(str(response, 'utf-8'))
                except JSONDecodeError:
                    response = None
                except UnicodeDecodeError:
                    ctx.log.error(f'response-json转换为python格式失败，请求url为：{flow.request.url}')
                flow_dic['response'] = response
            self.steps.append(flow_dic)
            self.yaml_dic['steps'] = self.steps
            ctx.log.alert(f'request: {flow.request.url}')
            ctx.log.alert(f'已捕获{len(self.steps)}个请求')
            self.flow_to_yaml(self.yaml_dic)

    def flow_to_yaml(self, content):
        # 列表中有重复元素会自动加锚点
        # yaml = ruamel.yaml.YAML()
        # yaml.representer.ignore_aliases = lambda *data: True
        # with open(self.file_name, mode='w', encoding='utf-8') as f:
        #     yaml.dump(content, f)
        workspace = os.getcwd()
        flow2yaml_dir = os.path.join(workspace, 'yamlcase')
        file_path = os.path.join(flow2yaml_dir, self.file_name)
        with open(file_path, mode='w', encoding='utf-8') as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def flow_filter(self, flow):
        if flowfilter.match('~u socket.io', flow):
            return True
        if flowfilter.match('~a', flow):
            return True
        if flowfilter.match('~hs text/html', flow):
            return True
        for suffix in self.exclude_suffix:
            if flowfilter.match(f'~u {suffix}', flow):
                return True

    def handle_path(self, path_components):
        if path_components:
            return '/' + '/'.join(path_components) + '/'
        else:
            return ''

    def handle_query(self, query_fields):
        query_dic = dict()
        for field in query_fields:
            query_dic[field[0]] = field[1]
        return query_dic

    def handle_urlencoded_form(self, form_data_tuple: tuple):
        form_dic = dict()
        for data in form_data_tuple:
            if data[0] == 'params':
                data = list(data)
                data[1] = json.loads(data[1])
            form_dic[data[0]] = data[1]
        return form_dic

    def handle_headers(self, headers):
        headers_dic = dict()
        for content in headers:
            key = str(content[0], 'utf-8')
            # 清洗请求头
            if key not in self.exclude_request_header:
                headers_dic[str(content[0], 'utf-8')] = str(content[1], 'utf-8')
        return headers_dic
