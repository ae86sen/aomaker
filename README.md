![logo_with_slogan.png](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/logo_with_slogan.png)


[![PyPI version](https://badge.fury.io/py/aomaker.svg)](https://badge.fury.io/py/aomaker) ![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)  ![License](https://img.shields.io/github/license/ae86sen/aomaker)


**aomaker**: 重新定义企业级接口自动化测试的工程范式，**文档即代码，定义即测试**，让接口测试变得简单、高效、易维护。

# 🤔 面临的挑战与 aomaker 的答案

在快速迭代的软件开发中，接口自动化测试往往面临诸多痛点：
*   接口定义与实现频繁变更，测试代码维护成本激增。
*   API 文档（如 OpenAPI/Swagger）与测试代码脱节，一致性难以保证。
*   传统方案缺乏结构化管理，导致定义散乱，复用性差。
*   团队协作中接口理解不一致，沟通成本高。

`aomaker` V3 针对这些痛点，提出了创新的解决方案：

**aomaker V3 的全新解法：用模型描述接口，让文档驱动代码。**

解决接口自动化维护难题的关键，在于**接口本身的工程化定义**。

aomaker V3 摒弃了将接口信息零散分布在代码或简单封装中的传统做法，引入了**声明式的接口对象化建模**。

### 1.核心理念和实现
#### 接口建模

aomaker V3选择使用`attrs`库作为建模工具，利用其强大特性，将接口的每一个要素（URL、方法、路径参数、查询参数、请求体、响应体等）结构化地定义在一个 Python 类中。

通过声明式定义让接口结构一目了然，代码即文档，文档即代码，告别硬编码和手动拼接的混乱。

接口定义示例：
```python
from attrs import define, field 

from aomaker.core.router import router
from aomaker.core.api_object import BaseAPIObject


@define(kw_only=True)  
@router.get("/api/{namespace}/containers")  
class GetContainersAPI(BaseAPIObject[ContainersResponse]):  
    """获取容器列表"""  
  
    @define  
    class PathParams:  
        namespace: str = field()  
  
    @define  
    class QueryParams:  
        offset: Optional[int] = field(default=0)  
        limit: Optional[int] = field(default=10)  
        name: Optional[str] = field(  
            default=None, metadata={"description": "容器名称, 模糊搜索"}  
        )  
        reverse: Optional[bool] = field(  
            default=True, metadata={"description": "按时间倒序排列"}  
        )  
        order_by: Optional[str] = field(  
            default="created_at", metadata={"description": "排序字段"}  
        )  
  
    path_params: PathParams  
    query_params: QueryParams = field(factory=QueryParams)  
    response: Optional[ContainersResponse] = field(  
        default=ContainersResponse  
    )
```

用例层调用示例：
```python
from apis.containers.api import GetContainersAPI


def test_notebooks_get():  
    path_params = GetContainersAPI.PathParams(namespace="usr-xxx")  
    query_param = GetContainersAPI.QueryParams(limit=100)  
    res = GetContainersAPI(path_params=path_params, query_params=query_param).send()  
    assert res.response_model.ret_code == 0
```

看到 `GetContainersAPI.PathParams(namespace=...)` 和 `res.response_model.ret_code` 了吗？

这就是 aomaker 带来的改变！

接口的请求参数和响应结构都被定义为清晰的 Python 对象。

在你的 IDE 中，无论是填充 `path_params` 还是访问 `response_model`，全程都有精准的智能提示和类型检查。再也不用猜测参数名，也不用面对 `res['data'][...]` 这样的“黑盒”，开发体验和代码健壮性直线提升！


> 为什么选择attrs？
> 
> 相比`dataclass`的轻量但功能有限，以及`pydantic`的强大但过于繁重，attrs恰好平衡了两者优点：
> - 简单直接，减少样板代码；
> - 支持类型注解和内置验证器，同时允许灵活关闭强校验，适应接口测试中验证异常参数的需求；
> - 性能优化后接近手写代码，运行高效。
>
> 更多`attrs` 特性可查看[官方文档](https://www.attrs.org/en/stable/why.html)。


觉得这套结构化定义略显复杂？没关系，这些其实都可以一键自动生成！👇🏻

#### 文档驱动测试开发

aomaker V3的一大亮点是与**OpenAPI 3.x**和**Swagger 2.0**的深度集成，支持从API文档中**一键生成接口定义模型**。

只需一行命令即可搞定。

![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250428220657.png)

这一功能极大地简化了接口定义的过程，提升了开发效率和准确性，尤其适用于大型项目或API频繁迭代的场景。

- **自动化生成**：测试人员无需手动编写复杂的接口模型。只需导入项目的OpenAPI 3.x或Swagger 2.0文档，aomaker V3即可自动解析并生成相应的attrs模型，包含路径参数、查询参数、请求体和响应体的定义。

- **确保一致性**：自动生成的模型与API文档严格同步，确保接口定义的准确性，减少人为错误的可能性。

- **提升效率**：测试人员可以快速适应接口变更，专注于业务逻辑和测试用例的编写，而无需担心接口定义的细节。


### 2.这意味着什么？

通过接口建模与文档驱动，aomaker 不仅仅是提供了一种新的工程范式，更是解决了一些传统接口自动化测试的老痛点：

- **告别混沌，拥抱工程化:** 接口定义不再是散落各处的神秘代码或脆弱约定。结构化的模型和与文档的强绑定，将接口管理提升到工程化水平，从根本上解决了定义混乱和维护困难的问题。
- **维护成本的指数级下降:** 想象一下修改一个接口需要同步多少测试脚本？甚至很多时候，你甚至都不知道接口发生了什么变更！在 aomaker 中，修改通常只涉及对应的模型类。无论接口发生什么变更，只需一键同步接口文档，让你从容应对快速迭代。
- **开发体验与效率的双重提升:** 精准的 IDE 提示、简洁的调用方式、一键生成的便利性... 这些都意味着更少的错误、更快的开发速度和更愉悦的编码体验。测试人员可以真正聚焦于业务逻辑验证，而不是接口定义的细节。
- **灵活性与测试深度兼顾:** 基于 `attrs` 的模型不仅结构清晰，还提供了灵活的参数校验机制，方便你测试各种正常及异常边界场景。同时，模块化的设计也易于团队协作和功能的扩展。


### 3.与传统方案的对比

|**特性**|**方案一**|**方案二**|**方案三**|**aomaker V3**|
|---|---|---|---|---|
|**接口定义方式**|硬编码|部分抽象|参数建模|声明式建模 + 自动化生成|
|**可维护性**|😞 差|😐 一般|🙂 中等|😄 高|
|**IDE支持**|🚫 无|🔧 弱|🔨 一般|🛠️ 强|
|**参数管理**|📋 无结构|🔒 硬编码|📐 结构化但弱|🏗️ 强结构化|
|**扩展性**|📉 差|📊 一般|📈 中等|🚀 高|
|**API文档集成**|❌ 无|❌ 无|❌ 无|✅ 支持OpenAPI/Swagger|

### 4.总结

aomaker 通过重塑接口定义与管理的方式，旨在将接口自动化从繁琐的“脚本维护”提升为高效的“工程实践”。

当接口的维护难题被解决，上层的测试用例编排就是手拿把掐的事。

因为底层的每一个接口定义都被制作成了标准化的“积木”（API Object），上层无非就是根据业务场景进行“积木拼装”（用例组织）罢了。所以，这就是为什么这个框架叫 **aomaker** 的原因：**API Object Maker**。

**用框架解决重复繁琐劳动，让测试工程师专注于核心逻辑验证。**


当然，aomaker不仅仅只有接口建模和自动生成，还有一系列配套工具链帮助你打造自动化测试工程！👇🏻

<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/aomaker-poster.PNG" width="360" height="450" alt="描述文本">

# ✨ 核心特性一览

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
    - **Mock Server**: 内置功能丰富的 Mock 服务，提供大量示例接口，方便快速上手和调试。
    - **Dashboard**: 提供 Web UI 实时监控测试执行进度、日志和环境配置。
    - **CLI 工具**: 提供脚手架创建、用例运行、模型生成、服务启动、静态统计等便捷命令。
    - **测试报告** : 提供优化版allure测试报告和aomaker专属测试报告。
    - **测试平台** : 提供丰富内部框架接口，测试平台可以快速方便接入。

# 🚀 快速开始
> aomaker提供了mock server和大量示例接口，帮助使用者理解aomaker的工程范式并快速上手。

### 0.安装
先创建虚拟环境，这里推荐`uv` ，然后进入虚拟环境，执行：

```bash
pip install aomaker
```

### 1.创建脚手架

```bash
# 创建脚手架
aomaker create xxx
# 进入脚手架项目
cd xxx
```
<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250429140340.png" width="50%" height="50%" alt="描述文本">


### 2.开启mock server

为了调用预置的mock接口，先开启mock服务：

```bash
aomaker mock start --web
```

可以查看接口文档
![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/aomaker%20v3.0%E6%96%B0%E5%8A%9F%E8%83%BD-20250227.png)

### 3.根据接口文档自动生成接口定义

> 脚手架已经预置了mock接口的定义，也可以体验如何自动生成。

执行自动生成后，会在项目根目录下的apis/mock2目录下生成模型定义代码。

```bash
aomaker gen models -s http://127.0.0.1:9999/api/aomaker-openapi.json -o apis/mock2
```

> -s 指定接口文档位置，可以是url，也可以是本地文件（JSON/YAML），-o 指定最终生成代码的目录。
>
> 更多参数和用法可以通过 aomaker gen models --help 查看。

![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250429150804.png)


### 4.运行测试用例

执行：
```bash
arun -e mock -m mock_api
```


> arun是aomaker运行测试用例的主命令，-e为环境切换参数，-m为指定运行哪些标记的测试用例（用法完全同pytest）。
>
> 更多参数和使用方法可以通过 arun --help 查看。


![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250429145331.png)


### 5.查看测试报告
测试报告位置：项目根目录下reports/aomaker-report.html

![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250428200733.png)

### 6.查看aomaker live console（可选）

可以在开始运行用例前，打开该页面，可以实时查看各个子进程的用例执行进度和日志。

打开方式：
```bash
aomaker service start --web
```

![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250428204248.png)

![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/20250428201246.png)


# 💡 核心特性剖面

## 1. 模型定义：接口=类+装饰器

> **一句话**：用 `@router.*` + `attrs` 声明接口，调用时就能让 IDE 自动补全路径 / 参数 / 响应类型。

**三步即可：**
### 1.导入

```python
from attrs import define, field
from aomaker.core.router import router
from aomaker.core.api_object import BaseAPIObject
```

### 2.声明

```python
@define(kw_only=True)
@router.get("/api/users/{user_id}") # 指定路由和请求方法
class GetUserAPI(BaseAPIObject[UserResponse]): # ▶️ IDE 可提示 UserResponse 字段
    
    @define
    class PathParams: user_id: int = field()
	    path_params: PathParams
    
    response: UserResponse = UserResponse

```


定义接口类名（推荐以`API`结尾），继承接口基类`BaseAPIObject`，如果需要在调用接口响应时有IDE自动补全和提示，需要指定响应模型泛型类。


一个接口类下主要有4个核心参数：
-  path_params: 路径参数，替换路由中`{}` 的内容
- query_params: 查询参数
- request_body: 请求体
- response: 响应

推荐按以下方式进行管理：
```
apis/
├── xxx/            # 接口类型
│   ├── apis.py           # 该类型下所有接口对象定义
│   └── models.py         # apis.py中所有嵌套模型定义
└── ...                   # 其他接口类型
```


> Tips:
>
>虽然支持手动编写接口定义，但还是强烈建议通过接口文档进行自动生成！
>
>更多示例和用法介绍（查询列表、POST 带 Body、嵌套模型…）👉 可查看官方文档「基础特性-模型定义」章节。


## 2.一键生成接口模型定义

> **一句话**：一行命令，把 Swagger / OpenAPI 文档变成可运行的 API 模型，省掉 90 % 手工敲代码。

### ⚡ 只需 3 步

```bash
# 1. 拉起本地或远程接口文档
SPEC=http://127.0.0.1:9999/api/openapi.json

# 2. 一键生成 attrs 模型
aomaker gen models -s $SPEC -o apis/demo

# 3. 编写测试用例并执行
arun -m demo_api

```

生成结果：
```bash
apis/demo/
├── orders/      ← tag 自动分包
│   ├── apis.py      # API 对象
│   └── models.py    # 请求 / 响应模型
└── users/ …

```

### 🧩 命名策略

生成的接口模型类类名可以根据接口文档情况，自行定义。

|需求|用何策略|
|---|---|
|文档里有 `operation_id`|**operation_id**（默认）|
|想用接口摘要|**summary**|
|希望 “Tag + Path + Method”|**tags**|
|还不满足？|**自定义** Python 函数|
```python
# conf/naming.py
from aomaker.maker.models import Operation

def custom_naming(path:str, method:str, op:Operation) -> str:
    # /api/v1/user/login  →  UserLoginAPI
    last_two = [p for p in path.split('/') if p][-2:]
    camel = ''.join(s.capitalize() for s in last_two)
    return f"{camel}API"

```

```bash
aomaker gen models -s $SPEC -o apis/demo --cs conf.naming.custom_naming
```

### 🔧 持久化配置
把常用参数写进 `conf/aomaker.yaml`：

```yaml
openapi:
  spec: api-doc.json
  output: apis/demo
  class_name_strategy: operation_id      # 或 tags / summary
  # custom_strategy: conf.naming.custom_naming
```

以后只需：

```bash
aomaker gen models        # 配置即生效
```

> 想了解完整 CLI 选项？👉 查看官方文档「基础特性-接口文档一键生成」章节。


## 3.存储管理

> **一句话**：配置、缓存、契约、统计——统统放进同一个 `aomaker.db`，零运维、线程安全、低成本。

###  设计初衷

为解决多任务环境下测试变量管理难题，aomaker采用SQLite数据库作为核心存储方案。SQLite作为轻量级嵌入式数据库，具备零配置、无服务端、单文件存储等特点，完美契合测试框架对轻量化与便捷性的要求。

### 四张核心表

项目初始化时自动创建`aomaker.db`数据库文件，内置四张功能明确的表结构：

| 表名             | 生命周期  | 存储内容              | 典型应用场景        |
| -------------- | ----- | ----------------- | ------------- |
| **config**     | 持久化存储 | 全局配置参数            | 环境host/账号信息等  |
| **cache**      | 会话级存储 | 临时变量/依赖数据         | 接口依赖参数传递，临时变量 |
| **schema**     | 持久化存储 | 接口响应模型JSON Schema | 响应结构验证        |
| **statistics** | 持久化存储 | 接口元数据统计           | 测试平台数据可视化     |

### 典型用法速览

#### 全局配置管理

存放全局环境配置、账号登信息。

```yaml
# 配置文件示例（conf/config.yaml）
env: test
test:
  host: http://test.aomaker.com
  account: 
    user: aomaker002
    pwd: 123456
```

```python
# 代码调用示例
from aomaker.storage import config

def test_env_config():
    current_env = config.get("env")  # 获取当前环境
    test_host = config.get("host")  # 获取对应环境host
```


#### 临时变量缓存

管理测试进程中的一些临时变量，如上游依赖等等。

```python
from aomaker.storage import cache

def setup():
    cache.set("auth_token", "Bearer xxxxx")  # 设置鉴权令牌

def test_api_call():
    headers = {"Authorization": cache.get("auth_token")}  # 获取缓存令牌
```


#### JsonSchema契约校验

当接口请求发送拿到响应后，会自动根据`schema`表中存储的该接口响应模型的JSONSchema信息做校验。

例如某个接口的响应模型为`UserResponse`：
```python

@define(kw_only=True)  
class GenericResponse:  
    ret_code: int = field(default=0)  
    message: str = field(default="success")
    
@define(kw_only=True)  
class User:  
    id: int = field()  
    username: str = field()  
    email: str = field()  
    created_at: datetime = field()  
    is_active: bool = field(default=True)
    
@define(kw_only=True)  
class UserResponse(GenericResponse):  
    data: Optional[User] = field(default=None)
    
```

那`UserResponse` 模型对应的JsonSchema为：
```json
{  
  "title": "UserResponse",  
  "type": "object",  
  "properties": {  
    "ret_code": {  
      "type": "integer"  
    },  
    "message": {  
      "type": "string"  
    },  
    "data": {  
      "anyOf": [  
        {  
          "title": "User",  
          "type": "object",  
          "properties": {  
            "id": {  
              "type": "integer"  
            },  
            "username": {  
              "type": "string"  
            },  
            "email": {  
              "type": "string"  
            },  
            "created_at": {  
              "type": "string",  
              "format": "date-time"  
            },  
            "is_active": {  
              "type": "boolean"  
            }  
          },  
          "required": [  
            "id",  
            "username",  
            "email",  
            "created_at"  
          ]  
        },  
        {  
          "type": "null"  
        }  
      ]  
    }  
  },  
  "required": []  
}
```

最终每个响应模型对应的JsonSchema会自动生成并自动存到`schema` 表中：
![](https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/aomaker%20v3.0%E6%96%B0%E5%8A%9F%E8%83%BD%EF%BC%88%E5%90%ABquick%20start%EF%BC%89-20250319-1.png)


> **Schema & Statistics**：首次调用即生成 JSON Schema 并记录元数据，可直接对接测试平台做覆盖率热图、性能趋势等报表。
>
> 详细字段与索引设计👉 见官方文档「基础特性-存储管理」章节。

## 4.并行运行：多线程/进程双模式，火力全开

> **一句话**：一条 `arun --mt/--mp` 命令，线程或进程随心切，标签 / 文件 / 套件三档调度，Allure 报告照样稳。

### 🚀 能力速览

| 维度        | 说明                                                        |
| --------- | --------------------------------------------------------- |
| **并发模式**  | 多线程 `--mt` （轻量）  <br>多进程 `--mp` （CPU 密集型场景优选）             |
| **任务分配**  | - **mark**：标签级  <br>- **file**：测试模块级  <br>- **suite**：目录级 |
| **报告兼容**  | 避免 pytest-parallel 常见的多线程写文件冲突                            |
| **一键策略**  | `dist_strategy.yaml` 批量声明 worker / 标签                     |
| **动态核心数** | 进程模式自动取可用 CPU；`-p 8` 手动限核                                 |
### ⚡ 常用 命令

```bash
# 线程并发，按标记分配
arun --mt --dist-mark "smoke regress"

# 进程并发，按测试文件分配
arun --mp --dist-file testcases/api
```

运行完自动聚合报告并清理环境。

### 🗂️ 大规模用例？用 worker分发策略

`conf/dist_strategy.yaml`

```bash
target: ['iaas', 'hpc']
marks:
  iaas:
    - iaas_image
    - iaas_volume
  hpc:
    - hpc_sw
    - hpc_fs

```

随后：
```bash
arun --mt        # 或 arun --mp
```

框架按策略自动拆分 4 个 worker 并发；改场景只需改 `target`，CLI 不变。

> 👉 更多自定义参数（核心数 `-p`, 忽略失败重跑等）请见文档「高级特性-并行运行测试用例」。


## 5.中间件：在“请求 → 响应”链路里插上任意插件

> **一句话**：少量代码 + 1 个配置，就能为每个接口挂上日志、Mock、重试、性能统计等自定义逻辑。

### 🧩 机制一览

- **可插拔**：任何 `callable(request, next) -> response` 都能成为中间件
- **可配置**：`middlewares/middleware.yaml` 切开/调序，无改代码
- **可观测**：内置日志中间件，支持自定义性能阈值报警

### ⚡ 30 秒上手
```python
# middlewares/retry.py
from aomaker.core.middlewares.registry import middleware,registry

@middleware(name="retry", priority=800, enabled=True,
            options={"max_retries": 3, "codes": [500, 502, 503]})
def retry_mw(request, call_next):
    for _ in range(registry.middleware_configs["retry"].options["max_retries"]):
        resp = call_next(request)
        if resp.status_code not in registry.middleware_configs["retry"].options["codes"]:
            return resp   # 成功即返回
    return resp            # 重试后仍失败

```

```yaml
# middlewares/middleware.yaml
logging_middleware: # 内置
  enabled: true
  priority: 900

retry:         # 👈 名称与装饰器保持一致
  enabled: true
  priority: 800
  options:
    max_retries: 3
    codes: [500, 502, 503]
```

启动 `arun`，框架自动扫描 `middlewares/`，按 **priority → options** 执行。

### 常见插件思路
| 用途             | 关键点                               | 典型做法                             |
| -------------- | --------------------------------- | -------------------------------- |
| **结构化日志**      | 全链路 request/response              | 开箱即用 `logging_middleware`        |
| **Mock / 桩服务** | URL 规则匹配，返回 `CachedResponse`      | 示例：拦截 `/products` → 自定义 JSON     |
| **性能统计**       | 记录 `time.time()` 差值，慢阈值报警         | `options: {slow_threshold: 1.0}` |
| **断网重试**       | 捕获 `RequestException` 循环调用 `next` | 见上方 Retry 示例                     |

> 更多内置中间件与高级写法 👉 官方文档「高级特性-注册自定义请求中间件」。


## 6. 自定义接口转换器： 把“接口模型”翻译成你想要的任何请求格式

>**一句话**：当真实网络流量≠接口文档时，只需继承 `RequestConverter` 重写 1 个钩子，就能让 aomaker 发送**完全贴合业务网关 / BFF / 签名规则**的请求。


### 🧩 典型场景

| 场景 | 文档里的 URL / Body | 线上流量 | 痛点 |
|------|-------------------|----------|------|
| **微服务网关** | `/api/containers/{ns}/list` | `POST /global_api/` + `params={"action": ".../list"}` | 用例想**100% 复现用户轨迹** |
| **加密签名** | 普通 JSON | 统一 `POST /proxy` + AES 包体 | 需要在请求前注入签名字段 |
| **公共参数** | 文档未列出 | 实际必须带 `owner` / `service` | 手写硬编码 & 复制粘贴难维护 |

### ⚡ 自定义只要 3 步

```python
# 1. 继承 RequestConverter
@define
class GatewayConverter(RequestConverter):
    def post_prepare(self, req: PreparedRequest) -> PreparedRequest:
        body = {"params": json.dumps(req.request_body or {}), "method": req.method}
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/global_api/",
            params={"action": self.route},
            request_body=body,
            headers=req.headers,
        )

# 2. 声明一个基类
@define
class GatewayAPI(BaseAPIObject[T]):
    converter = field(default=GatewayConverter)

# 3. 所有接口继承 GatewayAPI
class GetContainersAPI(GatewayAPI[ContainersResp]): 
	...

```

**就是这么简单**：只需重写 `post_prepare`这个钩子，其余只需交给框架处理。

### 🌟 你将获得

1. **真实度 100%** ——完全模拟前端流量，线上巡检 / 烟测再也不用抓包贴代码。
2. **单源可维护**——网关规则变？只改 1 个 Converter，无需重写接口 / 用例。

>  更多进阶玩法和详细用法👉详见官方文档「高级特性-自定义转换器」。


还有更多的特性在此就不再赘述，感兴趣可以前往官方文档进行了解：**https://aomaker.cn**

# 🤝 如何贡献

我们热烈欢迎社区的贡献！无论是报告 Bug、提出功能建议还是提交代码，都对 `aomaker` 的发展至关重要。

*   🐞 **报告 Bug**: 如果你发现了 Bug，请通过 [GitHub Issues](https://github.com/ae86sen/aomaker/issues) 提交详细的报告。
*   💡 **功能建议**: 有好的想法？欢迎在 [GitHub Issues](https://github.com/ae86sen/aomaker/issues) 中分享。
*   🧑‍💻 **提交代码**:
    1.  Fork 本仓库到你的 GitHub 账号。
    2.  基于 `main` (或开发分支) 创建你的特性分支 (`git checkout -b feature/your-amazing-feature`)。
    3.  进行代码修改和开发。
    4.  将你的更改推送到你的 Fork 仓库 (`git push origin feature/your-amazing-feature`)。
    5.  在 `aomaker` 原始仓库发起 Pull Request，详细说明你的更改。
# 加入社区

加作者微信，进入交流群与优秀同行一起交流进步

<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/wechat.JPG" width="30%" height="30%" alt="描述文本">

请作者喝杯☕️

<img src="https://picgo2listen.oss-cn-beijing.aliyuncs.com/imgs/payment.jpg" width="30%" height="30%" alt="描述文本">




# 📜 更新日志

详细的版本变更历史请查看 [CHANGELOG.md](https://aomaker.cn/releases) 文件。

# 📄 许可证

`aomaker` 项目基于 [MIT License](https://github.com/ae86sen/aomaker/blob/v3.0.0-beta/LICENSE) 发布。请查看 `LICENSE` 文件获取详细信息。