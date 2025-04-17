
![logo_with_slogan.png](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/logo_with_slogan.png)


[![PyPI version](https://badge.fury.io/py/aomaker.svg)](https://badge.fury.io/py/aomaker) ![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)  ![License](https://img.shields.io/github/license/ae86sen/aomaker)


**aomaker**: 重新定义企业级接口自动化测试的工程范式，**文档即代码，定义即测试**，让接口测试回归简单、高效、可维护。

## 🤔 面临的挑战与 aomaker 的答案

在快速迭代的软件开发中，接口自动化测试往往面临诸多痛点：
*   接口定义与实现频繁变更，测试代码维护成本激增。
*   API 文档（如 OpenAPI/Swagger）与测试代码脱节，一致性难以保证。
*   传统方案缺乏结构化管理，导致定义散乱，复用性差。
*   团队协作中接口理解不一致，沟通成本高。

`aomaker` V3 针对这些痛点，提出了创新的解决方案：
通过**对象化建模**将接口的完整定义（URL、方法、请求头、参数、请求体、响应体等）整合为统一、结构化的 Python 类。结合**声明式定义**和与 **OpenAPI/Swagger 的深度集成**，`aomaker` 彻底革新了接口自动化测试的开发与维护模式，实现了从“脚本级”到“工程化”的转变。
同时，在单元测试引擎上拥抱`pytest` 生态，支持并兼容所有`pytest` 插件。
<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/aomaker-poster.PNG" width="360" height="450" alt="描述文本">

## ✨ 核心特性一览

*   🚀 **声明式接口建模**: 使用 Python `attrs` 库定义接口，代码即文档，清晰直观，告别繁琐的硬编码和手动拼接。
*   📄 **OpenAPI/Swagger 无缝集成**: 支持从 OpenAPI 3.x 和 Swagger 2.0 文档**一键生成**类型安全的接口模型代码，确保测试代码与 API 定义的强一致性。
*   🔧 **极致的可维护性**: 结构化的参数（路径、查询、请求体、响应）管理，接口变更时只需修改对应模型，维护成本线性可控。
*   💡 **卓越的易用性**: 强大的 **IDE 类型提示与自动补全**支持，编写测试用例时参数定义一目了然，显著降低出错概率，提升开发效率。
*   ✅ **灵活的参数校验**: `attrs` 提供内置校验器，同时允许灵活关闭强校验，完美适配接口测试中对正常及异常参数的验证需求。
*   🔄 **自定义请求转换器**: 内置钩子允许轻松定制请求转换逻辑，适配前端请求包装、微服务网关等各种复杂场景。
*   🔬 **JSON Schema 自动校验**: 自动提取接口定义的响应模型生成 JSON Schema，并在每次请求后**自动校验响应结构**的完整性和类型，有效防止接口契约破坏。
*   💾 **强大的存储管理**: 基于轻量级 SQLite 数据库，提供线程安全的全局配置管理 (`config`)、会话级缓存 (`cache`)、Schema 存储 (`schema`) 和接口元数据统计 (`statistics`)。
*   🔑 **灵活的鉴权管理**: 支持多种认证方式，提供简洁的 API 实现登录认证逻辑，并支持请求头动态覆盖与作用域管理。
*   ⚡ **高效并行测试**: 支持**多线程**和**多进程**两种并行模式，提供按标记、文件、套件等多种任务分配策略，加速大规模测试执行。
*   🔌 **可扩展的中间件系统**: 允许注册自定义中间件，在请求发送前和响应接收后执行自定义逻辑（如日志记录、Mock、重试、性能统计等）。
*   🌊 **HTTP 流式响应支持**: 内置对流式响应的处理能力，适用于大数据传输、实时数据获取等场景。
*   🛠️ **配套工具生态**:
    *   **Mock Server**: 内置功能丰富的 Mock 服务，提供大量示例接口，方便快速上手和调试。
    *   **Dashboard**: 提供 Web UI 实时监控测试执行进度、日志和环境配置。
    *   **CLI 工具**: 提供脚手架创建、模型生成、服务启动、静态统计等便捷命令。

## 🚀 快速开始
1.  **创建并进入虚拟环境**:
通过`venv`，`conda`，`poetry`，`uv`（推荐）创建虚拟环境，然后进入虚拟环境
2.  **安装 aomaker**:
    ```bash
    pip install aomaker
    ```
3.  **创建项目脚手架**:
    ```bash
    aomaker create my_api_tests
    cd my_api_tests
    ```
    脚手架将包含推荐的项目结构、配置文件、示例接口定义和测试用例。
4.  **启动内置 Mock Server**:
    ```bash
    aomaker mock start --web
    ```
    访问 `http://127.0.0.1:9999` (默认端口) 查看 Mock API 的 Swagger 文档。
5.  **(可选) 从 Mock Server 的 API 文档生成接口模型**:
    ```bash
    # 确保 Mock Server 正在运行
    aomaker gen models -s http://127.0.0.1:9999/api/aomaker-openapi.json -o apis/mock_generated
    ```
    生成的代码会放在 `apis/mock_generated` 目录下。
6.  **运行脚手架提供的 Mock 测试用例**:
    ```bash
    # arun 是 aomaker run 的快捷方式
    arun -e mock -m mock_api
    ```
    `-e mock` 指定使用 `conf/config.yaml` 中的 `mock` 环境配置。
    `-m mock_api` 指定运行标记为 `mock_api` 的测试用例。
7.  **(可选) 启动 Dashboard 查看实时进度**:
    ```bash
    aomaker service start --web
    ```
    访问 `http://127.0.0.1:8888` (默认端口) 查看实时 Dashboard。

## 💡 用法示例

**1. 定义接口 (`apis/mock/user_apis.py`)**
```python
from attrs import define, field
from typing import Optional, List
from datetime import datetime
from aomaker.core.router import router
from aomaker.core.api_object import BaseAPIObject
# 假设响应模型定义在 user_models.py 中
from .user_models import User, UserListResponse, UserResponse

# 示例：获取用户列表接口 (GET /api/users)
@define(kw_only=True)
@router.get("/api/users")
class GetUsersAPI(BaseAPIObject[UserListResponse]): # 指定泛型 UserListResponse 以启用响应校验和提示
    """获取用户列表"""

    # 使用内部类定义查询参数模型
    @define
    class QueryParams:
        offset: int = field(default=0, metadata={"description": "偏移量"})
        limit: int = field(default=10, metadata={"description": "限制数量"})
        username: Optional[str] = field(
            default=None, metadata={"description": "用户名，模糊搜索"}
        )

    # 接口对象持有 QueryParams 实例
    query_params: QueryParams = field(factory=QueryParams)
    # 指定响应模型类型（可选，但强烈推荐）
    response: Optional[UserListResponse] = field(default=UserListResponse)

# 示例：创建用户接口 (POST /api/users)
@define(kw_only=True)
@router.post("/api/users")
class CreateUserAPI(BaseAPIObject[UserResponse]):
    """创建新用户"""

    # 使用内部类定义请求体模型
    @define
    class RequestBodyModel:
        id: int = field()
        username: str = field()
        email: str = field()
        created_at: datetime = field()
        is_active: bool = field(default=True)

    # 接口对象持有 RequestBodyModel 实例
    request_body: RequestBodyModel
    response: Optional[UserResponse] = field(default=UserResponse)
```

**2. 编写测试用例 (`testcases/test_mock.py`)**
```python
import pytest
from datetime import datetime
# 导入定义好的接口类
from apis.mock.user_apis import GetUsersAPI, CreateUserAPI

@pytest.mark.mock_api
def test_get_users_with_limit():
    """测试获取用户列表API，并限制数量"""
    # 实例化查询参数，IDE 会提供友好的参数提示和类型检查
    query_params = GetUsersAPI.QueryParams(limit=5)

    # 实例化接口对象并发送请求
    res = GetUsersAPI(query_params=query_params).send()

    # 基础断言 (aomaker 默认会检查 status_code 是否为 2xx)
    # assert res.raw.status_code == 200 # 可选

    # 业务断言 (直接访问响应模型属性，享受 IDE 补全)
    assert res.response_model.ret_code == 0
    assert isinstance(res.response_model.data, list)
    assert len(res.response_model.data) <= 5
    assert res.response_model.total >= 0

@pytest.mark.mock_api
def test_create_user_success():
    """测试创建用户API"""
    # 准备请求体数据
    user_data = CreateUserAPI.RequestBodyModel(
        id=101,
        username="测试用户",
        email="test@example.com",
        created_at=datetime.now()
    )

    # 实例化接口对象并发送请求
    res = CreateUserAPI(request_body=user_data).send()

    # 断言业务码和返回数据
    assert res.response_model.ret_code == 0
    assert res.response_model.data is not None
    assert res.response_model.data.id == 101
    assert res.response_model.data.username == "测试用户"
```

**👉 想了解更多高级用法？请查阅 [完整文档](占位符 - 指向你的详细文档链接，例如 Read the Docs 或 aomaker v3.0新功能（含quick start）.md 的在线版本)。**

## 🤝 如何贡献

我们热烈欢迎社区的贡献！无论是报告 Bug、提出功能建议还是提交代码，都对 `aomaker` 的发展至关重要。

*   🐞 **报告 Bug**: 如果你发现了 Bug，请通过 [GitHub Issues](占位符 - 指向你的项目 Issues 页面链接) 提交详细的报告。
*   💡 **功能建议**: 有好的想法？欢迎在 [GitHub Issues](占位符 - 指向你的项目 Issues 页面链接) 中分享。
*   🧑‍💻 **提交代码**:
    1.  Fork 本仓库到你的 GitHub 账号。
    2.  基于 `main` (或开发分支) 创建你的特性分支 (`git checkout -b feature/your-amazing-feature`)。
    3.  进行代码修改和开发。
    4.  将你的更改推送到你的 Fork 仓库 (`git push origin feature/your-amazing-feature`)。
    5.  在 `aomaker` 原始仓库发起 Pull Request，详细说明你的更改。
## 加入社区
加作者微信，进入交流群与优秀同行一起交流进步
<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/wechat.JPG" width="30%" height="30%" alt="描述文本">

请作者喝杯☕️
<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/payment.jpg" width="30%" height="30%" alt="描述文本">




## 📜 更新日志

详细的版本变更历史请查看 [CHANGELOG.md](占位符 - 指向你的 CHANGELOG 文件链接) 文件。

## 📄 许可证

`aomaker` 项目基于 [MIT License](占位符 - 指向你的 LICENSE 文件链接) 发布。请查看 `LICENSE` 文件获取详细信息。