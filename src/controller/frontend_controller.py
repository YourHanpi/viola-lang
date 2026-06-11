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
        self._all_paths: list[str] = []

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if not os.path.exists(args[0]):
            raise CommandException(f"Path \"{args[0]}\" does not exist")
        self._all_paths = _traverse_path(args[0])
        if "j" not in kwargs:
            for p in self._all_paths:
                self._lexer.lex_with_writer(p)
            return
        if not kwargs["j"].isnumeric():
            raise CommandException("Invalid number of parameter \"-j\"")
        threads_num: int = int(kwargs["j"])
        self._lexers = [deepcopy(self._lexer) for _ in range(threads_num)]
        for i in range(threads_num):
            self._threads.append(Thread(target=LexerController.__thread_task, args=(self._lexers[i],)))
            self._threads[i].start()
        for t in self._threads:
            t.join()
        self._threads.clear()

    def __thread_task(self, lexer: Lexer) -> None:
        while len(self._all_paths) > 0:
            with Lock():
                if len(self._all_paths) == 0:
                    break
                path = self._all_paths.pop()
            lexer.lex_with_writer(path)


class ParserController(SingleController):

    def __init__(self) -> None:
        super().__init__("parse")
