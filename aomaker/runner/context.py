import contextlib
from typing import Generator

from aomaker.session import Session
from aomaker.hook_manager import cli_hook, session_hook
from aomaker._printer import printer
from aomaker.storage import config, cache
from aomaker.config_handlers import set_conf_file

from .models import RunConfig
from .reporting import clean_allure_json, gen_reports


@printer("开始初始化环境...", "环境初始化完成，所有全局配置已加载到config表")
def setup(run_config: RunConfig):
    cache.clear()
    env = run_config.env
    if env:
        set_conf_file(env)
    
    run_mode = run_config.run_mode
    config.set("run_mode", run_mode)
    Session.set_session_vars(login_obj=run_config.login_obj)
    clean_allure_json()

    if cli_hook.custom_kwargs:
        cli_hook.run()
    session_hook.execute_pre_hooks()

@printer("运行结束，开始清理环境...", "环境清理完成!")
def teardown(run_config: RunConfig):
    try:
        if run_config.report_enabled:
            gen_reports()
        session_hook.execute_post_hooks()
    finally:
        Session.clear_env()


@contextlib.contextmanager
def runner_context(config: RunConfig)->Generator:
    setup(config)
    yield
    teardown(config)