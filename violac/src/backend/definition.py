# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import UnpackExpr, VariableRef, Expression, CallOp, AttrOp, ClassRef, TypeRef
from .statement import Statement, BlockStmt, DeclStmt, FnBlockStmt, CStmt, TryStmt, CatchStmt, OpStmt, \
    STACK_B_POP_FUNC, CleanupBlock
from .symbol import FunctionName, VariableName, LocalVariableName, VariableState, TupleTypeName, NamespaceName, \
    ClassName, MethodName, CLOSURE_T, TypeName, EXCEPTION_T_NAME, EnumName, GlobalVariableName, GenericArgument, \
    StringTypeName, PropertyVariableName, SymbolTable, VariableStateTable, FunctionTypeName, Object
from utils import CompilerException, SourceInfo, InternalCompilerException

from abc import ABC, abstractmethod
from copy import deepcopy
import os
from typing import Optional

TYPE_INFO_T: str = "viola$dynamic$TypeInfo"
PERROR_FUNC_NAME: str = "viola$io$perror"


class Definition(CompilingItem, ABC):
    """编译定义基类，表示源代码中的一个定义（函数、类、常量等）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """
        初始化定义对象。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        """
        super().__init__(src_info)
        self._symbol_table: SymbolTable = symbol_table

    @property
    @abstractmethod
    def global_init_text(self) -> Optional[str]:
        """获取全局初始化代码文本。"""
        pass

    @property
    @abstractmethod
    def header(self) -> str:
        """获取头文件声明文本。"""
        pass

    def instantiation_full_all(self) -> list["Definition"]:
        """获取此定义的所有泛型实例化结果。"""
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    @abstractmethod
    def is_finished(self) -> bool:
        """获取定义是否已完成。"""
        pass

    @property
    def is_generic(self) -> bool:
        """获取当前定义是否为泛型定义。"""
        return False

    @property
    def is_main(self) -> bool:
        """获取当前定义是否为主函数。"""
        return False

    @abstractmethod
    def optimize(self) -> "Definition":
        """优化当前定义。"""
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        """获取外层代码文本（如全局变量声明）。"""
        pass

    @property
    @abstractmethod
    def source(self) -> str:
        """获取源代码文本。"""
        pass

    @property
    def src_info(self) -> SourceInfo:
        return self._src_info


class ConstDef(Definition):
    """常量定义，封装了一个常量声明语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, namespace: list[NamespaceName]) -> None:
        """
        初始化常量定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param namespace: 命名空间路径。
        """
        super().__init__(src_info, symbol_table)
        self._define_stmt: Optional[Statement] = None
        self._namespace: list[NamespaceName] = namespace
        self._module_name: str = "$".join(map(lambda x: x.name, self._namespace))

    @property
    def global_init_text(self) -> str:
        """获取常量的全局初始化代码文本。"""
        result: list[str] = list(filter(lambda x: x is not None, [
            self._define_stmt.head_text,
            self._define_stmt.global_init_text,
            self._define_stmt.text
        ]))
        return "\n".join(result)

    @property
    def is_finished(self) -> bool:
        """获取常量定义是否已完成。"""
        return self._define_stmt is not None

    @property
    def header(self) -> str:
        """获取常量在头文件中的声明文本。"""
        results: list[str] = list(map(lambda x: "\n".join([
            f"#if _VIOLA_IMPORT_{self._module_name}${x.self_name} || _VIOLA_IMPORT_{self._module_name}$__all__ || _VIOLA_IMPORT_{self._module_name}$__module__",
            f"#ifndef _VIOLA_H_{self._module_name}${x.self_name}",
            f"#define _VIOLA_H_{self._module_name}${x.self_name}",
            f"extern {x.type_name_pair_calling};",
            f"#if _VIOLA_IMPORT_{self._module_name}${x.self_name} || _VIOLA_IMPORT_{self._module_name}$__all__",
            f"#define {x.self_name} {x.name}",
            "#endif",
            "#endif",
            "#endif"
        ]), self._define_stmt.new_variables))
        return "\n\n".join(results)

    def optimize(self) -> "Definition":
        """优化常量定义。"""
        self._define_stmt = self._define_stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        """获取常量的外层代码文本。"""
        return self._define_stmt.outer_text

    def set_stmt(self, stmt: Statement) -> None:
        """设置常量定义中的语句。"""
        self._define_stmt = stmt
        self._define_stmt.set_as_const_def()

    @property
    def source(self) -> str:
        """获取常量的源代码文本。"""
        rename_defines: str = "\n".join([
            f"#define {x.self_name} {x.name}" for x in self._define_stmt.new_variables
        ])
        return "\n".join(rename_defines)


class SqDef(Definition):
    """函数定义，表示一个可执行的函数（含参数和函数体）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str]) -> None:
        """
        初始化函数定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param name: 函数名。
        :param arg_types: 参数类型列表。
        """
        super().__init__(src_info, symbol_table)
        arg_types_decl: list[TypeName] = []
        for arg_type in arg_types:
            if (arg_type, None) not in self._symbol_table:
                raise CompilerException(f"Name {arg_type} is not defined.", src_info)
            arg_type = self._symbol_table[arg_type, None]
            if not isinstance(arg_type, TypeName):
                raise CompilerException(f"Argument {arg_type} is not a type.", src_info)
            arg_types_decl.append(arg_type)
        decl = self._symbol_table[name, tuple(arg_types_decl)]
        self._method_decl: Optional[MethodName] = decl if isinstance(decl, MethodName) else None
        if not isinstance(decl, FunctionName | MethodName):
            raise CompilerException(f"Name {name} is not a function.", src_info)
        self._self_name: str = decl.self_name
        self._decl = decl if isinstance(decl, FunctionName) else decl.as_function()
        self._var_states: VariableStateTable = var_states
        self._outer_variables: dict[VariableName, VariableState] = var_states.state
        self._args: list[LocalVariableName] = list(
            map(lambda n, t: LocalVariableName(src_info, n, t), self._decl.arg_names, self._decl.arg_types)
        )
        for arg in self._args:
            symbol_table.add(arg, arg.name, None)
        self._rets: list[LocalVariableName] = list(
            map(lambda n, t: LocalVariableName(src_info, n, t), self._decl.ret_names, self._decl.ret_types)
        )
        for ret in self._rets:
            symbol_table.add(ret, ret.name, None)
        self._outer_variables.update(dict(map(lambda x: (x, VariableState.ASSIGNED), self._args)))
        self._body: BlockStmt = BlockStmt(src_info, self._symbol_table, var_states)
        self._namespace: list[NamespaceName] = namespace
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._import_module: str = module_name + "$__module__"
        self._is_finished: bool = False
        self._is_from_generic: bool = False
        self._is_main: bool = name == "main"
        self._async_body = None

    def add_stmt(self, stmt: Statement) -> None:
        """向函数体中添加语句。"""
        self._body.add_stmt(stmt)

    @property
    def closure_struct_setting_code(self) -> str:
        """获取闭包结构体设置代码。"""
        return self._body.closure_struct_setting_code

    def finish(self) -> None:
        """完成函数定义，生成异步函数体。"""
        if self._is_finished:
            raise CompilerException("Function is already finished.", self._src_info)
        self._async_body = self.__get_async_body()
        self._body.indent()
        self._body.finish()
        self._is_finished = True

    @property
    def global_init_text(self) -> Optional[str]:
        """获取函数的全局初始化代码文本。"""
        results = list(filter(lambda x: x is not None, [self._body.global_init_text, self._async_body.global_init_text]))
        return "\n".join(results)

    @property
    def header(self) -> str:
        """获取函数在头文件中的声明文本。"""
        if self._is_from_generic:
            return "// GENERIC FUNCTION"
        result: list[str] = [
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all} || _VIOLA_IMPORT_{self._import_module}",
            f"#ifndef _VIOLA_H_{self._import_name}",
            f"#define _VIOLA_H_{self._import_name}",
            self.header_no_wrap,
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all}",
            f"#define {self._decl.self_name} {self._decl.name}",
            f"#define {self._decl.as_async().self_name} {self._decl.as_async().name}",
            "#endif",
            "#endif",
            "#endif"
        ]
        return "\n".join(result)

    @property
    def header_no_wrap(self) -> str:
        """获取函数在头文件中未经包装的声明文本（不含条件编译）。"""
        self._decl: FunctionName
        text: list[str] = [
            self._decl.as_declare() + ";",
            self._decl.as_async().as_declare() + ";"
        ]
        return "\n".join(text)

    def instantiation(self, cls_decl: ClassName, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        """将函数作为类方法进行泛型实例化。"""
        if not self._decl.type.is_generic:
            raise CompilerException("Function is not generic.", self._src_info)
        new_sq = deepcopy(self)
        type_args_tuple: tuple[TypeName, ...] = tuple(map(lambda x: type_args[x], cls_decl.generic_args))
        new_sq._method_decl = self._method_decl.set_cls(
            self._symbol_table.get_generic_cls_instance(cls_decl, type_args_tuple), 0
        )
        new_sq._decl = self._method_decl.as_function()
        new_sq._body = new_sq._body.instantiation(type_args)
        return new_sq

    def instantiation_full(self, type_args: tuple[TypeName, ...]) -> "SqDef":
        """使用元组形式的类型参数进行泛型实例化。"""
        type_args_dict: dict[GenericArgument, TypeName] = dict(zip(self._decl.type.generic_args, type_args))
        return self.instantiation_full_by_dict(type_args_dict)

    def instantiation_full_all(self) -> list["SqDef"]:
        """获取函数的所有泛型实例化结果。"""
        type_args_list: list[tuple[TypeName, ...]] = self._symbol_table.get_all_to_instantiate_symbols(
            self._src_info, self._decl)
        instances = list(map(lambda t: self.instantiation_full(t), type_args_list))
        return instances

    def instantiation_full_by_dict(self, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        """使用字典形式的类型参数进行泛型实例化。"""
        if not self._decl.type.is_generic:
            raise CompilerException("Function is not generic.", self._src_info)
        new_sq = deepcopy(self)
        new_sq._decl = new_sq._decl.instantiation(
            self._symbol_table.get_generic_func_instance(new_sq._decl, tuple(type_args)).name, type_args
        )
        new_sq._body = new_sq._body.instantiation(type_args)
        return new_sq

    @property
    def is_finished(self) -> bool:
        """获取函数定义是否已完成。"""
        return self._is_finished

    @property
    def is_generic(self) -> bool:
        """获取函数是否为泛型函数。"""
        return self._decl.type.is_generic

    @property
    def is_main(self) -> bool:
        """获取函数是否为主函数。"""
        return self._is_main

    @property
    def is_method(self) -> bool:
        """获取函数是否为类方法。"""
        return self._decl.is_method

    @property
    def name(self) -> str:
        """获取函数名。"""
        return self._decl.name

    def optimize(self) -> "SqDef":
        """优化函数定义。"""
        self._body = self._body.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        """获取函数的外层代码文本。"""
        results = list(filter(lambda x: x is not None, [self._body.outer_text, self._async_body.outer_text]))
        return "\n".join(results)

    @property
    def self_name(self) -> str:
        """获取函数在 Viola 中的别名。"""
        return self._self_name

    def set_as_closure(self, name: str) -> None:
        """将函数设置为闭包，绑定捕获结构体。"""
        self._body.set_as_closure(name, self._args)

    @property
    def source(self) -> str:
        """获取函数的源代码文本。"""
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([self._source(True), rename_define])

    @property
    def type(self) -> FunctionTypeName:
        """获取函数的返回类型。"""
        return self._decl.type

    @property
    def used_variables(self) -> set[VariableName]:
        """获取函数中使用的非参数外部变量集合。"""
        return self._body.input_variables - set(self._args)

    def _source(self, is_native_func: bool) -> str:
        """生成函数的 C 源代码文本。"""
        self._decl: FunctionName
        if is_native_func:
            define_name: str = self._decl.as_define_name()
        else:
            define_name: str = self._decl.as_define_name_raw()
        sync_text: list[str] = [
            define_name + " {",
            self._body.head_text + ("\n\r" + self._body.tail_recursive_mark) if self._body.tail_recursive_mark is not None else "",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exc;",
            self._body.text,
            CleanupBlock(self._src_info, self._symbol_table, self._var_states, list(self._body.new_variables)).text,
            "}"
        ]
        async_text: list[str] = [
            self._decl.as_async().as_declare() + " {",
            self._async_body.text,
            "}"
        ]
        text = [*sync_text, "", *async_text]
        return "\n".join(text)

    def __get_async_body(self) -> TryStmt:
        """生成异步函数体，包含参数解包、同步函数调用和异常处理。"""
        arg_tuple_name: TupleTypeName = TupleTypeName(self._src_info, self._decl.arg_types)
        ret_tuple_name: TupleTypeName = TupleTypeName(self._src_info, self._decl.ret_types)
        arg_unpack_expr: UnpackExpr = UnpackExpr(self._src_info, self._symbol_table,
                                                 VariableRef(self._src_info, self._symbol_table, LocalVariableName(
                                                     self._src_info, "params", arg_tuple_name
                                                 )))
        arg_unpack_stmt: DeclStmt = DeclStmt(self._src_info, self._symbol_table, self._var_states, self._namespace)
        arg_unpack_stmt.set_var_value(arg_unpack_expr)
        arg_unpack_stmt.set_vars_with_known_type(self._decl.arg_names, self._decl.arg_types,
                                                 [False] * len(self._decl.arg_names))
        arg_unpack_stmt.finish()
        arg_unpack_stmt.indent()
        ret_unpack_expr: UnpackExpr = UnpackExpr(self._src_info, self._symbol_table,
                                                 VariableRef(self._src_info, self._symbol_table, LocalVariableName(
                                                     self._src_info, "returns", ret_tuple_name
                                                 )))
        ret_unpack_stmt: DeclStmt = DeclStmt(self._src_info, self._symbol_table, self._var_states, self._namespace)
        ret_unpack_stmt.set_var_value(ret_unpack_expr)
        ret_unpack_stmt.set_vars_with_known_type(self._decl.ret_names, self._decl.ret_types,
                                                 [False] * len(self._decl.ret_names))
        ret_unpack_stmt.finish()
        ret_unpack_stmt.indent()
        sync_call_args_text: str = ", ".join(map(lambda x: f"${x}", self._decl.arg_names))
        sync_call_rets_text: str = ", ".join(map(lambda x: f"&${x}", self._decl.ret_names))
        if sync_call_args_text != "" and sync_call_rets_text != "":
            sync_call_params_text: str = f"{sync_call_args_text}, {sync_call_rets_text}"
        else:
            sync_call_params_text: str = sync_call_args_text + sync_call_rets_text
        if sync_call_params_text != "":
            sync_call_params_text: str = f"{sync_call_params_text}, listener->exc"
        else:
            sync_call_params_text: str = "listener->exc"
        sync_call_text: str = f"\t{self._decl.name}({sync_call_params_text});"
        try_stmt: TryStmt = TryStmt(self._src_info, self._symbol_table, self._var_states)
        try_inner: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
        try_inner.set_text("\n".join([
            arg_unpack_stmt.text,
            ret_unpack_stmt.text,
            sync_call_text,
            f"{STACK_B_POP_FUNC}(listener->currentThreadId);"
        ]))
        try_stmt.set_stmt(try_inner)
        catch_stmt: CatchStmt = CatchStmt(self._src_info, self._symbol_table, self._var_states)
        # noinspection PyTypeChecker
        catch_var: VariableName = LocalVariableName(self._src_info, "exc",
                                                    self._symbol_table[EXCEPTION_T_NAME, None])
        catch_stmt.set_except_decl(catch_var)
        catch_inner: BlockStmt = BlockStmt(self._src_info, self._symbol_table, self._var_states)
        catch_inner_print: OpStmt = OpStmt(self._src_info, self._symbol_table, self._var_states)
        catch_inner_print_call: CallOp = CallOp(self._src_info, self._symbol_table)
        catch_inner_what_attr: AttrOp = AttrOp(self._src_info, self._symbol_table)
        catch_inner_what_attr.set_attr("what")
        catch_inner_what_attr.set_caller(VariableRef(self._src_info, self._symbol_table, catch_var))
        catch_inner_what_call: CallOp = CallOp(self._src_info, self._symbol_table)
        catch_inner_what_call.set_func(catch_inner_what_attr)
        catch_inner_print_call.add_arg(catch_inner_what_call, None)
        # noinspection PyTypeChecker
        catch_inner_print_func: VariableRef = VariableRef(self._src_info, self._symbol_table, self._symbol_table[
            PERROR_FUNC_NAME, (StringTypeName,)
        ])
        catch_inner_print_call.set_func(catch_inner_print_func)
        catch_inner_print.set_expr(catch_inner_print_call)
        catch_inner.add_stmt(catch_inner_print)
        catch_inner_assign: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
        catch_inner_assign.set_text("listener->exc = exc;")
        catch_inner.add_stmt(catch_inner_assign)
        catch_inner.finish()
        catch_stmt.set_stmt(catch_inner)
        try_stmt.add_except_stmt(catch_stmt)
        try_stmt.remove_mark()
        return try_stmt


class ConstructorDef(SqDef):
    """构造函数定义，用于初始化类的实例。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], cls_name: str, arg_types: list[str]) -> None:
        """
        初始化构造函数定义，自动分配对象内存。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param cls_name: 类名。
        :param arg_types: 参数类型列表。
        """
        super().__init__(src_info, symbol_table, var_states, namespace, f"{cls_name}.__new__", arg_types)
        cls = self._symbol_table[cls_name, None]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"Name {cls_name} is not a class.", src_info)
        if len(self._decl.ret_names) != 1:
            raise CompilerException("Constructor must return exactly one value.", self._src_info)
        if self._decl.ret_types[0] != cls:
            raise CompilerException("Constructor must return a value of the same type as the class.", self._src_info)
        this_name: str = "_this"
        this_type: ClassName = cls
        self._this_var: LocalVariableName = LocalVariableName(self._src_info, this_name, this_type)
        this_alloc_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
        this_alloc_stmt.set_text(
            f"{self._this_var.type_name_pair_calling} = ({cls.c_calling_name})malloc(sizeof({cls.c_alloc_name}));")
        self.add_stmt(this_alloc_stmt)

    def add_stmt(self, stmt: Statement) -> None:
        """向构造函数体中添加语句，检查不能直接操作 this 对象。"""
        if self._this_var in stmt.input_variables:
            raise CompilerException("Statements in constructor should be static.", stmt._src_info)
        if self._this_var in stmt.new_variables:
            raise CompilerException("The object to be created can not be assigned directly.", stmt._src_info)
        super().add_stmt(stmt)

    @property
    def this_var(self) -> LocalVariableName:
        """获取构造函数中表示当前实例的 this 变量。"""
        return self._this_var


class DestructorDef(SqDef):
    """析构函数定义，用于释放类的实例资源。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], cls_name: str) -> None:
        """
        初始化析构函数定义，生成释放对象属性的清理代码。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param cls_name: 类名。
        """
        super().__init__(src_info, symbol_table, var_states, namespace, f"{cls_name}.__del__", [])
        cls = self._symbol_table[cls_name, None]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"Name {cls_name} is not a class.", src_info)
        self._this_var: LocalVariableName = LocalVariableName(self._src_info, self._decl.arg_names[0],
                                                              self._decl.arg_types[0])
        if cls.is_c_part:
            return
        this_free_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
        properties_to_free: list[VariableName] = list(filter(lambda y: y.is_object, cls.properties.values()))
        free_texts: list[str] = []
        for x in properties_to_free:
            attr_op: AttrOp = AttrOp(src_info, self._symbol_table)
            attr_op.set_attr("__del__")
            attr_op.set_caller(VariableRef(src_info, self._symbol_table, x))
            call_op: CallOp = CallOp(src_info, self._symbol_table)
            call_op.set_func(attr_op)
            call_op.set_returns([])
            free_call_text = call_op.front_text.split("\n")
            free_call_text = list(map(lambda y: "\t\t\t\t" + y, free_call_text))
            free_text_item: str = "\n".join([
                f"\t\tif ({self._this_var.name}->{x.name}) {{",
                f"\t\t\t{self._this_var.name}->{x.name}->$refCount--;",
                f"\t\t\tif ({self._this_var.name}->{x.name}->$refCount == 0) {{",
                "\n".join(free_call_text),
                "\t\t\t}"
                "\t\t}"
            ])
            free_texts.append(free_text_item)
        free_text: list[str] = [
            f"if ({self._this_var.name}->$refCount == 0) {{",
            f"\tif ({self._this_var.name}->$parent) {{",
            f"\t\t{self._this_var.name}->$parent->$refCount--;",
            "\t} else {",
            *free_texts,
            f"\t\tfree({self._this_var.name});",
            f"\t\t{self._this_var.name} = NULL;",
            "\t}"
            "}"
        ]
        this_free_stmt.set_text("\n".join(free_text))
        self.add_stmt(this_free_stmt)


class FnDef(SqDef):
    """函数定义（fn），使用 FnBlockStmt 作为函数体支持声明排序。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str]) -> None:
        """
        初始化函数定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param name: 函数名。
        :param arg_types: 参数类型列表。
        """
        super().__init__(src_info, symbol_table, var_states, namespace, name, arg_types)
        self._body: FnBlockStmt = FnBlockStmt(self._src_info, self._symbol_table, var_states)


class CPartSqDef(SqDef):
    """C 语言兼容的函数定义（与 extern "C" 配合使用）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, symbol_table, var_states, namespace, name, arg_types)

    def add_stmt(self, stmt: CStmt) -> None:
        """向函数体中添加 C 语句。"""
        self._body.add_stmt(stmt)

    @property
    def source(self) -> str:
        """获取 C 兼容函数的源代码文本（含 extern "C" 包装）。"""
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([
            "#ifdef __cplusplus",
            "extern \"C\" {",
            "#endif",
            self._source(False),
            rename_define,
            "#ifdef __cplusplus",
            "}",
            "#endif"
        ])


class CppSqDef(CPartSqDef):
    """C++ 兼容的函数定义（不含 extern "C" 包装）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, symbol_table, var_states, namespace, name, arg_types)

    def add_stmt(self, stmt: CStmt) -> None:
        """向函数体中添加 C 语句。"""
        self._body.add_stmt(stmt)

    @property
    def source(self) -> str:
        """获取 C++ 兼容函数的源代码文本。"""
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([
            self._source(True),
            rename_define
        ])


class GlobalDef(CPartSqDef):
    """全局初始化函数定义，用于模块的全局初始化代码。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable, namespace: list[NamespaceName]) -> None:
        """
        初始化全局函数定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        """
        super().__init__(src_info, symbol_table, var_states, namespace, "__global__", [])

    def add_stmt(self, stmt: CStmt) -> None:
        """向全局初始化函数中添加语句，移除其调试标记。"""
        stmt.remove_mark()
        super().add_stmt(stmt)

    def finish(self) -> None:
        super().finish()
        self._body.remove_mark()

    @property
    def header_no_wrap(self) -> str:
        """获取全局函数未经包装的头文件声明。"""
        return self._decl.as_declare() + ";"

    @property
    def header(self) -> str:
        """获取全局函数在头文件中的声明文本。"""
        result: list[str] = [
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all} || _VIOLA_IMPORT_{self._import_module}",
            f"#ifndef _VIOLA_H_{self._import_name}",
            f"#define _VIOLA_H_{self._import_name}",
            self.header_no_wrap,
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all}",
            f"#define {self._decl.self_name} {self._decl.name}",
            "#endif",
            "#endif",
            "#endif"
        ]
        return "\n".join(result)

    @property
    def source(self) -> str:
        """获取全局函数的源代码文本。"""
        outer_text: str = self._body.outer_text if self._body.outer_text is not None else ""
        namespace_name: str = "$".join(map(lambda x: x.name, self._namespace))
        define_name: str = f"void {namespace_name}$__global__()"
        sync_text: list[str] = [
            define_name + " {",
            self._body.text,
            "}"
        ]
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([outer_text, "\n".join(sync_text), rename_define])


class ClassDef(Definition):
    """类定义，管理类的虚函数表、方法和静态属性。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, namespace: list[NamespaceName], name: str,
                 var_states: VariableStateTable) -> None:
        """
        初始化类定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param namespace: 命名空间路径。
        :param name: 类名。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table)
        self._self_name: str = name
        self._namespace: list[NamespaceName] = namespace
        # noinspection PyTypeChecker
        self._decl: ClassName = self._symbol_table[name, None]
        if not isinstance(self._decl, ClassName):
            raise CompilerException(f"{name} is not a class.", src_info)
        self._global_vars: dict[VariableName, VariableState] = var_states.state
        self._this_var: VariableName = LocalVariableName(self._src_info, "_this", self._decl)
        self._methods: dict[str, SqDef] = {}
        self._static_properties: dict[PropertyVariableName, Expression] = {}
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._import_module: str = module_name + "$__module__"
        # var_states.add_scope()
        # destructor = DestructorDef(self._src_info, self._symbol_table, var_states, self._namespace, name)
        # destructor.finish()
        # self.add_method(destructor)
        # var_states.pop_scope()
        self._vtable_name: str = self._decl.vtable_name
        self._parent_vtable_name: str = f"{self._decl.parent.name}$$vtable" if self._decl.parent != Object else "NULL"
        self._is_finished: bool = False
        self._is_from_generic: bool = False

    def add_method(self, method: SqDef) -> None:
        """向类中添加方法定义。"""
        self._decl: ClassName
        if method.self_name in self._methods:
            raise CompilerException(f"{method.self_name} is already defined.", method._src_info)
        self._methods[method.self_name] = method

    def add_static_prop(self, name: str, value: Expression) -> None:
        """向类中添加静态属性。"""
        if name not in self._decl.properties:
            raise CompilerException(f"{name} is not a property of {self._self_name}.", value.src_info)
        if name in self._decl.properties:
            raise CompilerException(f"{name} is already defined.", value.src_info)
        self._static_properties[self._decl.properties[name]] = value

    @property
    def decl(self) -> ClassName:
        """获取类的类型声明。"""
        return self._decl

    def finish(self) -> None:
        """完成类定义。"""
        if self._is_finished:
            raise InternalCompilerException("ClassDef is already finished", self._src_info)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
        """获取类的全局初始化代码文本（虚函数表和静态属性）。"""
        # noinspection PyUnresolvedReferences
        if not self._decl.is_abstract:
            # noinspection PyUnresolvedReferences
            vfunc_text: str = f"malloc(sizeof({self._decl.c_alloc_name}$$vfunc))"
            # noinspection PyUnresolvedReferences
            vfunc: list[MethodName] = list(filter(lambda x: x.is_abstract, self._decl.methods.values()))
            sync_vfunc_text: list[str] = list(map(
                lambda x: f"(({self._decl.name}$$vfunc *){self._vtable_name}.vfunc)->{x.method_name} = {x.name};",
                vfunc
            ))
            async_vfunc_text: list[str] = list(map(
                lambda
                    x: f"(({self._decl.name}$$vfunc *){self._vtable_name}.vfunc)->{x.as_async().method_name} = {x.as_async().name};",
                vfunc
            ))
            vfunc_assign: list[str] = sync_vfunc_text + async_vfunc_text
        else:
            vfunc_text: str = "NULL"
            vfunc_assign: list[str] = []
        # noinspection PyUnresolvedReferences
        methods_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x.global_init_text, self._methods.values()))
        )
        static_props_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x.global_init_text, self._static_properties.values()))
        )
        result: list[str] = [
            f"{self._vtable_name}.$parent = {self._parent_vtable_name};",
            f"{self._vtable_name}.vfunc = {vfunc_text};",
            *vfunc_assign,
            *static_props_global_text,
            *methods_global_text
        ]
        return "\n".join(result)

    @property
    def header(self) -> str:
        """获取类在头文件中的声明文本。"""
        self._decl: ClassName
        if self._is_from_generic:
            return "// GENERIC CLASS"
        method_headers_list: list[str] = list(map(lambda x: x.header_no_wrap, self._methods.values()))
        result: list[str] = [
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all} || _VIOLA_IMPORT_{self._import_module}",
            f"#ifndef _VIOLA_H_{self._import_name}",
            f"#define _VIOLA_H_{self._import_name}",
            self.header_no_wrap,
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all}",
            f"#define {self._decl.self_name} {self._decl.name}",
            *[f"#define {prop.self_name_with_class} {prop.name}" for prop in self._static_properties],
            "#endif",
            "\n".join(method_headers_list),
            "#endif",
            "#endif"
        ]
        return "\n".join(result)

    @property
    def header_no_wrap(self) -> str:
        """获取类未经包装的头文件声明（结构体定义与方法声明）。"""
        self._decl: ClassName
        class_info_text: str = f"extern {TYPE_INFO_T} {self._vtable_name};"
        # noinspection PyUnresolvedReferences
        properties_text: str = "\n".join(
            map(
                lambda x: f"\t{x.type_name_pair_calling};",
                filter(lambda x: not x.is_static, self._decl.properties.values())
            )
        )
        struct_def: list[str] = [
            class_info_text,
            "\ntypedef struct {",
            properties_text,
            "} " + self._decl.name + ";"
        ]
        static_props_text: str = "\n".join(
            map(
                lambda x: f"extern {x.type_name_pair_calling};",
                filter(lambda x: x.is_static, self._decl.properties.values())
            )
        )
        # noinspection PyUnresolvedReferences
        if self._decl.is_abstract:
            result_def = self._vfunc_def.copy()
            if len(result_def) > 0:
                result_def.append("")
            result_def.extend(struct_def)
        else:
            result_def = struct_def
        result_def.append(static_props_text)
        methods_def: list[str] = list(map(lambda x: x.header_no_wrap, self._methods.values()))
        return "\n".join([*result_def, "\n", *methods_def])

    def instantiation(self, type_args: list[TypeName]) -> "ClassDef":
        """将类作为泛型类进行实例化。"""
        if not self._decl.is_generic:
            raise CompilerException("ClassDef.instantiation called on non-generic class", self._src_info)
        new_cls = deepcopy(self)
        new_cls._decl = self._symbol_table.get_generic_cls_instance(new_cls._decl, tuple(type_args))
        type_args_dict: dict[GenericArgument, TypeName] = dict(zip(self._decl.generic_args, type_args))
        new_cls._methods = dict(
            map(lambda x: (x.self_name, x.instantiation(self._decl, type_args_dict)), self._methods.values())
        )
        new_cls._is_from_generic = True
        return new_cls

    def instantiation_full_all(self) -> list["ClassDef"]:
        """获取类的所有泛型实例化结果。"""
        type_args_list: list[tuple[TypeName, ...]] = self._symbol_table.get_all_to_instantiate_symbols(
            self._src_info, self._decl)
        instances = list(map(lambda t: self.instantiation(t), type_args_list))
        return instances

    @property
    def is_finished(self) -> bool:
        """获取类定义是否已完成。"""
        return self._is_finished

    @property
    def is_generic(self) -> bool:
        """获取类是否为泛型类。"""
        return self._decl.is_generic

    def optimize(self) -> "ClassDef":
        """优化类定义及其所有方法。"""
        for k, v in self._methods.items():
            self._methods[k] = v.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        """获取类的外层代码文本（方法和静态属性的外层声明）。"""
        methods_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._methods.values())))
        props_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._static_properties.values())))
        result: str = "\n".join([methods_result, props_result])
        return result if result != "" else None

    @property
    def source(self) -> str:
        """获取类的源代码文本。"""
        methods_def: list[str] = list(map(lambda x: x.source, self._methods.values()))
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n\n".join(methods_def + [rename_define])

    @property
    def _vfunc_def(self) -> list[str]:
        """获取虚函数表结构体定义。"""
        self._decl: ClassName
        # noinspection PyUnresolvedReferences
        vfunc: list[MethodName] = list(filter(lambda x: x.is_abstract, self._decl.methods.values()))
        # noinspection PyUnresolvedReferences
        if not self._decl.is_abstract or len(vfunc) == 0:
            return []
        sync_vfunc_text: list[str] = list(map(lambda x: "\t" + x.as_method_type_name_pair + ";", vfunc))
        async_vfunc_text: list[str] = list(map(lambda x: "\t" + x.as_async().as_method_type_name_pair + ";", vfunc))
        struct_def: list[str] = [
            "typedef struct {",
            "\n".join(sync_vfunc_text),
            "\n".join(async_vfunc_text),
            "} " + self._decl.name + "$$vfunc;"
        ]
        return struct_def


class CPartImportDef(Definition):
    """C 语言头文件导入定义，生成 extern "C" 包装的 #include 指令。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, include_path: str) -> None:
        """
        初始化 C 部分导入定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param include_path: 头文件路径。
        """
        super().__init__(src_info, symbol_table)
        self._include_path: str = include_path

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def header(self) -> str:
        return "\n".join([
            "#ifdef __cplusplus",
            "extern \"C\" {",
            "#endif",
            f"#include {self._include_path}",
            "#ifdef __cplusplus",
            "}",
            "#endif"
        ])

    @property
    def is_finished(self) -> bool:
        return True

    def optimize(self) -> "Definition":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def source(self) -> str:
        return f"// #include {self._include_path}"


class FromImportDef(Definition):
    """from ... import ... 导入定义，生成条件编译的 #include 指令。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, root_path: str, module_path: str, def_name: list[str]) -> None:
        """
        初始化 from...import 导入定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param root_path: 项目根路径。
        :param module_path: 模块路径。
        :param def_name: 导入的符号名列表。
        """
        super().__init__(src_info, symbol_table)
        self._root_path: str = root_path
        self._module_path: str = module_path
        if len(def_name) == 1 and def_name[0] == "*":
            def_name = ["__all__"]
        self._def_name: list[str] = def_name
        self._get_include_path()
        self._namespace = self._get_namespace()

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def header(self) -> str:
        result: list[str] = [
            *[f"#define _VIOLA_IMPORT_{self._namespace}${def_name}" for def_name in self._def_name],
            f"#include \"{self._module_path}.viola.h\""
        ]
        return "\n".join(result)

    @property
    def is_finished(self) -> bool:
        return True

    def optimize(self) -> "Definition":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def source(self) -> str:
        return f"// from {self._module_path} import {', '.join(self._def_name)}"

    def _get_include_path(self) -> None:
        """解析模块路径为相对于源文件的 #include 路径。"""
        rel_path_about_root: str = os.path.relpath(os.path.dirname(self._src_info.path), self._root_path)
        dir_level: int = len(rel_path_about_root.split(os.pathsep))
        if self._module_path.startswith("."):
            self._module_path = self._module_path[1:]
            rel_path: str = ""
            dir_level_count: int = 0
            while self._module_path.startswith("."):
                rel_path += ".." + os.pathsep
                self._module_path = self._module_path[1:]
                dir_level_count += 1
                if dir_level_count >= dir_level:
                    raise CompilerException(f"{self._module_path} is not a valid module path.", self._src_info)
            self._module_path = rel_path.replace(".", os.pathsep)
        else:
            to_include_abs_path: str = os.path.join(self._module_path.replace(".", os.pathsep), self._root_path)
            self._module_path = os.path.relpath(to_include_abs_path, os.path.dirname(self._src_info.path))

    def _get_namespace(self) -> str:
        """获取模块路径对应的命名空间字符串。"""
        abs_path: str = os.path.abspath(os.path.join(self._root_path, self._module_path))
        rel_path_about_root: str = os.path.relpath(abs_path, self._root_path)
        return rel_path_about_root.replace(os.pathsep, "$")


class Closure(Expression):
    """闭包表达式，封装一个函数定义及其捕获的外部变量。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """
        初始化闭包表达式。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        """
        super().__init__(src_info, symbol_table)
        self._var_name: str = self._symbol_table.get_counter()
        self._sq_def: Optional[SqDef] = None
        self._inline_mapping: dict[str, str] = {}

    def as_async(self) -> "Expression":
        """闭包作为异步表达式使用。"""
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        """将闭包中的变量名映射为内联变量。"""
        new_expr = deepcopy(self)
        new_expr._inline_mapping = inline_mapping
        new_expr._inline_mapping[self._var_name] = self._symbol_table.get_counter()
        new_expr._var_name = new_expr.inline_mapping[self._var_name]
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        """闭包不参与尾递归优化。"""
        return self

    @property
    def front_text(self) -> Optional[str]:
        """获取闭包的前置代码（分配闭包结构体）。"""
        result: list[str] = [
            self._sq_def.closure_struct_setting_code,
            f"{self._var_name} = ({CLOSURE_T} *)malloc(sizeof({CLOSURE_T}));",
            f"{self._var_name}->func = {self._sq_def.name};",
            f"{self._var_name}->capture = {self._var_name}$$capture;"
        ]
        return "\n".join(result)

    @property
    def global_init_text(self) -> Optional[str]:
        """获取闭包的全局初始化代码。"""
        return self._sq_def.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        """获取闭包的头代码（声明闭包变量）。"""
        return f"{CLOSURE_T} *{self._var_name};"

    @property
    def inline_mapping(self) -> dict[str, str]:
        """获取内联变量映射。"""
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        """泛型实例化闭包内部的函数定义。"""
        new_expr: Closure = deepcopy(self)
        new_expr._sq_def = self._sq_def.instantiation_full_by_dict(type_args)
        return new_expr

    def optimize(self) -> "Expression":
        """优化闭包内部的函数定义。"""
        self._sq_def = self._sq_def.optimize()
        return self

    @property
    def outer_text(self) -> str:
        """获取闭包的外层代码（函数定义的源代码）。"""
        return self._sq_def.source

    @property
    def release_text(self) -> Optional[str]:
        """获取闭包的释放代码（引用计数减一）。"""
        result: list[str] = [
            f"if ({self._var_name}->$refCount == 0) {{",
            f"\tif ({self._var_name}->$parent) {{",
            f"\t\t{self._var_name}->$parent->$refCount--;",
            "\t} else {",
            f"\t\tfree({self._var_name});",
            f"\t\t{self._var_name} = NULL;",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        """获取闭包的返回类型。"""
        return self._sq_def.type

    def set_definition(self, sq_def: "SqDef") -> None:
        """设置闭包内部的函数定义。"""
        sq_def.set_as_closure(self._var_name)
        self._sq_def = sq_def

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        """闭包不参与常量替换。"""
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        """闭包不产生尾递归标记。"""
        return None

    @property
    def text(self) -> str:
        """获取闭包的文本表示（变量名）。"""
        return self._var_name

    @property
    def used_variables(self) -> set[VariableName]:
        """获取闭包中使用的外部变量集合。"""
        return self._sq_def.used_variables

    def validate(self) -> None:
        """验证闭包是否已完成。"""
        if not self._sq_def.is_finished:
            raise CompilerException("Closure is not finished.", self._sq_def.src_info)


class GenericCall(CompilingItem):
    """泛型调用，根据泛型表达式和类型参数实例化出具体的表达式。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """
        初始化泛型调用。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        """
        super().__init__(src_info)
        self._symbol_table = symbol_table
        self._generic_symbol: Optional[Expression] = None
        self._type_args: list[TypeName] = []
        self._instance: Optional[Expression] = None
        self._is_finished: bool = False

    def add_type_arg(self, t: TypeRef) -> None:
        """添加一个类型参数。"""
        self._type_args.append(t.return_type)

    def finish(self) -> None:
        """完成泛型调用，根据泛型表达式和类型参数生成具体的表达式。"""
        if self._generic_symbol is None:
            raise InternalCompilerException("The generic type is not specified", self._src_info)
        if len(self._type_args) == 0:
            raise CompilerException("Type arguments should not be empty", self._src_info)
        if isinstance(self._generic_symbol, VariableRef):
            func = self._generic_symbol.var
            if not isinstance(func, FunctionName):
                raise CompilerException(f"{func} is not a function.", self._src_info)
            func = self._symbol_table.get_generic_func_instance(func, tuple(self._type_args))
            self._instance = VariableRef(self._src_info, self._symbol_table, func)
        elif isinstance(self._generic_symbol, AttrOp):
            method = self._generic_symbol.as_method()
            if not isinstance(method, MethodName):
                raise CompilerException(f"{method} is not a method.", self._src_info)
            method = self._symbol_table.get_generic_method_instance(method, tuple(self._type_args))
            self._instance: AttrOp = AttrOp(self._src_info, self._symbol_table)
            self._instance.set_caller(self._generic_symbol.caller)
            self._instance.set_attr(method.self_name)
        elif isinstance(self._generic_symbol, ClassRef):
            cls = self._generic_symbol.return_type
            # noinspection PyTypeChecker
            cls = self._symbol_table.get_generic_cls_instance(cls, tuple(self._type_args))
            self._instance = ClassRef(self._src_info, self._symbol_table, cls)
        else:
            raise CompilerException(f"{self._generic_symbol} is not a function or method or class.", self._src_info)
        self._is_finished = True

    @property
    def instance(self) -> Expression:
        """获取泛型调用实例化后的表达式。"""
        if not self._is_finished:
            raise InternalCompilerException("GenericCall is not finished.", self._src_info)
        # noinspection PyTypeChecker
        return self._instance

    def optimize(self) -> CompilingItem:
        """空优化，泛型调用本身不包含可变内容。"""
        return self

    def set_generic_expr(self, expr: Expression) -> None:
        """设置泛型表达式（函数、方法或类）。"""
        self._generic_symbol = expr


class EnumDef(Definition):
    """枚举定义，包含一组具名的常量值。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, namespace: list[NamespaceName], name: str) -> None:
        """
        初始化枚举定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param namespace: 命名空间路径。
        :param name: 枚举名。
        """
        super().__init__(src_info, symbol_table)
        self._namespace: list[NamespaceName] = namespace
        self._name: str = name
        self._decl = self._symbol_table[name, None]
        if not isinstance(self._decl, EnumName):
            raise CompilerException(f"{name} is not an enum.", src_info)
        self._based_type: TypeName = self._decl.based_type
        self._enum: list[tuple[GlobalVariableName, Expression]] = []
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._is_finished: bool = False

    def add_enum(self, name: str, expr: Expression) -> None:
        """添加枚举值，包含名称和初始值表达式。"""
        if not expr.return_type.convertable_to(self._based_type, self._symbol_table.symbols):
            raise CompilerException(f"{expr.return_type} is not convertable to {self._based_type}.", self._src_info)
        var: GlobalVariableName = GlobalVariableName(self._src_info, self._decl.as_namespace(), name, self._based_type)
        self._enum.append((var, expr))

    def finish(self) -> None:
        """完成枚举定义。"""
        if self._is_finished:
            raise CompilerException("Enum is already finished.", self._src_info)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
        """获取枚举的全局初始化代码文本。"""
        front_text: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].front_text, self._enum)))
        result: list[str] = list(map(lambda x: f"{x[0].name} = {x[1].text};", self._enum))
        expr_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x[1].global_init_text, self._enum)))
        return "\n".join(front_text + expr_global_text + result)

    @property
    def header(self) -> str:
        """获取枚举在头文件中的声明文本。"""
        self._decl: ClassName
        result: list[str] = [
            f"#if _VIOLA_IMPORT_{self._import_name} || _VIOLA_IMPORT_{self._import_all}",
            f"#ifndef _VIOLA_H_{self._import_name}",
            f"#define _VIOLA_H_{self._import_name}",
            self.header_no_wrap,
            "#endif",
            "#endif"
        ]
        return "\n".join(result)

    @property
    def header_no_wrap(self) -> str:
        """获取枚举未经包装的头文件声明。"""
        result: list[str] = list(map(lambda x: f"extern {x[0].type_name_pair_calling};", self._enum))
        return "\n".join(result)

    @property
    def is_finished(self) -> bool:
        """获取枚举定义是否已完成。"""
        return self._is_finished

    def optimize(self) -> "Definition":
        """优化枚举中的所有值表达式。"""
        for i, (name, value) in enumerate(self._enum):
            self._enum[i] = (name, value.optimize())
        return self

    @property
    def outer_text(self) -> Optional[str]:
        """获取枚举的外层代码文本。"""
        result = "\n".join(map(lambda x: x[1].outer_text, self._enum))
        return result if result != "" else None

    @property
    def source(self) -> str:
        """获取枚举的源代码文本。"""
        return f"// ENUM: {self._name}"
