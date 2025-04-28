import pytest
from unittest.mock import patch, MagicMock

from aomaker.runner.base import Runner
from aomaker.runner.models import RunConfig
from aomaker import pytest_plugins as aomaker_pytest_plugins
from aomaker.path import ALLURE_JSON_DIR as AOMAKER_ALLURE_JSON_DIR


@patch('aomaker.runner.base.aomaker_logger')
@patch('aomaker.runner.base.pytest_plugins', new_callable=MagicMock)
@patch.dict('aomaker.runner.base.__dict__', {'ALLURE_JSON_DIR': '/mocked/allure/dir'})
def test_runner_init_defaults(mock_plugins_module, mock_logger):
    """测试目的：验证 Runner 初始化时，默认参数、插件和日志配置是否正确（非多进程模式）"""
    mock_plugins_module.__name__ = 'aomaker.pytest_plugins'

    runner = Runner(is_processes=False)

    expected_default_args = [
        "-s",
        f"--alluredir=/mocked/allure/dir", 
        "--show-capture=no",
        "--log-format=%(asctime)s %(message)s",
        "--log-date-format=%Y-%m-%d %H:%M:%S"
    ]
    assert runner.pytest_args == expected_default_args
    assert runner.pytest_plugins == [mock_plugins_module]

    mock_logger.allure_handler.assert_called_once_with("debug", is_processes=False)

@patch('aomaker.runner.base.aomaker_logger')
@patch('aomaker.runner.base.pytest_plugins', new_callable=MagicMock)
@patch.dict('aomaker.runner.base.__dict__', {'ALLURE_JSON_DIR': '/mocked/allure/dir'})
def test_runner_init_is_processes_true(mock_plugins_module, mock_logger):
    """测试目的：验证 Runner 初始化时，当 is_processes=True 时，日志配置正确"""
    mock_plugins_module.__name__ = 'aomaker.pytest_plugins'

    runner = Runner(is_processes=True)

    mock_logger.allure_handler.assert_called_once_with("debug", is_processes=True)



@patch('aomaker.runner.base.pytest.main')
@patch('aomaker.runner.base._progress_init')
@patch('aomaker.runner.base._get_pytest_ini')
@patch('aomaker.runner.base.print_message')
@patch.dict('aomaker.runner.base.__dict__', {'ALLURE_JSON_DIR': '/mocked/allure/run'})
def test_runner_run_calls_pytest_main(mock_print, mock_get_ini, mock_progress, mock_pytest_main):
    """测试目的：验证 runner.run() 是否正确调用 pytest.main，并传入合并后的参数和插件"""
    mock_get_ini.return_value = ['--ini-opt']
    runner = Runner()
    runner.pytest_plugins = [aomaker_pytest_plugins]

    user_pytest_args = ['-k', 'my_test', '--custom-flag']
    run_config = RunConfig(pytest_args=user_pytest_args)

    runner.run(run_config)

    mock_get_ini.assert_called_once()
    expected_final_args_for_progress = user_pytest_args[:] + runner.pytest_args
    mock_progress.assert_called_once_with(expected_final_args_for_progress)


    mock_pytest_main.assert_called_once()
    call_args, call_kwargs = mock_pytest_main.call_args
    
    expected_final_args_for_pytest = user_pytest_args[:] + runner.pytest_args
    assert call_args[0] == expected_final_args_for_pytest

    assert 'plugins' in call_kwargs
    assert call_kwargs['plugins'] == runner.pytest_plugins


@pytest.fixture
def runner_instance():
    """提供一个 Runner 实例供测试使用"""
    with patch('aomaker.runner.base.aomaker_logger'):
        yield Runner()

@patch('aomaker.runner.base.make_testsuite_path')
@patch('aomaker.runner.base.make_testfile_path')
def test_make_task_args_dispatch(mock_mkfilepath, mock_mksuitepath, runner_instance):
    """测试目的：验证 make_task_args 根据类型正确分发并调用相应函数"""
    list_input = ['-m mark1', 'tests/specific_test.py']
    assert runner_instance.make_task_args(list_input) == list_input
    mock_mksuitepath.assert_not_called()
    mock_mkfilepath.assert_not_called()

    str_input = "tests/my_suite_dir"
    mock_mksuitepath.return_value = ["tests/my_suite_dir/subdir1"]
    assert runner_instance.make_task_args(str_input) == ["tests/my_suite_dir/subdir1"]
    mock_mksuitepath.assert_called_once_with(str_input)
    mock_mkfilepath.assert_not_called()
    mock_mksuitepath.reset_mock() # 重置 mock 以便下次断言

    dict_input = {"path": "tests/my_file_dir"}
    mock_mkfilepath.return_value = ["tests/my_file_dir/test_a.py"]
    assert runner_instance.make_task_args(dict_input) == ["tests/my_file_dir/test_a.py"]
    mock_mkfilepath.assert_called_once_with(dict_input["path"])
    mock_mksuitepath.assert_not_called()
    mock_mkfilepath.reset_mock()

    with pytest.raises(TypeError, match="arg type must be List or Path"):
         runner_instance.make_task_args(123)


def test_prepare_extra_args(runner_instance):
    """测试目的：验证 _prepare_extra_args 正确合并默认和额外参数"""
    default_args = runner_instance.pytest_args[:]

    assert runner_instance._prepare_extra_args(None) == default_args

    assert runner_instance._prepare_extra_args([]) == default_args

    extra = ['--new-opt', '-x']
    expected = extra + default_args 
    assert runner_instance._prepare_extra_args(extra) == expected


@patch.object(Runner, 'make_task_args', return_value=['processed_arg'])
def test_prepare_task_args_calls_make_task_args(mock_make_task_args, runner_instance):
    """测试目的：验证 _prepare_task_args 调用了 make_task_args"""
    input_args = "some/path"
    result = runner_instance._prepare_task_args(input_args)

    mock_make_task_args.assert_called_once_with(input_args)
    assert result == ['processed_arg']
