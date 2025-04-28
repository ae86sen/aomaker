# --coding:utf-8--
import inspect
import sys
from importlib import import_module

from aomaker.path import BASEDIR

IS_LOADED = False


class Hook:
    HOOK_MODULE_NAME = "hooks"

    def __call__(self, *args, **kwargs):
        self.load_hooks()
        return self

    def load_hooks(self):
        global IS_LOADED
        if IS_LOADED is True:
            return
        sys.path.append(BASEDIR)
        try:
            module_obj = import_module(self.HOOK_MODULE_NAME)
        except ModuleNotFoundError:
            return
        for name, member in inspect.getmembers(module_obj):
            if inspect.isfunction(member) and hasattr(member, '__wrapped__'):
                # 被装饰的函数
                member()
        IS_LOADED = True


class CommandHook(Hook):
    def __init__(self):
        self._callbacks = {}
        self.ctx = None
        self.custom_kwargs = None

    def register(self, func, name):
        """
        注册回调函数。
        """
        self._callbacks[name] = func

    def run(self):
        """
        运行所有已注册的回调函数。
        """

        for param, value in self.custom_kwargs.items():
            if value is not None:
                self._callbacks[param](value)


class SessionHook(Hook):

    def __init__(self):
        self.hooks = []
        self.generators = []
        self.generator_functions = []

    def register(self, func):
        if inspect.isgeneratorfunction(func):
            self.generator_functions.append(func)
        else:
            self.hooks.append(func)

    def execute_pre_hooks(self):
        if self.hooks:
            print("🚀<AoMaker> 开始执行pre hooks...")
            for hook in self.hooks:
                hook()

        if self.generator_functions:
            print("🚀<AoMaker> 开始执行pre hooks...")
            for func in self.generator_functions:
                generator = func()
                self.generators.append(generator)
                next(generator)

    def execute_post_hooks(self):
        if self.generators:
            print("🚀<AoMaker> 开始执行post hooks...")
            for generator in self.generators:
                try:
                    next(generator)
                except StopIteration:
                    pass


cli_hook = CommandHook()
session_hook = SessionHook()
