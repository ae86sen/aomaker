import os
import re
import subprocess
from typing import List, Dict

from jinja2 import Template, DebugUndefined
from loguru import logger

from aomaker import utils
from aomaker.make import make_api_file_from_yaml
from aomaker.models import YamlTestcase
from aomaker.template import Template as Temp


class YamlParse:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = utils.ensure_file_path(yaml_file_path, file_type='YAML')
        self.yaml_testcase = YamlTestcase(**utils.load_yaml(self.yaml_file_path)).dict(by_alias=True)
        self.testcase_class_name = self.yaml_testcase.get('testcase_class_name')
        self.testcase_name = self.yaml_testcase.get('testcase_name')
        self.description = self.yaml_testcase.get('description')
        self.steps = self.yaml_testcase.get('steps')

    # @staticmethod
    def _render_ao(self, class_name, method_name, content):
        root_dir = os.getcwd()
        service_dir = os.path.join(root_dir, 'service')
        service_api_dir = os.path.join(service_dir, 'service_api')
        module = os.path.join(service_api_dir, f'{class_name}.py')
        with open(module) as f:
            template = f.read()
            if f'{{{{ {method_name}_params }}}}' in template:
                temp = Template(template, undefined=DebugUndefined)
                data = temp.render({f'{method_name}_params': content})
                # new_data = new_data.replace("'$", 'self.pp.').replace("$'", '').replace('"{', '{', 1).replace('}"', "}",
                #                                                                        1)
                new_data = self.__replace_params(data)
                with open(module, mode='w+') as f:
                    f.write(new_data)
                logger.info(f'render {module} successfully!')
        # os.system(f'black {module}')
        subprocess.run(f'black {module}')

    @staticmethod
    def __replace_params(data: str):
        str_with_mark: list = re.findall('(\$.*?\$)', data)
        str_without_mark: list = re.findall('\$(.*?)\$', data)
        for replace_mark, replace_value in zip(str_with_mark,str_without_mark):
            if '.' in replace_value:
                value_list = replace_value.split('.')
                replace_value = f'getattr(self.pp.{value_list[0]}, "{value_list[1]}")'

            else:
                replace_value = f'getattr(self.pp, "{replace_value}")'
            data = data.replace(f"'{replace_mark}'", replace_value)
        data = data.replace('"{', '{', 1).replace('}"', "}", 1)
        return data

    def make_ao_file(self):
        logger.info(f"Start to make ao file...")
        req_data_list = self.steps
        req_data_list = utils.distinct_req(req_data_list)
        # 生成ao文件
        make_api_file_from_yaml(req_data_list)
        logger.info(f"All done!")

    def render_ao_file(self):
        logger.info(f"Start to render ao file...")
        # 2.遍历steps
        for step in self.steps:
            # 3.根据class_name找到py文件
            # 4.根据method_name渲染对应方法，将协议进行填充
            req_data = step.get('request')
            class_name = step.get('class_name')
            method_name = step.get('method_name')
            data = req_data.get('data')
            if data:
                params = data.get('params')
                self._render_ao(class_name, method_name, params)
        logger.info(f"All done!")

    def make_testcase_scenario_file(self):
        logger.info(f"Start to make scenario testcase file...")
        class_name = self.testcase_class_name
        testcase_name = self.testcase_name
        description = self.description
        # 1.创建文件（判断是否有该文件，如果没有则创建，如果有则判断是否有该类，该方法）
        workspace = os.getcwd()
        testcase_dir = os.path.join(workspace, 'testcases')
        test_scenario_dir = os.path.join(testcase_dir, 'test_scenario')
        test_module_path = os.path.join(test_scenario_dir, f'test_{class_name.lower()}')
        # 2.确定有哪些ao
        #  剔除重复的请求
        ao_list = utils.distinct_req(self.steps)
        ao_class_list = []
        call_ao_list = []
        for ao in ao_list:
            ao_method = dict()
            ao_class_list.append(ao['class_name'])
            ao_method['ao'] = ao['class_name']
            ao_method['method'] = ao['method_name']
            is_extract = ao.get('extract')
            if is_extract:
                ao_method['extract'] = is_extract
            is_assert = ao.get('assert')
            if is_assert:
                ao_method['assert'] = self._handle_assert(is_assert)
            call_ao_list.append(ao_method)
        import_ao_class_list = list(set(ao_class_list))
        render_data = dict()
        render_data['class_list'] = import_ao_class_list
        render_data['call_ao_list'] = call_ao_list
        render_data['class_name'] = class_name
        render_data['testcase_name'] = testcase_name
        if description:
            render_data['description'] = description
        content = Temp.TEMP_SCENARIO_CASE.render(render_data)
        testcase_file_path = f'{test_module_path}.py'
        if not os.path.exists(testcase_file_path):
            with open(testcase_file_path, mode='w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f'make {testcase_file_path} successfully!')
        else:
            # 文件存在，类存在，方法不存在
            # try:
            #     exec(f'from testcases.test_scenario from Test{class_name}')
            # except ImportError as ie:
            #     raise ie
            # class_ = locals()[f'Test{class_name}']
            # if not hasattr(class_, f"test_{testcase_name}"):
            #     # 追加模板渲染
            #     content = Temp
            # 不支持追加用例
            logger.warning(f'make {testcase_file_path} failed, the file already exists!')
        logger.info('All done!')

    @staticmethod
    def _handle_assert(assert_content: List[Dict]) -> List:
        """
        :param assert_content: [{eq:['$..ret_code',0,0],le:['$..total',1]}]
        :return: [{
            comparator: eq,
            expr: '$..ret_code',
            index: 0,
            expect: 0
        },
        {
            comparator: le,
            expr: '$..total',
            expect: 0
        }]
        """
        new_assert_content = []
        for content_dict in assert_content:
            assert_dict = dict()
            comparator = list(content_dict.keys())[0]
            assert_data: list = content_dict.get(comparator)
            assert_dict['comparator'] = comparator
            assert_dict['expr'] = assert_data[0]
            assert_dict['expect'] = assert_data[-1]
            # 判断jsonpath是否有index，没有就默认为0
            # assert_dict['index'] = 0
            assert_dict['index'] = assert_data[1] if len(assert_data) == 3 else 0
            # if len(assert_data) == 3:
            #     assert_dict['index'] = assert_data[1]
            new_assert_content.append(assert_dict)
        return new_assert_content


if __name__ == '__main__':
    # if os.path.exists(r'D:\项目列表\aomaker\aomaker\testcases\test_scenario\test_demo.py'):
    #     print(1)
    yml = YamlParse('../hpc.yaml')
    # yml.make_ao_file()
    yml.render_ao_file()

