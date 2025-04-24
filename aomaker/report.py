# --coding:utf-8--
import os
import shutil  # 导入 shutil

from jinja2 import Template

from aomaker.utils.gen_allure_report import CaseSummary, CaseDetail
from aomaker.path import REPORT_DIR  # 假设有一个指向报告目录的常量
from aomaker._printer import printer

# 假设 logo/icon 文件位于 aomaker/html/assets/ 目录下
base_dir = os.path.dirname(__file__)
source_html_dir = os.path.join(base_dir, "html")
source_assets_dir = os.path.join(source_html_dir, "assets") # 源资源目录


class HtmlMaker:
    # report_target_dir 默认为 AOMAKER_HTML_DIR
    def __init__(self, report_target_dir=REPORT_DIR):
        self.template_html_path = os.path.join(source_html_dir, "template.html")
        self.report_target_dir = report_target_dir
        self.report_html_file_path = os.path.join(self.report_target_dir, "index.html") # 报告文件名改为 index.html
        self.target_assets_dir = os.path.join(self.report_target_dir, "assets") # 这行是正确的

        # 确保目标目录存在
        os.makedirs(self.report_target_dir, exist_ok=True)
        os.makedirs(self.target_assets_dir, exist_ok=True)

    @staticmethod
    def gen_html_to_str(html_path: str) -> str:
        """读取.html文件内容"""
        with open(html_path, 'r', encoding="utf-8") as f:
            html_str = f.read()
        return html_str

    @staticmethod
    def render_html(html_str: str, render_content):
        temp = Template(html_str)
        temp_str = temp.render(render_content)
        return temp_str

    def copy_assets(self):
        """将源 assets 目录内容复制到目标 assets 目录"""
        if os.path.exists(source_assets_dir):
            # 为了避免覆盖，可以先清空目标目录，或者逐个复制并处理冲突
            # 这里采用简单覆盖的方式
            if os.path.exists(self.target_assets_dir):
                 shutil.rmtree(self.target_assets_dir) # 清空目标防止旧文件残留
            shutil.copytree(source_assets_dir, self.target_assets_dir)
            # printer.print_info(f"Assets copied to {self.target_assets_dir}") # 注释掉或删除这行
            print(f"[INFO] Assets copied to {self.target_assets_dir}") # 改为这行
        else:
            # printer.print_warning(f"Source assets directory not found: {source_assets_dir}") # 注释掉或删除这行
            print(f"[WARNING] Source assets directory not found: {source_assets_dir}") # 改为这行


    def render_template_html(self, render_content: dict):
        """将所有内容直接渲染到 index.html"""
        # 1. 复制资源文件
        self.copy_assets()

        # 2. 读取并渲染 template.html
        template_str = self.gen_html_to_str(self.template_html_path)
        rendered_html = self.render_html(template_str, render_content)

        # 3. 写入目标报告文件 index.html
        with open(self.report_html_file_path, "w", encoding='utf-8') as f:
            f.write(rendered_html)
        # printer.print_info(f"HTML report generated at: {self.report_html_file_path}") # 注释掉或删除这行
        print(f"[INFO] HTML report generated at: {self.report_html_file_path}") # 改为这行


@printer("gen_rep")
def gen_reports():
    case_summary = CaseSummary()
    case_detail = CaseDetail()
    # 数据准备 (保持不变)
    summary = {
        "title": "AoMaker Test Report", # 可以增加一个标题
        "total": case_summary.total_count,
        "passed_count": case_summary.passed_count,
        "failed_count": case_summary.failed_count,
        "error_count": case_summary.broken_count,
        "skipped_count": case_summary.skipped_count,
        "passed_rate": case_summary.passed_rate,
        "error_rate": case_summary.broken_rate,
        "skipped_rate": case_summary.skipped_rate, # 这里之前可能是错误的用了 skipped_count
        "failed_rate": case_summary.failed_rate,
        "duration": case_summary.duration,
        "start_time": case_summary.start_time,
        "end_time": case_summary.stop_time,
        "case_list": case_detail.case_detail_info()
    }
    # 传入报告目录路径
    html_maker = HtmlMaker(report_target_dir=REPORT_DIR)
    html_maker.render_template_html(summary)

# 注意: 需要确保 aomaker/path.py 中定义了 AOMAKER_HTML_DIR
# 并且 aomaker/html/assets/ 目录下存放了 aomaker-logo.png 和 aomaker-icon.png
# 另外，之前 report.html 中的 skipped_rate 可能绑定到了 skipped_count，这里修正为 skipped_rate (假设 CaseSummary 有这个属性)
# 如果 CaseSummary 没有 skipped_rate，需要计算 (skipped_count / total * 100)
