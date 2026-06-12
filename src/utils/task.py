# -*- coding: utf-8 -*-
from .compiler_exceptions import CommandException

from enum import Enum
from threading import Lock
from typing import Optional


class TaskResultState(Enum):
    SUCCESS = 0
    FAILURE = 1
    DELAYED = 2


class TaskResult:

    def __init__(self, state: TaskResultState, data: Optional[list[str]] = None) -> None:
        self._state: TaskResultState = state
        self._data: list[str] = data if data is not None else []

    @property
    def data(self) -> list[str]:
        return self._data

    @property
    def state(self) -> TaskResultState:
        return self._state


class TaskStack:

    def __init__(self) -> None:
        self._tasks: list[str] = []
        self._executing_tasks_count: int = 0

    def finish_task(self) -> None:
        with Lock():
            if self._executing_tasks_count == 0:
                raise CommandException("No task to finish.")
            self._executing_tasks_count -= 1

    def get(self) -> str:
        with Lock():
            if len(self._tasks) == 0:
                raise CommandException("No task to execute.")
            task = self._tasks.pop()
            self._executing_tasks_count += 1
        return task

    @property
    def is_finished(self) -> bool:
        return len(self._tasks) == 0 and self._executing_tasks_count == 0

    def put(self, command: str) -> None:
        with Lock():
            self._tasks.append(command)


TASK_STACK: TaskStack = TaskStack()
