# --coding:utf-8--
# debug使用
import sys
sys.path.insert(0, 'D:\\项目列表\\aomaker')
from typing import Text, NoReturn

from jsonpath import jsonpath
from jsonschema import validate, ValidationError

from aomaker.log import logger
from aomaker.cache import Schema
from aomaker.exceptions import SchemaNotFound


class BaseTestcase:
    @staticmethod
    def extract_set_vars(res, var_name: Text, expr: Text, index=None) -> NoReturn:
        """
        提取响应结果中的变量并设置为参数池属性
        :param res: the json-encoded content of response
        :param var_name:
        :param expr: jsonpath expr
        :param index: jsonpath result index
        :return:
        """
        index = index if index else 0
        extract_variable = jsonpath(res, expr)[index]
        # setattr(ParamsPool().Vars, var_name, extract_variable)

    @staticmethod
    def assert_eq(actual_value, expected_value):
        """
        equals
        """
        try:
            assert actual_value == expected_value
        except AssertionError as e:
            logger.error(f"eq断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_gt(actual_value, expected_value):
        """
        greater than
        """
        try:
            assert actual_value > expected_value
        except AssertionError as e:
            logger.error(f"gt断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_lt(actual_value, expected_value):
        """
        less than
        """
        try:
            assert actual_value < expected_value
        except AssertionError as e:
            logger.error(f"lt断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_neq(actual_value, expected_value):
        """
        not equals
        """
        try:
            assert actual_value != expected_value
        except AssertionError as e:
            logger.error(f"neq断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_ge(actual_value, expected_value):
        """
        greater than or equals
        """
        try:
            assert actual_value >= expected_value
        except AssertionError as e:
            logger.error(f"ge断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_le(actual_value, expected_value):
        """
        less than or equals
        """
        try:
            assert actual_value <= expected_value
        except AssertionError as e:
            logger.error(f"le断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_contains(actual_value, expected_value):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expect_value should be list/tuple/dict/str/bytes type"
        try:
            assert expected_value in actual_value
        except AssertionError as e:
            logger.error(f"contains断言失败，预期结果：{expected_value}，实际结果：{actual_value}")
            raise e

    @staticmethod
    def assert_schema(instance, api_name):
        """
        Assert JSON Schema
        doc: https://json-schema.org/
        """
        json_schema = Schema().get(api_name)
        if json_schema is None:
            logger.error('jsonschema未找到！')
            raise SchemaNotFound(api_name)
        try:
            validate(instance, schema=json_schema)
            logger.warning(f"instance:{instance}\nschema:{json_schema}")
        except ValidationError as msg:
            logger.error(msg)
            raise AssertionError
