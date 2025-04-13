import pytest
from typing import Set, Dict, Any
from aomaker.maker.jsonschema import (
    normalize_class_name,
    normalize_enum_name,
    is_python_keyword,
    JsonSchemaParser,
    JsonSchemaObject,
    # ReferenceResolver, # 通过 Parser 间接测试
    # ModelRegistry,     # 通过 Parser 间接测试
    DataType,
    DataModel,
    Import,
)
from aomaker.maker.models import DataModelField, Reference # 确保导入

# --- Tests for Helper Functions ---

@pytest.mark.parametrize(
    "input_name, expected_name",
    [
        ("SimpleName", "SimpleName"),
        ("simple_name", "SimpleName"),
        ("name with spaces", "NameWithSpaces"),
        ("1Name", "_1Name"),
        ("MyClass«T»", "MyClassOfT"),
        ("MyClass«List«String»»", "MyClassOfListOfString"),
        ("你好世界", "你好世界"),
        ("_private_name", "PrivateName"),
        ("alreadyCamelCase", "AlreadyCamelCase"),
        ("__dunder__", "Dunder"),
        ("a-b-c", "ABC"),
        ("a_b_c", "ABC"),
        ("very_long_name_with_many_parts", "VeryLongNameWithManyParts"),
        ("", "UnnamedModel"),
        ("_", "UnnamedModel"),
        ("__", "UnnamedModel"),
        ("Name_With_中文", "NameWith中文"),
        ("Class_With_Number1", "ClassWithNumber1"),
        ("Trailing_", "Trailing"),
        ("_Leading", "Leading"),
        ("Multiple___Underscores", "MultipleUnderscores"),
        ("a%2Fb", "A2Fb"),
        ("a.b", "AB"),
        ("___", "UnnamedModel"),
        ("1", "_1"),
        ("%", "UnnamedModel"),
    ],
)
def test_normalize_class_name(input_name, expected_name):
    """测试类名规范化函数"""
    assert normalize_class_name(input_name) == expected_name

@pytest.mark.parametrize(
    "input_value, expected_name",
    [
        ("active", "active"),
        ("INACTIVE", "inactive"), # 转小写
        ("pending-approval", "pending_approval"), # 连字符转下划线
        ("123_value", "value_123_value"), # 数字开头加前缀
        ("_", "value__"), # 单下划线处理
        ("特殊 值", "特殊_值"), # 含空格和中文
        ("valid", "valid"),
        (123, "value_123"), # 整数输入
        (True, "true"), # 布尔输入
        (None, "none"), # None 输入
        ("", "value_empty"), # 空字符串处理
        (" ", "value__"), # 单个空格处理
        ("a b c", "a_b_c"), # 多个空格
        ("keyword_if", "keyword_if"), # 不检查关键字
    ]
)
def test_normalize_enum_name(input_value, expected_name):
    """测试枚举成员名称规范化函数"""
    assert normalize_enum_name(input_value) == expected_name

@pytest.mark.parametrize(
    "name, expected",
    [
        ("class", True),
        ("def", True),
        ("if", True),
        ("None", True),
        ("True", True),
        ("my_variable", False),
        ("MyClass", False),
        ("_internal", False),
        ("__dunder__", False), # Dunder 不是关键字
        ("async", True),
        ("await", True),
    ]
)
def test_is_python_keyword(name, expected):
    """测试 Python 关键字检查函数"""
    assert is_python_keyword(name) == expected


# --- Fixtures ---

@pytest.fixture
def parser() -> JsonSchemaParser:
    """提供一个空的 JsonSchemaParser 实例"""
    return JsonSchemaParser(schemas={})

@pytest.fixture
def parser_with_schemas() -> JsonSchemaParser:
    """提供一个带有预定义 schema 的 JsonSchemaParser 实例"""
    schemas = {
        "SimpleObject": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "required": ["id"],
        },
        "ObjectWithDate": {
            "type": "object",
            "properties": {
                "creation_date": {"type": "string", "format": "date-time"}
            }
        },
        "ObjectWithArray": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/SimpleObject"}
                }
            }
        },
        "StringEnum": {
            "type": "string",
            "enum": ["active", "inactive", "pending-approval"]
        },
         "IntEnum": {
            "type": "integer",
            "enum": [1, 2, 3]
        },
        "NullableString": {
            "type": ["string", "null"] # OpenAPI 3.1 nullable style
        },
         "ComponentWithKeyword": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "def": {"type": "string"} # 关键字属性
            }
        }
    }
    # 实例化解析器时，预处理 schema
    return JsonSchemaParser(schemas=schemas)


# --- Tests for Basic Type Parsing (via parse_schema) ---

def test_parse_schema_string(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string")
    data_type = parser.parse_schema(schema, "MyStringField")
    assert data_type.type == "str"
    assert data_type.imports == set()
    assert not data_type.is_optional

def test_parse_schema_string_datetime(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string", format="date-time")
    data_type = parser.parse_schema(schema, "MyDateTimeField")
    assert data_type.type == "datetime"
    assert data_type.imports == {Import(from_='datetime', import_='datetime')}

def test_parse_schema_string_date(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string", format="date")
    data_type = parser.parse_schema(schema, "MyDateField")
    assert data_type.type == "date"
    assert data_type.imports == {Import(from_='datetime', import_='date')}

def test_parse_schema_string_uuid(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string", format="uuid")
    data_type = parser.parse_schema(schema, "MyUuidField")
    assert data_type.type == "UUID"
    assert data_type.imports == {Import(from_='uuid', import_='UUID')}

def test_parse_schema_string_byte(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string", format="byte")
    data_type = parser.parse_schema(schema, "MyByteField")
    assert data_type.type == "bytes"
    assert data_type.imports == set()

def test_parse_schema_string_binary(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="string", format="binary")
    data_type = parser.parse_schema(schema, "MyBinaryField")
    assert data_type.type == "bytes"
    assert data_type.imports == set()

def test_parse_schema_integer(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="integer")
    data_type = parser.parse_schema(schema, "MyIntField")
    assert data_type.type == "int"
    assert data_type.imports == set()

def test_parse_schema_number(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="number")
    data_type = parser.parse_schema(schema, "MyFloatField")
    assert data_type.type == "float"
    assert data_type.imports == set()

def test_parse_schema_boolean(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type="boolean")
    data_type = parser.parse_schema(schema, "MyBoolField")
    assert data_type.type == "bool"
    assert data_type.imports == set()

def test_parse_schema_nullable_string_oas30(parser: JsonSchemaParser):
    # OpenAPI 3.0 style nullable
    schema = JsonSchemaObject(type="string", nullable=True)
    data_type = parser.parse_schema(schema, "MyNullableStringField")
    assert data_type.type == "str" # 基础类型是 str
    assert data_type.imports == set()
    assert data_type.is_optional # is_optional 标志为 True

def test_parse_schema_nullable_string_oas31(parser: JsonSchemaParser):
    # OpenAPI 3.1 style nullable
    schema = JsonSchemaObject(type=["string", "null"])
    data_type = parser.parse_schema(schema, "MyNullableStringField31")
    # _get_type_mapping 直接处理这种情况
    assert data_type.type_hint == "Optional[str]"
    assert data_type.type == "Optional[str]"
    assert data_type.imports == {Import(from_='typing', import_='Optional')}
    # type hint 已包含 Optional，所以 is_optional 标志为 False
    assert not data_type.is_optional

def test_parse_schema_nullable_integer_oas31(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type=["integer", "null"])
    data_type = parser.parse_schema(schema, "MyNullableIntField31")
    assert data_type.type_hint == "Optional[int]"
    assert data_type.type == "Optional[int]"
    assert data_type.imports == {Import(from_='typing', import_='Optional')}
    assert not data_type.is_optional

def test_parse_schema_only_null_oas31(parser: JsonSchemaParser):
    schema = JsonSchemaObject(type=["null"])
    data_type = parser.parse_schema(schema, "MyNullField31")
    assert data_type.type == "None"
    assert data_type.imports == set()
    assert not data_type.is_optional


# --- Tests for JsonSchemaParser Object Parsing ---

def test_parse_simple_object(parser: JsonSchemaParser):
    """测试解析简单的 object schema"""
    schema_dict = {
        "type": "object",
        "properties": {
            "id": {"type": "integer", "description": "The unique ID"},
            "name": {"type": "string", "default": "DefaultName"},
            "optional_val": {"type": "boolean"}
        },
        "required": ["id", "name"],
        "description": "A simple object model",
    }
    schema = JsonSchemaObject.model_validate(schema_dict)
    # 指定一个上下文名称，这将成为生成的模型名称
    model_name = "SimpleModel"
    data_type = parser.parse_schema(schema, model_name)

    # 检查返回的 DataType
    assert data_type.type == model_name
    assert data_type.is_custom_type # 这是一个自定义模型类型
    assert not data_type.is_inline # 不是内联定义的
    assert data_type.imports == {Import(from_=".models", import_=model_name)} # 应该从 .models 导入

    # 检查模型注册表中的模型
    model = parser.model_registry.get(model_name)
    assert isinstance(model, DataModel)
    assert model.name == model_name
    assert model.description == "A simple object model"
    assert len(model.fields) == 3
    # 因为 optional_val 不是必需的，所以需要 Optional
    assert model.imports == {Import(from_="typing", import_="Optional")}

    # 检查字段
    id_field = next(f for f in model.fields if f.name == "id")
    name_field = next(f for f in model.fields if f.name == "name")
    optional_field = next(f for f in model.fields if f.name == "optional_val")

    assert id_field.data_type.type == "int"
    assert id_field.required
    assert id_field.description == "The unique ID"
    assert id_field.default is None

    assert name_field.data_type.type == "str"
    assert name_field.required
    assert name_field.default == "DefaultName" # 检查默认值

    assert optional_field.data_type.type == "bool"
    assert not optional_field.required # 检查非必需字段
    assert optional_field.default is None

    # 检查字段顺序 (按 required=True, required=False 排序)
    assert model.fields[0].name == "id"
    assert model.fields[1].name == "name"
    assert model.fields[2].name == "optional_val"


def test_parse_object_with_keyword_property(parser_with_schemas: JsonSchemaParser):
    """测试 object 包含 Python 关键字作为属性名"""
    # 使用 fixture 中定义的 ComponentWithKeyword
    ref = "#/components/schemas/ComponentWithKeyword"
    schema = JsonSchemaObject.model_validate({'$ref': ref})
    data_type = parser_with_schemas.parse_schema(schema, "KeywordUsage")

    assert data_type.type == "ComponentWithKeyword" # 模型名来自 schema key
    model = parser_with_schemas.model_registry.get("ComponentWithKeyword")
    assert model is not None
    assert len(model.fields) == 2

    def_field = next(f for f in model.fields if f.alias == "def")
    assert def_field.name == "def_" # 名称被修改
    assert def_field.alias == "def" # alias 保存原始名称
    assert not def_field.required # 'def' is not in required list in fixture
    assert def_field.data_type.type == "str"

    id_field = next(f for f in model.fields if f.name == "id")
    assert id_field.name == "id"
    assert id_field.alias is None
    assert not id_field.required

def test_parse_inline_object(parser: JsonSchemaParser):
    """测试解析内联 object (例如非 $ref 的 requestBody)"""
    schema_dict = {
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"]
    }
    schema = JsonSchemaObject.model_validate(schema_dict)
    # 使用暗示其用途的上下文名称
    context_name = "MyOperation_RequestBody"
    data_type = parser.parse_schema(schema, context_name)

    assert data_type.type == context_name
    assert not data_type.is_custom_type # 不应注册为独立模型
    assert data_type.is_inline       # 应标记为内联
    assert data_type.fields is not None # 应该有字段列表
    assert len(data_type.fields) == 1
    field = data_type.fields[0]
    assert field.name == "param"
    assert field.data_type.type == "str"
    assert field.required
    assert data_type.imports == {Import(from_="typing", import_="Optional")} # 根据当前代码行为断言

# --- Tests for JsonSchemaParser Array Parsing ---

def test_parse_array_of_strings(parser: JsonSchemaParser):
    """测试解析字符串数组"""
    schema = JsonSchemaObject(type="array", items=JsonSchemaObject(type="string"))
    data_type = parser.parse_schema(schema, "StringList")

    assert data_type.type_hint == "List[str]" # 检查生成的类型提示
    assert data_type.type == "List[str]"
    assert data_type.is_list
    assert len(data_type.data_types) == 1
    assert data_type.data_types[0].type == "str"
    assert data_type.imports == {Import(from_='typing', import_='List')}

def test_parse_array_of_objects(parser_with_schemas: JsonSchemaParser):
    """测试解析对象数组 (items 是 $ref)"""
    # 使用 fixture 中的 ObjectWithArray schema
    schema = parser_with_schemas.resolver.get_ref_schema("ObjectWithArray")
    assert schema is not None
    assert schema.properties is not None
    array_prop_schema = schema.properties.get("items")
    assert array_prop_schema is not None

    # Ensure SimpleObject schema is parsed first, if needed for dependency
    parser_with_schemas.parse_schema(
        JsonSchemaObject.model_validate({'$ref': "#/components/schemas/SimpleObject"}), "EnsureSimpleObject"
    )

    data_type = parser_with_schemas.parse_schema(array_prop_schema, "ListOfSimpleObjects")

    assert data_type.type_hint == "List[SimpleObject]"
    assert data_type.type == "List[SimpleObject]"
    assert data_type.is_list
    assert len(data_type.data_types) == 1
    item_type = data_type.data_types[0]
    assert item_type.type == "SimpleObject"
    assert item_type.is_custom_type
    # 导入应包括 List 和 数组项的模型
    assert data_type.imports == {
        Import(from_='typing', import_='List'),
        Import(from_='.models', import_='SimpleObject')
    }

# --- Tests for JsonSchemaParser Reference Parsing ---

def test_parse_reference(parser_with_schemas: JsonSchemaParser):
    """测试解析简单的 $ref"""
    ref = "#/components/schemas/SimpleObject"
    # Use model_validate with alias
    schema = JsonSchemaObject.model_validate({'$ref': ref})

    data_type = parser_with_schemas.parse_schema(schema, "RefTest")

    # DataType 应该指向引用的模型
    assert data_type.type == "SimpleObject"
    assert data_type.is_custom_type
    assert not data_type.is_forward_ref # 非循环引用
    assert data_type.imports == {Import(from_='.models', import_='SimpleObject')}
    assert data_type.reference is not None and data_type.reference.ref == ref

    # 验证模型已在注册表中
    model = parser_with_schemas.model_registry.get("SimpleObject")
    assert model is not None
    assert model.name == "SimpleObject"

def test_parse_reference_url_encoded(parser_with_schemas: JsonSchemaParser):
    """测试解析含 URL 编码字符的 $ref"""
    # 添加一个带编码名称的 schema 到解析器的 schemas
    encoded_name = "Complex%2FObject%2BName" # 原始 $ref 中的名称
    decoded_name = "Complex/Object+Name"    # URL 解码后的名称
    # 规范化处理 `/` 和 `+`
    normalized_name = "ComplexObjectName"
    parser_with_schemas.resolver.schemas[decoded_name] = { # schema 按解码后的名称存储
        "type": "object",
        "properties": {"value": {"type": "string"}}
    }
    # 需要重新预处理 schema 对象
    parser_with_schemas.resolver.schema_objects = parser_with_schemas.resolver._preprocess_schemas()

    ref = f"#/components/schemas/{encoded_name}"
    # Use model_validate with alias
    schema = JsonSchemaObject.model_validate({'$ref': ref})

    data_type = parser_with_schemas.parse_schema(schema, "EncodedRefTest")

    # DataType 和导入应使用规范化后的名称
    assert data_type.type == normalized_name
    assert data_type.is_custom_type
    assert data_type.imports == {Import(from_='.models', import_=normalized_name)}
    assert data_type.reference is not None and data_type.reference.ref == ref

    # 验证模型使用规范化名称注册
    model = parser_with_schemas.model_registry.get(normalized_name)
    assert model is not None
    assert model.name == normalized_name
    assert len(model.fields) == 1
    assert model.fields[0].name == "value"


def test_parse_forward_reference(parser: JsonSchemaParser):
    """测试解析循环引用（前向引用）"""
    # 定义相互引用的 schema
    schemas = {
        "NodeA": {
            "type": "object",
            "properties": {"next": {"$ref": "#/components/schemas/NodeB"}}
        },
        "NodeB": {
            "type": "object",
            "properties": {"prev": {"$ref": "#/components/schemas/NodeA"}}
        }
    }
    parser = JsonSchemaParser(schemas)

    # 开始解析 NodeA
    # Use model_validate with alias
    data_type_a = parser.parse_schema(JsonSchemaObject.model_validate({'$ref': "#/components/schemas/NodeA"}), "StartNodeA")

    # 初始调用返回正常的 DataType
    assert data_type_a.type == "NodeA"
    assert data_type_a.is_custom_type
    assert not data_type_a.is_forward_ref

    # 检查注册的 NodeA 模型
    model_a = parser.model_registry.get("NodeA")
    assert model_a is not None
    assert len(model_a.fields) == 1
    field_a_next = model_a.fields[0]
    assert field_a_next.name == "next"
    # 'next' 字段的类型应指向 NodeB (在解析 NodeA 时 NodeB 会被解析)
    assert field_a_next.data_type.type == "NodeB"
    assert field_a_next.data_type.is_custom_type
    assert not field_a_next.data_type.is_forward_ref # NodeB 解析时还没遇到循环

    # 检查注册的 NodeB 模型
    model_b = parser.model_registry.get("NodeB")
    assert model_b is not None
    assert len(model_b.fields) == 1
    field_b_prev = model_b.fields[0]
    assert field_b_prev.name == "prev"
    # 'prev' 字段的类型应指向 NodeA，并且是前向引用
    assert field_b_prev.data_type.type == "NodeA"
    assert field_b_prev.data_type.is_custom_type
    assert field_b_prev.data_type.is_forward_ref # 检测到循环

# --- Tests for JsonSchemaParser Enum Parsing ---

def test_parse_enum(parser_with_schemas: JsonSchemaParser):
    """测试解析 enum schema"""
    ref = "#/components/schemas/StringEnum"
    # Use model_validate with alias
    schema = JsonSchemaObject.model_validate({'$ref': ref})
    # 解析引用以触发 enum 模型的生成
    data_type = parser_with_schemas.parse_schema(schema, "MyStringEnumUsage")

    assert data_type.type == "StringEnum" # 模型名来自 schema key
    assert data_type.is_custom_type
    assert data_type.imports == {Import(from_=".models", import_="StringEnum")}

    # 验证生成的 Enum 模型
    model = parser_with_schemas.model_registry.get("StringEnum")
    assert model is not None
    assert model.is_enum
    assert model.imports == {Import(from_="enum", import_="Enum")} # 导入 Python Enum
    assert len(model.fields) == 3 # 三个枚举成员

    # 检查枚举成员字段
    field_active = next(f for f in model.fields if f.name == "active")
    field_inactive = next(f for f in model.fields if f.name == "inactive")
    field_pending = next(f for f in model.fields if f.name == "pending_approval") # 名称规范化

    assert field_active.default == "'active'" # 默认值是值的 repr
    assert field_active.data_type.type == "str" # 基础类型正确推断
    assert field_inactive.default == "'inactive'"
    # 检查名称规范化和原始值
    assert field_pending.name == "pending_approval"
    assert field_pending.default == "'pending-approval'" # default 使用原始值

# --- Tests for JsonSchemaParser Union/Const Parsing ---

def test_parse_anyof_basic(parser: JsonSchemaParser):
    """测试解析基本的 anyOf (Union)"""
    schema = JsonSchemaObject(anyOf=[
        JsonSchemaObject(type="string"),
        JsonSchemaObject(type="integer")
    ])
    data_type = parser.parse_schema(schema, "StringOrInt")

    assert data_type.type_hint == "Union[str, int]"
    assert data_type.imports == {Import(from_='typing', import_='Union')}
    assert not data_type.is_optional
    assert len(data_type.data_types) == 2
    assert data_type.data_types[0].type == "str"
    assert data_type.data_types[1].type == "int"

def test_parse_anyof_with_null(parser: JsonSchemaParser):
    """测试解析 anyOf 包含 null (Optional)"""
    schema = JsonSchemaObject(anyOf=[
        JsonSchemaObject(type="string"),
        JsonSchemaObject(type="null") # OpenAPI 3.1 style null
    ])
    data_type = parser.parse_schema(schema, "OptionalString")

    # 应简化为 Optional[str]
    assert data_type.type_hint == "Optional[str]"
    assert data_type.imports == {Import(from_='typing', import_='Optional')}
    assert data_type.is_optional # is_optional 标志为 True
    assert len(data_type.data_types) == 1 # 只包含非 null 类型
    assert data_type.data_types[0].type == "str"

def test_parse_anyof_multiple_with_null(parser: JsonSchemaParser):
    """测试解析 anyOf 包含多个类型和 null"""
    schema = JsonSchemaObject(anyOf=[
        JsonSchemaObject(type="string"),
        JsonSchemaObject(type="integer"),
        JsonSchemaObject(type="null")
    ])
    data_type = parser.parse_schema(schema, "StringOrIntOrNull")

    # 应生成 Optional[Union[...]]
    assert data_type.type_hint == "Optional[Union[str, int]]"
    assert data_type.imports == {
        Import(from_='typing', import_='Optional'),
        Import(from_='typing', import_='Union')
    }
    assert data_type.is_optional # 标记为 Optional
    assert len(data_type.data_types) == 2 # 包含两个非 null 类型
    assert data_type.data_types[0].type == "str"
    assert data_type.data_types[1].type == "int"

def test_parse_oneof_literal(parser: JsonSchemaParser):
    """测试解析 oneOf 包含单值 enum (是否生成 Literal?)"""
    schema = JsonSchemaObject(oneOf=[
        # 每个项都是只含一个值的 enum
        JsonSchemaObject(type="string", enum=["apple"]),
        JsonSchemaObject(type="string", enum=["banana"])
    ])
    # 检查 _should_be_literal 是否按预期工作
    assert parser._should_be_literal(schema.oneOf)

    data_type = parser.parse_schema(schema, "FruitLiteral")

    expected_union_str = "Literal[FruitLiteral_Literal0, FruitLiteral_Literal1]"
    assert data_type.type_hint == expected_union_str
    assert data_type.type == expected_union_str # type 和 type_hint 一致
    assert data_type.imports == {
        Import(from_='typing', import_='Literal'),
        Import(from_='.models', import_='FruitLiteral_Literal0'),
        Import(from_='.models', import_='FruitLiteral_Literal1')
    }
    assert not data_type.is_optional

    # 验证生成的 Enum 模型
    enum0 = parser.model_registry.get("FruitLiteral_Literal0")
    enum1 = parser.model_registry.get("FruitLiteral_Literal1")
    assert enum0 is not None and enum0.is_enum and len(enum0.fields) == 1 and enum0.fields[0].name == "apple"
    assert enum1 is not None and enum1.is_enum and len(enum1.fields) == 1 and enum1.fields[0].name == "banana"

def test_parse_const_string(parser: JsonSchemaParser):
    """测试解析 string 类型的 const"""
    schema = JsonSchemaObject(type="string", const="fixed_value")
    data_type = parser.parse_schema(schema, "ConstString")

    # 预期生成 Literal 类型
    assert data_type.type_hint == "Literal['fixed_value']"
    assert data_type.type == "Literal['fixed_value']"
    assert data_type.imports == {Import(from_='typing', import_='Literal')}
    assert not data_type.is_optional

def test_parse_const_integer(parser: JsonSchemaParser):
    """测试解析 integer 类型的 const"""
    schema = JsonSchemaObject(type="integer", const=123)
    data_type = parser.parse_schema(schema, "ConstInt")

    assert data_type.type_hint == "Literal[123]"
    assert data_type.type == "Literal[123]"
    assert data_type.imports == {Import(from_='typing', import_='Literal')}

# --- Tests for JsonSchemaParser AllOf Parsing ---

def test_parse_all_of(parser: JsonSchemaParser):
    """测试解析 allOf，合并属性和 required"""
    # 定义基础和扩展 schema
    schemas = {
        "Base": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "common": {"type": "string", "default": "base_val"}
            },
            "required": ["id", "common"], # common 在 base 中是 required
            "description": "Base schema"
        },
        "Extended": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "common": {"type": "string", "default": "ext_val"} # 覆盖 base 的 common，非 required
            },
            "required": ["name"],
            "description": "Extended schema"
        }
    }
    parser = JsonSchemaParser(schemas)

    # 定义 allOf schema
    all_of_schema = JsonSchemaObject(allOf=[
        # Use model_validate with alias for items in allOf
        JsonSchemaObject.model_validate({'$ref': "#/components/schemas/Base"}),
        JsonSchemaObject.model_validate({'$ref': "#/components/schemas/Extended"})
    ])

    # 指定上下文名称，预期合并后的模型名为 ContextCombined
    context_name = "CombinedModel"
    expected_model_name = f"{context_name}Combined"

    data_type = parser.parse_schema(all_of_schema, context_name)

    # 检查返回的 DataType
    assert data_type.type == expected_model_name
    assert data_type.is_custom_type
    assert data_type.imports == {Import(from_=".models", import_=expected_model_name)}

    # 检查合并后的模型
    model = parser.model_registry.get(expected_model_name)
    assert model is not None
    assert model.name == expected_model_name
    # 描述合并（简单拼接）
    assert model.description == "Base schema\nExtended schema"

    # 检查字段合并结果
    assert len(model.fields) == 3 # id, common, name

    id_field = next(f for f in model.fields if f.name == "id")
    common_field = next(f for f in model.fields if f.name == "common")
    name_field = next(f for f in model.fields if f.name == "name")

    # 检查 id 字段 (来自 Base)
    assert id_field.data_type.type == "int"
    assert id_field.required # 因为 Base 中 required

    # 检查 common 字段 (来自 Extended，覆盖 Base)
    assert common_field.data_type.type == "str"
    assert common_field.default == "ext_val" # default 值被覆盖
    # required 状态：字段合并时，后出现的字段（Extended）覆盖先前的。Extended 中 common 非 required。
    assert not common_field.required

    # 检查 name 字段 (来自 Extended)
    assert name_field.data_type.type == "str"
    assert name_field.required # 因为 Extended 中 required

    assert set(f.name for f in model.fields if f.required) == {"id", "name"}

    # 检查 imports
    # 因为 common 字段最终不是 required，所以需要 Optional
    assert model.imports == {Import(from_='typing', import_='Optional')}


# --- Tests for JsonSchemaParser Advanced Features ---

def test_parse_recursion_depth(parser: JsonSchemaParser):
    """测试解析超过最大递归深度时返回 Any"""
    # 定义自引用 schema
    schemas = {
        "RecursiveNode": {
            "type": "object",
            "properties": {
                # 注意：为了更容易触发深度限制，让 child 也是一个可能递归的类型
                 "child": {"$ref": "#/components/schemas/RecursiveNode"}
                #"child": { "type": "object", "properties": { "grandchild": {"$ref": "#/components/schemas/RecursiveNode"}}}
            }
        }
    }
    parser = JsonSchemaParser(schemas)
    parser.max_recursion_depth = 3 # 设置一个低的限制用于测试

    # 解析 schema
    # Use model_validate with alias
    ref_schema = JsonSchemaObject.model_validate({'$ref': "#/components/schemas/RecursiveNode"})
    data_type = parser.parse_schema(ref_schema, "StartRecursion")

    # 顶层模型应正常解析
    assert data_type.type == "RecursiveNode"
    model = parser.model_registry.get("RecursiveNode")
    assert model is not None

    assert len(model.fields) == 1
    child_field = model.fields[0]
    assert child_field.name == "child"
    assert child_field.data_type.type == "Any"
    assert child_field.data_type.imports == {Import(from_='typing', import_='Any')}


def test_tag_propagation(parser: JsonSchemaParser):
    """测试解析时标签 (tags) 是否正确传递给嵌套模型"""
    schemas = {
        "NestedObject": {
            "type": "object",
            "properties": {"value": {"type": "string"}}
        },
        "ParentObject": {
            "type": "object",
            "properties": {
                "child": {"$ref": "#/components/schemas/NestedObject"}
            }
        }
    }
    parser = JsonSchemaParser(schemas)
    parser.current_tags = ["Tag1", "Tag2"] # 设置当前解析的标签

    # 解析父对象，这会触发嵌套对象的解析
    # Use model_validate with alias
    parent_ref = JsonSchemaObject.model_validate({'$ref': "#/components/schemas/ParentObject"})
    parser.parse_schema(parent_ref, "ParseParent")

    # 检查父对象的标签
    parent_model = parser.model_registry.get("ParentObject")
    assert parent_model is not None
    assert set(parent_model.tags) == {"Tag1", "Tag2"}

    # 检查嵌套对象的标签（在解析父对象时被解析）
    nested_model = parser.model_registry.get("NestedObject")
    assert nested_model is not None
    assert set(nested_model.tags) == {"Tag1", "Tag2"} # 应继承解析时的标签

    # 再次解析嵌套对象，但使用不同的标签
    parser.current_tags = ["Tag3"]
    # Use model_validate with alias
    nested_ref = JsonSchemaObject.model_validate({'$ref': "#/components/schemas/NestedObject"})
    parser.parse_schema(nested_ref, "ParseNestedAgain")

    # 检查嵌套对象的标签是否已更新（追加）
    nested_model = parser.model_registry.get("NestedObject")
    assert nested_model is not None
    assert set(nested_model.tags) == {"Tag1", "Tag2", "Tag3"} # 标签是追加的

# --- Tests for Constraints ---

@pytest.mark.parametrize(
    "constraint_key, constraint_value, expected_field_attr",
    [
        ("minLength", 5, {"min_length": 5}),
        ("maxLength", 10, {"max_length": 10}),
        ("pattern", "^[a-z]+$", {"pattern": "^[a-z]+$"}),
        ("minimum", 0, {"minimum": 0}),
        ("maximum", 100.5, {"maximum": 100.5}),
        # JSON Schema spec uses number for exclusiveMin/Max, OpenAPI 3.0 used boolean.
        # The model `JsonSchemaObject` uses Optional[float]. Assume float here.
        ("exclusiveMinimum", 0.1, {"exclusive_minimum": 0.1}),
        ("exclusiveMaximum", 99.9, {"exclusive_maximum": 99.9}),
        ("multipleOf", 5, {"multiple_of": 5}),
    ]
)
def test_parse_object_property_constraints(parser: JsonSchemaParser, constraint_key, constraint_value, expected_field_attr):
    """测试对象属性上的各种约束条件"""
    prop_schema: Dict[str, Any] = {"type": "string"} # Default type
    if constraint_key in ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"]:
        prop_schema["type"] = "number"

    # Add the constraint to the property schema
    prop_schema[constraint_key] = constraint_value

    # Create the object schema
    schema_dict = {
        "type": "object",
        "properties": {
            "constrained_prop": prop_schema
        }
    }
    schema = JsonSchemaObject.model_validate(schema_dict)
    data_type = parser.parse_schema(schema, "ConstrainedModel")

    # Verify the generated model's field
    model = parser.model_registry.get("ConstrainedModel")
    assert model is not None
    field = next(f for f in model.fields if f.name == "constrained_prop")

    # Check if the constraint attribute exists on the DataModelField and has the correct value
    attr_name = list(expected_field_attr.keys())[0]
    expected_value = list(expected_field_attr.values())[0]
    assert hasattr(field, attr_name), f"Field should have attribute {attr_name}"
    assert getattr(field, attr_name) == expected_value, f"Attribute {attr_name} has wrong value"

@pytest.mark.parametrize(
    "constraint_key, constraint_value, expected_field_attr",
    [
        ("minItems", 1, {"min_items": 1}),
        ("maxItems", 10, {"max_items": 10}),
        ("uniqueItems", True, {"unique_items": True}),
    ]
)
def test_parse_array_constraints(parser: JsonSchemaParser, constraint_key, constraint_value, expected_field_attr):
    """测试数组属性上的约束条件"""
    # Define the array schema with the constraint
    array_schema: Dict[str, Any] = {
        "type": "array",
        "items": {"type": "string"}
    }
    array_schema[constraint_key] = constraint_value

    # Define an object schema containing this array property
    schema_dict = {
        "type": "object",
        "properties": {
            "constrained_array": array_schema
        }
    }
    schema = JsonSchemaObject.model_validate(schema_dict)
    data_type = parser.parse_schema(schema, "ArrayConstraintModel")

    # Verify the generated model's field
    model = parser.model_registry.get("ArrayConstraintModel")
    assert model is not None
    field = next(f for f in model.fields if f.name == "constrained_array")

    # Check if the constraint attribute exists on the DataModelField for the array
    attr_name = list(expected_field_attr.keys())[0]
    expected_value = list(expected_field_attr.values())[0]
    assert hasattr(field, attr_name), f"Field should have attribute {attr_name}"
    assert getattr(field, attr_name) == expected_value, f"Attribute {attr_name} has wrong value"
    # Also check the field's data type is correct (List)
    assert field.data_type.is_list
    assert field.data_type.type_hint == "List[str]"


if __name__ == "__main__":
    pytest.main(["-v", "-s", "-k", "test_parse_object_with_keyword_property"])
