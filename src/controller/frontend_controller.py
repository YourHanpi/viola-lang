# -*- coding: utf-8 -*-
from .controller import SingleController
from frontend import Lexer
from utils import CommandException

from copy import deepcopy
import os
from threading import Thread, Lock


def _traverse_path(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    return sum([_traverse_path(os.path.join(path, file)) for file in os.listdir(path)], [])


class LexerController(SingleController):

    def __init__(self) -> None:
        super().__init__("lex")
        self._lexer: Lexer = Lexer()
        self._lexers: list[Lexer] = []
        self._threads: list[Thread] = []

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if not os.path.exists(args[0]):
            raise CommandException(f"Path \"{args[0]}\" does not exist")
        all_paths: list[str] = _traverse_path(args[0])
        if "j" not in kwargs:
            for p in all_paths:
                self._lexer.lex_with_writer(p)
            return
        if not kwargs["j"].isnumeric():
            raise CommandException("Invalid number of parameter \"-j\"")
        threads_num: int = int(kwargs["j"])
        self._lexers = [deepcopy(self._lexer) for _ in range(threads_num)]
        while len(all_paths) > 0:
            for i in range(len(self._lexers)):
                if len(all_paths) == 0:
                    break
                self._threads.append(Thread(target=self._lexers[i].lex_with_writer, args=(all_paths.pop(),)))
                self._threads[i].start()
            for i in range(len(self._threads)):
                self._threads[i].join()
