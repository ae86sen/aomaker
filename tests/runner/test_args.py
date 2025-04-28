from unittest.mock import patch

from aomaker.runner import args
from configparser import NoOptionError


@patch('aomaker.runner.args.HandleIni')
def test_get_pytest_ini_with_addopts(mock_handle_ini):
    """测试目的：验证当 pytest.ini 存在 [pytest] 和 addopts 时，能正确解析并返回列表"""
    mock_instance = mock_handle_ini.return_value
    mock_instance.get.return_value = "-s -v --custom-opt value"
    
    result = args._get_pytest_ini()
    
    expected = ["-s", "-v", "--custom-opt", "value"]
    assert result == expected
    mock_handle_ini.assert_called_once_with(args.PYTEST_INI_DIR)
    mock_instance.get.assert_called_once_with('pytest', 'addopts')

@patch('aomaker.runner.args.HandleIni')
def test_get_pytest_ini_no_addopts(mock_handle_ini):
    """测试目的：验证当 pytest.ini 中没有 addopts 选项时，返回空列表"""
    mock_instance = mock_handle_ini.return_value
    mock_instance.get.side_effect = NoOptionError('addopts', 'pytest') # 模拟抛出异常
    
    result = args._get_pytest_ini()
    
    assert result == []
    mock_handle_ini.assert_called_once_with(args.PYTEST_INI_DIR)
    mock_instance.get.assert_called_once_with('pytest', 'addopts')

@patch('aomaker.runner.args.HandleIni')
def test_get_pytest_ini_empty_addopts(mock_handle_ini):
    """测试目的：验证当 pytest.ini 中 addopts 为空字符串时，返回空列表"""
    mock_instance = mock_handle_ini.return_value
    mock_instance.get.return_value = "" # addopts 为空
    
    result = args._get_pytest_ini()
    
    assert result == []
    mock_handle_ini.assert_called_once_with(args.PYTEST_INI_DIR)
    mock_instance.get.assert_called_once_with('pytest', 'addopts')


@patch('aomaker.runner.args.os.path.isdir')
@patch('aomaker.runner.args.os.path.join', side_effect=lambda *parts: "/".join(parts)) # 模拟 join
@patch('aomaker.runner.args.os.listdir')
def test_make_testsuite_path_mixed_content(mock_listdir, mock_join, mock_isdir):
    """测试目的：验证在混合内容目录下，只返回子目录路径列表，并忽略 __ 开头的项"""
    mock_listdir.return_value = ["subdir1", "file1.py", "__pycache__", "subdir2", ".DS_Store"]
    def isdir_side_effect(path):
        return path in ["test/base/path/subdir1", "test/base/path/subdir2"]
    mock_isdir.side_effect = isdir_side_effect
    
    base_path = "test/base/path"
    result = args.make_testsuite_path(base_path)
    
    expected = ["test/base/path/subdir1", "test/base/path/subdir2"]
    assert sorted(result) == sorted(expected)
    mock_listdir.assert_called_once_with(base_path)
    assert mock_join.call_count == 4
    assert mock_isdir.call_count == 4

@patch('aomaker.runner.args.os.path.isdir')
@patch('aomaker.runner.args.os.path.join', side_effect=lambda *parts: "/".join(parts))
@patch('aomaker.runner.args.os.listdir')
def test_make_testsuite_path_only_files(mock_listdir, mock_join, mock_isdir):
    """测试目的：验证在只有文件的目录下，返回空列表"""
    mock_listdir.return_value = ["file1.py", "file2.txt"]
    mock_isdir.return_value = False 
    
    base_path = "test/files/only"
    result = args.make_testsuite_path(base_path)
    
    assert result == []
    mock_listdir.assert_called_once_with(base_path)
    assert mock_isdir.call_count == 2

@patch('aomaker.runner.args.os.listdir')
def test_make_testsuite_path_empty_dir(mock_listdir):
    """测试目的：验证在空目录下，返回空列表"""
    mock_listdir.return_value = []
    
    base_path = "test/empty"
    result = args.make_testsuite_path(base_path)
    
    assert result == []
    mock_listdir.assert_called_once_with(base_path)


@patch('aomaker.runner.args.os.path.isfile')
@patch('aomaker.runner.args.os.path.join', side_effect=lambda *parts: "/".join(parts)) # 模拟 join
@patch('aomaker.runner.args.os.listdir')
def test_make_testfile_path_mixed_content(mock_listdir, mock_join, mock_isfile):
    """测试目的：验证在混合内容目录下，仅返回符合 pytest 测试文件规则的 .py 文件"""
    mock_listdir.return_value = ["subdir1", "file1.py", "__pycache__", "test_alpha.py", "beta_test.py", "README.md"]
    def isfile_side_effect(path):
        return any(path.endswith(name) for name in ["file1.py", "test_alpha.py", "beta_test.py", "README.md"])
    mock_isfile.side_effect = isfile_side_effect

    base_path = "test/base/path"
    result = args.make_testfile_path(base_path)
    
    expected = ["test/base/path/test_alpha.py", "test/base/path/beta_test.py"]
    assert sorted(result) == sorted(expected)
    mock_listdir.assert_called_once_with(base_path)
    assert mock_join.call_count == 5
    assert mock_isfile.call_count == 5

@patch('aomaker.runner.args.os.path.isfile')
@patch('aomaker.runner.args.os.path.join', side_effect=lambda *parts: "/".join(parts))
@patch('aomaker.runner.args.os.listdir')
def test_make_testfile_path_only_dirs(mock_listdir, mock_join, mock_isfile):
    """测试目的：验证在只有目录的目录下，返回空列表"""
    mock_listdir.return_value = ["dir1", "dir2"]
    mock_isfile.return_value = False
    
    base_path = "test/dirs/only"
    result = args.make_testfile_path(base_path)
    
    assert result == []
    mock_listdir.assert_called_once_with(base_path)
    assert mock_isfile.call_count == 2

@patch('aomaker.runner.args.os.listdir')
def test_make_testfile_path_empty_dir(mock_listdir):
    """测试目的：验证在空目录下，返回空列表"""
    mock_listdir.return_value = []
    
    base_path = "test/empty"
    result = args.make_testfile_path(base_path)
    
    assert result == []
    mock_listdir.assert_called_once_with(base_path)


def test_make_args_group_basic():
    """测试目的：验证基本的参数组合功能，返回生成器"""
    task_args_list = ['test_a.py', 'test_b.py::TestClass', '-m "smoke or regression"']
    extra_args = ['-s', '--alluredir=results']
    
    result_generator = args.make_args_group(task_args_list, extra_args)
    result_list = list(result_generator)
    
    expected = [
        ['test_a.py', '-s', '--alluredir=results'],
        ['test_b.py::TestClass', '-s', '--alluredir=results'],
        ['-m "smoke or regression"', '-s', '--alluredir=results']
    ]
    assert result_list == expected

def test_make_args_group_empty_extra():
    """测试目的：验证当 extra_pytest_args 为空列表时，只包含 task arg"""
    task_args_list = ['test_c.py']
    extra_args = []
    
    result_generator = args.make_args_group(task_args_list, extra_args)
    result_list = list(result_generator)
    
    expected = [
        ['test_c.py']
    ]
    assert result_list == expected

def test_make_args_group_empty_tasks():
    """测试目的：验证当 task_args 为空列表时，生成器不产生任何值"""
    task_args_list = []
    extra_args = ['-v']
    
    result_generator = args.make_args_group(task_args_list, extra_args)
    result_list = list(result_generator)
    
    expected = []
    assert result_list == expected