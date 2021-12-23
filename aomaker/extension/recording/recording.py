import json
from json import JSONDecodeError

import yaml
from mitmproxy import http, tcp, connection, ctx, flowfilter
from mitmproxy.proxy import server_hooks

from aomaker.field import API, EXCLUDE_HEADER, EXCLUDE_SUFFIX
from aomaker import utils


class Record:
    def __init__(self, filter_field, file_name, save_headers=False, save_response=True):
        self.filter = filter_field
        self.file_name = file_name
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

    # def client_connected(self, client: connection.Client):
    #     ctx.log.warn(f'客户端已建立连接**********************')
    #
    # def client_disconnected(self, client: connection.Client):
    #     ctx.log.warn(f'客户端已关闭连接**********************')
    #     # self.flow_to_yaml(self.yaml_dic)
    #
    # def server_connected(self, data: server_hooks.ServerConnectionHookData):
    #     ctx.log.warn('服务端已连接')
    #
    # def server_disconnected(self, data: server_hooks.ServerConnectionHookData):
    #     ctx.log.warn('服务端已断开连接')
    #
    # def tcp_start(self, flow: tcp.TCPFlow):
    #     ctx.log.error('建立TCP连接***************')
    #
    # def tcp_end(self, flow: tcp.TCPFlow):
    #     ctx.log.error('断开TCP连接***************')
    #
    #
    # def done(self):
    #     ctx.log.error('触发了done（）')

    def response(self, flow: http.HTTPFlow):
        if self.filter in flow.request.host:
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
                'url_path': self.handle_path(path_components),
                'method': method
            }
            # 处理url中有请求参数的情况
            if '?' in path:
                query_fields = self.handle_query(query_fields)
                flow_dic['request']['params'] = query_fields
                # 处理请求参数是action的情况
                action_fields = query_fields.get('action')
                if action_fields and flow_dic['request']['url_path'] == '/api/':
                    utils.handle_class_method_name(API,action_fields,flow_dic)
                    # self.handle_class_method_name(API, action_fields, flow_dic)
            if content_type:
                if content_type == 'application/x-www-form-urlencoded':
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
        with open(self.file_name, mode='w', encoding='utf-8') as f:
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

    # def handle_class_method_name(self, api_action_dict: dict, action_fields: str, flow_dic: dict):
    #     for k, v in api_action_dict.items():
    #         if isinstance(v, str):
    #             if v in action_fields:
    #                 flow_dic['class_name'] = k
    #                 flow_dic['method_name'] = self.handle_action_field(action_fields)
    #         elif isinstance(v, list):
    #             for i in v:
    #                 if i in action_fields:
    #                     flow_dic['class_name'] = k
    #                     flow_dic['method_name'] = self.handle_action_field(action_fields)
    #
    # @staticmethod
    # def handle_action_field(field: str):
    #     for index, s in enumerate(field):
    #         if s.isupper():
    #             if index == 0:
    #                 field = field.replace(s, f'{s.lower()}')
    #             field = field.replace(s, f'_{s.lower()}')
    #     return field


addons = [
    Record("iot.staging.com", 'iot.yaml', save_headers=True, save_response=False)
]
