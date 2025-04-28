# --coding:utf-8--
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


# 用户模型
class User(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True


# 登录相关模型
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    username: str
    exp: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # 过期时间（秒）


# 产品模型
class Product(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None
    stock: int
    category: str


# 订单模型
class Order(BaseModel):
    id: int
    user_id: int
    products: List[Dict[str, Any]]
    total_price: float
    status: str
    created_at: datetime


# 通用响应模型
class GenericResponse(BaseModel):
    ret_code: int = 0
    message: str = "success"


class GenericDataResponse(GenericResponse):
    data: Any = None


class GenericListResponse(GenericResponse):
    data: List[Any] = []
    total: int = 0



class Address(BaseModel):
    street: str
    city: str
    province: str
    postal_code: str
    country: str = "中国"


class UserDetail(BaseModel):
    user_id: int
    address: Address
    phone: str
    birth_date: Optional[datetime] = None
    tags: List[str] = []
    preferences: Dict[str, Any] = {}


class Comment(BaseModel):
    id: int
    product_id: int
    user_id: int
    content: str
    rating: int
    created_at: datetime


class ProductDetail(BaseModel):
    basic_info: Product
    sales_count: int = 0
    comments: List[Comment] = []
    related_products: List[int] = []
    specifications: Dict[str, Any] = {}


class FileUploadResponse(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    file_type: str
    upload_time: datetime
    download_url: str

# 用户相关响应模型
class UserResponse(GenericDataResponse):
    data: Optional[User] = None

class UserListResponse(GenericListResponse):
    data: List[User] = []

class UserDetailResponse(GenericDataResponse):
    data: Optional[UserDetail] = None

# 产品相关响应模型
class ProductResponse(GenericDataResponse):
    data: Optional[Product] = None

class ProductListResponse(GenericListResponse):
    data: List[Product] = []

class ProductDetailResponse(GenericDataResponse):
    data: Optional[ProductDetail] = None

# 订单相关响应模型
class OrderResponse(GenericDataResponse):
    data: Optional[Order] = None

class OrderListResponse(GenericListResponse):
    data: List[Order] = []

# 评论相关响应模型
class CommentResponse(GenericDataResponse):
    data: Optional[Comment] = None

class CommentListResponse(GenericListResponse):
    data: List[Comment] = []

# 文件上传响应模型
class FileUploadDataResponse(GenericDataResponse):
    data: Optional[FileUploadResponse] = None

# 系统状态响应模型
class SystemStatusResponse(GenericDataResponse):
    data: Dict[str, Any] = {}

# 登录响应模型
class TokenResponseData(GenericDataResponse):
    data: Optional[TokenResponse] = None
