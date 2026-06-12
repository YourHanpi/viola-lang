# -*- coding: utf-8 -*-
from .compiler_exceptions import InternalCompilerException, CommandException
from .compiler_params import COMPILER_PARAMS
from .source_info import VIOLA_INIT

from enum import Enum
from sys import stderr
from threading import Lock
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

    def __init__(self) -> None:
        self._workspace: str = ""
        self._path: str = ""
        self._handler: Optional[TextIO] = None
        # noinspection PyTypeChecker
        self._encoding: str = COMPILER_PARAMS["log-encoding"]

    def config_workspace(self, workspace: str) -> None:
        self._workspace = workspace

    def close(self) -> None:
        if self._handler is not None:
            self._handler.close()
            self._handler = None

    def log(self, message: str) -> None:
        if self._handler is None:
            raise InternalCompilerException("Log file handler is not opened.", VIOLA_INIT)
        self._handler.write(message + "\n")

    def open(self) -> None:
        if self._workspace == "":
            raise InternalCompilerException("Log file handler is not configured.", VIOLA_INIT)
        self._path = f"{self._workspace}/viola-{time.strftime('%Y-%m-%d-%H-%M-%S')}.log"
        self._handler = open(self._path, "a")


class LoggerController:

    def __del__(self) -> None:
        self._file_handler.close()

    def __init__(self) -> None:
        self._log_level: LogLevel = LogLevel.INFO
        self._file_handler: FileHandler = FileHandler()

    def config_log_level(self, log_level: str) -> None:
        match log_level:
            case "debug":
                self._log_level = LogLevel.DEBUG
            case "info":
                self._log_level = LogLevel.INFO
            case "warning":
                self._log_level = LogLevel.WARNING
            case "error":
                self._log_level = LogLevel.ERROR
            case "critical":
                self._log_level = LogLevel.CRITICAL
            case _:
                raise CommandException("Invalid log level.")

    def config_workspace(self, workspace: str) -> None:
        self._file_handler.config_workspace(workspace)

    @property
    def log_level(self) -> LogLevel:
        return self._log_level

    def open(self) -> None:
        self._file_handler.open()

    def write(self, message: str) -> None:
        self._file_handler.log(message)


LOGGER_CONTROLLER: LoggerController = LoggerController()


class Logger:

    def __init__(self, name: str) -> None:
        self._name: str = name

    def critical(self, message: str) -> None:
        self.log(LogLevel.CRITICAL, message)

    def debug(self, message: str) -> None:
        self.log(LogLevel.DEBUG, message)

    def error(self, message: str) -> None:
        self.log(LogLevel.ERROR, message)

    def info(self, message: str) -> None:
        self.log(LogLevel.INFO, message)

    def log(self, level: LogLevel, message: str) -> None:
        if level >= LOGGER_CONTROLLER.log_level:
            msg = LogMessage(level, self._name, message)
            with Lock():
                if level.value <= LogLevel.WARNING.value:
                    print(msg)
                else:
                    print(msg, file=stderr)
                LOGGER_CONTROLLER.write(str(msg))

    def warning(self, message: str) -> None:
        self.log(LogLevel.WARNING, message)
