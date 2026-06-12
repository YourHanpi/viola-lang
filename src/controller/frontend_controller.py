# -*- coding: utf-8 -*-
from .controller import SingleController, ThreadWithResult
from frontend import Lexer
from utils import CommandException
from utils.task import TaskResult

from copy import deepcopy
import os
from threading import Thread, Lock
from typing import Callable


def _traverse_path(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    return sum([_traverse_path(os.path.join(path, file)) for file in os.listdir(path)], [])


class LexerController(SingleController):

    def __init__(self, workspace: str) -> None:
        super().__init__("lex")
        self._workspace: str = workspace

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> ThreadWithResult:
        if "thread-index" in kwargs:
            thread_index = int(kwargs["thread-index"])
        else:
            thread_index = 0
        if len(args) != 1:
            raise CommandException("Invalid number of arguments.")
        target: Callable[[...], TaskResult] = Lexer(self._workspace, thread_index).lex_with_writer
