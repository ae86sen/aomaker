import sys
import json
from typing import Optional, Dict, Any
from pathlib import Path

import requests
import yaml
from rich.console import Console
from rich.theme import Theme
from rich.table import Table

from aomaker.path import AOMAKER_YAML_PATH

from aomaker.utils.utils import load_yaml
from aomaker.maker.config import OpenAPIConfig, NAMING_STRATEGIES
from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.generator import Generator
from aomaker._printer import print_message


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

def _resolve_gen_models_config(
        spec: Optional[str],
        output: Optional[str],
        class_name_strategy: Optional[str],
        custom_strategy: Optional[str],
        base_api_class: Optional[str],
        base_api_class_alias: Optional[str]
) -> Dict[str, Any]:
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
    
    warnings = []

    # 判定CLI是否显式传参
    cli_c = class_name_strategy is not None
    cli_cs = custom_strategy is not None

    if cli_c and cli_cs:
        warnings.append("检测到同时传入 -c 和 -cs，已优先使用 -cs（自定义命名策略）")

    # 命名策略合并：-cs > -c；若仅传 -c，则忽略配置文件中的 custom_strategy
    if cli_cs:
        final_custom_strategy = custom_strategy
    elif cli_c:
        final_custom_strategy = None
    else:
        final_custom_strategy = openapi_config.get('custom_strategy')

    final_config = {
        "final_spec": final_spec,
        "final_output": output or openapi_config.get('output'),
        "final_class_name_strategy": class_name_strategy if cli_c else openapi_config.get('class_name_strategy'),
        "final_custom_strategy": final_custom_strategy,
        "final_base_api_class": base_api_class if base_api_class is not None else openapi_config.get('base_api_class'),
        "final_base_api_class_alias": base_api_class_alias if base_api_class_alias is not None else openapi_config.get('base_api_class_alias'),
        "warnings": warnings
    }

    return final_config

def _fetch_and_parse_openapi_spec(final_spec: str) -> Optional[Dict[str, Any]]:
    if final_spec.startswith(('http://', 'https://')):
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
            print_message(f"❌获取或解析URL失败: {e}", style="bold red")
            sys.exit(1)
    else:
        spec_path = Path(final_spec)

        if not spec_path.exists():
            print_message(f"❌ 文件不存在: {final_spec}", style="bold red")
            sys.exit(1)

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
            print_message(f"❌ 读取或解析文件失败: {e}", style="bold red")
            sys.exit(1)

    return doc


def handle_gen_models(spec: Optional[str],
                      output: Optional[str],
                      class_name_strategy: Optional[str],
                      custom_strategy: Optional[str],
                      base_api_class: Optional[str],
                      base_api_class_alias: Optional[str]):

    final_config = _resolve_gen_models_config(spec, output,
                                              class_name_strategy, custom_strategy,
                                              base_api_class, base_api_class_alias)
    final_class_name_strategy = final_config['final_class_name_strategy']
    final_output = final_config['final_output']
    final_base_api_class = final_config['final_base_api_class']
    final_base_api_class_alias = final_config['final_base_api_class_alias']
    final_custom_strategy = final_config['final_custom_strategy']

    default_base = "aomaker.core.api_object.BaseAPIObject"
    console = Console(theme=custom_theme)

    table = Table(title="最终生效配置", show_header=True, header_style="bold magenta", show_edge=True, border_style="green")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    cn = final_class_name_strategy or "operation_id(default)"
    cs = final_custom_strategy or "-"
    base = final_base_api_class or f"{default_base}(default)"
    alias = final_base_api_class_alias or "-"

    table.add_row("spec", final_config['final_spec'])
    table.add_row("output", final_output or "-")
    table.add_row("class_name_strategy", cn)
    table.add_row("custom_strategy", cs)
    table.add_row("base_api_class", base)
    table.add_row("base_api_class_alias", alias)

    console.print(table)

    for w in final_config.get('warnings', []):
        console.print(f"[bold yellow]⚠️ {w}[/]")

    naming_strategy = NAMING_STRATEGIES["operation_id"]
    if final_class_name_strategy in NAMING_STRATEGIES:
        naming_strategy = NAMING_STRATEGIES[final_class_name_strategy]

    doc = _fetch_and_parse_openapi_spec(final_config['final_spec'])

    output_path = Path(final_output)
    output_path.mkdir(parents=True, exist_ok=True)

    # 仅在非None时传参，避免用None覆盖默认值
    config_kwargs = {
        "class_name_strategy": naming_strategy
    }
    if final_base_api_class is not None:
        config_kwargs["base_api_class"] = final_base_api_class
    if final_base_api_class_alias is not None:
        config_kwargs["base_api_class_alias"] = final_base_api_class_alias
    if final_custom_strategy:
        config_kwargs["custom_strategy"] = final_custom_strategy

    config = OpenAPIConfig(**config_kwargs)

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
