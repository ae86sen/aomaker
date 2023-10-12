
![jRL5nO.md.png](https://s1.ax1x.com/2022/07/13/jRL5nO.md.png)

> Quickly Arrange,Quickly Test!

[![pyversions](https://img.shields.io/pypi/pyversions/httprunner.svg)](https://pypi.python.org/pypi/httprunner)
[详细使用指南🧭](https://aomaker.github.io/)

# 核心思想

**AoMaker**，即 Api object Maker，那什么是**API Object**呢？

**API Object**是**Page Object**设计模式在接口测试上的一种延伸，顾名思义，这里是将各种基础接口进行了一层抽象封装，将其作为 object，通过不同的 API 对象调用来组装成不同的业务流场景。

举个简单例子：

有一个购物车功能，它有如下接口：

- add，将物品添加到购物车
- list，查看购物车内所有物品
- delete，清空购物车内所有物品

那么，我们通过`ao` 的思想来封装这个功能所有接口：

```python
    class ShoppingTrolley:
        def add(self):
            """添加物品到购物车"""
            pass

        def delete(self):
            """清空购物车"""
            pass

        def list(self):
            """查看购物车内所有物品"""
            pass
```

当我们需要测试购物车的增-查-删流程时，只需要实例化`ShoppingTrolley` 类，通过调用对应的接口对象，即可完成业务场景的组装：

```python
    class TestShoppingTrolley:
        def test_shopping(self):
            """测试购物车增-查-删流程"""
            st = ShoppingTrolley()
            # 1.添加物品到购物车
            st.add()
            # 2.查看购物车内物品
            st.list()
            # 3.清空购物车
            st.delete()
```

解释了**API Object**，那**Maker**又怎么理解呢？

**Maker**其实就是框架本身提供各种辅助手段帮助快速的去编排`ao` 和`case` 。

**什么手段？怎么辅助呢？**
栗子：
```python
class Instance(BaseApi):

    @aomaker.dependence(image_api.describe_images, "describe_images")
    @aomaker.dependence("instance.describe_instance_types", "instance_types", imp_module="apis.iaas.instance.instance")
    @aomaker.async_api(ins_listener, "instances")
    def create_instance(self, test_data: dict, **kw_params):
        """创建主机"""

        kw_params["describe_images"] = self.cache.get_by_jsonpath("describe_images", "$..image_id")
        kw_params["instance_types"] = self.cache.get_by_jsonpath("instance_types", "$..instance_type_id")

        kw_params["cpu"] = test_data["cpu"]
        kw_params["memory"] = test_data["memory"]

        params_model = model.RunInstanceModel(**kw_params)
        resp = self.send_http(params_model)

        return resp
```
对于一个接口的封装，其实核心的处理就是接口参数进行参数化处理，一个接口的参数一般可分为以下三种情况：
- 常量：即不需要参数化的参数，写死即可
- 上游依赖变量：即该参数需要调用另一个接口，从其返回值中提取
- 测试数据：即需要从用例层传入的测试数据，一般会做数据驱动

其中，对于上游依赖变量的处理是每个接口测试框架必须要面对的问题，`aomaker`的解法是通过`@dependence`装饰器去标注该接口的依赖，让其自动识别并调用依赖，并结合`aomaker`特殊的变量管理机制去灵活存取依赖值。

此外，如果该接口是一个异步接口，那么还需要对其进行异步处理，`aomaker`的解法依然是通过装饰器标注，通过`@async_api`指定该接口的异步处理函数，在接口调用并正常收到返回后，将进行异步处理。

通过上面的栗子可以看出，`aomaker`对于一个接口的定义，包括：
- 前置：接口的上游依赖调用（同一个依赖只会调用一次）
- 定义：对接口进行http协议填充，包括接口参数的参数化处理、请求发送（`headers`等公共数据隐藏在基类中自动处理）
- 后置（如果是异步）：在接口调用完成并得到正常反馈后，开始自动进行轮询处理，直到得到异步任务完成的反馈

这样的目的是为了保证接口定义功能单一、简洁，方法中只有接口的定义，没有过多的数据处理、逻辑判断等操作，另一方面，提高了复用性，不用反复处理前后置并且同样的依赖不会重复调用。

当完成了这样一个`ao`的定义，就可以供上层（用例层或业务层）调用，在调用层不用再去关心该怎么处理它的依赖关系，该怎么处理后置操作，只需要调用`ao`这块积木去组装你的用例或业务即可，内部 细节全由框架自动帮你完成。

`aomaker` 早期1.0版本中，其实还提供了两种自动生成`ao`和`case`的方式：
- 通过`yaml`模板自动生成（包括`har`和`swagger`转换）
- 通过流量录制自动生成

当时受`httprunner` 的影响较大，陷入了一些思维定式，觉得通过模板转换自动生成代码感觉很高效，但经过长时间的项目实践，发现模板会有很多条条款款的限制，每个项目又不尽相同，这样反而限制了灵活性（没有说`httprunner`不好的意思，hr设计得非常优秀，收益良多，可以说没有hr就没有aomaker），处处掣肘不能放飞自我策马奔腾。所以后来在2.0版本中，基本弃用了这两种方式（但代码依然保留，或许有人喜欢呢），还是更推荐直接撸代码来得快，`aomaker`只是提供了一些辅助工具，帮你撸得更快更稳更方便，可扩展性还是非常高的，不会限制你的发挥。

# 定位

一款基于`pytest` ，将接口通过**ao 对象**方式来编排管理的接口自动化框架，让测试人员能快速完成自动化项目搭建和高可维护性脚本的编写，快速开始测试。

# 特性

- 提供 CLI 命令
- 提供脚手架一键安装，开箱即用
- 变量管理简单
- 简洁处理依赖和异步接口
- 不同粒度的重试机制
- 三种方式快速编写 ao 和 case
- 支持多进程和多线程
- 易扩展
- 丰富的断言
- 支持流量录制
- 支持 pytest 所有用法和插件
- allure 报告优化
- 测试报告消息通知
- ...

# 交流

如果对该框架感兴趣以及有更多好的想法，欢迎交流探讨~

[![v9XorQ.jpg](https://s1.ax1x.com/2022/07/28/v9XorQ.jpg)](https://imgtu.com/i/v9XorQ)
