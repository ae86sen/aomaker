# --coding:utf-8--
import os
import shutil
import subprocess

from aomaker._printer import printer, print_message
from aomaker.storage import config
from aomaker._constants import Allure
from aomaker.report import gen_aomaker_reports
from aomaker.utils.gen_allure_report import rewrite_summary
from aomaker.path import ALLURE_JSON_DIR

def gen_allure(is_clear=True) -> bool:
    cmd = f'allure generate "{Allure.JSON_DIR}" -o "{Allure.HTML_DIR}"'
    if is_clear:
        cmd += ' -c'

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        rewrite_summary()
        return True
    else:
        error_lines = [
            f"[bold red]❌ 测试报告收集失败![/bold red]",
            f"   命令: {cmd}",
            f"   返回码: {result.returncode}",
        ]
        if result.stderr:
            stderr_formatted = result.stderr.strip()
            error_lines.append(f"   [red]标准错误:[/red]\n      {stderr_formatted}")
        error_lines.extend([
            "   请检查:",
            "     1. 是否已正确安装 Allure Commandline (https://allurereport.org/)",
            "     2. allure 命令是否已添加到系统 PATH 环境变量中"
        ])

        for line in error_lines:
            print_message(line, style="red", prefix="")
        return False


def allure_env_prop():
    conf: dict = config.get_all()
    if conf:
        content = ""
        for k, v in conf.items():
            content += f"{k}={v}\n"
        os.makedirs(ALLURE_JSON_DIR, exist_ok=True)
        with open(os.path.join(ALLURE_JSON_DIR, "environment.properties"), mode='w', encoding='utf-8') as f:
            f.write(content)


@printer("测试完成, AoMaker开始收集报告...", "AoMaker已完成测试报告(reports/aomaker-report.html)!")
def gen_reports():
    allure_env_prop()
    is_gen_allure_success = gen_allure()
    if is_gen_allure_success == False:
        return 1
    gen_aomaker_reports()


def clean_allure_json(allure_json_path: str=ALLURE_JSON_DIR):
    shutil.rmtree(allure_json_path, ignore_errors=True)