# -*- coding: utf-8 -*-
from .controller import SingleController, ThreadWithResult
from backend import CompilerVM, Project
from frontend import Lexer, GlobalParser, ExprParser
from utils import CommandException

import os


def _traverse_path(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    return sum([_traverse_path(os.path.join(path, file)) for file in os.listdir(path)], [])


class LexerController(SingleController):

    def __init__(self, workspace: str) -> None:
        super().__init__("lex")
        self._workspace: str = workspace
        self._lexer: Lexer = Lexer(self._workspace)
        self._thread: ThreadWithResult = ThreadWithResult(self._lexer.lex_with_writer)

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if "thread-index" in kwargs:
            thread_index = int(kwargs["thread-index"])
        else:
            thread_index = 0
        if len(args) != 1:
            raise CommandException("Invalid number of arguments.")
        self._thread.start(args[0], thread_index)


class GlobalParserController(SingleController):

    def __init__(self, workspace: str) -> None:
        super().__init__("parse")
        self._workspace: str = workspace
        self._parser: GlobalParser = GlobalParser(self._workspace)
        self._thread: ThreadWithResult = ThreadWithResult(self._parser.parse_to_file)

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if "thread-index" in kwargs:
            thread_index = int(kwargs["thread-index"])
        else:
            thread_index = 0
        if len(args) != 1:
            raise CommandException("Invalid number of arguments.")
        self._thread.start(args[0], thread_index)


class ExprParserController(SingleController):

    def __init__(self, workspace: str) -> None:
        super().__init__("parse-expr")
        self._workspace: str = workspace
        self._parser: ExprParser = ExprParser(self._workspace)
        self._thread: ThreadWithResult = ThreadWithResult(self._parser.parse_expr_to_file)

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if "thread-index" in kwargs:
            thread_index = int(kwargs["thread-index"])
        else:
            thread_index = 0
        if len(args) != 1:
            raise CommandException("Invalid number of arguments.")
        self._thread.start(args[0], thread_index)


class CompilerVMController(SingleController):

    def __init__(self, project: Project) -> None:
        super().__init__("run-vm")
        self._project: Project = project
        self._compiler: CompilerVM = CompilerVM(self._project)
        self._thread: ThreadWithResult = ThreadWithResult(self._compiler.compile)

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        if "thread-index" in kwargs:
            thread_index = int(kwargs["thread-index"])
        else:
            thread_index = 0
        if len(args) != 1:
            raise CommandException("Invalid number of arguments.")
        self._thread.start(args[0], thread_index)
