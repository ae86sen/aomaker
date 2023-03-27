import argparse
import os
import jinja2

filter_expression = """
    The following operators are understood:\n
        ~q          Request\n
        ~s          Response\n
    Headers:\n
        Patterns are matched against "name: value" strings. Field names are\n
        all-lowercase.\n
        ~a          Asset content-type in response. Asset content types are:\n
                        text/javascript\n
                        application/x-javascript\n
                        application/javascript\n
                        text/css\n
                        image/*\n
                        application/x-shockwave-flash\n
        ~h rex      Header line in either request or response\n
        ~hq rex     Header in request\n
        ~hs rex     Header in response\n
        ~b rex      Expression in the body of either request or response\n
        ~bq rex     Expression in the body of request\n
        ~bs rex     Expression in the body of response\n
        ~t rex      Shortcut for content-type header.\n
        ~d rex      Request domain\n
        ~m rex      Method\n
        ~u rex      URL\n
        ~c CODE     Response code.\n
        rex         Equivalent to ~u rex\n
"""
temp = jinja2.Template(
    """from aomaker.extension.recording.recording import Record


addons = [Record('{{file_name}}', filter_str='{{filter_str}}',
save_response={{save_response}}, save_headers={{save_headers}})]
    """
)


class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def bool_switch(int_number):
    return True if int_number == 0 else False


def get_init_params(args, path):
    init_params = dict()
    init_params['file_name'] = args.file_name
    init_params['filter_str'] = args.filter_str
    init_params['save_response'] = args.save_response
    init_params['save_headers'] = args.save_headers
    content = temp.render(init_params)
    with open(path, mode='w', encoding='utf-8') as f:
        f.write(content)


def main_record(args):
    addons_file_path = os.path.join(os.path.dirname(__file__), 'addons.py')
    get_init_params(args, addons_file_path)
    port = args.port
    log_level = args.level
    try:
        print('AoMaker开始录制')
        from mitmproxy.tools.main import mitmdump
        mitmdump([f'-p {port}', f'-s {addons_file_path}', f'--flow-detail {log_level}'])
        # os.system(f'mitmdump -p {port} -s {addons_file_path} --flow-detail {log_level}')
    except KeyboardInterrupt:
        print('AoMaker录制完成')


def init_record_parser(subparsers):
    """ record flows: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "record", help="Make Api object by YAML/Swagger(Json)", formatter_class=SmartFormatter
    )
    parser.add_argument(
        "-f", "--filter_str", dest="filter_str", type=str, nargs="?",
        help=f'R|Specify filter keyword.\n'
             f'{filter_expression}'
    )
    parser.add_argument(
        "-p", "--port", dest="port", type=int, nargs="?", default=8082,
        help=f'Specify proxy service port.default port:8082.'
    )
    parser.add_argument(
        "--flow-detail", dest="level", type=int, nargs="?", default=0,
        help='R|The display detail level for flows in mitmdump: 0 (almost quiet) to 4 (very verbose).\n'
             '0(default): shortened request URL, response status code, WebSocket and TCP message notifications.\n'
             '1: full request URL with response status code.\n'
             '2: 1 + HTTP headers.\n'
             '3: 2 + truncated response content, content of WebSocket and TCP messages.\n'
             '4: 3 + nothing is truncated.\n'
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
    parser.add_argument(
        "file_name", type=str, nargs="?",
        help="Specify YAML file name."
    )
    return parser
