# -*- coding: utf-8 -*-
from utils.task import TaskResult

from abc import ABC, abstractmethod
from threading import Thread
from typing import Optional, Callable


class ThreadWithResult:

    def __init__(self, target: Callable[[...], TaskResult]) -> None:
        self._result: Optional[TaskResult] = None
        self._thread: Thread = Thread(target=self.__target_wrapper(target))

    def join(self) -> TaskResult:
        self._thread.join()
        # noinspection PyTypeChecker
        return self._result

    def start(self) -> None:
        self._thread.start()

    def __target_wrapper(self, target: Callable[[...], TaskResult]) -> Callable[[...], None]:
        def wrapper(*args, **kwargs):
            self._result = target(*args, **kwargs)
        return wrapper


class Controller(ABC):

    def __init__(self, matching_command: list[str]) -> None:
        self._matching_command = matching_command

    @abstractmethod
    def handle(self, command: list[str]) -> Optional[ThreadWithResult]:
        pass

    @staticmethod
    def _get_params(command: list[str]) -> dict[str, str]:
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
            if arg.startswith("-"):
                arg = arg[1:]
            elif arg.startswith("--"):
                arg = arg[2:]
            if "=" in arg:
                key, value = arg.split("=", 1)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                kwargs[key] = value
            else:
                kwargs[arg] = "true"
        return kwargs


class SingleController(Controller, ABC):

    def __init__(self, matching_command: str) -> None:
        super().__init__([matching_command])

    def handle(self, command: list[str]) -> Optional[ThreadWithResult]:
        if command[0] in self._matching_command:
            return self._handle(*self._get_params(command[1:]))
        return None

    @abstractmethod
    def _handle(self, args: list[str], kwargs: dict[str, str]) -> ThreadWithResult:
        pass


class GroupController(Controller):

    def __init__(self, controllers: list[Controller]) -> None:
        super().__init__(sum([controller._matching_command for controller in controllers], []))
        self._controllers: list[Controller] = controllers

    def handle(self, command: list[str]) -> Optional[ThreadWithResult]:
        for controller in self._controllers:
            if command[0] in controller._matching_command:
                return controller.handle(command)
        return None
