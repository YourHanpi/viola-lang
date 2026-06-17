# -*- coding: utf-8 -*-
from .compiler_exceptions import InternalCompilerException, CommandException
from .compiler_params import COMPILER_PARAMS
from .source_info import VIOLA_INIT

from enum import IntEnum
import os
from sys import stderr
from threading import Lock
import time
from typing import TextIO, Optional


class LogLevel(IntEnum):
    """日志级别枚举，定义DEBUG到CRITICAL五个级别。"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class LogMessage:
    """表示一条日志消息，包含级别、发送者、消息内容与时间戳。"""

    def __init__(self, level: LogLevel, sender: str, message: str) -> None:
        """
        初始化LogMessage。
        :param level: 日志级别。
        :param sender: 发送者名称。
        :param message: 日志消息内容。
        """
        self._level: LogLevel = level
        self._sender: str = sender
        self._message: str = message
        self._timestamp: float = time.time()

    def __str__(self) -> str:
        return f"[{self._level.name}] {self._sender} @ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._timestamp))}: {self._message}"


class FileHandler:
    """日志文件处理器，负责日志文件的打开、写入与关闭。"""

    def __init__(self) -> None:
        """
        初始化FileHandler。
        初始化工作区、路径、处理器与编码等属性为空状态。
        """
        self._workspace: str = ""
        self._path: str = ""
        self._handler: Optional[TextIO] = None
        # noinspection PyTypeChecker
        self._encoding: str = COMPILER_PARAMS["log-encoding"]
        self._output_name: str = ""

    def close(self) -> None:
        """关闭日志文件处理器。"""
        if self._handler is not None:
            self._handler.close()
            self._handler = None

    def config_project(self, workspace: str, output_name: str) -> None:
        """配置项目的工作区与输出名称。"""
        self._workspace = workspace
        self._output_name = os.path.basename(output_name.rstrip("/").rstrip("\\")) or output_name

    def log(self, message: str) -> None:
        """向日志文件写入一条消息。"""
        if self._handler is None:
            raise InternalCompilerException("Log file handler is not opened.", VIOLA_INIT)
        self._handler.write(message + "\n")

    def open(self) -> None:
        """打开日志文件，准备写入。"""
        if self._workspace == "":
            raise InternalCompilerException("Log file handler is not configured.", VIOLA_INIT)
        if not os.path.exists(os.path.join(self._workspace, "__log__")):
            os.mkdir(os.path.join(self._workspace, "__log__"))
        self._path = f"{self._workspace}/__log__/{self._output_name}-{time.strftime('%Y-%m-%d-%H-%M-%S')}.log"
        self._handler = open(self._path, "a", encoding=self._encoding)


class LoggerController:
    """日志控制器，管理日志级别与文件处理器。"""

    def __init__(self) -> None:
        """
        初始化LoggerController。
        默认日志级别为INFO，并创建文件处理器实例。
        """
        self._log_level: LogLevel = LogLevel.INFO
        self._file_handler: FileHandler = FileHandler()

    def close(self) -> None:
        """关闭日志文件处理器。"""
        self._file_handler.close()

    def config_log_level(self, log_level: str) -> None:
        """配置日志级别。"""
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

    def config_workspace(self, workspace: str, output_name: str) -> None:
        """配置日志的工作区与输出文件名。"""
        self._file_handler.config_project(workspace, output_name)

    @property
    def log_level(self) -> LogLevel:
        return self._log_level

    def open(self) -> None:
        """打开日志文件。"""
        self._file_handler.open()

    def write(self, message: str) -> None:
        """将消息写入日志文件。"""
        self._file_handler.log(message)


LOGGER_CONTROLLER: LoggerController = LoggerController()


class Logger:
    """日志记录器，提供按级别记录日志的便捷接口。"""

    def __init__(self, name: str) -> None:
        """
        初始化Logger。
        :param name: 日志记录器名称，用于标识消息发送者。
        """
        self._name: str = name

    def critical(self, message: str) -> None:
        """记录CRITICAL级别的日志消息。"""
        self.log(LogLevel.CRITICAL, message)

    def debug(self, message: str) -> None:
        """记录DEBUG级别的日志消息。"""
        self.log(LogLevel.DEBUG, message)

    def error(self, message: str) -> None:
        """记录ERROR级别的日志消息。"""
        self.log(LogLevel.ERROR, message)

    def info(self, message: str) -> None:
        """记录INFO级别的日志消息。"""
        self.log(LogLevel.INFO, message)

    def log(self, level: LogLevel, message: str) -> None:
        """
        记录指定级别的日志消息。
        若级别不低于全局日志级别，则输出到控制台并写入日志文件。
        """
        if level >= LOGGER_CONTROLLER.log_level:
            msg = LogMessage(level, self._name, message)
            with Lock():
                if level.value <= LogLevel.WARNING.value:
                    print(msg)
                else:
                    print(msg, file=stderr)
                LOGGER_CONTROLLER.write(str(msg))

    def warning(self, message: str) -> None:
        """记录WARNING级别的日志消息。"""
        self.log(LogLevel.WARNING, message)
