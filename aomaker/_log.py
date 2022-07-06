# --coding:utf-8--
"""
aomaker 内部调用日志
"""
import time
import logging
import colorlog

LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red',
}


class Logger:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s [AoMaker]-[%(levelname)s]%(message)s',
                                                   "%Y-%m-%d %H:%M:%S", log_colors=LOG_COLORS)
        self.sh_open = True

    def __console(self, log_level, message):
        """
        设置控制台与日志信息
        :param log_level: 日志等级
        :param message: 日志输出信息
        """
        # 控制台输出
        if self.sh_open:
            self.sh = logging.StreamHandler()
            self.sh.setLevel(logging.DEBUG)
            self.sh.setFormatter(self.formatter)
            self.logger.addHandler(self.sh)

        # 判断日志等级
        if log_level.upper() == 'INFO':
            self.logger.info("".join([message]))
        elif log_level.upper() == 'DEBUG':
            self.logger.debug("".join([message]))
        elif log_level.upper() == "WARNING" or log_level.upper() == "WARN":
            self.logger.warning("".join([message]))
        elif log_level.upper() == "ERROR":
            self.logger.error("".join([message]))
        # 避免日志重复
        if self.sh_open:
            self.logger.removeHandler(self.sh)

    def info(self, message):
        """
        输出info信息
        :param message: 输出信息
        """
        self.__console('info', ': {}'.format(message))

    def debug(self, message):
        """
        输出debug信息
        :param message: 输出信息
        """
        self.__console('debug', ': {}'.format(message))

    def warn(self, message):
        """
        输出warn信息
        :param message: 输出信息
        """
        self.__console('warn', ': {}'.format(message))

    def error(self, message):
        """
        输出error信息
        :param message: 输出信息
        """
        self.__console('error', ': {}'.format(message))

    def __nowdate(self):
        """获取当前日期"""
        return time.strftime("%Y%m%d")


logger = Logger()