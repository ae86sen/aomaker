import os
import sys
from typing import List, Text
import yaml
from ruamel.yaml import YAML

from aomaker.models import DistStrategyYaml
from aomaker.path import CONF_DIR, DIST_STRATEGY_PATH
from aomaker.exceptions import FileNotFound, ConfKeyError
from aomaker._printer import print_message
from aomaker._constants import Conf
from aomaker.utils.utils import load_yaml

ruamel_yaml = YAML()


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


def set_conf_file(env: str):
    conf_path = os.path.join(CONF_DIR, Conf.CONF_NAME)
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            doc = ruamel_yaml.load(f)
        doc['env'] = env
        if not doc.get(env):
            print_message(f':confounded_face: 测试环境-{env}还未在配置文件中配置！', style="bold red")
            sys.exit(1)
        with open(conf_path, 'w') as f:
            ruamel_yaml.dump(doc, f)
        print_message(f':globe_with_meridians: 当前测试环境: {env}')
    else:
        print_message(f':confounded_face: 配置文件{conf_path}不存在', style="bold red")
        sys.exit(1)


def handle_dist_strategy_yaml() -> List[Text]:
    if not os.path.exists(DIST_STRATEGY_PATH):
        print_message(f':confounded_face: aomaker并行执行策略文件{DIST_STRATEGY_PATH}不存在！', style="bold red")
        sys.exit(1)
    yaml_data = load_yaml(DIST_STRATEGY_PATH)
    content = DistStrategyYaml(**yaml_data)
    targets = content.target
    marks = content.marks
    d_mark = []
    for target in targets:
        if "." in target:
            target, strategy = target.split(".", 1)
            marks_li = marks[target][strategy]
        else:
            marks_li = marks[target]
        d_mark.extend([f"-m {mark}" for mark in marks_li])
    return d_mark