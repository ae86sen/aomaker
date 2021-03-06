# --coding:utf-8--
import json
import os

from aomaker.path import REPORT_DIR, BASEDIR

ALLURE_HTML_PATH = os.path.join(BASEDIR, "html")
WIDGETS_PATH = os.path.join(ALLURE_HTML_PATH, "widgets")
SUMMARY_JSON_PATH = os.path.join(WIDGETS_PATH, "summary.json")


def gen_allure_summary() -> dict:
    """ 收集allure总览信息 """
    with open(SUMMARY_JSON_PATH, 'r', encoding='utf-8') as fp:
        allure_summary = json.load(fp)
    return allure_summary


class CaseSummary:
    def __init__(self):
        self.allure_summary = gen_allure_summary()
        self.results = self.allure_summary["statistic"]

    @property
    def passed_count(self) -> int:
        """用例成功数"""
        return self.results['passed']

    @property
    def failed_count(self) -> int:
        """用例失败数"""
        return self.results['failed']

    @property
    def broken_count(self) -> int:
        """用例异常数"""
        return self.results['broken']

    @property
    def skipped_count(self) -> int:
        """用例跳过数"""
        return self.results['skipped']

    @property
    def total_count(self) -> int:
        """用例总数"""
        return self.results['total']

    @property
    def passed_rate(self) -> str:
        """用例成功率"""
        try:
            passed_rate = self.passed_count / self.total_count
        except ZeroDivisionError:
            passed_rate = "0.00%"
        else:
            passed_rate = "{:.2%}".format(passed_rate)
        return passed_rate

    @property
    def duration(self):
        """用例执行时长"""
        total_duration = self.allure_summary['time'].get('duration') or 0
        run_time = round(total_duration / 1000, 2)
        return f"{run_time}s"


if __name__ == '__main__':
    # print(CaseSummary().results)
    print(BASEDIR)
    print(REPORT_DIR)
    print(SUMMARY_JSON_PATH)
