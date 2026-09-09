# -*- coding: utf-8 -*-
from utils import SourceInfo

from abc import ABC, abstractmethod
from typing import Optional


class CompilingItem(ABC):

    def __str__(self) -> str:
        return self._src_info.src_text

    def __init__(self, src_info: SourceInfo) -> None:
        """
        初始化编译时对象。
        :param src_info: 源代码信息。
        """
        self._src_info: SourceInfo = src_info.copy()
        self._parent_item: Optional[CompilingItem] = None

    def __deepcopy__(self, memo: dict) -> "CompilingItem":
        """自定义深拷贝：不跟随_parent_item父级链。

        表达式通过_parent_item引用其父级（调用方CallOp、语句等），
        父链最终可达整个源文件（全部定义与符号）；若深拷贝跟随该链，
        泛型实例化的deepcopy会把整个模块重复复制（实测上亿次调用）。
        父级引用与copy.copy的浅拷贝语义一致，直接共享。
        """
        from copy import deepcopy
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "_parent_item":
                setattr(result, k, v)
            else:
                setattr(result, k, deepcopy(v, memo))
        return result

    def bind_parent(self, parent_item: "CompilingItem") -> None:
        """
        绑定父级编译时对象。
        :param parent_item: 父级编译时对象。
        """
        self._parent_item = parent_item

    @abstractmethod
    def optimize(self) -> "CompilingItem":
        """
        优化编译时对象。
        :return: 优化后的编译时对象。
        """
        pass

    @property
    def src_info(self) -> SourceInfo:
        """
        获取源代码信息。
        :return: 源代码信息。
        """
        return self._src_info
