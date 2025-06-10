# --coding:utf-8--
import json
from collections import defaultdict
from typing import Dict, List, Optional, Union

from rich.console import Console

from aomaker.maker.models import DataModelField, Operation, Reference, Response, RequestBody, Import, MediaType, \
    MediaTypeEnum, Parameter, APIGroup, Endpoint, DataType, JsonSchemaObject, DataModel
from aomaker.log import logger
from aomaker.maker.jsonschema import JsonSchemaParser, is_python_keyword
from aomaker.maker.config import OpenAPIConfig
from aomaker.maker.compat import SwaggerAdapter

SUPPORTED_CONTENT_TYPES = [
    MediaTypeEnum.JSON.value,
    MediaTypeEnum.ANY.value,
    MediaTypeEnum.FORM.value,
    MediaTypeEnum.MULTIPART.value,
    MediaTypeEnum.BINARY.value,
    MediaTypeEnum.XML.value,
    MediaTypeEnum.TEXT.value,
    MediaTypeEnum.HTML.value
]


class OpenAPIParser(JsonSchemaParser):
    def __init__(self, openapi_data: Dict, config: OpenAPIConfig = None, console: Console = None):
        if SwaggerAdapter.is_swagger(openapi_data):
            openapi_data =  SwaggerAdapter.adapt(openapi_data)
        components = openapi_data.get("components", {})
        super().__init__(components.get("schemas", {}))

        raw_parameters = components.get("parameters", {})
        self.parameters_objects = {
            name: Parameter.model_validate(raw)
            for name, raw in raw_parameters.items()
        }

        self.openapi_data = openapi_data
        self.api_groups: Dict[str, APIGroup] = {}
        self.config: OpenAPIConfig = config or OpenAPIConfig()
        self.console = console or Console()

    def _register_component_schemas(self):
        """预注册所有组件模式"""
        for name, schema in self.resolver.schema_objects.items():
            self.parse_schema(schema, name)

    def parse(self) -> List[APIGroup]:
        """主解析流程"""
        paths = self.openapi_data.get('paths', {})
        total_paths = len(paths)
        for idx, (path, path_item) in enumerate(paths.items(), 1):
            for method, op_data in path_item.items():
                if method.lower() not in {'get', 'post', 'put', 'delete', 'patch'}:
                    continue
                if self.console:
                    self.console.log(
                        f"[primary]✅ [bold]已解析:[/] "
                        f"[accent]{method.upper()}[/] "
                        f"[muted]on[/] "
                        f"[accent]{path}[/] "
                        f"[muted]({idx}/{total_paths})[/]"
                    )
                operation = Operation.model_validate(op_data)
                self.current_tags = operation.tags or ['default']
                endpoint = self.parse_endpoint(path, method, operation)

                for tag in self.current_tags:
                    if tag not in self.api_groups:
                        self.api_groups[tag] = APIGroup(tag=tag)
                    self.api_groups[tag].add_endpoint(endpoint)
                    self.api_groups[tag].collect_models(self.model_registry)
        # self._organize_models()
        return list(self.api_groups.values())

    def parse_endpoint(self, path: str, method: str, operation: Operation) -> Endpoint:
        class_name = self.config.class_name_strategy(path, method, operation)
        endpoint_tags = operation.tags or ['default']
        endpoint = Endpoint(
            class_name=class_name,
            endpoint_id=operation.operationId or f"{path}_{method}",
            path=path,
            method=method,
            tags=endpoint_tags,
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
            if request_body_datatype is not None:
                if request_body_datatype.reference:
                    endpoint.request_body = self.model_registry.get(request_body_datatype.type)
                elif request_body_datatype.is_inline is True:
                    # 检查是否为空模型，如果是空模型则跳过
                    if not request_body_datatype.fields:
                        logger.debug(f"跳过生成空的请求体模型: {endpoint.class_name}RequestBody")
                    else:
                        endpoint.request_body = DataModel(
                            name="RequestBody",
                            fields=request_body_datatype.fields,
                            imports=request_body_datatype.imports
                        )
                else:
                    endpoint.request_body = request_body_datatype

                if endpoint.request_body is not None:
                    for imp in endpoint.request_body.imports:
                        endpoint.imports.add(imp)

        # 解析响应
        if operation.responses:
            response_type = self.parse_response(operation.responses, endpoint.class_name)
            if response_type is not None:
                type_name = None

                if response_type.is_list and response_type.data_types and response_type.data_types[0].is_custom_type:
                    item_type = response_type.data_types[0]
                    type_name = item_type.type
                    endpoint.imports.add(Import(from_='typing', import_='List'))
                elif response_type.is_custom_type:
                    type_name = response_type.type

                if type_name:
                    endpoint.response = self.model_registry.get(type_name)
                    endpoint.imports.add(Import(from_='.models', import_=type_name))

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
                description = param_obj.description or param_obj.schema_.description
            elif param_obj.content:
                media = param_obj.content.get(MediaTypeEnum.JSON.value)
                schema_obj = media.schema_
                
                if isinstance(schema_obj, Reference):
                    real_schema = self.resolver.get_ref_schema(schema_obj.ref)
                else:
                    real_schema = schema_obj

                data_type = self._parse_content_schema(param_obj.name, param_obj.content)
                default = getattr(real_schema, "default", None)
                description = param_obj.description or getattr(real_schema, "description", None)
            else:
                raise ValueError(f"参数未定义 schema_obj 或 content: {param_obj.name}")

            # 处理 Python 关键字
            param_name = param_obj.name
            alias = None
            if is_python_keyword(param_name):
                alias = param_name
                param_name = f"{param_name}_"

            field_ = DataModelField(
                name=param_name,
                data_type=data_type,
                required=param_obj.required,
                default=default,
                description=description,
                alias=alias,
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
        for content_type in SUPPORTED_CONTENT_TYPES:
            # 1. 获取JSON Schema
            content = request_body.content.get(content_type)
            if not content or not content.schema_:
                continue

            # 2. 生成上下文名称
            context_name = f"{endpoint_name}RequestBody"
            # 3. 解析类型
            body_type = self.parse_schema(content.schema_, context_name)

            return body_type

    def parse_response(
            self,
            responses: Dict[Union[str, int], Union[Reference, Response]],
            class_name: str
    ) -> Optional[DataType]:
        """解析响应并生成对应数据模型，保持与请求体处理逻辑一致"""
        # todo：暂时只处理成功响应
        # 1. 定位成功响应（2xx状态码）
        success_code = next(
            (code for code in responses.keys() if str(code).startswith('2')),
            None
        )
        if not success_code:
            logger.debug(f"未找到成功响应状态码: {class_name}")
            return None
        response = responses[success_code]

        if response.content is None:
            logger.debug(f"响应 {success_code} in {class_name} 没有 'content' 字段")
            return None

        for content_type in SUPPORTED_CONTENT_TYPES:
            content = response.content.get(content_type)
            if not content or not content.schema_:
                continue

            # 4. 统一解析Schema（自动处理嵌套引用）
            context_name = f"{class_name}Response"
            try:
                response_type = self.parse_schema(schema_obj=content.schema_, context=context_name)
            except Exception as e:
                 logger.error(f"解析响应 schema 时出错 for {class_name}, content type {content_type}: {e}")
                 continue

            return response_type

        logger.debug(f"响应 {success_code} in {class_name} 没有在支持的 content types 中找到 schema")
        return None

    def _parse_content_schema(
            self,
            param_name: str,
            content: Dict[str, MediaType]
    ) -> DataType:
        """解析 content 类型的参数 Schema"""
        media_type = content.get(MediaTypeEnum.JSON.value)
        if not media_type or not media_type.schema_:
            raise ValueError("仅支持 JSON 类型的 content 参数")
        schema_obj = media_type.schema_
        if isinstance(schema_obj, Reference):
            return self._parse_reference(schema_obj.ref)
        return self._parse_parameter_schema(param_name, schema_obj)

    def _parse_parameter_schema(self, param_name: str, schema: JsonSchemaObject) -> DataType:
        """专用方法解析参数schema"""
        if self._is_basic_type(schema):
            return self._parse_basic_datatype(schema)
        model_name = f"{param_name.capitalize()}Param"

        datatype = self.parse_schema(schema, model_name)
        datatype.is_inline = True
        model = self.model_registry.models.get(model_name)
        if model:
            model.is_inline = True
        return datatype

    def _resolve_parameter(self, param: Union[Reference, Parameter]) -> Parameter:
        """解析参数引用"""
        if isinstance(param, Reference):
            ref = param.ref
            if ref.startswith("#/components/parameters/"):
                key = ref.split("/")[-1]
                return self.parameters_objects[key]

            return self.resolver.get_ref_schema(param.ref)
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
    with open("../../api.json", 'r', encoding='utf-8') as f:
        doc = json.load(f)
    parser = OpenAPIParser(doc)
    api_groups = parser.parse()
    print(api_groups)
    print(1)
