# -*- coding: utf-8 -*-
from typing import Callable


class UtilsController:

    def __init__(self) -> None:
        self._commands: dict[str, Callable[[list[str], dict[str, str]], None]] = {
            "about": lambda args, kwargs: self._about(),
            "help": lambda args, kwargs: self._help(),
            "license": lambda args, kwargs: self._license(),
            "version": lambda args, kwargs: self._version()
        }

    @staticmethod
    def _about() -> None:
        print("Viola - A safe, fast and easy to asynchronous programming language")
        print("Author: 白霜渡鸦_Corvus")
        print("Github: https://github.com/YourHanpi/viola-lang/")
        print("License: GPL-v3.0")
        print("Business license will be accessible after version 1.0")
        UtilsController._version()

    @staticmethod
    def _help() -> None:
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
        with open("LICENSE", "r", encoding="utf-8") as f:
            print(f.read())

    @staticmethod
    def _version() -> None:
        with open(".version", "r", encoding="utf-8") as f:
            print(f"Viola compiler version: {f.read()}")
