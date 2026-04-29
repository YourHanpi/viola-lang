# -*- coding: utf-8 -*-
from typing import Optional


class SourceInfo:
    """
    源代码信息。
    """

    def __init__(self, src_file_name: str) -> None:
        """
        初始化源代码信息对象。
        :param src_file_name: 源文件路径。
        """
        self._src_text: str = ""
        self._src_file_name: str = src_file_name
        self._start_line: int = 0
        self._start_col: int = 0
        self._end_line: int = 0
        self._end_col: int = 0

    @property
    def lineno(self) -> int:
        """
        获取源代码行数。
        """
        return self._start_line

    @property
    def path(self) -> str:
        """
        获取源代码文件路径。
        """
        return self._src_file_name

    def set_loc(self, start_line: Optional[int], start_col: Optional[int], end_line: Optional[int], end_col: Optional[int]) -> None:
        """
        设置源代码位置。
        :param start_line: 开始行。
        :param start_col: 开始列。
        :param end_line: 结束行。
        :param end_col: 结束列。
        """
        self._start_line = start_line if start_line is not None else self._start_line
        self._start_col = start_col if start_col is not None else self._start_col
        self._end_line = end_line if end_line is not None else self._end_line
        self._end_col = end_col if end_col is not None else self._end_col

    def set_text(self, src_text: str) -> None:
        """
        设置源代码文本。
        :param src_text: 源代码的一行文本。
        """
        self._src_text = src_text

    @property
    def traceback(self) -> str:
        """
        获取回溯信息。
        """
        text: str = self._src_text
        if self._end_line > self._start_line:
            end_col: int = len(text)
        else:
            end_col = self._end_col
        location_mark: str = " " * (self._start_col - 1) + "^" * (end_col - self._start_col) + " " * (len(text) - end_col)
        location: str = f"file {self._src_file_name} line {self._start_line}"
        return f"{text}\n{location_mark}\n\tat {location}"

    @property
    def traceback_no_location(self) -> str:
        """
        获取无位置回溯信息。
        """
        text: str = self._src_text
        if self._end_line > self._start_line:
            end_col: int = len(text)
        else:
            end_col = self._end_col
        location_mark: str = " " * (self._start_col - 1) + "^" * (end_col - self._start_col) + " " * (len(text) - end_col)
        return f"{text}\n{location_mark}"
