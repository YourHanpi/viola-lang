# -*- coding: utf-8 -*-
import tomllib
from typing import Optional


ItemType = str | int | float | bool


class CompilerParams:

    def __getitem__(self, key: str) -> ItemType:
        return self._params[key]

    def __init__(self, param_path: str) -> None:
        self._params: dict[str, ItemType] = CompilerParams._get_default()
        with open(param_path, "rb") as f:
            self._params.update(tomllib.load(f)["compiling"])

    @staticmethod
    def _get_default() -> dict[str, ItemType]:
        return {
            "debug-memory-accessViolation": True,
            "debug-type-dynamicCheck": True,
            "encoding": "utf-8",
            "runtime-argvEncoding": "utf-8",
            "runtime-stringChunkSize": 4096
        }


COMPILER_PARAMS: Optional[CompilerParams] = None
