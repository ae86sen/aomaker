# --coding:utf-8--
import typing as t
from aomaker.log import logger

from tenacity import Retrying, stop_after_attempt, wait_fixed, WrappedFn, retry_if_exception_type, retry_if_result


def before_log():
    def log_it(retry_state) -> None:
        attempt_number = retry_state.attempt_number
        logger.warning(f"遇到异常，开始尝试第{attempt_number}次重试...")

    return log_it


def after_log():
    def log_it(retry_state) -> None:
        logger.warning(f"已重试第{retry_state.attempt_number}次,重试状态:{retry_state.outcome._state}")

    return log_it


class AoMakerRetry(Retrying):
    def __init__(self, counts: int = 3, interval: int = 2, retry_condition=None, exception_type=None, **kwargs):
        super().__init__(**kwargs)
        self.reraise = True
        self.before = before_log()
        self.after = after_log()
        self.stop = stop_after_attempt(counts)
        self.wait = wait_fixed(interval)
        if retry_condition and exception_type:
            self.retry = (retry_if_exception_type(exception_type) | retry_if_result(retry_condition))
        elif exception_type:
            self.retry = retry_if_exception_type(exception_type)
        elif retry_condition:
            self.retry = retry_if_result(retry_condition)


def retry(*dargs: t.Any, **dkw: t.Any) -> t.Any:
    """Wrap a function with a new `Retrying` object.

    :param dargs: positional arguments passed to Retrying object
    :param dkw: keyword arguments passed to the Retrying object
    """
    if len(dargs) == 1 and callable(dargs[0]):
        return retry()(dargs[0])
    else:
        def wrap(f: WrappedFn) -> WrappedFn:
            r = AoMakerRetry(*dargs, **dkw)

            return r.wraps(f)

        return wrap
