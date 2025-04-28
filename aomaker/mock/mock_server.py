# --coding:utf-8--
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, Query, Path, Body, HTTPException, Depends, Request, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import uvicorn
import jwt
from jwt.exceptions import PyJWTError

from .mock_models import (
    UserListResponse,
    GenericResponse,
    UserDetailResponse,
    ProductDetailResponse,
    Comment,
    User,
    Order,
    UserDetail,
    OrderResponse,
    UserResponse,
    ProductDetail,
    ProductListResponse,
    ProductResponse,
    CommentListResponse,
    SystemStatusResponse,
    CommentResponse,
    FileUploadResponse,
    FileUploadDataResponse,
    LoginRequest,
    TokenData,
    TokenResponse,
    TokenResponseData
)
from .mock_datas import user_details, users, product_details, products, orders, comments, user_credentials

app = FastAPI(
    title="AOMaker Mock Server",
    description="这是一个用于演示aomaker的Mock服务器，提供了各种类型的API接口示例。",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/aomaker-openapi.json"
)

tags_metadata = [
    {
        "name": "auth",
        "description": "认证相关操作，包括用户登录、获取令牌等",
    },
    {
        "name": "users",
        "description": "用户相关操作，包括获取用户列表、获取单个用户信息、创建用户等",
    },
    {
        "name": "products",
        "description": "产品相关操作，包括获取产品列表、获取单个产品信息等",
    },
    {
        "name": "orders",
        "description": "订单相关操作，包括创建订单、更新订单状态等",
    },
    {
        "name": "comments",
        "description": "评论相关操作，包括获取评论列表、添加评论、删除评论等",
    },
    {
        "name": "systems",
        "description": "系统相关操作，包括获取系统状态等",
    },
]

# 更新app的openapi_tags
app.openapi_tags = tags_metadata

# JWT 配置
SECRET_KEY = "aomaker-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 设置OAuth2密码Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/token")

# 身份验证函数
def authenticate_user(username: str, password: str):
    """验证用户名和密码"""
    for user_cred in user_credentials:
        if user_cred["username"] == username and user_cred["password"] == password:
            return user_cred
    return None

def create_access_token(data: dict, expires_delta: timedelta):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


async def verify_token(token: str = Depends(oauth2_scheme)):
    """验证JWT令牌"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="凭证无效",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, exp=payload.get("exp"))
    except PyJWTError:
        raise credentials_exception
    return token_data

# 获取当前用户
async def get_current_user(token_data: TokenData = Depends(verify_token)):
    """根据令牌获取当前用户"""
    for user_cred in user_credentials:
        if user_cred["username"] == token_data.username:
            for user in users:
                if user.id == user_cred["user_id"]:
                    return user
    raise HTTPException(status_code=401, detail="用户不存在或已停用")

# 登录接口
@app.post("/api/login/token", response_model=TokenResponseData, tags=["auth"],
         summary="用户登录获取令牌",
         description="用户提供用户名和密码进行登录，成功后返回JWT令牌")
async def login_for_access_token(login_data: LoginRequest):
    """登录获取访问令牌"""
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, expire = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    expires_in = int((expire - datetime.now()).total_seconds())
    token_response = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )
    return TokenResponseData(ret_code=0, message="登录成功", data=token_response)


@app.get("/api/users", response_model=UserListResponse, tags=["users"],
         summary="获取用户列表",
         description="获取系统中的用户列表，支持分页和按用户名模糊搜索")
async def get_users(
        current_user: User = Depends(get_current_user),
        offset: int = Query(0, description="偏移量，用于分页"),
        limit: int = Query(10, description="限制数量，用于分页"),
        username: Optional[str] = Query(None, description="用户名，支持模糊搜索")
):
    filtered_users = users
    if username:
        filtered_users = [user for user in users if username in user.username]

    return UserListResponse(
        ret_code=0,
        message="success",
        data=filtered_users[offset:offset + limit],
        total=len(filtered_users)
    )


@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["users"],
         summary="获取单个用户信息",
         description="根据用户ID获取单个用户的详细信息")
async def get_user(
        user_id: int = Path(..., description="用户ID"),
        current_user: User = Depends(get_current_user)
):
    for user in users:
        if user.id == user_id:
            return UserResponse(ret_code=0, message="success", data=user)

    raise HTTPException(status_code=404, detail="用户不存在")


@app.post("/api/users", response_model=UserResponse, tags=["users"],
          summary="创建新用户",
          description="创建一个新的用户")
async def create_user(user: User = Body(..., description="用户信息")):
    users.append(user)
    return UserResponse(ret_code=0, message="用户创建成功", data=user)


@app.get("/api/products", response_model=ProductListResponse, tags=["products"],
         summary="获取产品列表",
         description="获取系统中的产品列表，支持分页和按类别筛选")
async def get_products(
        current_user: User = Depends(get_current_user),
        offset: int = Query(0, description="偏移量，用于分页"),
        limit: int = Query(10, description="限制数量，用于分页"),
        category: Optional[str] = Query(None, description="产品类别，精确匹配")
):
    filtered_products = products
    if category:
        filtered_products = [product for product in products if product.category == category]

    return ProductListResponse(
        ret_code=0,
        message="success",
        data=filtered_products[offset:offset + limit],
        total=len(filtered_products)
    )


@app.get("/api/products/{product_id}", response_model=ProductResponse, tags=["products"],
         summary="获取单个产品信息",
         description="根据产品ID获取单个产品的详细信息")
async def get_product(product_id: int = Path(..., description="产品ID")):
    for product in products:
        if product.id == product_id:
            return ProductResponse(ret_code=0, message="success", data=product)

    raise HTTPException(status_code=404, detail="产品不存在")


@app.post("/api/orders", response_model=OrderResponse, tags=["orders"],
          summary="创建新订单",
          description="创建一个新的订单")
async def create_order(order: Order = Body(..., description="订单信息")):
    orders.append(order)
    return OrderResponse(ret_code=0, message="订单创建成功", data=order)


@app.put("/api/orders/{order_id}/status", response_model=GenericResponse, tags=["orders"],
         summary="更新订单状态",
         description="根据订单ID更新订单的状态")
async def update_order_status(
        order_id: int = Path(..., description="订单ID"),
        status: str = Body(..., embed=True, description="新的订单状态")
):
    for order in orders:
        if order.id == order_id:
            order.status = status
            return GenericResponse(ret_code=0, message="订单状态更新成功")

    raise HTTPException(status_code=404, detail="订单不存在")


# 1. GET请求，带路径参数
@app.get("/api/user_details/{user_id}", response_model=UserDetailResponse, tags=["users"],
         summary="获取用户详细信息",
         description="根据用户ID获取用户的详细信息，包括地址、联系方式等")
async def get_user_detail(user_id: int = Path(..., description="用户ID")):
    for detail in user_details:
        if detail.user_id == user_id:
            return UserDetailResponse(ret_code=0, message="success", data=detail)

    raise HTTPException(status_code=404, detail="用户详情不存在")


# 2. GET请求，带查询参数
@app.get("/api/comments", response_model=CommentListResponse, tags=["comments"],
         summary="获取评论列表",
         description="获取系统中的评论列表，支持按产品ID、用户ID和最低评分筛选")
async def get_comments(
        product_id: Optional[int] = Query(None, description="产品ID"),
        user_id: Optional[int] = Query(None, description="用户ID"),
        min_rating: Optional[int] = Query(None, description="最低评分，1-5"),
        offset: int = Query(0, description="偏移量，用于分页"),
        limit: int = Query(10, description="限制数量，用于分页")
):
    filtered_comments = comments

    if product_id is not None:
        filtered_comments = [c for c in filtered_comments if c.product_id == product_id]

    if user_id is not None:
        filtered_comments = [c for c in filtered_comments if c.user_id == user_id]

    if min_rating is not None:
        filtered_comments = [c for c in filtered_comments if c.rating >= min_rating]

    return CommentListResponse(
        ret_code=0,
        message="success",
        data=filtered_comments[offset:offset + limit],
        total=len(filtered_comments)
    )


# 3. GET请求，无路径参数和查询参数
@app.get("/api/system/status", response_model=SystemStatusResponse, tags=["systems"],
         summary="获取系统状态",
         description="获取当前系统的运行状态，包括版本、运行时间、资源使用情况等")
async def get_system_status():
    return SystemStatusResponse(
        ret_code=0,
        message="success",
        data={
            "status": "running",
            "version": "1.0.0",
            "uptime": "3天12小时",
            "cpu_usage": 35.2,
            "memory_usage": 42.8,
            "user_count": len(users),
            "product_count": len(products),
            "order_count": len(orders)
        }
    )


# 4. POST请求，带路径参数和请求体
@app.post("/api/products/{product_id}/comments", response_model=CommentResponse, tags=["comments"],
          summary="添加产品评论",
          description="为指定产品添加一条评论")
async def add_product_comment(
        product_id: int = Path(..., description="产品ID"),
        comment_data: Comment = Body(..., description="评论信息")
):
    # 确保产品存在
    product_exists = False
    for product in products:
        if product.id == product_id:
            product_exists = True
            break

    if not product_exists:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 确保评论的产品ID与路径参数一致
    if comment_data.product_id != product_id:
        raise HTTPException(status_code=400, detail="评论的产品ID与路径参数不一致")

    comments.append(comment_data)

    # 更新产品详情中的评论
    for detail in product_details:
        if detail.basic_info.id == product_id:
            detail.comments.append(comment_data)
            break

    return CommentResponse(ret_code=0, message="评论添加成功", data=comment_data)


# 5. DELETE请求
@app.delete("/api/comments/{comment_id}", response_model=GenericResponse, tags=["comments"],
            summary="删除评论",
            description="根据评论ID删除一条评论")
async def delete_comment(comment_id: int = Path(..., description="评论ID")):
    global comments

    comment_to_delete = None
    for comment in comments:
        if comment.id == comment_id:
            comment_to_delete = comment
            break

    if comment_to_delete is None:
        raise HTTPException(status_code=404, detail="评论不存在")

    comments = [c for c in comments if c.id != comment_id]

    # 从产品详情中也删除评论
    for detail in product_details:
        detail.comments = [c for c in detail.comments if c.id != comment_id]

    return GenericResponse(ret_code=0, message="评论删除成功")


# 6. PATCH请求，模拟文件上传
@app.patch("/api/users/{user_id}/avatar", response_model=FileUploadDataResponse, tags=["users"],
           summary="上传用户头像",
           description="为指定用户上传头像文件")
async def upload_avatar(
        user_id: int = Path(..., description="用户ID"),
        file_info: Dict[str, Any] = Body(..., description="文件信息")
):
    # 检查用户是否存在
    user_exists = False
    for user in users:
        if user.id == user_id:
            user_exists = True
            break

    if not user_exists:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 模拟文件上传处理
    file_id = f"avatar_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    response_data = FileUploadResponse(
        file_id=file_id,
        file_name=file_info.get("file_name", "avatar.jpg"),
        file_size=file_info.get("file_size", 1024),
        file_type=file_info.get("file_type", "image/jpeg"),
        upload_time=datetime.now(),
        download_url=f"https://example.com/files/{file_id}"
    )

    return FileUploadDataResponse(ret_code=0, message="头像上传成功", data=response_data)


# 7. PUT请求，更新用户详情
@app.put("/api/user_details/{user_id}", response_model=UserDetailResponse, tags=["users"],
         summary="更新用户详细信息",
         description="根据用户ID更新用户的详细信息")
async def update_user_detail(
        user_id: int = Path(..., description="用户ID"),
        user_detail: UserDetail = Body(..., description="用户详细信息")
):
    # 确保用户ID一致
    if user_detail.user_id != user_id:
        raise HTTPException(status_code=400, detail="用户ID与路径参数不一致")

    # 检查用户是否存在
    detail_index = None
    for i, detail in enumerate(user_details):
        if detail.user_id == user_id:
            detail_index = i
            break

    if detail_index is None:
        raise HTTPException(status_code=404, detail="用户详情不存在")

    # 更新用户详情
    user_details[detail_index] = user_detail

    return UserDetailResponse(ret_code=0, message="用户详情更新成功", data=user_detail)


# 8. 带嵌套模型的GET请求
@app.get("/api/product_details/{product_id}", response_model=ProductDetailResponse, tags=["products"],
         summary="获取产品详细信息",
         description="根据产品ID获取产品的详细信息，包括销售数据、评论等")
async def get_product_detail(product_id: int = Path(..., description="产品ID")):
    for detail in product_details:
        if detail.basic_info.id == product_id:
            return ProductDetailResponse(ret_code=0, message="success", data=detail)

    raise HTTPException(status_code=404, detail="产品详情不存在")


# 9. 带嵌套模型的POST请求
@app.post("/api/product_details", response_model=ProductDetailResponse, tags=["products"],
          summary="创建产品详细信息",
          description="创建一个新的产品详细信息")
async def create_product_detail(product_detail: ProductDetail = Body(..., description="产品详细信息")):
    # 检查产品是否已存在
    for detail in product_details:
        if detail.basic_info.id == product_detail.basic_info.id:
            raise HTTPException(status_code=400, detail="产品详情已存在")

    # 添加产品基本信息
    products.append(product_detail.basic_info)

    # 添加产品详情
    product_details.append(product_detail)

    return ProductDetailResponse(ret_code=0, message="产品详情创建成功", data=product_detail)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "欢迎使用AOMaker Mock Server",
        "documentation": {
            "Swagger UI": "/api/docs",
            "ReDoc": "/api/redoc",
            "OpenAPI JSON": "/api/openapi.json"
        }
    }


from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_whitelist = [
            "/api/login/token",  # 登录接口
            "/",                 # 根路径
            "/api/docs",         # Swagger文档
            "/api/redoc",        # ReDoc文档
            "/api/aomaker-openapi.json",  # OpenAPI规范
        ]
        
        # 检查请求路径是否在白名单中
        path = request.url.path
        if path in auth_whitelist:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response(
                content='{"detail":"缺少认证信息"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return Response(
                    content='{"detail":"认证方案无效"}',
                    status_code=401,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return Response(
                    content='{"detail":"无效的认证凭据"}',
                    status_code=401,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
            user_exists = False
            for user_cred in user_credentials:
                if user_cred["username"] == username:
                    user_exists = True
                    break
                    
            if not user_exists:
                return Response(
                    content='{"detail":"用户不存在或已停用"}',
                    status_code=401,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
            return await call_next(request)
        except Exception:
            return Response(
                content='{"detail":"无效的认证凭据"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"}
            )

app.add_middleware(AuthMiddleware)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
