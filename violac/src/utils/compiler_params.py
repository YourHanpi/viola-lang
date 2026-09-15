# -*- coding: utf-8 -*-
"""编译器参数配置。

原先从TOML文件读取参数：TOML解析不是C语言原生的标准库功能，为将来能够自举
（见README_zh.md与versions_dev_plan_zh.md"漏洞修复"）不再使用，改为只提供
内置默认值。若将来需要参数文件，应改为编译期本身可实现的简单格式。
"""


_SingleItemType = str | int | float | bool
ItemType = _SingleItemType | list[_SingleItemType] | dict[str, _SingleItemType]


class CompilerParams:
    """编译器参数配置类，提供参数读取与默认值。"""

    def __getitem__(self, key: str) -> ItemType:
        """获取指定键对应的参数值。"""
        return self._params[key]

    def __init__(self) -> None:
        """初始化CompilerParams（使用内置默认参数）。"""
        self._params: dict[str, ItemType] = CompilerParams._get_default()

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
