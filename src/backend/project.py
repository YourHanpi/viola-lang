# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .definition import Definition, CPartSqDef
from .expression import SYMBOL_TABLE
from .statement import CStmt
from .symbol import NamespaceName, TypeName, ArrayTypeName
from utils import SourceInfo, InternalCompilerException, COMPILER_PARAMS

import os


class SourceFile(CompilingItem):

    def __init__(self, source_info: SourceInfo, src_path: str, namespace: list[NamespaceName]) -> None:
        super().__init__(source_info)
        self._src_path = src_path
        self._dst_code_path = src_path + ".c"
        self._dst_header_path = src_path + ".h"
        self._definitions: list[Definition] = []
        self._global_stmt: list[str] = []
        self._namespace: list[NamespaceName] = namespace
        self._is_finished: bool = False

    def add_definition(self, definition: Definition) -> None:
        self._definitions.append(definition)
        self._global_stmt.append(definition.global_init_text)

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException(f"SourceFile {self._src_path} is already finished", self._src_info)
        global_text: str = "\n".join(self._global_stmt)
        global_stmt: CStmt = CStmt(self._src_info)
        global_stmt.set_text(global_text)
        global_sq: CPartSqDef = CPartSqDef(self._src_info, self._namespace, [], "__global__", [])
        global_sq.add_stmt(global_stmt)
        self._definitions.insert(0, global_sq)
        self._is_finished = True

    def get_main_func(self) -> Definition:
        results = list(filter(lambda x: x.is_main, self._definitions))
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise InternalCompilerException(f"SourceFile {self._src_path} has no main function", self._src_info)
        else:
            raise InternalCompilerException(f"SourceFile {self._src_path} has more than one main function", self._src_info)

    @property
    def src_path(self) -> str:
        return self._src_path

    def write(self) -> None:
        if not self._is_finished:
            raise InternalCompilerException(f"SourceFile {self._src_path} is not finished", self._src_info)
        sources: list[str] = list(map(lambda x: x.source, self._definitions))
        headers: list[str] = list(map(lambda x: x.header, self._definitions))
        with open(self._dst_code_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write("\n\n".join(sources))
        with open(self._dst_header_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write("\n\n".join(headers))


class _MainFile:

    def __init__(self, src_info: SourceInfo, root_path: str) -> None:
        self._src_info: SourceInfo = src_info
        self._dst_path: str = os.path.join(root_path, "__main__.c")
        self._global_calls: list[str] = []
        self._entry_call: str = ""
        self._text: str = ""

    def add_global_call(self, namespace: list[NamespaceName]) -> None:
        call_name: str = "$".join(list(map(lambda x: x.name, namespace))) + "$__global__();"
        self._global_calls.append(call_name)

    def finish(self) -> None:
        if self._entry_call == "":
            raise InternalCompilerException("Entry point is not set", self._src_info)
        # noinspection PyTypeChecker
        argv_array_type: TypeName = ArrayTypeName(self._src_info, SYMBOL_TABLE["string"])
        argv_setting_text: list[str] = [
            f"{argv_array_type.c_calling_name}argvArray = ({argv_array_type.c_calling_name})malloc(sizeof({argv_array_type.c_alloc_name}));",
            "argvArray->refCount = 1;",
            "argvArray->parent = NULL;",
            "argvArray->size = argc;",
            "for (int i = 0; i < argc; i++) {",
            f"\targvArray->data[i] = {argv_array_type.name}$decode(argv[i], {COMPILER_PARAMS['runtime-argvEncoding']});",
            "}"
        ]
        text = "\n".join(argv_setting_text) + "\n" + "\n".join(self._global_calls) + "\n" + self._entry_call + "\nreturn 0;"
        text = "\n".join(list(map(lambda x: f"\t{x}", text.split("\n"))))
        self._text = f"int main(int argc, char **argv) {{\n{text}\n}}"

    def set_entry(self, namespace: list[NamespaceName]) -> None:
        call_name: str = "$".join(list(map(lambda x: x.name, namespace))) + "$main(argvArray);"
        self._entry_call = call_name

    def write(self) -> None:
        if self._text == "":
            raise InternalCompilerException("Main file is not finished", self._src_info)
        with open(self._dst_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write(self._text)


class Project:

    def __init__(self, src_info: SourceInfo, root_path: str, entry_path: str) -> None:
        self._root_path: str = root_path
        self._source_files: dict[str, SourceFile] = {}
        self._src_info: SourceInfo = src_info
        self._entry_path: str = entry_path
        self._entry_namespace: list[NamespaceName] = self._get_namespace(entry_path)
        self._main_file: _MainFile = _MainFile(self._src_info, self._root_path)
        self._main_file.set_entry(self._entry_namespace)

    def add_source_file(self, source_file: SourceFile) -> None:
        if source_file.src_path in self._source_files:
            raise InternalCompilerException(f"SourceFile {source_file.src_path} is already added", self._src_info)
        self._source_files[source_file.src_path] = source_file
        self._main_file.add_global_call(self._get_namespace(source_file.src_path))

    def create_source_file(self, src_path: str) -> SourceFile:
        namespace: list[NamespaceName] = self._get_namespace(src_path)
        source_file: SourceFile = SourceFile(self._src_info, src_path, namespace)
        return source_file

    def finish(self) -> None:
        for k in self._source_files:
            self._source_files[k].finish()
        self._main_file.finish()

    def write(self) -> None:
        for k in self._source_files:
            self._source_files[k].write()
        self._main_file.write()

    def _get_namespace(self, src_path: str) -> list[NamespaceName]:
        return list(map(lambda x: NamespaceName(x), os.path.relpath(src_path, self._root_path).split(os.sep)))
