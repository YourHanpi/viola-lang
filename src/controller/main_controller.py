# -*- coding: utf-8 -*-
from .controller import Controller
from .single_controllers import LexerController, GlobalParserController, ExprParserController, CompilerVMController
from backend.project import Project
from utils import CommandException
from utils.logger import LOGGER_CONTROLLER, Logger
from utils.task import TaskStack, TaskResultState

from copy import copy
import subprocess
import time


class MainController:

    def __init__(self, workspace: str, entry_path: str, output_path: str, thread_num: int) -> None:
        project: Project = Project(workspace, entry_path, output_path)
        self._lexer_controller: LexerController = LexerController(workspace)
        self._parser_controller: GlobalParserController = GlobalParserController(workspace)
        self._expr_parser_controller: ExprParserController = ExprParserController(workspace)
        self._compiler_vm_controller: CompilerVMController = CompilerVMController(project)
        self._thread_num: int = thread_num
        self._controllers: list[Controller] = []
        self._task_stack: TaskStack = TaskStack()
        LOGGER_CONTROLLER.config_workspace(workspace)
        self._logger: Logger = Logger("Main")

    def run(self) -> None:
        LOGGER_CONTROLLER.open()
        try:
            while not self._task_stack.is_finished:
                self._post_task()
        except CommandException:
            exit(1)

    def _post_task(self) -> None:
        not_busy: list[int] = self._wait()
        for i in not_busy:
            self._task_stack.finish_task()
            result = self._controllers[i].join()
            if result.state == TaskResultState.FAILURE:
                self._logger.critical("Critical error occurred. Stop.")
                raise CommandException("")
            if self._task_stack.is_empty:
                break
            command = self._task_stack.get()
            if command[0] == "violac":
                if command[1] == "lexer":
                    self._controllers[i] = copy(self._lexer_controller)
                elif command[1] == "parser":
                    self._controllers[i] = copy(self._parser_controller)
                elif command[1] == "expr_parser":
                    self._controllers[i] = copy(self._expr_parser_controller)
                elif command[1] == "compiler_vm":
                    self._controllers[i] = copy(self._compiler_vm_controller)
                else:
                    raise CommandException("Invalid command")
                self._controllers[i].handle(command[1:])
            else:
                subprocess.run(command)

    def _wait(self) -> list[int]:
        not_busy: list[int] = []
        while len(not_busy) == 0:
            time.sleep(0.1)
            for i, controller in enumerate(self._controllers):
                if not controller.is_busy:
                    not_busy.append(i)
        return not_busy
