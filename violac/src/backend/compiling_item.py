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
