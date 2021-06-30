
    from loguru import logger


def api_call(func):
    """
    接口调用记录
    :param func: 装饰的函数
    :return:
    """

    def inner(*args, **kwargs):
        logger.info(f"开始调用接口：{func.__name__}")
        res = func(*args, **kwargs)
        logger.info(f"结束调用接口：{func.__name__}")
        return res

    return inner
    