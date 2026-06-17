# -*- coding: utf-8 -*-
from utils import COMPILER_PARAMS
from utils.file_marks import MAKE_CONFIG_POSTFIX


class TargetSourceRecorder:
    """目标源码记录器，记录编译目标和编译标志，生成配置文件。"""
    _ENCODING: str = COMPILER_PARAMS["encoding"]

    def __init__(self, target_dir: str, output_path: str) -> None:
        """
        初始化TargetSourceRecorder。
        :param target_dir: 目标目录。
        :param output_path: 输出路径。
        """
        self._target_dir: str = target_dir
        self._make_targets: list[tuple[str, str]] = []
        self._compile_flags: list[str] = []
        self._output_path: str = output_path + MAKE_CONFIG_POSTFIX

    def add_make(self, target_path: str) -> None:
        """添加一个编译目标及其对应的目标文件路径。"""
        self._make_targets.append((target_path, target_path + ".o"))

    def set_compile_flags(self, flags: list[str]) -> None:
        """设置编译标志。"""
        self._compile_flags = flags

    def write(self) -> None:
        """将编译配置写入目标目录中的配置文件。"""
        make_targets: list[str] = [f"[[object_path]]\n\"{target_path}\" = \"{object_path}\"\n" for target_path, object_path in self._make_targets]
        flags: str = "flags = [\"" + "\", \"".join(self._compile_flags) + "\"]"
        output_path: str = f"output = \"{self._output_path}\""
        lines: list[str] = [flags, "", output_path, ""] + make_targets
        with open(self._target_dir + MAKE_CONFIG_POSTFIX, "w", encoding=self._ENCODING) as f:
            f.writelines(lines)
