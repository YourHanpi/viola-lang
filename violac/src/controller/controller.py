# -*- coding: utf-8 -*-
from utils.task import TaskResult, TaskResultState

from abc import ABC, abstractmethod
from threading import Thread
from typing import Optional, Callable


class ThreadWithResult:

    def __init__(self, target: Callable[[...], TaskResult]) -> None:
        self._result: Optional[TaskResult] = None
        self._target: Callable[[...], None] = self.__target_wrapper(target)
        self._thread: Optional[Thread] = None

    @property
    def is_busy(self) -> bool:
        return self._result is None

    def join(self) -> TaskResult:
        if self._thread is None:
            return TaskResult(TaskResultState.PASSED)
        self._thread.join()
        # noinspection PyTypeChecker
        return self._result

    def start(self, *args, **kwargs) -> None:
        self._result = None
        self._thread = Thread(target=self._target, args=args, kwargs=kwargs)
        self._thread.start()

    def __target_wrapper(self, target: Callable[[...], TaskResult]) -> Callable[[...], None]:
        def wrapper(*args, **kwargs):
            self._result = target(*args, **kwargs)
        return wrapper


class Controller(ABC):

    def __init__(self, matching_command: list[str]) -> None:
        self._matching_command = matching_command

    @abstractmethod
    def handle(self, command: list[str]) -> None:
        pass

    @property
    @abstractmethod
    def is_busy(self) -> bool:
        pass

    @abstractmethod
    def join(self) -> TaskResult:
        pass

    @staticmethod
    def _get_params(command: list[str]) -> tuple[list[str], dict[str, str]]:
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
        super().__init__([matching_command])
        self._thread: Optional[ThreadWithResult] = None

    def handle(self, command: list[str]) -> None:
        if command[0] in self._matching_command:
            self._handle(*self._get_params(command[1:]))

    @property
    def is_busy(self) -> bool:
        return self._thread is not None and self._thread.is_busy

    def join(self) -> TaskResult:
        if self._thread is None:
            return TaskResult(TaskResultState.PASSED)
        return self._thread.join()

    @abstractmethod
    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        pass


class EmptyController(SingleController):

    def __init__(self) -> None:
        super().__init__("\0")

    @property
    def is_busy(self) -> bool:
        return False

    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        pass
