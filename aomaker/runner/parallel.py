# --coding:utf-8--
import os
import functools
import importlib
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import pytest

from aomaker.log import logger
from aomaker._printer import print_message

from .base import Runner
from .args import  make_args_group, _get_pytest_ini
from .progress import _progress_init
from .models import RunConfig


class ProcessesRunner(Runner):

    @property
    def max_process_count(self):
        return os.cpu_count()

    def _calculate_process_count(self, task_args):
        process_count = len(task_args)
        max_process = self.max_process_count
        return min(process_count, max_process)

    def _execute_tasks(self, process_count, task_args, extra_pytest_args, pytest_plugin_names):
        logger.info(f"<AoMaker> 多进程任务启动，进程数：{process_count}")
        with Pool(process_count) as pool:
            task_func = functools.partial(main_task, pytest_plugin_names=pytest_plugin_names)
            pool.map(task_func, make_args_group(task_args, extra_pytest_args))

    def run(self, run_config: RunConfig, **kwargs):
        """
        多进程启动pytest任务
        """
        print_message("🚀多进程模式准备启动...")

        extra_pytest_args = self._prepare_extra_args(run_config.pytest_args)
        task_args = self._prepare_task_args(run_config.task_args)
        process_count = run_config.processes

        if process_count is None:
            process_count = self._calculate_process_count(task_args)
        else:
            process_count = min(process_count, len(task_args), self.max_process_count)
        pytest_plugin_names = [plugin.__name__ for plugin in self.pytest_plugins]
        self._execute_tasks(process_count, task_args, extra_pytest_args, pytest_plugin_names)



class ThreadsRunner(Runner):
    def run(self, run_config: RunConfig, **kwargs):
        """
        多线程启动pytest任务
        """
        print_message("🚀多线程模式准备启动...")

        extra_pytest_args = self._prepare_extra_args(run_config.pytest_args)
        task_args = self._prepare_task_args(run_config.task_args)
        thread_count = len(task_args)

        tp = ThreadPoolExecutor(max_workers=thread_count)
        logger.info(f"<AoMaker> 多线程任务启动，线程数：{thread_count}")
        pytest_plugin_names = [plugin.__name__ for plugin in self.pytest_plugins]
        _ = [tp.submit(main_task, arg, pytest_plugin_names) for arg in make_args_group(task_args, extra_pytest_args)]
        wait(_, return_when=ALL_COMPLETED)
        tp.shutdown()


def main_task(args: list, pytest_plugin_names: list):
    """pytest启动"""
    pytest_opts = _get_pytest_ini()
    logger.info(f"<AoMaker> pytest的执行参数：{args}")
    if pytest_opts:
        logger.info(f"<AoMaker> pytest.ini配置参数：{pytest_opts}")
    pytest_plugins_module = [importlib.import_module(name) for name in pytest_plugin_names]
    _progress_init(args)
    pytest.main(args, plugins=pytest_plugins_module)