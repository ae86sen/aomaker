import pytest
from unittest.mock import MagicMock

from aomaker.storage import cache, config
import aomaker.session as session_mod
import aomaker.config_handlers as ch
import aomaker.hook_manager as hm
import aomaker.runner.context as ctx_module
from aomaker.session import BaseLogin

from aomaker.runner.context import setup as ctx_setup, teardown as ctx_teardown, runner_context
from aomaker.runner.models import RunConfig


def test_setup_without_env_no_hooks(monkeypatch):
    """测试 setup 在无 env 且无自定义 hook 参数时的行为"""
    # stub 依赖
    monkeypatch.setattr(cache, 'clear', MagicMock())
    monkeypatch.setattr(ch, 'set_conf_file', MagicMock())
    monkeypatch.setattr(config, 'set', MagicMock())
    monkeypatch.setattr(session_mod.Session, 'set_session_vars', MagicMock())
    monkeypatch.setattr(ctx_module, 'clean_allure_json', MagicMock())
    # 无自定义参数
    monkeypatch.setattr(hm.cli_hook, 'custom_kwargs', {})
    monkeypatch.setattr(hm.cli_hook, 'run', MagicMock())
    monkeypatch.setattr(hm.session_hook, 'execute_pre_hooks', MagicMock())

    cfg = RunConfig()  # 默认 env None，不会调用 set_conf_file
    ctx_setup(cfg)

    cache.clear.assert_called_once()
    ch.set_conf_file.assert_not_called()
    config.set.assert_called_once_with('run_mode', cfg.run_mode)
    session_mod.Session.set_session_vars.assert_called_once_with(login_obj=cfg.login_obj)
    ctx_module.clean_allure_json.assert_called_once()
    hm.cli_hook.run.assert_not_called()
    hm.session_hook.execute_pre_hooks.assert_called_once()


def test_setup_with_env_and_hooks(monkeypatch):
    """测试 setup 在指定 env 且有自定义 hook 参数时的行为"""
    monkeypatch.setattr(cache, 'clear', MagicMock())
    # Patch set_conf_file within the context module
    mock_set_conf = MagicMock()
    monkeypatch.setattr(ctx_module, 'set_conf_file', mock_set_conf)
    monkeypatch.setattr(config, 'set', MagicMock())
    monkeypatch.setattr(session_mod.Session, 'set_session_vars', MagicMock())
    monkeypatch.setattr(ctx_module, 'clean_allure_json', MagicMock())
    # 有自定义参数
    monkeypatch.setattr(hm.cli_hook, 'custom_kwargs', {'k': 'v'})
    monkeypatch.setattr(hm.cli_hook, 'run', MagicMock())
    monkeypatch.setattr(hm.session_hook, 'execute_pre_hooks', MagicMock())

    dummy_login = MagicMock(spec=BaseLogin)
    cfg = RunConfig(env='dev', login_obj=dummy_login, run_mode='mp', task_args=['a'])
    ctx_setup(cfg)

    cache.clear.assert_called_once()
    # Assert the mock within the context module was called
    mock_set_conf.assert_called_once_with('dev')
    config.set.assert_called_once_with('run_mode', 'mp')
    session_mod.Session.set_session_vars.assert_called_once_with(login_obj=dummy_login)
    ctx_module.clean_allure_json.assert_called_once()
    hm.cli_hook.run.assert_called_once()
    hm.session_hook.execute_pre_hooks.assert_called_once()


def test_teardown_with_and_without_report(monkeypatch):
    """测试 teardown 在 report_enabled 为 True/False 时的行为"""
    monkeypatch.setattr(ctx_module, 'gen_reports', MagicMock())
    monkeypatch.setattr(hm.session_hook, 'execute_post_hooks', MagicMock())
    monkeypatch.setattr(session_mod.Session, 'clear_env', MagicMock())

    # report_enabled True
    cfg1 = RunConfig(report_enabled=True)
    ctx_teardown(cfg1)
    ctx_module.gen_reports.assert_called_once()
    hm.session_hook.execute_post_hooks.assert_called_once()
    session_mod.Session.clear_env.assert_called_once()

    # reset
    ctx_module.gen_reports.reset_mock()
    hm.session_hook.execute_post_hooks.reset_mock()
    session_mod.Session.clear_env.reset_mock()

    # report_enabled False
    cfg2 = RunConfig(report_enabled=False)
    ctx_teardown(cfg2)
    ctx_module.gen_reports.assert_not_called()
    hm.session_hook.execute_post_hooks.assert_called_once()
    session_mod.Session.clear_env.assert_called_once()


def test_runner_context(monkeypatch):
    """测试 runner_context 上下文管理器调用顺序"""
    calls = []
    import aomaker.runner.context as ctx
    monkeypatch.setattr(ctx, 'setup', lambda cfg: calls.append(('setup', cfg)))
    monkeypatch.setattr(ctx, 'teardown', lambda cfg: calls.append(('teardown', cfg)))

    cfg = RunConfig()
    with runner_context(cfg):
        calls.append('inside')

    assert calls == [('setup', cfg), 'inside', ('teardown', cfg)] 