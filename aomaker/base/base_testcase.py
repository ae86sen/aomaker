# --coding:utf-8--

from jsonschema import validate, ValidationError

from aomaker.log import logger
from aomaker.storage import Schema
from aomaker.exceptions import SchemaNotFound


class BaseTestcase:

    @staticmethod
    def assert_eq(actual_value, expected_value, msg: str = ""):
        """
        equals
        """
        try:
            assert actual_value == expected_value, msg
        except AssertionError as e:
            logger.error(f"eq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_gt(actual_value, expected_value, msg: str = ""):
        """
        greater than
        """
        try:
            assert actual_value > expected_value, msg
        except AssertionError as e:
            logger.error(f"gt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_lt(actual_value, expected_value, msg: str = None):
        """
        less than
        """
        try:
            assert actual_value < expected_value, msg
        except AssertionError as e:
            logger.error(f"lt断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_neq(actual_value, expected_value, msg: str = ""):
        """
        not equals
        """
        try:
            assert actual_value != expected_value, msg
        except AssertionError as e:
            logger.error(f"neq断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_ge(actual_value, expected_value, msg: str = ""):
        """
        greater than or equals
        """
        try:
            assert actual_value >= expected_value, msg
        except AssertionError as e:
            logger.error(f"ge断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_le(actual_value, expected_value, msg: str = ""):
        """
        less than or equals
        """
        try:
            assert actual_value <= expected_value, msg
        except AssertionError as e:
            logger.error(f"le断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_contains(actual_value, expected_value, msg: str = ""):
        assert isinstance(
            expected_value, (list, tuple, dict, str, bytes)
        ), "expect_value should be list/tuple/dict/str/bytes type"
        try:
            assert expected_value in actual_value, msg
        except AssertionError as e:
            logger.error(f"contains断言失败，预期结果：{expected_value}，实际结果：{actual_value}，message：{msg}")
            raise e

    @staticmethod
    def assert_schema(instance, api_name):
        """
        Assert JSON Schema
        :param instance: 请求响应结果
        :param api_name: 存放在schema表中的对应key名
        :return:
        """
        json_schema = Schema().get(api_name)
        if json_schema is None:
            logger.error('jsonschema未找到！')
            raise SchemaNotFound(api_name)
        try:
            validate(instance, schema=json_schema)
        except ValidationError as msg:
            logger.error(msg)
            raise AssertionError
