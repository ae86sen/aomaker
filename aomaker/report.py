# --coding:utf-8--
from pathlib import Path

from jinja2 import Template

from aomaker.utils.gen_allure_report import CaseSummary, CaseDetail
from aomaker.path import REPORT_DIR
from aomaker.storage import config

base_dir = Path(__file__).parent
source_html_dir = base_dir / "html"


class HtmlMaker:
    def __init__(self, report_target_dir=REPORT_DIR):
        self.template_html_path = source_html_dir / "template.html"
        self.report_target_dir = Path(report_target_dir)
        self.report_html_file_path = self.report_target_dir / "aomaker-report.html" 

        self.report_target_dir.mkdir(exist_ok=True)

    @staticmethod
    def gen_html_to_str(html_path: Path) -> str:
        """读取.html文件内容"""
        with open(html_path, 'r', encoding="utf-8") as f:
            html_str = f.read()
        return html_str

    @staticmethod
    def render_html(html_str: str, render_content):
        temp = Template(html_str)
        temp_str = temp.render(render_content)
        return temp_str


    def render_template_html(self, render_content: dict):
        """将所有内容直接渲染到 index.html"""
        template_str = self.gen_html_to_str(self.template_html_path)
        rendered_html = self.render_html(template_str, render_content)

        with open(self.report_html_file_path, "w", encoding='utf-8') as f:
            f.write(rendered_html)

def gen_aomaker_reports():
    case_summary = CaseSummary()
    case_detail = CaseDetail()
    summary = {
        "title": "AoMaker Test Report",
        "total": case_summary.total_count,
        "passed_count": case_summary.passed_count,
        "failed_count": case_summary.failed_count,
        "broken_count": case_summary.broken_count,
        "skipped_count": case_summary.skipped_count,
        "passed_rate": case_summary.passed_rate,
        "broken_rate": case_summary.broken_rate,
        "skipped_rate": case_summary.skipped_rate,
        "failed_rate": case_summary.failed_rate,
        "duration": case_summary.duration,
        "start_time": case_summary.start_time,
        "end_time": case_summary.stop_time,
        "case_list": case_detail.case_detail_info()
    }
    current_env = config.get("current_env")
    account = config.get("account")
    base_config = {
        "current_env": current_env,
        "base_url": config.get("base_url"),
        "account": account.get("user","Anonymous"),
        "tester": config.get("tester") if config.get("tester") else "Tester",
        "note": config.get("note") if config.get("note") else ""
    }
    summary["base_config"] = base_config
    html_maker = HtmlMaker(report_target_dir=Path(REPORT_DIR))
    html_maker.render_template_html(summary)

