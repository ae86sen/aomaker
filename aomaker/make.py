import sys
from typing import Text

from aomaker.yaml2case import YamlParse, init_yaml_parse
from aomaker.make_api import make_api_file, make_api_file_restful
from aomaker._log import logger

def make_ao(yp: YamlParse):
    yp.make_ao_file()
    yp.render_ao_file()


# aomaker make
def main_make(file_path: Text, template='restful'):
    if file_path.endswith('.yaml') or file_path.endswith('.yml'):
        yp = init_yaml_parse(file_path)
        make_ao(yp)
    elif file_path.endswith('.json'):
        if template == 'restful':
            make_api_file_restful(file_path)
        elif template == 'qingcloud':
            make_api_file(file_path, template)
        else:
            logger.error('Currently, only two styles(restful and qingcloud) are supported!please input correct style!')
            sys.exit(1)
    else:
        logger.error('The file format is unsupported!')
        sys.exit(1)


def init_make_parser(subparsers):
    """ make api object: parse command line options and run commands.
    """
    parser = subparsers.add_parser(
        "make", help="Make Api object by YAML/Swagger(Json)",
    )
    parser.add_argument(
        "-t", "--template", dest="template", type=str, nargs="?",
        help="Set template of swagger.Default template: restful."
    )
    parser.add_argument(
        "file_path", type=str, nargs="?",
        help="Specify YAML/Swagger file path.The file suffix must be '.yaml','.yml' or '.json'."
    )
    return parser
