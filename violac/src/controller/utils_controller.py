# -*- coding: utf-8 -*-
from typing import Callable


class UtilsController:
    """工具控制器类，处理辅助命令（帮助、版本信息等）。"""

    def __init__(self) -> None:
        """初始化工具控制器，注册命令映射表。"""
        self._commands: dict[str, Callable[[list[str], dict[str, str]], None]] = {
            "about": lambda args, kwargs: self._about(),
            "help": lambda args, kwargs: self._help(),
            "license": lambda args, kwargs: self._license(),
            "version": lambda args, kwargs: self._version()
        }

    def run(self, command: str, args: list[str], kwargs: dict[str, str]) -> None:
        """运行指定的工具命令。"""
        if command not in self._commands:
            print("Invalid command. Use 'violac help' to see available commands.")
            return
        self._commands[command](args, kwargs)

    @staticmethod
    def _about() -> None:
        """显示关于信息。"""
        print("Viola - A safe, fast and easy to asynchronous programming language")
        print("Author: 白霜渡鸦_Corvus")
        print("Github: https://github.com/YourHanpi/viola-lang/")
        print("License: GPL-v3.0")
        print("Business license will be accessible after version 1.0")
        UtilsController._version()

    @staticmethod
    def _help() -> None:
        """显示帮助信息。"""
        print("""
Usage: violac [command] [options] [arguments]

Commands:
    about                           Show the about info of violac.
    compile                         Compile a viola file.
        Options and arguments:
            <argument>              Specify a workspace for compiling. It will be CWD if not be specified.
            -i          [REQUIRED]  Specify an entry of the program.
            -j                      Specify a number of threads for compiling.
            -o                      Specify an output dir for the compiler.
    help                            Show this help message.
    license                         Show the license of violac.
    version                         Show the version of violac.
""")

    @staticmethod
    def _license() -> None:
        """显示许可证信息。"""
        with open("LICENSE", "r", encoding="utf-8") as f:
            print(f.read())

    @staticmethod
    def _version() -> None:
        """显示版本信息。"""
        with open(".version", "r", encoding="utf-8") as f:
            print(f"Viola compiler version: {f.read()}")
