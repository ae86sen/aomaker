# --coding:utf-8--
from .base import Runner
from .parallel import ProcessesRunner, ThreadsRunner
from .models import RunConfig
from .context import runner_context


__all__ = [
    "Runner",
    "ProcessesRunner",
    "ThreadsRunner",
    "run",
    "threads_run",
    "processes_run",
    "run_tests",
    "RunConfig"
]

RUN_MODE_MAP = {
    "main": Runner,
    "mp": ProcessesRunner,
    "mt": ThreadsRunner
}

def run_tests(run_config: RunConfig):
    run_mode = RUN_MODE_MAP.get(run_config.run_mode, Runner)
    with runner_context(run_config):
        runner = run_mode()
        runner.run(run_config)

run = Runner().run
threads_run = ThreadsRunner().run
processes_run = ProcessesRunner().run