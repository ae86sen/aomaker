import pytest
import yaml
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path


from aomaker.core.middlewares.registry import (
    MiddlewareConfig,
    middleware,
    registry as global_registry,
    apply_middleware_config,
    init_middlewares,
)

try:
    from aomaker.core.middlewares import logging_middleware
except ImportError:
    logging_middleware = MagicMock()
    logging_middleware.structured_logging_middleware = MagicMock(__name__="mocked_logging")

MIDDLEWARE_CONFIG_PATH = Path("./middleware.yaml")
MIDDLEWARES_DIR = Path("./middlewares")


# --- Helper Functions & Fixtures ---

@middleware(name="mw_high", priority=100)
async def sample_middleware_high(request, call_next):
    pass

@middleware(name="mw_low", priority=10, enabled=False)
async def sample_middleware_low(request, call_next):
    pass

@middleware(name="mw_default") # Default priority 0, enabled=True
async def sample_middleware_default(request, call_next):
    pass

@middleware(name="mw_options", options={"key": "value"})
async def sample_middleware_with_options(request, call_next):
    pass

async def non_middleware_func(request, call_next):
    pass # Not decorated

@pytest.fixture(autouse=True)
def fresh_registry():
    """
    Provides a clean global registry state for each test.
    Using autouse=True to apply it automatically.
    """
    original_configs = global_registry.middleware_configs.copy()
    original_active = global_registry.active_middlewares.copy()
    global_registry.middleware_configs.clear()
    global_registry.active_middlewares.clear()
    yield global_registry
    global_registry.middleware_configs = original_configs
    global_registry.active_middlewares = original_active
    global_registry._rebuild_active_middlewares() # Ensure active list is correct

# --- Test Cases ---

def test_middleware_decorator():
    """测试 @middleware 装饰器是否正确附加配置."""
    assert hasattr(sample_middleware_high, 'middleware_config')
    config = getattr(sample_middleware_high, 'middleware_config')
    assert config == {
        "name": "mw_high",
        "enabled": True,
        "priority": 100,
        "options": {}
    }

    assert hasattr(sample_middleware_low, 'middleware_config')
    config_low = getattr(sample_middleware_low, 'middleware_config')
    assert config_low == {
        "name": "mw_low",
        "enabled": False,
        "priority": 10,
        "options": {}
    }

    assert hasattr(sample_middleware_default, 'middleware_config')
    config_default = getattr(sample_middleware_default, 'middleware_config')
    assert config_default == {
        "name": "mw_default",
        "enabled": True,
        "priority": 0,
        "options": {}
    }

    assert hasattr(sample_middleware_with_options, 'middleware_config')
    config_options = getattr(sample_middleware_with_options, 'middleware_config')
    assert config_options == {
        "name": "mw_options",
        "enabled": True,
        "priority": 0,
        "options": {"options": {"key": "value"}}
    }

    assert not hasattr(non_middleware_func, 'middleware_config')

def test_registry_register_manual(fresh_registry):
    """测试 register 的默认行为和显式 override。"""
    reg = fresh_registry

    # 1) 默认注册：key=函数名，priority 默认 0
    reg.register(sample_middleware_high)
    assert "sample_middleware_high" in reg.middleware_configs
    cfg1 = reg.middleware_configs["sample_middleware_high"]
    assert cfg1.enabled is True
    assert cfg1.priority == 0

    # 2) override name/priority/options
    reg.register(
        sample_middleware_low,
        name="low_mw",
        enabled=True,
        priority=10,
        options={"foo": "bar"}
    )
    assert "low_mw" in reg.middleware_configs
    cfg2 = reg.middleware_configs["low_mw"]
    assert cfg2.enabled is True
    assert cfg2.priority == 10
    assert cfg2.options == {"foo": "bar"}

    # 3) 只 override name 和 priority（enabled 用默认 True）
    reg.register(sample_middleware_default, name="override_default", priority=50)
    assert "override_default" in reg.middleware_configs
    cfg3 = reg.middleware_configs["override_default"]
    assert cfg3.enabled is True
    assert cfg3.priority == 50

    # 激活列表按 priority 降序
    assert reg.get_middlewares() == [
        sample_middleware_default,  # prio 50
        sample_middleware_low,      # prio 10
        sample_middleware_high      # prio  0
    ]

def test_registry_rebuild_active_middlewares(fresh_registry):
    """测试 _rebuild_active_middlewares 的排序和过滤逻辑."""
    reg = fresh_registry
    reg.middleware_configs = {
        "mw_high": MiddlewareConfig(name="mw_high", middleware=sample_middleware_high, enabled=True, priority=100),
        "mw_low": MiddlewareConfig(name="mw_low", middleware=sample_middleware_low, enabled=False, priority=10),
        "mw_default": MiddlewareConfig(name="mw_default", middleware=sample_middleware_default, enabled=True, priority=0),
        "mw_another": MiddlewareConfig(name="mw_another", middleware=non_middleware_func, enabled=True, priority=100), # Same priority as mw_high
    }

    reg._rebuild_active_middlewares()
    # 过滤掉 mw_low，再按 priority 降序，同 priority 保留字典插入顺序
    active = reg.get_middlewares()
    assert active == [
        sample_middleware_high,  # mw_high, prio=100
        non_middleware_func,     # mw_ano,  prio=100
        sample_middleware_default # mw_def, prio=0
    ]

def test_registry_enable_disable_priority(fresh_registry):
    """测试启用、禁用和设置优先级."""
    reg = fresh_registry
    reg.register(sample_middleware_high)
    reg.register(sample_middleware_default)

    # 初始按 priority(都0)，保留插入顺序
    assert reg.get_middlewares() == [sample_middleware_high, sample_middleware_default]

    # Disable sample_middleware_high
    reg.disable("sample_middleware_high")
    # 现在只剩下 default
    assert reg.get_middlewares() == [sample_middleware_default]
    assert reg.middleware_configs["sample_middleware_high"].enabled is False

    # Enable it again
    reg.enable("sample_middleware_high")
    assert reg.get_middlewares() == [sample_middleware_high, sample_middleware_default]
    assert reg.middleware_configs["sample_middleware_high"].enabled is True

    # Change priority
    reg.set_priority("sample_middleware_high", -10)
    # priority=-10，default(0)排在前面
    assert reg.get_middlewares() == [sample_middleware_default, sample_middleware_high]
    assert reg.middleware_configs["sample_middleware_high"].priority == -10

def test_registry_apply_config(fresh_registry):
    """测试应用配置字典."""
    reg = fresh_registry
    # 显式把 decorator 上的 name/enabled/priority/options 传给 register
    reg.register(sample_middleware_high,       **sample_middleware_high.middleware_config)
    reg.register(sample_middleware_low,        **sample_middleware_low.middleware_config)
    reg.register(sample_middleware_with_options, **sample_middleware_with_options.middleware_config)

    initial_active = reg.get_middlewares()
    # low 是 disabled，只有 high + options 两条
    assert initial_active == [sample_middleware_high, sample_middleware_with_options]

    config_updates = {
        "mw_high": {"enabled": False, "priority": 5}, # Disable, change priority
        "mw_low":  {"enabled": True},
        "mw_options": {"priority": 200, "options": {"new_key": 123}},
        "non_existent": {"enabled": True} # Should be ignored
    }

    reg.apply_config(config_updates)

    assert reg.middleware_configs["mw_high"].enabled is False
    assert reg.middleware_configs["mw_high"].priority == 5
    assert reg.middleware_configs["mw_low"].enabled is True
    assert reg.middleware_configs["mw_low"].priority == 10 # Original priority retained if not in update
    assert reg.middleware_configs["mw_options"].enabled is True
    assert reg.middleware_configs["mw_options"].priority == 200
    assert reg.middleware_configs["mw_options"].options == {"new_key": 123} # Options replaced
    assert "non_existent" not in reg.middleware_configs

    # Verify active list
    new_active = reg.get_middlewares()
    assert len(new_active) == 2
    assert new_active[0] is sample_middleware_with_options # New highest priority
    assert new_active[1] is sample_middleware_low # Now enabled

def test_load_middleware_config(tmp_path):
    """测试从 YAML 加载配置."""
    import importlib
    import aomaker.core.middlewares.registry as reg_mod
    importlib.reload(reg_mod)

    default_config_path = tmp_path / "default_middleware.yaml"
    expected_config = {"mw1": {"enabled": False}}
    default_config_path.write_text(yaml.dump(expected_config))

    with patch('aomaker.core.middlewares.registry.MIDDLEWARE_CONFIG_PATH', default_config_path):
        # 直接调用 reload 后的函数
        config = reg_mod.load_middleware_config()
    assert config == expected_config

    # 2. Test with specific path
    custom_path = tmp_path / "custom_mw.yaml"
    expected_config_custom = {"mw2": {"priority": 50}}
    custom_path.write_text(yaml.dump(expected_config_custom))

    config_custom = reg_mod.load_middleware_config(custom_path)
    assert config_custom == expected_config_custom

def test_apply_middleware_config_calls_registry(fresh_registry):
    """测试 apply_middleware_config 是否调用 registry.apply_config."""
    test_config = {"mw1": {"enabled": True}}
    with patch('aomaker.core.middlewares.registry.registry.apply_config') as mock_apply:
        apply_middleware_config(test_config)
        mock_apply.assert_called_once_with(test_config)

    with patch('aomaker.core.middlewares.registry.registry.apply_config') as mock_apply_none:
        apply_middleware_config(None)
        apply_middleware_config({})
        mock_apply_none.assert_not_called()

# --- scan_middlewares tests ---


@pytest.fixture(scope="function")
def dummy_middleware_package(tmp_path):
    """Creates a temporary directory structure for middleware scanning tests."""
    pkg_dir = tmp_path / "scan_test_pkg"
    sub_dir = pkg_dir / "subpackage"
    pkg_dir.mkdir(exist_ok=True)
    sub_dir.mkdir(exist_ok=True)
    pkg_name = "scan_test_pkg"

    (pkg_dir / "__init__.py").touch()
    (sub_dir / "__init__.py").touch()


    (pkg_dir / "mw_a.py").write_text(f"""
from aomaker.core.middlewares.registry import middleware
@middleware(name='MW_A', priority=10)
async def middleware_a(r, c): pass

# A non-middleware func
async def helper_a(r, c): pass
""")


    (sub_dir / "mw_b.py").write_text(f"""
from aomaker.core.middlewares.registry import middleware
@middleware(name='MW_B', enabled=False)
async def middleware_b(r, c): pass

@middleware(name='MW_C', priority=-5)
async def middleware_c(r, c): pass
""")

    (pkg_dir / "utils.py").write_text("def helper(): pass")

    (pkg_dir / "bad_import.py").write_text("import non_existent_module")


    sys.path.insert(0, str(tmp_path))

    yield pkg_name

    sys.path.pop(0)
    modules_to_remove = [m for m in sys.modules if m.startswith(pkg_name)]
    for mod_name in modules_to_remove:
        del sys.modules[mod_name]


def test_registry_scan_middlewares(fresh_registry, dummy_middleware_package):
    """测试扫描和注册包中的中间件."""
    reg = fresh_registry
    package_name = dummy_middleware_package

    with patch('builtins.print') as mock_print:
        reg.scan_middlewares(package_name)

    assert "MW_A" in reg.middleware_configs
    assert "MW_B" in reg.middleware_configs
    assert "MW_C" in reg.middleware_configs
    assert len(reg.middleware_configs) == 3


    assert reg.middleware_configs["MW_A"].enabled is True
    assert reg.middleware_configs["MW_A"].priority == 10
    assert reg.middleware_configs["MW_B"].enabled is False # From decorator
    assert reg.middleware_configs["MW_B"].priority == 0
    assert reg.middleware_configs["MW_C"].enabled is True
    assert reg.middleware_configs["MW_C"].priority == -5


    active = reg.get_middlewares()
    assert len(active) == 2 # MW_B is disabled
    assert active[0].__name__ == "middleware_a" # Priority 10
    assert active[1].__name__ == "middleware_c" # Priority -5

 
@patch('aomaker.core.middlewares.registry.register_internal_middlewares')
@patch('aomaker.core.middlewares.registry.MiddlewareRegistry.scan_middlewares')
@patch('aomaker.core.middlewares.registry.load_middleware_config')
@patch('aomaker.core.middlewares.registry.apply_middleware_config')
@patch('aomaker.core.middlewares.registry.os.path.exists')
def test_init_middlewares_flow(
    mock_exists,
    mock_apply_config,
    mock_load_config,
    mock_scan,
    mock_register_internal,
    fresh_registry # Ensure clean global registry
):
    """测试 init_middlewares 的调用流程."""
    # Arrange
    mock_exists.return_value = True 
    mock_load_config.return_value = {"some_config": True}
    with patch('aomaker.core.middlewares.registry.MIDDLEWARES_DIR', Path("./mock_middlewares_dir")):
        mock_exists.return_value = True

        init_middlewares()

        mock_register_internal.assert_called_once()
        mock_exists.assert_called_once_with(Path("./mock_middlewares_dir"))
        mock_scan.assert_called_once_with("middlewares")
        mock_load_config.assert_called_once_with()
        mock_apply_config.assert_called_once_with({"some_config": True})

@patch('aomaker.core.middlewares.registry.register_internal_middlewares')
@patch('aomaker.core.middlewares.registry.MiddlewareRegistry.scan_middlewares')
@patch('aomaker.core.middlewares.registry.load_middleware_config')
@patch('aomaker.core.middlewares.registry.apply_middleware_config')
@patch('aomaker.core.middlewares.registry.os.path.exists')
def test_init_middlewares_no_scan_dir(
    mock_exists,
    mock_apply_config,
    mock_load_config,
    mock_scan,
    mock_register_internal,
    fresh_registry
):
    """测试当 MIDDLEWARES_DIR 不存在时不调用 scan."""
    # Arrange
    mock_load_config.return_value = {}
    with patch('aomaker.core.middlewares.registry.MIDDLEWARES_DIR', Path("./non_existent_dir")) as mock_dir_path:
        mock_exists.return_value = False

        # Act
        init_middlewares()

        # Assert
        mock_register_internal.assert_called_once()
        mock_exists.assert_called_once_with(mock_dir_path)
        mock_scan.assert_not_called() # Scan should not be called
        mock_load_config.assert_called_once_with()
        mock_apply_config.assert_called_once_with({}) 