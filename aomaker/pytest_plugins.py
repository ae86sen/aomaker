# --coding:utf-8--
from aomaker.storage import cache

deselected_cases = 0


def pytest_configure(config):
    config.total_cases = 0
    config.completed_cases = 0
    config.selected_cases = 0
    config.deselected_cases = 0


def pytest_collection_modifyitems(config, items):
    config.total_cases = len(items)


def pytest_deselected(items):
    global deselected_cases
    deselected_cases = len(items)


def pytest_runtest_teardown(item, nextitem):
    item.config.completed_cases += 1
    completed = item.config.completed_cases
    total = item.config.total_cases - deselected_cases
    progress = (completed / total) * 100
    progress_name = f"_progress.{cache.worker}"
    progress_info = {"total": total, "completed": completed}
    # execute = cache.update if cache.get(progress_name) else cache.set
    cache.upsert(progress_name,progress_info)
    print(f"Test Progress: {completed}/{total} cases completed ({progress:.2f}%)")

