import argparse

from aomaker.extension.har_parse.har_parse import HarParser


class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def bool_switch(int_number):
    return True if int_number == 0 else False


# aomaker har2y
def main_har2yaml(args):
    har_path = args.har_path
    yaml_path: str = args.yaml_path
    hp = HarParser(har_path, yaml_path,
                   filter_str=args.filter_str,
                   exclude_str=args.exclude_str,
                   save_response=args.save_response,
                   save_headers=args.save_headers)
    hp.har2yaml_testcase()


def init_har2yaml_parser(subparsers):
    """ convert HAR to YAML: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "har2y", help="Convert HAR(HTTP Archive) to YAML testcases for AoMaker.", formatter_class=SmartFormatter
    )
    parser.add_argument(
        "har_path", type=str, nargs="?",
        help="Specify HAR file path."
    )
    parser.add_argument(
        "yaml_path", type=str, nargs="?",
        help="Specify YAML file path."
    )
    parser.add_argument(
        "--filter_str", dest="filter_str", type=str, nargs="?",
        help="Specify filter keyword, only url include filter string will be converted."
    )
    parser.add_argument(
        "--exclude_str", dest="exclude_str", type=str, nargs="?",
        help="Specify exclude keyword, url that includes exclude string will be ignored, "
             "multiple keywords can be joined with '|'"
    )
    parser.add_argument(
        "--save_response", dest="save_response", type=int, nargs="?", default=0,
        help="R|Specify whether to save response.\n"
             "0(default): save response.\n"
             "1: don't save response.\n"
    )
    parser.add_argument(
        "--save_headers", dest="save_headers", type=int, nargs="?", default=1,
        help="R|Specify whether to save request headers.\n"
             "0: save request headers.\n"
             "1(default): don't save request headers.\n"
    )
    return parser
