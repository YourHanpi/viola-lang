# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .definition import Definition, GlobalDef, FromImportDef
from .statement import CStmt
from .symbol import NamespaceName, TypeName, ArrayTypeName, SymbolTable, StringTypeName, VariableStateTable
from utils import SourceInfo, InternalCompilerException, COMPILER_PARAMS, VIOLA_INIT

import os
from typing import Optional


class SourceFile(CompilingItem):

    def __init__(self, source_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 src_path: str, dst_path: str, namespace: list[NamespaceName]) -> None:
        super().__init__(source_info)
        self._src_path = src_path
        self._dst_code_path = dst_path + ".c"
        self._dst_header_path = dst_path + ".h"
        self._definitions: list[Definition] = []
        self._instances: list[Definition] = []
        self._global_stmt: list[CStmt] = []
        self._namespace: list[NamespaceName] = namespace
        self._is_finished: bool = False
        self._symbol_table: SymbolTable = symbol_table
        self._var_states: VariableStateTable = var_states

    def add_def(self, definition: Definition) -> None:
        self._definitions.append(definition)
        if definition.global_init_text is not None:
            global_stmt = CStmt(VIOLA_INIT, self._symbol_table, self._var_states)
            global_stmt.add_text(definition.global_init_text)
            self._global_stmt.append(global_stmt)

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException(f"SourceFile {self._src_path} is already finished", self._src_info)
        global_sq: GlobalDef = GlobalDef(self._src_info, self._symbol_table, self._var_states, self._namespace)
        for stmt in self._global_stmt:
            global_sq.add_stmt(stmt)
        global_sq.finish()
        self._definitions.insert(0, global_sq)
        self._initialize_all_symbols()
        self.optimize()
        self._is_finished = True

    def get_main_func(self) -> Definition:
        results = list(filter(lambda x: x.is_main, self._definitions))
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise InternalCompilerException(f"SourceFile {self._src_path} has no main function", self._src_info)
        else:
            raise InternalCompilerException(f"SourceFile {self._src_path} has more than one main function", self._src_info)

    def optimize(self) -> "SourceFile":
        for i, d in enumerate(self._definitions):
            self._definitions[i] = d.optimize()
        for i, d in enumerate(self._instances):
            self._instances[i] = d.optimize()
        return self

    @property
    def src_path(self) -> str:
        return self._src_path

    def write(self) -> None:
        if not self._is_finished:
            raise InternalCompilerException(f"SourceFile {self._src_path} is not finished", self._src_info)
        instance_sources: list[str] = list(map(lambda x: x.source, self._instances))
        outer_texts: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._definitions)))
        sources: list[str] = instance_sources + list(map(lambda x: x.source, self._definitions))
        headers: list[str] = list(map(lambda x: x.header, self._definitions))
        with open(self._dst_code_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write(f"#define _VIOLA_IMPORT_{'$'.join(map(lambda x: x.name, self._namespace))}$__all__\n")
            f.write(f"#include \"{os.path.basename(self._dst_header_path)}\"\n\n")
            f.write("\n".join(outer_texts) + "\n")
            f.write("\n\n".join(sources))
        with open(self._dst_header_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write("\n\n".join(headers))

    def _initialize_all_symbols(self) -> None:
        generics: list[Definition] = list(filter(lambda x: x.is_generic, self._definitions))
        for g in generics:
            self._instances.extend(g.instantiation_full_all())


class ImportDef(FromImportDef):

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, root_path: str, module_path: str) -> None:
        super().__init__(src_info, symbol_table, root_path, module_path, ["__module__"])

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def source(self) -> str:
        return f"// import {self._module_path}"


class _MainFile:

    def __init__(self, src_info: SourceInfo, output_path: str) -> None:
        self._src_info: SourceInfo = src_info
        self._dst_path: str = os.path.join(output_path, "__main__.c")
        self._global_calls: list[str] = []
        self._entry_call: str = ""
        self._entry_include: str = ""
        self._text: str = ""

    def add_global_call(self, namespace: list[NamespaceName]) -> None:
        call_name: str = "$".join(list(map(lambda x: x.name, namespace))) + "$__global__();"
        self._global_calls.append(call_name)

    def finish(self) -> None:
        if self._entry_call == "":
            raise InternalCompilerException("Entry point is not set", self._src_info)
        # noinspection PyTypeChecker
        argv_array_type: TypeName = ArrayTypeName(self._src_info, StringTypeName)
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
        self._text = f"{self._entry_include}\n\nint main(int argc, char **argv) {{\n{text}\n}}"

    def set_entry(self, namespace: list[NamespaceName]) -> None:
        entry = "$".join(list(map(lambda x: x.name, namespace)))
        call_name: str = entry + "$main_0(argvArray);"
        self._entry_call = call_name
        self._entry_include = f"#define _VIOLA_IMPORT_{entry}$main\n#include \"{entry}.vla.h\""

    def write(self) -> None:
        if self._text == "":
            raise InternalCompilerException("Main file is not finished", self._src_info)
        with open(self._dst_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write(self._text)


class Project:

    def __init__(self, root_path: str, entry_path: str, output_path: str) -> None:
        self._root_path: str = os.path.abspath(root_path)
        self._output_path: str = os.path.abspath(output_path)
        self._source_files: dict[str, SourceFile] = {}
        self._src_info: SourceInfo = VIOLA_INIT
        self._entry_path: str = os.path.abspath(entry_path)
        self._entry_namespace: list[NamespaceName] = self._get_namespace(entry_path)
        self._main_file: _MainFile = _MainFile(self._src_info, output_path)
        self._main_file.set_entry(self._entry_namespace)

    def add_source_file(self, source_file: SourceFile) -> None:
        if source_file.src_path in self._source_files:
            raise InternalCompilerException(f"SourceFile {source_file.src_path} is already added", self._src_info)
        self._source_files[source_file.src_path] = source_file
        self._main_file.add_global_call(self._get_namespace(source_file.src_path))

    def finish(self) -> None:
        self._main_file.finish()

    @property
    def output_path(self) -> str:
        return self._output_path

    @property
    def root_path(self) -> str:
        return self._root_path

    def write(self) -> None:
        self._main_file.write()

    def _get_namespace(self, src_path: str) -> list[NamespaceName]:
        return list(map(lambda x: NamespaceName(x), os.path.relpath(src_path[:-4], self._root_path).split(os.sep)))
