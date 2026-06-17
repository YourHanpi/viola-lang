# -*- coding: utf-8 -*-
from utils import COMPILER_PARAMS, SourceInfo
from utils.file_marks import COMMAND_POSTFIX, GLOBAL_COMMAND_POSTFIX, SYMBOL_TABLE_POSTFIX, EXPR_TOKENS_POSTFIX

from abc import ABC, abstractmethod
import os
from typing import Optional


class Token:
    """
    词法记号类，包含文本、类型列表和起始列号。
    """

    def __init__(self, text: str, token_type: list[str], start_col: int = -1) -> None:
        """
        初始化词法记号对象。
        :param text: 记号文本。
        :param token_type: 记号类型列表。
        :param start_col: 起始列号。
        """
        self._text: str = text
        self._type: list[str] = token_type
        self._start_col: int = start_col

    @property
    def start_col(self) -> int:
        """
        获取起始列号。
        """
        return self._start_col

    @property
    def text(self) -> str:
        """
        获取记号文本。
        """
        return self._text

    @property
    def type(self) -> list[str]:
        """
        获取记号类型列表。
        """
        return self._type


class StateNode:
    """
    有限状态机中的状态结点，包含状态转移表和输出。
    """

    def __init__(self) -> None:
        """
        初始化状态结点。
        """
        self._output: Optional[str] = None
        self._transfers: dict[str, "StateNode"] = {}

    def add_transfer(self, token_type: str, next_state: "StateNode") -> None:
        """
        添加状态转移。
        :param token_type: 触发的记号类型。
        :param next_state: 下一状态结点。
        """
        self._transfers[token_type] = next_state

    @property
    def output(self) -> Optional[str]:
        """
        获取状态输出。
        """
        return self._output

    def set_output(self, output: str) -> None:
        """
        设置状态输出。
        :param output: 输出字符串。
        """
        self._output = output

    def transfer(self, token: Token) -> Optional["StateNode"]:
        """
        根据记号进行状态转移。
        :param token: 输入记号。
        :return: 转移后的状态结点，若无匹配则返回None。
        """
        for t in token.type:
            if t in self._transfers:
                return self._transfers[t]
        return None


class FSM(ABC):
    """
    有限状态机基类，提供状态转移和重置功能。
    """

    def __init__(self) -> None:
        """
        初始化有限状态机。
        """
        self._start: StateNode = self._set_states_list()
        self._current: StateNode = self._start

    @property
    def output(self) -> Optional[str]:
        """
        获取当前状态的输出。
        """
        return self._current.output

    def reset(self) -> None:
        """
        重置状态机到起始状态。
        """
        self._current = self._start

    def transfer(self, token: Token) -> Optional[StateNode]:
        """
        根据记号进行状态转移。
        :param token: 输入记号。
        :return: 转移后的状态结点。
        """
        return self._current.transfer(token)

    @abstractmethod
    def _set_states_list(self) -> StateNode:
        """
        设置状态列表（抽象方法，由子类实现）。
        :return: 起始状态结点。
        """
        pass


class ParserGenericTable:
    """
    泛型参数表，记录类型名称与其泛型参数数量的映射关系。
    """

    def __contains__(self, item: str) -> bool:
        return item in self._table

    def __init__(self) -> None:
        """
        初始化泛型参数表。
        """
        self._table: dict[str, int] = {}

    def add(self, name: str, params_num: int) -> None:
        """
        添加泛型类型及其参数数量。
        :param name: 类型名称。
        :param params_num: 泛型参数数量。
        """
        self._table[name] = params_num

    def dump(self) -> str:
        """
        序列化泛型参数表为字符串。
        """
        return "\n".join(f"{name} {params_num}" for name, params_num in self._table.items())

    def get_params_num(self, name: str) -> int:
        """
        获取指定类型的泛型参数数量。
        :param name: 类型名称。
        """
        return self._table[name]

    @classmethod
    def load(cls, data: str) -> "ParserGenericTable":
        """
        从字符串加载泛型参数表。
        :param data: 序列化后的数据字符串。
        """
        self = cls()
        for line in data.split("\n"):
            name, params_num = line.split()
            self.add(name, int(params_num))
        return self


class ParsingSlice(str):
    """
    解析切片类，表示一段待解析的表达式及其源代码信息。
    """

    def __init__(self, src_info: SourceInfo, token_list: list[Token], index: int) -> None:
        """
        初始化解析切片。
        :param src_info: 源代码信息。
        :param token_list: 记号列表。
        :param index: 切片索引。
        """
        self._src_info: SourceInfo = src_info.copy()
        self._tokens: list[Token] = token_list
        self._index: int = index

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._src_info}, {self._tokens}, {self._index})"

    def __str__(self) -> str:
        return f"RAW {self._index}"

    @property
    def src_info(self) -> SourceInfo:
        """
        获取源代码信息。
        """
        return self._src_info

    @property
    def tokens(self) -> list[Token]:
        """
        获取记号列表。
        """
        return self._tokens


class TokenStreamIO:
    """
    记号流IO类，提供记号的二进制序列化与反序列化。
    """
    # noinspection PyTypeChecker
    _ENCODING: str = COMPILER_PARAMS["encoding"]

    @staticmethod
    def read(path: str) -> list[Token]:
        """
        从文件读取记号列表。
        :param path: 文件路径。
        :return: 记号列表。
        """
        with open(path, "rb") as f:
            return TokenStreamIO._load_token_list_bytes(f.read())

    @staticmethod
    def read_lists(path: str) -> list[list[Token]]:
        """
        从文件读取多层记号列表。
        :param path: 文件路径。
        :return: 多层记号列表。
        """
        with open(path, "rb") as f:
            return TokenStreamIO._load_token_lists(f.read())

    @staticmethod
    def write(path: str, tokens: list[Token]) -> None:
        """
        将记号列表写入文件。
        :param path: 文件路径。
        :param tokens: 记号列表。
        """
        with open(path, "wb") as f:
            f.write(TokenStreamIO._dump_token_list_bytes(tokens))

    @staticmethod
    def write_lists(path: str, token_lists: list[list[Token]]) -> None:
        """
        将多层记号列表写入文件。
        :param path: 文件路径。
        :param token_lists: 多层记号列表。
        """
        with open(path, "wb") as f:
            f.write(TokenStreamIO._dump_token_lists(token_lists))

    @staticmethod
    def _dump_single_token_bytes(token: Token) -> bytes:
        """
        将单个记号序列化为字节。
        :param token: 记号对象。
        :return: 字节数据。
        """
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
        """
        将记号列表序列化为字节。
        :param tokens: 记号列表。
        :return: 字节数据。
        """
        text: bytes = b"VLAt" + len(tokens).to_bytes(4, "little")
        for token in tokens:
            text += TokenStreamIO._dump_single_token_bytes(token)
        return text

    @staticmethod
    def _dump_token_lists(tokens: list[list[Token]]) -> bytes:
        """
        将多层记号列表序列化为字节。
        :param tokens: 多层记号列表。
        :return: 字节数据。
        """
        data: list[bytes] = [TokenStreamIO._dump_token_list_bytes(token) for token in tokens]
        pos_list: list[int] = [0] + [sum(map(len, data[:i])) for i in range(1, len(data))]
        header: bytes = b"VLAe" + len(pos_list).to_bytes(4, "little")
        pos_buffers: bytes = b"".join([pos.to_bytes(4, "little") for pos in pos_list])
        return header + pos_buffers + b"".join(data)

    @staticmethod
    def _load_single_token_bytes(buffer: bytes) -> tuple[Token, bytes]:
        """
        从字节数据加载单个记号。
        :param buffer: 字节数据缓冲区。
        :return: 记号对象及剩余字节数据。
        """
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
        """
        从字节数据加载记号列表。
        :param buffer: 字节数据缓冲区。
        :return: 记号列表。
        """
        tokens: list[Token] = []
        buffer = buffer[4:]
        token_count: int = int.from_bytes(buffer[:4], "little")
        buffer = buffer[4:]
        for _ in range(token_count):
            token, buffer = TokenStreamIO._load_single_token_bytes(buffer)
            tokens.append(token)
        return tokens

    @staticmethod
    def _load_token_lists(buffer: bytes) -> list[list[Token]]:
        """
        从字节数据加载多层记号列表。
        :param buffer: 字节数据缓冲区。
        :return: 多层记号列表。
        """
        pos_count: int = int.from_bytes(buffer[4:8], "little")
        buffer = buffer[8:]
        pos_list: list[int] = [int.from_bytes(buffer[:4], "little") for _ in range(pos_count)]
        buffer = buffer[pos_count * 4:]
        data_list: list[bytes] = [buffer[pos:pos_list[i + 1]] for i, pos in enumerate(pos_list[:-1])] + [buffer[pos_list[-1]:]]
        return [TokenStreamIO._load_token_list_bytes(data) for data in data_list]


class ParsingResult:
    """
    解析结果类，包含命令、符号表、表达式记号以及来源标记。
    """

    def __init__(self, command: list[str], symbol: list[str], expr_tokens: list[list[Token]], from_global_parser: bool) -> None:
        """
        初始化解析结果对象。
        :param command: 命令列表。
        :param symbol: 符号列表。
        :param expr_tokens: 表达式记号列表。
        :param from_global_parser: 是否来自全局解析器。
        """
        self._command: list[str] = command
        self._symbol: list[str] = symbol
        self._expr_tokens: list[list[Token]] = expr_tokens
        self._from_global_parser: bool = from_global_parser

    @property
    def command(self) -> list[str]:
        """
        获取命令列表。
        """
        return self._command

    @property
    def expr_tokens(self) -> list[list[Token]]:
        """
        获取表达式记号列表。
        """
        return self._expr_tokens

    @classmethod
    def read(cls, path: str) -> "ParsingResult":
        """
        从文件中读取解析结果。
        :param path: 文件路径（不含后缀）。
        :return: 解析结果对象。
        """
        if os.path.exists(path + COMMAND_POSTFIX):
            with open(path + COMMAND_POSTFIX, "r") as f:
                command = f.readlines()
            from_global_parser = False
        else:
            with open(path + GLOBAL_COMMAND_POSTFIX, "r") as f:
                command = f.readlines()
            from_global_parser = True
        with open(path + SYMBOL_TABLE_POSTFIX, "r") as f:
            symbol = f.readlines()
        if from_global_parser:
            expr_tokens = TokenStreamIO.read_lists(path + EXPR_TOKENS_POSTFIX)
        else:
            expr_tokens = []
        return cls(command, symbol, expr_tokens, from_global_parser)

    @property
    def symbol(self) -> list[str]:
        """
        获取符号列表。
        """
        return self._symbol

    def write(self, path: str) -> None:
        """
        将解析结果写入文件。
        :param path: 文件路径（不含后缀）。
        """
        with open(path + (GLOBAL_COMMAND_POSTFIX if self._from_global_parser else COMMAND_POSTFIX), "w") as f:
            for cmd in self._command:
                f.write(str(cmd) if not isinstance(cmd, str) else cmd)
                if not (isinstance(cmd, str) and cmd.endswith('\n')):
                    f.write('\n')
        with open(path + SYMBOL_TABLE_POSTFIX, "w") as f:
            f.write(path + "\n")
            f.write(os.path.dirname(path) + "\n")
            f.write("---\n")
            for sym in self._symbol:
                s = str(sym) if not isinstance(sym, str) else sym
                f.write(s)
                if not s.endswith('\n'):
                    f.write('\n')
        if self._from_global_parser:
            TokenStreamIO.write_lists(path + EXPR_TOKENS_POSTFIX, self._expr_tokens)
