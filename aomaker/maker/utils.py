# --coding:utf-8--
import re
import keyword


class NameStyleConverterMixin:
    @staticmethod
    def to_pascal_case(name: str) -> str:
        """将字符串转换为大驼峰风格（PascalCase）"""
        # 处理特殊字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # 处理下划线和空格
        words = re.split(r'[_\s]+', name)
        # 首字母大写
        return ''.join(word.capitalize() for word in words if word)

    @staticmethod
    def to_camel_case(name: str) -> str:
        """将字符串转换为小驼峰风格（camelCase）"""
        pascal = NameStyleConverterMixin.to_pascal_case(name)
        if not pascal:
            return ''
        return pascal[0].lower() + pascal[1:]

    @staticmethod
    def to_snake_case(name: str) -> str:
        """将字符串转换为蛇形命名（snake_case）"""
        # 处理特殊字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # 在大写字母前添加下划线
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        # 转换为小写并处理多余的下划线
        return re.sub(r'_+', '_', s2.lower()).strip('_')

    @staticmethod
    def safe_name(name: str, style: str = 'snake') -> str:
        """生成安全的Python标识符，避免关键字冲突"""
        if style == 'pascal':
            converted = NameStyleConverterMixin.to_pascal_case(name)
        elif style == 'camel':
            converted = NameStyleConverterMixin.to_camel_case(name)
        else:  # 默认使用snake_case
            converted = NameStyleConverterMixin.to_snake_case(name)

        # 确保不是空字符串
        if not converted:
            converted = 'unnamed'

        # 确保不以数字开头
        if converted[0].isdigit():
            converted = 'n' + converted

        # 处理关键字冲突
        if keyword.iskeyword(converted) or converted in ('None', 'True', 'False'):
            converted += '_'

        return converted