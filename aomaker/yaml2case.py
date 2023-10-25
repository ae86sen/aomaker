import os
import re
import copy
import subprocess
from typing import List, Dict, Mapping, Text
from itertools import zip_longest

from jinja2 import Template, DebugUndefined

from aomaker.utils import utils
from aomaker.make_api import make_api_file_from_yaml
from aomaker.models import YamlTestcase
from aomaker.template import Template as Temp
from aomaker._log import logger


class YamlParse:
    def __init__(self, yaml_file_path):
        self.yaml_file_path = utils.ensure_file_path(yaml_file_path, file_type='YAML')
        self.yaml_testcase = YamlTestcase(**utils.load_yaml(self.yaml_file_path)).dict(by_alias=True)
        self.testcase_class_name = self.yaml_testcase.get('testcase_class_name')
        self.testcase_name = self.yaml_testcase.get('testcase_name')
        self.description = self.yaml_testcase.get('description')
        self.steps = self.yaml_testcase.get('steps')
        self.api_datas = {}

    def make_ao_file(self):
        logger.info(f"开始生成ao文件...")
        req_data_list = copy.deepcopy(self.steps)
        req_data_list = utils.distinct_req(req_data_list)
        # 生成ao文件
        make_api_file_from_yaml(req_data_list)
        logger.info(f"全部完成!")

    def render_ao_file(self):
        logger.info(f"开始渲染ao文件...")
        root_dir = os.getcwd()
        apis_dir = os.path.join(root_dir, 'apis')
        # 2.遍历steps
        module_flag_list = list()
        step_len = len(self.steps)
        for index, step in enumerate(self.steps):
            # 3.根据class_name找到py文件
            # 4.根据method_name渲染对应方法，将协议进行填充
            req_data = step.get('request')
            class_name = step.get('class_name')
            method_name = step.get('method_name')
            data = req_data.get('data')
            json_data = req_data.get('json')
            dependent_params = step.get('dependent_params')
            module = os.path.join(apis_dir, f'{class_name}.py')
            if data:
                params = data.get('params')
                render_content = params if params else data
                # print(render_content)
                self._render_ao(module, method_name, render_content, dependent_params)
            if json_data:
                self._render_ao(module, method_name, json_data, dependent_params)
            if module not in module_flag_list:
                module_flag_list.append(module)
            if step_len - 1 == index:
                for module in module_flag_list:
                    logger.info(f'渲染 {module} 成功!')
                    try:
                        # 有些操作系统可能会出现文件找不到的报错，需要加shell=True这个参数
                        subprocess.run(fr'black {module}')
                    except Exception:
                        os.system(fr'black {module}')
        logger.info(f"全部渲染完成!")

    def make_testcase_file(self):
        logger.info(f"开始生成用例文件...")
        class_name = self.testcase_class_name
        testcase_name = self.testcase_name
        description = self.description
        # 1.创建文件
        workspace = os.getcwd()
        data_dir = os.path.join(workspace, 'data')
        scenario_data_dir = os.path.join(data_dir, 'scenario_data')
        api_data_dir = os.path.join(data_dir, 'api_data')
        testcase_dir = os.path.join(workspace, 'testcases')
        test_scenario_dir = os.path.join(testcase_dir, 'test_scenario')
        test_api_dir = os.path.join(testcase_dir, 'test_api')
        test_module_path = os.path.join(test_scenario_dir, f'test_{class_name.lower()}')
        testcase_file_path = f'{test_module_path}.py'
        scenario_data_file_path = os.path.join(scenario_data_dir, f'{class_name}.yaml')
        # 2.确定有哪些ao
        #  剔除重复的请求
        ao_list = utils.distinct_req(self.steps)
        ao_class_list = []
        call_ao_list = []
        # 存放业务场景的数据驱动数据
        test_step_data = dict()
        # 存放单接口的数据驱动数据
        api_datas = dict()
        api_render_data = dict()
        new_call_ao_list = []
        for ao in ao_list:
            ao_method = dict()
            ao_class_list.append(ao['class_name'])
            ao_method['ao'] = ao['class_name']
            ao_method['method'] = ao['method_name']
            is_assert = ao.get('assert')
            is_data_driven = ao.get('data_driven')
            if is_assert:
                ao_method['assert'] = self._handle_assert(is_assert)
            if is_data_driven:
                ao_method['test_data'] = True
                # 每个step转换成一个列表嵌套字典
                # method_name可能重复
                data_list = self._handle_data_driven(is_data_driven)
                ao_data = {
                    ao['method_name']: data_list
                }
                test_step_data.update(ao_data)
                # 生成单接口数据
                self.__handle_api_datas(api_datas, ao['class_name'], ao['method_name'], data_list)
                # 准备生成单接口用例文件数据
                ao['ao'] = ao['class_name']
                ao['method'] = ao['method_name']
                ao['test_data'] = True
                ao['assert'] = self._handle_assert(is_assert)
                self._prepare_api_testcase_data(ao, call_ao_list, api_render_data, new_call_ao_list)
            dep_apis = remove_dependent_api(ao_list)
            if {"module": ao_method['ao'], "api": ao_method['method']} not in dep_apis:
                call_ao_list.append(ao_method)
        render_data = dict()
        if api_datas:
            # 生成单接口数据文件
            for key in api_datas.keys():
                self._write_api_data(key, api_datas[key], api_data_dir)
        if test_step_data:
            # 得到一个大列表，test_datas
            test_step_datas = self._handle_data_driven(test_step_data)
            # 生成场景接口数据文件
            self._write_scenario_data(class_name, testcase_name, test_step_datas, scenario_data_file_path)
            render_data['test_step_datas'] = test_step_datas
        import_ao_class_list = list(set(ao_class_list))
        render_data['class_list'] = import_ao_class_list
        render_data['call_ao_list'] = call_ao_list
        render_data['class_name'] = class_name
        render_data['testcase_name'] = testcase_name
        if description:
            render_data['description'] = description
        # 单接口用例文件生成
        self._make_api_testcase_file(api_render_data, test_api_dir)
        # 场景用例文件生成
        self._make_scenario_testcase_file(render_data, testcase_file_path)

        logger.info('用例文件已全部生成!')

    @staticmethod
    def _prepare_api_testcase_data(ao, call_ao_list, api_render_data, new_call_ao_list):
        extract_values = re.findall('\$Vars\.(.*?)\$', str(ao))
        # 当前api参数有依赖，在call_ao_list中找依赖api，并加入到api_render_data
        if extract_values:
            for call_ao in call_ao_list:
                call_ao_extract = call_ao.get('extract')
                if call_ao_extract:
                    extract_name_list = [i.get('var_name') for i in call_ao_extract]
                    for ev in extract_values:
                        if ev in extract_name_list:
                            new_call_ao_list.append(call_ao)
            for call_ao in new_call_ao_list:
                render_ao_class = api_render_data.get(ao['class_name'])
                if render_ao_class:
                    render_ao_method = render_ao_class.get(ao['method_name'])
                    if not render_ao_method:
                        render_ao_list = list()
                        if call_ao not in render_ao_list:
                            render_ao_list.append(call_ao)
                            import_list = [i.get('ao') for i in render_ao_list]
                            import_list.append(ao.get('class_name'))
                            render_ao_class[ao['method_name']] = render_ao_list
                            render_ao_class['import_list'] = import_list
                    else:
                        method_list = [i.get('method') for i in render_ao_method]
                        if ao['method_name'] not in method_list:
                            if call_ao not in render_ao_method:
                                render_ao_method.append(call_ao)
                                render_ao_class['import_list'].append(call_ao.get('ao'))
                else:

                    api_render_data.update(
                        {ao['class_name']: {ao['method_name']: [], 'import_list': []}})
                    render_ao_list = api_render_data.get(ao['class_name']).get(
                        ao['method_name'])
                    render_ao_list.append(call_ao)
                    import_list = [i.get('ao') for i in render_ao_list]
                    import_list.append(ao.get('class_name'))
                    api_render_data[ao['class_name']]['import_list'] = import_list
            else:
                _ao_list = api_render_data[ao['class_name']].get(ao['method_name'])
                _import_list = api_render_data[ao['class_name']].get('import_list')
                api_render_data[ao['class_name']]['import_list'] = list(set(_import_list))
                _ao_list.append(ao)

        else:
            api_render_data.update(
                {ao['class_name']: {ao['method_name']: [ao], 'import_list': [ao['class_name']]}})

    @staticmethod
    def _make_api_testcase_file(api_render_data, test_api_dir):
        for k, v in api_render_data.items():
            import_list = set(v.pop('import_list'))
            method_list = list(v.keys())
            content = Temp.TEMP_API_CASE2.render(
                {'test_class': k, 'import_list': import_list, 'method_list': method_list, 'steps': v})
            test_api_module_path = os.path.join(test_api_dir, f'test_{k.lower()}')
            testcase_api_file_path = f'{test_api_module_path}.py'
            if not os.path.exists(testcase_api_file_path):
                with open(testcase_api_file_path, mode='w', encoding='utf-8') as f:
                    f.write(content)

    @staticmethod
    def _make_scenario_testcase_file(render_data, testcase_file_path):
        if not os.path.exists(testcase_file_path):
            content = Temp.TEMP_SCENARIO_CASE.render(render_data)
            with open(testcase_file_path, mode='w', encoding='utf-8') as f:
                f.write(content)
            # subprocess.run(f'black {testcase_file_path}')
            os.system(f'black {testcase_file_path}')
        else:
            print(f'{testcase_file_path} 已存在！')

    @staticmethod
    def _handle_data_driven(step_data: Mapping[Text, List]) -> List[Dict]:
        """
        step_data:

        step_data = {
            'user_name': ['admin1', 'admin2', 'admin3'],
            'password': ['zhu8jie', 'zhu9jie', 'zhu10jie']
        }

        return：

        step_data = [
            {username:admin1,password:zhu88jie},
            {username:admin2,password:zhu9jie}
        ]
        """
        keys = list(step_data.keys())
        values = list(step_data.values())
        new_step_data = list()
        for v in zip_longest(*values):
            dic = dict()
            for k, vv in zip(keys, v):
                dic[k] = vv
            for k, value in dic.items():
                if value is None:
                    dic[k] = new_step_data[-1][k]
            new_step_data.append(dic)
        return new_step_data

    @staticmethod
    def __handle_api_datas(api_datas, class_name, method_name, datas):
        class_ = api_datas.get(class_name)
        if class_:
            method = class_.get(method_name)
            if not method:
                api_datas[class_name].update({method_name: datas})
        else:
            api_datas[class_name] = {method_name: datas}
        return api_datas

    @staticmethod
    def _write_api_data(key, value, api_data_dir):
        logger.info("开始生成YAML测试数据文件...")
        yaml_file = f'{api_data_dir}\\{key}.yaml'
        # 不覆盖同名文件
        if not os.path.exists(yaml_file):
            utils.dump_yaml({key: value}, yaml_file)
        logger.info(f"YAML测试数据文件：{yaml_file} 已生成！")

    @staticmethod
    def _write_scenario_data(class_name, testcase_name, test_step_datas, scenario_data_file_path):
        data = {
            class_name: {
                testcase_name: test_step_datas
            }
        }
        # 不覆盖已有同名文件
        if not os.path.exists(scenario_data_file_path):
            utils.dump_yaml(data, scenario_data_file_path)

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
            assert_dict['comparator'] = "assert_" + comparator
            assert_dict['expr'] = assert_data[0]
            assert_dict['expect'] = assert_data[-1]
            assert_dict['index'] = assert_data[1] if len(assert_data) == 3 else 0
            # if len(assert_data) == 3:
            #     assert_dict['index'] = assert_data[1]
            new_assert_content.append(assert_dict)
        return new_assert_content

    def _render_ao(self, module, method_name, content, dependent_params: List):
        with open(module) as f:
            template = f.read()
            if f'{{{{ {method_name}_params }}}}' in template:
                temp = Template(template, undefined=DebugUndefined)
                data = temp.render({f'{method_name}_params': content})
                new_data = self.__replace_params(data, dependent_params)
                with open(module, mode='w+') as f:
                    f.write(new_data)

    @staticmethod
    def __replace_params(data: str, dependent_params: List):
        # 有依赖参数才进行替换
        if dependent_params:
            str_with_mark: list = re.findall('(\$\w*?\$)', data)
            str_without_mark: list = re.findall('\$(\w*?)\$', data)
            for replace_mark, replace_value in zip(str_with_mark, str_without_mark):
                # 处理依赖参数
                for dep in dependent_params:
                    var = dep.get('params')
                    if var == replace_value:
                        jsonpath_expr = dep.get('jsonpath')
                        expr_index = dep.get('index')
                        if jsonpath_expr:
                            replace_value = f'self.cache.get_by_jsonpath("{var}",jsonpath_expr="{jsonpath_expr}")'
                            if expr_index is not None:
                                replace_value = f'self.cache.get_by_jsonpath("{var}",jsonpath_expr="{jsonpath_expr}", expr_index={expr_index})'
                        else:
                            replace_value = f'self.cache.get({var.get()})'
                        data = data.replace(f"'{replace_mark}'", replace_value)
            data = data.replace('"{', '{').replace('}"', "}")
            data = data.replace('"self.', 'self.').replace(')"', ')')
            data = data.replace('"test_data', 'test_data').replace(']"', ']')

        return data


def init_yaml_parse(file_path: Text):
    yp = YamlParse(file_path)
    return yp


def remove_dependent_api(ao_list: list) -> list:
    """在测试步骤接口列表中，去除被依赖的接口"""
    dep_apis = []
    for ao in ao_list:
        dependent_api_list = ao.get("dependent_api")
        if dependent_api_list is not None:
            for dependent_api in dependent_api_list:
                _, dep_module = dependent_api.get('module').split(".")
                x = {"module": dep_module, "api": dependent_api["api"]}
                if x not in dep_apis:
                    dep_apis.append(x)
    return dep_apis

