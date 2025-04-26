# --coding:utf-8--
import os
import shutil
import importlib
import functools
import subprocess
from typing import Union, List, Text
from multiprocessing import Pool
from functools import singledispatchmethod
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import pytest

from aomaker._printer import printer, print_message
from aomaker.storage import config, cache
from aomaker.fixture import SetUpSession, TearDownSession, BaseLogin
from aomaker.log import logger, aomaker_logger
from aomaker._constants import Allure
from aomaker.path import REPORT_DIR, PYTEST_INI_DIR
from aomaker.report import gen_aomaker_reports
from aomaker import pytest_plugins
from aomaker.utils.gen_allure_report import rewrite_summary

from aomaker.hook_manager import cli_hook, session_hook

allure_json_dir = os.path.join(REPORT_DIR, "json")
RUN_MODE = {
    "Runner": "main",
    "ProcessesRunner": "mp",
    "ThreadsRunner": "mt"
}


def fixture_session(func):
    """全局夹具装饰器"""

    def wrapper(*args, **kwargs):
        login = kwargs.get('login')
        _init(func, login)
        r = func(*args, **kwargs)
        session_hook.execute_post_hooks()
        TearDownSession().clear_env()
        return r

    return wrapper


@printer("开始初始化环境...", "环境初始化完成，所有全局配置已加载到config表")
def _init(func, login):
    method_of_class_name = func.__qualname__.split('.')[0]
    config.set("run_mode", RUN_MODE[method_of_class_name])
    SetUpSession(login).set_session_vars()
    shutil.rmtree(allure_json_dir, ignore_errors=True)
    if cli_hook.custom_kwargs:
        cli_hook.run()
    session_hook().execute_pre_hooks()


class Runner:
    def __init__(self, is_processes=False):
        self.pytest_args = ["-s",
                            f"--alluredir={allure_json_dir}",
                            "--show-capture=no",
                            "--log-format=%(asctime)s %(message)s",
                            "--log-date-format=%Y-%m-%d %H:%M:%S"
                            ]
        self.pytest_plugins = [pytest_plugins]
        aomaker_logger.allure_handler("debug", is_processes=is_processes)

    @fixture_session
    def run(self, args: list, login: BaseLogin = None, is_gen_allure=True, **kwargs):
        args.extend(self.pytest_args)
        pytest_opts = _get_pytest_ini()
        print_message(f":rocket: 单进程启动", style="cyan")
        print_message(f":gear: pytest的执行参数：{args}", style="cyan")
        if pytest_opts:
            print_message(f":gear: pytest.ini配置参数：{pytest_opts}", style="cyan")

        _progress_init(args)
        pytest.main(args, plugins=self.pytest_plugins)
        if is_gen_allure:
            self.gen_reports()

    @staticmethod
    def make_testsuite_path(path: str) -> list:
        """
        构建测试套件路径列表
        :param path: 测试套件所在目录
        :return: 测试套件路径列表
        """
        path_list = [p for p in os.listdir(path) if "__" not in p]
        testsuite = []
        for p in path_list:
            testsuite_path = os.path.join(path, p)
            if os.path.isdir(testsuite_path):
                testsuite.append(testsuite_path)
        return testsuite

    @staticmethod
    def make_testfile_path(path: str) -> list:
        """
        构建测试文件路径列表
        :param path: 测试文件所在目录
        :return: 测试文件路径列表
        """
        path_list = [p for p in os.listdir(path) if "__" not in p]
        testfile_path_list = []
        for p in path_list:
            testfile_path = os.path.join(path, p)
            if os.path.isfile(testfile_path):
                testfile_path_list.append(testfile_path)
        return testfile_path_list

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
        return self.make_testsuite_path(arg)

    @make_task_args.register(dict)
    def _(self, arg: dict) -> list:
        """dist_mode:file"""
        return self.make_testfile_path(arg["path"])

    @staticmethod
    def gen_allure(is_clear=True) -> bool:
        """生成 Allure 报告"""
        cmd = f'allure generate "{Allure.JSON_DIR}" -o "{Allure.HTML_DIR}"'
        if is_clear:
            cmd += ' -c'

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            rewrite_summary()
            return True
        else:
            error_lines = [
                f"[bold red]❌ 测试报告收集失败![/bold red]",
                f"   命令: {cmd}",
                f"   返回码: {result.returncode}",
            ]
            if result.stderr:
                stderr_formatted = result.stderr.strip()
                error_lines.append(f"   [red]标准错误:[/red]\n      {stderr_formatted}")
            error_lines.extend([
                "   请检查:",
                "     1. 是否已正确安装 Allure Commandline (https://allurereport.org/)",
                "     2. allure 命令是否已添加到系统 PATH 环境变量中"
            ])

            for line in error_lines:
                print_message(line, style="red")
            return False

    @staticmethod
    def allure_env_prop():
        conf: dict = config.get_all()
        if conf:
            content = ""
            for k, v in conf.items():
                content += f"{k}={v}\n"
            os.makedirs(allure_json_dir, exist_ok=True)
            with open(os.path.join(allure_json_dir, "environment.properties"), mode='w', encoding='utf-8') as f:
                f.write(content)

    @printer("测试结束, AoMaker开始收集报告...", "AoMaker已完成测试报告(reports/aomaker-report.html)!")
    def gen_reports(self):
        self.allure_env_prop()
        is_gen_allure_success = self.gen_allure()
        if is_gen_allure_success:
            gen_aomaker_reports()

    @staticmethod
    def clean_allure_json(allure_json_path: str):
        shutil.rmtree(allure_json_path, ignore_errors=True)


def _get_pytest_ini() -> list:
    from aomaker.utils.utils import HandleIni
    from configparser import NoOptionError
    conf = HandleIni(PYTEST_INI_DIR)
    try:
        pytest_opts = conf.get('pytest', 'addopts')
    except NoOptionError:
        pytest_opts = []
    if pytest_opts:
        pytest_opts = pytest_opts.split()
    return pytest_opts


class ProcessesRunner(Runner):

    @property
    def max_process_count(self):
        return os.cpu_count()

    def _prepare_extra_args(self, extra_args):
        if extra_args is None:
            extra_args = []
        extra_args.extend(self.pytest_args)
        return extra_args

    def _prepare_task_args(self, task_args):
        return self.make_task_args(task_args)

    def _calculate_process_count(self, task_args):
        process_count = len(task_args)
        max_process = self.max_process_count
        return min(process_count, max_process)

    def _execute_tasks(self, process_count, task_args, extra_args, pytest_plugin_names):
        logger.info(f"<AoMaker> 多进程任务启动，进程数：{process_count}")
        with Pool(process_count) as pool:
            task_func = functools.partial(main_task, pytest_plugin_names=pytest_plugin_names)
            pool.map(task_func, make_args_group(task_args, extra_args))

    @fixture_session
    def run(self, task_args: Union[List, Text], login: BaseLogin = None, extra_args=None, is_gen_allure=True, process_count=None,
            **kwargs):
        """
        多进程启动pytest任务
        :param task_args:
                list：mark标记列表
                str：测试套件或测试文件所在目录路径
        :param login: Login登录对象
        :param extra_args: pytest其它参数列表
        :param is_gen_allure: 是否自动收集allure报告，默认收集
        :param process_count: 进程数
        :return:
        """
        extra_args = self._prepare_extra_args(extra_args)
        task_args = self._prepare_task_args(task_args)
        if process_count is None:
            process_count = self._calculate_process_count(task_args)
        else:
            process_count = min(process_count, len(task_args), self.max_process_count)
        pytest_plugin_names = [plugin.__name__ for plugin in self.pytest_plugins]
        self._execute_tasks(process_count, task_args, extra_args, pytest_plugin_names)
        if is_gen_allure:
            self.gen_reports()


class ThreadsRunner(Runner):
    @fixture_session
    def run(self, task_args: Union[List, Text], login: BaseLogin = None, extra_args=None, is_gen_allure=True, **kwargs):
        """
        多线程启动pytest任务
        :param task_args:
                list：mark标记列表
                str：测试套件或测试文件所在目录路径
        :param login: Login登录对象
        :param extra_args: pytest其它参数列表
        :param is_gen_allure: 是否自动收集allure报告，默认收集
        :return:
        """
        if extra_args is None:
            extra_args = []
        extra_args.extend(self.pytest_args)
        task_args = self.make_task_args(task_args)
        thread_count = len(task_args)
        tp = ThreadPoolExecutor(max_workers=thread_count)
        logger.info(f"<AoMaker> 多线程任务启动，线程数：{thread_count}")
        pytest_plugin_names = [plugin.__name__ for plugin in self.pytest_plugins]
        _ = [tp.submit(main_task, arg, pytest_plugin_names) for arg in make_args_group(task_args, extra_args)]
        wait(_, return_when=ALL_COMPLETED)
        tp.shutdown()
        if is_gen_allure:
            self.gen_reports()


def main_task(args: list, pytest_plugin_names: list):
    """pytest启动"""
    pytest_opts = _get_pytest_ini()
    logger.info(f"<AoMaker> pytest的执行参数：{args}")
    if pytest_opts:
        logger.info(f"<AoMaker> pytest.ini配置参数：{pytest_opts}")
    pytest_plugins_module = [importlib.import_module(name) for name in pytest_plugin_names]
    _progress_init(args)
    pytest.main(args, plugins=pytest_plugins_module)


def make_args_group(args: list, extra_args: list):
    """构造pytest参数列表
    pytest_args_group： [['-s','-m demo'],['-s','-m demo2'],...]
    :return pytest_args_group[-1] --> ['-s','-m demo2']
    """
    pytest_args_group = []
    for arg in args:
        pytest_args = []
        pytest_args.append(arg)
        pytest_args.extend(extra_args)
        pytest_args_group.append(pytest_args)
        yield pytest_args_group[-1]


def _progress_init(pytest_args: list):
    if len(pytest_args) > 0:
        cache.set(f"_progress.{cache.worker}", {"target": pytest_args[0], "total": 0, "completed": 0})


run = Runner().run
threads_run = ThreadsRunner().run
processes_run = ProcessesRunner(is_processes=True).run

if __name__ == '__main__':
    ProcessesRunner().run(['-m hpc', '-m ehpc', '-m ehpc1', '-m hpc1'])
