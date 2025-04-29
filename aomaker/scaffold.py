import sys
from pathlib import Path
from rich.panel import Panel

from aomaker._printer import printer, print_message, console
from aomaker._constants import PROJECT_ROOT_FILE


class ExtraArgument:
    create_venv = False


def init_parser_scaffold(subparsers):
    sub_parser_scaffold = subparsers.add_parser(
        "startproject", help="Create a new project with template structure."
    )
    sub_parser_scaffold.add_argument(
        "project_name", type=str, nargs="?", help="Specify new project name."
    )
    sub_parser_scaffold.add_argument(
        "-venv",
        dest="create_venv",
        action="store_true",
        help="Create virtual environment in the project and install aomaker.",
    )
    return sub_parser_scaffold


@printer(start_msg="开始创建脚手架", end_msg="项目脚手架创建完成！")
def create_scaffold(project_name):
    """ Create scaffold with specified project name.
    """
    if Path(project_name).is_dir():
        print_message(
            f"项目目录：{project_name} 已存在, 请重新设置一个目录名称.",
            style="bold red"
        )
        return 1

    elif Path(project_name).is_file():
        print_message(
            f"项目目录：{project_name} 存在同名文件，请重新设置一个目录名称",
            style="bold red"
        )
        return 1

    creation_steps = []

    def create_folder(path):
        Path(path).mkdir(parents=True, exist_ok=True)
        msg = f"创建目录: {path}"
        creation_steps.append(msg)

    def create_file(path, file_content=""):
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        msg = f"创建文件: {path}"
        creation_steps.append(msg)

    create_folder(project_name)
    create_file(Path(project_name) / PROJECT_ROOT_FILE)
    create_file(Path(project_name) / "__init__.py")
    apis_path = Path(project_name) / "apis"
    create_folder(apis_path)
    create_file(apis_path / "__init__.py")
    mock_path = apis_path / "mock"
    create_folder(mock_path)
    create_file(mock_path / "__init__.py")
    apis_content = """from typing import Optional, Dict, List, Any
from datetime import datetime

from attrs import define, field
from aomaker.core.router import router
from aomaker.core.api_object import BaseAPIObject

from .models import (
    UserListResponse,
    GenericResponse,
    UserDetailResponse,
    ProductResponse,
    ProductDetailResponse,
    Comment,
    Address,
    Product,
    UserResponse,
    OrderResponse, 
    CommentListResponse, 
    SystemStatusResponse, 
    CommentResponse, 
    ProductListResponse,
    FileUploadDataResponse,
    TokenResponseData

)

@define(kw_only=True)
@router.post("/api/login/token")
class LoginAPI(BaseAPIObject[TokenResponseData]):
    \"""登录\"""

    @define
    class RequestBodyModel:
        username: str = field()
        password: str = field()

    request_body: RequestBodyModel
    response: Optional[TokenResponseData] = field(default=TokenResponseData)


@define(kw_only=True)
@router.get("/api/users")
class GetUsersAPI(BaseAPIObject[UserListResponse]):
    \"""获取用户列表\"""

    @define
    class QueryParams:
        offset: int = field(default=0, metadata={"description": "偏移量"})
        limit: int = field(default=10, metadata={"description": "限制数量"})
        username: Optional[str] = field(
            default=None, metadata={"description": "用户名，模糊搜索"}
        )

    query_params: QueryParams = field(factory=QueryParams)
    response: Optional[UserListResponse] = field(default=UserListResponse)
    endpoint_id: Optional[str] = field(default="get_users_api_users_get")


@define(kw_only=True)
@router.get("/api/users/{user_id}")
class GetUserAPI(BaseAPIObject[UserResponse]):
    \"""获取单个用户信息\"""

    @define
    class PathParams:
        user_id: int = field(metadata={"description": "用户ID"})

    path_params: PathParams
    response: Optional[UserResponse] = field(default=UserResponse)
    endpoint_id: Optional[str] = field(default="get_user_api_users__user_id__get")


@define(kw_only=True)
@router.post("/api/users")
class CreateUserAPI(BaseAPIObject[UserResponse]):
    \"""创建新用户\"""

    @define
    class RequestBodyModel:
        id: int = field()
        username: str = field()
        email: str = field()
        created_at: datetime = field()
        is_active: bool = field(default=True)

    request_body: RequestBodyModel
    response: Optional[UserResponse] = field(default=UserResponse)
    endpoint_id: Optional[str] = field(default="create_user_api_users_post")


@define(kw_only=True)
@router.get("/api/products")
class GetProductsAPI(BaseAPIObject[ProductListResponse]):
    \"""获取产品列表\"""

    @define
    class QueryParams:
        offset: int = field(default=0, metadata={"description": "偏移量"})
        limit: int = field(default=10, metadata={"description": "限制数量"})
        category: Optional[str] = field(
            default=None, metadata={"description": "产品类别"}
        )

    query_params: QueryParams = field(factory=QueryParams)
    response: Optional[ProductListResponse] = field(default=ProductListResponse)
    endpoint_id: Optional[str] = field(default="get_products_api_products_get")


@define(kw_only=True)
@router.get("/api/products/{product_id}")
class GetProductAPI(BaseAPIObject[ProductResponse]):
    \"""获取单个产品信息\"""

    @define
    class PathParams:
        product_id: int = field(metadata={"description": "产品ID"})

    path_params: PathParams
    response: Optional[ProductResponse] = field(default=ProductResponse)
    endpoint_id: Optional[str] = field(default="get_product_api_products__product_id__get")


@define(kw_only=True)
@router.post("/api/orders")
class CreateOrderAPI(BaseAPIObject[OrderResponse]):
    \"""创建新订单\"""

    @define
    class RequestBodyModel:
        id: int = field()
        user_id: int = field()
        products: List[Dict[str, Any]] = field()
        total_price: float = field()
        status: str = field()
        created_at: datetime = field()

    request_body: RequestBodyModel
    response: Optional[OrderResponse] = field(default=OrderResponse)
    endpoint_id: Optional[str] = field(default="create_order_api_orders_post")


@define(kw_only=True)
@router.put("/api/orders/{order_id}/status")
class UpdateOrderStatusAPI(BaseAPIObject[GenericResponse]):
    \"""更新订单状态\"""

    @define
    class PathParams:
        order_id: int = field(metadata={"description": "订单ID"})

    @define
    class RequestBodyModel:
        status: str = field(metadata={"description": "新状态"})

    path_params: PathParams
    request_body: RequestBodyModel
    response: Optional[GenericResponse] = field(default=GenericResponse)
    endpoint_id: Optional[str] = field(default="update_order_status_api_orders__order_id__status_put")


# 1. GET请求，带路径参数
@define(kw_only=True)
@router.get("/api/user_details/{user_id}")
class GetUserDetailAPI(BaseAPIObject[UserDetailResponse]):
    \"""获取用户详细信息\"""

    @define
    class PathParams:
        user_id: int = field(metadata={"description": "用户ID"})

    path_params: PathParams
    response: Optional[UserDetailResponse] = field(default=UserDetailResponse)
    endpoint_id: Optional[str] = field(default="get_user_detail_api_user_details__user_id__get")


# 2. GET请求，带查询参数
@define(kw_only=True)
@router.get("/api/comments")
class GetCommentsAPI(BaseAPIObject[CommentListResponse]):
    \"""获取评论列表\"""

    @define
    class QueryParams:
        product_id: Optional[int] = field(default=None, metadata={"description": "产品ID"})
        user_id: Optional[int] = field(default=None, metadata={"description": "用户ID"})
        min_rating: Optional[int] = field(default=None, metadata={"description": "最低评分"})
        offset: int = field(default=0, metadata={"description": "偏移量"})
        limit: int = field(default=10, metadata={"description": "限制数量"})

    query_params: QueryParams = field(factory=QueryParams)
    response: Optional[CommentListResponse] = field(default=CommentListResponse)
    endpoint_id: Optional[str] = field(default="get_comments_api_comments_get")


# 3. GET请求，无路径参数和查询参数
@define(kw_only=True)
@router.get("/api/system/status")
class GetSystemStatusAPI(BaseAPIObject[SystemStatusResponse]):
    \"""获取系统状态\"""

    response: Optional[SystemStatusResponse] = field(default=SystemStatusResponse)
    endpoint_id: Optional[str] = field(default="get_system_status_api_system_status_get")


# 4. POST请求，带路径参数和请求体
@define(kw_only=True)
@router.post("/api/products/{product_id}/comments")
class AddProductCommentAPI(BaseAPIObject[CommentResponse]):
    \"""添加产品评论\"""

    @define
    class PathParams:
        product_id: int = field(metadata={"description": "产品ID"})

    @define
    class RequestBodyModel:
        id: int = field()
        product_id: int = field()
        user_id: int = field()
        content: str = field()
        rating: int = field()
        created_at: datetime = field()

    path_params: PathParams
    request_body: RequestBodyModel
    response: Optional[CommentResponse] = field(default=CommentResponse)
    endpoint_id: Optional[str] = field(default="add_product_comment_api_products__product_id__comments_post")


# 5. DELETE请求
@define(kw_only=True)
@router.delete("/api/comments/{comment_id}")
class DeleteCommentAPI(BaseAPIObject[GenericResponse]):
    \"""删除评论\"""

    @define
    class PathParams:
        comment_id: int = field(metadata={"description": "评论ID"})

    path_params: PathParams
    response: Optional[GenericResponse] = field(default=GenericResponse)
    endpoint_id: Optional[str] = field(default="delete_comment_api_comments__comment_id__delete")


# 6. PATCH请求，模拟文件上传
@define(kw_only=True)
@router.patch("/api/users/{user_id}/avatar")
class UploadAvatarAPI(BaseAPIObject[FileUploadDataResponse]):
    \"""上传用户头像\"""

    @define
    class PathParams:
        user_id: int = field(metadata={"description": "用户ID"})

    @define
    class RequestBodyModel:
        file_name: str = field()
        file_size: int = field()
        file_type: str = field()

    path_params: PathParams
    request_body: RequestBodyModel
    response: Optional[FileUploadDataResponse] = field(default=FileUploadDataResponse)
    endpoint_id: Optional[str] = field(default="upload_avatar_api_users__user_id__avatar_patch")


# 7. PUT请求，更新用户详情
@define(kw_only=True)
@router.put("/api/user_details/{user_id}")
class UpdateUserDetailAPI(BaseAPIObject[UserDetailResponse]):
    \"""更新用户详细信息\"""

    @define
    class PathParams:
        user_id: int = field(metadata={"description": "用户ID"})

    @define
    class RequestBodyModel:
        user_id: int = field()
        address: Address = field()
        phone: str = field()
        birth_date: Optional[datetime] = field(default=None)
        tags: List[str] = field(factory=list)
        preferences: Dict[str, Any] = field(factory=dict)

    path_params: PathParams
    request_body: RequestBodyModel
    response: Optional[UserDetailResponse] = field(default=UserDetailResponse)
    endpoint_id: Optional[str] = field(default="update_user_detail_api_user_details__user_id__put")


# 8. 带嵌套模型的GET请求
@define(kw_only=True)
@router.get("/api/product_details/{product_id}")
class GetProductDetailAPI(BaseAPIObject[ProductDetailResponse]):
    \"""获取产品详细信息\"""

    @define
    class PathParams:
        product_id: int = field(metadata={"description": "产品ID"})

    path_params: PathParams
    response: Optional[ProductDetailResponse] = field(default=ProductDetailResponse)
    endpoint_id: Optional[str] = field(default="get_product_detail_api_product_details__product_id__get")


# 9. 带嵌套模型的POST请求
@define(kw_only=True)
@router.post("/api/product_details")
class CreateProductDetailAPI(BaseAPIObject[ProductDetailResponse]):
    \"""创建产品详细信息\"""

    @define
    class RequestBodyModel:
        basic_info: Product = field()
        sales_count: int = field(default=0)
        comments: List[Comment] = field(factory=list)
        related_products: List[int] = field(factory=list)
        specifications: Dict[str, Any] = field(factory=dict)

    request_body: RequestBodyModel
    response: Optional[ProductDetailResponse] = field(default=ProductDetailResponse)
    endpoint_id: Optional[str] = field(default="create_product_detail_api_product_details_post")
  
    """
    create_file(mock_path / "apis.py", apis_content)
    models_content = """from typing import Any, Dict, List, Optional
from datetime import datetime
from attrs import define, field

@define(kw_only=True)
class GenericResponse:
    ret_code: int = field(default=0)
    message: str = field(default="success")


@define(kw_only=True)
class GenericDataResponse(GenericResponse):
    data: Any = field(default=None)


@define(kw_only=True)
class GenericListResponse(GenericResponse):
    data: List[Any] = field(factory=list)
    total: int = field(default=0)


@define(kw_only=True)
class User:
    id: int = field()
    username: str = field()
    email: str = field()
    created_at: datetime = field()
    is_active: bool = field(default=True)


@define(kw_only=True)
class Product:
    id: int = field()
    name: str = field()
    price: float = field()
    description: Optional[str] = field(default=None)
    stock: int = field()
    category: str = field()


@define(kw_only=True)
class Order:
    id: int = field()
    user_id: int = field()
    products: List[Dict[str, Any]] = field()
    total_price: float = field()
    status: str = field()
    created_at: datetime = field()


@define(kw_only=True)
class Address:
    street: str = field()
    city: str = field()
    province: str = field()
    postal_code: str = field()
    country: str = field(default="中国")


@define(kw_only=True)
class UserDetail:
    user_id: int = field()
    address: Address = field()
    phone: str = field()
    birth_date: Optional[datetime] = field(default=None)
    tags: List[str] = field(factory=list)
    preferences: Dict[str, Any] = field(factory=dict)


@define(kw_only=True)
class Comment:
    id: int = field()
    product_id: int = field()
    user_id: int = field()
    content: str = field()
    rating: int = field()
    created_at: datetime = field()


@define(kw_only=True)
class ProductDetail:
    basic_info: Product = field()
    sales_count: int = field(default=0)
    comments: List[Comment] = field(factory=list)
    related_products: List[int] = field(factory=list)
    specifications: Dict[str, Any] = field(factory=dict)


@define(kw_only=True)
class FileUploadResponse:
    file_id: str = field()
    file_name: str = field()
    file_size: int = field()
    file_type: str = field()
    upload_time: datetime = field()
    download_url: str = field()


@define(kw_only=True)
class SystemStatus:
    status: str = field()
    version: str = field()
    uptime: str = field()
    cpu_usage: float = field()
    memory_usage: float = field()
    user_count: int = field()
    product_count: int = field()
    order_count: int = field()

@define(kw_only=True)
class UserResponse(GenericResponse):
    data: Optional[User] = field(default=None)

@define(kw_only=True)
class UserListResponse(GenericResponse):
    data: List[User] = field(factory=list)
    total: int = field(default=0)

@define(kw_only=True)
class UserDetailResponse(GenericResponse):
    data: Optional[UserDetail] = field(default=None)

# 产品相关响应模型
@define(kw_only=True)
class ProductResponse(GenericResponse):
    data: Optional[Product] = field(default=None)

@define(kw_only=True)
class ProductListResponse(GenericResponse):
    data: List[Product] = field(factory=list)
    total: int = field(default=0)

@define(kw_only=True)
class ProductDetailResponse(GenericResponse):
    data: Optional[ProductDetail] = field(default=None)

@define(kw_only=True)
class OrderResponse(GenericResponse):
    data: Optional[Order] = field(default=None)

@define(kw_only=True)
class OrderListResponse(GenericResponse):
    data: List[Order] = field(factory=list)
    total: int = field(default=0)

@define(kw_only=True)
class CommentResponse(GenericResponse):
    data: Optional[Comment] = field(default=None)

@define(kw_only=True)
class CommentListResponse(GenericResponse):
    data: List[Comment] = field(factory=list)
    total: int = field(default=0)

@define(kw_only=True)
class FileUploadDataResponse(GenericResponse):
    data: Optional[FileUploadResponse] = field(default=None)

@define(kw_only=True)
class SystemStatusResponse(GenericResponse):
    data: Optional[SystemStatus] = field(default=None)

@define(kw_only=True)
class TokenResponse:
    access_token: str = field()
    token_type: str = field()
    expires_in: int = field()

@define(kw_only=True)
class TokenResponseData(GenericDataResponse):
    data: Optional[TokenResponse] = field(default=None)   
    """
    create_file(mock_path / "models.py", models_content)
    testcase_path = Path(project_name) / "testcases"
    create_folder(testcase_path)
    create_file(testcase_path / "__init__.py")
    test_mock_content = """from datetime import datetime

import pytest

from apis.mock.apis import (
    GetUserAPI, 
    GetUsersAPI,
    CreateUserAPI,
    GetProductsAPI,
    GetProductAPI,
    CreateOrderAPI,
    UpdateOrderStatusAPI,
    GetUserDetailAPI,
    GetCommentsAPI,
    GetSystemStatusAPI,
    AddProductCommentAPI,
    DeleteCommentAPI,
    UploadAvatarAPI,
)



@pytest.mark.mock_api
def test_get_users():
    ""\"测试获取用户列表API\"""
    query_params = GetUsersAPI.QueryParams(limit=2)
    res = GetUsersAPI(query_params=query_params).send()

    assert res.response_model.ret_code == 0
    assert len(res.response_model.data) <= 2
    assert res.response_model.total >= 0


@pytest.mark.mock_api
def test_get_user():
    ""\"测试获取单个用户API\"""
    path_params = GetUserAPI.PathParams(user_id=1)

    res = GetUserAPI(path_params=path_params).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.id == 1
    assert res.response_model.data.username is not None


@pytest.mark.mock_api
def test_create_user():
    ""\"测试创建用户API\"""
    request_body = CreateUserAPI.RequestBodyModel(
        id=4,
        username="赵六",
        email="zhaoliu@example.com",
        created_at=datetime.now()
    )

    res = CreateUserAPI(request_body=request_body).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.id == 4
    assert res.response_model.data.username == "赵六"


@pytest.mark.mock_api
def test_get_products():
    ""\"测试获取产品列表API"\""
    query_params = GetProductsAPI.QueryParams(
        category="电子产品"
    )

    res = GetProductsAPI(query_params=query_params).send()

    assert res.response_model.ret_code == 0
    assert len(res.response_model.data) > 0
    for product in res.response_model.data:
        assert product.category == "电子产品"


@pytest.mark.mock_api
def test_get_product():
    ""\"测试获取单个产品API"\""
    path_params = GetProductAPI.PathParams(product_id=1)

    res = GetProductAPI(path_params=path_params).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.id == 1
    assert res.response_model.data.name is not None


@pytest.mark.mock_api
def test_create_order():
    ""\"测试创建订单API\"""
    request_body = CreateOrderAPI.RequestBodyModel(
        id=3,
        user_id=3,
        products=[{"product_id": 3, "quantity": 2}],
        total_price=1998.0,
        status="待付款",
        created_at=datetime.now()
    )

    res = CreateOrderAPI(request_body=request_body).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.id == 3
    assert res.response_model.data.status == "待付款"


@pytest.mark.mock_api
def test_update_order_status():
    ""\"测试更新订单状态API\"""
    path_params = UpdateOrderStatusAPI.PathParams(order_id=1)
    request_body = UpdateOrderStatusAPI.RequestBodyModel(status="已发货")

    res = UpdateOrderStatusAPI(
        path_params=path_params,
        request_body=request_body
    ).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.message == "订单状态更新成功"


@pytest.mark.mock_api
def test_get_user_detail():
    ""\"测试获取用户详细信息API"\""
    path_params = GetUserDetailAPI.PathParams(user_id=1)

    res = GetUserDetailAPI(path_params=path_params).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.user_id == 1
    assert res.response_model.data.address is not None
    assert res.response_model.data.phone is not None


@pytest.mark.mock_api
def test_get_comments():
    ""\"测试获取评论列表API"\""
    query_params = GetCommentsAPI.QueryParams(
        product_id=1,
        min_rating=4
    )

    res = GetCommentsAPI(query_params=query_params).send()

    assert res.response_model.ret_code == 0
    assert len(res.response_model.data) > 0
    for comment in res.response_model.data:
        assert comment.product_id == 1
        assert comment.rating >= 4


@pytest.mark.mock_api
def test_get_system_status():
    ""\"测试获取系统状态API"\""
    res = GetSystemStatusAPI().send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.status == "running"
    assert res.response_model.data.version is not None


@pytest.mark.mock_api
def test_add_product_comment():
    ""\"测试添加产品评论API"\""
    path_params = AddProductCommentAPI.PathParams(product_id=1)
    request_body = AddProductCommentAPI.RequestBodyModel(
        id=5,
        product_id=1,
        user_id=2,
        content="非常满意的购物体验",
        rating=5,
        created_at=datetime.now()
    )

    res = AddProductCommentAPI(
        path_params=path_params,
        request_body=request_body
    ).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.id == 5
    assert res.response_model.data.content == "非常满意的购物体验"


@pytest.mark.mock_api
def test_delete_comment():
    ""\"测试删除评论API""\"
    # 先添加一个评论
    add_comment_path_params = AddProductCommentAPI.PathParams(product_id=1)
    add_comment_request_body = AddProductCommentAPI.RequestBodyModel(
        id=6,
        product_id=1,
        user_id=3,
        content="测试删除评论",
        rating=4,
        created_at=datetime.now()
    )

    AddProductCommentAPI(
        path_params=add_comment_path_params,
        request_body=add_comment_request_body
    ).send()

    # 然后删除这个评论
    path_params = DeleteCommentAPI.PathParams(comment_id=6)

    res = DeleteCommentAPI(path_params=path_params).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.message == "评论删除成功"


@pytest.mark.mock_api
def test_upload_avatar():
    ""\"测试上传头像API""\"
    path_params = UploadAvatarAPI.PathParams(user_id=1)
    request_body = UploadAvatarAPI.RequestBodyModel(
        file_name="avatar.png",
        file_size=2048,
        file_type="image/png"
    )

    res = UploadAvatarAPI(
        path_params=path_params,
        request_body=request_body
    ).send()

    assert res.response_model.ret_code == 0
    assert res.response_model.data.file_name == "avatar.png"
    assert res.response_model.data.download_url is not None
    """
    create_file(testcase_path / "test_mock.py", test_mock_content)
    create_folder(testcase_path / "test_api")
    create_file(testcase_path / "test_api" / "__init__.py")
    create_folder(testcase_path / "test_scenario")
    create_file(testcase_path / "test_scenario" / "__init__.py")
    create_folder(Path(project_name) / "conf")
    config_content = """env: mock
mock:
  base_url: 'http://127.0.0.1:9999'
  account:
    user: 'aomaker'
    pwd: '123456'

release:
  base_url: 'https://release.aomaker.com'
  account:
    user: 'aomaker'
    pwd: '123456'

"""
    create_file(Path(project_name) / "conf" / "config.yaml", config_content)
    aomaker_content="""openapi:
    # OpenAPI规范文件路径
    spec: "path/to/openapi.json"
    # 代码输出目录
    output: "apis/demo"
    # 使用预定义命名策略 (operation_id, summary, tags)
    class_name_strategy: "operation_id"
    # 或者使用自定义命名策略, 如：myproject.naming.custom_strategy
    custom_strategy: ""
    # API基类完整路径
    base_api_class: "aomaker.core.api_object.BaseAPIObject"
    # 基类在生成代码中的别名
    base_api_class_alias: "BaseAPI"
    """
    create_file(Path(project_name) / "conf" / "aomaker.yaml", aomaker_content)
    create_file(Path(project_name) / "conf" / "dist_strategy.yaml")

    utils_config_content = """wechat: 
    webhook:
    """
    create_file(Path(project_name) / "conf" / "utils.yaml", utils_config_content)
    conftest_content = """"""
    create_file(Path(project_name) / "conftest.py", conftest_content)
    run_content = """\"""测试任务运行说明

================================单进程启动================================
启动函数：run()
参数: 接收一个列表，pytest和arun支持的所有参数
Example：
run(["-s","-m demo","-e testing"])

================================多线程启动================================
启动函数：threads_run()           
参数：
    根据传入参数类型不同，启动不同的多线程分配模式
    list: dist-mark模式
    str：dist-file模式
    dict：dist-suite模式
多线程分配模式：
    1.dist-mark: 根据mark标记来分配线程，每个mark标记的线程独立运行
        example：
            threads_run(["-m demo1","-m demo2","-m demo3"])
            将启动三个子线程，分别执行标记为demo1,demo2,demo3的case
    2.dist-file: 根据测试文件来分配线程，每个文件下的case由独立线程运行
        example：
            threads_run({"path":"testcases/test_api"})
            testcases/test_api目录下有多少个测试文件，就启动多少个子线程来运行
    3.dist-suite: 根据测试套件来分配线程，每个套件下的case由独立的线程运行
        example：
            threads_run("testcases/test_api")
            testcases/test_api目录下有多少个测试套件，就启动多少个子线程来运行

================================多进程启动================================
****注意：windows下暂时不支持，linux和mac支持****
启动函数：processes_run()           
参数：
    根据传入参数类型不同，启动不同的多线程分配模式
    list: dist-mark模式
    str：dist-file模式
    dict：dist-suite模式
多线程分配模式：
    同多进程
=========================================================================
\"""
from aomaker.cli import main_run

if __name__ == '__main__':
    main_run(env="mock", pytest_args=['-m mock_api'])"""
    create_file(Path(project_name) / "run.py", run_content)
    pytest_ini_content = """[pytest]
markers =
    smoke: smoke test
    regress: regress test
    
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
    """
    create_file(Path(project_name) / "pytest.ini", pytest_ini_content)
    login_content = """from typing import Union

from aomaker.session import BaseLogin
from aomaker.core.http_client import HTTPClient

from apis.mock.apis import LoginAPI

class Login(BaseLogin):


    def login(self) -> Union[dict, str]:
        login_request_data = LoginAPI.RequestBodyModel(
            username=self.account['user'],
            password=self.account['pwd']
        )
        login_api = LoginAPI(
            request_body=login_request_data,
            http_client=HTTPClient()
        )
        resp_login = login_api.send()
        return resp_login.response_model.data.access_token

    def make_headers(self, resp_login: Union[dict, str]) -> dict:
        token = resp_login
        headers = {
            'Authorization': f'Bearer {token}'
        }
        return headers
    
    """
    create_file(Path(project_name) / "login.py", login_content)
    create_file(Path(project_name) / "hooks.py", "")
    create_folder(Path(project_name) / "middlewares")
    create_file(Path(project_name) / "middlewares" / "__init__.py")
    content = """logging_middleware:
    priority: 1000
    enabled: true
"""
    create_file(Path(project_name) / "middlewares" / "middlewares.yaml", content)
    
    data_path = Path(project_name) / "data"
    create_folder(data_path)
    create_folder(data_path / "api_data")
    create_folder(data_path / "scenario_data")
    create_folder(Path(project_name) / "reports")
    create_folder(Path(project_name) / "logs")
    db_dir_path = Path(project_name) / "database"
    create_folder(db_dir_path)

    panel_content = "\n".join(creation_steps)
    panel = Panel(panel_content, title="[bold cyan]脚手架创建详情[/bold cyan]", border_style="blue", expand=False)
    console.print(panel)

    return 0


def main_scaffold(args):
    ExtraArgument.create_venv = args.create_venv
    sys.exit(create_scaffold(args.project_name))


if __name__ == '__main__':
    create_scaffold('FFFF')
