# -*- coding: utf-8 -*-
from utils import CommandException

from abc import ABC, abstractmethod


class Controller(ABC):

    def __init__(self, matching_command: list[str]) -> None:
        self._matching_command = matching_command

    @abstractmethod
    def handle(self, command: list[str]) -> None:
        pass

    @abstractmethod
    def join(self) -> None:
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

    def handle(self, command: list[str]) -> None:
        if command[0] in self._matching_command:
            self._handle(*self._get_params(command[1:]))

    @abstractmethod
    def _handle(self, args: list[str], kwargs: dict[str, str]) -> None:
        pass


class GroupController(Controller):

    def __init__(self, controllers: list[Controller]) -> None:
        super().__init__(sum([controller._matching_command for controller in controllers], []))
        self._controllers: list[Controller] = controllers

    def handle(self, command: list[str]) -> None:
        for controller in self._controllers:
            if command[0] in controller._matching_command:
                controller.handle(command)
                return
        raise CommandException(f"Command {command[0]} not found, use \"viola help\" to see available commands")

    def join(self) -> None:
        for controller in self._controllers:
            controller.join()
