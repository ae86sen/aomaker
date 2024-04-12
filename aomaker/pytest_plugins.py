from aomaker.cache import cache, _get_worker

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
    worker = _get_worker()
    cache.set(f"_progress.{worker}", {"total": total, "completed": completed}, is_rewrite=True)
    print(f"Progress: {completed}/{total} tests completed ({progress:.2f}%)")


plugins = [pytest_configure, pytest_collection_modifyitems, pytest_deselected, pytest_runtest_teardown]
