from aomaker.core.base_model import EndpointConfig, HTTPMethod
from aomaker.core.router import router


def test_router_get_basic():
    """测试 @router.get 装饰器基本功能"""
    @router.get("/users")
    class GetUsersAPI:
        pass

    assert hasattr(GetUsersAPI, '_endpoint_config')
    config: EndpointConfig = getattr(GetUsersAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/users"
    assert config.method == HTTPMethod.GET
    assert config.route_params == []


def test_router_post_basic():
    """测试 @router.post 装饰器基本功能"""
    @router.post("/items")
    class CreateItemAPI:
        pass

    assert hasattr(CreateItemAPI, '_endpoint_config')
    config: EndpointConfig = getattr(CreateItemAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/items"
    assert config.method == HTTPMethod.POST
    assert config.route_params == []


def test_router_put_basic():
    """测试 @router.put 装饰器基本功能"""
    @router.put("/items")
    class UpdateItemAPI:
        pass

    assert hasattr(UpdateItemAPI, '_endpoint_config')
    config: EndpointConfig = getattr(UpdateItemAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/items"
    assert config.method == HTTPMethod.PUT
    assert config.route_params == []


def test_router_delete_basic():
    """测试 @router.delete 装饰器基本功能"""
    @router.delete("/items")
    class DeleteItemAPI:
        pass

    assert hasattr(DeleteItemAPI, '_endpoint_config')
    config: EndpointConfig = getattr(DeleteItemAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/items"
    assert config.method == HTTPMethod.DELETE
    assert config.route_params == []


def test_router_patch_basic():
    """测试 @router.patch 装饰器基本功能"""
    @router.patch("/items")
    class PatchItemAPI:
        pass

    assert hasattr(PatchItemAPI, '_endpoint_config')
    config: EndpointConfig = getattr(PatchItemAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/items"
    assert config.method == HTTPMethod.PATCH
    assert config.route_params == []


def test_router_with_single_path_param():
    """测试带有单个路径参数的路由"""
    @router.get("/users/{user_id}")
    class GetUserByIdAPI:
        pass

    assert hasattr(GetUserByIdAPI, '_endpoint_config')
    config: EndpointConfig = getattr(GetUserByIdAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/users/{user_id}"
    assert config.method == HTTPMethod.GET
    assert config.route_params == ["user_id"]


def test_router_with_multiple_path_params():
    """测试带有多个路径参数的路由"""
    @router.post("/items/{item_id}/subitems/{sub_id}")
    class CreateSubItemAPI:
        pass

    assert hasattr(CreateSubItemAPI, '_endpoint_config')
    config: EndpointConfig = getattr(CreateSubItemAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/items/{item_id}/subitems/{sub_id}"
    assert config.method == HTTPMethod.POST
    assert config.route_params == ["item_id", "sub_id"]


def test_router_decorator_returns_class():
    """测试装饰器返回的是被装饰的类本身"""
    class OriginalClass:
        pass

    DecoratedGet = router.get("/test_get")(OriginalClass)
    assert DecoratedGet is OriginalClass

    DecoratedPost = router.post("/test_post")(OriginalClass)
    assert DecoratedPost is OriginalClass

    DecoratedPut = router.put("/test_put")(OriginalClass)
    assert DecoratedPut is OriginalClass

    DecoratedDelete = router.delete("/test_delete")(OriginalClass)
    assert DecoratedDelete is OriginalClass

    DecoratedPatch = router.patch("/test_patch")(OriginalClass)
    assert DecoratedPatch is OriginalClass


def test_router_with_mixed_params_and_path():
    """测试混合固定路径和参数的路由"""
    @router.put("/users/{user_id}/profile")
    class UpdateUserProfileAPI:
        pass

    assert hasattr(UpdateUserProfileAPI, '_endpoint_config')
    config: EndpointConfig = getattr(UpdateUserProfileAPI, '_endpoint_config')
    assert isinstance(config, EndpointConfig)
    assert config.route == "/users/{user_id}/profile"
    assert config.method == HTTPMethod.PUT
    assert config.route_params == ["user_id"] 