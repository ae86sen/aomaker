from __future__ import annotations
import re
import keyword

from typing import Optional, List, Dict, Set, Tuple, Literal, Any

from aomaker.maker.models import DataModel, Import, DataType, DataModelField, JsonSchemaObject, Reference, normalize_python_name
from aomaker.log import logger,aomaker_logger
aomaker_logger.change_level("DEBUG")

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
        # 添加一个映射表，存储原始名称到规范化名称的映射
        self.name_mapping: Dict[str, str] = {}
        # 添加反向映射，从规范化名称到原始名称
        self.reverse_name_mapping: Dict[str, Set[str]] = {}
        # 初始化名称映射关系
        self._initialize_name_mappings()

    def _preprocess_schemas(self) -> Dict[str, JsonSchemaObject]:
        return {
            name: JsonSchemaObject.model_validate(schema_)
            for name, schema_ in self.schemas.items()
        }
        
    def _initialize_name_mappings(self):
        """初始化名称映射关系，建立原始名称和规范化名称之间的双向映射"""
        for name in self.schemas.keys():
            normalized = normalize_python_name(name)
            # 原始名称到规范化名称的映射
            self.name_mapping[name] = normalized
            # 规范化名称到原始名称的映射（可能多对一）
            if normalized not in self.reverse_name_mapping:
                self.reverse_name_mapping[normalized] = set()
            self.reverse_name_mapping[normalized].add(name)

    def get_ref_schema(self, name: str) -> Optional[JsonSchemaObject]:
        """尝试通过多种策略获取引用的模式对象"""
        # 处理完整引用路径
        if name.startswith("#/components/schemas/"):
            name = name.split("/")[-1]
            
        # 处理URL编码的引用
        if "%" in name:
            import urllib.parse
            decoded_name = urllib.parse.unquote(name)
            schema = self.schema_objects.get(decoded_name)
            if schema:
                return schema
        
        # 1. 尝试直接通过原始名称获取
        schema = self.schema_objects.get(name)
        if schema:
            return schema
            
        # 2. 尝试通过规范化后的名称反查原始名称
        normalized_name = normalize_python_name(name)
        if normalized_name in self.reverse_name_mapping:
            # 获取所有与这个规范化名称关联的原始名称
            original_names = self.reverse_name_mapping[normalized_name]
            # 遍历所有可能的原始名称
            for orig_name in original_names:
                schema = self.schema_objects.get(orig_name)
                if schema:
                    return schema
        
        # 3. 尝试通过名称映射表查找
        if name in self.name_mapping:
            normalized = self.name_mapping[name]
            # 通过规范化名称反查所有可能的原始名称
            if normalized in self.reverse_name_mapping:
                for orig_name in self.reverse_name_mapping[normalized]:
                    schema = self.schema_objects.get(orig_name)
                    if schema:
                        return schema
                        
        # 4. 尝试模糊匹配（大小写不敏感）
        lower_name = name.lower()
        for orig_name, schema in self.schema_objects.items():
            if orig_name.lower() == lower_name:
                return schema
                
        return None


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, DataModel] = {}  # 使用原始名称作为键
        self.placeholders: Set[str] = set()  # 仍然使用规范化名称作为占位符
        self.original_to_normalized: Dict[str, str] = {}  # 原始名称到规范化名称的映射
        self.normalized_to_original: Dict[str, Set[str]] = {}  # 规范化名称到原始名称的反向映射
    
    def _normalize_name(self, name: str) -> str:
        """规范化模型名称，并维护双向映射"""
        if not name:
            return "DefaultModel"
        normalized = normalize_python_name(name)
        # 更新映射
        self.original_to_normalized[name] = normalized
        if normalized not in self.normalized_to_original:
            self.normalized_to_original[normalized] = set()
        self.normalized_to_original[normalized].add(name)
        return normalized
    
    def add_placeholder(self, name: str):
        """添加模型占位符"""
        normalized = self._normalize_name(name)
        if name not in self.models and normalized not in self.placeholders:
            logger.debug(f"[ModelRegistry.add_placeholder] Adding placeholder for: '{name}' (normalized: '{normalized}')")
            self.placeholders.add(normalized)
    
    def register(self, model: DataModel):
        """注册模型，使用原始名称作为键"""
        if not model.name:
            logger.warning("[ModelRegistry.register] Model name is empty, using 'DefaultModel'.")
            model.name = "DefaultModel"
        
        original_name = model.name
        logger.debug(f"[ModelRegistry.register] Received model with name: '{original_name}'")
        
        # 生成规范化名称，但不修改模型的原始名称
        normalized_name = self._normalize_name(original_name)
        
        # 设置模型的规范化名称属性
        model.normalized_name = normalized_name
        logger.debug(f"[ModelRegistry.register] Set normalized_name: '{normalized_name}' for model: '{original_name}'")
        
        # 检查是否已经存在同名模型
        if original_name in self.models:
            logger.warning(f"[ModelRegistry.register] Model with name '{original_name}' already registered. Skipping.")
            return  # 跳过注册
        
        # 如果存在相关的占位符，移除它
        if normalized_name in self.placeholders:
            logger.debug(f"[ModelRegistry.register] Removing placeholder: '{normalized_name}'")
            self.placeholders.remove(normalized_name)
        
        # 使用原始名称作为键注册模型
        logger.debug(f"[ModelRegistry.register] Registering model with original name: '{original_name}'")
        self.models[original_name] = model
    
    def get(self, name: str) -> Optional[DataModel]:
        """获取模型，优先使用原始名称查找"""
        logger.debug(f"[ModelRegistry.get] Attempting to get model with name: '{name}'")
        if not name:
            logger.warning("[ModelRegistry.get] Received empty name for get request.")
            return None
        
        # 1. 直接尝试使用原始名称查找
        if name in self.models:
            logger.debug(f"[ModelRegistry.get] Found model using original name: '{name}'")
            return self.models[name]
        
        # 2. 规范化请求的名称
        normalized_requested_name = self._normalize_name(name)
        
        # 3. 通过规范化名称查找可能的原始名称
        if normalized_requested_name in self.normalized_to_original:
            for orig_name in self.normalized_to_original[normalized_requested_name]:
                if orig_name in self.models:
                    logger.debug(f"[ModelRegistry.get] Found model via normalized mapping: '{orig_name}' (from '{name}')")
                    return self.models[orig_name]
        
        # 4. 检查是否是占位符
        if normalized_requested_name in self.placeholders:
            logger.warning(f"[ModelRegistry.get] Model '{name}' (normalized: '{normalized_requested_name}') is still a placeholder.")
            return None
        
        # 尝试所有可能性后仍未找到
        logger.warning(f"[ModelRegistry.get] Model not found for name: '{name}' (normalized: '{normalized_requested_name}')")
        return None


class JsonSchemaParser:
    def __init__(self, schemas: Dict):
        self.resolver = ReferenceResolver(schemas)
        self.model_registry = ModelRegistry()
        self.schema_registry: Dict[str, DataModel] = {}
        self.imports: Set[Import] = set()
        self.current_tags: List[str] = list()
        self.max_recursion_depth = 10
        self.current_recursion_path: List[str] = []

    def parse_schema(self, schema_obj: JsonSchemaObject, context: str) -> DataType:

        if len(self.current_recursion_path) >= self.max_recursion_depth:
            data_type = DataType(
                type="Any",
                imports={Import(from_='typing', import_='Any')}
            )
            data_type.normalized_name = "Any"
            return data_type

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

            if schema_obj.is_array:
                return self._parse_array_type(schema_obj, context)

            if schema_obj.properties:
                return self._parse_object_type(schema_obj, context)

            return self._parse_basic_datatype(schema_obj)
        finally:
            self.current_recursion_path.pop()

    def _parse_reference(self, ref: str) -> DataType:
        """解析引用，包括泛型引用"""
        schema_name = ref.split("/")[-1]
        
        # 获取规范化后的名称
        normalized_name = normalize_python_name(schema_name)
        
        # 更新引用解析器中的名称映射 (双向)
        self.resolver.name_mapping[schema_name] = normalized_name
        if normalized_name not in self.resolver.reverse_name_mapping:
            self.resolver.reverse_name_mapping[normalized_name] = set()
        self.resolver.reverse_name_mapping[normalized_name].add(schema_name)
        
        # 获取schema 定义
        schema = self.resolver.get_ref_schema(schema_name)
        
        # 如果获取不到 schema，尝试其他名称变体
        if not schema:
            # 尝试通过规范化名称查找原始名称再获取
            if normalized_name in self.resolver.reverse_name_mapping:
                for orig_name in self.resolver.reverse_name_mapping[normalized_name]:
                    # 避免再次调用 get_ref_schema 导致潜在的无限递归
                    schema = self.resolver.schema_objects.get(orig_name)
                    if schema:
                        schema_name = orig_name # 更新 schema_name 为实际找到的原始名称
                        break # 找到即停止
            
            # 如果仍然找不到，处理引用缺失情况
            if not schema:
                # 返回前向引用，允许后续可能的解析
                data_type = DataType(
                    type=schema_name,  # 使用原始名称作为类型
                    reference=Reference(ref=ref), # 保留原始引用
                    is_custom_type=True,
                    is_forward_ref=True, # 标记为前向引用
                    imports={Import(from_='.models', import_=normalized_name)}
                )
                # 设置规范化名称
                data_type.normalized_name = normalized_name
                return data_type
        
        # 确保引用类型已经注册或添加占位符
        # 使用原始名称检查模型是否存在
        if schema_name not in self.model_registry.models:
            # 添加占位符，使用原始名称
            self.model_registry.add_placeholder(schema_name)
            
            # 递归解析schema，使用原始schema_name作为上下文
            self.parse_schema(schema, schema_name)
        
        # 返回DataType，引用.models中的类型
        # 使用原始名称作为类型名，但设置规范化名称为normalized_name属性
        data_type = DataType(
            type=schema_name,  # 使用原始名称
            reference=Reference(ref=ref),  # 保留原始引用
            is_custom_type=True,
            imports={Import(from_='.models', import_=normalized_name)}  # 导入使用规范化名称
        )
        # 设置规范化名称属性
        data_type.normalized_name = normalized_name
        return data_type

    def _parse_object_type(self, schema_obj: JsonSchemaObject, context: str) -> DataType:
        """深度解析对象类型"""
        # 确保模型名称有效
        model_name = context if context else "DefaultModel"
        # 注意：这里的 model_name 是基于传入的 context，可能是原始名称或规范化名称
        logger.debug(f"[_parse_object_type] Initial context: {context}, Trying model_name: {model_name}")

        # 计算规范化名称用于字段和返回值
        normalized_model_name = normalize_python_name(model_name)
        
        fields = []
        required_fields = schema_obj.required or []
        is_add_optional_import = False
        # 确保 schema_obj.properties 存在且非空
        if schema_obj.properties:
            for prop_name, prop_schema in schema_obj.properties.items():
                # 使用规范化后的父模型名称来构造嵌套上下文
                capitalized_prop_name = prop_name[0].upper() + prop_name[1:] if prop_name else ""
                nested_context = f"{normalized_model_name}{capitalized_prop_name}"
                prop_type = self.parse_schema(prop_schema, nested_context)
                
                if prop_type.is_custom_type and prop_type.type:
                    # 如果有normalized_name属性，确保使用它
                    if hasattr(prop_type, 'normalized_name') and prop_type.normalized_name:
                        prop_type.type = prop_type.normalized_name
                    else:
                        prop_type.type = normalize_python_name(prop_type.type)
                
                if is_python_keyword(prop_name):
                    alias = prop_name
                    prop_name = f"{prop_name}_"
                else:
                    alias = None
                    
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
                    required=prop_name in required_fields,
                    default=prop_schema.default,
                    description=prop_schema.description,
                    alias=alias,
                    **field_constraints
                )
                fields.append(field)
                if not field.required:
                    is_add_optional_import = True
        else:
            # 处理没有 properties 的 object 类型 (例如纯粹的 Dict[str, Any])
            logger.debug(f"[_parse_object_type] Schema for {model_name} has no properties, treating as Dict[str, Any]")
            # 返回一个字典类型
            dict_imports = {Import(from_='typing', import_='Dict'), Import(from_='typing', import_='Any')}
            data_type = DataType(
                type="Dict[str, Any]",
                is_dict=True,
                imports=dict_imports
            )
            # 设置规范化名称
            data_type.normalized_name = "Dict[str, Any]"
            return data_type

        fields.sort(key=lambda field_: not field_.required)
        imports_from_fields = self._collect_imports_from_fields(fields)
        if is_add_optional_import:
            imports_from_fields.add(Import(from_='typing', import_='Optional'))

        # 检查是否是请求体或者通用响应 (使用原始 model_name 判断)
        is_request_body = model_name.endswith("RequestBody")
        is_response = model_name.endswith("Response") or "Response" in model_name
        is_general_model = model_name.startswith("Generic") and ("Response" in model_name or is_response)
        
        # 对于请求体，保持内联而不单独生成模型
        if is_request_body and not is_general_model:
             logger.debug(f"[_parse_object_type] Treating {model_name} as inline RequestBody.")
             data_type = DataType(
                type=model_name,  # 使用原始名称
                is_custom_type=False,
                is_inline=True,
                fields=fields,
                imports=imports_from_fields
             )
             # 设置规范化名称
             data_type.normalized_name = normalized_model_name
             return data_type

        # 创建数据模型，使用原始名称
        data_model = DataModel(
            name=model_name,  # 使用原始名称
            fields=fields,
            description=schema_obj.description,
            tags=self.current_tags,
            imports=imports_from_fields
        )
        
        logger.debug(f"[_parse_object_type] Preparing to register model. Original name: '{data_model.name}'")
        self.model_registry.register(data_model)
        logger.debug(f"[_parse_object_type] Registered model with original name: '{data_model.name}'")

        # 返回 DataType，使用原始名称作为类型，但设置 normalized_name 属性
        data_type = DataType(
            type=model_name,  # 使用原始名称
            is_custom_type=True,
            imports={Import(from_='.models', import_=normalized_model_name)}  # 导入使用规范化名称
        )
        # 设置规范化名称
        data_type.normalized_name = normalized_model_name
        return data_type

    def _parse_basic_datatype(self, schema_obj: JsonSchemaObject) -> DataType:
        base_type, imports = self._get_type_mapping(schema_obj.type, schema_obj.format)

        data_type = DataType(
            type=base_type,
            is_optional=schema_obj.nullable,
            imports=imports
        )
        # 设置规范化名称
        data_type.normalized_name = base_type
        return data_type

    def _get_type_mapping(self, schema_type: str, schema_format: Optional[str] = None) -> Tuple[str, Set[Import]]:
        # 处理schema_type为列表的情况（某些OpenAPI定义可能使用多个类型）
        if isinstance(schema_type, list):
            if 'null' in schema_type:
                # 移除null，设置可选类型
                non_null_types = [t for t in schema_type if t != 'null']
                if len(non_null_types) == 1:
                    # 只有一个非null类型，使用Optional
                    base_type, base_imports = self._get_type_mapping(non_null_types[0], schema_format)
                    optional_imports = base_imports | {Import(from_='typing', import_='Optional')}
                    return f"Optional[{base_type}]", optional_imports
                else:
                    # 多个类型，使用Union
                    types_imports = []
                    for t in non_null_types:
                        base, imps = self._get_type_mapping(t, None)
                        types_imports.append((base, imps))
                    
                    type_names = [t[0] for t in types_imports]
                    union_imports = {Import(from_='typing', import_='Union'), Import(from_='typing', import_='Optional')}
                    for _, imps in types_imports:
                        union_imports.update(imps)
                    
                    return f"Optional[Union[{', '.join(type_names)}]]", union_imports
            else:
                # 没有null，直接使用Union
                types_imports = []
                for t in schema_type:
                    base, imps = self._get_type_mapping(t, None)
                    types_imports.append((base, imps))
                
                type_names = [t[0] for t in types_imports]
                union_imports = {Import(from_='typing', import_='Union')}
                for _, imps in types_imports:
                    union_imports.update(imps)
                
                return f"Union[{', '.join(type_names)}]", union_imports
        
        # 处理单一类型的情况
        if schema_type == 'string':
            # 日期和时间类型
            if schema_format == 'date-time':
                return 'datetime', {Import(from_='datetime', import_='datetime')}
            elif schema_format == 'date':
                return 'date', {Import(from_='datetime', import_='date')}
            elif schema_format == 'time':
                return 'time', {Import(from_='datetime', import_='time')}
            
            # ID和标识符
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
            
            # 其他格式如 hostname, password 等依然映射为 str

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
        
        # 处理items为列表的情况
        if isinstance(item_schema, list):
            # 如果是列表，则创建Union类型
            child_types = []
            child_imports = set()
            
            for i, schema in enumerate(item_schema):
                if isinstance(schema, JsonSchemaObject):
                    child_type = self.parse_schema(schema, f"{context}Item{i}")
                    # 规范化自定义类型名称
                    if child_type.is_custom_type and child_type.type:
                        child_type.type = normalize_python_name(child_type.type)
                    child_types.append(child_type)
                    child_imports.update(child_type.imports)
            
            # 创建Union类型
            if len(child_types) == 1:
                union_hint = child_types[0].type_hint
                union_imports = child_types[0].imports
            else:
                # 确保在type_hint中使用规范化的名称
                union_hint = f"Union[{', '.join(t.type_hint for t in child_types)}]"
                union_imports = child_imports | {Import(from_='typing', import_='Union')}
            
            data_type = DataType(
                type=f"List[{union_hint}]",
                is_list=True,
                data_types=child_types,
                imports=union_imports | {Import(from_='typing', import_='List')}
            )
            # 设置规范化名称
            data_type.normalized_name = f"List[{union_hint}]"
            return data_type
        
        # 处理普通单个item的情况
        item_type = self.parse_schema(item_schema, f"{context}Item")
        
        # 规范化数组元素类型名称
        if item_type.is_custom_type and item_type.type:
            item_type.type = normalize_python_name(item_type.type)

        if item_type.is_list:
            return item_type

        data_type = DataType(
            type=f"List[{item_type.type_hint}]",
            is_list=True,
            data_types=[item_type],
            imports=item_type.imports | {Import(from_='typing', import_='List')}
        )
        # 设置规范化名称
        data_type.normalized_name = f"List[{item_type.type_hint}]"
        return data_type

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
            data_type = DataType(
                type="None",
                imports=set(),
                is_optional=True
            )
            data_type.normalized_name = "None"
            return data_type

        # 检查是否有Any类型
        any_types = [t for t in child_types if t.type_hint == "Any"]
        if any_types:
            # 如果有Any类型，简化为Any或Optional[Any]
            if has_null:
                data_type = DataType(
                    type="Optional[Any]",
                    imports={Import(from_='typing', import_='Any'), Import(from_='typing', import_='Optional')},
                    is_optional=True
                )
                data_type.normalized_name = "Optional[Any]"
                return data_type
            else:
                data_type = DataType(
                    type="Any",
                    imports={Import(from_='typing', import_='Any')},
                    is_optional=False
                )
                data_type.normalized_name = "Any"
                return data_type

        # 如果只有一个非null类型，且有null类型，则使用Optional
        if has_null and len(child_types) == 1:
            type_hint = f"Optional[{child_types[0].type_hint}]"
            data_type = DataType(
                type=type_hint,
                data_types=child_types,
                imports=imports | {Import(from_='typing', import_='Optional')},
                is_optional=True
            )
            data_type.normalized_name = type_hint
            return data_type

        # 如果有多个非null类型，且有null类型，则使用Union加Optional
        if has_null and len(child_types) > 1:
            type_hint = f"Optional[Union[{', '.join(t.type_hint for t in child_types)}]]"
            data_type = DataType(
                type=type_hint,
                data_types=child_types,
                imports=imports | {Import(from_='typing', import_='Optional'), Import(from_='typing', import_='Union')},
                is_optional=True
            )
            data_type.normalized_name = type_hint
            return data_type

        # 如果没有null类型
        type_hint = f"{union_type}[{', '.join(t.type_hint for t in child_types)}]"
        data_type = DataType(
            type=type_hint,
            data_types=child_types,
            imports=imports | {Import(from_='typing', import_=union_type)},
            is_optional=False
        )
        data_type.normalized_name = type_hint
        return data_type

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

        # 生成模型名称和规范化名称
        original_name = f"{context}Combined"
        normalized_name = normalize_python_name(original_name)

        merged_model = DataModel(
            name=original_name,  # 使用原始名称
            fields=self._merge_fields(merged_fields),
            required=merged_required,
            imports=merged_imports,
            tags=self.current_tags,
            description="\n".join(merged_descriptions)
        )

        self.model_registry.register(merged_model)

        # 返回 DataType，使用原始名称作为类型，但设置 normalized_name 属性
        data_type = DataType(
            type=original_name,  # 使用原始名称
            is_custom_type=True,
            reference=Reference(ref=original_name),
            imports={Import(from_='.models', import_=normalized_name)}  # 导入使用规范化名称
        )
        # 设置规范化名称
        data_type.normalized_name = normalized_name
        return data_type

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
            data_type = DataType(
                type=type_hint,
                imports=imports,
                is_optional=schema_obj.nullable
            )
            data_type.normalized_name = type_hint
            return data_type
        else:
            # 对于复杂类型（如对象、数组等），回退到基本类型
            # 注意：严格来说，这不符合 const 的语义，但这里是一个合理的妥协
            data_type = DataType(
                type=base_type,
                imports=imports,
                is_optional=schema_obj.nullable
            )
            data_type.normalized_name = base_type
            return data_type

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
            
        # 保存原始名称
        original_name = context
        # 生成规范化名称
        normalized_name = normalize_python_name(original_name)
        
        enum_model = DataModel(
            name=original_name,  # 使用原始名称
            is_enum=True,
            tags=self.current_tags,
            imports={Import(from_="enum", import_="Enum")},
            fields=fields
        )

        self.model_registry.register(enum_model)

        # 返回 DataType，使用原始名称作为类型，但设置 normalized_name 属性
        data_type = DataType(
            type=original_name,  # 使用原始名称
            imports={Import(from_='.models', import_=normalized_name)},  # 导入使用规范化名称
            is_custom_type=True
        )
        # 设置规范化名称
        data_type.normalized_name = normalized_name
        return data_type

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
    return field_name in keyword.kwlist

