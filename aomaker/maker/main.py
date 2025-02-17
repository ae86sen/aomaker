# --coding:utf-8--
import json
import sys

sys.path.insert(0, '/Users/zhanglinsen/Projects/aomaker')
from aomaker.maker.config import OpenAPIConfig
from aomaker.maker.parser import OpenAPIParser
from aomaker.maker.generator import Generator

from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    # 主色调
    "primary": "#7B61FF",  # 活力紫 (主流程指示)
    "secondary": "#00C7BE",  # 清新青 (辅助信息)

    # 功能色
    "success": "#34D399",  # 薄荷绿 (成功状态)
    "warning": "#FBBF24",  # 琥珀黄 (警告提示)
    "error": "#EF4444",  # 珊瑚红 (错误信息)

    # 文本增强
    "highlight": "#F472B6",  # 樱粉色 (关键数据高亮)
    "muted": "#94A3B8",  # 雾霾蓝 (辅助文本)
    "accent": "#38BDF8",  # 天际蓝 (交互强调)

    # 特殊效果
    "gradient_start": "#8B5CF6",  # 渐变起始色
    "gradient_end": "#EC4899"  # 渐变结束色
})

def main():
    console = Console(theme=custom_theme)
    config = OpenAPIConfig(backend_prefix="aicp", frontend_prefix="portal_api")
    with open("/api.json", 'r', encoding='utf-8') as f:
        doc = json.load(f)

    console.print(
        "[bold gradient(75)][gradient_start]⚡[/][gradient_end]AOMaker OpenAPI Processor[/]",
        justify="center"
    )

    with console.status("[primary]🚀 Initializing...[/]", spinner="dots") as status:
        status.update("[gradient(75)]🔨 OpenAPI数据解析中...[/]")
        parser = OpenAPIParser(doc, config=config,console=console)
        api_groups = parser.parse()

        status.update("[gradient(75)]⚡ Generating code[/]")
        generator = Generator(output_dir="demo", config=config,console=console)
        generator.generate(api_groups)

    console.print(
        "[success on black]  🍺 [bold]All API Objects generation completed![/]  ",
        style="blink bold", justify="center"
    )


if __name__ == '__main__':
    main()