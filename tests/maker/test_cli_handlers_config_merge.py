import sys
import textwrap
import types
import importlib
import yaml
import pytest

from aomaker.maker import cli_handlers
from aomaker.maker.cli_handlers import _resolve_gen_models_config
from aomaker.maker.config import OpenAPIConfig, NAMING_STRATEGIES


def _write_yaml(path, data: dict):
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _prepare_yaml(monkeypatch, tmp_path, openapi_dict: dict):
    # 指定临时 aomaker.yaml 并写入
    aomaker_yaml = tmp_path / "aomaker.yaml"
    _write_yaml(aomaker_yaml, {"openapi": openapi_dict})
    # 替换被测模块中的常量路径为临时文件
    monkeypatch.setattr(cli_handlers, "AOMAKER_YAML_PATH", str(aomaker_yaml))


def _prepare_custom_strategy_module(monkeypatch, tmp_path, module_path="testpkg.naming", func_name="my_strategy"):
    """
    在临时目录下创建 testpkg.naming 模块，并注入 sys.path 以便 importlib 导入。
    """
    pkg_dir = tmp_path / "testpkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    naming_py = pkg_dir / "naming.py"
    naming_py.write_text(
        textwrap.dedent(f"""
        def {func_name}(path, method, operation, suffix: str = "API") -> str:
            return "DummyAPI"
        """),
        encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    # 确保 importlib 能找到
    importlib.invalidate_caches()
    return f"{module_path}.{func_name}"


def test_cli_c_overrides_yaml_custom_strategy(monkeypatch, tmp_path):
    """
    CLI 传 -c summary，YAML 有 custom_strategy；预期：忽略 YAML 的 custom_strategy，仅使用 summary。
    """
    _prepare_yaml(monkeypatch, tmp_path, {
        "spec": "file.json",
        "output": "out_dir",
        "class_name_strategy": "operation_id",
        "custom_strategy": "conf.naming.custom_naming",
        "base_api_class": "pkg.Base",
        "base_api_class_alias": "Alias",
    })

    final = _resolve_gen_models_config(
        spec="cli_spec.json",
        output="cli_out",
        class_name_strategy="summary",
        custom_strategy=None,
        base_api_class=None,
        base_api_class_alias=None
    )
    assert final["final_class_name_strategy"] == "summary"
    assert final["final_custom_strategy"] is None  # 被屏蔽
    # 构建 OpenAPIConfig，确保不会被 custom_strategy 覆盖
    config = OpenAPIConfig(class_name_strategy=NAMING_STRATEGIES["summary"])
    assert config.class_name_strategy is NAMING_STRATEGIES["summary"]


def test_cli_cs_overrides_and_warns(monkeypatch, tmp_path, capsys):
    """
    同时传 -c 和 -cs，预期以 -cs 为准，并产生警告。
    """
    # YAML 里给些无关紧要的默认
    _prepare_yaml(monkeypatch, tmp_path, {
        "spec": "file.json",
        "output": "out_dir",
        "class_name_strategy": "operation_id",
        "custom_strategy": "conf.naming.custom_naming",
    })
    cs_path = _prepare_custom_strategy_module(monkeypatch, tmp_path)

    final = _resolve_gen_models_config(
        spec="cli_spec.json",
        output=None,
        class_name_strategy="summary",
        custom_strategy=cs_path,
        base_api_class=None,
        base_api_class_alias=None
    )
    # 优先 cs
    assert final["final_custom_strategy"] == cs_path
    assert final["final_class_name_strategy"] == "summary"  # 仍保留，但会被 custom_strategy 覆盖
    assert any("已优先使用 -cs" in w for w in final["warnings"])

    # 构建 OpenAPIConfig，验证 custom_strategy 生效并覆盖 class_name_strategy
    cfg = OpenAPIConfig(
        class_name_strategy=NAMING_STRATEGIES["summary"],
        custom_strategy=cs_path
    )
    # custom_strategy 被解析为函数，且取代 summary
    assert callable(cfg.class_name_strategy)
    assert cfg.class_name_strategy is not NAMING_STRATEGIES["summary"]
    # 自定义函数返回 "DummyAPI"
    # 这里不直接调用，但可简单断言名称以 MyStrategy 命名约定
    assert cfg.class_name_strategy.__name__ == cs_path.rsplit(".", 1)[-1]


def test_yaml_only_applies(monkeypatch, tmp_path):
    """
    不传 CLI 参数，预期完全采用 YAML 值。
    """
    _prepare_yaml(monkeypatch, tmp_path, {
        "spec": "yaml_spec.json",
        "output": "yaml_out",
        "class_name_strategy": "summary",
        "custom_strategy": None,
        "base_api_class": "yaml.Base",
        "base_api_class_alias": "AliasY",
    })
    final = _resolve_gen_models_config(
        spec=None, output=None,
        class_name_strategy=None, custom_strategy=None,
        base_api_class=None, base_api_class_alias=None
    )
    assert final["final_spec"] == "yaml_spec.json"
    assert final["final_output"] == "yaml_out"
    assert final["final_class_name_strategy"] == "summary"
    assert final["final_custom_strategy"] is None
    assert final["final_base_api_class"] == "yaml.Base"
    assert final["final_base_api_class_alias"] == "AliasY"


def test_base_api_class_cli_overrides_yaml(monkeypatch, tmp_path):
    """
    -B 未传时用 YAML；传入 -B 时覆盖 YAML。
    """
    _prepare_yaml(monkeypatch, tmp_path, {
        "spec": "file.json",
        "output": "out_dir",
        "base_api_class": "yaml.Base",
        "base_api_class_alias": "AliasY",
    })
    # 未传 -B，取 YAML
    final1 = _resolve_gen_models_config(
        spec="cli_spec.json", output=None,
        class_name_strategy=None, custom_strategy=None,
        base_api_class=None, base_api_class_alias=None
    )
    assert final1["final_base_api_class"] == "yaml.Base"
    assert final1["final_base_api_class_alias"] == "AliasY"

    # 传入 -B 覆盖
    final2 = _resolve_gen_models_config(
        spec="cli_spec.json", output=None,
        class_name_strategy=None, custom_strategy=None,
        base_api_class="cli.Base", base_api_class_alias="AliasC"
    )
    assert final2["final_base_api_class"] == "cli.Base"
    assert final2["final_base_api_class_alias"] == "AliasC"


def test_base_api_class_defaults_when_yaml_missing(monkeypatch, tmp_path):
    """
    YAML 未提供 base_api_class 且 CLI 也未传，预期交由 OpenAPIConfig 默认值生效。
    """
    _prepare_yaml(monkeypatch, tmp_path, {
        "spec": "file.json",
        "output": "out_dir",
        # 无 base_api_class / alias
    })
    final = _resolve_gen_models_config(
        spec="cli_spec.json", output=None,
        class_name_strategy=None, custom_strategy=None,
        base_api_class=None, base_api_class_alias=None
    )
    # 合并结果为 None，构建时不传则使用默认
    assert final["final_base_api_class"] is None
    assert final["final_base_api_class_alias"] is None

    cfg = OpenAPIConfig(class_name_strategy=NAMING_STRATEGIES["operation_id"])
    # 默认值来自 OpenAPIConfig 定义
    assert cfg.base_api_class == "aomaker.core.api_object.BaseAPIObject"
    assert cfg.base_api_class_alias is None


def test_openapi_config_maps_strategy_string():
    """
    保障 OpenAPIConfig 能将字符串策略名映射为函数（防御性测试）。
    """
    cfg = OpenAPIConfig(class_name_strategy="summary")
    assert cfg.class_name_strategy is NAMING_STRATEGIES["summary"]