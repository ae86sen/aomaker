from unittest.mock import patch, MagicMock, call

from aomaker.runner import run_tests
from aomaker.runner.models import RunConfig

MockProcessesRunnerClass = MagicMock(name='MockProcessesRunnerClass')
MockThreadsRunnerClass = MagicMock(name='MockThreadsRunnerClass')
MockBaseRunnerClass = MagicMock(name='MockBaseRunnerClass')

MockProcessRunnerInstance = MockProcessesRunnerClass.return_value
MockThreadRunnerInstance = MockThreadsRunnerClass.return_value
MockBaseRunnerInstance = MockBaseRunnerClass.return_value


@patch('aomaker.runner.runner_context')
@patch.dict('aomaker.runner.RUN_MODE_MAP', {
    'mp': MockProcessesRunnerClass,
    'mt': MockThreadsRunnerClass,
    'main': MockBaseRunnerClass
}, clear=True)
def test_run_tests_mp_mode(mock_runner_context):
    """验证 run_tests 在 run_mode='mp' 时调用 ProcessesRunner 的 mock"""
    MockProcessesRunnerClass.reset_mock()
    MockProcessRunnerInstance.reset_mock()
    MockThreadsRunnerClass.reset_mock()
    MockBaseRunnerClass.reset_mock()

    run_config = RunConfig(run_mode='mp', task_args=['a'])

    run_tests(run_config)

    mock_runner_context.assert_called_once_with(run_config)
    MockProcessesRunnerClass.assert_called_once_with()
    MockProcessRunnerInstance.run.assert_called_once_with(run_config)
    MockThreadsRunnerClass.assert_not_called()
    MockBaseRunnerClass.assert_not_called()


@patch('aomaker.runner.runner_context')
@patch.dict('aomaker.runner.RUN_MODE_MAP', {
    'mp': MockProcessesRunnerClass,
    'mt': MockThreadsRunnerClass,
    'main': MockBaseRunnerClass
}, clear=True)
def test_run_tests_mt_mode(mock_runner_context):
    """验证 run_tests 在 run_mode='mt' 时调用 ThreadsRunner 的 mock"""
    MockProcessesRunnerClass.reset_mock()
    MockThreadsRunnerClass.reset_mock()
    MockThreadRunnerInstance.reset_mock()
    MockBaseRunnerClass.reset_mock()

    run_config = RunConfig(run_mode='mt', task_args=['a'])

    run_tests(run_config)

    mock_runner_context.assert_called_once_with(run_config)
    MockThreadsRunnerClass.assert_called_once_with()
    MockThreadRunnerInstance.run.assert_called_once_with(run_config)
    MockProcessesRunnerClass.assert_not_called()
    MockBaseRunnerClass.assert_not_called()


@patch('aomaker.runner.runner_context')
@patch.dict('aomaker.runner.RUN_MODE_MAP', {
    'mp': MockProcessesRunnerClass,
    'mt': MockThreadsRunnerClass,
    'main': MockBaseRunnerClass
}, clear=True)
@patch('aomaker.runner.Runner', new=MockBaseRunnerClass) # Patch default lookup too
def test_run_tests_main_mode(mock_runner_context):
    """验证 run_tests 在 run_mode='main' 时调用 base.Runner 的 mock"""
    MockProcessesRunnerClass.reset_mock()
    MockThreadsRunnerClass.reset_mock()
    MockBaseRunnerClass.reset_mock()
    MockBaseRunnerInstance.reset_mock()

    run_config = RunConfig(run_mode='main')

    run_tests(run_config)

    mock_runner_context.assert_called_once_with(run_config)
    MockBaseRunnerClass.assert_called_once_with()
    MockBaseRunnerInstance.run.assert_called_once_with(run_config)
    MockProcessesRunnerClass.assert_not_called()
    MockThreadsRunnerClass.assert_not_called()


@patch('aomaker.runner.runner_context')
@patch.dict('aomaker.runner.RUN_MODE_MAP', {
    'mp': MockProcessesRunnerClass,
    'mt': MockThreadsRunnerClass,
    'main': MockBaseRunnerClass
}, clear=True)
@patch('aomaker.runner.Runner', new=MockBaseRunnerClass) # Patch default lookup
def test_run_tests_context_management(mock_runner_context):
    """验证 Runner 实例化和 run 调用发生在 runner_context 内部 (使用 main 模式)"""
    MockBaseRunnerClass.reset_mock()
    MockBaseRunnerInstance.reset_mock() 
    MockBaseRunnerInstance.run.reset_mock() 

    run_config = RunConfig() 

    context_manager_mock = MagicMock()
    mock_runner_context.return_value = context_manager_mock

    call_order = MagicMock()
    context_manager_mock.__enter__.side_effect = lambda: call_order.__enter__()
    context_manager_mock.__exit__.side_effect = lambda exc_type, exc_val, exc_tb: call_order.__exit__(exc_type, exc_val, exc_tb)

    def mock_runner_init_side_effect():
        call_order.Runner_init() 
        return MockBaseRunnerInstance

    def mock_runner_run_side_effect(cfg):
        call_order.runner_run(cfg)
        return None

    MockBaseRunnerClass.side_effect = mock_runner_init_side_effect
    MockBaseRunnerInstance.run.side_effect = mock_runner_run_side_effect

    run_tests(run_config)

    expected_calls = [
        call.__enter__(),
        call.Runner_init(),
        call.runner_run(run_config),
        call.__exit__(None, None, None)
    ]
    call_order.assert_has_calls(expected_calls)

    context_manager_mock.__enter__.assert_called_once()
    context_manager_mock.__exit__.assert_called_once()
    MockBaseRunnerClass.assert_called_once()
    MockBaseRunnerInstance.run.assert_called_once_with(run_config)
