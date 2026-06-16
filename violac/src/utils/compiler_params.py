# -*- coding: utf-8 -*-
import tomllib


_SingleItemType = str | int | float | bool
ItemType = _SingleItemType | list[_SingleItemType] | dict[str, _SingleItemType]


class CompilerParams:

    def __getitem__(self, key: str) -> ItemType:
        return self._params[key]

    def __init__(self, param_path: str = "") -> None:
        self._params: dict[str, ItemType] = CompilerParams._get_default()
        if param_path == "":
            return
        with open(param_path, "rb") as f:
            self._params.update(tomllib.load(f)["compiling"])

    @staticmethod
    def _get_default() -> dict[str, ItemType]:
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
