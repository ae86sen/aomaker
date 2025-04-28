# --coding:utf-8--
from datetime import datetime
from .mock_models import User, Product, Order, Comment, Address, UserDetail, ProductDetail

# 模拟数据
users = [
    User(id=1, username="张三", email="zhangsan@example.com", created_at=datetime.now()),
    User(id=2, username="李四", email="lisi@example.com", created_at=datetime.now()),
    User(id=3, username="王五", email="wangwu@example.com", created_at=datetime.now()),
]

products = [
    Product(id=1, name="笔记本电脑", price=5999.0, description="高性能笔记本", stock=100, category="电子产品"),
    Product(id=2, name="智能手机", price=3999.0, description="最新款智能手机", stock=200, category="电子产品"),
    Product(id=3, name="无线耳机", price=999.0, description="蓝牙无线耳机", stock=300, category="配件"),
]

orders = [
    Order(
        id=1,
        user_id=1,
        products=[{"product_id": 1, "quantity": 1}],
        total_price=5999.0,
        status="已完成",
        created_at=datetime.now()
    ),
    Order(
        id=2,
        user_id=2,
        products=[{"product_id": 2, "quantity": 1}, {"product_id": 3, "quantity": 1}],
        total_price=4998.0,
        status="处理中",
        created_at=datetime.now()
    ),
]

# 添加更多模拟数据
addresses = [
    Address(street="人民路123号", city="上海", province="上海", postal_code="200001"),
    Address(street="建国路456号", city="北京", province="北京", postal_code="100001"),
    Address(street="解放路789号", city="广州", province="广东", postal_code="510000"),
]

user_details = [
    UserDetail(
        user_id=1,
        address=addresses[0],
        phone="13800138000",
        birth_date=datetime(1990, 1, 1),
        tags=["VIP", "常客"],
        preferences={"theme": "dark", "newsletter": True}
    ),
    UserDetail(
        user_id=2,
        address=addresses[1],
        phone="13900139000",
        tags=["新用户"],
        preferences={"theme": "light", "newsletter": False}
    ),
    UserDetail(
        user_id=3,
        address=addresses[2],
        phone="13700137000",
        birth_date=datetime(1985, 5, 5),
        tags=["VIP"],
        preferences={"theme": "auto", "newsletter": True}
    ),
]

comments = [
    Comment(id=1, product_id=1, user_id=1, content="非常好用的笔记本电脑", rating=5, created_at=datetime.now()),
    Comment(id=2, product_id=1, user_id=2, content="性价比很高", rating=4, created_at=datetime.now()),
    Comment(id=3, product_id=2, user_id=3, content="手机很流畅", rating=5, created_at=datetime.now()),
    Comment(id=4, product_id=3, user_id=1, content="音质不错", rating=4, created_at=datetime.now()),
]

product_details = [
    ProductDetail(
        basic_info=products[0],
        sales_count=120,
        comments=[comments[0], comments[1]],
        related_products=[2, 3],
        specifications={"cpu": "Intel i7", "memory": "16GB", "storage": "512GB SSD"}
    ),
    ProductDetail(
        basic_info=products[1],
        sales_count=200,
        comments=[comments[2]],
        related_products=[3],
        specifications={"screen": "6.7英寸", "memory": "8GB", "storage": "256GB"}
    ),
    ProductDetail(
        basic_info=products[2],
        sales_count=150,
        comments=[comments[3]],
        related_products=[1, 2],
        specifications={"type": "入耳式", "battery": "24小时", "noise_cancelling": True}
    ),
]

# 用户凭证数据（用于登录验证）
user_credentials = [
    {"username": "aomaker", "password": "123456", "user_id": 1},
]
