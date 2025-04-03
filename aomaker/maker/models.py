# --coding:utf-8--
import re
from dataclasses import field
from enum import Enum
from functools import cached_property
from typing import Any, Dict, List, Optional, Union, Set
from pydantic import BaseModel, Field, ConfigDict, field_validator


def normalize_python_name(name: str, to_pascal_case: bool = True) -> str:
    """将名称规范化为合法的Python标识符
    
    Args:
        name: 要规范化的名称
        to_pascal_case: 是否转换为大驼峰形式（PascalCase），适用于类名
        
    Returns:
        规范化后的名称
    """
    # 如果名称为空，返回默认值
    if not name:
        return "DefaultModel"
    
    # 处理泛型表示法，例如 "响应结果«boolean»"
    generic_match = re.search(r'^(.*?)«(.+?)»$', name)
    if generic_match:
        outer_type = generic_match.group(1)
        inner_type = generic_match.group(2)
        
        # 递归处理内部类型（处理嵌套泛型情况）
        normalized_inner = normalize_python_name(inner_type)
        
        # 组合成最终类名 (例如: 响应结果Of_Boolean)
        name = f"{outer_type}Of{normalized_inner}"
    
    # 替换非法字符，但保留中文字符
    normalized = re.sub(r'[^\w\u4e00-\u9fff]', '_', name)
    
    # 确保不以数字或下划线开头
    if normalized and (normalized[0].isdigit() or normalized[0] == '_'):
        normalized = 'X' + normalized
    
    # 转换为大驼峰形式
    if to_pascal_case and '_' in normalized:
        # 将连续的下划线替换为单个下划线
        normalized = re.sub(r'_+', '_', normalized)
        # 分割字符串，保留每个部分原有的大小写形式，但确保首字母大写
        parts = normalized.split('_')
        normalized = ''.join(
            (part[0].upper() + part[1:]) if part else ''
            for part in parts
        )
    elif to_pascal_case and normalized:
        # 处理已有驼峰形式的情况，确保首字母大写
        normalized = normalized[0].upper() + normalized[1:] if normalized else ''
    
    # 确保结果不为空
    if not normalized:
        return "DefaultModel"
    
    return normalized


class Reference(BaseModel):
    # name: str
    ref: str = Field(..., alias='$ref')  # 存储引用路径，例如 "#/components/schemas/Pet"

    class Config:
        populate_by_name = True


class Import(BaseModel):
    """导入语句"""
    from_: Optional[str]
    import_: str
    alias: Optional[str] = None
    model_config = ConfigDict(
        frozen=True,
        extra='forbid'
    )


class DataType(BaseModel):
    type: str
    normalized_name: Optional[str] = None  # 添加规范化名称字段
    reference: Optional[Reference] = None
    data_types: Optional[List['DataType']] = None
    is_list: bool = False
    is_dict: bool = False
    is_optional: bool = False
    is_custom_type: bool = False
    is_forward_ref: bool = False
    is_inline: bool = False
    imports: Set[Import] = Field(default_factory=set)
    fields: List["DataModelField"] = Field(default_factory=list)

    # @field_validator('type')
    # @classmethod
    # def normalize_type_name(cls, type_name: str, info) -> str:
    #     if getattr(info.data, 'is_custom_type', False):
    #         return normalize_python_name(type_name)
    #     return type_name

    # @field_validator('imports')
    # @classmethod
    # def normalize_import_names(cls, imports: Set[Import], info) -> Set[Import]:
    #     # 只有自定义类型需要规范化导入名称
    #     if getattr(info.data, 'is_custom_type', False):
    #         new_imports = set()
    #         for imp in imports:
    #             if imp.from_ == '.models':
    #                 # 规范化导入的模型名称
    #                 new_imports.add(Import(
    #                     from_=imp.from_,
    #                     import_=normalize_python_name(imp.import_),
    #                     alias=imp.alias
    #                 ))
    #             else:
    #                 new_imports.add(imp)
    #         return new_imports
    #     return imports

    @property
    def type_hint(self) -> str:
        """生成类型提示"""
        type_str = self.type
        
        # 确保自定义类型使用规范化名称
        if self.is_custom_type and type_str:
            # 如果已有normalized_name，优先使用
            if hasattr(self, 'normalized_name') and self.normalized_name:
                type_str = self.normalized_name
            else:
                # 否则计算规范化名称
                type_str = normalize_python_name(type_str)
            
        if self.is_list:
            # 确保列表元素类型也被规范化
            if self.data_types and self.data_types[0].is_custom_type:
                inner_type = self.data_types[0].type_hint  # 递归调用type_hint确保内部类型也被规范化
            else:
                inner_type = self.data_types[0].type_hint if self.data_types else 'Any'
            type_str = f'List[{inner_type}]'
        elif self.is_dict:
            key_type = self.data_types[0].type_hint if self.data_types else 'str'
            value_type = self.data_types[1].type_hint if len(self.data_types) > 1 else 'Any'
            type_str = f'Dict[{key_type}, {value_type}]'
        elif self.is_optional:
            type_str = f'Optional[{type_str}]'
        
        return type_str


class DataModelField(BaseModel):
    """模型字段"""
    name: str
    data_type: DataType
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None
    alias: Optional[str] = None
    
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    exclusive_minimum: Union[bool, int, float, None] = None
    exclusive_maximum: Union[bool, int, float, None] = None
    multiple_of: Optional[Union[int, float]] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: Optional[bool] = None


DataType.model_rebuild()
DataModelField.model_rebuild()


class DataModel(BaseModel):
    """数据模型"""
    name: str  # 原始名称
    normalized_name: Optional[str] = None  # 规范化后的名称，用于生成Python类
    fields: List[DataModelField]
    tags: List[str] = Field(default_factory=list)
    is_enum: bool = False
    is_inline: bool = False  # 是否内联在接口类中
    reference: Optional[Reference] = None
    description: Optional[str] = None
    base_class: str = "attrs.define"
    imports: Set[Import] = Field(default_factory=set)
    required: List[DataModelField] = Field(default_factory=list)
    is_forward_ref: bool = False

    # @field_validator('name')
    # @classmethod
    # def normalize_model_name(cls, name: str) -> str:
    #     return normalize_python_name(name)


class ParameterLocation(str, Enum):
    query = 'query'
    path = 'path'
    header = 'header'
    cookie = 'cookie'


class MediaTypeEnum(Enum):
    """常用的 Media Type 枚举"""
    JSON = "application/json"
    XML = "application/xml"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"
    HTML = "text/html"
    BINARY = "application/octet-stream"
    PDF = "application/pdf"
    ANY = "*/*"


class Example(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    value: Any = None
    externalValue: Optional[str] = None


class MediaType(BaseModel):
    schema_: Union[Reference, "JsonSchemaObject", None] = Field(
        None, alias='schema'
    )
    example: Any = None
    examples: Union[str, Reference, Example, None] = None


class Parameter(BaseModel):
    name: Optional[str] = None
    in_: Optional[ParameterLocation] = Field(None, alias='in')
    description: Optional[str] = None
    required: bool = False
    deprecated: bool = False
    schema_: Optional["JsonSchemaObject"] = Field(None, alias='schema')
    example: Any = None
    examples: Union[str, Reference, Example, None] = None
    content: Dict[str, MediaType] = Field(default_factory=dict)


class RequestBody(BaseModel):
    content: Dict[str, MediaType] = None
    required: bool = False
    description: Optional[str] = None


class Response(BaseModel):
    content: Dict[str, MediaType] = None
    description: Optional[str] = None


class Operation(BaseModel):
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    parameters: List[Union[Reference, Parameter]] = field(default_factory=list)
    requestBody: Union[Reference, RequestBody, None] = None
    responses: Dict[Union[str, int], Union[Reference, Response]] = field(default_factory=dict)
    deprecated: bool = False


class Endpoint(BaseModel):
    class_name: str
    path: str
    method: str
    endpoint_id: str = field(default=None)
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    path_parameters: List[DataModelField] = field(default_factory=list)
    query_parameters: List[DataModelField] = field(default_factory=list)
    header_parameters: List[DataModelField] = field(default_factory=list)
    request_body: Optional[DataModel] = None
    response: Optional[DataModel] = None
    imports: Set[Import] = field(default_factory=set)


class APIGroup(BaseModel):
    tag: str
    endpoints: List[Endpoint] = field(default_factory=list)
    models: Dict[str, DataModel] = field(default_factory=dict)
    endpoint_names: Set[str] = field(default_factory=set)

    def collect_models(self, model_registry):
        """从全局注册表中收集属于当前 Tag 的模型"""
        # 所有要收集的模型
        models_to_collect = {}
        
        # 1. 按标签匹配收集模型
        for name, model in model_registry.models.items():
            if not model.is_inline and (self.tag in model.tags or not model.tags):
                # 确保模型有normalized_name属性
                if not hasattr(model, 'normalized_name') or not model.normalized_name:
                    model.normalized_name = normalize_python_name(model.name)
                
                # 使用原始名称作为键
                models_to_collect[name] = model
                
        # 2. 添加在endpoints中引用的模型
        for endpoint in self.endpoints:
            # 添加响应模型
            if endpoint.response and endpoint.response.name:
                if endpoint.response.name in model_registry.models:
                    models_to_collect[endpoint.response.name] = model_registry.models[endpoint.response.name]
            
            # 添加请求体模型
            if endpoint.request_body and endpoint.request_body.name:
                if endpoint.request_body.name in model_registry.models:
                    models_to_collect[endpoint.request_body.name] = model_registry.models[endpoint.request_body.name]
        
        # 3. 递归添加依赖模型
        added = True
        while added:
            added = False
            new_models = {}
            
            for model in models_to_collect.values():
                for field in model.fields:
                    # 如果字段类型是自定义类型，检查是否需要添加该类型的模型
                    if field.data_type.is_custom_type and field.data_type.type:
                        ref_name = field.data_type.type
                        if ref_name in model_registry.models and ref_name not in models_to_collect:
                            new_models[ref_name] = model_registry.models[ref_name]
                            added = True
            
            # 添加新发现的模型
            models_to_collect.update(new_models)
        
        # 更新API组的模型字典
        self.models = models_to_collect

    def add_endpoint(self, endpoint: Endpoint):
        name = endpoint.class_name
        if name in self.endpoint_names:
            i = 1
            while f"{name}_{i}" in self.endpoint_names:
                i += 1
            name = f"{name}_{i}"
            endpoint.class_name = name
        self.endpoint_names.add(name)
        self.endpoints.append(endpoint)


class JsonSchemaObject(BaseModel):
    """ 仅用于解析 OpenAPI Schema 的中间模型，与最终生成的 attrs 模型无关 """

    type: Union[str, List[str], None] = None
    format: Optional[str] = None
    items: Union['JsonSchemaObject', List['JsonSchemaObject'], None] = None
    properties: Optional[Dict[str, 'JsonSchemaObject']] = None
    required: List[str] = field(default_factory=list)
    enum: List[Any] = field(default_factory=list)
    const: Any = None  # 添加 OpenAPI 3.1 的 const 字段
    ref: Optional[str] = Field(None, alias='$ref')  # 解析 $ref 时使用
    nullable: bool = False
    title: str = None

    # 数值类约束
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    exclusive_minimum: Union[bool, int, float, None] = Field(None, alias='exclusiveMinimum')  # 添加别名
    exclusive_maximum: Union[bool, int, float, None] = Field(None, alias='exclusiveMaximum')  # 添加别名
    multiple_of: Optional[Union[int, float]] = Field(None, alias='multipleOf')  # 添加别名
    
    # 字符串类约束
    min_length: Optional[int] = Field(None, alias='minLength')
    max_length: Optional[int] = Field(None, alias='maxLength')
    pattern: Optional[str] = None
    
    # 数组类约束
    min_items: Optional[int] = Field(None, alias='minItems')
    max_items: Optional[int] = Field(None, alias='maxItems')
    unique_items: Optional[bool] = Field(None, alias='uniqueItems')

    oneOf: List["JsonSchemaObject"] = field(default_factory=list)
    anyOf: List["JsonSchemaObject"] = field(default_factory=list)
    allOf: List["JsonSchemaObject"] = field(default_factory=list)

    description: Optional[str] = None
    default: Any = None

    @cached_property
    def is_array(self) -> bool:
        return self.items is not None or self.type == 'array'

    @cached_property
    def is_object(self) -> bool:
        return (
                self.properties is not None
                or self.type == 'object'
                and not self.allOf
                and not self.oneOf
                and not self.anyOf
                and not self.ref
        )


JsonSchemaObject.model_rebuild()

if __name__ == '__main__':
    Reference(ref="#/components/schemas/EnvModel")
