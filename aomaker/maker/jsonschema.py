from __future__ import annotations
import re
import keyword

from typing import Optional, List, Dict, Set, Tuple, Literal, Any

from aomaker.maker.models import DataModel, Import, DataType, DataModelField, JsonSchemaObject, Reference

TypeMap = {
    'string': ('str', set()),
    'integer': ('int', set()),
    'number': ('float', set()),
    'boolean': ('bool', set()),
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
        if name.startswith("#/components/schemas/"):
            name = name.split("/")[-1]
        if "%" in name:
            import urllib.parse
            decoded_name = urllib.parse.unquote(name)
            return self.schema_objects.get(decoded_name)
        return self.schema_objects.get(name)


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
            raise
            # raise ModelNotGeneratedError(f"Model {name} is still a placeholder")
        return self.models.get(name)


class JsonSchemaParser:
    def __init__(self, schemas: Dict):
        self.resolver = ReferenceResolver(schemas)
        self.model_registry = ModelRegistry()
        self.schema_registry: Dict[str, DataModel] = {}  # 全局模型注册表
        self.imports: Set[Import] = set()  # 统一管理导入
        self.current_tags: List[str] = list()

    def parse_schema(self, schema_obj: JsonSchemaObject, context: str) -> DataType:

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

        if schema_obj.enum:
            return self._parse_enum(schema_obj, context)

        if schema_obj.is_array:
            return self._parse_array_type(schema_obj, context)

        if schema_obj.properties:
            return self._parse_object_type(schema_obj, context)

        return self._parse_basic_datatype(schema_obj)

    def _parse_object_type(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        """深度解析对象类型"""
        model_name = context

        fields = []
        required_fields = schema_obj.required or []
        is_add_optional_import = False
        for prop_name, prop_schema in schema_obj.properties.items():
            prop_type = self.parse_schema(prop_schema, f"{model_name}_{prop_name}")
            alias = f"{prop_name}_" if is_python_keyword(prop_name) else None
            field = DataModelField(
                name=prop_name,
                data_type=prop_type,
                required=prop_name in required_fields,
                default=prop_schema.default,
                description=prop_schema.description,
                alias=alias
            )
            fields.append(field)
            if field.required:
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

        data_model = DataModel(
            name=model_name,
            fields=fields,
            description=schema_obj.description,
            tags=self.current_tags,
            imports=imports_from_fields
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

    def _get_type_mapping(self, schema_type: str, schema_format: Optional[str] = None) -> Tuple[str, Set[Import]]:
        if schema_type == 'string':
            if schema_format == 'date-time':
                return 'datetime', {Import(from_='datetime', import_='datetime')}
            elif schema_format == 'date':
                return 'date', {Import(from_='datetime', import_='date')}
            elif schema_format == 'uuid':
                return 'UUID', {Import(from_='uuid', import_='UUID')}

        return TypeMap.get(schema_type, ('Any', {Import(from_='typing', import_='Any')}))

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

        if item_type.is_list:
            return item_type

        return DataType(
            type=f"List[{item_type.type_hint}]",
            is_list=True,
            data_types=[item_type],
            imports=item_type.imports | {Import(from_='typing', import_='List')}
        )

    def _parse_reference(self, ref: str) -> DataType:
        """处理 $ref 引用，返回已注册模型的DataType"""
        ref_name = ref.split("/")[-1]
        import urllib.parse

        if "%" in ref_name:
            ref_name = urllib.parse.unquote(ref_name)
        if ref_name not in self.model_registry.models:
            ref_schema = self.resolver.get_ref_schema(ref)
            self.parse_schema(ref_schema, ref_name)
        else:
            model = self.model_registry.get(ref_name)
            if model:
                self._update_model_tags_recursive(model)
        datatype = DataType(
            type=ref_name,
            is_custom_type=True,
            imports={Import(from_='.models', import_=ref_name)},
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
                type=f"Optional[{child_types[0].type_hint}]",
                data_types=child_types,
                imports=imports | {Import(from_='typing', import_='Optional')},
                is_optional=True
            )

        # 如果有多个非null类型，且有null类型，则使用Union加Optional
        if has_null and len(child_types) > 1:
            type_hint = f"Optional[Union[{', '.join(t.type_hint for t in child_types)}]]"
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

            merged_fields.extend(data_model.fields)
            merged_required.update(data_model.required)
            merged_imports.update(data_model.imports)

            if data_model.description:
                merged_descriptions.append(schema_.description)

        merged_model = DataModel(
            name=f"{context}Combined",
            fields=self._merge_fields(merged_fields),
            required=merged_required,
            imports=merged_imports,
            tags=self.current_tags,
            description="\n".join(merged_descriptions)
        )

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

    def _parse_enum(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        base_type = self._parse_basic_datatype(schema_obj)
        fields = []
        for value in schema_obj.enum:
            field_name = normalize_name(value)
            if is_python_keyword(field_name=field_name):
                alias = f"{field_name}_"
                field_name = alias
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


def normalize_name(value: Any) -> str:
    """规范化枚举值名称"""
    # 转换为字符串
    str_value = str(value)
    # 替换特殊字符为下划线
    name = re.sub(r'[^a-zA-Z0-9]', '_', str_value)
    # 处理数字开头的情况
    if name[0].isdigit():
        name = f'value_{name}'
    # 处理纯下划线的情况
    if name.strip('_') == '':
        name = f'value_{str_value}'
    # 确保是有效的 Python 标识符
    name = name.lower()
    return name


def is_python_keyword(field_name: str) -> bool:
    if field_name in keyword.kwlist:
        return True
    return False


if __name__ == '__main__':
    x = {
        'properties': {
            'aipods_scope': {'description': '产品范围', 'title': 'Aipods Scope', 'type': 'string'},
            'aipods_type': {'description': '规格类型', 'title': 'Aipods Type', 'type': 'string'},
            'aipods_usage': {'description': '资源类型', 'title': 'Aipods Usage', 'type': 'string'},
            'cpu_count': {'description': 'CPU核数', 'title': 'Cpu Count', 'type': 'string'},
            'cpu_model': {'description': 'CPU型号', 'title': 'Cpu Model', 'type': 'string'},
            'disk': {'description': '数据盘', 'title': 'Disk', 'type': 'string'},
            'gpu_count': {'description': 'GPU数量', 'title': 'Gpu Count', 'type': 'string'},
            'gpu_memory': {'description': 'GPU显存', 'title': 'Gpu Memory', 'type': 'string'},
            'gpu_model': {'description': 'GPU型号', 'title': 'Gpu Model', 'type': 'string'},
            'memory': {'description': '内存', 'title': 'Memory', 'type': 'string'},
            'network': {'default': '0', 'description': 'IB网络', 'title': 'Network', 'type': 'string'},
            'nvlink': {'default': '0', 'description': 'nvlink', 'title': 'Nvlink', 'type': 'string'},
            'os_disk': {'description': '系统盘', 'title': 'Os Disk', 'type': 'string'}
        },
        'required': ['aipods_type', 'aipods_scope', 'aipods_usage', 'cpu_count', 'memory', 'cpu_model', 'gpu_model',
                     'gpu_count', 'gpu_memory', 'os_disk', 'disk'],
        'title': 'AddProductRequest',
        'type': 'object'
    }

    # 直接解析
    schema = JsonSchemaObject.model_validate(x)
    print(schema)
