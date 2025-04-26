# --coding:utf-8--
import os
import ast
import sys
import json
from typing import List, Text
import webbrowser
from threading import Timer
from pathlib import Path

import click
import uvicorn
from ruamel.yaml import YAML
from click_help_colors import HelpColorsGroup, version_option
from rich.console import Console
from rich.theme import Theme
from rich.table import Table

from aomaker import __version__, __image__
from aomaker._constants import Conf
from aomaker.log import logger, AoMakerLogger
from aomaker.path import CONF_DIR, AOMAKER_YAML_PATH, DIST_STRATEGY_PATH
from aomaker.hook_manager import cli_hook
from aomaker.param_types import QUOTED_STR
from aomaker.scaffold import create_scaffold

from aomaker.utils.utils import load_yaml
from aomaker.models import DistStrategyYaml
from aomaker.maker.config import OpenAPIConfig, NAMING_STRATEGIES
from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.generator import Generator
from aomaker._printer import print_message

SUBCOMMAND_RUN_NAME = "run"
yaml = YAML()


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
@click.option("--no_login", help="Don't login and make headers.", is_flag=True, flag_value=False, default=True)
@click.option("--no_gen", help="Don't generate allure reports.", is_flag=True, flag_value=False, default=True)
@click.option("-p", "--processes", default=None, type=int,
              help="Number of processes to run concurrently. Defaults to the number of CPU cores available on the system.")
@click.pass_context
def run(ctx, env, log_level, mp, mt, d_suite, d_file, d_mark, no_login, no_gen, processes, **custom_kwargs):
    pytest_args = ctx.args
    extra_custom_kwargs = ctx.obj or {}
    all_custom_kwargs = {**custom_kwargs, **extra_custom_kwargs}
    _run(ctx, env, log_level, mp, mt, d_suite, d_file, d_mark, no_login, no_gen, pytest_args, processes,
         **all_custom_kwargs)


@main.command()
@click.argument("project_name")
def create(project_name):
    """ Create a new project with template structure.

    Arguments:\n
    PROJECT_NAME: Name of the project to create.
    """
    create_scaffold(project_name)
    print_message(":beer_mug: 项目脚手架创建完成！", style="bold green")


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
    openapi_config = {}
    try:
        if Path(AOMAKER_YAML_PATH).exists():
            yaml_data = load_yaml(AOMAKER_YAML_PATH)
            openapi_config = yaml_data.get('openapi', {})
    except Exception as e:
        print_message(f"❌ 读取配置文件失败: {e}", style="bold red")
        sys.exit(1)
    
    # 命令行参数优先级高于配置文件
    final_spec = spec or openapi_config.get('spec')
    if not final_spec:
        print_message("❌  错误：必须在命令行参数或配置文件中提供spec参数", style="bold red")
        sys.exit(1)
    final_output = output or openapi_config.get('output')
    final_class_name_strategy = class_name_strategy or openapi_config.get('class_name_strategy')
    final_custom_strategy = custom_strategy or openapi_config.get('custom_strategy','')
    final_base_api_class = base_api_class or openapi_config.get('base_api_class')
    final_base_api_class_alias = base_api_class_alias or openapi_config.get('base_api_class_alias')

    naming_strategy = NAMING_STRATEGIES["operation_id"]
    if final_class_name_strategy in NAMING_STRATEGIES:
        naming_strategy = NAMING_STRATEGIES[final_class_name_strategy]
    
    import yaml
    
    if final_spec.startswith(('http://', 'https://')):
        import requests
        try:
            response = requests.get(final_spec)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')

            if 'json' in content_type:
                doc = response.json()
            elif 'yaml' in content_type or 'yml' in content_type:
                doc = yaml.safe_load(response.text)
            else:
                try:
                    doc = response.json()
                except:
                    doc = yaml.safe_load(response.text)
        except Exception as e:
            print_message(f"获取或解析URL失败: {e}", style="bold red")
            return
    else:
        spec_path = Path(final_spec)

        if not spec_path.exists():
            print_message(f"文件不存在: {final_spec}", style="bold red")
            return

        file_suffix = spec_path.suffix.lower()
        try:
            with spec_path.open('r', encoding='utf-8') as f:
                if file_suffix == '.json':
                    doc = json.load(f)
                elif file_suffix in ['.yaml', '.yml']:
                    doc = yaml.safe_load(f)
                else:
                    content = f.read()
                    try:
                        doc = json.loads(content)
                    except json.JSONDecodeError:
                        doc = yaml.safe_load(content)
        except Exception as e:
            print_message(f"读取或解析文件失败: {e}", style="bold red")
            return

    output_path = Path(final_output)
    output_path.mkdir(parents=True, exist_ok=True)

    config = OpenAPIConfig(
        class_name_strategy=naming_strategy,
        base_api_class=final_base_api_class,
        base_api_class_alias=final_base_api_class_alias,
        custom_strategy=final_custom_strategy
    )

    custom_theme = Theme({
        "primary": "#7B61FF",
        "secondary": "#00C7BE",
        "success": "#34D399",
        "warning": "#FBBF24",
        "error": "#EF4444",
        "highlight": "#F472B6",
        "muted": "#94A3B8",
        "accent": "#38BDF8",
        "gradient_start": "#8B5CF6",
        "gradient_end": "#EC4899"
    })

    console = Console(theme=custom_theme)
    console.print(
        "[bold gradient(75)][gradient_start]⚡[/][gradient_end]AOMaker OpenAPI Processor[/]",
        justify="center"
    )

    with console.status("[primary]🚀 Initializing...[/]", spinner="dots") as status:
        status.update("[gradient(75)]🔨 OpenAPI数据解析中...[/]")
        parser = OpenAPIParser(doc, config=config, console=console)
        api_groups = parser.parse()

        status.update("[gradient(75)]⚡ Generating code[/]")
        generator = Generator(output_dir=final_output, config=config, console=console)
        generator.generate(api_groups)

    console.print(
        "[success on black]  🍺 [bold]All API Objects generation completed![/]  ",
        style="blink bold", justify="center"
    )


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


def _run(ctx, env, log_level, mp, mt, d_suite, d_file, d_mark, no_login, no_gen, pytest_args, processes,
         **custom_kwargs):
    if len(sys.argv) == 2:
        ctx.exit(ctx.get_help())
    # 执行自定义参数
    cli_hook.ctx = ctx
    cli_hook.custom_kwargs = custom_kwargs
    if env:
        set_conf_file(env)
    if log_level != "info":
        print_message(f":wrench:切换日志等级：{log_level}")
        AoMakerLogger.change_level(log_level)
    login_obj = _handle_login(no_login)
    from aomaker.runner import run as runner_run, processes_run, threads_run
    if mp:
        print_message("🚀多进程模式准备启动...")
        processes_run(_handle_dist_mode(d_mark, d_file, d_suite), login=login_obj, extra_args=pytest_args,
                      is_gen_allure=no_gen, process_count=processes)
        ctx.exit()
    elif mt:
        print_message("🚀多线程模式准备启动...")
        threads_run(_handle_dist_mode(d_mark, d_file, d_suite), login=login_obj, extra_args=pytest_args,
                    is_gen_allure=no_gen)
        ctx.exit()
    print_message("🚀单进程模式准备启动...")
    runner_run(pytest_args, login=login_obj, is_gen_allure=no_gen)
    ctx.exit()


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
            doc = yaml.load(f)
        doc['env'] = env
        if not doc.get(env):
            print_message(f'	:confounded_face: 测试环境-{env}还未在配置文件中配置！', style="bold red")
            sys.exit(1)
        with open(conf_path, 'w') as f:
            yaml.dump(doc, f)
        print_message(f':globe_with_meridians: 当前测试环境: {env}')
    else:
        print_message(f':confounded_face: 配置文件{conf_path}不存在', style="bold red")
        sys.exit(1)


def _handle_dist_mode(d_mark, d_file, d_suite):
    if d_mark:
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

    params = _handle_dist_strategy_yaml()
    mode_msg = "dist-mark(dist_strategy.yaml策略)"
    print_message(f":hammer_and_wrench: 分配模式: {mode_msg}")
    return params


def _handle_dist_strategy_yaml() -> List[Text]:
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
             no_login: bool = True,
             no_gen: bool = True,
             pytest_args: List[str] = None,
             **custom_kwargs):
    print(__image__)
    cli_hook()

    from click.testing import CliRunner
    runner = CliRunner()
    args = []

    if env:
        args.extend(["--env", env])
    if log_level:
        args.extend(["--log_level", log_level])
    if mp:
        args.append("--mp")
    if mt:
        args.append("--mt")
    if d_suite:
        args.extend(["--dist-suite", d_suite])
    if d_file:
        args.extend(["--dist-file", d_file])
    if d_mark:
        args.extend(["--dist-mark", d_mark])
    if not no_login:
        args.append("--no_login")
    if not no_gen:
        args.append("--no_gen")

    if pytest_args:
        args.append("--")
        args.extend(pytest_args)

    result = runner.invoke(run, args=args, standalone_mode=False, obj=custom_kwargs)
    if result.exit_code != 0:
        from aomaker.storage import cache, config
        cache.clear()
        cache.close()
        config.close()
        raise result.exception


if __name__ == '__main__':
    main()
