import pytest
from typing import Optional
from aomaker.maker.generator import collect_apis_imports, collect_models_imports,generate_imports, ImportManager
from aomaker.maker.models import Import, DataType, DataModelField, DataModel, Endpoint
from aomaker.maker.config import OpenAPIConfig



def make_endpoint_with_imports():
    imp = Import(from_="foo.bar", import_="Baz", alias="BazAlias")
    ep = Endpoint(
        class_name="TestAPI",
        path="/test",
        method="get",
        imports={imp},
        tags=[],
    )
    return ep, imp


def test_collect_apis_imports_includes_core_and_user_imports(tmp_path):
    """
    collect_apis_imports 应当包含：
    - attrs.define, field
    - aomaker.core.router.router
    - base_api_class
    - endpoint.imports
    """
    ep, custom_imp = make_endpoint_with_imports()
    cfg = OpenAPIConfig(base_api_class="foo.base.BaseAPI", base_api_class_alias="BaseAlias")
    mgr = collect_apis_imports([ep], cfg)

    keys = set(mgr._imports.keys())
    # attrs.define, field （整体导入项）
    assert ("attrs", "define, field") in keys
    # router
    assert ("aomaker.core.router", "router") in keys
    # base_api_class
    assert ("foo.base", "BaseAPI") in keys
    # 自定义 import
    assert (custom_imp.from_, custom_imp.import_) in keys


def test_collect_models_imports_optional_and_custom_imports():
    """
    collect_models_imports:
    - 如果有非必填字段或 is_optional，应引入 typing.Optional
    - 合并 model.imports
    """
    # 模拟两个字段，一个必填，一个 optional
    dt_req = DataType(type="int", is_optional=False)
    dt_opt = DataType(type="str", is_optional=True)
    f1 = DataModelField(name="a", data_type=dt_req, required=True)
    f2 = DataModelField(name="b", data_type=dt_opt, required=False)
    custom_imp = Import(from_="foo.typing", import_="Something", alias=None)
    model = DataModel(name="M", fields=[f1, f2], imports={custom_imp})
    mgr = collect_models_imports([model])
    keys = set(mgr._imports.keys())
    # 包含 Optional
    assert ("typing", "Optional") in keys
    # 包含自定义 import
    assert (custom_imp.from_, custom_imp.import_) in keys



def test_generate_imports_categorization_and_order():
    """
    构造三个导入：
      - 标准库 typing.Optional
      - 第三方 attrs.define
      - 内部模块 myproj.mod.ClassX
    检查输出的顺序和内容
    """
    mgr = ImportManager()
    mgr.add_import(Import(from_="typing", import_="Optional"))
    mgr.add_import(Import(from_="attrs", import_="define"))
    mgr.add_import(Import(from_="myproj.mod", import_="ClassX", alias="CX"))

    lines = generate_imports(mgr)
    # stdlib 在前
    assert lines[0].startswith("from typing import Optional")
    # third_party
    assert any("from attrs import define" in l for l in lines)
    # internal
    assert any("from myproj.mod import ClassX as CX" in l for l in lines)

    # exclude_internal=True 时不应出现 internal
    lines2 = generate_imports(mgr, exclude_internal=True)
    assert not any("myproj.mod" in l for l in lines2)


def test_generate_imports_direct_imports_and_alias():
    """
    测试直接 import a as b 的情况
    """
    mgr = ImportManager()
    mgr.add_import(Import(from_=None, import_="os", alias=None))
    mgr.add_import(Import(from_=None, import_="sys", alias="sys_alias"))

    lines = generate_imports(mgr)
    # os、sys 的 direct_imports 在最后按字母排序
    assert "import os" in lines
    assert "import sys as sys_alias" in lines


# tests/test_template_render_utils.py
import pytest
from aomaker.maker.generator import TemplateRenderUtils
from aomaker.maker.models import DataModelField, DataType

utils = TemplateRenderUtils(config=None)


@pytest.mark.parametrize("default_value, type_name, expected", [
    (None, "int", "default=None"),
    ("", "str", "default=None"),
    ("abc", "str", 'default="abc"'),
    ([1, 2], "list", "factory=list"),
    ({}, "dict", "factory=dict"),
    (42, "int", "default=42"),
    (True, "bool", "default=True"),
    # 类型不匹配：default True，但类型指定为 str
    (True, "str", "default=None"),
])
def test_render_field_default(default_value, type_name, expected):
    dt = DataType(type=type_name.lower())
    field = DataModelField(name="x", data_type=dt, required=True, default=default_value)
    assert utils.render_field_default(field) == expected


def test_render_field_metadata_empty():
    """无描述、无约束 → 空串"""
    dt = DataType(type="int")
    f = DataModelField(name="x", data_type=dt)
    assert utils.render_field_metadata(f) == ""


def test_render_field_metadata_description_and_constraints():
    """
    包含描述、min_length、pattern 等约束，检查元数据 key 是否正确拼接
    """
    dt = DataType(type="str")
    desc = 'he said "hello"\nworld'
    f = DataModelField(
        name="y", data_type=dt, description=desc,
        min_length=1, max_length=5, pattern=r"\d+"
    )
    meta = utils.render_field_metadata(f)
    assert '"description": ' in meta
    assert '"""\\\nhe said \\"hello\\"\nworld\n"""' in meta
    assert '"minLength": 1' in meta
    assert '"maxLength": 5' in meta
    assert '"pattern": "\\d+"' in meta


def test_get_attrs_field_parameters_combine():
    """
    组合 default + metadata + alias
    """
    dt = DataType(type="str")
    f = DataModelField(name="z", data_type=dt, default="abc", description="d", alias="ali")
    params = utils.get_attrs_field_parameters(f)
    # 顺序不限，但三部分都应该出现
    assert 'default="abc"' in params
    assert 'metadata={' in params
    # assert "alias='ali'" in params


@pytest.mark.parametrize("required,is_optional,expected", [
    (True, False, "int"),
    (False, False, "Optional[int]"),
    (True, True, "Optional[int]"),   # is_optional 优先
    (False, True, "Optional[int]"),  # 同上
])
def test_render_optional_hint(required, is_optional, expected):
    dt = DataType(type="int", is_optional=is_optional)
    f = DataModelField(name="n", data_type=dt, required=required)
    hint = utils.render_optional_hint(f)
    assert hint == expected



@pytest.mark.parametrize("kwargs,expected", [
    ({"type":"int"}, "int"),
    ({"type":"str", "is_list":True, "data_types":[DataType(type="int")]}, "List[int]"),
    ({"type":"str", "is_dict":True, "data_types":[DataType(type="str"), DataType(type="bool")]}, "Dict[str, bool]"),
    ({"type":"float", "is_optional":True}, "Optional[float]"),
    ({"type":"CustomType", "is_custom_type":True}, "CustomType"),
])
def test_data_type_type_hint(kwargs, expected):
    dt = DataType(**kwargs)
    assert dt.type_hint == expected



@pytest.mark.parametrize("kwargs,expected", [
    ({"type":"int"}, "int"),
    ({"type":"str", "is_list":True, "data_types":[DataType(type="int")]}, "List[int]"),
    ({"type":"str", "is_dict":True, "data_types":[DataType(type="str"), DataType(type="bool")]}, "Dict[str, bool]"),
    ({"type":"float", "is_optional":True}, "Optional[float]"),
    ({"type":"CustomType", "is_custom_type":True}, "CustomType"),
])
def test_data_type_type_hint(kwargs, expected):
    dt = DataType(**kwargs)
    assert dt.type_hint == expected

# tests/test_generator_format_content.py
import pytest
import black
from aomaker.maker.generator import Generator
from aomaker.maker.config import OpenAPIConfig
from rich.console import Console

g = Generator(output_dir=".", config=OpenAPIConfig(), console=Console())


def test_format_valid_python():
    """
    传入合法代码，应返回 black 格式化后的字符串
    """
    src = "def foo():\n  return 1\n"
    formatted = g._format_content(src)
    assert "def foo()" in formatted
    assert "return 1" in formatted
    # Black 通常会把两个空格缩成四个
    assert "    return 1" in formatted


def test_format_invalid_python_raises():
    """
    传入语法错误代码，应抛出 black.InvalidInput
    并打印原始内容（不在单元测试里验证打印，只保证抛出）
    """
    bad = "def bad(:\n    pass"
    with pytest.raises(black.InvalidInput):
        g._format_content(bad)