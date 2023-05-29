from emoji import emojize
from aomaker.log import logger


class TestSessionInfo:
    init_env_s = "开始初始化环境", "puzzle_piece"
    init_env_e = "环境初始化完成，所有全局配置已加载到config表", "beer_mug"
    gen_rep_s = "测试结束, AoMaker开始收集报告", "glowing_star"
    gen_rep_e = "AoMaker已完成测试报告(reports/aomaker.html)!", "glowing_star"
    clean_env_s = "测试结束，开始清理环境", "broom"
    clean_env_e = "清理环境完成！", "broom"

    @classmethod
    def map(cls, attr):
        def wrapper():
            value = getattr(cls, attr)
            text = emojize(f":{value[1]}: {value[0]} :{value[1]}:")
            logger.info(cls.output(text))

        return wrapper

    @classmethod
    def output(cls, text: str, total_len: int = 90):
        text_len = len(text)
        padding_len = (total_len - text_len - 4) // 2
        output = "*" * padding_len + text + "*" * padding_len
        return output


def printer(label:str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            TestSessionInfo.map(label+"_s")()
            func(*args, **kwargs)
            TestSessionInfo.map(label+"_e")()

        return wrapper

    return decorator
