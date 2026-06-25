# -*- coding: utf-8 -*-
from controller.main_controller import MainController
from controller.utils_controller import UtilsController
from utils import CommandException

import os
import sys


def _get_params(command: list[str]) -> tuple[list[str], dict[str, str]]:
    """解析命令行参数，将其分割为位置参数和关键字参数。"""
    args: list[str] = []
    kwargs: dict[str, str] = {}
    for arg in command:
        if not arg.startswith("-"):
            if arg.startswith('"') and arg.endswith('"'):
                arg = arg[1:-1]
            elif arg.startswith("'") and arg.endswith("'"):
                arg = arg[1:-1]
            args.append(arg)
            continue
        if arg.startswith("--"):
            arg = arg[2:]
        elif arg.startswith("-"):
            arg = arg[1:]
        if "=" in arg:
            key, value = arg.split("=", 1)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            kwargs[key] = value
        else:
            kwargs[arg] = "true"
    return args, kwargs


def _set_default(args: list[str], kwargs: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """为未指定的参数设置默认值。"""
    if "o" not in kwargs:
        kwargs["o"] = os.path.join(args[0], "viola-compiled")
    if "j" not in kwargs:
        kwargs["j"] = "1"
    elif kwargs["j"] == "true":
        kwargs["j"] = str(os.cpu_count() - 1)
    return args, kwargs


def main() -> None:
    """Viola编译器入口函数。"""
    if len(sys.argv) < 2:
        UtilsController().run("help", [], {})
    args, kwargs = _get_params(sys.argv[1:])
    args, kwargs = _set_default(args, kwargs)
    if kwargs["j"].isdecimal():
        threads_num: int = int(kwargs["j"])
    else:
        raise CommandException("Parameter '-j' should be integer")
    if args[0] == "compile":
        MainController(args[1], kwargs["i"], kwargs["o"], threads_num, kwargs).run()
    else:
        UtilsController().run(args[0], args[1:], kwargs)


if __name__ == "__main__":
    main()
