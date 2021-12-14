import jinja2


class Template:
    TEMP_HPC_API = jinja2.Template(
        """import json
from common.base_api import BaseApi


class Define{{ class_name | title}}(BaseApi):
    {% for func,v in func_list.items() %}
    {% if v.method != 'get'%}def api_{{func}}(self, body):{% else %}def api_{{func}}(self):{% endif %}
        \"""{{v.description}}""\"
        payload = {
            'url': f'{getattr(self, "host")}{getattr(self, "base_path")}',
            'method': '{{v.method}}',
            'headers': getattr(self, 'headers'),
            'params': {'action': '{{v.path}}'},
            {% if v.method != 'get'%}'data': {
                'params': json.dumps(body)
            }{% endif %}
        }
        response = self.send_http(payload)
        return response
        {% endfor %}   
    """)
    TEMP_HPC_AO = jinja2.Template(
        """import threading
from apis.{{ class_name }} import Define{{ class_name | title}}


class {{ class_name | title}}(Define{{ class_name | title}}):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr({{ class_name | title}}, '_instance'):
            with cls._instance_lock:
                if not hasattr({{ class_name | title}}, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance    
    {% for func,v in func_list.items() %}
    def {{func}}(self):{% if v.method != 'get'%}
        body = {{ v.body }}
        res = self.get_resp_json(self.api_{{ func }}(body)){% else %}
        res = self.get_resp_json(self.api_{{ func }}()){% endif %}
        return res
    {% endfor %}   
    """)
    TEMP_RESTFUL_API = jinja2.Template(
        """from common.base_api import BaseApi
    

class Define{{ class_name}}(BaseApi):
    {% for func,v in func_list.items() %}
    def api_{{func}}(self, req_params):
        \"""{{v.summary}}""\"
        payload = {
            'url': f'{getattr(self, "host")}{getattr(self, "base_path")}',
            'method': 'POST',
            'headers': getattr(self, 'headers'),
            'parameters': req_params.get('query'),
            'json': req_params.get('body')
        }
        header_params = req_params.get('header')
        if header_params:
            payload['headers'].update(header_params)
        {% if v.var %}path_params = req_params.get('path')
        payload['headers']['X-Path'] = f'{{v.path}}'{% else %}payload['headers']['X-Path'] = '{{v.path}}'{% endif %}
        payload['headers']['X-Method'] = '{{v.method}}'
        response = self.send_http(payload)
        return response
        {% endfor %}   
    """)
    TEMP_RESTFUL_AO = jinja2.Template(
        """import threading
from apis.{{ module_name }} import Define{{ class_name }}


class {{ class_name }}(Define{{ class_name}}):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr({{ class_name }}, '_instance'):
            with cls._instance_lock:
                if not hasattr({{ class_name }}, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance    
    {% for func,v in func_list.items() %}
    def {{func}}(self):
        \"""{{v.summary}}""\"
        req_params = {{v.req_params}}
        res = self.get_resp_json(self.api_{{ func }}(req_params))
        return res
    {% endfor %}   
    """)
    TEMP_ADDITIONAL_API = jinja2.Template("""
    {% if request.method != 'GET'%}def api_{{method_name}}(self, body):{% else %}def api_{{method_name}}(self):{% endif %}
        payload = {
            'url': f'{getattr(self, "host")}{{request.url_path}}',
            'method': '{{request.method}}',
            'headers': getattr(self, 'headers'),
            'params': {{request.params}},
            {% if request.method != 'GET'%}'data': {
                'params': json.dumps(body),
                {% if request.data.method %}'method': '{{request.data.method}}'{% endif %}
            }{% endif %}
        }
        response = self.send_http(payload)
        return response
        
""")
    TEMP_ADDITIONAL_AO = jinja2.Template("""
    {% set sp= '{{' -%}{% set ep= '}}' -%}
    def {{method_name}}(self):{% if request.data %}
        body = "{{sp}} {{method_name}}_params {{ep}}"
        res = self.get_resp_json(self.api_{{ method_name }}(body)){% else %}
        res = self.get_resp_json(self.api_{{ method_name }}()){% endif %}
        return res
""")
    TEMP_HAR_API = jinja2.Template(
        """import json
from common.base_api import BaseApi


class Define{{ module_name | title}}(BaseApi):
    {% for ao in ao_list %}
    {% if ao.request.data %}def api_{{ao.method_name}}(self, body):{% else %}def api_{{ao.method_name}}(self):{% endif %}
        payload = {
            'url': f'{getattr(self, "host")}{{ao.request.url_path}}',
            'method': '{{ao.request.method}}',
            'headers': getattr(self, 'headers'),
            'params': {{ao.request.params}},
            {% if ao.request.data %}'data': {
                'params': json.dumps(body),
                {% if ao.request.data.method %}'method': '{{ao.request.data.method}}'{% endif %}
            }{% endif %}
        }
        response = self.send_http(payload)
        return response
        {% endfor %}    
    """)
    TEMP_HAR_AO = jinja2.Template(
        """import threading
from apis.{{ module_name }} import Define{{ module_name | title}}
from service.params_pool import ParamsPool
{% set sp= '{{' %}
{% set ep= '}}' %}
class {{ module_name | title}}(Define{{ module_name | title}}):
    _instance_lock = threading.Lock()
    pp = ParamsPool()
    
    def __new__(cls, *args, **kwargs):
        if not hasattr({{ module_name | title}}, '_instance'):
            with cls._instance_lock:
                if not hasattr({{ module_name | title}}, '_instance'):
                    cls._instance = super().__new__(cls)
        return cls._instance    
    {% for ao in ao_list %}
    def {{ao.method_name}}(self):{% if ao.request.data %}
        body = "{{sp}} {{ao.method_name}}_params {{ep}}"
        res = self.get_resp_json(self.api_{{ ao.method_name }}(body)){% else %}
        res = self.get_resp_json(self.api_{{ ao.method_name }}()){% endif %}
        return res
    {% endfor %}   
    """)

    TEMP_API_CASE = jinja2.Template(
        """import os

import pytest
import yaml

from service.service_api.{{api}} import {{api | capitalize}}
from common.base_api import BaseApi
from common.handle_path import DATA_DIR

case_data_path = os.path.join(DATA_DIR, '{{api}}_datas.yaml')
datas = yaml.safe_load(open(case_data_path, encoding='utf-8'))


class Test{{api | capitalize}}:
    {{api}} = {{api | capitalize}}()
    {% for case in case_list %}
    @pytest.mark.parametrize('data', datas['{{api}}']['{{case}}'])
    def test_{{case}}(self, data):
        res = self.{{api}}.{{case}}(data['variables'])
        assert res['ret_code'] == data['expected']
    {% endfor %}
    """
    )

    TEMP_SCENARIO_CASE = jinja2.Template(
        """import os

import pytest
import yaml
from jsonpath import jsonpath

from common.base_testcase import BaseTestcase
from service.params_pool import ParamsPool
{% for class in class_list-%}
from service.service_api.{{class}} import {{class | capitalize}}
{%endfor%}

class Test{{class_name | capitalize}}(BaseTestcase):
    {%for class in class_list%}{{class}} = {{class | capitalize}}()
    {%endfor%}
    def test_{{testcase_name}}(self):
        \"""{{description}}""\"
        {%for ao in call_ao_list -%}
        # step{{loop.index}}
        {%if ao.extract or ao.assert is defined -%}
        res = self.{{ao.ao}}.{{ao.method}}()
        {%else-%}
        self.{{ao.ao}}.{{ao.method}}()
        {%endif-%}
        {%for extract in ao.extract-%}
        {%if extract.index is defined -%}
        self.extract_set_vars(res, '{{extract.var_name}}', '{{extract.expr}}', {{extract.index}})
        {%else-%}
        self.extract_set_vars(res, '{{extract.var_name}}', '{{extract.expr}}')
        {%endif-%}
        {%endfor-%}
        {%if ao.assert-%}
        {%for assert in ao.assert-%}
        assert_content = jsonpath(res, '{{assert.expr}}')[{{assert.index}}]
        {%if assert.expect is string -%}
        self.{{assert.comparator}}(assert_content, '{{assert.expect}}')
        {%else-%}
        self.{{assert.comparator}}(assert_content, {{assert.expect}})
        {%endif-%}
 
        {%endfor-%}
        {%endif-%}
        {%-endfor-%}
    """
    )


