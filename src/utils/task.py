# -*- coding: utf-8 -*-
from .compiler_exceptions import CommandException

from enum import Enum
from threading import Lock


class TaskResult(Enum):
    SUCCESS = 0
    FAILURE = 1
    DELAYED = 2


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
