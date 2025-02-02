# --coding:utf-8--
# from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Any, Dict, List, Optional, Union, Set, TYPE_CHECKING
from pydantic import BaseModel, Field,ConfigDict



class Reference(BaseModel):
    # name: str
    ref: str = Field(..., alias='$ref')  # 存储引用路径，例如 "#/components/schemas/Pet"
    class Config:
        populate_by_name = True  # 允许使用字段名而不是别名


class Import(BaseModel):
    """导入语句"""
    from_: Optional[str]
    import_: str
    alias: Optional[str] = None
    model_config = ConfigDict(
        frozen=True,    # 冻结实例（Python 3.11+）
        extra='forbid'  # 禁止额外字段
    )


class DataType(BaseModel):
    type: str
    reference: Optional[Reference] = None
    data_types: Optional[List['DataType']] = None
    is_list: bool = False
    is_dict: bool = False
    is_optional: bool = False
    is_custom_type: bool = False
    is_forward_ref: bool = False  # 标记是否为前向引用
    is_inline: bool = False       # 是否是内联类型（直接展开字段）
    imports: Set[Import] = field(default_factory=set)  # 新增字段
    fields: List["DataModelField"] = field(default_factory=list) # 新增：内联字段（当 is_inline=True 时有效）

    @property
    def type_hint(self) -> str:
        """生成类型提示"""
        type_str = self.type
        if self.is_list:
            inner_type = self.data_types[0].type_hint if self.data_types else 'Any'
            type_str = f'List[{inner_type}]'
        elif self.is_dict:
            key_type = self.data_types[0].type_hint if self.data_types else 'str'
            value_type = self.data_types[1].type_hint if len(self.data_types) > 1 else 'Any'
            type_str = f'Dict[{key_type}, {value_type}]'
        elif self.is_optional:
            type_str = f'Optional[{type_str}]'
        elif self.is_custom_type:
            type_str = f"{self.type}"
        return type_str


class DataModelField(BaseModel):
    """模型字段"""
    name: str
    data_type: DataType
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None

DataType.model_rebuild()
DataModelField.model_rebuild()

class DataModel(BaseModel):
    """数据模型"""
    name: str
    fields: List[DataModelField]
    tags: List[str] = field(default_factory=list)
    is_enum: bool = False
    is_inline: bool = False  # 是否内联在接口类中
    reference: Optional[Reference] = None
    description: Optional[str] = None
    base_class: str = "attrs.define"
    imports: Set[Import] = field(default_factory=set)
    required:List[DataModelField] = field(default_factory=set)
    is_forward_ref: bool = False


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
    content: Dict[str, MediaType] = field(default_factory=dict)


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
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    path_parameters: List[DataModelField] = field(default_factory=list)
    query_parameters: List[DataModelField] = field(default_factory=list)
    header_parameters: List[DataModelField] = field(default_factory=list)
    request_body: Optional[DataModel] = None
    response: Optional[DataModel] = None
    imports:Set[Import] = field(default_factory=set)


class APIGroup(BaseModel):
    tag: str
    endpoints: List[Endpoint] = field(default_factory=list)
    models: Dict[str, DataModel] = field(default_factory=dict)

    def collect_models(self, model_registry):
        """从全局注册表中收集属于当前 Tag 的模型"""
        # todo: 有的模型可能会同时出现在多个tag中，这种其实可以提取出来放到common中，看怎么处理
        for model in model_registry.models.values():
            if self.tag in model.tags:
                self.models[model.name] = model

class JsonSchemaObject(BaseModel):
    """ 仅用于解析 OpenAPI Schema 的中间模型，与最终生成的 attrs 模型无关 """

    # 基础字段
    type: Union[str, List[str], None] = None
    format: Optional[str] = None
    items: Union['JsonSchemaObject', List['JsonSchemaObject'], None] = None
    properties: Optional[Dict[str, 'JsonSchemaObject']] = None
    required: List[str] = field(default_factory=list)
    enum: List[Any] = field(default_factory=list)
    ref: Optional[str] = Field(None, alias='$ref')  # 解析 $ref 时使用
    nullable: bool = False
    title: str = None

    # 约束字段（可选，根据是否需要校验逻辑保留）
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    min_length: Optional[int] = Field(None, alias='minLength')
    max_length: Optional[int] = Field(None, alias='maxLength')

    oneOf: List["JsonSchemaObject"] = field(default_factory=list)
    anyOf: List["JsonSchemaObject"] = field(default_factory=list)
    allOf: List["JsonSchemaObject"] = field(default_factory=list)
    # 其他字段（按需添加）
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


# 处理前向引用
JsonSchemaObject.model_rebuild()

if __name__ == '__main__':
    Reference(ref="#/components/schemas/EnvModel")