# -*- coding: utf-8 -*-
from utils import COMPILER_PARAMS

from abc import ABC, abstractmethod
from typing import Optional


class Token:

    def __init__(self, text: str, token_type: list[str], start_col: int = -1) -> None:
        self._text: str = text
        self._type: list[str] = token_type
        self._start_col: int = start_col

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


class TokenStreamIO:
    # noinspection PyTypeChecker
    _ENCODING: str = COMPILER_PARAMS["encoding"]

    @staticmethod
    def read(path: str) -> list[Token]:
        with open(path, "rb") as f:
            return TokenStreamIO._load_token_list_bytes(f.read())

    @staticmethod
    def write(path: str, tokens: list[Token]) -> None:
        with open(path, "wb") as f:
            f.write(TokenStreamIO._dump_token_list_bytes(tokens))

    @staticmethod
    def _dump_single_token_bytes(token: Token) -> bytes:
        text_buffer: bytes = token.text.encode(TokenStreamIO._ENCODING)
        text_length_buffer: bytes = len(text_buffer).to_bytes(4, "little")
        text_head: bytes = b"TEXT"
        text: bytes = text_head + text_length_buffer + text_buffer + b"TYPE" + len(token.type).to_bytes(2, "little")
        for t in token.type:
            type_length_buffer: bytes = len(t).to_bytes(2, "little")
            token_type: bytes = type_length_buffer + t.encode(TokenStreamIO._ENCODING)
            text += token_type
        return text

    @staticmethod
    def _dump_token_list_bytes(tokens: list[Token]) -> bytes:
        text: bytes = b"VLAt" + len(tokens).to_bytes(4, "little")
        for token in tokens:
            text += TokenStreamIO._dump_single_token_bytes(token)
        return text

    @staticmethod
    def _load_single_token_bytes(buffer: bytes) -> tuple[Token, bytes]:
        text_length: int = int.from_bytes(buffer[4:8], "little")
        text_buffer: bytes = buffer[8:8 + text_length]
        text_data: str = text_buffer.decode(TokenStreamIO._ENCODING)
        buffer = buffer[8 + text_length:]
        type_data: list[str] = []
        type_length: int = int.from_bytes(buffer[4:6], "little")
        buffer = buffer[6:]
        for _ in range(type_length):
            type_length: int = int.from_bytes(buffer[:2], "little")
            type_data.append(buffer[2:2 + type_length].decode(TokenStreamIO._ENCODING))
            buffer = buffer[2 + type_length:]
        return Token(text_data, type_data), buffer

    @staticmethod
    def _load_token_list_bytes(buffer: bytes) -> list[Token]:
        tokens: list[Token] = []
        buffer = buffer[4:]
        token_count: int = int.from_bytes(buffer[:4], "little")
        for _ in range(token_count):
            token, buffer = TokenStreamIO._load_single_token_bytes(buffer)
            tokens.append(token)
        return tokens
