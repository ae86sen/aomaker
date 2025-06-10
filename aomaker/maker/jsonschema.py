from __future__ import annotations
import re
import urllib.parse
import keyword

from typing import Optional, List, Dict, Set, Tuple, Literal, Any

from aomaker.maker.models import DataModel, Import, DataType, DataModelField, JsonSchemaObject, Reference
from aomaker.log import logger

TypeMap = {
    'string': ('str', None),
    'integer': ('int', None),
    'number': ('float', None),
    'boolean': ('bool', None),
    'array': ('List', {Import(from_='typing', import_='List')}),
    'object': ('Dict', {Import(from_='typing', import_='Dict')}),
}


class ReferenceResolver:
    def __init__(self, schemas: Dict):
        self.schemas = schemas
        self.schema_objects: Dict[str, JsonSchemaObject] = self._preprocess_schemas()
        self.registry: Dict[str, DataModel] = {}

    def _preprocess_schemas(self) -> Dict[str, JsonSchemaObject]:
        return {
            name: JsonSchemaObject.model_validate(schema_)
            for name, schema_ in self.schemas.items()
        }

    def get_ref_schema(self, name: str) -> Optional[JsonSchemaObject]:
        logger.debug(f"尝试获取引用schema: {name}")

        if name.startswith("#/components/schemas/"):
            original_name = name
            name = name.split("/")[-1]
            logger.debug(f"提取schema名称: {original_name} -> {name}")

        if "%" in name:
            original_name = name
            decoded_name = urllib.parse.unquote(name)
            logger.debug(f"URL解码schema名称: {original_name} -> {decoded_name}")
            schema = self.schema_objects.get(decoded_name)
        else:
            schema = self.schema_objects.get(name)

        if schema is None:
            # 尝试使用规范化名称查找
            normalized_name = normalize_class_name(name)
            logger.debug(f"原始名称未找到schema，尝试使用规范化名称: {name} -> {normalized_name}")
            schema = self.schema_objects.get(normalized_name)

        if schema is None:
            logger.warning(f"无法找到schema: {name}")
        else:
            logger.debug(f"成功找到schema: {name}")

        return schema


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, DataModel] = {}  # 已生成的模型
        self.placeholders: Set[str] = set()

    def add_placeholder(self, name: str):
        self.placeholders.add(name)

    def register(self, model: DataModel):
        if model.name in self.placeholders:
            self.placeholders.remove(model.name)
        self.models[model.name] = model

    def get(self, name: str) -> DataModel:
        if name in self.placeholders:
            raise ValueError(f"Model {name} is still a placeholder")
            # raise ModelNotGeneratedError(f"Model {name} is still a placeholder")
        return self.models.get(name)


class JsonSchemaParser:
    def __init__(self, schemas: Dict):
        self.resolver = ReferenceResolver(schemas)
        self.model_registry = ModelRegistry()
        self.schema_registry: Dict[str, DataModel] = {}
        self.imports: Set[Import] = set()
        self.current_tags: List[str] = list()
        self.max_recursion_depth = 15
        self.current_recursion_path: List[str] = []

    def parse_schema(self, schema_obj: JsonSchemaObject, context: str) -> DataType:

        if len(self.current_recursion_path) >= self.max_recursion_depth:
            logger.warning(f"递归深度达到限制 ({self.max_recursion_depth}) at path: {self.current_recursion_path}. 返回 Any.")
            return DataType(
                type="Any",
                imports={Import(from_='typing', import_='Any')}
            )

        self.current_recursion_path.append(context)

        try:
            if schema_obj.ref:
                return self._parse_reference(schema_obj.ref)

            if schema_obj.anyOf or schema_obj.oneOf:
                if self._should_be_literal(schema_obj.oneOf):
                    union_type = "Literal"
                else:
                    union_type = "Union"
                return self._parse_union_type(
                    schema_obj.anyOf or schema_obj.oneOf,
                    context,
                    union_type=union_type
                )
            if schema_obj.allOf:
                return self._parse_all_of(schema_obj.allOf, context)

            # 检查是否有 const 值 (OpenAPI 3.1)
            if schema_obj.const is not None:
                return self._parse_const(schema_obj, context)

            if schema_obj.enum:
                return self._parse_enum(schema_obj, context)

            if schema_obj.type == 'object' or schema_obj.properties:
                return self._parse_object_type(schema_obj, context)

            if schema_obj.is_array:
                return self._parse_array_type(schema_obj, context)

            return self._parse_basic_datatype(schema_obj)
        finally:
            self.current_recursion_path.pop()

    def _parse_object_type(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        """深度解析对象类型"""
        model_name = context
        is_add_optional_import = False

        # 如果没有属性，则视为空模型
        if not schema_obj.properties:
            fields = []
            required_fields = []
        else:
            fields = []
            required_fields = schema_obj.required or []
            for prop_name, prop_schema in schema_obj.properties.items():
                original_prop_name = prop_name  # 保存原始字段名用于 required 检查
                prop_type = self.parse_schema(prop_schema, f"{model_name}_{prop_name}")
                
                # 规范化字段名，处理连字符等非法字符
                normalized_prop_name, alias = normalize_field_name(prop_name)
                prop_name = normalized_prop_name

                # 从 schema 中提取约束条件
                field_constraints = {}

                # 提取字符串类约束
                if prop_schema.min_length is not None:
                    field_constraints['min_length'] = prop_schema.min_length
                if prop_schema.max_length is not None:
                    field_constraints['max_length'] = prop_schema.max_length
                if prop_schema.pattern is not None:
                    field_constraints['pattern'] = prop_schema.pattern

                # 提取数值类约束
                if prop_schema.minimum is not None:
                    field_constraints['minimum'] = prop_schema.minimum
                if prop_schema.maximum is not None:
                    field_constraints['maximum'] = prop_schema.maximum
                if prop_schema.exclusive_minimum is not None:
                    field_constraints['exclusive_minimum'] = prop_schema.exclusive_minimum
                if prop_schema.exclusive_maximum is not None:
                    field_constraints['exclusive_maximum'] = prop_schema.exclusive_maximum
                if prop_schema.multiple_of is not None:
                    field_constraints['multiple_of'] = prop_schema.multiple_of

                # 提取数组类约束
                if prop_schema.min_items is not None:
                    field_constraints['min_items'] = prop_schema.min_items
                if prop_schema.max_items is not None:
                    field_constraints['max_items'] = prop_schema.max_items
                if prop_schema.unique_items is not None:
                    field_constraints['unique_items'] = prop_schema.unique_items

                field = DataModelField(
                    name=prop_name,
                    data_type=prop_type,
                    required=original_prop_name in required_fields,  # 使用原始字段名检查 required
                    default=prop_schema.default,
                    description=prop_schema.description,
                    alias=alias,
                    **field_constraints
                )
                fields.append(field)
                if not field.required:
                    is_add_optional_import = True

        fields.sort(key=lambda field_: not field_.required)
        imports_from_fields = self._collect_imports_from_fields(fields)
        if is_add_optional_import:
            imports_from_fields.add(Import(from_='typing', import_='Optional'))

        if model_name.endswith("RequestBody"):
            # request_body非引用的情况
            return DataType(
                type=model_name,
                is_custom_type=False,
                is_inline=True,
                fields=fields,
                imports=imports_from_fields
            )

        # 检查是否为空模型，如果是空模型则不注册，返回None类型
        if not fields:
            logger.debug(f"跳过注册空模型: {model_name}")
            return self._parse_basic_datatype(schema_obj)

        data_model = DataModel(
            name=model_name,
            fields=fields,
            description=schema_obj.description,
            tags=self.current_tags,
            imports=imports_from_fields,
            required=set(schema_obj.required),
        )
        self.model_registry.register(data_model)

        return DataType(
            type=model_name,
            is_custom_type=True,
            imports={Import(from_='.models', import_=model_name)}
        )

    def _parse_basic_datatype(self, schema_obj: JsonSchemaObject) -> DataType:
        base_type, imports = self._get_type_mapping(schema_obj.type, schema_obj.format)

        return DataType(
            type=base_type,
            is_optional=schema_obj.nullable,
            imports=imports
        )


    def _is_basic_type(self, schema_obj: JsonSchemaObject) -> bool:
        return (
                schema_obj.type in {'string', 'integer', 'number', 'boolean'}
                and not schema_obj.properties
                and not schema_obj.items
                and not schema_obj.ref
                and not schema_obj.format  # 无特殊格式
                and schema_obj.minimum is None
                and schema_obj.maximum is None
        )

    def _parse_array_type(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        item_schema = schema_obj.items
        item_type = self.parse_schema(item_schema, f"{context}Item")
        
        if item_type.is_custom_type:
            dt = DataType(
                type=f"List[{item_type.type_hint}]",
                is_list=True,
                data_types=[item_type],
                is_custom_type=False,
                imports=item_type.imports | {Import(from_='typing', import_='List')}
            )
            return dt
        
        dt = DataType(
            type=f"List[{item_type.type_hint}]",
            is_list=True,
            data_types=[item_type],
            imports=item_type.imports | {Import(from_='typing', import_='List')}
        )
        return dt

    def _parse_reference(self, ref: str) -> DataType:
        """处理 $ref 引用，返回已注册模型的DataType"""
        logger.debug(f"开始处理引用: {ref}")

        if len(self.current_recursion_path) >= self.max_recursion_depth:
            logger.warning(f"处理引用 {ref} 前检测到递归深度达到限制 ({self.max_recursion_depth}) at path: {self.current_recursion_path}. 返回 Any.")
            return DataType(
                type="Any",
                imports={Import(from_='typing', import_='Any')}
            )

        ref_name = ref.split("/")[-1]
        import urllib.parse

        if "%" in ref_name:
            old_ref_name = ref_name
            ref_name = urllib.parse.unquote(ref_name)
            logger.debug(f"URL解码引用名: {old_ref_name} -> {ref_name}")

        # 规范化类名
        normalized_name = normalize_class_name(ref_name)
        logger.debug(f"引用名规范化: {ref_name} -> {normalized_name}")

        # 创建原始名称到规范化名称的映射
        if not hasattr(self, '_ref_name_mapping'):
            self._ref_name_mapping = {}

        self._ref_name_mapping[ref_name] = normalized_name

        # 检查是否已经在当前递归路径中
        if normalized_name in self.current_recursion_path:
            logger.debug(f"检测到循环引用: {normalized_name}, 路径: {self.current_recursion_path}")
            # 检测到循环引用，返回前向引用
            return DataType(
                type=normalized_name,
                is_custom_type=True,
                is_forward_ref=True,
                imports={Import(from_='.models', import_=normalized_name)}
            )

        # 使用规范化名称检查模型注册表
        if normalized_name not in self.model_registry.models:
            logger.debug(f"模型 {normalized_name} 未注册，开始解析原始schema")
            # 获取原始schema并使用规范化名称解析
            ref_schema = self.resolver.get_ref_schema(ref)
            if ref_schema is None:
                logger.warning(f"无法找到引用的schema: {ref}")
                return DataType(
                    type="Any",
                    imports={Import(from_='typing', import_='Any')},
                )
            else:
                logger.debug(f"找到引用schema，开始解析: {ref}")
                self.parse_schema(ref_schema, normalized_name)
        else:
            logger.debug(f"模型 {normalized_name} 已注册，更新标签")
            model = self.model_registry.get(normalized_name)
            if model:
                self._update_model_tags_recursive(model)

        # 返回使用规范化名称的DataType
        logger.debug(f"引用处理完成，返回类型: {normalized_name}")
        datatype = DataType(
            type=normalized_name,
            is_custom_type=True,
            imports={Import(from_='.models', import_=normalized_name)},
            reference=Reference(ref=ref)
        )

        return datatype

    def _parse_union_type(
            self,
            schemas: List[JsonSchemaObject],
            context: str,
            union_type: Literal["Union", "Literal"] = "Union"
    ) -> DataType:
        """通用方法处理 anyOf/oneOf"""
        child_types = []
        imports = set()
        has_null = False

        for i, schema_ in enumerate(schemas):
            # 检查是否有null类型
            if schema_.type == 'null':
                has_null = True
                continue

            child_type = self.parse_schema(schema_, f"{context}_{union_type}{i}")
            child_types.append(child_type)
            imports.update(child_type.imports)

        # 处理空列表情况（所有元素都是null）
        if not child_types:
            return DataType(
                type="None",
                imports=set(),
                is_optional=True
            )

        # 检查是否有Any类型
        any_types = [t for t in child_types if t.type_hint == "Any"]
        if any_types:
            # 如果有Any类型，简化为Any或Optional[Any]
            if has_null:
                return DataType(
                    type="Optional[Any]",
                    imports={Import(from_='typing', import_='Any'), Import(from_='typing', import_='Optional')},
                    is_optional=True
                )
            else:
                return DataType(
                    type="Any",
                    imports={Import(from_='typing', import_='Any')},
                    is_optional=False
                )

        # 如果只有一个非null类型，且有null类型，则使用Optional
        if has_null and len(child_types) == 1:
            return DataType(
                type=child_types[0].type_hint,
                data_types=child_types,
                imports=imports | {Import(from_='typing', import_='Optional')},
                is_optional=True 
            )

        # 如果有多个非null类型，且有null类型，则使用Union加Optional
        if has_null and len(child_types) > 1:
            type_hint = f"Union[{', '.join(t.type_hint for t in child_types)}]"
            return DataType(
                type=type_hint,
                data_types=child_types,
                imports=imports | {Import(from_='typing', import_='Optional'), Import(from_='typing', import_='Union')},
                is_optional=True
            )

        # 如果没有null类型
        type_hint = f"{union_type}[{', '.join(t.type_hint for t in child_types)}]"
        return DataType(
            type=type_hint,
            data_types=child_types,
            imports=imports | {Import(from_='typing', import_=union_type)},
            is_optional=False
        )

    def _parse_all_of(
            self,
            schemas: List[JsonSchemaObject],
            context: str
    ) -> DataType:
        """解析 allOf 结构，合并所有子模式的属性和约束"""
        if len(schemas) == 1:
            return self.parse_schema(schemas[0], context)

        merged_fields: List[DataModelField] = []
        merged_required: Set[str] = set()
        merged_imports: Set[Import] = set()
        merged_descriptions: List[str] = []

        for schema_ in schemas:
            data_type = self.parse_schema(schema_, f"{context}_AllOfPart")
            data_model = self.model_registry.get(data_type.type)
            if not data_model:
                 logger.warning(f"在 allOf 合并期间未能找到模型: {data_type.type} (来自 {context})")
                 continue

            merged_fields.extend(data_model.fields)
            merged_required.update(data_model.required)
            merged_imports.update(data_model.imports)

            if data_model.description:
                merged_descriptions.append(data_model.description)

        valid_descriptions = [desc for desc in merged_descriptions if desc is not None]

        merged_model = DataModel(
            name=f"{context}Combined",
            fields=self._merge_fields(merged_fields),
            imports=merged_imports,
            tags=self.current_tags,
            description="\n".join(valid_descriptions)
        )
        merged_model.required = {f.name for f in merged_model.fields if f.required}

        self.model_registry.register(merged_model)

        return DataType(
            type=merged_model.name,
            is_custom_type=True,
            reference=Reference(ref=merged_model.name),
            imports={Import(from_='.models', import_=merged_model.name)}
        )

    def _merge_fields(self, fields: List[DataModelField]) -> List[DataModelField]:
        """合并重复字段（后出现的覆盖先前的）"""
        seen = {}
        for field_ in reversed(fields):
            if field_.name not in seen:
                seen[field_.name] = field_
        return list(reversed(seen.values()))

    def _parse_const(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        """处理 OpenAPI 3.1 中的 const 关键字，将其视为单值 Literal 类型"""
        base_type, imports = self._get_type_mapping(schema_obj.type, schema_obj.format)
        const_value = schema_obj.const

        # 使用 Literal 类型，将 const 值作为唯一可能的值
        imports.add(Import(from_='typing', import_='Literal'))

        # 如果值是字符串、整数或浮点数等简单类型，直接使用
        if isinstance(const_value, (str, int, float, bool)):
            type_hint = f"Literal[{repr(const_value)}]"
            return DataType(
                type=type_hint,
                imports=imports,
                is_optional=schema_obj.nullable
            )
        else:
            # 对于复杂类型（如对象、数组等），回退到基本类型
            # 注意：严格来说，这不符合 const 的语义，但这里是一个合理的妥协
            return DataType(
                type=base_type,
                imports=imports,
                is_optional=schema_obj.nullable
            )

    def _parse_enum(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        base_type = self._parse_basic_datatype(schema_obj)
        fields = []
        for value in schema_obj.enum:
            field_name = normalize_enum_name(value)
            if is_python_keyword(field_name=field_name):
                alias = field_name  # 原始名称作为 alias
                field_name = f"{field_name}_"  # 修改后的名称作为字段名
            else:
                alias = None
            fields.append(DataModelField(
                name=field_name,
                data_type=base_type,
                default=repr(value),
                alias=alias
            ))
        enum_model = DataModel(
            name=context,
            is_enum=True,
            tags=self.current_tags,
            imports={Import(from_="enum", import_="Enum")},
            fields=fields
        )

        self.model_registry.register(enum_model)

        return DataType(
            type=enum_model.name,
            imports={Import(from_='.models', import_=enum_model.name)},
            is_custom_type=True
        )

    def _collect_imports_from_fields(self, fields: List[DataModelField]) -> Set[Import]:
        imports = set()
        for f in fields:
            imports.update(f.data_type.imports)
        return imports

    def _generate_enum_name(self, schema_obj: JsonSchemaObject) -> str:
        return schema_obj.title.replace(' ', '') if schema_obj.title else f"AnonymousEnum_{id(schema_obj)}"

    def _should_be_literal(self, schemas: List[JsonSchemaObject]) -> bool:
        if not schemas:
            return False
        return all(s.enum and len(s.enum) == 1 for s in schemas)

    def _update_model_tags_recursive(self, model: DataModel):
        for tag in self.current_tags:
            if tag not in model.tags:
                model.tags.append(tag)

        for field in model.fields:
            if field.data_type.is_custom_type and not field.data_type.is_forward_ref:
                nested_model_name = field.data_type.type
                nested_model = self.model_registry.get(nested_model_name)
                if nested_model:
                    self._update_model_tags_recursive(nested_model)

    def _get_type_mapping(self, schema_type: str, schema_format: Optional[str] = None) -> Tuple[str, Set[Import]]:
        # 处理类型是列表的情况
        if isinstance(schema_type, list):
            # 检查是否包含null类型
            has_null = "null" in schema_type
            # 移除null类型，获取第一个非null类型
            non_null_types = [t for t in schema_type if t != "null"]

            if not non_null_types:  # 如果只有null
                return 'None', set()

            # 使用第一个非null类型
            schema_type = non_null_types[0]

            # 获取基本类型映射
            base_type, imports = self._get_base_type_mapping(schema_type, schema_format)

            # 如果有null，标记为Optional
            if has_null:
                return f"Optional[{base_type}]", imports.union({Import(from_='typing', import_='Optional')})
            return base_type, imports

        # 原始逻辑用于字符串类型
        return self._get_base_type_mapping(schema_type, schema_format)

    def _get_base_type_mapping(self, schema_type: str, schema_format: Optional[str] = None) -> Tuple[str, Set[Import]]:
        default_imports = {Import(from_='typing', import_='Any')}
        base_type, imports_or_none = TypeMap.get(schema_type, ('Any', default_imports))
        imports = set() if imports_or_none is None else imports_or_none

        if schema_type == 'string':
            if schema_format == 'date-time':
                return 'datetime', {Import(from_='datetime', import_='datetime')}
            elif schema_format == 'date':
                return 'date', {Import(from_='datetime', import_='date')}
            elif schema_format == 'uuid':
                return 'UUID', {Import(from_='uuid', import_='UUID')}
            # 网络类型
            elif schema_format == 'email':
                return 'str', set()  # Python 中电子邮件仍然是字符串，但可以添加元数据
            elif schema_format == 'uri' or schema_format == 'uri-reference':
                return 'str', set()
            elif schema_format == 'ipv4' or schema_format == 'ipv6':
                return 'str', set()  # 或者可以考虑使用 ipaddress 模块

            # 二进制数据
            elif schema_format == 'byte':  # base64 编码的字符串
                return 'bytes', set()
            elif schema_format == 'binary':  # 二进制数据
                return 'bytes', set()
        return base_type, imports

def normalize_enum_name(value: Any) -> str:
    """规范化枚举值名称，生成有效的 Python 标识符，支持 Unicode"""
    # 转换为字符串
    str_value = str(value)

    # 替换非字母数字（包括 Unicode）和下划线的字符为下划线
    # 使用 \w 包含字母、数字、下划线，并显式添加中文范围
    name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', str_value)

    # 确保名称不为空，如果为空则使用原始值的安全版本
    if not name:
        name = f'value_{re.sub(r"[^a-zA-Z0-9_]", "_", str_value)}' # Fallback for completely invalid original value
        if not name.strip('value_'): # If still empty after fallback
             name = 'value_empty' # Final fallback

    # 处理数字开头的情况
    # 添加 name and 检查，防止空字符串导致 IndexError
    if name and name[0].isdigit():
        name = f'value_{name}'

    # 处理原始值只包含非法字符，导致 name 只剩下下划线的情况
    # 使用处理后的 name 而不是原始 str_value 来构建，确保合法性
    if name.strip('_') == '':
        # Example: input ' ' -> name = '_', strip = '' -> name = 'value__'
        # Example: input '%' -> name = '_', strip = '' -> name = 'value__'
        name = f'value_{name}' # 用处理后的 name (下划线) 构建

    # 转换为小写
    name = name.lower()
    return name


def normalize_class_name(name: str) -> str:
    """将名称规范化为合法的 Python 类名（大驼峰命名），支持 Unicode。"""
    logger.debug(f"开始规范化类名: {name}")
    original_name = name

    # 处理 Java 泛型符号
    if '«' in name:
        pattern = r'(\w+)«(.+?)»'
        while re.search(pattern, name):
            old_name = name
            name = re.sub(pattern, r'\1Of\2', name)
            logger.debug(f"泛型处理: {old_name} -> {name}")

    # 替换非法字符（非字母数字包括 Unicode，非下划线）为下划线
    old_name = name
    name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', name)
    if old_name != name:
        logger.debug(f"特殊字符处理: {old_name} -> {name}")

    # 如果处理后名称为空，直接返回默认名称
    if not name or name == '_': # 处理完全由非法字符组成的名称
        logger.debug(f"处理后名称为空或仅为下划线，返回默认名称: {original_name} -> UnnamedModel")
        return "UnnamedModel"

    # 存储是否需要前导下划线（因为数字开头）
    needs_leading_underscore = name[0].isdigit()

    # 转换为大驼峰形式
    old_name = name
    parts = name.split('_')
    # 使用 part[0].upper() + part[1:] 来保证 PascalCase，避免 capitalize() 的副作用
    # 同时过滤掉因连续下划线产生的空部分
    name = ''.join(part[0].upper() + part[1:] if part else '' for part in parts if part)

    if not name: # 如果分割和处理后变为空（例如输入 "__"）
        logger.debug(f"大驼峰处理后为空，返回默认名称: {original_name} -> UnnamedModel")
        return "UnnamedModel"


    # 如果原始名称以数字开头，确保最终名称有前导下划线
    if needs_leading_underscore and not name.startswith('_'):
         name = '_' + name
         logger.debug(f"添加前导下划线（因数字开头）: {old_name} -> {name}")
    elif not needs_leading_underscore and name.startswith('_') and len(parts)>1 and parts[0]=='':
         # 处理原本以下划线开头的情况, e.g., _my_var -> MyVar (移除因split产生的前导下划线)
         # 只有在非数字开头且确实是下划线分割产生的首个空部分时才移除
         pass # 在 join 时已处理好类似 _my_var -> MyVar

    # 确保首字母大写（对于没有下划线的情况）
    if name and not name[0].isupper() and not name.startswith('_'):
         name = name[0].upper() + name[1:]

    logger.debug(f"类名规范化完成: {original_name} -> {name}")
    return name


def normalize_field_name(field_name: str) -> Tuple[str, Optional[str]]:
    """
    规范化字段名为合法的Python标识符
    
    Args:
        field_name: 原始字段名
        
    Returns:
        Tuple[str, Optional[str]]: (规范化后的字段名, 原始字段名作为alias或None)
    """
    original_name = field_name
    
    # 如果字段名包含连字符、空格或其他非法字符，需要处理
    if not field_name.isidentifier() or is_python_keyword(field_name):
        # 将连字符、空格等替换为下划线
        normalized = re.sub(r'[^\w]', '_', field_name)
        
        # 如果以数字开头，添加下划线前缀
        if normalized and normalized[0].isdigit():
            normalized = f'_{normalized}'
        
        # 如果是Python关键字，添加下划线后缀
        if is_python_keyword(normalized):
            normalized = f'{normalized}_'
            
        # 如果处理后为空或只有下划线，使用默认名称
        if not normalized or normalized.strip('_') == '':
            normalized = 'field_'
            
        return normalized, original_name
    else:
        # 字段名已经是合法的Python标识符，不需要alias
        return field_name, None


def is_python_keyword(field_name: str) -> bool:
    return field_name in keyword.kwlist
