import jinja2


class Template:
    TEMP_HPC_API = jinja2.Template(
        """import json
from aomaker.base.base_api import BaseApi


class {{ class_name | title}}(BaseApi):
    {% for func,v in func_list.items() %}
    {% if v.method != 'get'%}def {{func}}(self):{% else %}def api_{{func}}(self):{% endif %}
        \"""{{v.description}}""\"
        {% if v.method != 'get'%}
        body = {}
        {% endif %}
        payload = {
            'method': '{{v.method}}',
            'params': {'action': '{{v.path}}'},
            {% if v.method != 'get'%}'data': {
                'params': json.dumps(body)
            }{% endif %}
        }
        resp = self.send_http(payload)
        return resp
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
        """from aomaker.base.base_api import BaseApi
    

class {{ class_name}}(BaseApi):
    {% for func,v in func_list.items() %}
    def {{func}}(self):
        \"""{{v.summary}}""\"
        body = {}
        http_data = {
            'method': 'POST',
            'api_path': '',
            'parameters': req_params.get('query'),
            'json': body
        }
        response = self.send_http(http_data)
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
    {% for dep in dependent_api %}
    {{dep.decorator}}
    {% endfor -%}
    {% set sp= '{{' %}
    {% set ep= '}}' %}
    def {{method_name}}(self, test_data: dict = None):
        {%- if request.data or request.json %}
        body = "{{sp}} {{method_name}}_params {{ep}}"{% endif %}
        http_data = {
            'api_path': '{{request.api_path}}',
            'method': '{{request.method}}',
            {% if request.params -%}
            'params': {{request.params}},
            {% endif -%}
            {% if request.data %}'data': {
                'params': json.dumps(body),
                {% if request.data.method %}'method': '{{request.data.method}}'{% endif %}
            }{% endif -%}
            {% if request.json -%}
            'json': body
            {% endif -%}
        }
        {% if request.headers -%}
        self._headers.update({{ request.headers }})
        {% endif -%}
        resp = self.send_http(http_data)
        return resp        
""")
    TEMP_HAR_API = jinja2.Template(
        """import json

{% for ao in ao_list %}
{% if ao.dependent_api %}
{% for dep in ao.dependent_api %}
{{dep.module}}
{% endfor -%}
{% endif -%}
{% endfor -%}
from aomaker.base.base_api import BaseApi
from aomaker.aomaker import dependence
{% set sp= '{{' %}
{% set ep= '}}' %}

class {{ module_name | title}}(BaseApi):

    {% for ao in ao_list %}
    {% for dep in ao.dependent_api %}
    {{dep.decorator}}
    {% endfor -%}
    def {{ao.method_name}}(self, test_data: dict = None):
        {%- if ao.request.data or ao.request.json %}
        body = "{{sp}} {{ao.method_name}}_params {{ep}}"{% endif %}
        http_data = {
            'api_path': '{{ao.request.api_path}}',
            'method': '{{ao.request.method}}',
            {% if ao.request.params -%}
            'params': {{ao.request.params}},
            {% endif -%}
            {% if ao.request.data %}'data': {
                'params': json.dumps(body),
                {% if ao.request.data.method %}'method': '{{ao.request.data.method}}'{% endif %}
            }{% endif -%}
            {% if ao.request.json -%}
            'json': body
            {% endif -%}
        }
        {% if ao.request.headers -%}
        self._headers.update({{ ao.request.headers }})
        {% endif -%}
        resp = self.send_http(http_data)
        return resp
        {% endfor %}

{{module_name}}={{module_name | title}}()
    """)

    TEMP_API_CASE = jinja2.Template(
        """import os

import pytest
import yaml

from service.service_api.{{api}} import {{api | capitalize}}
from common.base_testcase import BaseTestcase
from common.handle_path import DATA_DIR

case_data_path = os.path.join(DATA_DIR, '{{api}}_datas.yaml')
datas = yaml.safe_load(open(case_data_path, encoding='utf-8'))


class Test{{api | capitalize}}(BaseTestcase):
    {{api}} = {{api | capitalize}}()
    {% for case in case_list %}
    @pytest.mark.parametrize('test_data', datas['{{api}}']['{{case}}'])
    def test_{{case}}(self, test_data):
        res = self.{{api}}.{{case}}(test_data['variables'])
        assert res['ret_code'] == test_data['expected']
    {% endfor %}
    """
    )
    TEMP_API_CASE2 = jinja2.Template(
        """import pytest
from jsonpath import jsonpath
from aomaker.base.base_testcase import BaseTestcase
from aomaker.aomaker import data_maker

{% for class in import_list -%}
from apis.{{class}} import {{class}}
{% endfor %}

class Test{{ test_class | capitalize}}(BaseTestcase):
    {% for method in method_list %}
    @pytest.mark.parametrize('test_data', data_maker('data/api_data/{{test_class}}.yaml','{{test_class}}', '{{method}}'))
    def test_{{method}}(self, test_data):
        {% for k,aos in steps.items() -%}
        {% if k==method -%}
        {% for ao in aos -%}
        {%if ao.assert is defined -%}
        {% if ao.test_data -%}
        # test api
        res = {{ao.ao}}.{{ao.method}}(test_data)
        {% else -%}
        res = {{ao.ao}}.{{ao.method}}()
        {% endif -%}
        {%else-%}
        {% if ao.test_data -%}
        # test api
        {{ao.ao}}.{{ao.method}}(test_data)
        {% else -%}
        {{ao.ao}}.{{ao.method}}()
        {% endif -%}
        {%endif-%}
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
        {%endfor-%}
        {%endif-%}
        {%-endfor-%}
    {% endfor -%}
    """
    )
    TEMP_SCENARIO_CASE = jinja2.Template(
        """import os

import pytest
import yaml
from jsonpath import jsonpath
from aomaker.base.base_testcase import BaseTestcase
from aomaker.aomaker import data_maker

{% for class in class_list-%}
from apis.{{class}} import {{class}}
{%endfor-%}


class Test{{class_name | capitalize}}(BaseTestcase):


    {% if test_step_datas -%}
    @pytest.mark.parametrize('test_data', data_maker('data/scenario_data/{{class_name}}.yaml','{{class_name}}', '{{testcase_name}}'))
    def test_{{testcase_name}}(self, test_data: dict):{% else %}
    def test_{{testcase_name}}(self):{% endif %}
        \"""{{description}}""\"
        {%for ao in call_ao_list -%}
        # step{{loop.index}}
        {%if ao.assert is defined -%}
        {% if ao.test_data -%}
        res = {{ao.ao}}.{{ao.method}}(test_data['{{ ao.method }}'])
        {% else -%}
        res = {{ao.ao}}.{{ao.method}}()
        {% endif -%}
        {%else-%}
        {% if ao.test_data -%}
        {{ao.ao}}.{{ao.method}}(test_data['{{ ao.method }}'])
        {% else -%}
        {{ao.ao}}.{{ao.method}}()
        {% endif -%}
        {%endif-%}
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
