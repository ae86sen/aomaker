# --coding:utf-8--
import configparser
import json
import os
import time
from typing import List, Dict

from aomaker.path import REPORT_DIR, PYTEST_INI_DIR
from aomaker.utils.utils import HandleIni

ALLURE_HTML_PATH = os.path.join(REPORT_DIR, "html")
ALLURE_JSON_PATH = os.path.join(REPORT_DIR, "json")
WIDGETS_PATH = os.path.join(ALLURE_HTML_PATH, "widgets")
SUMMARY_JSON_PATH = os.path.join(WIDGETS_PATH, "summary.json")


def gen_allure_summary() -> dict:
    """ 收集allure总览信息 """
    with open(SUMMARY_JSON_PATH, 'r', encoding='utf-8') as fp:
        allure_summary = json.load(fp)
    return allure_summary


def get_allure_results(sep: str) -> dict:
    """解析allure json"""
    # 1.find all result.json file
    results = {}
    result_jsons = parse_allure_res_json()
    n = 0
    all_results_json = []
    status_list = []
    marks_group = _get_marks_group_from_pytest_ini()
    for result_json in result_jsons:
        with open(result_json, encoding="utf-8") as load_f:
            load_dict = json.load(load_f)
            keys = load_dict.keys()
            # 判断是否有labels
            if "labels" in keys and "status" in keys:
                result = {
                    "name": load_dict["name"],
                    "full_name": load_dict["fullName"],
                    "labels": load_dict["labels"],
                    "case_id": load_dict['testCaseId'],
                    "parameters": load_dict.get("parameters")
                }
                status = load_dict["status"]
                start_time = load_dict["start"]
                status_dict = {"name": load_dict["name"], "status": status, "full_name": load_dict["fullName"],
                               "start_time": start_time}
                if result in all_results_json:
                    # 处理重试机制
                    index = all_results_json.index(result)
                    elem = status_list[index]
                    # 处理重试机制时，状态变更的情况，用最后一次状态
                    if start_time > elem["start_time"]:
                        elem["status"] = status
                else:
                    all_results_json.append(result)
                    status_list.append(status_dict)
    for load_dict, status_dict in zip(all_results_json, status_list):
        status = status_dict["status"]
        tags = [label.get("value") for label in _handle_labels(load_dict['labels'])]
        product_name = _handle_tags(tags, marks_group, sep=sep)
        if product_name is not None:
            if results.get(product_name) is None:
                results[product_name] = {"passed": 0, "failed": 0, "skipped": 0, "broken": 0}
            results[product_name][status] += 1
    results = _count_passed_rate(results)
    return results


def parse_allure_res_json():
    res = []
    for root, directory, files in os.walk(ALLURE_JSON_PATH):
        for filename in files:
            name, suf = os.path.splitext(filename)
            if suf == ".json":
                res.append(os.path.join(root, filename))
    result_jsons = [data for data in res if "result.json" in data]
    return result_jsons


def _get_marks_group_from_pytest_ini() -> str:
    pytest_config_parser = HandleIni(PYTEST_INI_DIR)
    try:
        marks_group = pytest_config_parser.get("pytest", "marks_group")
    except (configparser.NoSectionError, configparser.NoOptionError):
        marks_group = ""
    return marks_group


def _handle_labels(labels: list):
    for label in labels:
        if label.get('name') == "tag":
            yield label


def _handle_tags(tags: list, marks_group, sep=None):
    """将标记按照指定分隔符分割,默认按空格"""
    for tag in tags:
        prefix_tag = tag.split(sep)[0]
        if prefix_tag in marks_group:
            return prefix_tag


def _count_passed_rate(results: dict) -> dict:
    new_results = results
    for product, result in results.items():
        passed_count = result["passed"]
        failed_count = result["failed"]
        broken_count = result["broken"]
        try:
            passed_rate = passed_count / (passed_count + failed_count + broken_count)
        except ZeroDivisionError:
            passed_rate = "0.00%"
        else:
            passed_rate = "{:.2%}".format(passed_rate)
        new_results[product]["passed_rate"] = passed_rate
    return new_results


def rewrite_summary():
    try:
        case_summary = CaseSummary()
    except FileNotFoundError:
        class NewCaseSummary:
            passed_rate = "0%"
            failed_rate = "0%"
            broken_rate = "0%"
            skipped_rate = "0%"
            total_count = 0
            passed_count = 0
            failed_count = 0
            broken_count = 0
            skipped_count = 0
            duration = "0s"
            start_time = "--"
            stop_time = "--"

        case_summary = NewCaseSummary()

    reports = get_allure_results(sep="_")
    if reports:
        markdown_li = []
        for product, result in reports.items():
            mark_dic = {"format_wechat": "", "format_email": ""}
            mark_dic["format_wechat"] = f"<font color='info'>🎯「{product}」成功率: {result['passed_rate']}</font>"
            mark_dic["format_email"] = f"「{product}」成功率: {result['passed_rate']}"
            mark_dic[product] = result['passed_rate']
            markdown_li.append(mark_dic)
        marks_rate = markdown_li
    else:
        marks_rate = []

    new_summary = {
        "summary":
            {
                "passed_rate": case_summary.passed_rate,
                "failed_rate": case_summary.failed_rate,
                "skipped_rate": case_summary.skipped_rate,
                "broken_rate": case_summary.broken_rate,
                "total_count": case_summary.total_count,
                "passed_count": case_summary.passed_count,
                "failed_count": case_summary.failed_count,
                "broken_count": case_summary.broken_count,
                "skipped_count": case_summary.skipped_count,
                "duration": case_summary.duration,
                "start_time": case_summary.start_time,
                "stop_time": case_summary.stop_time,
                "marks_rate": marks_rate
            }
    }
    #
    if os.path.exists(SUMMARY_JSON_PATH):
        with open(SUMMARY_JSON_PATH, "w") as f:
            case_summary.allure_summary.update(new_summary)
            f.write(json.dumps(case_summary.allure_summary))


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
        """用例运行成功率：成功用例数/运行用例数（不计算跳过用例）"""
        try:
            passed_rate = self.passed_count / (self.total_count - self.skipped_count)
        except ZeroDivisionError:
            passed_rate = "0.00%"
        else:
            passed_rate = "{:.2%}".format(passed_rate)
        return passed_rate

    @property
    def failed_rate(self) -> str:
        """用例运行失败率：失败用例数/运行用例数（不计算跳过用例）"""
        try:
            failed_rate = self.failed_count / (self.total_count - self.skipped_count)
        except ZeroDivisionError:
            failed_rate = "0.00%"
        else:
            failed_rate = "{:.2%}".format(failed_rate)
        return failed_rate

    @property
    def skipped_rate(self) -> str:
        """用例运行失败率：失败用例数/用例数"""
        try:
            skipped_rate = self.skipped_count / self.total_count
        except ZeroDivisionError:
            skipped_rate = "0.00%"
        else:
            skipped_rate = "{:.2%}".format(skipped_rate)
        return skipped_rate

    @property
    def broken_rate(self) -> str:
        """用例运行阻塞/错误率：阻塞/错误用例数/运行用例数（不计算跳过用例）"""
        try:
            broken_rate = self.broken_count / (self.total_count - self.skipped_count)
        except ZeroDivisionError:
            broken_rate = "0.00%"
        else:
            broken_rate = "{:.2%}".format(broken_rate)
        return broken_rate

    @property
    def duration(self):
        """用例执行时长"""
        total_duration = self.allure_summary['time'].get('duration') or 0
        run_time = round(total_duration / 1000, 2)
        return time_format(run_time)

    @property
    def start_time(self):
        st = self.allure_summary['time'].get("start")
        if st is None:
            return ""
        return timestamp_to_standard(st)

    @property
    def stop_time(self):
        st = self.allure_summary['time'].get("stop")
        if st is None:
            return ""
        return timestamp_to_standard(st)


class CaseDetail:
    def __init__(self):
        self.result_jsons = parse_allure_res_json()

    def case_detail_info(self) -> List[Dict]:
        """解析所有allure-result.json"""
        results = []
        for result_json in self.result_jsons:
            case_info = {}
            with open(result_json, encoding="utf-8") as load_f:
                load_dict = json.load(load_f)
                keys = load_dict.keys()
                if "status" in keys:
                    # 用例执行结果
                    case_info["result"] = load_dict['status']
                if "statusDetails" in keys:
                    case_info["logs"] = load_dict["statusDetails"]["trace"]
                if "description" in keys:
                    # 用例标题描述
                    case_info["doc"] = load_dict['description']
                if "start" and "stop" in keys:
                    duration = load_dict['stop'] - load_dict['start']
                    case_info["duration"] = round(duration / 1000, 2)
                    case_info["f_duration"] = "%.2fs" % case_info["duration"]
                    case_info["time"] = timestamp_to_standard(load_dict['start'])
                if "fullName" in keys:
                    full_name = load_dict["fullName"]
                    case_info["test_class"], case_info["test_method"] = full_name.split("#")
                if "testCaseId" in keys:
                    case_info["case_id"] = load_dict["testCaseId"]
                results.append(case_info)
        return results


def time_format(seconds: int or float) -> str:
    """将秒数转化为时分秒格式"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%02dh:%02dm:%02ds" % (h, m, s)


def timestamp_to_standard(timestamp: int) -> str:
    """将13位时间戳转换为年月日 时分秒标准时间格式"""
    tup_time = time.localtime(float(timestamp / 1000))
    standard_time = time.strftime("%Y-%m-%d %H:%M:%S", tup_time)
    return standard_time


if __name__ == '__main__':
    # print(CaseSummary().results)
    # print(BASEDIR)
    # print(REPORT_DIR)
    # print(SUMMARY_JSON_PATH)
    print(timestamp_to_standard(1664264521754))
