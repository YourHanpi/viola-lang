# -*- coding: utf-8 -*-
from .compiler_exceptions import CommandException

from enum import Enum
from threading import Lock
from typing import Optional


class TaskResultState(Enum):
    """任务结果状态枚举，定义失败、成功、延迟与跳过四种状态。"""
    FAILURE = 0
    SUCCESS = 1
    DELAYED = 2
    PASSED = 3


class TaskResult:
    """任务结果类，封装任务执行的状态和数据。"""

    def __init__(self, state: TaskResultState, data: Optional[list[list[str]]] = None) -> None:
        """
        初始化TaskResult。
        :param state: 任务结果状态。
        :param data: 任务结果数据，可选。
        """
        self._state: TaskResultState = state
        self._data: list[list[str]] = data if data is not None else []

    @property
    def data(self) -> list[list[str]]:
        return self._data

    @property
    def state(self) -> TaskResultState:
        return self._state


class TaskStack:
    """线程安全的任务栈，管理待执行任务的入栈、出栈与完成状态。"""

    def __init__(self) -> None:
        """
        初始化TaskStack。
        任务列表为空，正在执行的任务计数为0。
        """
        self._tasks: list[list[str]] = []
        self._executing_tasks_count: int = 0

    def finish_task(self) -> None:
        """标记一个任务已完成。"""
        with Lock():
            if self._executing_tasks_count == 0:
                raise CommandException("No task to finish.")
            self._executing_tasks_count -= 1

    def get(self) -> list[str]:
        """从栈顶取出一个待执行任务。"""
        with Lock():
            if len(self._tasks) == 0:
                raise CommandException("No task to execute.")
            task = self._tasks.pop()
            self._executing_tasks_count += 1
        return task

    @property
    def is_empty(self) -> bool:
        return len(self._tasks) == 0

    @property
    def is_finished(self) -> bool:
        return len(self._tasks) == 0 and self._executing_tasks_count == 0

    def put(self, command: list[str]) -> None:
        """向栈顶压入一个任务。"""
        with Lock():
            self._tasks.append(command)


TASK_STACK: TaskStack = TaskStack()
