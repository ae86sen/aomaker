# --coding:utf-8--
import sys

# debug使用
sys.path.insert(0, 'D:\\项目列表\\aomaker')
import os
import re

import yaml
from requests import request

from aomaker.path import CONF_DIR
from aomaker.cache import cache, config
from aomaker.log import logger
from aomaker.exceptions import FileNotFound, ConfKeyError
from aomaker._constants import Conf


class ReadConfig:
    def __init__(self, conf_name=Conf.CONF_NAME):
        # todo:测试
        self.conf_path = r"D:/项目列表/aomaker/aomaker/tttttttt/conf/config.yaml"
        # self.conf_path = os.path.join(CONF_DIR, conf_name)

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


class BaseLogin:
    env_vars = EnvVars()

    def __init__(self):
        self.host = self.env_vars.current_env_conf.get('host')
        self.account = self.env_vars.current_env_conf.get('account')
        self.current_env = self.env_vars.current_env

    def _pre_login(self):
        data = {
            'url': self.host + '/login',
            'method': 'get',
        }
        resp = request(**data)
        csrftoken = resp.cookies['csrftoken']
        sid = resp.cookies['sid']
        return {'csrftoken': csrftoken, 'sid': sid}

    def login(self):
        submit_host = self.env_vars.current_env_conf.get('submit_host')
        resp_login = self._pre_login()
        payload = {
            'verifyType': 'passwd',
            'loginType': 'email',
            'email': self.account['user'],
            'passwd': self.account['pwd'],
            'csrfmiddlewaretoken': resp_login["csrftoken"],
            'login_account_email_postfix': '@xxx.com'
        }

        if self.current_env in ['shanhe', 'nscc']:
            del payload['verifyType']
            del payload['loginType']
            del payload['email']
            payload['user'] = self.account['user']
            submit_login_url = self.host + '/login/submit'
        else:
            submit_login_url = submit_host + "/login/api/submit/"
        data = {
            'url': submit_login_url,
            'method': 'post',
            'headers': {'Cookie': f'csrftoken={resp_login["csrftoken"]};sid={resp_login["sid"]}',
                        "Referer": self.host, 'Content-Type': 'application/x-www-form-urlencoded'
                        },
            'data': payload
        }

        resp_submit = request(**data)
        # print(resp_submit.text)
        if self.current_env in ['shanhe', 'nscc']:

            sk = re.findall("sk: '(.+?)',", resp_submit.text)[0]
        else:
            sk = resp_submit.cookies.get('sk')
        resp_login['sk'] = sk
        resp_login['host'] = self.host
        # print(resp_login)
        return resp_login


class Login(BaseLogin):
    pass


class SetUpSession:

    def login(self):
        resp = Login().login()
        return resp

    def set_session_vars(self):
        logger.info('******************************开始初始化环境******************************')
        # 1.设置全局配置
        env_conf = EnvVars()
        conf_dict = env_conf.current_env_conf
        config.set("current_env", env_conf.current_env)
        for k, v in conf_dict.items():
            config.set(k, v)
        # 2.设置全局headers
        resp = self.login()
        headers = self.make_headers(resp)
        cache.set('headers', headers)

    def make_headers(self, resp_login):
        headers = {
            'Cookie': f'csrftoken={resp_login["csrftoken"]};sid={resp_login["sid"]};sk={resp_login["sk"]};console_ver=3',
            'X-CSRFToken': resp_login["csrftoken"], "Referer": resp_login['host']}
        return headers


class TearDownSession:
    def clear_env(self):
        logger.info('******************************测试结束，开始清理环境******************************')
        cache.clear()
        cache.close()
        config.close()
        logger.info('清理cache完成')


if __name__ == '__main__':
    # print(ReadConfig().conf)
    print(EnvVars().current_env)
    print(EnvVars().current_env_conf)
    # save_env_vars_to_db()
    # print(db.get('host'))
    # Login().login()
    SetUpSession().set_session_vars()
    # TearDownFixture().clear_env()
