# --coding:utf-8--
import requests
import os

from aomaker.utils.gen_allure_report import CaseSummary, get_allure_results
from aomaker.utils.utils import load_yaml
from aomaker.cache import Config
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

    def send_text(self, content, mentioned_mobile_list=None):
        """
        发送文本类型通知
        :param content: 文本内容，最长不超过2048个字节，必须是utf8编码
        :param mentioned_mobile_list: 手机号列表，提醒手机号对应的群成员(@某个成员)，@all表示提醒所有人
        :return:
        """
        _DATA = {"msgtype": "text", "text": {"content": content, "mentioned_list": None,
                                             "mentioned_mobile_list": mentioned_mobile_list}}

        if mentioned_mobile_list is None or isinstance(mentioned_mobile_list, list):
            # 判断手机号码列表中得数据类型，如果为int类型，发送得消息会乱码
            if len(mentioned_mobile_list) >= 1:
                for i in mentioned_mobile_list:
                    if isinstance(i, str):
                        res = requests.post(url=self.curl, json=_DATA, headers=self.headers)
                        if res.json()['errcode'] != 0:
                            raise ValueError(f"企业微信「文本类型」消息发送失败")

                    else:
                        raise TypeError("手机号码必须是字符串类型.")
        else:
            raise ValueError("手机号码列表必须是list类型.")

    def send_markdown(self, content):
        """
        发送 MarkDown 类型消息
        :param content: 消息内容，markdown形式
        :return:
        """
        _DATA = {"msgtype": "markdown", "markdown": {"content": content}}
        res = requests.post(url=self.curl, json=_DATA, headers=self.headers)
        if res.json()['errcode'] != 0:
            raise ValueError(f"企业微信「MarkDown类型」消息发送失败")

    def articles(self, article):
        """

        发送图文消息
        :param article: 传参示例：{
               "title" : ”标题，不超过128个字节，超过会自动截断“,
               "description" : "描述，不超过512个字节，超过会自动截断",
               "url" : "点击后跳转的链接",
               "picurl" : "图文消息的图片链接，支持JPG、PNG格式，较好的效果为大图 1068*455，小图150*150。"
           }
        如果多组内容，则对象之间逗号隔开传递
        :return:
        """
        _data = {"msgtype": "news", "news": {"articles": [article]}}
        if isinstance(article, dict):
            lists = ['description', "title", "url", "picurl"]
            for i in lists:
                # 判断所有参数都存在
                if article.__contains__(i):
                    res = requests.post(url=self.curl, headers=self.headers, json=_data)
                    if res.json()['errcode'] != 0:
                        raise ValueError(f"企业微信「图文类型」消息发送失败")
                else:
                    raise ValueError("发送图文消息失败，标题、描述、链接地址、图片地址均不能为空！")
        else:
            raise TypeError("图文类型的参数必须是字典类型")

    def _upload_file(self, file):
        """
        先将文件上传到临时媒体库
        """
        key = self.curl.split("key=")[1]
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
        data = {"file": open(file, "rb")}
        res = requests.post(url, files=data).json()
        return res['media_id']

    def send_file_msg(self, file):
        """
        发送文件类型的消息
        @return:
        """

        _data = {"msgtype": "file", "file": {"media_id": self._upload_file(file)}}
        res = requests.post(url=self.curl, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            raise ValueError(f"企业微信「file类型」消息发送失败")

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

        self.send_markdown(text)
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
        self.send_markdown(text)
        self.config_db.close()


if __name__ == '__main__':
    # WeChatSend().send_wechat_notification()
    print(utils_yaml_path)
    print(CONF_DIR)
