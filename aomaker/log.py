# --coding:utf-8--
import os
import sys
# debug使用
sys.path.insert(0, 'D:\\项目列表\\aomaker')
import logging
from loguru import logger as uru_logger

from aomaker.path import LOG_DIR
from aomaker._constants import Log

log_path = os.path.join(LOG_DIR, Log.LOG_NAME)


class PropogateHandler(logging.Handler):
    def emit(self, record):
        logging.getLogger(record.name).handle(record)


class AoMakerLogger:
    # log level: TRACE < DEBUG < INFO < SUCCESS < WARNING < ERROR
    def __init__(self, level: str = Log.DEFAULT_LEVEL, log_file_path=log_path):
        self.logger = uru_logger
        # 清空所有设置
        self.logger.remove()
        # 添加控制台输出的格式,sys.stdout为输出到屏幕;关于这些配置还需要自定义请移步官网查看相关参数说明
        self.logger.add(sys.stdout,
                        level=level.upper(),
                        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> "  # 颜色>时间
                               "[{process.name}]-"  # 进程名
                               "[{thread.name}]-"  # 进程名
                               "<cyan>[{module}</cyan>.<cyan>{function}</cyan>"  # 模块名.方法名
                               ":<cyan>{line}]</cyan>-"  # 行号
                               "<level>[{level}]</level>: "  # 等级
                               "<level>{message}</level>",  # 日志内容
                        )
        # 输出到文件的格式,注释下面的add',则关闭日志写入
        self.logger.add(log_file_path, level=level.upper(),
                        format='{time:YYYY-MM-DD HH:mm:ss} '  # 时间
                               "[{process.name}]-"  # 进程名
                               "[{thread.name}]-"  # 进程名
                               '[{module}.{function}:{line}]-[{level}]:{message}',  # 模块名.方法名:行号
                        rotation="10 MB")

    def get_logger(self):
        return self.logger


logger = AoMakerLogger().get_logger()
