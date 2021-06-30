
from string import Template
from faker import Faker

import yaml
from loguru import logger


class Utils:
    @classmethod
    def handle_yaml(cls, file_name):
        try:
            yaml_data = yaml.safe_load(open(file_name, encoding='utf-8'))
        except Exception as e:
            logger.error(f'yaml文件读取失败，文件名称：{file_name}')
            raise e
        else:
            return yaml_data

    @classmethod
    def handle_template(cls, source_data, replace_data: dict, ):
        """
        替换文本变量
        :param source_data:
        :param replace_data:
        :return:
        """
        res = Template(str(source_data)).safe_substitute(**replace_data)
        return yaml.safe_load(res)

    @classmethod
    def handle_random_phone(cls):
        """
        生成随机手机号
        :return:
        """
        fake = Faker(locale='zh_CN')
        phone_number = fake.phone_number()
        return phone_number
    