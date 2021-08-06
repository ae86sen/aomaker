import argparse
import sys

# from aom import __description__, __version__
from __init__ import __description__, __version__, __image__
# from aom.scaffold import init_parser_scaffold, main_scaffold
from scaffold import init_parser_scaffold, main_scaffold
from make import init_make_parser, main_make
from swagger2yaml import init_swagger2yaml_parser, main_swagger2yaml
from make_testcase import init_make_case_parser, main_make_case


def main():
    """Parse command line options and run commands.
    """
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument(
        "-V", "--version", dest="version", action="store_true", help="show version"
    )
    subparsers = parser.add_subparsers(help="sub-command help")
    sub_parser_scaffold = init_parser_scaffold(subparsers)
    sub_parser_make = init_make_parser(subparsers)
    sub_parser_s2y = init_swagger2yaml_parser(subparsers)
    sub_parser_a2c = init_make_case_parser(subparsers)

    if len(sys.argv) == 1:
        # aomker
        print(__image__)
        parser.print_help()
        sys.exit(0)
    elif len(sys.argv) == 2:
        # print help for sub-commands
        if sys.argv[1] in ["-V", "--version"]:
            # aomaker -V
            print(f"{__version__}")
        elif sys.argv[1] in ["-h", "--help"]:
            # aomaker -h
            parser.print_help()
        elif sys.argv[1] == "startproject":
            # aomaker startproject
            sub_parser_scaffold.print_help()
        elif sys.argv[1] == "make":
            sub_parser_make.print_help()
        elif sys.argv[1] == "s2y":
            sub_parser_s2y.print_help()
        elif sys.argv[1] == "a2case":
            sub_parser_a2c.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.version:
        print(f"{__version__}")
        sys.exit(0)

    if sys.argv[1] == "startproject":
        main_scaffold(args)
        print('Project created successfully!')
    elif sys.argv[1] == "make":
        main_make(args.yaml_path)
        print('API object  generated successfully!')
    elif sys.argv[1] == "s2y":
        main_swagger2yaml(args.param)
        print('API definition of YAML generated successfully from swagger!')
    elif sys.argv[1] == "a2case":
        main_make_case(args.data_path)
        print('Test cases generated successfully from test data!')


if __name__ == '__main__':
    main()