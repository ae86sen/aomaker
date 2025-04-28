# --coding:utf-8--
import os
import ast
import sys
from typing import List
import webbrowser
from threading import Timer
from pathlib import Path

import click
import uvicorn
from click_help_colors import HelpColorsGroup, version_option
from rich.console import Console
from rich.table import Table

from aomaker import __version__, __image__
from aomaker.log import AoMakerLogger
from aomaker.hook_manager import cli_hook
from aomaker.param_types import QUOTED_STR
from aomaker.scaffold import create_scaffold
from aomaker.maker.config import NAMING_STRATEGIES
from aomaker._printer import print_message

from aomaker.maker.cli_handlers import handle_gen_models
from aomaker.config_handlers import handle_dist_strategy_yaml

SUBCOMMAND_RUN_NAME = "run"


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
    cli_hook()


@main.group()
def show():
    """Show various statistics."""
    pass


@main.group()
def gen():
    """Generate various statistics or attrs models."""
    pass

@main.group()
def service():
    """Aomaker Service."""
    pass


@main.group()
def mock():
    """Aomaker mock server."""
    pass

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
@click.option("--skip_login", help="Skip login and no headers.", is_flag=True, default=False)
@click.option("--no_gen", help="Don't generate allure reports.", is_flag=True, flag_value=False, default=True)
@click.option("-p", "--processes", default=None, type=int,
              help="Number of processes to run concurrently. Defaults to the number of CPU cores available on the system.")
@click.pass_context
def run(ctx, env, log_level, mp, mt, d_suite, d_file, d_mark, skip_login, no_gen, processes, **custom_kwargs):
    from aomaker.runner import run_tests, RunConfig
    pytest_args = ctx.args
    extra_custom_kwargs = ctx.obj or {}
    all_custom_kwargs = {**custom_kwargs, **extra_custom_kwargs}
    if len(sys.argv) == 2:
        ctx.exit(ctx.get_help())
    # 执行自定义参数
    cli_hook.ctx = ctx
    cli_hook.custom_kwargs = all_custom_kwargs

    if log_level != "info":
        print_message(f":wrench:切换日志等级：{log_level}")
        AoMakerLogger.change_level(log_level)

    login_obj = _handle_login(skip_login)

    task_args = None
    run_mode = "main"
    if mp or mt:
        run_mode = "mp" if mp else "mt"
        task_args = _handle_dist_mode(d_mark, d_file, d_suite)
    
    run_config = RunConfig(
        env=env,
        run_mode=run_mode,
        task_args=task_args,
        pytest_args=pytest_args,
        login_obj=login_obj,
        report_enabled=no_gen,
        processes=processes
        )

    run_tests(run_config)


@main.command()
@click.argument("project_name")
def create(project_name):
    """ Create a new project with template structure.

    Arguments:\n
    PROJECT_NAME: Name of the project to create.
    """
    create_scaffold(project_name)


@gen.command(name="models")
@click.option("--spec", "-s",
              help="OpenAPI规范文件路径（JSON/YAML/URL）")
@click.option("--output", "-o", help="代码输出目录")
@click.option("--class-name-strategy", "-c",
              type=click.Choice(list(NAMING_STRATEGIES.keys()), case_sensitive=False),
              default="operation_id",
              show_default=True,
              help="API Object Class name生成策略（operation_id/summary/tags）")
@click.option("--custom-strategy", "-cs", required=False,
              help="自定义命名策略的Python模块路径 (例如: 'mypackage.naming.custom_function')")
@click.option("--base-api-class", "-B", default="aomaker.core.api_object.BaseAPIObject",
              show_default=True,
              help="API基类完整路径（module.ClassName格式）")
@click.option("--base-api-class-alias", "-A",
              help="基类在生成代码中的别名")
def gen_models(spec, output, class_name_strategy,custom_strategy,base_api_class, base_api_class_alias):
    """
    Generate Attrs models from an OpenAPI specification.
    """
    handle_gen_models(spec, output, class_name_strategy, custom_strategy, base_api_class, base_api_class_alias)

@show.command(name="stats")
@click.option("--package", help="Package name to filter by.")
@click.option("--showindex", is_flag=True, default=False, help="Enable to show index.")
def query_stats(package, showindex):
    """Query API statistics with optional filtering."""
    from aomaker.storage import stats
    conditions = {}

    if package:
        conditions['package'] = package

    results = stats.get(conditions=conditions)
    print_message(f"Total APIs: {len(results)}", style="bold green")

    console = Console()
    table = Table(show_header=True, header_style="bold magenta", title="API Statistics", show_edge=True, border_style="green")

    if showindex:
        table.add_column("Index", style="dim", width=6)
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("ApiName", style="green")

    for index, item in enumerate(results):
        row_data = []
        if showindex:
            row_data.append(str(index))
        package_name = str(item.get('package', 'N/A'))
        api_name = str(item.get('api_name', 'N/A'))
        row_data.extend([package_name, api_name])
        table.add_row(*row_data)

    console.print(table)


@gen.command(name="stats")
@click.option("--api-dir", default="apis", type=click.Path(exists=True), show_default=True, help="Specify the api dir.")
def gen_stats(api_dir):
    _generate_apis(api_dir)
    print_message(":beer_mug: 接口信息统计完毕！", style="bold green")


@service.command(help="Start a web service.")
@click.option('--web', is_flag=True, help="Open the web interface in a browser.")
@click.option('--port', default=8888, help="Specify the port number to run the server on. Default is 8888.")
def start(web, port):
    from aomaker.service import app
    progress_url = f"http://127.0.0.1:{port}/statics/progress.html"
    if web:
        Timer(2, open_web, args=[progress_url]).start()
    uvicorn.run(app, host="127.0.0.1", port=port)


@mock.command(help="Start the mock server.")
@click.option('--web', is_flag=True, help="Open the API documentation in a browser.")
@click.option('--port', default=9999, help="Specify the port number to run the mock server on. Default is 9999.")
def start(web, port):
    """Start the mock server."""
    from aomaker.mock.mock_server import app
    docs_url = f"http://127.0.0.1:{port}/api/docs"
    if web:
        Timer(2, open_web, args=[docs_url]).start()
    print_message(f"🚀 启动Mock服务器在端口 {port}")
    print_message(f"📚 API文档地址: {docs_url}")
    uvicorn.run(app, host="127.0.0.1", port=port)

def open_web(url):
    webbrowser.open(url)

def _parse_all_from_ast(filepath: Path):
    with filepath.open(encoding='utf-8') as f:
        tree = ast.parse(f.read())

    # AST解析逻辑保持不变
    all_items = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if node.targets[0].id == '__ALL__':
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for element in node.value.elts:
                        if isinstance(element, (ast.Str, ast.Constant)):
                            all_items.append(element.s if isinstance(element, ast.Str) else element.value)
    return all_items


def _generate_apis(api_dir: str):
    from aomaker.storage import stats
    root_dir = Path(api_dir)

    for apis_path in root_dir.rglob('apis.py'):
        try:
            package_path = apis_path.parent.relative_to(root_dir)
        except ValueError:
            continue

        package_name = '.'.join(package_path.parts) if package_path.parts else ''
        interfaces = _parse_all_from_ast(apis_path)

        for interface in interfaces:
            stats.set(package=package_name, api_name=interface)


def _handle_login(skip_login: bool):
    if skip_login is True:
        return
    sys.path.append(os.getcwd())
    exec('from login import Login')
    login_obj = locals()['Login']()
    return login_obj


def _handle_dist_mode(d_mark, d_file, d_suite):
    if d_mark:
        if isinstance(d_mark, str):
            d_mark = d_mark.split(" ")
        params = [f"-m {mark}" for mark in d_mark]
        mode_msg = "dist-mark"
        print_message(f":hammer_and_wrench: 分配模式: {mode_msg}")
        return params

    if d_file:
        params = {"path": d_file}
        mode_msg = "dist-file"
        print_message(f":hammer_and_wrench: 分配模式: {mode_msg}")
        return params

    if d_suite:
        params = d_suite
        mode_msg = "dist-suite"
        print_message(f":hammer_and_wrench: 分配模式: {mode_msg}")
        return params

    params = handle_dist_strategy_yaml()
    mode_msg = "dist-mark(dist_strategy.yaml策略)"
    print_message(f":hammer_and_wrench: 分配模式: {mode_msg}")
    return params



def main_arun_alias():
    """ command alias
        arun = aomaker run
    """
    sys.argv.insert(1, "run")
    # if len(sys.argv) != 2:
    #     sys.argv.insert(1, "run")
    #     click.echo(sys.argv)
    main()


def main_run(env: str = None,
             log_level: str = "info",
             mp: bool = False,
             mt: bool = False,
             d_suite: str = None,
             d_file: str = None,
             d_mark: str = None,
             skip_login: bool = False,
             no_gen: bool = True,
             pytest_args: List[str] = None,
             processes: int = None,
             **custom_kwargs):
    print(__image__)
    cli_hook.custom_kwargs = custom_kwargs
    cli_hook()
    if cli_hook.custom_kwargs:
        cli_hook.run()

    if pytest_args is None:
        pytest_args = []

    if log_level != "info":
        print_message(f":wrench:切换日志等级：{log_level}")
        AoMakerLogger.change_level(log_level)

    login_obj = _handle_login(skip_login)

    task_args = None
    run_mode = "main"
    if mp or mt:
        run_mode = "mp" if mp else "mt"
        task_args = _handle_dist_mode(d_mark, d_file, d_suite)
    from aomaker.runner import run_tests, RunConfig
    run_config = RunConfig(
        env=env,
        run_mode=run_mode,
        task_args=task_args,
        pytest_args=pytest_args,
        login_obj=login_obj,
        report_enabled=no_gen,
        processes=processes
        )
    
    run_tests(run_config)


if __name__ == '__main__':
    main()
