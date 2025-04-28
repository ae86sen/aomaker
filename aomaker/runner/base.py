# --coding:utf-8--
from functools import singledispatchmethod

import pytest

from aomaker._printer import print_message
from aomaker.log import aomaker_logger
from aomaker import pytest_plugins
from aomaker.path import ALLURE_JSON_DIR

from .args import _get_pytest_ini, make_testfile_path, make_testsuite_path
from .progress import _progress_init
from .models import RunConfig



class Runner:
    def __init__(self, is_processes=False):
        self.pytest_args = ["-s",
                            f"--alluredir={ALLURE_JSON_DIR}",
                            "--show-capture=no",
                            "--log-format=%(asctime)s %(message)s",
                            "--log-date-format=%Y-%m-%d %H:%M:%S"
                            ]
        self.pytest_plugins = [pytest_plugins]
        aomaker_logger.allure_handler("debug", is_processes=is_processes)

    def run(self, run_config: RunConfig, **kwargs):
        print_message("🚀单进程模式准备启动...")

        final_pytest_args = run_config.pytest_args[:]
        final_pytest_args.extend(self.pytest_args)

        pytest_ini_opts = _get_pytest_ini()

        print_message(f":rocket: 单进程启动", style="cyan")
        print_message(f":gear: pytest的执行参数：{final_pytest_args}", style="cyan")
        if pytest_ini_opts:
            print_message(f":gear: pytest.ini配置参数：{pytest_ini_opts}", style="cyan")

        _progress_init(final_pytest_args)
        pytest.main(final_pytest_args, plugins=self.pytest_plugins)


    @singledispatchmethod
    def make_task_args(self, arg):
        raise TypeError("arg type must be List or Path")

    @make_task_args.register(list)
    def _(self, arg: list) -> list:
        """dist_mode:mark"""
        return arg

    @make_task_args.register(str)
    def _(self, arg: str) -> list:
        """dist_mode:suite"""
        return make_testsuite_path(arg)

    @make_task_args.register(dict)
    def _(self, arg: dict) -> list:
        """dist_mode:file"""
        return make_testfile_path(arg["path"])

    def _prepare_extra_args(self, extra_args):
        if extra_args is None:
            extra_args = []
        extra_args.extend(self.pytest_args)
        return extra_args

    def _prepare_task_args(self, task_args):
        return self.make_task_args(task_args)