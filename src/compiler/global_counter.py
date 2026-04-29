# -*- coding: utf-8 -*-
class GlobalCounter:

    def __init__(self):
        self._src_line_count: int = 0
        self._dst_line_count: int = 0
        self._src_path: str = ""
        self._dst_path: str = ""

    def add_dst_line_count(self) -> None:
        self._dst_line_count += 1

    def add_src_line_count(self) -> None:
        self._src_line_count += 1

    @property
    def dst_line_count(self) -> int:
        return self._dst_line_count

    @property
    def dst_path(self) -> str:
        return self._dst_path

    def set_dst_path(self, path: str) -> None:
        self._dst_path = path
        self._dst_line_count = 0

    def set_src_path(self, path: str) -> None:
        self._src_path = path
        self._src_line_count = 0

    @property
    def src_line_count(self) -> int:
        return self._src_line_count

    @property
    def src_path(self) -> str:
        return self._src_path


GLOBAL_COUNTER: GlobalCounter = GlobalCounter()
