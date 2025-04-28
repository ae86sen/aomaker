from abc import ABCMeta, abstractmethod


from aomaker.storage import cache, config
from aomaker.config_handlers import EnvVars


class BaseLogin(metaclass=ABCMeta):
    env_vars = EnvVars()

    def __init__(self):
        self.base_url = self.env_vars.current_env_conf.get('base_url')
        self.account = self.env_vars.current_env_conf.get('account')
        self.current_env = self.env_vars.current_env

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def make_headers(self, resp_login: dict):
        pass


class Session:

    @classmethod
    def set_session_vars(cls, login_obj: BaseLogin=None):
        # 1.设置全局配置
        env_conf = EnvVars()
        conf_dict = env_conf.current_env_conf
        config.set("current_env", env_conf.current_env)
        for k, v in conf_dict.items():
            config.set(k, v)
        # 2.设置全局headers
        headers = {}
        if login_obj:
            resp = login_obj.login()
            headers = login_obj.make_headers(resp)
        cache.set('headers', headers)
        
    @classmethod
    def clear_env(cls):
        cache.clear()
        cache.close()
        config.close()

