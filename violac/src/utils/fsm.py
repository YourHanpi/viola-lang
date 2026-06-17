# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional


class Token:
    """表示词法分析中的令牌，包含文本内容、类型及起始列信息。"""

    def __init__(self, children: str | list[str], token_type: list[str], start_col: int = -1) -> None:
        """
        初始化Token。
        :param children: 令牌内容，字符串或子令牌列表。
        :param token_type: 令牌类型列表。
        :param start_col: 起始列号。
        """
        self._text: str = children if isinstance(children, str) else ""
        self._children: list[str] = [] if isinstance(children, str) else children
        self._type: list[str] = token_type
        self._start_col: int = start_col

    def add_types(self, new_types: list[str]) -> None:
        """为令牌添加新的类型标签。"""
        self._type += new_types

    def append(self, text: str) -> None:
        """向令牌追加文本内容。"""
        if str is str:
            self._text += text
        else:
            self._children.append(text)

    @property
    def children(self) -> list[str]:
        return self._children

    @staticmethod
    def concat(tokens: list["Token"], new_types: list[str]) -> "Token":
        """合并多个令牌为一个新令牌，并指定新类型。"""
        if str is not str:
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
    
    def set_types(self, new_types: list[str]) -> None:
        """设置令牌的类型标签。"""
        self._type = new_types

    @property
    def type(self) -> list[str]:
        return self._type


class StateNode:
    """有限状态机中的状态节点，支持转移和输出。"""

    def __init__(self) -> None:
        """
        初始化StateNode。
        初始状态下无输出，转移表为空。
        """
        self._output: Optional[str] = None
        self._transfers: dict[str, "StateNode"] = {}

    def add_transfer(self, token_type: str, next_state: "StateNode") -> None:
        """添加基于令牌类型的状态转移规则。"""
        self._transfers[token_type] = next_state

    @property
    def output(self) -> Optional[str]:
        return self._output

    def set_output(self, output: str) -> None:
        """设置当前状态的输出内容。"""
        self._output = output

    def transfer(self, token: Token) -> Optional["StateNode"]:
        """根据令牌类型进行状态转移，若无匹配则返回None。"""
        for t in token.type:
            if t in self._transfers:
                return self._transfers[t]
        return None


class FSM(ABC):
    """有限状态机抽象基类，定义状态机的初始化、重置与转移接口。"""

    def __init__(self) -> None:
        """
        初始化FSM。
        调用子类实现的_set_states_list构建状态图，并将当前状态设为起始状态。
        """
        self._start: StateNode = self._set_states_list()
        self._current: StateNode = self._start

    @property
    def output(self) -> Optional[str]:
        return self._current.output

    def reset(self) -> None:
        """将状态机重置为起始状态。"""
        self._current = self._start

    def transfer(self, token: Token) -> Optional[StateNode]:
        """将令牌传入当前状态进行转移，返回下一状态或None。"""
        return self._current.transfer(token)

    @abstractmethod
    def _set_states_list(self) -> StateNode:
        """构建状态机的状态图（抽象方法，由子类实现）。"""
        pass
