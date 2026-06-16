# -*- coding: utf-8 -*-
from .source_info import SourceInfo, VIOLA_INIT

from warnings import warn


class CommandException(Exception):
    """
    命令异常类。
    """

    def __init__(self, message: str) -> None:
        """
        初始化命令异常对象。
        :param message: 错误信息。
        """
        self._message: str = message

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self._message


class InternalCommandException(CommandException):

    def __init__(self, message: str) -> None:
        """
        初始化内部命令异常对象。
        :param message: 错误信息。
        """
        super().__init__("Internal exception occurred, please report this exception.\n" + message)


class CompilerException(Exception):
    """
    编译异常类。
    """

    def __init__(self, message: str, src_info: SourceInfo) -> None:
        """
        初始化编译异常对象。
        :param message: 异常信息。
        :param src_info: 源代码信息。
        """
        self._message: str = message
        self._src_info: SourceInfo = src_info

    def __str__(self) -> str:
        return self._src_info.traceback + "\n" + self.__class__.__name__ + ": " + self._message


class InternalCompilerException(CompilerException):
    """
    内部编译异常类。
    """

    def __init__(self, message: str, src_info: SourceInfo) -> None:
        """
        初始化内部编译异常对象。
        :param message: 错误信息。
        :param src_info: 源代码信息。
        """
        super().__init__("Internal exception occurred, please report this exception.\n" + message, src_info)


class CompilerParamError(Exception):
    """
    参数错误。
    """

    def __init__(self, message: str, key: str, value: str) -> None:
        """
        初始化参数错误对象。
        :param message: 错误信息。
        :param key: 出错的参数名。
        :param value: 出错的参数值。
        """
        self._message: str = message
        self._key: str = key
        self._value: str = value

    def __str__(self) -> str:
        return (f"{self._message}\n"
                f"\tat {self._key}:{self._value}\n")


class CompilerExceptionGroup(CompilerException):
    """
    编译异常组类。
    """

    def __init__(self, exceptions: list[CompilerException]) -> None:
        """
        初始化编译异常组对象。
        :param exceptions: 错误列表。
        """
        super().__init__("", src_info=VIOLA_INIT)
        self._exceptions: list[CompilerException] = exceptions

    def __str__(self) -> str:
        return "\n\n".join([str(e) for e in self._exceptions])


def unreachable_warning(message: str, src_info: SourceInfo):
    """
    无法执行警告。
    :param message: 警告信息。
    :param src_info: 源代码信息。
    """
    warn(f"{src_info.traceback}\nUnreachableWarning: {message}")
