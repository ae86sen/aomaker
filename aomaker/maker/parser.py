# --coding:utf-8--
import re
import json
from collections import defaultdict
from typing import Dict, List, Optional, Union, Callable

from aomaker.maker.models import DataModelField, Operation, Reference, Response, RequestBody, Import, MediaType, \
    MediaTypeEnum, Parameter, APIGroup, Endpoint, DataType, JsonSchemaObject
from aomaker.log import logger
from aomaker.maker.jsonschema import JsonSchemaParser
from .config import OpenAPIConfig


class OpenAPIParser(JsonSchemaParser):
    def __init__(self, openapi_data: Dict, config: OpenAPIConfig = None):
        super().__init__(openapi_data.get("components", {}).get("schemas", {}))
        self.openapi_data = openapi_data
        self.api_groups: Dict[str, APIGroup] = {}
        self.config: OpenAPIConfig = config or OpenAPIConfig()

    def _register_component_schemas(self):
        """预注册所有组件模式"""
        for name, schema in self.resolver.schema_objects.items():
            self.parse_schema(schema, name)

    def parse(self) -> List[APIGroup]:
        """主解析流程"""
        for path, path_item in self.openapi_data.get('paths', {}).items():
            for method, op_data in path_item.items():
                if method.lower() not in {'get', 'post', 'put', 'delete', 'patch'}:
                    continue
                operation = Operation.model_validate(op_data)
                self.current_tags = operation.tags
                endpoint = self.parse_endpoint(path, method, operation)

                for tag in operation.tags or ['default']:
                    if tag not in self.api_groups:
                        self.api_groups[tag] = APIGroup(tag=tag)
                    self.api_groups[tag].endpoints.append(endpoint)
                    self.api_groups[tag].collect_models(self.model_registry)

        # self._organize_models()
        return list(self.api_groups.values())

    def parse_endpoint(self, path: str, method: str, operation: Operation) -> Endpoint:
        class_name = self.config.class_name_strategy(operation, method)
        endpoint = Endpoint(
            class_name=class_name,
            endpoint_id=operation.operationId,
            path=path,
            method=method,
            tags=operation.tags,
            description=operation.description
        )

        # 解析参数
        parameters = self.parse_parameters(operation.parameters)
        endpoint.path_parameters = parameters['path']
        endpoint.query_parameters = parameters['query']
        endpoint.header_parameters = parameters['header']
        for field_ in endpoint.path_parameters + endpoint.query_parameters:
            for imp in field_.data_type.imports:
                endpoint.imports.add(imp)
        # 解析请求体
        if operation.requestBody:
            request_body_datatype = self.parse_request_body(operation.requestBody, endpoint.class_name)
            endpoint.request_body = self.model_registry.get(request_body_datatype.type)
            for imp in endpoint.request_body.imports:
                endpoint.imports.add(imp)

        # 解析响应
        if operation.responses:
            response_type = self.parse_response(operation.responses, endpoint.class_name)
            endpoint.response = self.model_registry.get(response_type.type)
            response_import = Import(from_='.models', import_=response_type.type)
            endpoint.imports.add(response_import)
            # for imp in endpoint.response.imports:
            #     endpoint.imports.add(imp)
        endpoint.imports.add(Import(from_='typing', import_='Optional'))
        return endpoint

    def parse_parameters(self, parameters: List[Union[Reference, Parameter]]) -> Dict[str, List[DataModelField]]:
        parsed = defaultdict(list)
        for param in parameters:
            param_obj = self._resolve_parameter(param)
            location = param_obj.in_.value
            if param_obj.schema_:
                data_type = self._parse_parameter_schema(param_obj.name, param_obj.schema_)
                default = param_obj.schema_.default
                description = param_obj.schema_.description
            elif param_obj.content:
                data_type = self._parse_content_schema(param_obj.name, param_obj.content)
                default = param_obj.content.get(MediaTypeEnum.JSON.value).schema_.default
                description = param_obj.content.get(MediaTypeEnum.JSON.value).description
            else:
                raise ValueError(f"参数未定义 schema_obj 或 content: {param_obj.name}")

            field_ = DataModelField(
                name=param_obj.name,
                data_type=data_type,
                required=param_obj.required,
                default=default,
                description=description,
            )
            parsed[location].append(field_)

        # 排序：必填参数在前
        for loc in parsed:
            parsed[loc].sort(key=lambda x: not x.required)
        return parsed

    def parse_request_body(
            self,
            request_body: RequestBody,
            endpoint_name: str
    ) -> Optional[DataType]:
        """解析请求体，返回类型并触发模型生成"""

        # 1. 获取JSON Schema
        content = request_body.content.get(MediaTypeEnum.JSON.value)
        if not content or not content.schema_:
            return None

        # 2. 生成上下文名称
        context_name = f"{endpoint_name}RequestBody"

        # 3. 解析类型
        body_type = self.parse_schema(content.schema_, context_name)

        # 4. 如果是对象类型，确保模型已生成
        if body_type.is_custom_type and body_type.type not in self.model_registry.models:
            raise
            # raise ModelNotGeneratedError(f"模型 {body_type.type} 尚未生成")

        return body_type

    def parse_response(
            self,
            responses: Dict[Union[str, int], Union[Reference, Response]],
            class_name: str
    ) -> Optional[DataType]:
        """解析响应并生成对应数据模型，保持与请求体处理逻辑一致"""
        # 1. 定位成功响应（2xx状态码）
        success_code = next(
            (code for code in responses.keys() if str(code).startswith('2')),
            None
        )
        if not success_code:
            logger.debug(f"未找到成功响应状态码: {class_name}")
            return None
        response = responses[success_code]
        content = response.content.get(MediaTypeEnum.JSON.value)
        if not content or not content.schema_:
            logger.debug(f"响应未定义JSON Schema: {class_name}")
            return None

        # 4. 统一解析Schema（自动处理嵌套引用）
        context_name = f"{class_name}Response"

        response_type = self.parse_schema(schema_obj=content.schema_, context=context_name)
        if response_type.is_custom_type and response_type.type not in self.model_registry.models:
            raise
        return response_type

    def _parse_content_schema(
            self,
            param_name: str,
            content: Dict[str, MediaType]
    ) -> DataType:
        """解析 content 类型的参数 Schema"""
        # 示例：仅处理 application/json
        media_type = content.get(MediaTypeEnum.JSON.value)
        if not media_type or not media_type.schema_:
            raise ValueError("仅支持 JSON 类型的 content 参数")

        return self._parse_parameter_schema(param_name, media_type.schema_)

    def _parse_parameter_schema(self, param_name: str, schema: JsonSchemaObject) -> DataType:
        """专用方法解析参数schema"""
        if self._is_basic_type(schema):
            return self._parse_basic_datatype(schema)
        model_name = f"{param_name.capitalize()}Param"

        datatype = self.parse_schema(schema, model_name)
        return datatype

    def _resolve_parameter(self, param: Union[Reference, Parameter]) -> Parameter:
        """解析参数引用"""
        if isinstance(param, Reference):
            param = self.resolver.get_ref_schema(param.ref)
        return param

    def _organize_models(self):
        """整理模型到对应的APIGroup"""
        for group in self.api_groups.values():
            group.models = {
                name: model
                for name, model in self.model_registry.models.items()
                if not model.is_inline
            }


if __name__ == '__main__':
    with open("../api.json", 'r', encoding='utf-8') as f:
        doc = json.load(f)
    parser = OpenAPIParser(doc)
    api_groups = parser.parse()
    print(api_groups)
    print(1)
