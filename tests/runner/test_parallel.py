from unittest.mock import patch, MagicMock


from aomaker.runner.parallel import ProcessesRunner, ThreadsRunner, main_task, ALL_COMPLETED
from aomaker.runner.models import RunConfig


def test_max_process_count_and_calculate(monkeypatch):
    """测试目的：验证 max_process_count 属性和 _calculate_process_count 行为"""
    monkeypatch.setattr('os.cpu_count', lambda: 4)
    runner = ProcessesRunner()
    assert runner.max_process_count == 4

    small_args = ['a', 'b']
    assert runner._calculate_process_count(small_args) == 2
    large_args = list(range(10))
    assert runner._calculate_process_count(large_args) == 4


@patch('aomaker.runner.parallel.ProcessesRunner._execute_tasks')
@patch('aomaker.runner.parallel.ProcessesRunner._calculate_process_count', return_value=3)
@patch('aomaker.runner.parallel.print_message')
def test_processes_runner_run_without_specified_processes(mock_print, mock_calc, mock_exec):
    """测试目的：验证多进程模式下，当未指定 processes 时，使用 _calculate_process_count"""
    runner = ProcessesRunner()
    runner._prepare_extra_args = MagicMock(return_value=['E1'])
    runner._prepare_task_args = MagicMock(return_value=['t1', 't2', 't3'])
    runner.pytest_plugins = [MagicMock(__name__='p1'), MagicMock(__name__='p2')]
    run_config = RunConfig(run_mode='mp', pytest_args=['-A'], task_args=['a', 'b', 'c'], processes=None)

    runner.run(run_config)

    mock_print.assert_called_once_with("🚀多进程模式准备启动...")
    mock_calc.assert_called_once_with(['t1', 't2', 't3'])
    mock_exec.assert_called_once_with(3, ['t1', 't2', 't3'], ['E1'], ['p1', 'p2'])


@patch('aomaker.runner.parallel.ProcessesRunner._execute_tasks')
@patch('aomaker.runner.parallel.print_message')
def test_processes_runner_run_with_specified_processes(mock_print, mock_exec, monkeypatch):
    """测试目的：验证多进程模式下，当指定 processes 时，使用 min(processes, len(task_args), max_process_count)"""
    monkeypatch.setattr('os.cpu_count', lambda: 5)
    runner = ProcessesRunner()
    runner._prepare_extra_args = MagicMock(return_value=['E2'])
    runner._prepare_task_args = MagicMock(return_value=['x1', 'x2', 'x3', 'x4'])
    runner.pytest_plugins = [MagicMock(__name__='pX')]
    run_config = RunConfig(run_mode='mp', pytest_args=[], task_args=['a', 'b', 'c', 'd'], processes=10)

    runner.run(run_config)

    mock_exec.assert_called_once_with(4, ['x1', 'x2', 'x3', 'x4'], ['E2'], ['pX'])


@patch('aomaker.runner.parallel.make_args_group', return_value=[['R1'], ['R2']])
@patch('aomaker.runner.parallel.wait')
@patch('aomaker.runner.parallel.ThreadPoolExecutor')
@patch('aomaker.runner.parallel.print_message')
def test_threads_runner_run(mock_print, mock_tpe, mock_wait, mock_make_args_group):
    """测试目的：验证多线程模式下，能按任务数量启动线程池并提交 main_task"""
    runner = ThreadsRunner()
    runner._prepare_extra_args = MagicMock(return_value=['EX'])
    runner._prepare_task_args = MagicMock(return_value=['job1', 'job2'])
    runner.pytest_plugins = [MagicMock(__name__='A1'), MagicMock(__name__='A2')]
    run_config = RunConfig(run_mode='mt', pytest_args=['-X'], task_args=['job1', 'job2'])

    executor = mock_tpe.return_value
    fake_futures = [MagicMock(), MagicMock()]
    executor.submit.side_effect = fake_futures

    runner.run(run_config)

    mock_print.assert_called_once_with("🚀多线程模式准备启动...")
    mock_tpe.assert_called_once_with(max_workers=2)

    assert executor.submit.call_count == 2
    plugin_names = ['A1', 'A2']
    executor.submit.assert_any_call(main_task, ['R1'], plugin_names)
    executor.submit.assert_any_call(main_task, ['R2'], plugin_names)

    mock_wait.assert_called_once_with(fake_futures, return_when=ALL_COMPLETED)
    executor.shutdown.assert_called_once() 