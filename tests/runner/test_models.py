import pytest
from pydantic import ValidationError

from aomaker.runner.models import RunConfig


def test_default_runconfig():
    """验证 RunConfig 的默认字段值"""
    cfg = RunConfig()
    assert cfg.env is None
    assert cfg.log_level == "info"
    assert cfg.run_mode == "main"
    assert cfg.task_args is None
    assert cfg.pytest_args == []
    assert cfg.login_obj is None
    assert cfg.report_enabled is True
    assert cfg.processes is None


def test_task_args_various_types():
    """验证 task_args 支持 list、str 和 dict 类型"""
    # 列表
    cfg1 = RunConfig(run_mode="main", task_args=["a", "b"] )
    assert isinstance(cfg1.task_args, list)
    assert cfg1.task_args == ["a", "b"]
    # 字符串
    cfg2 = RunConfig(run_mode="main", task_args="tests/smoke")
    assert isinstance(cfg2.task_args, str)
    assert cfg2.task_args == "tests/smoke"
    # 字典
    cfg3 = RunConfig(run_mode="main", task_args={"path": "tests/smoke"})
    assert isinstance(cfg3.task_args, dict)
    assert cfg3.task_args == {"path": "tests/smoke"}


def test_parallel_mode_requires_task_args():
    """验证在 mp/mt 模式下，缺少 task_args 会抛出 ValidationError"""
    with pytest.raises(ValidationError):
        RunConfig(run_mode="mp")
    with pytest.raises(ValidationError):
        RunConfig(run_mode="mt")


def test_processes_must_be_positive():
    """验证 processes 必须为正整数"""
    with pytest.raises(ValidationError):
        RunConfig(processes=0)
    with pytest.raises(ValidationError):
        RunConfig(processes=-1)
    # 正数情况
    cfg = RunConfig(processes=3)
    assert cfg.processes == 3


def test_literal_choices_enforced():
    """验证 run_mode 和 log_level 的 Literal 限制"""
    with pytest.raises(ValidationError):
        RunConfig(run_mode="invalid_mode")
    with pytest.raises(ValidationError):
        RunConfig(log_level="verbose") 