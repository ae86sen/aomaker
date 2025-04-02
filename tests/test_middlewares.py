import pytest
import yaml
from unittest.mock import MagicMock, patch
import io
from typing import Dict, Any

from aomaker.core.middlewares.registry import (
    middleware, registry, MiddlewareRegistry, MiddlewareCallable
)

# 创建测试中间件
@middleware(name="middleware1", priority=100)
def middleware1(request, call_next):
    request["middleware1_executed"] = True
    request.setdefault("execution_order", []).append("middleware1_before")
    response = call_next(request)
    request["execution_order"].append("middleware1_after")
    return response

@middleware(name="middleware2", priority=50)
def middleware2(request, call_next):
    request["middleware2_executed"] = True
    request.setdefault("execution_order", []).append("middleware2_before")
    response = call_next(request)
    request["execution_order"].append("middleware2_after")
    return response

# 实际的测试函数
def test_middleware_registration():
    """测试中间件注册功能"""
    # 创建新的注册表进行测试，避免影响全局注册表
    test_registry = MiddlewareRegistry()
    
    # 注册中间件
    test_registry.register(middleware1, name="middleware1", priority=100)
    test_registry.register(middleware2, name="middleware2", priority=50)
    
    # 检查中间件是否正确注册
    assert "middleware1" in test_registry.middleware_configs
    assert "middleware2" in test_registry.middleware_configs
    
    # 检查优先级排序
    middlewares = test_registry.get_middlewares()
    assert len(middlewares) == 2
    assert middlewares[0] == middleware1  # 高优先级应该先执行
    assert middlewares[1] == middleware2

def test_middleware_execution():
    """测试中间件执行顺序和功能"""
    test_registry = MiddlewareRegistry()
    test_registry.register(middleware1, name="middleware1", priority=100)
    test_registry.register(middleware2, name="middleware2", priority=50)
    
    # 创建请求和最终处理函数
    request = {}
    final_handler = MagicMock(return_value={"result": "success"})
    
    # 执行中间件链
    middlewares = test_registry.get_middlewares()
    
    # 构建中间件调用链
    def build_middleware_chain(middlewares, index=0):
        if index >= len(middlewares):
            return final_handler
        current_middleware = middlewares[index]
        next_middleware = build_middleware_chain(middlewares, index + 1)
        return lambda req: current_middleware(req, next_middleware)
    
    # 执行中间件链
    chain = build_middleware_chain(middlewares)
    response = chain(request)
    
    # 验证结果
    assert response == {"result": "success"}
    assert request["middleware1_executed"] is True
    assert request["middleware2_executed"] is True
    assert request["execution_order"] == [
        "middleware1_before", 
        "middleware2_before", 
        "middleware2_after", 
        "middleware1_after"
    ]

def test_middleware_enable_disable():
    """测试启用和禁用中间件"""
    test_registry = MiddlewareRegistry()
    test_registry.register(middleware1, name="middleware1", priority=100)
    test_registry.register(middleware2, name="middleware2", priority=50)
    
    # 默认情况下两个中间件都启用
    assert len(test_registry.get_middlewares()) == 2
    
    # 禁用一个中间件
    test_registry.disable("middleware1")
    middlewares = test_registry.get_middlewares()
    assert len(middlewares) == 1
    assert middlewares[0] == middleware2
    
    # 重新启用
    test_registry.enable("middleware1")
    assert len(test_registry.get_middlewares()) == 2