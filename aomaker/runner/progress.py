# --coding:utf-8--
from aomaker.storage import cache

def _progress_init(pytest_args: list):
    if len(pytest_args) > 0:
        cache.set(f"_progress.{cache.worker}", {"target": pytest_args[0], "total": 0, "completed": 0})