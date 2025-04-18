import pytest
from copy import deepcopy

from aomaker.maker.compat import SwaggerAdapter, RefFixer, validate_openapi3


# -----------------------------
# 1. 测试 is_swagger
# -----------------------------

def test_is_swagger_true():
    """当 swagger 字段以 '2' 开头时，应返回 True"""
    doc = {"swagger": "2.0"}
    assert SwaggerAdapter.is_swagger(doc) is True


@pytest.mark.parametrize("doc", [
    ({}),  # 缺少 swagger
    ({"swagger": "3.0.0"}),  # 不是 2.x
    ({"swagger": "1.1"})  # 不是 2.x
])
def test_is_swagger_false(doc):
    """无 swagger 字段或非 2.x 开头，都应返回 False"""
    assert SwaggerAdapter.is_swagger(doc) is False


# -----------------------------
# 2. 测试 fix_ref 辅助方法
# -----------------------------

@pytest.mark.parametrize("inp, expected", [
    ("#/definitions/Pet", "#/components/schemas/Pet"),
    ("#/parameters/LimitParam", "#/components/parameters/LimitParam"),
    ("#/responses/ErrorResp", "#/components/responses/ErrorResp"),
    ("#/securityDefinitions/ApiKeyAuth", "#/components/securitySchemes/ApiKeyAuth"),
    ("#/noMapping/X", "#/noMapping/X"),  # 无映射前缀，保持原样
])
def test_fix_ref_mapping(inp, expected):
    """各种映射前缀应被正确替换，不相关的保持原样"""
    assert SwaggerAdapter.fix_ref(inp) == expected


def test_fix_ref_invalid_input():
    """非字符串类型的 ref，应返回 InvalidRef"""
    for bad in (None, 123, {"$ref": "xxx"}):
        assert SwaggerAdapter.fix_ref(bad) == "#/components/schemas/InvalidRef"


# -----------------------------
# 3. 测试 RefFixer.fix_refs
# -----------------------------

def test_fix_refs_nested_and_circular():
    """
    1) 嵌套 dict/list 中的 $ref 应被修正
    2) 循环引用时不抛异常，且 self 引用保持不变
    """
    # 构造一个同时包含嵌套和自引用的对象
    a = {
        "$ref": "#/definitions/A",
        "nested": [
            {"$ref": "#/parameters/P"}
        ]
    }
    a["self"] = a  # 循环引用

    result = RefFixer.fix_refs(a)

    # 嵌套 ref 被修正
    assert result["$ref"] == "#/components/schemas/A"
    assert result["nested"][0]["$ref"] == "#/components/parameters/P"
    # 循环引用没有丢失，且保持原对象
    assert result is result["self"]


# -----------------------------
# 4. 测试 _adapt_parameters
# -----------------------------
def test_adapt_parameters_scalar_and_array():
    """普通标量类型和数组类型参数应被正确转换为 schema 结构"""
    params = [
        {
            "name": "id",
            "in": "query",
            "type": "string",
            "format": "uuid",
            "default": "abc",
            "required": True
        },
        {
            "name": "tags",
            "in": "query",
            "type": "array",
            "items": {"type": "string"},
            "description": "标签列表"
        },
        {
            # 已经包含 schema 的参数，不应重复转换
            "name": "filter",
            "in": "query",
            "schema": {"type": "object"}
        }
    ]

    adapted = SwaggerAdapter._adapt_parameters(deepcopy(params))

    # id 参数
    id_param = next(p for p in adapted if p["name"] == "id")
    assert "schema" in id_param
    assert id_param["schema"]["type"] == "string"
    assert id_param["schema"]["format"] == "uuid"
    assert id_param["schema"]["default"] == "abc"

    # tags 数组参数
    tags_param = next(p for p in adapted if p["name"] == "tags")
    assert tags_param["schema"]["type"] == "array"
    assert tags_param["schema"]["items"] == {"type": "string"}
    assert tags_param["description"] == "标签列表"

    # 已有 schema 的 filter 参数
    filter_param = next(p for p in adapted if p["name"] == "filter")
    assert filter_param["schema"] == {"type": "object"}


# -----------------------------
# 5. 测试 _adapt_body_parameter
# -----------------------------
def test_adapt_body_parameter_basic():
    """将 body 参数转换为 requestBody，并移除 consumes 和原 parameters 中的 body"""
    op = {
        "parameters": [
            {
                "name": "payload",
                "in": "body",
                "schema": {"type": "object"},
                "required": True,
                "description": "请求体描述"
            }
        ],
        "consumes": ["application/xml"]
    }

    SwaggerAdapter._adapt_body_parameter(op)

    # 参数列表中不再含 body
    assert all(p.get("in") != "body" for p in op.get("parameters", []))
    # requestBody 正确生成
    rb = op["requestBody"]
    assert rb["required"] is True
    assert rb["description"] == "请求体描述"
    assert "application/xml" in rb["content"]
    assert rb["content"]["application/xml"]["schema"] == {"type": "object"}


def test_adapt_body_parameter_default_media_type():
    """缺省 consumes 时，默认 application/json"""
    op = {
        "parameters": [
            {"name": "p", "in": "body", "schema": {"type": "string"}}
        ]
    }
    SwaggerAdapter._adapt_body_parameter(op)
    # 默认 application/json
    assert "application/json" in op["requestBody"]["content"]


# -----------------------------
# 6. 测试 _adapt_form_parameters
# -----------------------------
def test_adapt_form_parameters_urlencoded_and_multipart():
    """
    formData 参数转换为 requestBody，
    普通字段为 x-www-form-urlencoded，
    包含 file 字段时用 multipart/form-data
    """
    # case1：无文件类型
    op1 = {
        "parameters": [
            {"name": "field1", "in": "formData", "type": "string", "required": True},
            {"name": "field2", "in": "formData", "type": "integer"}
        ]
    }
    SwaggerAdapter._adapt_form_parameters(op1)
    rb1 = op1["requestBody"]
    # content-type 应为 x-www-form-urlencoded
    assert "application/x-www-form-urlencoded" in rb1["content"]
    schema1 = rb1["content"]["application/x-www-form-urlencoded"]["schema"]
    assert schema1["properties"]["field1"]["type"] == "string"
    assert schema1["properties"]["field2"]["type"] == "integer"
    assert schema1["required"] == ["field1"]

    # case2：含文件类型时
    op2 = {
        "parameters": [
            {"name": "uploader", "in": "formData", "type": "file", "required": False}
        ]
    }
    SwaggerAdapter._adapt_form_parameters(op2)
    rb2 = op2["requestBody"]
    assert "multipart/form-data" in rb2["content"]
    schema2 = rb2["content"]["multipart/form-data"]["schema"]
    assert schema2["properties"]["uploader"]["type"] == "file"


def test_adapt_form_parameters_merge_existing_request_body():
    """已经存在 requestBody 时，应合并 content 而不是覆盖"""
    op = {
        "requestBody": {
            "content": {
                "application/json": {"schema": {"type": "string"}}
            }
        },
        "parameters": [
            {"name": "f", "in": "formData", "type": "string"}
        ]
    }
    SwaggerAdapter._adapt_form_parameters(op)
    # 合并后应同时含有 application/json 和 formData 的 content
    c = op["requestBody"]["content"]
    assert "application/json" in c
    assert "application/x-www-form-urlencoded" in c


# -----------------------------
# 7. 测试 _adapt_responses
# -----------------------------
def test_adapt_responses_with_schema_and_produces():
    """响应中带 schema 和 produces，schema 应被迁移到 content，并移除 produces"""
    op = {
        "produces": ["application/json", "application/xml"],
        "responses": {
            "200": {
                "description": "OK",
                "schema": {"type": "object"}
            }
        }
    }
    SwaggerAdapter._adapt_responses(op["responses"], op)
    # produces 应被移除
    assert "produces" not in op
    # content 应包含两个媒体类型
    resp = op["responses"]["200"]
    assert "content" in resp
    assert set(resp["content"].keys()) == {"application/json", "application/xml"}
    for v in resp["content"].values():
        assert v["schema"] == {"type": "object"}


def test_adapt_responses_without_schema():
    """响应中不带 schema，应自动生成 type: object"""
    op = {
        "produces": ["application/json"],
        "responses": {
            "404": {"description": "Not found"}
        }
    }
    SwaggerAdapter._adapt_responses(op["responses"], op)
    resp = op["responses"]["404"]
    assert "content" in resp
    assert "application/json" in resp["content"]
    assert resp["content"]["application/json"]["schema"] == {"type": "object"}


# -----------------------------
# 8. 测试 adapt 主流程
# -----------------------------
def test_adapt_full_workflow():
    """
    完整流程测试：
    - swagger -> openapi
    - servers, components, paths, parameters 合并去重
    - body 参数、responses 转换、$ref 修正
    """
    swagger_doc = {
        "swagger": "2.0",
        "info": {"title": "My API"},
        "host": "api.example.com",
        "basePath": "/v1",
        "schemes": ["https"],
        "definitions": {"Pet": {"type": "object", "properties": {}}},
        "parameters": {"limit": {"name": "limit", "in": "query", "type": "integer", "default": 10}},
        "responses": {"ErrorResp": {"description": "Error"}},
        "paths": {
            "/pets": {
                "parameters": [{"name": "limit", "in": "query", "type": "integer"}],
                "get": {
                    "summary": "List pets",
                    "parameters": [{"name": "offset", "in": "query", "type": "integer"}],
                    "responses": {
                        "200": {"schema": {"type": "array", "items": {"$ref": "#/definitions/Pet"}}}
                    },
                    "produces": ["application/json"]
                }
            },
            "/login": {
                "post": {
                    "parameters": [
                        {"name": "body", "in": "body", "schema": {"type": "object"}}
                    ],
                    "consumes": ["application/json"],
                    "responses": {"201": {"schema": {"type": "object"}}}
                }
            }
        }
    }

    result = SwaggerAdapter.adapt(deepcopy(swagger_doc))

    # 顶层字段
    assert result["openapi"] == "3.0.0"
    assert "swagger" not in result

    # servers
    assert result["servers"] == [{"url": "https://api.example.com/v1"}]

    # components
    comps = result["components"]
    assert "schemas" in comps and "Pet" in comps["schemas"]
    assert "parameters" in comps and "limit" in comps["parameters"]
    assert "responses" in comps and "ErrorResp" in comps["responses"]

    # /pets get 参数合并去重
    get_op = result["paths"]["/pets"]["get"]
    names = {p["name"] for p in get_op["parameters"]}
    assert names == {"limit", "offset"}

    # /pets get 响应转换
    resp200 = get_op["responses"]["200"]
    assert "content" in resp200
    assert "application/json" in resp200["content"]
    # items.$ref 已修正
    schema = resp200["content"]["application/json"]["schema"]
    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/components/schemas/Pet"

    # /login post requestBody 转换
    post_op = result["paths"]["/login"]["post"]
    assert "requestBody" in post_op
    assert "application/json" in post_op["requestBody"]["content"]


# -----------------------------
# 9. 测试 validate_openapi3
# -----------------------------
@pytest.mark.parametrize("doc, expected_errors", [
    ({}, ["缺少 'openapi' 字段", "缺少 'info' 对象", "缺少 'paths' 对象", "缺少 'components' 对象"]),
    ({"openapi": "2.0"}, ["openapi 版本不是 3.x: 2.0", "缺少 'info' 对象", "缺少 'paths' 对象", "缺少 'components' 对象"]),
    ({"openapi": "3.0.0", "info": "not a dict"}, ["'info' 不是对象", "缺少 'paths' 对象", "缺少 'components' 对象"]),
    ({"openapi": "3.0.0", "info": {}, "paths": {}}, ["'info' 对象缺少 'title'", "'info' 对象缺少 'version'", "缺少 'components' 对象"]),
    ({"openapi": "3.0.0", "info": {"title": "T"}, "paths": {}, "components": {}}, ["'info' 对象缺少 'version'"]),
    ({"openapi": "3.0.0", "info": {"title": "T", "version": "1.0"}, "paths": {}, "components": {}}, []),
])
def test_validate_openapi3(doc, expected_errors):
    """各种缺失或错误场景下，validate_openapi3 返回对应错误列表"""
    errors = validate_openapi3(doc)
    assert errors == expected_errors