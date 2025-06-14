from unittest.mock import patch, MagicMock

from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.config import OpenAPIConfig
from aomaker.maker.models import DataModel, DataType, DataModelField, JsonSchemaObject, Import


# Minimal valid OpenAPI v3 structure
MINIMAL_OPENAPI_V3_DOC = {
    "openapi": "3.0.0",
    "info": {"title": "Minimal API", "version": "1.0.0"},
    "paths": {}
}

# Minimal valid Swagger v2 structure
MINIMAL_SWAGGER_V2_DOC = {
    "swagger": "2.0",
    "info": {"title": "Minimal Swagger API", "version": "1.0.0"},
    "paths": {}
}

DOC_SINGLE_ENDPOINT_NO_TAGS = {
    "openapi": "3.0.0",
    "info": {"title": "Single Endpoint API", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "summary": "Get items",
                "operationId": "getItems",
                "responses": {
                    "200": {"description": "Success"}
                }
            }
        }
    }
}

DOC_MULTI_ENDPOINT_SINGLE_TAG = {
    "openapi": "3.0.0",
    "info": {"title": "Multi Endpoint Single Tag API", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "summary": "Get items",
                "tags": ["Items"],
                "operationId": "getItems",
                "responses": {"200": {"description": "Success"}}
            },
             "post": {
                "summary": "Create item",
                "tags": ["Items"],
                "operationId": "createItem",
                "responses": {"201": {"description": "Created"}}
            }
        }
    }
}

DOC_MULTI_ENDPOINT_MULTI_TAGS = {
    "openapi": "3.0.0",
    "info": {"title": "Multi Tag API", "version": "1.0.0"},
    "paths": {
        "/items": {
            "get": {
                "summary": "Get items",
                "tags": ["Items"],
                "operationId": "getItems",
                "responses": {"200": {"description": "Success"}}
            }
        },
        "/users": {
             "get": {
                "summary": "Get users",
                "tags": ["Users"],
                "operationId": "getUsers",
                "responses": {"200": {"description": "Success"}}
            }
        }
    }
}

DOC_WITH_NON_HTTP_METHODS = {
    "openapi": "3.0.0",
    "info": {"title": "Non HTTP Methods API", "version": "1.0.0"},
    "paths": {
        "/items": {
            "parameters": [
                {"name": "commonParam", "in": "query", "schema": {"type": "string"}}
            ],
            "get": {
                "summary": "Get items",
                "operationId": "getItems",
                "responses": {"200": {"description": "Success"}}
            },
            "x-custom-property": "some_value",
            "summary": "Path summary ignored"
        }
    }
}

# 新增一个测试文档，包含无标签接口且引用模型
DOC_NO_TAGS_WITH_MODEL = {
    "openapi": "3.0.0",
    "info": {"title": "No Tags With Model API", "version": "1.0.0"},
    "components": {
        "schemas": {
            "SimpleData": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"}
                },
                "required": ["value"]
            }
        }
    },
    "paths": {
        "/data": {
            "get": {
                "summary": "Get data",
                "operationId": "getDataNoTags",
                # 没有 tags 字段
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SimpleData"}
                            }
                        }
                    }
                }
            }
        }
    }
}

def create_parser(doc):
    mock_console = MagicMock()
    return OpenAPIParser(doc, console=mock_console)

# --- Initialization Tests ---

def test_init_with_openapi_v3():
    """
    Purpose: Verify successful initialization with a minimal valid OpenAPI v3 spec.
    Input: Simple OpenAPI v3 dict.
    Expected: Parser instance created, attributes initialized correctly.
    """
    parser = create_parser(MINIMAL_OPENAPI_V3_DOC)

    assert parser.openapi_data == MINIMAL_OPENAPI_V3_DOC
    assert isinstance(parser.config, OpenAPIConfig)
    assert parser.api_groups == {}
    assert hasattr(parser, 'resolver')
    assert hasattr(parser, 'model_registry')
    assert parser.model_registry.models == {}

@patch('aomaker.maker.parser.SwaggerAdapter')
def test_init_with_swagger_v2(mock_swagger_adapter):
    """
    Purpose: Verify initialization and conversion for Swagger v2 spec.
    Input: Simple Swagger v2 dict.
    Expected: SwaggerAdapter.adapt is called, parser uses adapted data.
    """
    mock_swagger_adapter.is_swagger.return_value = True
    adapted_doc = {"openapi": "3.0.0", "info": {"title": "Adapted API"}, "paths": {}}
    mock_swagger_adapter.adapt.return_value = adapted_doc

    parser = create_parser(MINIMAL_SWAGGER_V2_DOC)

    # Verify is_swagger was called
    mock_swagger_adapter.is_swagger.assert_called_once_with(MINIMAL_SWAGGER_V2_DOC)
    mock_swagger_adapter.adapt.assert_called_once_with(MINIMAL_SWAGGER_V2_DOC)
    assert parser.openapi_data == adapted_doc
    assert isinstance(parser.config, OpenAPIConfig)
    assert parser.api_groups == {}
    assert hasattr(parser, 'resolver')
    assert hasattr(parser, 'model_registry')

def test_init_with_components():
    """
    Purpose: Verify components/schemas are processed during initialization.
    Input: OpenAPI v3 dict with a simple component schema.
    Expected: Schema is registered in the model_registry after init.
    """
    doc_with_component = {
        "openapi": "3.0.0",
        "info": {"title": "API with Component", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "SimpleItem": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"}
                    },
                    "required": ["id", "name"]
                }
            }
        }
    }
    parser = create_parser(doc_with_component)

    assert "SimpleItem" in parser.resolver.schema_objects
    assert isinstance(parser.resolver.schema_objects["SimpleItem"], JsonSchemaObject)
    parser._register_component_schemas()  # 触发注册
    assert "SimpleItem" in parser.model_registry.models
    registered_model = parser.model_registry.models["SimpleItem"]
    assert isinstance(registered_model, DataModel)
    assert registered_model.name == "SimpleItem"
    assert len(registered_model.fields) == 2
    assert registered_model.fields[0].name == "id"
    assert registered_model.fields[0].data_type.type == "int"
    assert registered_model.fields[0].required is True
    assert registered_model.fields[1].name == "name"
    assert registered_model.fields[1].data_type.type == "str"
    assert registered_model.fields[1].required is True


# --- Main Parsing Tests ---

def test_parse_empty_paths():
    """
    Purpose: Test parsing when paths is empty.
    Input: OpenAPI dict with empty paths.
    Expected: parse() returns an empty list.
    """
    parser = create_parser(MINIMAL_OPENAPI_V3_DOC)
    api_groups = parser.parse()
    assert api_groups == []

def test_parse_single_endpoint_no_tags():
    """
    Purpose: Verify an endpoint without tags is added to the 'default' APIGroup,
             and the Endpoint object itself has tags set to ['default'].
    Input: OpenAPI dict with one path/method, no tags.
    Expected: One APIGroup ('default') with one Endpoint having tags=['default'].
    """
    parser = create_parser(DOC_SINGLE_ENDPOINT_NO_TAGS)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    group = api_groups[0]
    assert group.tag == 'default'
    assert len(group.endpoints) == 1
    endpoint = group.endpoints[0]
    assert endpoint.path == '/items'
    assert endpoint.method == 'get'
    assert endpoint.endpoint_id == 'getItems'
    assert endpoint.tags == ['default'], "Endpoint tags should default to ['default']"

def test_parse_multiple_endpoints_single_tag():
    """
    Purpose: Verify multiple endpoints with the same tag are grouped correctly.
    Input: OpenAPI dict with two path/methods sharing the same tag.
    Expected: One APIGroup with two Endpoints.
    """
    parser = create_parser(DOC_MULTI_ENDPOINT_SINGLE_TAG)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    group = api_groups[0]
    assert group.tag == 'Items'
    assert len(group.endpoints) == 2
    endpoint_ids = {ep.endpoint_id for ep in group.endpoints}
    assert endpoint_ids == {'getItems', 'createItem'}
    assert all(ep.tags == ["Items"] for ep in group.endpoints)

def test_parse_multiple_endpoints_multiple_tags():
    """
    Purpose: Verify endpoints with different tags result in multiple APIGroup's.
    Input: OpenAPI dict with endpoints having distinct tags.
    Expected: Multiple APIGroup's, each with correct Endpoint's.
    """
    parser = create_parser(DOC_MULTI_ENDPOINT_MULTI_TAGS)
    api_groups = parser.parse()

    assert len(api_groups) == 2
    groups_by_tag = {group.tag: group for group in api_groups}
    assert 'Items' in groups_by_tag
    assert 'Users' in groups_by_tag

    items_group = groups_by_tag['Items']
    assert len(items_group.endpoints) == 1
    assert items_group.endpoints[0].endpoint_id == 'getItems'

    users_group = groups_by_tag['Users']
    assert len(users_group.endpoints) == 1
    assert users_group.endpoints[0].endpoint_id == 'getUsers'

def test_parse_ignores_non_http_methods():
    """
    Purpose: Ensure non-HTTP methods/keys at path level are ignored.
    Input: OpenAPI dict with non-standard keys under a path item.
    Expected: Only valid HTTP methods are parsed into Endpoints.
    """
    parser = create_parser(DOC_WITH_NON_HTTP_METHODS)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    group = api_groups[0]
    assert group.tag == 'default'
    assert len(group.endpoints) == 1
    endpoint = group.endpoints[0]
    assert endpoint.method == 'get'
    assert endpoint.endpoint_id == 'getItems'

# --- Endpoint Parsing Tests ---

DOC_ENDPOINT_BASIC = {
    "openapi": "3.0.0",
    "info": {"title": "Basic Endpoint API", "version": "1.0.0"},
    "paths": {
        "/status": {
            "get": {
                "summary": "Get system status",
                "description": "Returns the current operational status.",
                "operationId": "getStatus",
                "tags": ["System"],
                "responses": {
                    "200": {"description": "OK"}
                }
            }
        }
    }
}

def test_endpoint_basic_info():
    """
    Purpose: Verify basic endpoint attributes are parsed correctly.
    Input: Simple operation with description, operationId.
    Expected: Endpoint object has correct path, method, description, endpoint_id.
    """
    parser = create_parser(DOC_ENDPOINT_BASIC)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    group = api_groups[0]
    assert group.tag == 'System'
    assert len(group.endpoints) == 1
    endpoint = group.endpoints[0]

    assert endpoint.path == '/status'
    assert endpoint.method == 'get'
    assert endpoint.description == "Returns the current operational status."
    assert endpoint.endpoint_id == 'getStatus'
    assert endpoint.tags == ["System"]

DOC_ENDPOINT_PATH_PARAM = {
    "openapi": "3.0.0",
    "info": {"title": "Path Param API", "version": "1.0.0"},
    "paths": {
        "/users/{user_id}": {
            "get": {
                "summary": "Get user by ID",
                "operationId": "getUserById",
                "tags": ["Users"],
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"}
                    }
                ],
                "responses": {
                    "200": {"description": "User details"}
                }
            }
        }
    }
}

def test_endpoint_class_name_default():
    """
    Purpose: Check default class name generation.
    Input: Operation for GET /users/{user_id}.
    Expected: Endpoint.class_name follows the default convention.
    """
    parser = create_parser(DOC_ENDPOINT_PATH_PARAM)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.class_name == 'GetUserByIdAPI'

def test_endpoint_class_name_custom():
    """
    Purpose: Check class name generation with a custom strategy.
    Input: Operation, custom class_name_strategy in config.
    Expected: Endpoint.class_name matches the output of the custom strategy.
    """
    def custom_strategy(path, method, operation):
        if operation.operationId:
            return "".join(word.capitalize() for word in operation.operationId.split('_'))
        return f"{method.capitalize()}{path.replace('/', '').replace('{', '').replace('}', '').capitalize()}"

    custom_config = OpenAPIConfig(class_name_strategy=custom_strategy)
    mock_console = MagicMock()
    parser = OpenAPIParser(DOC_ENDPOINT_PATH_PARAM, config=custom_config, console=mock_console)
    api_groups = parser.parse()

    assert len(api_groups) == 1
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.class_name == 'Getuserbyid'

# --- Parameter Parsing Tests ---

def test_param_path_required_string():
    """
    Purpose: Parse a required string path parameter.
    Input: Parameter in: path, required: true, schema: {type: string}.
           (Note: DOC_ENDPOINT_PATH_PARAM has integer, let's adjust or use a new doc)
    Expected: Endpoint.path_parameters has one field, type str, required=True.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Path String API", "version": "1.0.0"},
        "paths": {
            "/items/{item_name}": {
                "get": {
                    "operationId": "getItemByName", "tags": ["Items"],
                    "parameters": [{
                        "name": "item_name", "in": "path", "required": True,
                        "schema": {"type": "string"}, "description": "Name of the item"
                    }],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.path_parameters) == 1
    assert len(endpoint.query_parameters) == 0
    assert len(endpoint.header_parameters) == 0

    param = endpoint.path_parameters[0]
    assert isinstance(param, DataModelField)
    assert param.name == "item_name"
    assert param.required is True
    assert param.default is None
    assert param.description == "Name of the item"
    assert isinstance(param.data_type, DataType)
    assert param.data_type.type == "str"
    assert not param.data_type.is_custom_type
    assert not param.data_type.is_list
    assert not param.data_type.is_inline
    assert param.data_type.imports == set()

def test_param_query_optional_int_default():
    """
    Purpose: Parse an optional integer query parameter with a default.
    Input: Parameter in: query, required: false, schema: {type: integer, default: 10}.
    Expected: Endpoint.query_parameters has one field, type int, required=False, default=10.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Query Param API", "version": "1.0.0"},
        "paths": {
            "/search": {
                "get": {
                    "operationId": "searchItems", "tags": ["Search"],
                    "parameters": [{
                        "name": "limit", "in": "query", "required": False,
                        "schema": {"type": "integer", "format": "int32", "default": 10},
                        "description": "Max number of results"
                    }],
                    "responses": {"200": {"description": "Search Results"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.path_parameters) == 0
    assert len(endpoint.query_parameters) == 1
    assert len(endpoint.header_parameters) == 0

    param = endpoint.query_parameters[0]
    assert isinstance(param, DataModelField)
    assert param.name == "limit"
    assert param.required is False
    assert param.default == 10 # Default value is captured
    assert param.description == "Max number of results"
    assert isinstance(param.data_type, DataType)
    assert param.data_type.type == "int"
    assert not param.data_type.is_custom_type
    assert not param.data_type.is_list
    assert param.data_type.imports == set()

def test_param_header_boolean():
    """
    Purpose: Parse a header parameter.
    Input: Parameter in: header, schema: {type: boolean}.
    Expected: Endpoint.header_parameters has one field, type bool.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Header Param API", "version": "1.0.0"},
        "paths": {
            "/ping": {
                "get": {
                    "operationId": "pingServer", "tags": ["Debug"],
                    "parameters": [{
                        "name": "X-Debug-Enabled", "in": "header", "required": False,
                        "schema": {"type": "boolean"},
                        "description": "Enable debug logs"
                    }],
                    "responses": {"204": {"description": "Pong"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.path_parameters) == 0
    assert len(endpoint.query_parameters) == 0
    assert len(endpoint.header_parameters) == 1

    param = endpoint.header_parameters[0]
    assert isinstance(param, DataModelField)
    assert param.name == "X-Debug-Enabled"
    assert param.required is False
    assert param.default is None
    assert param.description == "Enable debug logs"
    assert isinstance(param.data_type, DataType)
    assert param.data_type.type == "bool"
    assert not param.data_type.is_custom_type
    assert param.data_type.imports == set()


def test_param_reference():
    """
    Purpose: Parse a parameter referencing a component parameter.
    Input: Parameter $ref: '#/components/parameters/CommonLimit'. Component defined.
    Expected: Correct DataModelField created based on the referenced component.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Ref Param API", "version": "1.0.0"},
        "components": {
            "parameters": {
                "CommonLimit": {
                    "name": "limit", "in": "query", "required": False,
                    "schema": {"type": "integer", "default": 20},
                    "description": "Common limit parameter"
                }
            }
        },
        "paths": {
            "/data": {
                "get": {
                    "operationId": "getData", "tags": ["Data"],
                    "parameters": [
                        {"$ref": "#/components/parameters/CommonLimit"}
                    ],
                    "responses": {"200": {"description": "Data retrieved"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.query_parameters) == 1
    param = endpoint.query_parameters[0]

    assert param.name == "limit"
    assert param.required is False
    assert param.default == 20
    assert param.description == "Common limit parameter"
    assert param.data_type.type == "int"
    assert Import(from_='typing', import_='Optional') in endpoint.imports
    assert len(endpoint.imports) == 1

def test_param_inline_object():
    """
    Purpose: Parse a parameter with an inline object schema.
    Input: Parameter in: query, name: filter, schema: {type: object, ...}.
    Expected: Endpoint.query_parameters contains field with DataType for an inline model.
              An inline DataModel is generated and registered. Imports added.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Inline Object Param API", "version": "1.0.0"},
        "paths": {
            "/list": {
                "get": {
                    "operationId": "listItems", "tags": ["Items"],
                    "parameters": [{
                        "name": "filter", "in": "query", "required": False,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string", "enum": ["active", "inactive"]},
                                "min_value": {"type": "integer"}
                            }
                        },
                        "description": "Filter criteria"
                    }],
                    "responses": {"200": {"description": "List of items"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.query_parameters) == 1
    param = endpoint.query_parameters[0]

    assert param.name == "filter"
    assert param.required is False
    assert param.description == "Filter criteria"

    assert isinstance(param.data_type, DataType)
    assert param.data_type.is_custom_type is True
    assert param.data_type.type == "FilterParam"
    assert param.data_type.is_inline is True
    assert param.data_type.is_list is False
    assert Import(from_='.models', import_='FilterParam') in param.data_type.imports

    assert "FilterParam" in parser.model_registry.models
    inline_model = parser.model_registry.models["FilterParam"]
    assert isinstance(inline_model, DataModel)
    assert inline_model.name == "FilterParam"
    assert inline_model.is_inline is True
    assert len(inline_model.fields) == 2
    assert inline_model.fields[0].name == "status"
    assert inline_model.fields[0].data_type.type == "FilterParam_status"
    assert inline_model.fields[1].name == "min_value"
    assert inline_model.fields[1].data_type.type == "int"

    assert Import(from_='.models', import_='FilterParam') in endpoint.imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_param_with_content():
    """
    Purpose: Parse a parameter defined via `content` instead of `schema`.
    Input: Parameter in: query, name: filter, content: {'application/json': ...}.
    Expected: DataModelField created based on the schema within `content`.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Content Param API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "FilterObject": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}}
                }
            }
        },
        "paths": {
            "/query_content": {
                "get": {
                    "operationId": "queryWithContent", "tags": ["Content"],
                    "parameters": [{
                        "name": "filter", "in": "query", "required": True,
                        "content": {
                            "application/json": { # Only JSON content is parsed for params currently
                                "schema": {"$ref": "#/components/schemas/FilterObject"}
                            }
                        },
                         "description": "Filter as JSON string in query"
                    }],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.query_parameters) == 1
    param = endpoint.query_parameters[0]

    assert param.name == "filter"
    assert param.required is True
    assert param.description == "Filter as JSON string in query"
    assert isinstance(param.data_type, DataType)
    assert param.data_type.is_custom_type is True
    assert param.data_type.type == "FilterObject"
    assert param.data_type.reference.ref == "#/components/schemas/FilterObject"
    assert not param.data_type.is_inline

    assert Import(from_='.models', import_='FilterObject') in endpoint.imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_param_sorting():
    """
    Purpose: Verify required parameters appear before optional ones.
    Input: Mix of required and optional query parameters.
    Expected: Endpoint.query_parameters list is sorted correctly (required first).
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Param Sort API", "version": "1.0.0"},
        "paths": {
            "/sorted_params": {
                "get": {
                    "operationId": "getSorted", "tags": ["Sorting"],
                    "parameters": [
                        { # Optional
                            "name": "optional_param", "in": "query", "required": False,
                            "schema": {"type": "string"}
                        },
                        { # Required
                            "name": "required_param", "in": "query", "required": True,
                            "schema": {"type": "integer"}
                        },
                         { # Optional with default
                            "name": "optional_default", "in": "query", "required": False,
                            "schema": {"type": "boolean", "default": False}
                        },
                        { # Required path (should not affect query sorting)
                            "name": "id", "in": "path", "required": True,
                            "schema": {"type": "string"}
                        },
                         { # Required header (should not affect query sorting)
                            "name": "X-Req", "in": "header", "required": True,
                            "schema": {"type": "string"}
                        },

                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }
    doc["paths"]["/sorted_params/{id}"] = doc["paths"].pop("/sorted_params")

    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert len(endpoint.query_parameters) == 3
    query_param_names = [p.name for p in endpoint.query_parameters]
    assert query_param_names == ["required_param", "optional_param", "optional_default"]
    assert endpoint.query_parameters[0].required is True
    assert endpoint.query_parameters[1].required is False
    assert endpoint.query_parameters[2].required is False

    assert len(endpoint.path_parameters) == 1
    assert endpoint.path_parameters[0].name == "id"
    assert endpoint.path_parameters[0].required is True

    assert len(endpoint.header_parameters) == 1
    assert endpoint.header_parameters[0].name == "X-Req"
    assert endpoint.header_parameters[0].required is True

# --- Request Body Parsing Tests ---

def test_reqbody_json_ref():
    """
    Purpose: Parse a request body referencing a component schema.
    Input: requestBody with content -> application/json -> schema -> $ref.
    Expected: Endpoint.request_body points to the registered DataModel for the ref.
              Import for the referenced model added to endpoint.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Req Body Ref API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "UserInput": {
                    "type": "object",
                    "properties": {"email": {"type": "string"},"username": {"type": "string"} },
                    "required": ["username"]
                }
            }
        },
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser", "tags": ["Users"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserInput"}
                            }
                        }
                    },
                    "responses": {"201": {"description": "User created"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    assert endpoint.request_body is not None
    assert isinstance(endpoint.request_body, DataModel)
    assert len(endpoint.request_body.fields) == 2
    assert endpoint.request_body.fields[0].name == "username"
    assert endpoint.request_body.fields[0].data_type.type == "str"
    assert endpoint.request_body.fields[1].name == "email"
    assert endpoint.request_body.fields[1].data_type.type == "str"
    assert endpoint.request_body.required == {"username"}

    endpoint_imports = {str(i) for i in endpoint.imports}
    assert "Import(from_='.models', import_='UserInput')" not in endpoint_imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_reqbody_json_inline_object():
    """
    Purpose: Parse a request body with an inline object schema.
    Input: requestBody with content -> application/json -> schema -> {type: object, ...}.
    Expected: Endpoint.request_body is an inline DataModel named *RequestBody.
              The DataModel has correct fields. Imports added.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Req Body Inline API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "post": {
                    "operationId": "createItem", "tags": ["Items"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "price": {"type": "number", "format": "float"},
                                        "name": {"type": "string"},
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Item created"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.request_body is not None
    assert isinstance(endpoint.request_body, DataModel)
    assert endpoint.request_body.name == "RequestBody"

    assert len(endpoint.request_body.fields) == 2
    assert endpoint.request_body.fields[0].name == "name"
    assert endpoint.request_body.fields[0].data_type.type == "str"
    assert endpoint.request_body.fields[1].name == "price"
    assert endpoint.request_body.fields[1].data_type.type == "float"

    assert Import(from_='typing', import_='Optional') in endpoint.request_body.imports

def test_reqbody_json_primitive():
    """
    Purpose: Parse a request body that's a primitive type (e.g., string).
    Input: requestBody with content -> application/json -> schema -> {type: string}.
    Expected: Endpoint.request_body is a DataType for str.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Req Body Primitive API", "version": "1.0.0"},
        "paths": {
            "/echo": {
                "post": {
                    "operationId": "echoString", "tags": ["Echo"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "text/plain": {
                                "schema": {"type": "string"}
                            }
                        }
                    },
                    "responses": {"200": {"description": "Echo response"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.request_body is not None
    assert isinstance(endpoint.request_body, DataType)
    assert endpoint.request_body.type == "str"
    assert not endpoint.request_body.is_custom_type
    assert not endpoint.request_body.is_list
    assert not endpoint.request_body.is_inline
    assert endpoint.request_body.imports == set()

    assert len(endpoint.imports) == 1
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_reqbody_no_body():
    """
    Purpose: Test endpoint with no requestBody.
    Input: Operation without requestBody field.
    Expected: Endpoint.request_body is None.
    """
    parser = create_parser(DOC_SINGLE_ENDPOINT_NO_TAGS)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.request_body is None

def test_reqbody_form_data():
    """
    Purpose: Parse application/x-www-form-urlencoded request body.
    Input: requestBody with form content type.
    Expected: Handled similarly to inline JSON object, creating an inline DataModel.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Form Data API", "version": "1.0.0"},
        "paths": {
            "/login": {
                "post": {
                    "operationId": "loginUser", "tags": ["Auth"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"}
                                    },
                                    "required": ["username", "password"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Login successful"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.request_body is not None
    assert isinstance(endpoint.request_body, DataModel)
    assert endpoint.request_body.name == "RequestBody"
    assert len(endpoint.request_body.fields) == 2
    fields_dict = {f.name: f for f in endpoint.request_body.fields}
    assert "username" in fields_dict
    assert fields_dict["username"].required is True
    assert "password" in fields_dict
    assert fields_dict["password"].required is True

    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_reqbody_multipart():
    """
    Purpose: Parse multipart/form-data request body.
    Input: requestBody with multipart content type and potential binary format.
    Expected: Handled as inline DataModel. Check for potential UploadFile import if format: binary.
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Multipart API", "version": "1.0.0"},
        "paths": {
            "/upload": {
                "post": {
                    "operationId": "uploadFile", "tags": ["Files"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "description": {"type": "string"},
                                        "file": {
                                            "type": "string",
                                            "format": "binary" # Indicates a file upload
                                         }
                                    },
                                    "required": ["file"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "File uploaded"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    assert endpoint.request_body is not None
    assert isinstance(endpoint.request_body, DataModel)
    assert endpoint.request_body.name == "RequestBody"
    assert len(endpoint.request_body.fields) == 2

    fields_dict = {f.name: f for f in endpoint.request_body.fields}
    assert "description" in fields_dict
    assert fields_dict["description"].data_type.type == "str"
    assert fields_dict["description"].required is False
    assert "file" in fields_dict
    assert fields_dict["file"].required is True
    assert fields_dict["file"].data_type.type == "bytes"

    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_reqbody_json_inline_empty_object():
    """
    Purpose: Parse a request body with an inline but empty object schema.
    Input: requestBody with content -> application/json -> schema -> {type: object}.
    Expected: 空对象不应该生成模型，endpoint.request_body应为None。
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Req Body Empty Object API", "version": "1.0.0"},
        "paths": {
            "/submit/anything": {
                "post": {
                    "operationId": "submitAnything", "tags": ["Items"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object", # An empty object
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Data received"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    # This call should not raise a ValueError
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    # 空对象不应该生成模型
    assert endpoint.request_body is None

def test_reqbody_json_inline_empty_properties_object():
    """
    Purpose: Parse a request body with an inline object that has an empty properties-object.
    Input: requestBody with ... schema -> {type: object, "properties": {}}.
    Expected: 空对象不应该生成模型，endpoint.request_body应为None。
    """
    doc = {
        "openapi": "3.0.0", "info": {"title": "Req Body Empty Props API", "version": "1.0.0"},
        "paths": {
            "/submit/empty_props": {
                "post": {
                    "operationId": "submitEmptyProps", "tags": ["Items"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {}  # Empty properties object
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Data received"}}
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]

    # 空对象不应该生成模型
    assert endpoint.request_body is None


def test_response_inline_empty_object_schema():
    """
    Purpose: 测试空的 inline 对象响应模式的解析。
    Input: 接口返回空的 inline object schema。
    Expected: 空对象不应该生成模型。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Empty Inline Response API", "version": "1.0.0"},
        "paths": {
            "/item/empty": {
                "get": {
                    "operationId": "getEmptyItem",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object" # Empty object
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    # This call should not raise a ValueError
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    
    # 空对象不应该生成模型
    assert endpoint.response is None
    # 由于没有生成模型，相关的import也不应该存在
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_response_inline_empty_properties_object_schema():
    """
    Purpose: 测试一个带有空 properties 对象的 inline 响应模式的解析。
    Input: 接口返回 {type: object, "properties": {}}。
    Expected: 空对象不应该生成模型。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Empty Props Inline Response API", "version": "1.0.0"},
        "paths": {
            "/item/empty_props": {
                "get": {
                    "operationId": "getEmptyPropsItem",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {} # Empty properties object
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    
    # 空对象不应该生成模型
    assert endpoint.response is None
    # 由于没有生成模型，相关的import也不应该存在
    assert Import(from_='typing', import_='Optional') in endpoint.imports

# --- Response Parsing Tests ---

def test_response_ref_component_schema():
    """
    Purpose: 测试响应引用组件模式 ($ref) 的解析。
    Input: components.schemas 定义了 CustomModel, 接口返回 JSON 的 $ref。
    Expected: endpoint.response 是 DataModel(CustomModel)，字段及类型正确，imports 包含 .models 和 Optional。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Ref Response API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "CustomModel": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"}
                    },
                    "required": ["id"]
                }
            }
        },
        "paths": {
            "/custom": {
                "get": {
                    "operationId": "getCustom",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CustomModel"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    # 响应模型应注册为 CustomModel
    assert isinstance(endpoint.response, DataModel)
    assert endpoint.response.name == "CustomModel"
    # 校验字段顺序：必填字段 id 在前，可选字段 title 在后
    assert [f.name for f in endpoint.response.fields] == ["id", "title"]
    assert endpoint.response.fields[0].data_type.type == "int"
    assert endpoint.response.fields[1].data_type.type == "str"
    # Imports 应包含 .models.CustomModel 和 Optional
    assert Import(from_='.models', import_='CustomModel') in endpoint.imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_response_inline_object_schema():
    """
    Purpose: 测试 inline 对象响应模式的解析。
    Input: 接口返回 inline object schema。
    Expected: endpoint.response 是 DataModel 并命名为 <ClassName>Response，字段及类型正确，imports 包含 .models 及 Optional。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Inline Response API", "version": "1.0.0"},
        "paths": {
            "/item": {
                "get": {
                    "operationId": "getItem",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "count": {"type": "integer"}
                                        },
                                        "required": ["name"]
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    expected_model = endpoint.class_name + "Response"
    assert isinstance(endpoint.response, DataModel)
    assert endpoint.response.name == expected_model
    # 字段顺序: name(required) 首位，count 可选
    assert [f.name for f in endpoint.response.fields] == ["name", "count"]
    assert endpoint.response.fields[0].data_type.type == "str"
    assert endpoint.response.fields[1].data_type.type == "int"
    # Imports 验证
    assert Import(from_='.models', import_=expected_model) in endpoint.imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_response_primitive_not_model():
    """
    Purpose: 测试原始类型响应不生成模型。
    Input: 接口返回 primitive 类型 JSON。
    Expected: endpoint.response 为 None，imports 仅包含 Optional。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Primitive Response API", "version": "1.0.0"},
        "paths": {
            "/echo": {
                "get": {
                    "operationId": "echo",
                    "responses": {
                        "200": {
                            "description": "Echo",
                            "content": {"application/json": {"schema": {"type": "string"}}}
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    assert endpoint.response is None
    # 仅 Optional 导入
    assert endpoint.imports == {Import(from_='typing', import_='Optional')}

def test_response_only_error_codes():
    """
    Purpose: 测试仅有非2xx状态码时不生成模型。
    Input: 只有 400 响应。
    Expected: endpoint.response 为 None。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Error Only API", "version": "1.0.0"},
        "paths": {
            "/err": {
                "get": {
                    "operationId": "getErr",
                    "responses": {
                        "400": {
                            "description": "Bad Request",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"msg": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    assert endpoint.response is None

def test_response_array_of_ref():
    """
    Purpose: 测试数组响应中引用组件模式的解析。
    Input: responses 返回 array of $ref。
    Expected: endpoint.response 对应组件模型，imports 包含 List、 .models 和 Optional。
    """
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "Array Ref Response API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"}
                    },
                    "required": ["id", "name"]
                }
            }
        },
        "paths": {
            "/items": {
                "get": {
                    "operationId": "getItems",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Item"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    parser = create_parser(doc)
    api_groups = parser.parse()
    endpoint = api_groups[0].endpoints[0]
    # 对应组件模型 Item
    assert isinstance(endpoint.response, DataModel)
    assert endpoint.response.name == "Item"
    # 字段 id, name 都为 required
    assert [f.name for f in endpoint.response.fields] == ["id", "name"]
    # imports 验证
    assert Import(from_='typing', import_='List') in endpoint.imports
    assert Import(from_='.models', import_='Item') in endpoint.imports
    assert Import(from_='typing', import_='Optional') in endpoint.imports

def test_parse_endpoint_no_tags_collects_models():
    """
    Purpose: Verify endpoint without tags referencing a model is correctly processed.
             Ensures the model is associated with the 'default' tag and collected.
    Input: OpenAPI dict with an endpoint lacking tags but referencing a component schema.
    Expected:
        - One APIGroup ('default') is created.
        - The endpoint is added to the 'default' group.
        - The referenced model ('SimpleData') is parsed.
        - The 'SimpleData' model is correctly collected into the 'default' APIGroup's models.
        - The collected model should have ['default'] as its tag.
    """
    parser = create_parser(DOC_NO_TAGS_WITH_MODEL)
    # 需要先手动调用 _register_component_schemas 来模拟组件模型的预注册
    # 因为 parser.parse() 内部依赖模型已存在于 model_registry
    parser._register_component_schemas()

    api_groups = parser.parse()

    # 1. 验证分组
    assert len(api_groups) == 1, "Should create one 'default' group"
    group = api_groups[0]
    assert group.tag == 'default', "Group tag should be 'default'"

    # 2. 验证端点
    assert len(group.endpoints) == 1, "Should have one endpoint in the group"
    endpoint = group.endpoints[0]
    assert endpoint.endpoint_id == 'getDataNoTags'
    assert endpoint.tags == ['default'], "Endpoint tags should default to ['default']" # parser内部会补充默认值

    # 3. 验证端点引用的响应模型
    assert endpoint.response is not None, "Endpoint should have a response model reference"
    assert isinstance(endpoint.response, DataModel)
    assert endpoint.response.name == 'SimpleData', "Endpoint response should reference SimpleData model"

    # 4. 验证模型被正确收集到分组中
    assert 'SimpleData' in group.models, "SimpleData model should be collected in the default group"
    collected_model = group.models['SimpleData']
    assert isinstance(collected_model, DataModel)
    assert collected_model.name == 'SimpleData'

    # 5. 验证收集到的模型具有正确的标签
    # 在应用修复后，这里应该包含 'default'
    # parser.parse() -> endpoint.parse() -> schema_parser.parse() 会设置 current_tags
    # 然后 model_registry 注册的模型会带有正确的 tags
    # APIGroup.collect_models 会根据模型的 tags 收集
    assert collected_model.tags == ['default'], f"Collected model tags should be ['default'], but got {collected_model.tags}"

