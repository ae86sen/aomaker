# --coding:utf-8--
import requests
import os

from aomaker.utils.gen_allure_report import CaseSummary, get_allure_results
from aomaker.utils.utils import load_yaml
from aomaker.storage import Config
from aomaker.path import CONF_DIR
from aomaker._constants import Conf

utils_yaml_path = os.path.join(CONF_DIR, Conf.UTILS_CONF_NAME)


class WeChatSend:
    """
    企业微信消息通知
    """

    def __init__(self, tester="古一", title="自动化测试通知", report_address=""):
        self.wechat_conf = load_yaml(utils_yaml_path)['wechat']
        self.curl = self.wechat_conf['webhook']
        self.headers = {"Content-Type": "application/json"}
        self.test_results = CaseSummary()
        self.total = str(self.test_results.total_count)
        self.passed = str(self.test_results.passed_count)
        self.failed = str(self.test_results.failed_count)
        self.skipped = str(self.test_results.skipped_count)
        self.broken = str(self.test_results.broken_count)
        self.passed_rate = self.test_results.passed_rate
        self.duration = self.test_results.duration
        self.config_db = Config()
        self.current_env = self.config_db.get('current_env')
        self.tester = tester
        self.title = title
        self.report_address = report_address

    def _send_markdown(self, content):
        json_data = {"msgtype": "markdown", "markdown": {"content": content}}
        res = requests.post(url=self.curl, json=json_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            raise ValueError(f"企业微信「MarkDown类型」消息发送失败")

    def send_msg(self):
        """发送企业微信通知"""
        text = f"""【{self.title}】
                                   >测试环境：<font color=\"info\">{self.current_env}</font>
                                    >测试负责人：{self.tester}
                                    >
                                    > **执行结果**
                                    ><font color=\"info\">🎯运行成功率: {self.passed_rate}</font>
                                    >❤用例  总数：<font color=\"info\">{self.total}个</font>
                                    >😁成功用例数：<font color=\"info\">{self.passed}个</font>
                                    >😭失败用例数：`{self.failed}个`
                                    >😡阻塞用例数：`{self.broken}个`
                                    >😶跳过用例数：<font color=\"warning\">{self.skipped}个</font>
                                    >🕓用例执行时长：<font color=\"warning\">{self.duration}</font>
                                    >
                                    >测试报告，点击[查看>>测试报告]({self.report_address})"""

        self._send_markdown(text)
        self.config_db.close()

    def send_detail_msg(self, sep="_"):
        """通知中可根据标记分类显示通过率
        sep: 标记分隔符
        """
        reports = get_allure_results(sep=sep)
        if reports:
            markdown_li = []
            for product, result in reports.items():
                format_ = f"><font color=\"info\">🎯「{product}」成功率: {result['passed_rate']}</font>"
                markdown_li.append(format_)
            format_product_rate = "\n".join(markdown_li)
        else:
            format_product_rate = ""
        text = f"""【{self.title}】
                                   >测试环境：<font color=\"info\">{self.current_env}</font>
                                    >测试负责人：{self.tester}
                                    >
                                    > **执行结果**
                                    ><font color=\"info\">🎯运行成功率: {self.passed_rate}</font>
                                    {format_product_rate}
                                    >❤用例  总数：<font color=\"info\">{self.total}个</font>
                                    >😁成功用例数：<font color=\"info\">{self.passed}个</font>
                                    >😭失败用例数：`{self.failed}个`
                                    >😡阻塞用例数：`{self.broken}个`
                                    >😶跳过用例数：<font color=\"warning\">{self.skipped}个</font>
                                    >🕓用例执行时长：<font color=\"warning\">{self.duration}</font>
                                    >
                                    >测试报告，点击[查看>>测试报告]({self.report_address})"""
        self._send_markdown(text)
        self.config_db.close()


if __name__ == '__main__':
    # WeChatSend().send_wechat_notification()
    print(utils_yaml_path)
    print(CONF_DIR)
