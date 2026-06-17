# -*- coding: utf-8 -*-
from controller.main_controller import MainController
from utils import CommandException

import os
import sys


def _get_params(command: list[str]) -> tuple[list[str], dict[str, str]]:
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
    if "o" not in kwargs:
        kwargs["o"] = os.path.join(args[0], "viola-compiled")
    if "j" not in kwargs:
        kwargs["j"] = "1"
    elif kwargs["j"] == "true":
        kwargs["j"] = str(os.process_cpu_count() - 1)
    return args, kwargs


def main() -> None:
    args, kwargs = _get_params(sys.argv[1:])
    args, kwargs = _set_default(args, kwargs)
    if kwargs["j"].isdecimal():
        threads_num: int = int(kwargs["j"])
    else:
        raise CommandException("Parameter '-j' should be integer")
    if args[0] == "compile":
        MainController(args[1], kwargs["i"], kwargs["o"], threads_num, kwargs).run()


if __name__ == "__main__":
    main()
