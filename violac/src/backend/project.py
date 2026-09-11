# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .definition import Definition, GlobalDef, FromImportDef
from .statement import CStmt
from .symbol import NamespaceName, TypeName, ArrayTypeName, SymbolTable, StringTypeName, VariableStateTable, \
    type_def_class_names
from utils import SourceInfo, InternalCompilerException, COMPILER_PARAMS, VIOLA_INIT

import os
from typing import Optional


class SourceFile(CompilingItem):
    """源文件对象，管理一个源文件的所有定义、实例化和代码生成。"""

    def __init__(self, source_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 src_path: str, dst_path: str, namespace: list[NamespaceName]) -> None:
        """
        初始化源文件对象。
        :param source_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param src_path: 源文件路径。
        :param dst_path: 输出文件路径（不含扩展名）。
        :param namespace: 命名空间路径。
        """
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
        # 已实例化的(泛型定义, 类型实参)缓存（refresh_generic_instances的不动点迭代去重）。
        # 键使用类型实参的名称元组而非对象身份：类型查找可能重建等价类型对象
        # （如数组类型按C名重建），按身份比较会导致缓存永不命中
        self._refreshed_instances: set[tuple[int, tuple[str, ...]]] = set()

    def add_def(self, definition: Definition) -> None:
        """向源文件中添加一个定义。"""
        self._definitions.append(definition)
        # 收集定义的全局初始化文本（虚函数表、静态属性、常量等），
        # 供finish生成模块的__global__函数
        if definition.global_init_text is not None and definition.global_init_text != "":
            # 去重：优化后的语句可能重复产生相同的全局初始化文本（如调试标记）
            for stmt in self._global_stmt:
                if stmt.text == definition.global_init_text:
                    break
            else:
                global_stmt = CStmt(VIOLA_INIT, self._symbol_table, self._var_states)
                global_stmt.add_text(definition.global_init_text)
                self._global_stmt.append(global_stmt)

    @property
    def definitions(self) -> list[Definition]:
        """获取源文件的所有定义。"""
        return self._definitions

    def finish(self) -> None:
        """完成源文件，生成全局初始化函数并进行泛型实例化。"""
        # 泛型实例化必须先生成，以便实例的全局初始化文本进入__global__函数，
        # 且泛型定义自身的初始化文本被移除
        self._initialize_all_symbols()
        global_sq: GlobalDef = GlobalDef(self._src_info, self._symbol_table, self._var_states, self._namespace)
        for stmt in self._global_stmt:
            global_sq.add_stmt(stmt)
        global_sq.finish()
        self._definitions.insert(0, global_sq)
        self.optimize()
        self._is_finished = True

    def get_main_func(self) -> Definition:
        """获取源文件中的主函数定义。"""
        results = list(filter(lambda x: x.is_main, self._definitions))
        if len(results) == 1:
            return results[0]
        elif len(results) == 0:
            raise InternalCompilerException(f"SourceFile {self._src_path} has no main function", self._src_info)
        else:
            raise InternalCompilerException(f"SourceFile {self._src_path} has more than one main function", self._src_info)

    def optimize(self) -> "SourceFile":
        """优化源文件中的所有定义和实例。"""
        for i, d in enumerate(self._definitions):
            self._definitions[i] = d.optimize()
        for i, d in enumerate(self._instances):
            self._instances[i] = d.optimize()
        return self

    @property
    def src_path(self) -> str:
        """获取源文件路径。"""
        return self._src_path

    def write(self) -> None:
        """将源文件写入磁盘，生成 .c 和 .h 文件。"""
        if not self._is_finished:
            raise InternalCompilerException(f"SourceFile {self._src_path} is not finished", self._src_info)
        instance_sources: list[str] = list(map(lambda x: x.source, self._instances))
        outer_texts: list[str] = list(filter(
            lambda x: x is not None,
            map(lambda x: x.outer_text, self._definitions + self._instances)
        ))
        sources: list[str] = instance_sources + list(map(lambda x: x.source, self._definitions))
        headers: list[str] = list(map(lambda x: x.header, self._definitions + self._instances))
        # 元组与数组类型的结构体定义（带include guard，确定性文本，可安全地出现在所有模块头文件中）
        # 数组在前：元组成员可能引用数组类型
        from .definition import ClassDef
        own_classes: set[str] = {
            d.decl.name for d in self._definitions + self._instances if isinstance(d, ClassDef)
        }
        forward_decls: list[str] = [
            f"typedef struct {name} {name};"
            for name in sorted(own_classes | type_def_class_names())
        ]
        # 依赖顺序：数组 -> 同步函数指针 -> 元组（成员可能引用同步函数指针） -> 异步函数指针（引用元组）
        type_defs: list[str] = forward_decls + SymbolTable.array_type_decl_texts() + \
            SymbolTable.function_type_defs_sync() + SymbolTable.tuple_type_defs() + \
            SymbolTable.function_type_defs_async()
        if not os.path.exists(os.path.dirname(self._dst_code_path)):
            os.makedirs(os.path.dirname(self._dst_code_path), exist_ok=True)
        with open(self._dst_code_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write(f"#define _VIOLA_IMPORT_{'$'.join(map(lambda x: x.name, self._namespace))}$__all__ 1\n")
            f.write(f"#include \"{os.path.basename(self._dst_header_path)}\"\n\n")
            f.write("\n".join(outer_texts) + "\n")
            f.write("\n\n".join(sources))
        with open(self._dst_header_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write("\n\n".join(type_defs + headers))

    def refresh_generic_instances(self) -> bool:
        """合并其他模块发起的泛型实例化请求，补充实例。

        返回本轮是否新增了实例。实例化过程中可能产生新的实例化请求
        （泛型函数体调用其他泛型函数），因此调用方需迭代至不动点。
        已实例化的(泛型定义, 类型实参)对缓存于_refreshed_instances，
        避免不动点迭代的每一轮都重建全部已知实例（实例化包含完整的
        深拷贝与代码生成，代价较高）。
        """
        if not hasattr(self, "_generic_defs"):
            return False
        # 用实例的C函数名去重（SqDef无decl属性，取内部_decl）
        def inst_name(inst: Definition) -> str:
            if hasattr(inst, "decl") and getattr(inst, "decl", None) is not None:
                return inst.decl.name
            return getattr(getattr(inst, "_decl", None), "name", "")
        known: set[str] = {inst_name(inst) for inst in self._instances}
        changed: bool = False
        for g in self._generic_defs:
            decl = getattr(g, "_decl", None) if getattr(g, "_decl", None) is not None else getattr(g, "decl", None)
            type_args_list: list[tuple[TypeName, ...]] = self._symbol_table.get_all_to_instantiate_symbols(
                self._src_info, decl)
            for t in type_args_list:
                cache_key = (id(g), tuple(x.name for x in t))
                if cache_key in self._refreshed_instances:
                    continue
                self._refreshed_instances.add(cache_key)
                if hasattr(g, "instantiation_full"):
                    inst = g.instantiation_full(t)
                else:
                    # 泛型类（ClassDef）：instantiation(t)按类型实参实例化
                    inst = g.instantiation(t)
                name: str = inst_name(inst)
                if name != "" and name in known:
                    continue
                self._instances.append(inst)
                if name != "":
                    known.add(name)
                changed = True
                inst_init: Optional[str] = inst.global_init_text
                if inst_init:
                    inst_stmt = CStmt(VIOLA_INIT, self._symbol_table, self._var_states)
                    inst_stmt.add_text(inst_init)
                    self._global_stmt.append(inst_stmt)
        return changed

    def _initialize_all_symbols(self) -> None:
        """初始化所有泛型符号的实例化。"""
        generics: list[Definition] = list(filter(lambda x: x.is_generic, self._definitions))
        self._generic_defs = generics
        self._definitions = list(filter(lambda x: not x.is_generic, self._definitions))
        for g in generics:
            # 泛型定义自身的全局初始化文本移除（其C定义不会生成），
            # 实例的全局初始化文本在实例化时重新收集
            g_init: Optional[str] = g.global_init_text
            if g_init:
                self._global_stmt = list(filter(lambda s: s._inner_text != g_init, self._global_stmt))
            for inst in g.instantiation_full_all():
                self._instances.append(inst)
                inst_init: Optional[str] = inst.global_init_text
                if inst_init:
                    inst_stmt = CStmt(VIOLA_INIT, self._symbol_table, self._var_states)
                    inst_stmt.add_text(inst_init)
                    self._global_stmt.append(inst_stmt)


class ImportDef(FromImportDef):
    """模块导入定义，封装 import 语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, root_path: str, module_path: str) -> None:
        """
        初始化 import 导入定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param root_path: 项目根路径。
        :param module_path: 模块路径。
        """
        super().__init__(src_info, symbol_table, root_path, module_path, ["__module__"])

    @property
    def outer_text(self) -> Optional[str]:
        """导入定义没有外层代码文本。"""
        return None

    @property
    def source(self) -> str:
        """获取 import 语句的源代码文本。"""
        return f"// import {self._module_path}"


class _MainFile:
    """主入口文件，生成 C 语言的 main 函数。"""

    def __init__(self, src_info: SourceInfo, output_path: str) -> None:
        """
        初始化主入口文件。
        :param src_info: 源代码信息。
        :param output_path: 输出目录路径。
        """
        self._src_info: SourceInfo = src_info
        self._dst_path: str = os.path.join(output_path, "__main__.c")
        self._global_calls: list[str] = []
        self._entry_call: str = ""
        self._entry_include: str = ""
        self._text: str = ""

    def add_global_call(self, namespace: list[NamespaceName]) -> None:
        """添加一个全局初始化函数的调用。"""
        call_name: str = "$".join(list(map(lambda x: x.name, namespace))) + "$__global__(listener);"
        self._global_calls.append(call_name)

    def finish(self) -> None:
        """完成主入口文件的生成，组装 argv 处理、运行库定义和 main 函数体。"""
        if self._entry_call == "":
            raise InternalCompilerException("Entry point is not set", self._src_info)
        # noinspection PyTypeChecker
        argv_array_type: TypeName = ArrayTypeName(self._src_info, StringTypeName)
        argv_setting_text: list[str] = [
            f"{argv_array_type.c_calling_name} argvArray = ({argv_array_type.c_calling_name})malloc(sizeof({argv_array_type.c_alloc_name}));",
            "argvArray->$refCount = 1;",
            "argvArray->$parent = NULL;",
            "argvArray->size = argc;",
            "argvArray->data = (viola$lang$string **)malloc(sizeof(viola$lang$string *) * (argc > 0 ? argc : 1));",
            "for (int i = 0; i < argc; i++) {",
            f"\targvArray->data[i] = {argv_array_type.c_alloc_name}$decode(argv[i], "
            f"\"{COMPILER_PARAMS['runtime-argvEncoding']}\");",
            "}"
        ]
        # 运行库类型定义与数组方法实现（元组/数组按类型生成，仅此一个编译单元）
        # 类型定义可能引用各模块的类，先生成这些类的前置声明
        fwd_decls: list[str] = [
            f"typedef struct {name} {name};" for name in sorted(type_def_class_names())
        ]
        runtime_defs: list[str] = fwd_decls + \
            SymbolTable.array_type_decl_texts() + SymbolTable.function_type_defs_sync() + \
            SymbolTable.tuple_type_defs() + SymbolTable.function_type_defs_async() + \
            SymbolTable.array_type_impl_texts()
        main_body: list[str] = [
            "viola$threads$Listener *listener = (viola$threads$Listener *)malloc(sizeof(viola$threads$Listener));",
            "viola$threads$initListener(listener, 0);",
            *argv_setting_text,
            *self._global_calls,
            self._entry_call,
            "viola$threads$waitListener(listener);",
            "return 0;"
        ]
        text = "\n".join(runtime_defs) + "\n\nint main(int argc, char **argv) {\n" + \
            "\n".join(list(map(lambda x: f"\t{x}", main_body))) + "\n}"
        self._text = f"{self._entry_include}\n\n{text}"

    def set_entry(self, namespace: list[NamespaceName]) -> None:
        """设置程序入口点（main 函数调用）。"""
        entry = "$".join(list(map(lambda x: x.name, namespace)))
        call_name: str = entry + "$main$_0(listener);"
        self._entry_call = call_name
        self._entry_include = f"#define _VIOLA_IMPORT_{entry}$main 1\n#include \"{entry}.vla.h\""

    def write(self) -> None:
        """将主入口文件写入磁盘。"""
        if self._text == "":
            raise InternalCompilerException("Main file is not finished", self._src_info)
        with open(self._dst_path, "w", encoding=COMPILER_PARAMS["encoding"]) as f:
            f.write(self._text)


class Project:
    """项目对象，管理源文件集合、编译输出和主入口文件。"""

    def __init__(self, root_path: str, entry_path: str, output_path: str) -> None:
        """
        初始化项目。
        :param root_path: 项目根路径。
        :param entry_path: 入口文件路径。
        :param output_path: 输出目录路径。
        """
        self._root_path: str = os.path.abspath(root_path)
        self._output_path: str = os.path.abspath(output_path)
        self._source_files: dict[str, SourceFile] = {}
        self._src_info: SourceInfo = VIOLA_INIT
        self._entry_path: str = os.path.abspath(entry_path)
        self._entry_namespace: list[NamespaceName] = self._get_namespace(entry_path)
        self._main_file: _MainFile = _MainFile(self._src_info, output_path)
        self._main_file.set_entry(self._entry_namespace)

    def add_source_file(self, source_file: SourceFile) -> None:
        """添加一个源文件到项目中。

        同一个源文件可能被多个导入方触发重复编译（并发任务竞争），
        重复添加时直接忽略。
        """
        if source_file.src_path in self._source_files:
            return
        self._source_files[source_file.src_path] = source_file
        self._main_file.add_global_call(self._get_namespace(source_file.src_path))

    def finish(self) -> None:
        """完成项目构建，完成主入口文件的生成。"""
        # 全部模块编译完成后，合并各模块发起的泛型实例化请求并重写输出。
        # 实例化可能产生新的实例化请求（泛型函数体调用其他泛型函数，
        # 请求注册可能晚于被调泛型的快照），迭代至不动点后再统一写出。
        for _ in range(64):
            changed: bool = False
            for source_file in self._source_files.values():
                if source_file.refresh_generic_instances():
                    changed = True
            if not changed:
                break
        for source_file in self._source_files.values():
            source_file.write()
        self._main_file.finish()

    @property
    def output_path(self) -> str:
        """获取项目输出路径。"""
        return self._output_path

    @property
    def root_path(self) -> str:
        """获取项目根路径。"""
        return self._root_path

    def write(self) -> None:
        """将所有生成的文件写入磁盘。"""
        self._main_file.write()

    def _get_namespace(self, src_path: str) -> list[NamespaceName]:
        """根据源文件路径获取对应的命名空间列表。"""
        rel: str = os.path.relpath(src_path[:-4], self._root_path)
        if rel.startswith(".."):
            # 工作区之外的模块（如运行库viola_libs）：相对VIOLA_HOME计算命名空间
            if "VIOLA_HOME" in os.environ:
                for lib_root in os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":"):
                    lib_root = lib_root.strip()
                    if lib_root == "":
                        continue
                    try:
                        rel_in_lib: str = os.path.relpath(src_path[:-4], lib_root)
                    except ValueError:
                        continue
                    if not rel_in_lib.startswith(".."):
                        rel = rel_in_lib
                        break
        return list(map(lambda x: NamespaceName(x), rel.split(os.sep)))
