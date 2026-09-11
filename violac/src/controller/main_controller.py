# -*- coding: utf-8 -*-
import os
import shutil
import time

from .controller import Controller, EmptyController
from .single_controllers import LexerController, GlobalParserController, ExprParserController, CompilerVMController
from backend.project import Project
from maker import TargetSourceRecorder
from utils import CommandException
from utils.file_marks import CACHE_DIR, LOG_DIR


def _clear_dir(path: str) -> None:
    """清空目录。

    Windows上刚结束的进程（如上一次测试运行的可执行文件）可能仍短暂持有
    目录句柄，导致rmtree抛出PermissionError；此处重试若干次，
    仍失败时忽略（后续写入会覆盖文件），避免编译偶发失败
    （见开发疑问记录71、94关于偶发失败的分析）。
    """
    for _ in range(10):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
            os.makedirs(path, exist_ok=True)
            return
        except (PermissionError, OSError):
            time.sleep(0.1)
from utils.logger import LOGGER_CONTROLLER, Logger
from utils.task import TaskStack, TaskResultState

import os
import shutil
import subprocess
import sys
import time


class MainController:
    """主控制器类，负责编译流程的整体调度。"""

    def __init__(self, workspace: str, entry_path: str, output_path: str, thread_num: int, kwargs: dict[str, str]) -> None:
        """初始化主控制器对象。
        :param workspace: 工作空间路径。
        :param entry_path: 入口文件路径。
        :param output_path: 输出路径。
        :param thread_num: 线程数。
        :param kwargs: 其他参数。
        """
        self._project: Project = Project(workspace, entry_path, output_path)
        self._thread_num: int = thread_num
        self._controllers: list[Controller] = [EmptyController() for _ in range(thread_num)]
        self._task_stack: TaskStack = TaskStack()
        LOGGER_CONTROLLER.config_workspace(workspace, output_path)
        self._logger: Logger = Logger("Main")
        self._maker: TargetSourceRecorder = TargetSourceRecorder(workspace, output_path)
        self._workspace: str = workspace
        self._entry_path: str = entry_path
        if "clear-cache" in kwargs and kwargs["clear-cache"] == "true":
            _clear_dir(os.path.join(workspace, CACHE_DIR))
        if "clear-output" in kwargs and kwargs["clear-output"] == "true":
            _clear_dir(output_path)
        if "clear-log" in kwargs and kwargs["clear-log"] == "true":
            _clear_dir(os.path.join(workspace, LOG_DIR))

    def run(self) -> None:
        """运行编译流程。"""
        LOGGER_CONTROLLER.open()
        self._logger.info(f"The compiler will run with {self._thread_num} thread{'s' if self._thread_num > 1 else ''}.")
        try:
            entry_path = os.path.abspath(self._entry_path)
            self._task_stack.put(["violac", "parse", entry_path])
            while not self._task_stack.is_finished:
                if self._post_task():
                    break
            self._project.finish()
            self._project.write()
            self._maker.write()
        except CommandException as e:
            sys.stderr.write(str(e))
            exit(1)
        finally:
            for controller in self._controllers:
                controller.join()
            LOGGER_CONTROLLER.close()

    def _post_task(self) -> bool:
        """处理任务队列中的下一个任务，返回所有任务是否已完成。"""
        not_busy: list[int] = self._wait()
        progressed: bool = False
        for i in not_busy:
            result = self._controllers[i].join()
            if result.state != TaskResultState.PASSED:
                self._task_stack.finish_task()
                self._controllers[i] = EmptyController()
            if result.state == TaskResultState.FAILURE:
                self._logger.critical("Critical error occurred. Stop.")
                raise CommandException("")
            if result.state == TaskResultState.DELAYED or result.state == TaskResultState.SUCCESS:
                for task in result.data:
                    self._task_stack.put(task)
            if self._task_stack.is_empty:
                continue
            command = self._task_stack.get()
            progressed = True
            if command[0] == "violac":
                if command[1] == "add-make":
                    self._maker.add_make(command[2])
                    self._task_stack.finish_task()
                else:
                    self._controllers[i] = self._get_controller(command)
                    self._controllers[i].handle(command[1:] + [f"--thread-index={i}"])
            else:
                subprocess.run(command)
                self._task_stack.finish_task()
        if not progressed and not self._task_stack.is_finished:
            # 任务栈为空但仍有任务在执行时，短暂休眠避免忙等
            time.sleep(0.05)
        return self._task_stack.is_finished

    def _get_controller(self, command: list[str]) -> Controller:
        """根据命令创建对应的控制器，每个任务使用独立的控制器实例。"""
        if command[1] == "lex":
            return LexerController(self._workspace)
        elif command[1] == "parse":
            return GlobalParserController(self._workspace)
        elif command[1] == "parse-expr":
            return ExprParserController(self._workspace)
        elif command[1] == "run-vm":
            return CompilerVMController(self._project)
        else:
            raise CommandException("Invalid command")

    def _wait(self) -> list[int]:
        """等待至少一个控制器空闲，返回所有空闲控制器的索引。"""
        not_busy: list[int] = []
        while len(not_busy) == 0:
            if len(self._controllers) == 0:
                return [0]
            for i, controller in enumerate(self._controllers):
                if not controller.is_busy:
                    not_busy.append(i)
            if len(not_busy) == 0:
                time.sleep(0.1)
        return not_busy
