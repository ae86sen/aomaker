import argparse
import os
import sys

import pytest
import yaml

from aomaker import __version__, __description__, __image__
from aomaker.scaffold import init_parser_scaffold, main_scaffold
from aomaker.make import init_make_parser, main_make
from aomaker.make_testcase import init_make_case_parser, main_make_case, init_case_parser, main_case
from aomaker.extension.har_parse import init_har2yaml_parser, main_har2yaml
from aomaker.extension.recording import init_record_parser, main_record
from aomaker.path import CONF_DIR
from aomaker._constants import Conf
from aomaker.log import AoMakerLogger
from aomaker._log import logger


def init_parser_run(subparsers):
    sub_parser_run = subparsers.add_parser(
        "run", help="Make testcases and run with aomaker."
    )
    sub_parser_run.add_argument(
        "-e", "--env", dest="env", help="switch test environment."
    )
    sub_parser_run.add_argument(
        "--not_gen",
        dest="gen_allure",
        action="store_false",
        help="dont't generate allure report."
    )
    sub_parser_run.add_argument(
        "--log_level",
        dest="level",
        choices=["trace", "debug", "info", "success", "warning", "error", "critical"],
        default="info",
        help="set log level."
    )
    sub_parser_run.add_argument(
        "--no_login",
        dest="no_login",
        action="store_false",
        help="don't login and make headers."
    )
    group = sub_parser_run.add_argument_group("multi-run")
    group.add_argument(
        "--mp",
        "--multi-process",
        dest="mp",
        action="store_true",
        help="specifies a multi-process running mode."
    )
    group.add_argument(
        "--mt",
        "--multi-thread",
        dest="mt",
        action="store_true",
        help="specifies a multi-thread running mode."
    )
    group.add_argument(
        "--dist-suite",
        dest="dist_suite",
        help="specifies a dist mode for per worker."
    )
    group.add_argument(
        "--dist-file",
        dest="dist_file",
        help="specifies a dist mode for per worker."
    )
    group.add_argument(
        "--dist-mark",
        dest="dist_mark",
        # 将传入参数值放到一个list中且至少需要传入一个值
        nargs="+",
        help="specifies a dist mode for per worker."
    )

    group = sub_parser_run.add_argument_group("qingcloud")
    group.add_argument(
        "--zone",
        dest="zone",
        help="qingcloud:switch zone of test environment."
    )
    group.add_argument(
        "--role",
        dest="role",
        default="user",
        help="qingcloud:switch role of user,defalut value:'user'"
    )
    group.add_argument(
        "--no_lease",
        dest="no_lease",
        action="store_false",
        help="qingcloud:turn off lease"
    )
    return sub_parser_run


def set_conf_file(env):
    conf_path = os.path.join(CONF_DIR, Conf.CONF_NAME)
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            doc = yaml.safe_load(f)
        doc['env'] = env
        if not doc.get(env):
            logger.error(f'测试环境-{env}还未在配置文件中配置！')
            sys.exit(1)
        with open(conf_path, 'w') as f:
            yaml.safe_dump(doc, f, default_flow_style=False)
        print(f'<AoMaker> 当前测试环境: {env}')
    else:
        logger.error(f'配置文件{conf_path}不存在')
        sys.exit(1)


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
    sub_parser_case = init_case_parser(subparsers)
    sub_parser_mcase = init_make_case_parser(subparsers)
    sub_parser_har2y = init_har2yaml_parser(subparsers)
    sub_parser_run = init_parser_run(subparsers)
    sub_parser_record = init_record_parser(subparsers)
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
        elif sys.argv[1] == "case":
            # aomaker case
            sub_parser_case.print_help()
        elif sys.argv[1] == "mcase":
            # aomaker mcase
            sub_parser_mcase.print_help()
        elif sys.argv[1] == "har2y":
            # aomaker har2y
            sub_parser_har2y.print_help()
        elif sys.argv[1] == "record":
            # aomaker record
            sub_parser_record.print_help()
        elif sys.argv[1] == "run":
            # aomaker run
            sub_parser_run.print_help()
        sys.exit(0)
    elif len(sys.argv) == 3:
        if sys.argv[1] == "run" and sys.argv[2] in ["-h", "--help"]:
            # aomaker run -h
            pytest.main(["-h"])
            sys.exit(0)
        elif sys.argv[1] == "run" and sys.argv[2] == "-e":
            # aomaker run -e xxx
            logger.error('please input env name in "conf/config.yaml"')
            sys.exit(0)
        elif sys.argv[1] == "make" and sys.argv[2] == "-t":
            # aomaker make -s xxx
            logger.error('please input file path(YAML or Swagger)')
            # print('please input template:"qingcloud" or "restful".default template style:restful')
            sys.exit(0)
    # elif sys.argv[1] == "run" and sys.argv[2] == "-e":
    #     # aomaker run -e xxx
    #     # print('please input env name in "conf/config.yaml"')
    #     # sys.exit(0)
    #
    #     set_conf_file(sys.argv[3])
    elif sys.argv[1] == "make" and sys.argv[2] == "-t" and sys.argv[3] not in ["qingcloud", "restful"]:
        logger.error('please input template style:qingcloud or restful')
        sys.exit(0)
    elif sys.argv[1] == "har2y":
        if not sys.argv[-1].endswith('.yaml') or sys.argv[-1].endswith('.har'):
            logger.error("please input YAML/HAR file path.")
            sys.exit(1)

    extra_args = []
    if len(sys.argv) >= 2 and sys.argv[1] in ["run"]:
        args, extra_args = parser.parse_known_args()
    else:
        args = parser.parse_args()
    if args.version:
        print(f"{__version__}")
        sys.exit(0)

    if sys.argv[1] == "startproject":
        print(__image__)
        main_scaffold(args)
        logger.info('项目脚手架创建完成')
    elif sys.argv[1] == "make":
        print(__image__)
        if sys.argv[2] == '-t' and sys.argv[3] == 'qingcloud':
            main_make(args.file_path, template=args.template)
        else:
            main_make(args.file_path)
        logger.info('api object渲染完成')
    elif sys.argv[1] == "case":
        print(__image__)
        main_case(args.file_path)
        logger.info('用例脚本编写完成')
    elif sys.argv[1] == "mcase":
        print(__image__)
        main_make_case(args.file_path)
        logger.info('测试用例生成完成')
    elif sys.argv[1] == "har2y":
        print(__image__)
        main_har2yaml(args)
        logger.info('har转换yaml完成')
    elif sys.argv[1] == "record":
        print(__image__)
        main_record(args)
        logger.info('用例录制完成')
    elif sys.argv[1] == "run":
        print(__image__)
        if sys.argv[2] == "-e":
            set_conf_file(args.env)
        # if "--log-level" in sys.argv or "-l" in sys.argv:
        if args.level:
            AoMakerLogger.change_level(args.level)
        kwargs = {}
        if args.zone:
            kwargs["zone"] = args.zone
        if args.role:
            kwargs["role"] = args.role
        kwargs["no_lease"] = args.no_lease

        from aomaker.runner import run, threads_run, processes_run
        login_obj = _handle_login(args.no_login)
        if args.mp:
            # login_obj = _handle_login()
            # 多进程
            if "--dist-mark" in sys.argv:
                mark_list = [f"-m {mark}" for mark in args.dist_mark]
                sys.exit(
                    processes_run(mark_list, login=login_obj, extra_args=extra_args, is_gen_allure=args.gen_allure,
                                  **kwargs))
            elif "--dist-suite" in sys.argv:
                sys.exit(processes_run(args.dist_suite, login=login_obj, extra_args=extra_args,
                                       is_gen_allure=args.gen_allure, **kwargs))
            elif "--dist-file" in sys.argv:
                sys.exit(processes_run({"path": args.dist_file}, login=login_obj, extra_args=extra_args,
                                       is_gen_allure=args.gen_allure, **kwargs))
        if args.mt:
            # login_obj = _handle_login()
            # 多线程
            if "--dist-mark" in sys.argv:
                mark_list = [f"-m {mark}" for mark in args.dist_mark]
                sys.exit(threads_run(mark_list, login=login_obj, extra_args=extra_args, is_gen_allure=args.gen_allure,
                                     **kwargs))
            elif "--dist-suite" in sys.argv:
                sys.exit(threads_run(args.dist_suite, login=login_obj, extra_args=extra_args,
                                     is_gen_allure=args.gen_allures, **kwargs))
            elif "--dist-file" in sys.argv:
                sys.exit(threads_run({"path": args.dist_file}, login=login_obj, extra_args=extra_args,
                                     is_gen_allure=args.gen_allure, **kwargs))
        # login_obj = _handle_login()
        sys.exit(run(extra_args, login=login_obj, is_gen_allure=args.gen_allure, **kwargs))


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


def main_record_alias():
    """ command alias
        arec = aomaker record
    """
    sys.argv.insert(1, "record")
    main()


def _handle_login(is_login: bool):
    if is_login is False:
        return
    sys.path.append(os.getcwd())
    exec('from login import Login')
    login_obj = locals()['Login']()
    return login_obj


if __name__ == '__main__':
    main()
