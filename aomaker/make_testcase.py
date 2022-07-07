import sys
from typing import Text

from aomaker.yaml2case import YamlParse, init_yaml_parse
from aomaker.make import make_ao
from aomaker._log import logger


def make_testcase(yp: YamlParse):
    yp.make_testcase_file()


def main_case(file_path: Text):
    yp = init_yaml_parse(file_path)
    make_testcase(yp)


def main_make_case(file_path: Text):
    try:
        yp = init_yaml_parse(file_path)
        make_ao(yp)
        make_testcase(yp)
    except Exception as e:
        logger.error(e)
        sys.exit(1)


def init_case_parser(subparsers):
    """make testcase: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "case", help="Make testcases by YAML."
    )
    parser.add_argument(
        "file_path", type=str, nargs="?", help="YAML file path."
    )
    return parser


def init_make_case_parser(subparsers):
    """ make ao and testcases: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "mcase", help="A combined command of 'make' and 'case'",
    )
    parser.add_argument(
        "file_path", type=str, nargs="?", help="YAML file path."
    )

    return parser

# main_make_case('job_datas.yaml')
