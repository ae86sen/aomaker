# tests/conftest.py
import pytest
import importlib
from pathlib import Path
import sys
from typing import Optional, Union, Dict, Any # Added for type hinting

# 确保 aomaker 目录在 sys.path 中
project_root_dir = Path(__file__).parent.parent
if str(project_root_dir) not in sys.path:
    sys.path.insert(0, str(project_root_dir))

# --- 顶层补丁逻辑 ---

# 1a. Patch find_project_root
import aomaker.database.sqlite
print("\n[INFO][TopLevel] Patching find_project_root...")
_original_find_project_root = aomaker.database.sqlite.find_project_root
def _find_project_root_mock(start_path: Path) -> Path:
    return Path.cwd()
aomaker.database.sqlite.find_project_root = _find_project_root_mock
print("[INFO][TopLevel] Patched find_project_root.")

# 1b. Patch load_middleware_config
#     先导入 registry 模块，以便后续 patch
import aomaker.core.middlewares.registry
print("[INFO][TopLevel] Patching load_middleware_config...")
_original_load_middleware_config = aomaker.core.middlewares.registry.load_middleware_config
def _load_middleware_config_mock(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    # 返回空字典，模拟无配置文件
    return {
        'logging_middleware': {
            'priority': 1000,
            'enabled': True
        }
    }
aomaker.core.middlewares.registry.load_middleware_config = _load_middleware_config_mock
print("[INFO][TopLevel] Patched load_middleware_config.")


# 2. 重新加载依赖模块 (顺序很重要，但不 reload registry)
try:
    print("[INFO][TopLevel] Reloading dependent modules (excluding registry)...")
    # Reload storage (depends on find_project_root patch)
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

# --- 其他 Fixtures ---

@pytest.fixture(autouse=True)
def clear_middlewares_and_client(request):
    """
    每个测试函数运行前后，自动清空中间件和 get_http_client 单例。
    """
    # print(f"[DEBUG] Running clear setup for {request.node.name}")
    # 导入 registry 时，它使用的是我们 patch 后的 load_middleware_config
    from aomaker.core.middlewares.registry import registry
    from aomaker.core.http_client import get_http_client # 导入的是 reload 后的版本


    if hasattr(registry, 'middleware_configs'): # 清理已注册的配置
        registry.middleware_configs.clear()
    if hasattr(registry, 'active_middlewares'): # 清理活动列表
         registry.active_middlewares.clear()

    # 清理 get_http_client 的单例缓存
    if hasattr(get_http_client, 'client'):
        delattr(get_http_client, 'client')


    yield

    if hasattr(registry, 'middleware_configs'):
        registry.middleware_configs.clear()
    if hasattr(registry, 'active_middlewares'):
        registry.active_middlewares.clear()
    if hasattr(get_http_client, 'client'):
        delattr(get_http_client, 'client')

