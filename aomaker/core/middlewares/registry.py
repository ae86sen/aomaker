# --coding:utf-8--
from typing import Callable, Dict, List, Any, TypeVar, Optional, Union
from importlib import import_module
import inspect
import pkgutil
import os
from functools import wraps
from pathlib import Path
import yaml
from pydantic import BaseModel, Field

from aomaker.path import MIDDLEWARE_CONFIG_PATH, MIDDLEWARES_DIR

RequestType = Dict[str, Any]
ResponseType = TypeVar('ResponseType')

CallNext = Callable[[RequestType], ResponseType]
MiddlewareCallable = Callable[[RequestType, CallNext], ResponseType]


class MiddlewareConfig(BaseModel):
    """中间件配置信息"""
    name: str
    middleware: MiddlewareCallable
    enabled: bool = False
    priority: int = 0
    options: Dict[str, Any] = Field(default_factory=dict)
    
    # pydantic 模型配置
    class Config:
        arbitrary_types_allowed = True  # 允许任意类型，因为middleware是可调用对象


class MiddlewareRegistry:
    """中间件注册中心"""
    
    def __init__(self):
        self.middleware_configs: Dict[str, MiddlewareConfig] = {}
        self.active_middlewares: List[MiddlewareCallable] = []
        
    def register(self, middleware: MiddlewareCallable, *, 
                name: Optional[str] = None, 
                enabled: bool = True,
                priority: int = 0, 
                options: Dict[str, Any] = None) -> MiddlewareCallable:
        """注册一个中间件"""
        middleware_name = name or middleware.__name__
        # 创建 MiddlewareConfig 实例
        self.middleware_configs[middleware_name] = MiddlewareConfig(
            name=middleware_name,
            middleware=middleware,
            enabled=enabled,
            priority=priority,
            options=options or {}
        )
        self._rebuild_active_middlewares()
        return middleware
        
    def scan_middlewares(self, package_path: str):
        """扫描并注册指定包中的所有中间件"""
        try:
            package = import_module(package_path)
        except ImportError:
            try:
                if '.' not in package_path:
                    package = import_module(f"aomaker.middlewares.{package_path}")
                else:
                    raise
            except ImportError:
                print(f"未找到中间件包: {package_path}")
                return
        
        for _, name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if is_pkg:
                self.scan_middlewares(name)
            else:
                try:
                    module = import_module(name)
                    self._register_module_middlewares(module)
                except Exception as e:
                    print(f"加载模块 {name} 失败: {str(e)}")
        
        self._rebuild_active_middlewares()
    
    def _register_module_middlewares(self, module):
        """注册模块中所有标记为中间件的函数"""
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and hasattr(obj, "middleware_config"):
                config = getattr(obj, "middleware_config", {})
                self.register(
                    middleware=obj,
                    name=config.get("name", name),
                    enabled=config.get("enabled", True),
                    priority=config.get("priority", 0),
                    options=config.get("options", {})
                )
    
    def _rebuild_active_middlewares(self):
        """重建活动中间件列表"""
        # 获取所有启用的中间件，并按优先级排序
        active_configs = sorted(
            [config for config in self.middleware_configs.values() if config.enabled],
            key=lambda c: c.priority,
            reverse=True  # 高优先级先执行
        )
        self.active_middlewares = [config.middleware for config in active_configs]
    
    def get_middlewares(self) -> List[MiddlewareCallable]:
        """获取所有活动中间件"""
        return self.active_middlewares
    
    def apply_config(self, config_dict: Dict[str, Dict[str, Any]]):
        """应用配置文件中的设置"""
        for name, settings in config_dict.items():
            if name in self.middleware_configs:
                config = self.middleware_configs[name]
                # 使用 Pydantic 模型的 copy 和 update 方法更新配置
                updated_config = config.model_copy(update=settings)
                self.middleware_configs[name] = updated_config
        
        self._rebuild_active_middlewares()
    
    def disable(self, middleware_name: str):
        """禁用指定中间件"""
        if middleware_name in self.middleware_configs:
            config = self.middleware_configs[middleware_name]
            self.middleware_configs[middleware_name] = config.model_copy(update={"enabled": False})
            self._rebuild_active_middlewares()
            
    def enable(self, middleware_name: str):
        """启用指定中间件"""
        if middleware_name in self.middleware_configs:
            config = self.middleware_configs[middleware_name]
            self.middleware_configs[middleware_name] = config.model_copy(update={"enabled": True})
            self._rebuild_active_middlewares()
            
    def set_priority(self, middleware_name: str, priority: int):
        """设置中间件优先级"""
        if middleware_name in self.middleware_configs:
            config = self.middleware_configs[middleware_name]
            self.middleware_configs[middleware_name] = config.model_copy(update={"priority": priority})
            self._rebuild_active_middlewares()


# 创建全局注册表实例
registry = MiddlewareRegistry()


def middleware(name: Optional[str] = None, enabled: bool = True, 
              priority: int = 0, **options):
    """用于标记和配置中间件的装饰器"""
    def decorator(func: MiddlewareCallable) -> MiddlewareCallable:
        # 将配置保存到函数属性中
        func.middleware_config = {
            "name": name or func.__name__,
            "enabled": enabled,
            "priority": priority,
            "options": options
        }
        return func
    return decorator


def load_middleware_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = MIDDLEWARE_CONFIG_PATH
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
    
def apply_middleware_config(config: Dict[str, Any]):
    if config:
        registry.apply_config(config)

def register_internal_middlewares():
    from aomaker.core.middlewares import logging_middleware
    registry.register(logging_middleware.structured_logging_middleware)

def init_middlewares():
    """初始化中间件系统"""
    register_internal_middlewares()

    if os.path.exists(MIDDLEWARES_DIR):
        registry.scan_middlewares("middlewares")

    custom_middleware_config = load_middleware_config()
    apply_middleware_config(custom_middleware_config)




