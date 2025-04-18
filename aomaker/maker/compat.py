# --coding:utf-8--
from copy import deepcopy
from typing import Dict, Any, List, Optional
import uuid


class SwaggerAdapter:
    """适配Swagger 2.0格式到OpenAPI 3.0兼容格式"""

    @staticmethod
    def is_swagger(doc: Dict[str, Any]) -> bool:
        """判断是否为Swagger 2.0文档"""
        return 'swagger' in doc and doc.get('swagger', '').startswith('2')

    @staticmethod
    def adapt(swagger_doc: Dict[str, Any]) -> Dict[str, Any]:
        """将Swagger 2.0文档适配为OpenAPI 3.0兼容格式"""
        doc = deepcopy(swagger_doc)

        if 'swagger' in doc:
            doc.pop('swagger')
            doc['openapi'] = '3.0.0'

        if 'info' not in doc or not isinstance(doc['info'], dict):
            doc['info'] = {'title': 'Converted API', 'version': '1.0.0'}
        elif 'version' not in doc['info']:
            doc['info']['version'] = '1.0.0'
        elif 'title' not in doc['info']:
            doc['info']['title'] = 'Converted API'

        SwaggerAdapter._adapt_servers(doc)

        SwaggerAdapter._adapt_components(doc)

        SwaggerAdapter._adapt_paths(doc)

        doc = RefFixer.fix_refs(doc)

        return doc

    @staticmethod
    def _adapt_servers(doc: Dict[str, Any]) -> None:
        """将host、basePath和schemes转换为servers数组"""
        servers = []

        host = doc.pop('host', None)
        base_path = doc.pop('basePath', '')
        schemes = doc.pop('schemes', ['https'])

        if host:
            for scheme in schemes:
                url = f"{scheme}://{host}{base_path}"
                servers.append({"url": url})

        if not servers:
            servers.append({"url": "/"})

        doc['servers'] = servers

    @staticmethod
    def _adapt_components(doc: Dict[str, Any]) -> None:
        """适配所有组件定义"""
        components = {'schemas': {}}

        if 'definitions' in doc:
            components['schemas'] = doc.pop('definitions')

        if 'securityDefinitions' in doc:
            components['securitySchemes'] = doc.pop('securityDefinitions')

        if 'parameters' in doc:
            components['parameters'] = doc.pop('parameters')

        if 'responses' in doc:
            components['responses'] = doc.pop('responses')

        doc['components'] = components

    @staticmethod
    def _adapt_parameters(parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """适配参数对象，确保每个参数都有正确的OpenAPI 3.0结构"""
        result = []
        for param in parameters:
            if not isinstance(param, dict):
                continue

            adapted_param = deepcopy(param)

            if 'type' in adapted_param and 'schema' not in adapted_param and adapted_param.get('in') != 'body':
                schema = {'type': adapted_param.pop('type')}

                for prop in ['format', 'enum', 'minimum', 'maximum', 'minLength',
                             'maxLength', 'pattern', 'default', 'multipleOf',
                             'exclusiveMinimum', 'exclusiveMaximum']:
                    if prop in adapted_param:
                        schema[prop] = adapted_param.pop(prop)

                if schema['type'] == 'array' and 'items' in adapted_param:
                    schema['items'] = adapted_param.pop('items')

                adapted_param['schema'] = schema

            result.append(adapted_param)
        return result

    @staticmethod
    def _adapt_paths(doc: Dict[str, Any]) -> None:
        """适配paths下的操作"""
        paths = doc.get('paths', {})
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            path_parameters = []
            if 'parameters' in path_item:
                path_parameters = path_item.pop('parameters')
                path_parameters = SwaggerAdapter._adapt_parameters(path_parameters)

            for method, operation in path_item.items():
                if method not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    continue

                if not isinstance(operation, dict):
                    continue

                if path_parameters:
                    operation_params = operation.get('parameters', [])
                    param_names = {p.get('name') for p in operation_params if isinstance(p, dict)}
                    for param in path_parameters:
                        if isinstance(param, dict) and param.get('name') not in param_names:
                            operation_params.append(param)
                    operation['parameters'] = operation_params

                SwaggerAdapter._adapt_operation(operation)

    @staticmethod
    def _adapt_body_parameter(operation: Dict[str, Any]) -> None:
        """将body参数转换为requestBody，考虑consumes字段"""
        parameters = operation.get('parameters', [])
        body_params = [p for p in parameters if p.get('in') == 'body']

        if body_params:
            body_param = body_params[0]

            media_types = operation.get('consumes', ['application/json'])

            content = {}
            for media_type in media_types:
                content[media_type] = {
                    'schema': body_param.get('schema', {})
                }

            operation['requestBody'] = {
                'content': content,
                'required': body_param.get('required', False),
                'description': body_param.get('description', '')
            }

            operation['parameters'] = [p for p in parameters if p.get('in') != 'body']

            if 'consumes' in operation:
                operation.pop('consumes')

    @staticmethod
    def _adapt_form_parameters(operation: Dict[str, Any]) -> None:
        """将formData参数转换为requestBody"""
        parameters = operation.get('parameters', [])
        form_params = [p for p in parameters if p.get('in') == 'formData']

        if form_params:
            # 确定合适的content-type
            content_types = []
            if 'consumes' in operation and operation['consumes']:
                form_content_types = [ct for ct in operation['consumes']
                                      if ct in ['application/x-www-form-urlencoded', 'multipart/form-data']]
                if form_content_types:
                    content_types = form_content_types

            if not content_types:
                content_type = 'application/x-www-form-urlencoded'
                for param in form_params:
                    if param.get('type') == 'file':
                        content_type = 'multipart/form-data'
                        break
                content_types = [content_type]

            properties = {}
            required_props = []

            for param in form_params:
                param_name = param.get('name', '')
                if not param_name:
                    continue

                schema = param.get('schema', {})
                if not schema and 'type' in param:
                    schema = {'type': param.get('type')}

                    for prop in ['format', 'enum', 'minimum', 'maximum', 'minLength',
                                 'maxLength', 'pattern', 'default', 'multipleOf',
                                 'exclusiveMinimum', 'exclusiveMaximum']:
                        if prop in param:
                            schema[prop] = param[prop]

                    if schema['type'] == 'array' and 'items' in param:
                        schema['items'] = param['items']

                properties[param_name] = schema

                if param.get('required', False):
                    required_props.append(param_name)

            form_schema = {
                'type': 'object',
                'properties': properties
            }

            if required_props:
                form_schema['required'] = required_props

            content_obj = {}
            for ct in content_types:
                content_obj[ct] = {'schema': form_schema}

            if 'requestBody' in operation:
                operation['requestBody']['content'].update(content_obj)
            else:
                operation['requestBody'] = {
                    'content': content_obj,
                    'required': any(p.get('required', False) for p in form_params)
                }

            operation['parameters'] = [p for p in parameters if p.get('in') != 'formData']

    @staticmethod
    def _adapt_operation(operation: Dict[str, Any]) -> None:
        """适配单个操作"""
        if not isinstance(operation, dict):
            return

        if 'parameters' in operation:
            operation['parameters'] = SwaggerAdapter._adapt_parameters(operation['parameters'])

            SwaggerAdapter._adapt_body_parameter(operation)
            SwaggerAdapter._adapt_form_parameters(operation)

        if 'responses' in operation:
            SwaggerAdapter._adapt_responses(operation['responses'], operation)

        if 'operationId' not in operation:
            if 'summary' in operation:
                operation['operationId'] = operation['summary'].lower().replace(' ', '_')
            elif 'description' in operation:
                operation['operationId'] = operation['description'].lower().replace(' ', '_')[:30]
            else:
                operation['operationId'] = f"operation_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def fix_ref(ref: str) -> str:
        """修复引用路径"""
        if not isinstance(ref, str):
            return "#/components/schemas/InvalidRef"

        if ref.startswith('#/definitions/'):
            return ref.replace('#/definitions/', '#/components/schemas/')
        elif ref.startswith('#/parameters/'):
            return ref.replace('#/parameters/', '#/components/parameters/')
        elif ref.startswith('#/responses/'):
            return ref.replace('#/responses/', '#/components/responses/')
        elif ref.startswith('#/securityDefinitions/'):
            return ref.replace('#/securityDefinitions/', '#/components/securitySchemes/')
        return ref

    @staticmethod
    def _adapt_responses(responses: Dict[str, Any], operation: Dict[str, Any]) -> None:
        """适配响应对象，考虑produces字段"""
        media_types = operation.get('produces', ['application/json'])

        for status_code, response in responses.items():
            if not isinstance(response, dict):
                continue

            if 'schema' in response:
                schema = response.pop('schema')
                content = {}

                for media_type in media_types:
                    content[media_type] = {
                        'schema': schema
                    }

                response['content'] = content
            else:
                content = {}
                for media_type in media_types:
                    content[media_type] = {
                        'schema': {'type': 'object'}
                    }

                response['content'] = content

        if 'produces' in operation:
            operation.pop('produces')


class RefFixer:
    """修复文档中的引用路径"""

    @staticmethod
    def fix_refs(obj: Any, visited: Optional[List] = None) -> Any:
        """递归修复对象中的所有引用，避免循环引用导致的无限递归"""
        if visited is None:
            visited = []

        if isinstance(obj, (dict, list)) and id(obj) in visited:
            return obj

        if isinstance(obj, dict):
            visited.append(id(obj))

            if '$ref' in obj and isinstance(obj['$ref'], str):
                obj['$ref'] = SwaggerAdapter.fix_ref(obj['$ref'])

            for key, value in list(obj.items()):
                try:
                    obj[key] = RefFixer.fix_refs(value, visited)
                except RecursionError:
                    print(f"警告: 处理字段 '{key}' 时检测到递归引用，已跳过")
                    obj[key] = {"type": "object", "description": "循环引用已简化"}

        elif isinstance(obj, list):
            visited.append(id(obj))

            result = []
            for item in obj:
                try:
                    result.append(RefFixer.fix_refs(item, visited))
                except RecursionError:
                    print("警告: 处理列表项时检测到递归引用，已跳过")
                    result.append({"type": "object", "description": "循环引用已简化"})
            return result

        return obj


def validate_openapi3(doc):
    """验证文档是否符合 OpenAPI 3.0 基本规范"""
    errors = []

    # 检查版本
    if 'openapi' not in doc:
        errors.append("缺少 'openapi' 字段")
    elif not doc['openapi'].startswith('3.'):
        errors.append(f"openapi 版本不是 3.x: {doc['openapi']}")

    # 检查必要字段
    if 'info' not in doc:
        errors.append("缺少 'info' 对象")
    elif not isinstance(doc['info'], dict):
        errors.append("'info' 不是对象")
    else:
        # 在 info 已存在且为 dict 的情况下，分别检查 title 和 version
        if 'title' not in doc['info']:
            errors.append("'info' 对象缺少 'title'")
        if 'version' not in doc['info']:
            errors.append("'info' 对象缺少 'version'")

    # 检查 paths
    if 'paths' not in doc:
        errors.append("缺少 'paths' 对象")

    # 检查 components
    if 'components' not in doc:
        errors.append("缺少 'components' 对象")

    return errors