# --coding:utf-8--
import os
from configparser import NoOptionError
import fnmatch

from aomaker.path import PYTEST_INI_DIR
from aomaker.utils.utils import HandleIni


def _get_pytest_ini() -> list:
    conf = HandleIni(PYTEST_INI_DIR)
    try:
        pytest_opts = conf.get('pytest', 'addopts')
    except NoOptionError:
        return []
    if not pytest_opts:
        return []
    return pytest_opts.split()


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
        if os.path.isfile(testfile_path) and (fnmatch.fnmatch(p, "test_*.py") or fnmatch.fnmatch(p, "*_test.py")):
            testfile_path_list.append(testfile_path)
    return testfile_path_list


def make_args_group(args: list, extra_pytest_args: list):
    """构造pytest参数列表
    pytest_args_group： [['-s','-m demo'],['-s','-m demo2'],...]
    :return pytest_args_group[-1] --> ['-s','-m demo2']
    """
    pytest_args_group = []
    for arg in args:
        pytest_args = []
        pytest_args.append(arg)
        pytest_args.extend(extra_pytest_args)
        pytest_args_group.append(pytest_args)
        yield pytest_args_group[-1]