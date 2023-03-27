# --coding:utf-8--
import os
from abc import ABCMeta, abstractmethod

import yaml

from aomaker.path import CONF_DIR
from aomaker.cache import cache, config
from aomaker.log import logger
from aomaker.exceptions import FileNotFound, ConfKeyError
from aomaker._constants import Conf


class ReadConfig:
    def __init__(self, conf_name=Conf.CONF_NAME):
        self.conf_path = os.path.join(CONF_DIR, conf_name)

    @property
    def conf(self) -> dict:
        if not os.path.exists(self.conf_path):
            raise FileNotFound(self.conf_path)
        with open(self.conf_path, "r", encoding="utf-8") as f:
            config = yaml.load(f.read(), Loader=yaml.FullLoader)

        return config


class EnvVars:
    def __init__(self):
        self.conf = ReadConfig().conf

    @property
    def current_env(self) -> str:
        current_env = self.conf.get(Conf.CURRENT_ENV_KEY)
        if not current_env:
            raise ConfKeyError(Conf.CURRENT_ENV_KEY)
        return current_env

    @property
    def current_env_conf(self) -> dict:
        current_env_conf = self.conf.get(self.current_env)
        if not current_env_conf:
            raise ConfKeyError(self.current_env)
        return current_env_conf


class BaseLogin(metaclass=ABCMeta):
    env_vars = EnvVars()

    def __init__(self):
        self.host = self.env_vars.current_env_conf.get('host')
        self.account = self.env_vars.current_env_conf.get('account')
        self.current_env = self.env_vars.current_env

    @abstractmethod
    def login(self):
        pass

    @abstractmethod
    def make_headers(self, resp_login: dict):
        pass


class SetUpSession:
    def __init__(self, login):
        self.login_obj = login

    def set_session_vars(self):
        # 1.设置全局配置
        env_conf = EnvVars()
        conf_dict = env_conf.current_env_conf
        config.set("current_env", env_conf.current_env)
        for k, v in conf_dict.items():
            config.set(k, v)
        zone = config.get("zone")
        if zone:
            # 如果zone有多个，默认取第一个
            if isinstance(zone, list):
                config.set("zone", zone[0])
        # 2.设置全局headers
        headers = {}
        if self.login_obj:
            resp = self.login_obj.login()
            headers = self.login_obj.make_headers(resp)
        cache.set('headers', headers)


class TearDownSession:
    def clear_env(self):
        logger.info('******************************测试结束，开始清理环境******************************')
        cache.clear()
        cache.close()
        config.close()
        logger.info('******************************清理环境完成******************************')


if __name__ == '__main__':
    # print(ReadConfig().conf)
    print(EnvVars().current_env)
    print(EnvVars().current_env_conf)
    # save_env_vars_to_db()
    # print(db.get('host'))
    # Login().login()
    SetUpSession().set_session_vars()
    # TearDownFixture().clear_env()
