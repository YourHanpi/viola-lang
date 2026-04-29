# -*- coding: utf-8 -*-
from utils import SourceInfo

from abc import ABC
from copy import deepcopy


class CompilingItem(ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        """
        初始化编译时对象。
        :param src_info: 源代码信息。
        """
        self._src_info: SourceInfo = deepcopy(src_info)
