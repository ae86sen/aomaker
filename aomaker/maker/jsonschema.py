from __future__ import annotations

from typing import Optional, Any, List, Dict, Union, Set, Tuple, Literal

from aomaker.maker.models import DataModel, Import, DataType, DataModelField, JsonSchemaObject, Parameter, RequestBody, \
    Response, Reference

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
        self.schema_objects: Dict[str, JsonSchemaObject] = self._preprocess_schemas()  # 预处理所有模式
        self.registry: Dict[str, DataModel] = {}  # 模型注册表

    def _preprocess_schemas(self) -> Dict[str, JsonSchemaObject]:
        """预处理所有组件模式（关键初始化步骤）"""
        return {
            name: JsonSchemaObject.model_validate(schema_)
            for name, schema_ in self.schemas.items()
        }

    def get_ref_schema(self, name: str) -> Optional[JsonSchemaObject]:
        if name.startswith("#/components/schemas/"):
            name = name.split("/")[-1]
        return self.schema_objects.get(name)


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, DataModel] = {}  # 已生成的模型
        self.placeholders: Set[str] = set()

    def add_placeholder(self, name: str):
        """注册占位符处理前向引用"""
        self.placeholders.add(name)

    def register(self, model: DataModel):
        """注册完整模型"""
        if model.name in self.placeholders:
            self.placeholders.remove(model.name)
        self.models[model.name] = model

    def get(self, name: str) -> DataModel:
        """获取已注册模型"""
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
        # 0. 处理引用（优先级最高）
        if schema_obj.ref:
            return self._parse_reference(schema_obj.ref)
        # 1. 处理复合类型（新增）
        if schema_obj.anyOf or schema_obj.oneOf:
            if self._should_be_literal(schema_obj.oneOf):
                union_type = "Literal"
            else:
                union_type = "Union"  # 根据规范 anyOf≈Union，oneOf≈Literal（需根据实际需求调整）
            return self._parse_union_type(
                schema_obj.anyOf or schema_obj.oneOf,
                context,
                union_type=union_type
            )
        if schema_obj.allOf:
            return self._parse_all_of(schema_obj.allOf, context)

        # 2. 处理枚举类型
        if schema_obj.enum:
            return self._parse_enum(schema_obj, context)

        if schema_obj.is_array:
            return self._parse_array_type(schema_obj, context)

        if schema_obj.properties:
            return self._parse_object_type(schema_obj, context)

        return self._parse_basic_datatype(schema_obj)

    def _parse_object_type(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        """深度解析对象类型"""
        # 生成唯一模型名
        model_name = context


        # 解析字段
        fields = []
        required_fields = schema_obj.required or []
        is_add_optional_import = False
        for prop_name, prop_schema in schema_obj.properties.items():
            # 递归解析属性
            prop_type = self.parse_schema(prop_schema, f"{model_name}_{prop_name}")
            field = DataModelField(
                name=prop_name,
                data_type=prop_type,
                required=prop_name in required_fields,
                default=prop_schema.default,
                description=prop_schema.description,
            )
            # 构建字段
            fields.append(field)
            if field.required:
                is_add_optional_import = True

        fields.sort(key=lambda field_: not field_.required)
        imports_from_fields = self._collect_imports_from_fields(fields)
        if is_add_optional_import:
            imports_from_fields.add(Import(from_='typing', import_='Optional'))
        # 注册完整模型
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
        """增强版基础类型解析"""
        base_type, imports = self._get_type_mapping(schema_obj.type, schema_obj.format)

        return DataType(
            type=base_type,
            is_optional=schema_obj.nullable,
            imports=imports
        )

    def _get_type_mapping(self, schema_type: str, schema_format: Optional[str] = None) -> Tuple[str, Set[Import]]:
        """统一管理类型映射逻辑"""
        if schema_type == 'string':
            if schema_format == 'date-time':
                return 'datetime', {Import(from_='datetime', import_='datetime')}
            elif schema_format == 'date':
                return 'date', {Import(from_='datetime', import_='date')}
            elif schema_format == 'uuid':
                return 'UUID', {Import(from_='uuid', import_='UUID')}

        return TypeMap.get(schema_type, ('Any', {Import(from_='typing', import_='Any')}))

    def _is_basic_type(self, schema_obj: JsonSchemaObject) -> bool:
        """扩展判断逻辑：无额外约束的基础类型"""
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
        """解析数组类型"""
        # 解析数组元素类型
        item_schema = schema_obj.items
        item_type = self.parse_schema(item_schema, f"{context}Item")

        # 处理多维数组
        if item_type.is_list:
            return item_type  # 直接复用已有列表类型

        return DataType(
            type=f"List[{item_type.type_hint}]",
            is_list=True,
            data_types=[item_type],
            imports=item_type.imports | {Import(from_='typing', import_='List')}
        )

    def _parse_reference(self, ref: str) -> DataType:
        """处理 $ref 引用，返回已注册模型的DataType"""
        # 提取模型名称（假设引用格式为 #/components/schemas/ModelName）
        ref_name = ref.split("/")[-1]
        # 检查是否已解析过该模型
        if ref_name not in self.model_registry.models:
            # 若未解析，先解析被引用的Schema
            ref_schema = self.resolver.get_ref_schema(ref_name)
            self.parse_schema(ref_schema, ref_name)
        else:
            # 模型已存在，更新其 tags 及其嵌套模型的 tags
            model = self.model_registry.get(ref_name)
            if model:
                self._update_model_tags_recursive(model)  # 关键修改：递归更新
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
            union_type: Literal["Union", "Literal"] = Literal["Union"]
    ) -> DataType:
        """通用方法处理 anyOf/oneOf"""
        child_types = []
        imports = set()

        for i, schema_ in enumerate(schemas):
            child_type = self.parse_schema(schema_, f"{context}_{union_type}{i}")
            child_types.append(child_type)
            imports.update(child_type.imports)

        # 生成联合类型表达式
        type_hint = f"{union_type}[{', '.join(t.type_hint for t in child_types)}]"

        return DataType(
            type=type_hint,
            data_types=child_types,
            imports=imports | {Import(from_='typing', import_=union_type)},
            is_optional=any(t.is_optional for t in child_types)
        )

    def _parse_all_of(
            self,
            schemas: List[JsonSchemaObject],
            context: str
    ) -> DataType:
        """解析 allOf 结构，合并所有子模式的属性和约束"""
        if len(schemas) == 1:
            return self.parse_schema(schemas[0], context)
        # 初始化合并容器
        merged_fields: List[DataModelField] = []
        merged_required: Set[str] = set()
        merged_imports: Set[Import] = set()
        merged_descriptions: List[str] = []

        # 递归解析每个子模式
        for schema_ in schemas:
            # 解析子模式（自动处理引用和内联）
            data_type = self.parse_schema(schema_, f"{context}_AllOfPart")
            data_model = self.model_registry.get(data_type.type)
            # 处理引用模型
            # if data_type.is_custom_type and data_type.reference:
            #     ref_model = self.resolver.get_ref_schema(data_type.reference.ref)
            #
            #     if not ref_model:
            #         raise ValueError(f"引用的模型未找到: {data_type.reference.ref}")

            merged_fields.extend(data_model.fields)
            merged_required.update(data_model.required)
            merged_imports.update(data_model.imports)

            # 处理内联字段
            # elif data_type.is_inline:
            #     merged_fields.extend(data_type.fields)
            #     merged_required.update(
            #         field_.name for field_ in data_type.fields
            #         if field_.required
            #     )
            #     merged_imports.update(data_type.imports)

            # 收集描述信息
            if data_model.description:
                merged_descriptions.append(schema_.description)

        # 生成合并后的模型
        merged_model = DataModel(
            name=f"{context}Combined",
            fields=self._merge_fields(merged_fields),  # 处理字段冲突
            required=merged_required,
            imports=merged_imports,
            tags=self.current_tags,
            description="\n".join(merged_descriptions)
        )

        # 注册模型
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
        # 确定基础类型
        base_type = self._parse_basic_datatype(schema_obj)  # 根据schema.type判断基础类型

        # 生成枚举模型
        enum_model = DataModel(
            name=f"{context}Enum",
            is_enum=True,
            tags=self.current_tags,
            fields=[
                DataModelField(
                    name=str(value),
                    data_type=base_type,
                    default=repr(value)
                ) for value in schema_obj.enum
            ]
        )

        # 注册枚举模型
        self.model_registry.register(enum_model)

        return DataType(
            type=enum_model.name,
            imports={Import(from_='models', import_=enum_model.name)},
            is_custom_type=True
        )

    def _collect_imports_from_fields(self, fields: List[DataModelField]) -> Set[Import]:
        """从字段列表中收集 imports"""
        imports = set()
        for f in fields:
            imports.update(f.data_type.imports)
        return imports

    def _generate_enum_name(self, schema_obj: JsonSchemaObject) -> str:
        """生成枚举类名（示例逻辑）"""
        return schema_obj.title.replace(' ', '') if schema_obj.title else f"AnonymousEnum_{id(schema_obj)}"

    def _should_be_literal(self, schemas: List[JsonSchemaObject]) -> bool:
        """检查是否所有子模式都是单值枚举"""
        return all(s.enum and len(s.enum) == 1 for s in schemas)

    def _update_model_tags_recursive(self, model: DataModel):
        """递归更新模型及其所有嵌套子模型的 tags"""
        # 更新当前模型的 tags
        for tag in self.current_tags:
            if tag not in model.tags:
                model.tags.append(tag)

        # 递归处理字段中的嵌套模型
        for field in model.fields:
            # 如果字段类型是自定义模型类型
            if field.data_type.is_custom_type and not field.data_type.is_forward_ref:
                nested_model_name = field.data_type.type
                # 获取嵌套模型
                nested_model = self.model_registry.get(nested_model_name)
                if nested_model:
                    # 递归调用
                    self._update_model_tags_recursive(nested_model)
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
