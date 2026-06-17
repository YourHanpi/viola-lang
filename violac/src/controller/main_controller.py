# -*- coding: utf-8 -*-
from .controller import Controller, EmptyController
from .single_controllers import LexerController, GlobalParserController, ExprParserController, CompilerVMController
from backend.project import Project
from maker import TargetSourceRecorder
from utils import CommandException
from utils.file_marks import CACHE_DIR
from utils.logger import LOGGER_CONTROLLER, Logger
from utils.task import TaskStack, TaskResultState

from copy import copy
import os
import shutil
import subprocess
import sys
import time


class MainController:

    def __init__(self, workspace: str, entry_path: str, output_path: str, thread_num: int, kwargs: dict[str, str]) -> None:
        self._project: Project = Project(workspace, entry_path, output_path)
        self._lexer_controller: LexerController = LexerController(workspace)
        self._parser_controller: GlobalParserController = GlobalParserController(workspace)
        self._expr_parser_controller: ExprParserController = ExprParserController(workspace)
        self._compiler_vm_controller: CompilerVMController = CompilerVMController(self._project)
        self._thread_num: int = thread_num
        self._controllers: list[Controller] = [EmptyController()] * thread_num
        self._task_stack: TaskStack = TaskStack()
        LOGGER_CONTROLLER.config_workspace(workspace, output_path)
        self._logger: Logger = Logger("Main")
        self._maker: TargetSourceRecorder = TargetSourceRecorder(workspace, output_path)
        self._workspace: str = workspace
        self._entry_path: str = entry_path
        if kwargs["clear-cache"] == "true":
            shutil.rmtree(os.path.join(workspace, CACHE_DIR))
        if kwargs["clear-output"] == "true":
            shutil.rmtree(output_path)
            os.mkdir(output_path)

    def run(self) -> None:
        LOGGER_CONTROLLER.open()
        try:
            entry_path = os.path.join(self._workspace, self._entry_path)
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
        not_busy: list[int] = self._wait()
        not_busy_count: int = len(not_busy)
        for i in not_busy:
            result = self._controllers[i].join()
            if result.state == TaskResultState.FAILURE:
                self._logger.critical("Critical error occurred. Stop.")
                raise CommandException("")
            if result.state == TaskResultState.DELAYED or result.state == TaskResultState.SUCCESS:
                for task in result.data:
                    self._task_stack.put(task)
            if self._task_stack.is_empty:
                break
            command = self._task_stack.get()
            if command[0] == "violac":
                if command[1] == "add-make":
                    self._maker.add_make(command[2])
                else:
                    self._controllers[i] = self._get_controller(command)
                    self._controllers[i].handle(command[1:] + [f"--thread-index={i}"])
                    not_busy_count -= 1
            else:
                subprocess.run(command)
        return not_busy_count >= len(self._controllers) and self._task_stack.is_empty

    def _get_controller(self, command: list[str]) -> Controller:
        if command[1] == "lex":
            return copy(self._lexer_controller)
        elif command[1] == "parse":
            return copy(self._parser_controller)
        elif command[1] == "parse-expr":
            return copy(self._expr_parser_controller)
        elif command[1] == "run-vm":
            return copy(self._compiler_vm_controller)
        else:
            raise CommandException("Invalid command")

    def _wait(self) -> list[int]:
        not_busy: list[int] = []
        while len(not_busy) == 0:
            if len(self._controllers) == 0:
                return [0]
            time.sleep(0.1)
            for i, controller in enumerate(self._controllers):
                if not controller.is_busy:
                    not_busy.append(i)
        return not_busy
