# --coding:utf-8--
import re
from typing import Optional,Callable

from translate import Translator
from attrs import define,field

from aomaker.maker.models import Operation

class ClassNameStrategy:
    # 内置术语词典
    TERM_MAP = {
        "对外端口": "ExternalPort",
        "工作空间": "Workspace",
        "新增": "Add"
    }

    @classmethod
    def from_summary(cls, operation: Operation, method: str) -> str:
        """智能处理中英文混合summary"""
        # if not operation.summary:
        #     return cls.fallback_name(operation, method)

        # 预处理：术语替换 → 分词 → 混合翻译
        processed = cls._preprocess_text(operation.summary)
        translated = cls._translate_mixed_text(processed)
        class_name = cls._format_class_name(translated, method)

        return f"{class_name}API"

    @classmethod
    def _preprocess_text(cls, text: str) -> str:
        """预处理：清洗+术语替换"""
        # 去除特殊字符
        cleaned = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)
        # 术语替换
        for zh, en in cls.TERM_MAP.items():
            cleaned = cleaned.replace(zh, en)
        return cleaned.strip()

    @classmethod
    def _translate_mixed_text(cls, text: str) -> str:
        """智能处理中英文混合文本"""
        buffer = []
        current_segment = []
        is_english = False

        for char in text:
            if cls._is_chinese(char):
                if is_english and current_segment:
                    buffer.append(''.join(current_segment))
                    current_segment = []
                is_english = False
                current_segment.append(char)
            else:
                if not is_english and current_segment:
                    buffer.append(cls._translate_chinese(''.join(current_segment)))
                    current_segment = []
                is_english = True
                current_segment.append(char)

        if current_segment:
            if is_english:
                buffer.append(''.join(current_segment))
            else:
                buffer.append(cls._translate_chinese(''.join(current_segment)))

        return ' '.join(buffer)

    @staticmethod
    def _is_chinese(char: str) -> bool:
        return '\u4e00' <= char <= '\u9fff'

    @classmethod
    def _translate_chinese(cls, text: str) -> str:
        """仅翻译纯中文部分"""
        try:
            return Translator(to_lang="en", from_lang="zh-cn").translate(text).title()
        except:
            return text  # 翻译失败时返回原文

    @classmethod
    def _format_class_name(cls, text: str, method: str) -> str:
        """格式化类名"""
        # 方法前缀（如Post/Get）
        # method_prefix = method.capitalize()

        # 处理混合大小写
        words = re.findall(r'[A-Z]?[a-z]+|\d+|[A-Z]+(?=[A-Z]|$)', text)
        core_name = ''.join(word.title() for word in words if word)

        return core_name

    # @classmethod
    # def fallback_name(cls, operation: 'Operation', method: str) -> str:
    #     """极简回退策略"""
    #     if operation.operationId:
    #         parts = operation.operationId.split('_')[1:-2]
    #         return f"{method.capitalize()}{''.join(p.title() for p in parts)}API"
    #
    #     last_path = operation.path.split('/')[-1]
    #     return f"{method.capitalize()}{last_path.title().replace('_', '')}API"

    @classmethod
    def from_operation_id(cls, operation: Operation, method: str) -> str:
        """改进的operationId策略"""
        if not operation.operationId:
            return f"Anonymous{method.capitalize()}API"

        parts = operation.operationId.split('_')
        filtered = [p for p in parts[1:-2] if p not in ["get", "post"]]
        return f"{method.capitalize()}{''.join(p.title() for p in filtered)}API"

    @classmethod
    def from_path(cls, path, method: str) -> str:
        """路径策略"""
        core = path.split('/')[-1].replace('_', '').title()
        return f"{method.capitalize()}{core}API"



@define
class OpenAPIConfig:
    class_name_strategy: Callable = field(default=ClassNameStrategy.from_summary)
    backend_prefix: Optional[str] = field(default=None)  # 显式指定的后端前缀
    frontend_prefix: Optional[str] = field(default=None)  # 显式指定的前端前缀
    base_api_class: str = field(default="aomaker.core.api_object.BaseAPIObject")  # 默认基类路径
    base_api_class_alias: Optional[str] = field(default=None)  # 自定义别名

    @base_api_class.validator
    def check(self,attribute,value):
        if value.count('.') < 1:
            raise ValueError("必须包含完整模块路径（例如：package.module.subModule.ClassName）")
        return value

if __name__ == '__main__':
    OpenAPIConfig(base_api_class="x.asd")