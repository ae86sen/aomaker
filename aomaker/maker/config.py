# --coding:utf-8--
import re
from typing import Optional, Callable

from inflection import camelize
from attrs import define, field

from aomaker.maker.models import Operation


class ClassNameStrategy:
    """OpenAPI 接口类名生成策略"""

    @staticmethod
    def from_operation_id(operation: Operation, suffix: str = "API") -> str:
        """
        从operationId生成类名
        示例:
        - create_user..._post → CreateUserCreatePostAPI
        """
        operation_id = operation.operationId
        if not operation_id:
            path_parts = []

            path = getattr(operation, '_path', '')
            method = getattr(operation, '_method', '')

            if operation.tags and len(operation.tags) > 0:
                tag = operation.tags[0]
                path_parts.append(tag)

            if path:
                clean_path_parts = [p for p in path.split('/') if p and not (p.startswith('{') and p.endswith('}'))]
                path_parts.extend(clean_path_parts)

            if method:
                path_parts.append(method.lower())

            if not path_parts and operation.summary:
                return ClassNameStrategy.from_summary(operation, suffix)
            elif not path_parts:
                return f"Default{suffix}"

            operation_id = '_'.join(path_parts)

        # 清理特殊字符并合并连续下划线
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", operation_id)
        cleaned = re.sub(r"_+", "_", cleaned)
        return ClassNameStrategy._format_name(cleaned, suffix, separator='_')

    @staticmethod
    def from_summary(operation: Operation, suffix: str = "API") -> str:
        """
        从summary生成类名（修正空格处理和驼峰转换）
        示例:
        - "Create User" → CreateUserAPI
        """
        summary = operation.summary
        if not summary:
            raise ValueError("Summary is required for this naming strategy")

        # 清理特殊字符并合并连续空格
        cleaned = re.sub(r"[^a-zA-Z0-9 ]", " ", summary).strip()
        cleaned = re.sub(r" +", " ", cleaned)
        return ClassNameStrategy._format_name(cleaned, suffix, separator=' ')

    @staticmethod
    def from_tags(operation: Operation, suffix: str = "API") -> str:
        """
        从tags生成类名
        示例:
        - tags=["User"] + operationId=getUser → UserGetUserAPI
        """
        tags = operation.tags
        tag_part = camelize(tags[0]) if tags else ""
        operation_part = ClassNameStrategy.from_operation_id(operation, suffix="")
        return f"{tag_part}{operation_part}{suffix}"

    @staticmethod
    def _format_name(raw: str, suffix: str, separator: str = '_') -> str:
        """通用格式化方法"""
        # 替换非法字符并统一分隔符
        processed = re.sub(fr"[^{re.escape(separator)}\w]", "_", raw)
        # 将自定义分隔符转为下划线并合并连续下划线
        processed = re.sub(fr"{re.escape(separator)}", "_", processed)
        processed = re.sub(r"_+", "_", processed)

        # 驼峰式转换（保持首字母大写）
        camelized = camelize(processed, uppercase_first_letter=True)

        return f"{camelized}{suffix}" if suffix else camelized


NAMING_STRATEGIES = {
    "operation_id": ClassNameStrategy.from_operation_id,
    "summary": ClassNameStrategy.from_summary,
    "tags": ClassNameStrategy.from_tags,
}

@define
class OpenAPIConfig:
    class_name_strategy: Callable = field(default=NAMING_STRATEGIES["operation_id"])
    enable_translation: bool = field(default=False)
    base_api_class: str = field(default="aomaker.core.api_object.BaseAPIObject")  # 默认基类路径
    base_api_class_alias: Optional[str] = field(default=None)  # 自定义别名

    @base_api_class.validator
    def check(self, attribute, value):
        if value.count('.') < 1:
            raise ValueError("必须包含完整模块路径（例如：package.module.subModule.ClassName）")
        return value


if __name__ == '__main__':
    OpenAPIConfig(base_api_class="x.asd")
