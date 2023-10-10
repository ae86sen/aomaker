# --coding:utf-8--
import os
import sys
from typing import List, Text

import click
import inspect
from importlib import import_module

import yaml
from emoji import emojize
from click_help_colors import HelpColorsGroup, version_option

from aomaker import __version__, __image__
from aomaker._constants import Conf
from aomaker.log import logger, AoMakerLogger
from aomaker.path import CONF_DIR, AOMAKER_YAML_PATH
from aomaker.hook_manager import _cli_hook
from aomaker.param_types import QUOTED_STR
from aomaker.path import BASEDIR
from aomaker.scaffold import create_scaffold
from aomaker.make import main_make
from aomaker.make_testcase import main_case, main_make_case
from aomaker.extension.har_parse import main_har2yaml
from aomaker.extension.recording import filter_expression, main_record
from aomaker.utils.utils import load_yaml
from aomaker.models import AomakerYaml

SUBCOMMAND_RUN_NAME = "run"
HOOK_MODULE_NAME = "hooks"
plugin_path = os.path.join(BASEDIR, f'{HOOK_MODULE_NAME}.py')


class OptionHandler:
    def __init__(self):
        self.options = {}

    def add_option(self, name, **kwargs):
        kwargs["name"] = (name,)
        if "action_store" in kwargs.keys():
            kwargs["is_flag"] = True
            action_store = kwargs.get("action_store")
            kwargs["default"] = False if action_store else True
            kwargs["flag_value"] = action_store
            del kwargs["action_store"]
        self.options = kwargs


def load_plugin():
    sys.path.append(BASEDIR)
    try:
        module_obj = import_module(HOOK_MODULE_NAME)
    except ModuleNotFoundError:
        return
    for name, member in inspect.getmembers(module_obj):
        if inspect.isfunction(member) and hasattr(member, '__wrapped__'):
            # 被装饰的函数
            member()


@click.group(cls=HelpColorsGroup,
             invoke_without_command=True,
             help_headers_color='magenta',
             help_options_color='cyan',
             context_settings={"max_content_width": 120, })
@version_option(version=__version__, prog_name="aomaker", message_color="green")
@click.pass_context
def main(ctx):
    click.echo(__image__)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(help="Run testcases.", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("-e", "--env", help="Switch test environment.")
@click.option("--log_level", default="info",
              type=click.Choice(["trace", "debug", "info", "success", "warning", "error", "critical"]),
              help="Set running log level.")
@click.option("--mp", "--multi-process", help="Enable multi-process running mode.", is_flag=True)
@click.option("--mt", "--multi-thread", help="Enable multi-thread running mode.", is_flag=True)
@click.option("--dist-suite", "d_suite",
              help="Distribute each test package under the test suite to a different worker.")
@click.option("--dist-file", "d_file", help="Distribute each test file under the test package to a different worker.")
@click.option("--dist-mark", "d_mark", help="Distribute each test mark to a different worker.", type=QUOTED_STR)
@click.option("--no_login", help="Don't login and make headers.", is_flag=True, flag_value=False, default=True)
@click.option("--no_gen", help="Don't generate allure reports.", is_flag=True, flag_value=False, default=True)
@click.pass_context
def run(ctx, env, log_level, mp, mt, d_suite, d_file, d_mark, no_login, no_gen, **custom_kwargs):
    if len(sys.argv) == 2:
        ctx.exit(ctx.get_help())
    pytest_args = ctx.args
    # 执行自定义参数
    _cli_hook.ctx = ctx
    _cli_hook.custom_kwargs = custom_kwargs
    if env:
        set_conf_file(env)
    if log_level != "info":
        click.echo(emojize(f":rocket:<AoMaker>切换日志等级：{log_level}"))
        AoMakerLogger.change_level(log_level)
    login_obj = _handle_login(no_login)
    from aomaker.runner import run as runner_run, processes_run, threads_run
    if mp:
        click.echo("🚀<AoMaker> 多进程模式准备启动...")
        processes_run(_handle_dist_mode(d_mark, d_file, d_suite), login=login_obj, extra_args=pytest_args,
                      is_gen_allure=no_gen)
        ctx.exit()
    elif mt:
        click.echo("🚀<AoMaker> 多线程模式准备启动...")
        threads_run(_handle_dist_mode(d_mark, d_file, d_suite), login=login_obj, extra_args=pytest_args,
                    is_gen_allure=no_gen)
        ctx.exit()
    click.echo("🚀<AoMaker> 单进程模式准备启动...")
    runner_run(pytest_args, login=login_obj, is_gen_allure=no_gen)
    ctx.exit()


@main.command()
@click.argument("project_name")
def create(project_name):
    """ Create a new project with template structure.

    Arguments:\n
    PROJECT_NAME: Name of the project to create.
    """
    create_scaffold(project_name)
    click.echo(emojize(":beer_mug: 项目脚手架创建完成！"))


@main.command()
@click.option("-t", "--template", help="Set template of swagger.Default template: restful.",
              type=click.Choice(["qingcloud", "restful"]), default="restful")
@click.argument("file_path", )
def make(file_path, template):
    """Make Api object by YAML/Swagger(Json)

    Arguments:\n
    FILE_PATH: Specify YAML/Swagger file path.The file suffix must be '.yaml','.yml' or '.json'.
    """
    main_make(file_path, template)
    click.echo(emojize(":beer_mug: Api Object渲染完成！"))


@main.command()
@click.argument("file_path")
def case(file_path):
    """Make testcases by YAML.

    Arguments:\n
    FILE_PATH: YAML file path.
    """
    main_case(file_path)
    click.echo(emojize(":beer_mug: 用例脚本编写完成！"))


@main.command()
@click.argument("file_path")
def mcase(file_path):
    """A combined command of 'make' and 'case'.

    Arguments:\n
    FILE_PATH: YAML file path.
    """
    main_make_case(file_path)
    click.echo(emojize(":beer_mug: 测试用例生产完成！"))


@main.command()
@click.argument("har_path")
@click.argument("yaml_path")
@click.option("--filter_str", help="Specify filter keyword, only url include filter string will be converted.")
@click.option("--exclude_str", help="Specify exclude keyword, url that includes exclude string will be ignored, "
                                    "multiple keywords can be joined with '|'")
@click.option("--save_response", is_flag=True, help="Save response.")
@click.option("--save_headers", is_flag=True, help="Save headers.")
def har2y(har_path, yaml_path, filter_str, exclude_str, save_response, save_headers):
    """Convert HAR(HTTP Archive) to YAML testcases for AoMaker.

    Arguments:\n
    HAR_PATH: HAR file path.
    FILE_PATH: YAML file path.
    """

    class Args:
        def __init__(self):
            self.har_path = har_path
            self.yaml_path = yaml_path
            self.filter_str = filter_str
            self.exclude_str = exclude_str
            self.save_response = save_response
            self.save_headers = save_headers

    main_har2yaml(Args())
    click.echo(emojize(":beer_mug: har转换yaml完成！"))


@main.command()
@click.argument("file_name")
@click.option("-f", "--filter_str", help=f"""Specify filter keyword.\n{filter_expression}""")
@click.option("-p", "--port", type=int, default=8082, help='Specify proxy service port.default port:8082.')
@click.option("--flow_detail", type=int, default=0, help="""
    The display detail level for flows in mitmdump: 0 (almost quiet) to 4 (very verbose).\n
    0(default): shortened request URL, response status code, WebSocket and TCP message notifications.\n
    1: full request URL with response status code.\n
    2: 1 + HTTP headers.\n
    3: 2 + truncated response content, content of WebSocket and TCP messages.\n
    4: 3 + nothing is truncated.\n""")
@click.option("--save_response", is_flag=True, help="Save response.")
@click.option("--save_headers", is_flag=True, help="Save headers.")
def record(file_name, filter_str, port, flow_detail, save_response, save_headers):
    """Record flows: parse command line options and run commands.

    Arguments:\n
    FILE_NAME: Specify YAML file name.
    """

    class Args:
        def __init__(self):
            self.file_name = file_name
            self.filter_str = filter_str
            self.port = port
            self.level = flow_detail
            self.save_response = save_response
            self.save_headers = save_headers

    main_record(Args())


def _handle_login(is_login: bool):
    if is_login is False:
        return
    sys.path.append(os.getcwd())
    exec('from login import Login')
    login_obj = locals()['Login']()
    return login_obj


def set_conf_file(env):
    conf_path = os.path.join(CONF_DIR, Conf.CONF_NAME)
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            doc = yaml.safe_load(f)
        doc['env'] = env
        if not doc.get(env):
            click.echo(emojize(f'	:confounded_face: 测试环境-{env}还未在配置文件中配置！'))
            sys.exit(1)
        with open(conf_path, 'w') as f:
            yaml.safe_dump(doc, f, default_flow_style=False)
        click.echo(emojize(f':rocket:<AoMaker> 当前测试环境: {env}'))
    else:
        click.echo(emojize(f':confounded_face: 配置文件{conf_path}不存在'))
        sys.exit(1)


def _handle_dist_mode(d_mark, d_file, d_suite):
    if d_mark:
        params = [f"-m {mark}" for mark in d_mark]
        mode_msg = "dist-mark"
        click.echo(f"🚀<AoMaker> 分配模式: {mode_msg}")
        return params

    if d_file:
        params = {"path": d_file}
        mode_msg = "dist-file"
        click.echo(f"🚀<AoMaker> 分配模式: {mode_msg}")
        return params

    if d_suite:
        params = d_suite
        mode_msg = "dist-suite"
        click.echo(f"🚀<AoMaker> 分配模式: {mode_msg}")
        return params

    params = _handle_aomaker_yaml()
    mode_msg = "dist-mark(aomaker.yaml策略)"
    click.echo(f"🚀<AoMaker> 分配模式: {mode_msg}")
    return params


def _handle_aomaker_yaml() -> List[Text]:
    if not os.path.exists(AOMAKER_YAML_PATH):
        click.echo(emojize(f':confounded_face: aomaker策略文件{AOMAKER_YAML_PATH}不存在！'))
        sys.exit(1)
    yaml_data = load_yaml(AOMAKER_YAML_PATH)
    content = AomakerYaml(**yaml_data)
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


def main_arun_alias():
    """ command alias
        arun = aomaker run
    """
    sys.argv.insert(1, "run")
    # if len(sys.argv) != 2:
    #     sys.argv.insert(1, "run")
    #     click.echo(sys.argv)
    main()


def main_make_alias():
    """ command alias
        amake = aomaker make
    """
    sys.argv.insert(1, "make")
    main()


def main_record_alias():
    """ command alias
        arec = aomaker record
    """
    sys.argv.insert(1, "record")
    main()


load_plugin()

if __name__ == '__main__':
    main()
