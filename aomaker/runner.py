# --coding:utf-8--
import os
import shutil
from multiprocessing import Pool
from functools import singledispatchmethod
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

import pytest

from aomaker._printer import printer
from aomaker.cache import config
from aomaker.fixture import SetUpSession, TearDownSession, BaseLogin
from aomaker.log import logger, aomaker_logger
from aomaker._constants import Allure
from aomaker.exceptions import LoginError
from aomaker.path import REPORT_DIR, PYTEST_INI_DIR
from aomaker.report import gen_reports
from aomaker.hook_manager import _cli_hook, _session_hook

allure_json_dir = os.path.join(REPORT_DIR, "json")
RUN_MODE = {
    "Runner": "main",
    "ProcessesRunner": "mp",
    "ThreadsRunner": "mt"
}


def fixture_session(func):
    """全局夹具装饰器"""
    def wrapper(*args, **kwargs):
        # Login登录类对象
        login = kwargs.get('login')
        _init(func, login)
        r = func(*args, **kwargs)
        TearDownSession().clear_env()
        return r

    return wrapper


@printer("init_env")
def _init(func, login):
    method_of_class_name = func.__qualname__.split('.')[0]
    config.set("run_mode", RUN_MODE[method_of_class_name])
    SetUpSession(login).set_session_vars()
    shutil.rmtree(allure_json_dir, ignore_errors=True)
    if _cli_hook.custom_kwargs:
        _cli_hook.run()
    _session_hook.run()


class Runner:
    def __init__(self, is_processes=False):
        self.pytest_args = ["-s",
                            f"--alluredir={allure_json_dir}",
                            "--show-capture=no",  # 控制台不显示pytest的捕获日志
                            "--log-format=%(asctime)s %(message)s",
                            "--log-date-format=%Y-%m-%d %H:%M:%S"
                            ]
        aomaker_logger.allure_handler("debug", is_processes=is_processes)

    @fixture_session
    def run(self, args: list, login: BaseLogin = None, is_gen_allure=True, **kwargs):
        # 配置allure报告中显示日志
        # AoMakerLogger().allure_handler('debug')
        args.extend(self.pytest_args)
        pytest_opts = _get_pytest_ini()
        logger.info(f"<AoMaker> 单进程启动")
        logger.info(f"<AoMaker> pytest的执行参数：{args}")
        if pytest_opts:
            logger.info(f"<AoMaker> pytest.ini配置参数：{pytest_opts}")
        pytest.main(args)
        if is_gen_allure:
            self.allure_env_prop()
            self.gen_allure()
            gen_reports()

    @staticmethod
    def make_testsuite_path(path: str) -> list:
        """
        构建测试套件路径列表
        :param path: 测试套件所在目录
        :return: 测试套件路径列表
        """
        path_list = [path for path in os.listdir(path) if "__" not in path]
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
        path_list = [path for path in os.listdir(path) if "__" not in path]
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
        path_list = self.make_testsuite_path(arg)
        return path_list

    @make_task_args.register(dict)
    def _(self, arg: dict) -> list:
        """dist_mode:file"""
        path_list = self.make_testfile_path(arg["path"])
        return path_list

    @staticmethod
    def gen_allure(is_clear=True):
        cmd = f'allure generate ./{Allure.JSON_DIR} -o ./{Allure.HTML_DIR}'
        if is_clear:
            cmd = cmd + ' -c'
        os.system(cmd)

    @staticmethod
    def allure_env_prop():
        conf: dict = config.get_all()
        if conf:
            content = ""
            for k, v in conf.items():
                content += f"{k}={v}\n"
            with open(os.path.join(allure_json_dir, "environment.properties"), mode='w', encoding='utf-8') as f:
                f.write(content)

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

    @fixture_session
    def run(self, task_args, login: BaseLogin = None, extra_args=None, is_gen_allure=True, **kwargs):
        """
        多进程启动pytest任务
        :param task_args:
                list：mark标记列表
                str：测试套件或测试文件所在目录路径
        :param login: Login登录对象
        :param extra_args: pytest其它参数列表
        :param is_gen_allure: 是否自动收集allure报告，默认收集
        :return:
        """
        # 配置allure报告中显示日志
        # AoMakerLogger().allure_handler('debug', is_processes=True)
        if extra_args is None:
            extra_args = []
        extra_args.extend(self.pytest_args)
        task_args = self.make_task_args(task_args)
        process_count = len(task_args)
        p = Pool(process_count)
        logger.info(f"<AoMaker> 多进程任务启动，进程数：{process_count}")
        for arg in make_args_group(task_args, extra_args):
            p.apply_async(main_task, args=(arg,))
        p.close()
        p.join()
        if is_gen_allure:
            self.allure_env_prop()
            self.gen_allure()
            gen_reports()


class ThreadsRunner(Runner):
    @fixture_session
    def run(self, task_args: list or str, login: BaseLogin = None, extra_args=None, is_gen_allure=True, **kwargs):
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
        _ = [tp.submit(main_task, arg) for arg in make_args_group(task_args, extra_args)]
        wait(_, return_when=ALL_COMPLETED)
        tp.shutdown()
        if is_gen_allure:
            self.allure_env_prop()
            self.gen_allure()
            gen_reports()


def main_task(args: list):
    """pytest启动"""
    pytest_opts = _get_pytest_ini()
    logger.info(f"<AoMaker> pytest的执行参数：{args}")
    if pytest_opts:
        logger.info(f"<AoMaker> pytest.ini配置参数：{pytest_opts}")
    pytest.main(args)


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


run = Runner().run
threads_run = ThreadsRunner().run
processes_run = ProcessesRunner(is_processes=True).run

if __name__ == '__main__':
    ProcessesRunner().run(['-m hpc', '-m ehpc', '-m ehpc1', '-m hpc1'])
