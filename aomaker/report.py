# --coding:utf-8--
import os

from jinja2 import Template

from aomaker.utils.gen_allure_report import CaseSummary, CaseDetail
from aomaker.path import AOMAKER_HTML
from aomaker._printer import printer

base_dir = os.path.dirname(__file__)
base_html_path = os.path.join(base_dir, "html")


class HtmlMaker:
    def __init__(self, report_target_path=AOMAKER_HTML):
        self.heading_html_path = os.path.join(base_html_path, "heading.html")
        self.report_html_path = os.path.join(base_html_path, "report.html")
        self.template_html_path = os.path.join(base_html_path, "template.html")
        self.report_target_path = report_target_path

    @staticmethod
    def gen_html_to_str(html_path: str) -> str:
        """读取.html文件内容
        html_file: heading.html,report.html
        """
        # 读取heading.html内容
        with open(html_path, 'r', encoding="utf-8") as f:
            html_str = f.read()
        return html_str

    @staticmethod
    def render_html(html_str: str, render_content):
        temp = Template(html_str)
        temp_str = temp.render(render_content)
        return temp_str

    def render_template_html(self, render_content: dict):
        """将heading.html,report.html渲染到template.html"""
        template_str = self.gen_html_to_str(self.template_html_path)
        html_path_dict = {
            "heading": self.heading_html_path,
            "report": self.report_html_path,
        }
        html_rendered_dict = {}
        # 1.分别读取并渲染heading.html,report.html,stylesheet.html
        for key, html_path in html_path_dict.items():
            html_str = self.gen_html_to_str(html_path)
            rendered_html = self.render_html(html_str, render_content)
            html_rendered_dict[key] = rendered_html

        # 2.全部内容渲染到目标报告：aoreporter.html
        with open(self.report_target_path, "w", encoding='utf-8') as f:
            temp = Template(template_str)
            temp_str = temp.render(html_rendered_dict)
            f.write(temp_str)


@printer("gen_rep")
def gen_reports():
    case_summary = CaseSummary()
    case_detail = CaseDetail()
    summary = {
        "total": case_summary.total_count,
        "passed_count": case_summary.passed_count,
        "failed_count": case_summary.failed_count,
        "error_count": case_summary.broken_count,
        "skipped_count": case_summary.skipped_count,
        "passed_rate": case_summary.passed_rate,
        "error_rate": case_summary.broken_rate,
        "skipped_rate": case_summary.skipped_count,
        "failed_rate": case_summary.failed_rate,
        "duration": case_summary.duration,
        "start_time": case_summary.start_time,
        "end_time": case_summary.stop_time,
        "case_list": case_detail.case_detail_info()
    }
    html_maker = HtmlMaker()
    html_maker.render_template_html(summary)
