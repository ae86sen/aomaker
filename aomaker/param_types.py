# --coding:utf-8--
import click


class QuotedStrParamType(click.ParamType):
    """
    带''号的字符串类型
    """
    name = "quoted_str"

    def convert(self, value: str, param, ctx):
        value_repr = f"{value!r}"
        if value_repr.startswith("'") and value_repr.endswith("'"):
            return value.split(' ')
        elif value is None:
            return value
        else:
            self.fail(f"{value!r} is must be quoted", param, ctx)


QUOTED_STR = QuotedStrParamType()
