# -*- coding: utf-8 -*-
import tomllib


_SingleItemType = str | int | float | bool
ItemType = _SingleItemType | list[_SingleItemType] | dict[str, _SingleItemType]


class CompilerParams:
    """编译器参数配置类，提供参数读取与默认值。"""

    def __getitem__(self, key: str) -> ItemType:
        """获取指定键对应的参数值。"""
        return self._params[key]

    def __init__(self, param_path: str = "") -> None:
        """
        初始化CompilerParams。
        :param param_path: 参数文件路径，为空则使用默认参数。
        """
        self._params: dict[str, ItemType] = CompilerParams._get_default()
        if param_path == "":
            return
        with open(param_path, "rb") as f:
            self._params.update(tomllib.load(f)["compiling"])

    @staticmethod
    def _get_default() -> dict[str, ItemType]:
        """获取默认编译器参数字典。"""
        return {
            "cCompile-exec": "gcc",
            "cCompile-flags": ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2"],
            "debug-memory-accessViolation": True,
            "debug-type-dynamicCheck": True,
            "encoding": "utf-8",
            "log-encoding": "utf-8",
            "runtime-argvEncoding": "utf-8",
            "runtime-stringChunkSize": 4096
        }


COMPILER_PARAMS: CompilerParams = CompilerParams()
