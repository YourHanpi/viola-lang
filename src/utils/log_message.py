# -*- coding: utf-8 -*-
from .compiler_params import COMPILER_PARAMS

from enum import Enum
from sys import stderr
import time
from typing import TextIO, Optional


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class LogMessage:

    def __init__(self, level: LogLevel, sender: str, message: str) -> None:
        self._level: LogLevel = level
        self._sender: str = sender
        self._message: str = message
        self._timestamp: float = time.time()

    def __str__(self) -> str:
        return f"[{self._level.name}] {self._sender} @ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._timestamp))}: {self._message}"


class FileHandler:

    def __init__(self, workspace: str) -> None:
        self._workspace: str = workspace
        self._path: str = ""
        self._handler: Optional[TextIO] = None
        # noinspection PyTypeChecker
        self._encoding: str = COMPILER_PARAMS["log-encoding"]

    def open(self) -> None:
        self._path = f"{self._workspace}/viola-{time.strftime('%Y-%m-%d-%H-%M-%S')}.log"
        self._handler = open(self._path, "a")


class Logger:

    def __init__(self, name: str, log_level: LogLevel = LogLevel.INFO) -> None:
        self._name: str = name
        self._log_level: LogLevel = log_level

    def critical(self, message: str) -> None:
        self.log(LogLevel.CRITICAL, message)

    def debug(self, message: str) -> None:
        self.log(LogLevel.DEBUG, message)

    def error(self, message: str) -> None:
        self.log(LogLevel.ERROR, message)

    def info(self, message: str) -> None:
        self.log(LogLevel.INFO, message)

    def log(self, level: LogLevel, message: str) -> None:
        if level >= self._log_level:
            if level.value <= LogLevel.WARNING.value:
                print(LogMessage(level, self._name, message))
            else:
                print(LogMessage(level, self._name, message), file=stderr)

    def warning(self, message: str) -> None:
        self.log(LogLevel.WARNING, message)
