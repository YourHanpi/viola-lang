# -*- coding: utf-8 -*-
from utils.task import TaskResult, TaskResultState

from abc import ABC, abstractmethod
from threading import Thread
from typing import Optional, Callable


class ThreadWithResult:
    """带返回值的线程封装类。"""

    def __init__(self, target: Callable[[...], TaskResult]) -> None:
        """初始化带返回值的线程对象。
        :param target: 线程目标函数，应返回TaskResult对象。
        """
        self._result: Optional[TaskResult] = None
        self._target: Callable[[...], None] = self.__target_wrapper(target)
        self._thread: Optional[Thread] = None

    @property
    def is_busy(self) -> bool:
        return self._result is None

    def join(self) -> TaskResult:
        """等待线程执行完毕并获取返回值。"""
        if self._thread is None:
            return TaskResult(TaskResultState.PASSED)
        self._thread.join()
        # noinspection PyTypeChecker
        return self._result

    def start(self, *args, **kwargs) -> None:
        """启动线程。"""
        self._result = None
        self._thread = Thread(target=self._target, args=args, kwargs=kwargs)
        self._thread.start()

    def __target_wrapper(self, target: Callable[[...], TaskResult]) -> Callable[[...], None]:
        """包装目标函数，将返回值保存到实例变量中。"""
        def wrapper(*args, **kwargs):
            self._result = target(*args, **kwargs)
        return wrapper


class Controller(ABC):
    """控制器抽象基类，定义控制器的基本接口。"""

    def __init__(self, matching_command: list[str]) -> None:
        """初始化控制器对象。
        :param matching_command: 匹配的命令列表。
        """
        self._matching_command = matching_command

    @abstractmethod
    def handle(self, command: list[str]) -> None:
        """处理命令。"""
        pass

    @property
    @abstractmethod
    def is_busy(self) -> bool:
        """获取控制器是否正忙。"""
        pass

    @abstractmethod
    def join(self) -> TaskResult:
        """等待控制器完成任务并获取结果。"""
        pass

    @staticmethod
    def _get_params(command: list[str]) -> tuple[list[str], dict[str, str]]:
        """解析命令行参数，将其分割为位置参数和关键字参数。"""
        args: list[str] = []
        kwargs: dict[str, str] = {}
        for arg in command:
            if not arg.startswith("-"):
                if arg.startswith('"') and arg.endswith('"'):
                    arg = arg[1:-1]
                elif arg.startswith("'") and arg.endswith("'"):
                    arg = arg[1:-1]
                args.append(arg)
                continue
            if arg.startswith("--"):
                arg = arg[2:]
            elif arg.startswith("-"):
                arg = arg[1:]
            if "=" in arg:
                key, value = arg.split("=", 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                kwargs[key] = value
            else:
                kwargs[arg] = "true"
        return args, kwargs


class SingleController(Controller, ABC):

    def __init__(self, matching_command: str) -> None:
        """初始化单命令控制器对象。
        :param matching_command: 匹配的命令名。
        """
        super().__init__([matching_command])
        self._thread: Optional[ThreadWithResult] = None

    def handle(self, command: list[str]) -> None:
        """处理命令并调用内部处理方法。"""
        if command[0] in self._matching_command:
            try:
                self._handle(*self._get_params(command[1:]))
            except Exception as exc:
                self._handle_error(exc)

    @property
    def is_busy(self) -> bool:
        """获取控制器是否正忙。"""
        return self._thread is not None and self._thread.is_busy

    def join(self) -> TaskResult:
        """等待当前任务执行完毕。"""
        if self._thread is None:
            return TaskResult(TaskResultState.PASSED)
        return self._thread.join()

    @abstractmethod
    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        """内部处理方法，由子类实现具体逻辑。"""
        pass

    def _handle_error(self, exc: Exception) -> None:
        """处理错误。"""
        print(str(exc))


class EmptyController(SingleController):
    """空控制器类，用于占位，始终处于空闲状态。"""

    def __init__(self) -> None:
        """初始化空控制器对象。"""
        super().__init__("\0")

    @property
    def is_busy(self) -> bool:
        """获取控制器是否正忙，空控制器始终返回False。"""
        return False

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        """空处理函数，不执行任何操作。"""
        pass

    def _handle_error(self, exc: Exception) -> None:
        """空错误处理函数，不执行任何操作。"""
        pass
