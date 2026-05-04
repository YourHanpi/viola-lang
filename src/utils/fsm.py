# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional, TypeVar


T = TypeVar("T", "Token", str)


class Token[T = str]:

    def __init__(self, children: str | list[T], token_type: list[str], start_col: int = -1) -> None:
        self._text: str = children if isinstance(children, str) else ""
        self._children: list[T] = [] if isinstance(children, str) else children
        self._type: list[str] = token_type
        self._start_col: int = start_col

    def add_types(self, new_types: list[str]) -> None:
        self._type += new_types

    def append(self, text: T) -> None:
        if T is str:
            self._text += text
        else:
            self._children.append(text)

    @property
    def children(self) -> list[T]:
        return self._children

    @staticmethod
    def concat(tokens: list["Token[T]"], new_types: list[str]) -> "Token[T]":
        if T is not str:
            children = []
            for t in tokens:
                children += t.children
            return Token(children, new_types, tokens[0].start_col)
        children = "".join([t.text for t in tokens])
        return Token(children, new_types, tokens[0].start_col)

    @property
    def start_col(self) -> int:
        return self._start_col

    @property
    def text(self) -> str:
        return self._text

    @property
    def type(self) -> list[str]:
        return self._type


class StateNode:

    def __init__(self) -> None:
        self._output: Optional[str] = None
        self._transfers: dict[str, "StateNode"] = {}

    def add_transfer(self, token_type: str, next_state: "StateNode") -> None:
        self._transfers[token_type] = next_state

    @property
    def output(self) -> Optional[str]:
        return self._output

    def set_output(self, output: str) -> None:
        self._output = output

    def transfer(self, token: Token) -> Optional["StateNode"]:
        for t in token.type:
            if t in self._transfers:
                return self._transfers[t]
        return None


class FSM(ABC):

    def __init__(self) -> None:
        self._start: StateNode = self._set_states_list()
        self._current: StateNode = self._start

    @property
    def output(self) -> Optional[str]:
        return self._current.output

    def reset(self) -> None:
        self._current = self._start

    def transfer(self, token: Token) -> Optional[StateNode]:
        return self._current.transfer(token)

    @abstractmethod
    def _set_states_list(self) -> StateNode:
        pass
