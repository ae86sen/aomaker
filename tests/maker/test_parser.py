import pytest
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

# Use pydantic v2 compatible model_validate
from pydantic import TypeAdapter

from aomaker.maker.parser import OpenAPIParser, SUPPORTED_CONTENT_TYPES
from aomaker.maker.models import (
    APIGroup, Endpoint, DataModel, DataModelField, DataType, Import,
    ParameterLocation, MediaTypeEnum, Operation, Parameter, RequestBody,
    Response, Reference, JsonSchemaObject
)
from aomaker.maker.config import OpenAPIConfig

# Helper function to create minimal valid OpenAPI structure
def create_openapi_spec(
    paths: Dict[str, Any] = None,
    components: Dict[str, Any] = None
) -> Dict[str, Any]:
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths or {},
    }
    if components:
        spec["components"] = components
    return spec

# Helper to find endpoint by operationId
def find_endpoint(api_groups: List[APIGroup], operation_id: str) -> Optional[Endpoint]:
    for group in api_groups:
        for endpoint in group.endpoints:
            if endpoint.endpoint_id == operation_id:
                return endpoint
    return None

# Helper to get imports as strings for easier comparison
def get_import_strings(imports: Set[Import]) -> Set[str]:
    return {f"from {imp.from_} import {imp.import_}" for imp in imports}

# --- Fixtures ---
@pytest.fixture
def basic_config() -> OpenAPIConfig:
    """Provides a default OpenAPIConfig."""
    return OpenAPIConfig()

@pytest.fixture
def user_schema_component() -> Dict[str, Any]:
    """Provides a reusable User schema component."""
    return {
        "User": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "format": "int64"},
                "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "isActive": {"type": "boolean", "default": True}
            },
            "required": ["id", "username", "email"]
        }
    }

@pytest.fixture
def error_schema_component() -> Dict[str, Any]:
    """Provides a reusable Error schema component."""
    return {
        "Error": {
            "type": "object",
            "properties": {
                "code": {"type": "integer"},
                "message": {"type": "string"}
            },
             "required": ["code", "message"]
        }
    }

# --- Test Classes ---

class TestOpenAPIParserInitialization:
    def test_init_with_empty_spec(self, basic_config):
        """Test initialization with an empty OpenAPI v3 spec."""
        spec = create_openapi_spec()
        parser = OpenAPIParser(spec, config=basic_config)
        assert parser.openapi_data == spec
        assert not parser.api_groups
        assert parser.config == basic_config

    def test_init_registers_component_schemas(self, basic_config, user_schema_component):
        """Test that component schemas are available after initialization."""
        spec = create_openapi_spec(components={"schemas": user_schema_component})
        parser = OpenAPIParser(spec, config=basic_config)
        # parser._register_component_schemas() # Called internally by jsonschemaparser __init__
        assert "User" in parser.resolver.schema_objects
        assert "User" not in parser.model_registry # Parsing not done yet

class TestBasicParsing:
    def test_parse_single_get_endpoint_no_extras(self, basic_config):
        """Test parsing the simplest GET endpoint."""
        spec = create_openapi_spec(paths={
            "/hello": {
                "get": {
                    "summary": "Say Hello",
                    "operationId": "getHello",
                    "tags": ["greeting"],
                    "responses": {
                        "200": {"description": "Successful response"}
                    }
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()

        assert len(api_groups) == 1
        group = api_groups[0]
        assert isinstance(group, APIGroup)
        assert group.tag == "greeting"
        assert len(group.endpoints) == 1

        endpoint = group.endpoints[0]
        assert isinstance(endpoint, Endpoint)
        assert endpoint.class_name == "GetHelloAPI" # Default strategy
        assert endpoint.endpoint_id == "getHello"
        assert endpoint.path == "/hello"
        assert endpoint.method == "get"
        assert endpoint.tags == ["greeting"]
        assert endpoint.description is None # Summary is not description
        assert not endpoint.path_parameters
        assert not endpoint.query_parameters
        assert not endpoint.header_parameters
        assert endpoint.request_body is None
        assert endpoint.response is None # 200 response has no schema
        assert Import(from_='typing', import_='Optional') in endpoint.imports # Always added

    def test_parse_endpoint_with_description(self, basic_config):
        """Test parsing an endpoint with an explicit description."""
        spec = create_openapi_spec(paths={
            "/status": {
                "get": {
                    "summary": "Get Status",
                    "description": "Returns the current status.",
                    "operationId": "getStatus",
                    "tags": ["status"],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "getStatus")
        assert endpoint is not None
        assert endpoint.description == "Returns the current status."

    def test_multiple_methods_same_path(self, basic_config):
        """Test parsing multiple methods under the same path."""
        spec = create_openapi_spec(paths={
            "/items/{item_id}": {
                "get": {"operationId": "getItem", "tags": ["items"], "responses": {"200": {"description": "OK"}}},
                "put": {"operationId": "updateItem", "tags": ["items"], "responses": {"200": {"description": "OK"}}}
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()

        assert len(api_groups) == 1
        group = api_groups[0]
        assert group.tag == "items"
        assert len(group.endpoints) == 2
        methods = {ep.method for ep in group.endpoints}
        ids = {ep.endpoint_id for ep in group.endpoints}
        assert methods == {"get", "put"}
        assert ids == {"getItem", "updateItem"}

    def test_multiple_tags_and_default_tag(self, basic_config):
        """Test endpoints with multiple tags and endpoints with no tags (default)."""
        spec = create_openapi_spec(paths={
            "/users": {"get": {"operationId": "listUsers", "tags": ["users", "admin"], "responses": {"200": {"description": "OK"}}}},
            "/ping": {"get": {"operationId": "pingServer", "responses": {"200": {"description": "OK"}}}} # No tags
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()

        assert len(api_groups) == 3 # users, admin, default
        tags_found = {group.tag for group in api_groups}
        assert tags_found == {"users", "admin", "default"}

        users_group = next(g for g in api_groups if g.tag == "users")
        admin_group = next(g for g in api_groups if g.tag == "admin")
        default_group = next(g for g in api_groups if g.tag == "default")

        assert len(users_group.endpoints) == 1 and users_group.endpoints[0].endpoint_id == "listUsers"
        assert len(admin_group.endpoints) == 1 and admin_group.endpoints[0].endpoint_id == "listUsers"
        # Ensure it's the same Endpoint object shared across groups
        assert users_group.endpoints[0] is admin_group.endpoints[0]
        assert len(default_group.endpoints) == 1 and default_group.endpoints[0].endpoint_id == "pingServer"

    def test_no_operation_id_fallback_naming(self, basic_config):
        """Test fallback class naming when operationId is missing."""
        spec = create_openapi_spec(paths={
            "/basic/resource": {
                "post": { # No operationId
                    "tags": ["basic"],
                    "responses": {"201": {"description": "Created"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = api_groups[0].endpoints[0]
        # Default fallback strategy might be method + path parts
        assert endpoint.class_name == "PostBasicResourceAPI" # Based on default config strategy
        assert endpoint.endpoint_id == "/basic/resource_post" # Fallback ID


class TestParameterParsing:
    def test_parse_path_query_header_params(self, basic_config):
        """Test parsing parameters in path, query, and header."""
        spec = create_openapi_spec(paths={
            "/entity/{entity_id}": {
                "get": {
                    "operationId": "getEntity",
                    "tags": ["entity"],
                    "parameters": [
                        {"name": "entity_id", "in": "path", "required": True, "schema": {"type": "integer", "format": "int64"}},
                        {"name": "filter", "in": "query", "required": False, "schema": {"type": "string", "default": "active"}},
                        {"name": "X-Request-ID", "in": "header", "required": False, "schema": {"type": "string", "format": "uuid"}}
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "getEntity")
        assert endpoint is not None

        # Path Param
        assert len(endpoint.path_parameters) == 1
        path_p = endpoint.path_parameters[0]
        assert path_p.name == "entity_id"
        assert path_p.required is True
        assert path_p.data_type.type == "int"
        assert path_p.default is None

        # Query Param
        assert len(endpoint.query_parameters) == 1
        query_p = endpoint.query_parameters[0]
        assert query_p.name == "filter"
        assert query_p.required is False
        assert query_p.data_type.type == "str"
        assert query_p.default == "active"

        # Header Param
        assert len(endpoint.header_parameters) == 1
        header_p = endpoint.header_parameters[0]
        assert header_p.name == "X-Request-ID" # Retains original name for header
        assert header_p.required is False
        assert header_p.data_type.type == "UUID" # Type mapping from jsonschema parser
        assert header_p.default is None

        # Check imports from parameters
        expected_imports = {
            "from typing import Optional", # Default
            "from uuid import UUID"        # From header param format
        }
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_parse_parameter_ref(self, basic_config):
        """Test parsing parameters defined via $ref."""
        spec = create_openapi_spec(
            paths={
                "/search": {
                    "get": {
                        "operationId": "searchItems",
                        "parameters": [
                            {"$ref": "#/components/parameters/LimitParam"},
                            {"$ref": "#/components/parameters/QueryParam"}
                        ],
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
            components={
                "parameters": {
                    "LimitParam": {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 10}},
                    "QueryParam": {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}}
                }
            }
        )
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "searchItems")
        assert endpoint is not None

        assert len(endpoint.query_parameters) == 2
        # Params should be sorted: required first
        assert endpoint.query_parameters[0].name == "q"
        assert endpoint.query_parameters[0].required is True
        assert endpoint.query_parameters[1].name == "limit"
        assert endpoint.query_parameters[1].required is False # Default is False
        assert endpoint.query_parameters[1].default == 10

    def test_parse_parameter_with_content(self, basic_config):
        """Test parsing parameters defined using 'content' (less common)."""
        spec = create_openapi_spec(paths={
            "/complex_param": {
                "get": {
                    "operationId": "getWithComplexParam",
                    "parameters": [
                        {
                            "name": "complex",
                            "in": "query",
                            "required": True,
                            "content": { # Instead of schema
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"key": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        # NOTE: parser.py's _parse_content_schema seems to handle this,
        # but it might generate an inline model or a named one.
        # Current implementation _parse_parameter_schema generates a named model
        # like "ComplexParam".
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "getWithComplexParam")
        assert endpoint is not None

        assert len(endpoint.query_parameters) == 1
        param = endpoint.query_parameters[0]
        assert param.name == "complex"
        assert param.required is True
        # Expect a DataType pointing to a generated model for the complex param
        assert param.data_type.is_custom_type
        assert param.data_type.type == "ComplexParam" # Generated name
        assert "ComplexParam" in parser.model_registry

        # Check imports for the generated parameter model
        expected_imports = {
            "from typing import Optional",
            "from .models import ComplexParam"
        }
        assert get_import_strings(endpoint.imports) == expected_imports


class TestRequestBodyParsing:
    def test_request_body_ref_schema(self, basic_config, user_schema_component):
        """Test requestBody referencing a component schema."""
        spec = create_openapi_spec(
            paths={
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "tags": ["users"],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            },
            components={"schemas": user_schema_component}
        )
        parser = OpenAPIParser(spec, config=basic_config)
        # parser._register_component_schemas() # Auto-called
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "createUser")
        assert endpoint is not None

        assert endpoint.request_body is not None
        assert isinstance(endpoint.request_body, DataModel) # Check it's a DataModel instance
        assert endpoint.request_body.name == "User" # Points to the component model
        assert endpoint.request_body is parser.model_registry.get("User") # Should be the exact model from registry

        expected_imports = {
            "from typing import Optional",
            "from .models import User" # Import for the request body model
        }
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_request_body_inline_schema(self, basic_config):
        """Test requestBody with an inline schema definition."""
        spec = create_openapi_spec(paths={
            "/login": {
                "post": {
                    "operationId": "loginUser",
                    "tags": ["auth"],
                    "requestBody": {
                        "content": {"application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"user": {"type": "string"}, "pass": {"type": "string"}},
                                "required": ["user", "pass"]
                            }
                        }}
                    },
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "loginUser")
        assert endpoint is not None

        assert endpoint.request_body is not None
        assert isinstance(endpoint.request_body, DataModel)
        # Inline request body gets a specific name 'RequestBody' within the endpoint context
        assert endpoint.request_body.name == "RequestBody"
        assert endpoint.request_body.is_inline is True # Marked as inline
        assert len(endpoint.request_body.fields) == 2
        field_names = {f.name for f in endpoint.request_body.fields}
        assert field_names == {"user", "pass"}
        # Should not be in the global registry under 'RequestBody' unless multiple endpoints define identical inline bodies?
        # Current logic seems to make it specific to the endpoint.
        # assert "RequestBody" not in parser.model_registry # Or it is, but marked inline? Check parser logic.

        # No import from .models needed for inline schema
        expected_imports = {"from typing import Optional"}
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_request_body_different_content_types_json_priority(self, basic_config):
        """Test that JSON content type is preferred for request body."""
        spec = create_openapi_spec(paths={
            "/submit": {
                "post": {
                    "operationId": "submitData",
                    "requestBody": {
                        "content": {
                            "application/xml": {"schema": {"type": "string"}},
                            "application/json": {"schema": {"type": "object", "properties": {"id": {"type": "integer"}}}},
                            "multipart/form-data": {"schema": {"type": "object", "properties": {"file": {"type": "string"}}}}
                        }
                    },
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "submitData")
        assert endpoint is not None

        assert endpoint.request_body is not None
        # Check that the JSON schema was parsed
        assert endpoint.request_body.name == "RequestBody" # Inline JSON schema
        assert len(endpoint.request_body.fields) == 1
        assert endpoint.request_body.fields[0].name == "id"
        assert endpoint.request_body.fields[0].data_type.type == "int"

    def test_request_body_form_data(self, basic_config):
        """Test requestBody with application/x-www-form-urlencoded."""
        spec = create_openapi_spec(paths={
            "/form": {
                "post": {
                    "operationId": "submitForm",
                    "requestBody": {
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "age": {"type": "integer"}
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "submitForm")
        assert endpoint is not None

        # Currently, parser prioritizes JSON. If JSON isn't present, it looks for others
        # in SUPPORTED_CONTENT_TYPES order. 'application/x-www-form-urlencoded' is MediaTypeEnum.FORM.value
        assert MediaTypeEnum.FORM.value in SUPPORTED_CONTENT_TYPES
        assert endpoint.request_body is not None
        assert endpoint.request_body.name == "RequestBody" # Inline form schema
        assert len(endpoint.request_body.fields) == 2
        field_names = {f.name for f in endpoint.request_body.fields}
        assert field_names == {"name", "age"}
        name_field = next(f for f in endpoint.request_body.fields if f.name == "name")
        assert name_field.required is True


class TestResponseParsing:
    def test_response_ref_schema_success(self, basic_config, user_schema_component):
        """Test successful response (200) referencing a component schema."""
        spec = create_openapi_spec(
            paths={
                "/users/me": {
                    "get": {
                        "operationId": "getMe", "tags": ["users"],
                        "responses": {
                            "200": {
                                "description": "User data",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}
                            },
                            "404": {"description": "Not Found"}
                        }
                    }
                }
            },
            components={"schemas": user_schema_component}
        )
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "getMe")
        assert endpoint is not None

        assert endpoint.response is not None
        assert isinstance(endpoint.response, DataModel)
        assert endpoint.response.name == "User" # Points to component model
        assert endpoint.response is parser.model_registry.get("User")

        expected_imports = {
            "from typing import Optional",
            "from .models import User" # Import for response model
        }
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_response_inline_schema_success(self, basic_config):
        """Test successful response (201) with an inline schema definition."""
        spec = create_openapi_spec(paths={
            "/tokens": {
                "post": {
                    "operationId": "createToken", "tags": ["auth"],
                    "responses": {
                        "201": {
                            "description": "Token created",
                            "content": {"application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"token": {"type": "string"}, "expires": {"type": "integer"}}
                                }
                            }}
                        },
                         "400": {"description": "Bad Request"}
                    }
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "createToken")
        assert endpoint is not None

        assert endpoint.response is not None
        assert isinstance(endpoint.response, DataModel)
        # Inline response schema gets name <ClassName>Response
        assert endpoint.response.name == "CreateTokenResponse"
        assert endpoint.response.is_inline is False # Response models are registered globally
        assert len(endpoint.response.fields) == 2
        field_names = {f.name for f in endpoint.response.fields}
        assert field_names == {"token", "expires"}
        assert "CreateTokenResponse" in parser.model_registry # Should be registered

        expected_imports = {
            "from typing import Optional",
            "from .models import CreateTokenResponse" # Import for the generated response model
        }
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_response_only_error_schema(self, basic_config, error_schema_component):
        """Test that non-2xx response schemas are ignored for endpoint.response."""
        spec = create_openapi_spec(
            paths={
                "/data/{id}": {
                    "get": {
                        "operationId": "getData",
                        "responses": {
                            "404": {
                                "description": "Not Found",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                            },
                             "500": {"description": "Server Error"}
                        }
                    }
                }
            },
            components={"schemas": error_schema_component}
        )
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "getData")
        assert endpoint is not None

        assert endpoint.response is None # No successful (2xx) response defined with schema
        # Error model should still be parsed and registered if referenced, but not linked to endpoint.response
        assert "Error" in parser.model_registry
        assert not any(imp.import_ == "Error" for imp in endpoint.imports) # No import for Error model

    def test_response_no_content_schema(self, basic_config):
        """Test successful response with description but no content/schema."""
        spec = create_openapi_spec(paths={
            "/delete/{id}": {
                "delete": {
                    "operationId": "deleteItem",
                    "responses": {
                        "204": {"description": "Deleted successfully"}, # No content
                        "200": {"description": "OK"} # No content schema
                    }
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        # Find endpoint (may be in 'default' group if no tags)
        endpoint = next((ep for group in api_groups for ep in group.endpoints if ep.endpoint_id == "deleteItem"), None)
        assert endpoint is not None
        assert endpoint.response is None # No schema found for 2xx responses


class TestComplexSchemaIntegration:

    def test_endpoint_with_allof_request_response(self, basic_config):
        """Test endpoint using models generated from allOf schemas."""
        spec = create_openapi_spec(
            paths={
                "/combined": {
                    "put": {
                        "operationId": "updateCombined",
                        "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CombinedInput"}}}},
                        "responses": {
                            "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/CombinedOutput"}}}}
                        }
                    }
                }
            },
            components={"schemas": {
                "Base": {"type": "object", "properties": {"base_prop": {"type": "string"}}},
                "Mixin": {"type": "object", "properties": {"mixin_prop": {"type": "integer"}}},
                "CombinedInput": {"allOf": [{"$ref": "#/components/schemas/Base"}, {"properties": {"input_prop": {"type": "boolean"}}}]},
                "CombinedOutput": {"allOf": [{"$ref": "#/components/schemas/Base"}, {"$ref": "#/components/schemas/Mixin"}]}
            }}
        )
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "updateCombined")
        assert endpoint is not None

        # Assume JsonSchemaParser correctly created CombinedInput and CombinedOutput models
        # Verify OpenAPIParser links them and imports them correctly

        assert endpoint.request_body is not None
        assert endpoint.request_body.name == "CombinedInput"
        assert endpoint.response is not None
        assert endpoint.response.name == "CombinedOutput"

        expected_imports = {
            "from typing import Optional",
            "from .models import CombinedInput",
            "from .models import CombinedOutput",
        }
        # Note: Base, Mixin imports might be needed by the models themselves,
        # but the endpoint only needs to import the final combined models.
        assert get_import_strings(endpoint.imports) == expected_imports

    def test_endpoint_with_array_of_objects(self, basic_config, user_schema_component):
        """Test endpoint where request/response is an array of component objects."""
        spec = create_openapi_spec(
            paths={
                "/users/batch": {
                    "post": {
                        "operationId": "createUsersBatch",
                        "requestBody": {"content": {"application/json": {"schema": {
                            "type": "array", "items": {"$ref": "#/components/schemas/User"}
                        }}}},
                        "responses": {
                            "201": {"content": {"application/json": {"schema": {
                                "type": "array", "items": {"$ref": "#/components/schemas/User"}
                            }}}}
                        }
                    }
                }
            },
            components={"schemas": user_schema_component}
        )
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        endpoint = find_endpoint(api_groups, "createUsersBatch")
        assert endpoint is not None

        # How does parser represent Array[Model]?
        # Request body parsing seems to return the item type's DataType/Model.
        # Response parsing also seems to return the item type's DataType/Model.
        # The fact it's an array might be lost at the Endpoint level in current design.
        # Let's assert based on the current implementation's apparent behavior.

        assert endpoint.request_body is not None
        assert endpoint.request_body.name == "User" # Points to the item model

        assert endpoint.response is not None
        assert endpoint.response.name == "User" # Points to the item model

        # Imports should include the item model and potentially List
        expected_imports = {
            "from typing import Optional",
            "from .models import User",
            "from typing import List", # JsonSchemaParser should add this for array types
        }
        # Check if List import is actually added by the underlying JsonSchemaParser
        # We need to look at the DataType returned by parse_schema for the array
        # Let's simulate the parse_response call
        resp_schema = spec["paths"]["/users/batch"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]
        resp_type = parser.parse_schema(JsonSchemaObject.model_validate(resp_schema), "CreateUsersBatchResponse")
        assert Import(from_='typing', import_='List') in resp_type.imports

        # Now check the endpoint's collected imports
        assert get_import_strings(endpoint.imports) >= expected_imports # Use >= if more imports are ok


class TestEdgeCasesAndErrors:

    def test_ignore_non_http_methods(self, basic_config):
        """Test that non-standard methods (like 'parameters') are ignored."""
        spec = create_openapi_spec(paths={
            "/resource": {
                "parameters": [{"name": "common", "in": "query"}], # Top-level parameters
                "get": {"operationId": "getResource", "responses": {"200": {"description": "OK"}}},
                "x-custom-method": {"summary": "Custom extension"} # Non-HTTP method
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        api_groups = parser.parse()
        assert len(api_groups) == 1 # default group
        assert len(api_groups[0].endpoints) == 1
        assert api_groups[0].endpoints[0].method == "get" # Only GET was parsed

    def test_invalid_ref_in_parameter(self, basic_config, caplog):
        """Test handling of an invalid $ref in parameters."""
        spec = create_openapi_spec(paths={
            "/invalid": {
                "get": {
                    "operationId": "getInvalid",
                    "parameters": [{"$ref": "#/components/parameters/NonExistentParam"}],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        with pytest.raises(KeyError): # Expecting resolver to raise KeyError
             parser.parse()
        # Check logs? Resolver might log warnings/errors. Check JsonSchemaParser behavior.

    def test_invalid_ref_in_request_body(self, basic_config, caplog):
        """Test handling of an invalid $ref in requestBody."""
        spec = create_openapi_spec(paths={
            "/invalid_body": {
                "post": {
                    "operationId": "postInvalidBody",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/InvalidSchema"}}}},
                    "responses": {"200": {"description": "OK"}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        # JsonSchemaParser's parse_schema called internally might raise or return Any
        # Let's assume it raises for now.
        with pytest.raises(KeyError):
            parser.parse()

    def test_invalid_ref_in_response(self, basic_config, caplog):
        """Test handling of an invalid $ref in response."""
        spec = create_openapi_spec(paths={
            "/invalid_resp": {
                "get": {
                    "operationId": "getInvalidResp",
                    "responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/InvalidSchema"}}}}}
                }
            }
        })
        parser = OpenAPIParser(spec, config=basic_config)
        with pytest.raises(KeyError):
            parser.parse()


class TestConfigurationImpact:
    def test_custom_class_name_strategy(self):
        """Test using a custom class naming strategy."""
        def custom_strategy(path: str, method: str, operation: Operation) -> str:
            op_id = operation.operationId
            if op_id:
                # Simple: capitalize operationId and add 'Api'
                return op_id.replace("_", " ").replace("-", " ").title().replace(" ", "") + "Api"
            # Fallback (simplified)
            return f"{method.upper()}{path.replace('/', '_').replace('{','').replace('}','')}_Api"

        config = OpenAPIConfig(class_name_strategy=custom_strategy)
        spec = create_openapi_spec(paths={
            "/users/{user_id}/posts": {
                "get": {
                    "operationId": "get_user_posts",
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/simple": {
                 "post": { # No operationId
                      "responses": {"201": {"description": "Created"}}
                 }
            }
        })
        parser = OpenAPIParser(spec, config=config)
        api_groups = parser.parse()

        endpoint_posts = find_endpoint(api_groups, "get_user_posts")
        endpoint_simple = next((ep for group in api_groups for ep in group.endpoints if ep.path == "/simple"), None)

        assert endpoint_posts is not None
        assert endpoint_posts.class_name == "GetUserPostsApi" # Based on custom strategy

        assert endpoint_simple is not None
        assert endpoint_simple.class_name == "POST_simple_Api" # Fallback in custom strategy 