from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

import black
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from .parser import APIGroup, Endpoint
from .config import OpenAPIConfig
from .models import Import, DataModelField, DataModel, DataType


class ImportManager:
    def __init__(self):
        # 存储结构：{ (from_module, import_name): {aliases} }
        self._imports: Dict[tuple, Set[str]] = defaultdict(set)

    def add_import(self, imp: Import):
        """添加一个导入项"""
        key = (imp.from_, imp.import_)
        self._imports[key].add(imp.alias)


def collect_apis_imports(endpoints: List[Endpoint], config: OpenAPIConfig) -> ImportManager:
    manager = ImportManager()
    manager.add_import(Import(from_="attrs", import_="define, field"))
    manager.add_import(Import(from_="aomaker.core.router", import_="router"))

    module_path, _, class_name = config.base_api_class.rpartition('.')
    manager.add_import(
        Import(
            from_=module_path,
            import_=class_name,
            alias=config.base_api_class_alias
        )
    )

    for endpoint in endpoints:
        for imp in endpoint.imports:
            manager.add_import(imp)
    return manager


def collect_models_imports(models: List[DataModel]) -> ImportManager:
    manager = ImportManager()
    manager.add_import(Import(from_="attrs", import_="define, field"))
    
    # 检查是否需要导入Optional
    needs_optional = False
    for model in models:
        for field in model.fields:
            if not field.required or field.data_type.is_optional:
                needs_optional = True
                break
        if needs_optional:
            break
    
    if needs_optional:
        manager.add_import(Import(from_="typing", import_="Optional"))
    
    combined_imports = set().union(*(model.imports for model in models))
    for imp in combined_imports:
        manager.add_import(imp)
    
    return manager


def generate_imports(manager: ImportManager, exclude_internal: bool = False) -> List[str]:
    stdlib_modules = {"typing", "datetime", "uuid", "enum"}
    third_party_modules = {"attrs", "aomaker"}

    categorized = {
        "stdlib": {"from_imports": defaultdict(list), "direct_imports": set()},
        "third_party": {"from_imports": defaultdict(list), "direct_imports": set()},
        "internal": {"from_imports": defaultdict(list), "direct_imports": set()},
    }
    for (from_, import_), aliases in manager._imports.items():
        if len(aliases) > 1:
            raise ValueError(f"导入项冲突: {import_} 有多个别名 {aliases}")

        alias = aliases.pop() if aliases else None
        module = from_ if from_ is not None else import_
        if module in stdlib_modules:
            category = "stdlib"
        elif module in third_party_modules:
            category = "third_party"
        else:
            category = "internal"

        if from_ is not None:
            categorized[category]["from_imports"][module].append((import_, alias))
        else:
            categorized[category]["direct_imports"].add((import_, alias))

    imports = []
    categories_order = ["stdlib", "third_party", "internal"]
    if exclude_internal:
        categories_order = ["stdlib", "third_party"]

    for category in categories_order:
        from_imports = categorized[category]["from_imports"]
        for module in sorted(from_imports.keys()):
            items = from_imports[module]
            imports.append(
                f"from {module} import {', '.join(_format_item(i) for i in items)}"
            )

        direct_imports = categorized[category]["direct_imports"]
        if direct_imports:
            lines = []
            for imp, alias in sorted(direct_imports, key=lambda x: x[0]):
                if alias:
                    lines.append(f"import {imp} as {alias}")
                else:
                    lines.append(f"import {imp}")
            imports.extend(lines)
    return imports


def _gen_models_imports(models: List[DataModel]) -> List[str]:
    imports_manager = collect_models_imports(models)
    imports = generate_imports(imports_manager, exclude_internal=True)
    return imports


def _format_item(item: tuple) -> str:
    """格式化单个导入项"""
    name, alias = item
    return f"{name} as {alias}" if alias else name


class TemplateRenderUtils:
    def __init__(self, config: OpenAPIConfig):
        self.config = config or OpenAPIConfig()

    @classmethod
    def render_field_default(cls, field: DataModelField) -> str:
        """优化后的默认值渲染函数"""
        # 获取 default 值（兼容字段不存在 default 的情况）
        default = getattr(field, "default", None)
        # 统一处理空值场景：None、空字符串、字段无 default
        if default in (None, ""):
            return "default=None"

        # 处理非空值场景
        data_type = field.data_type.type.lower()

        if default is not None and data_type is not None:
            if type(default).__name__ != data_type:
                return "default=None"

        if data_type == "str":
            # 字符串类型需要保留原始值的类型（例如 True -> "True"）
            return f'default="{default}"'
        elif data_type in ("list", "dict"):
            return f"factory={type(default).__name__}"  # 动态获取类型名
        else:
            # 其他类型直接赋值（数字、布尔值等）
            return f"default={default}"

    @classmethod
    def render_field_metadata(cls, field: DataModelField) -> str:
        """生成带有多行支持的元数据表达式"""
        metadata_parts = []
        jsonschema_parts = []
        
        # 处理描述
        if field.description:
            # 清理两端的空白字符
            desc = field.description.strip()
            # 转义双引号（仅在需要时）
            if '"' in desc:
                desc = desc.replace('"', '\\"')
            # 判断是否需要多行模式
            if "\n" in desc:
                # 使用三双引号包裹
                formatted_desc = f'"""\\\n{desc}\n"""'
            else:
                formatted_desc = f'"{desc}"'
            
            metadata_parts.append(f'"description": {formatted_desc}')
        
        # 处理原始字段名（用于序列化）
        if field.alias:
            metadata_parts.append(f'"original_name": "{field.alias}"')
        
        # 处理jsonschema约束
        
        # 类型和格式（特殊处理UUID）
        type_entry = None
        if field.data_type.type == "UUID":
            type_ = "string" if field.required else ["string", "null"]
            jsonschema_parts.append(f'"type": {type_}')
            jsonschema_parts.append('"format": "uuid"')
        
        # 字符串类约束
        if field.min_length is not None:
            jsonschema_parts.append(f'"minLength": {field.min_length}')
        if field.max_length is not None:
            jsonschema_parts.append(f'"maxLength": {field.max_length}')
        if field.pattern is not None:
            # 转义模式中的双引号
            pattern = field.pattern.replace('"', '\\"')
            jsonschema_parts.append(f'"pattern": "{pattern}"')
        
        # 数值类约束
        if field.minimum is not None:
            jsonschema_parts.append(f'"minimum": {field.minimum}')
        if field.maximum is not None:
            jsonschema_parts.append(f'"maximum": {field.maximum}')
        if field.exclusive_minimum is not None and field.exclusive_minimum:
            jsonschema_parts.append(f'"exclusiveMinimum": True')
        if field.exclusive_maximum is not None and field.exclusive_maximum:
            jsonschema_parts.append(f'"exclusiveMaximum": True')
        if field.multiple_of is not None:
            jsonschema_parts.append(f'"multipleOf": {field.multiple_of}')
        
        # 数组类约束
        if field.min_items is not None:
            jsonschema_parts.append(f'"minItems": {field.min_items}')
        if field.max_items is not None:
            jsonschema_parts.append(f'"maxItems": {field.max_items}')
        if field.unique_items is not None and field.unique_items:
            jsonschema_parts.append(f'"uniqueItems": True')
        
        # 只有在有约束时才添加jsonschema部分
        if jsonschema_parts:
            jsonschema_str = ", ".join(jsonschema_parts)
            metadata_parts.append(f'"jsonschema": {{ {jsonschema_str} }}')
        
        # 如果没有任何元数据，返回空字符串
        if not metadata_parts:
            return ""
        
        # 否则，返回完整的元数据表达式
        metadata_str = ", ".join(metadata_parts)
        return f'metadata={{ {metadata_str} }}'

    @classmethod
    def get_attrs_field_parameters(cls, field: DataModelField) -> str:
        """生成完整的 field() 参数"""
        params = []

        if default := cls.render_field_default(field):
            params.append(default)
        if metadata := cls.render_field_metadata(field):
            params.append(metadata)

        # if field.alias:
        #     params.append(f"alias='{field.alias}'")

        return ", ".join(params)

    @classmethod
    def render_optional_hint(cls, field: DataModelField) -> str:
        """渲染字段的类型注解，非必填字段添加 Optional 包装"""
        base_type = field.data_type.type
        if field.data_type.is_optional:
            return base_type
        if field.required is False:
            return f"Optional[{base_type}]"
        return base_type

    def get_base_class(self) -> str:
        _, _, class_name = self.config.base_api_class.rpartition(".")
        if self.config.base_api_class_alias:
            class_name = self.config.base_api_class_alias
        return class_name

    @classmethod
    def get_all_api_class_name(cls, endpoints: List[Endpoint]):
        return [endpoint.class_name for endpoint in endpoints]

    @classmethod
    def get_all_model_class_name(cls, datamodels: List[DataModel]):
        return [datamodel.name for datamodel in datamodels]

    @classmethod
    def is_datamodel(cls, value):
        return isinstance(value, DataModel)

    @classmethod
    def is_datatype(cls, value):
        return isinstance(value, DataType)


class Generator:
    def __init__(self, output_dir: str, config: OpenAPIConfig, console: Console = None):
        self.output_dir = Path(output_dir)
        self.config = config or OpenAPIConfig()
        self.console = console or Console()

        self.env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates"),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.render_utils = TemplateRenderUtils(config=self.config)
        # 注册全局函数
        self.env.globals.update({
            'get_attrs_field': self.render_utils.get_attrs_field_parameters,
            'get_field_metadata': self.render_utils.render_field_metadata,
            'render_optional_hint': self.render_utils.render_optional_hint,
            'get_base_class': self.render_utils.get_base_class,
            'get_all_api_class_name': self.render_utils.get_all_api_class_name,
            'get_all_model_class_name': self.render_utils.get_all_model_class_name,
        })
        self.env.tests['datamodel'] = self.render_utils.is_datamodel
        self.env.tests['datatype'] = self.render_utils.is_datatype

    def generate(self, api_groups: List[APIGroup]):
        """生成所有API组的代码"""
        total_groups = len(api_groups)
        for idx, api_group in enumerate(api_groups, 1):
            if self.console:
                self.console.log(
                    f"[primary]✅ [bold]已生成:[/] "
                    f"[highlight]{api_group.tag}[/] "
                    f"[muted]package[/] "
                    f"([muted]{idx}/{total_groups}[/])"
                )
            self._generate_package(api_group.tag, api_group)
        # for api_group in api_groups:
        #     self._generate_package(api_group.tag, api_group)

    def _generate_package(self, tag: str, api_group: APIGroup) -> None:
        """为每个tag生成一个Python包"""
        endpoints = api_group.endpoints
        package_dir = self.output_dir / tag
        package_dir.mkdir(parents=True, exist_ok=True)

        # 生成导入语句
        apis_all_imports = self._generate_apis_imports(endpoints)
        referenced_models = list(api_group.models.values())

        models_all_imports = self._gen_models_imports(referenced_models)

        # 创建__init__.py
        self._generate_init(package_dir)

        # 生成models.py
        self._generate_models(package_dir, referenced_models, models_all_imports)

        # 生成apis.py
        self._generate_apis(package_dir, endpoints, apis_all_imports)

    def _generate_init(self, package_dir: Path):
        template = self.env.get_template("init.j2")
        content = template.render()
        (package_dir / "__init__.py").write_text(content,encoding="utf-8")

    def _generate_models(self, package_dir: Path, referenced_models: List[DataModel], imports: List[str]):
        """生成models.py文件"""
        template = self.env.get_template("models.j2")
        content = template.render(
            referenced_models=referenced_models,
            imports=imports,
        )

        format_content = self._format_content(content)

        # 写入文件
        (package_dir / "models.py").write_text(format_content,encoding="utf-8")

    def _generate_apis(self, package_dir: Path, endpoints: List[Endpoint], imports: List[str]):
        """生成apis.py文件"""
        template = self.env.get_template("apis.j2")
        content = template.render(
            endpoints=endpoints,
            imports=imports,
        )

        format_content = self._format_content(content)

        # 写入文件
        (package_dir / "apis.py").write_text(format_content,encoding="utf-8")

    def _generate_apis_imports(self, endpoints: List[Endpoint]) -> List[str]:
        import_manager = collect_apis_imports(endpoints, self.config)
        imports = generate_imports(import_manager)

        return imports

    def _gen_models_imports(self, models: List[DataModel]) -> List[str]:
        imports_manager = collect_models_imports(models)
        imports = generate_imports(imports_manager, exclude_internal=True)
        return imports

    def _get_referenced_models(self, imports: List[str], all_models: Dict[str, DataModel]) -> List[DataModel]:
        target_line = next((line for line in imports if line.startswith('from models import')), None)

        model_name_list = []
        if target_line:
            # 分割并清理类名
            _, classes_part = target_line.split(' import ', 1)
            model_name_list = [cls.strip() for cls in classes_part.split(',')]

        referenced_models = [all_models[model] for model in model_name_list if model in all_models]
        return referenced_models

    def _format_content(self, content: str):
        origin_content = content
        try:
            return black.format_str(content, mode=black.FileMode())
        except black.InvalidInput as e:
            print("Generated content before formatting:")
            print("=" * 80)
            print(origin_content)
            print("=" * 80)
            print(f"❌ 语法错误 @ : {e}")
            # 打印出错位置的上下文
            lines = content.split('\n')
            line_num = int(str(e).split(':')[1])
            start = max(0, line_num - 5)
            end = min(len(lines), line_num + 5)
            print(f"问题上下文 (行 {start}-{end}):")
            for i in range(start, end):
                print(f"{i}: {lines[i]}")
            raise e