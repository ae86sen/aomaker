# tests/conftest.py
import pytest
import importlib
from pathlib import Path
import sys
from typing import Optional, Union, Dict, Any
import os
import shutil

import aomaker.config_handlers
aomaker.config_handlers.ReadConfig.__init__ = lambda self, conf_name=None: None
aomaker.config_handlers.ReadConfig.conf = property(lambda self: {})

project_root_dir = Path(__file__).parent.parent
if str(project_root_dir) not in sys.path:
    sys.path.insert(0, str(project_root_dir))


import aomaker.database.sqlite
print("\n[INFO][TopLevel] Patching find_project_root...")
_original_find_project_root = aomaker.database.sqlite.find_project_root
def _find_project_root_mock(start_path: Path) -> Path:
    return Path.cwd()
aomaker.database.sqlite.find_project_root = _find_project_root_mock
print("[INFO][TopLevel] Patched find_project_root.")


import aomaker.core.middlewares.registry
print("[INFO][TopLevel] Patching load_middleware_config...")
_original_load_middleware_config = aomaker.core.middlewares.registry.load_middleware_config
def _load_middleware_config_mock(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    return {
        'logging_middleware': {
            'priority': 1000,
            'enabled': True
        }
    }
aomaker.core.middlewares.registry.load_middleware_config = _load_middleware_config_mock
print("[INFO][TopLevel] Patched load_middleware_config.")


try:
    print("[INFO][TopLevel] Reloading dependent modules (excluding registry)...")
    import aomaker.storage
    importlib.reload(aomaker.storage)
    print("[INFO][TopLevel] Reloaded aomaker.storage")

    import aomaker.core.http_client
    importlib.reload(aomaker.core.http_client)
    print("[INFO][TopLevel] Reloaded aomaker.core.http_client")

    print("[INFO][TopLevel] Module reloading complete.")
except Exception as e:
    print(f"\n[ERROR][TopLevel] Error reloading modules: {e}")
    raise ImportError(f"Failed to reload modules after patching: {e}") from e


@pytest.fixture(autouse=True)
def clear_middlewares_and_client(request):
    """
    每个测试函数运行前后，自动清空中间件和 get_http_client 单例。
    """

    from aomaker.core.middlewares.registry import registry
    from aomaker.core.http_client import get_http_client


    if hasattr(registry, 'middleware_configs'):
        registry.middleware_configs.clear()
    if hasattr(registry, 'active_middlewares'):
         registry.active_middlewares.clear()

    if hasattr(get_http_client, 'client'):
        delattr(get_http_client, 'client')


    yield

    if hasattr(registry, 'middleware_configs'):
        registry.middleware_configs.clear()
    if hasattr(registry, 'active_middlewares'):
        registry.active_middlewares.clear()
    if hasattr(get_http_client, 'client'):
        delattr(get_http_client, 'client')

@pytest.fixture(scope="session", autouse=True)
def manage_temp_dir():
    """
    在测试会话开始前准备 conf/config.yaml， database/ database.db
    结束后清理 conf 目录和 database 目录
    """
    conf_dir = os.path.join(os.getcwd(), 'conf')
    database_dir = os.path.join(os.getcwd(), 'database')
    report_dir = os.path.join(os.getcwd(), 'reports')
    os.makedirs(conf_dir, exist_ok=True)
    config_path = os.path.join(conf_dir, 'config.yaml')
    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("env: test\ntest: {}\n")
    yield
    if os.path.exists(conf_dir):
        shutil.rmtree(conf_dir)
    if os.path.exists(database_dir):
        shutil.rmtree(database_dir)
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)

