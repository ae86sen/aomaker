import argparse
import os
import sys

import pytest
import yaml
from loguru import logger

from aomaker import __version__, __description__, __image__
from aomaker.scaffold import init_parser_scaffold, main_scaffold
from aomaker.make import init_make_parser, main_make
from aomaker.make_testcase import init_make_case_parser, main_make_case


def init_parser_run(subparsers):
    sub_parser_run = subparsers.add_parser(
        "run", help="Make AOMaker testcases and run with pytest."
    )
    sub_parser_run.add_argument(
        "-e", "--env", dest="env", help="switch test environment "
    )
    return sub_parser_run


def set_conf_file(env):
    if os.path.exists('conf/config.yaml'):
        with open('conf/config.yaml') as f:
            doc = yaml.safe_load(f)
        doc['env'] = env
        if not doc.get(env):
            logger.error(f'测试环境-{env}还未在配置文件中配置！')
            sys.exit(1)
        with open('conf/config.yaml', 'w') as f:
            yaml.safe_dump(doc, f, default_flow_style=False)
    else:
        logger.error('配置文件conf/config.yaml不存在')
        sys.exit(1)


def main_run(extra_args):
    logger.info("start to run")
    if "--pytest-tmreport-name=report/test_report.html" not in extra_args:
        extra_args.append("--pytest-tmreport-path=report/")
        extra_args.append("--pytest-tmreport-name=test_report.html")

    logger.info(f"start to run tests with pytest. AOMaker version: {__version__}")
    return pytest.main(extra_args)


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
    # sub_parser_s2y = init_swagger2yaml_parser(subparsers)
    sub_parser_a2c = init_make_case_parser(subparsers)
    sub_parser_run = init_parser_run(subparsers)

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
            # aomaker make
            sub_parser_make.print_help()
        elif sys.argv[1] == "mcase":
            # aomaker mcase
            sub_parser_a2c.print_help()
        elif sys.argv[1] == "run":
            # aomaker run
            sub_parser_run.print_help()
        sys.exit(0)
    elif (
            len(sys.argv) == 3 and sys.argv[1] == "run" and sys.argv[2] in ["-h", "--help"]
    ):
        # aomaker run -h
        pytest.main(["-h"])
        sys.exit(0)
    elif sys.argv[1] == "run" and sys.argv[2] == "-e":
        # aomaker run -e xxx
        logger.info(sys.argv[3])
        set_conf_file(sys.argv[3])

    extra_args = []
    if len(sys.argv) >= 2 and sys.argv[1] in ["run"]:
        args, extra_args = parser.parse_known_args()
    else:
        args = parser.parse_args()

    if args.version:
        print(f"{__version__}")
        sys.exit(0)

    if sys.argv[1] == "startproject":
        main_scaffold(args)
        print('Project created successfully!')
    elif sys.argv[1] == "make":
        main_make(args.param)
        print('API object generated successfully!')
    elif sys.argv[1] == "mcase":
        main_make_case(args.data_path)
        print('Test cases generated successfully from test data!')
    elif sys.argv[1] == "run":
        sys.exit(main_run(extra_args))


def main_arun_alias():
    """ command alias
        arun = aomaker run
    """
    if len(sys.argv) == 2:
        if sys.argv[1] in ["-V", "--version"]:
            # arun -V
            sys.argv = ["aomaker", "-V"]
        elif sys.argv[1] in ["-h", "--help"]:
            pytest.main(["-h"])
            sys.exit(0)
        else:
            # arun
            sys.argv.insert(1, "run")
    else:
        sys.argv.insert(1, "run")
    main()


def main_make_alias():
    """ command alias
        amake = aomaker make
    """
    sys.argv.insert(1, "make")
    main()


if __name__ == '__main__':
    main()
