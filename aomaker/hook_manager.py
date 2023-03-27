# --coding:utf-8--

class CommandHook:
    def __init__(self):
        self._callbacks = {}
        self.ctx = None
        self.custom_kwargs = None

    def register(self, func, name):
        """
        注册回调函数。
        """
        self._callbacks[name] = func

    # def unregister(self, func):
    #     """
    #     取消注册回调函数。
    #     """
    #     if func in self._callbacks:
    #         self._callbacks.remove(func)

    def run(self):
        """
        运行所有已注册的回调函数。
        """

        for param, value in self.custom_kwargs.items():
            if value is not None:
                self._callbacks[param](value)


class SessionHook:
    def __init__(self):
        self._callbacks = []

    def register(self, func):
        self._callbacks.append(func)

    def run(self):
        for func in self._callbacks:
            func()


_cli_hook = CommandHook()
_session_hook = SessionHook()
