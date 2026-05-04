# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import UnpackExpr, VariableRef, Expression, CallOp, AttrOp
from .statement import Statement, BlockStmt, VAR_STATE_TABLE, DeclStmt, FnBlockStmt, CStmt, TryStmt, CatchStmt, OpStmt, \
    STACK_B_POP_FUNC
from .symbol import FunctionName, VariableName, TemporaryVariableName, VariableState, TupleTypeName, NamespaceName, \
    ClassName, MethodName, CLOSURE_T, TypeName, EXCEPTION_T_NAME, EnumName, GlobalVariableName, GenericArgument, \
    ArrayTypeName, StringTypeName, PropertyVariableName
import backend.expression as expression
from utils import CompilerException, SourceInfo, InternalCompilerException

from abc import ABC, abstractmethod
from copy import deepcopy
import os
from typing import Optional

TYPE_INFO_T: str = "viola$dynamic$TypeInfo"
PERROR_FUNC_NAME: str = "viola$io$perror"


class Definition(CompilingItem, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)

    @property
    @abstractmethod
    def global_init_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def header(self) -> str:
        pass

    def instantiation_full_all(self) -> list["Definition"]:
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    @abstractmethod
    def is_finished(self) -> bool:
        pass

    @property
    def is_generic(self) -> bool:
        return False

    @property
    def is_main(self) -> bool:
        return False

    @abstractmethod
    def optimize(self) -> "Definition":
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def source(self) -> str:
        pass

    @property
    def src_info(self) -> SourceInfo:
        return self._src_info


class ConstDef(Definition):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName]) -> None:
        super().__init__(src_info)
        self._define_stmt: Optional[Statement] = None
        self._namespace: list[NamespaceName] = namespace
        self._module_name: str = "$".join(map(lambda x: x.name, self._namespace))

    @property
    def global_init_text(self) -> str:
        result: list[str] = list(filter(lambda x: x is not None, [
            self._define_stmt.head_text,
            self._define_stmt.global_init_text,
            self._define_stmt.text
        ]))
        return "\n".join(result)

    @property
    def is_finished(self) -> bool:
        return self._define_stmt is not None

    @property
    def header(self) -> str:
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
        self._define_stmt = self._define_stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return self._define_stmt.outer_text

    def set_stmt(self, stmt: Statement) -> None:
        self._define_stmt = stmt
        self._define_stmt.set_as_const_def()

    @property
    def source(self) -> str:
        rename_defines: str = "\n".join([
            f"#define {x.self_name} {x.name}" for x in self._define_stmt.new_variables
        ])
        return "\n".join(rename_defines)


class SqDef(Definition):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], outer_variables_list: list[VariableName],
                 name: str, arg_types: list[str]) -> None:
        super().__init__(src_info)
        arg_types_decl: list[TypeName] = []
        for arg_type in arg_types:
            if (arg_type, None) not in expression.SYMBOL_TABLE:
                raise CompilerException(f"Name {arg_type} is not defined.", src_info)
            arg_type = expression.SYMBOL_TABLE[arg_type, None]
            if not isinstance(arg_type, TypeName):
                raise CompilerException(f"Argument {arg_type} is not a type.", src_info)
            arg_types_decl.append(arg_type)
        decl = expression.SYMBOL_TABLE[name, tuple(arg_types_decl)]
        if not isinstance(decl, FunctionName):
            raise CompilerException(f"Name {name} is not a function.", src_info)
        self._self_name: str = decl.self_name
        self._decl = decl
        self._outer_variables: dict[VariableName, VariableState] = dict(
            map(lambda x: (x, VAR_STATE_TABLE[x]), outer_variables_list)
        )
        self._args: list[TemporaryVariableName] = list(
            map(lambda n, t: TemporaryVariableName(src_info, n, t), self._decl.arg_names, self._decl.arg_types)
        )
        self._outer_variables.update(dict(map(lambda x: (x, VariableState.ASSIGNED), self._args)))
        self._body: BlockStmt = BlockStmt(src_info, self._outer_variables)
        self._namespace: list[NamespaceName] = namespace
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._import_module: str = module_name + "$__module__"
        self._is_finished: bool = False
        self._is_from_generic: bool = False
        self._is_main: bool = name == "main"

    def add_stmt(self, stmt: Statement) -> None:
        self._body.add_stmt(stmt)

    @property
    def closure_struct_setting_code(self) -> str:
        return self._body.closure_struct_setting_code

    def finish(self) -> None:
        if self._is_finished:
            raise CompilerException("Function is already finished.", self._src_info)
        self._body.indent()
        self._body.finish()
        self._is_finished = True

    @property
    def global_init_text(self) -> Optional[str]:
        return self._body.global_init_text

    @property
    def header(self) -> str:
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
        self._decl: FunctionName
        text: list[str] = [
            self._decl.as_declare() + ";",
            self._decl.as_async().as_declare() + ";"
        ]
        return "\n".join(text)

    def instantiation(self, cls_decl: ClassName, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        if not self._decl.type.is_generic:
            raise CompilerException("Function is not generic.", self._src_info)
        new_sq = deepcopy(self)
        type_args_tuple: tuple[TypeName, ...] = tuple(map(lambda x: type_args[x], cls_decl.generic_args))
        new_sq._decl = new_sq._decl.as_method(cls_decl).set_cls(
            expression.SYMBOL_TABLE.get_generic_cls_instance(cls_decl, type_args_tuple), 0
        )
        new_sq._body = new_sq._body.instantiation(type_args)
        return new_sq

    def instantiation_full(self, type_args: tuple[TypeName, ...]) -> "SqDef":
        type_args_dict: dict[GenericArgument, TypeName] = dict(zip(self._decl.type.generic_args, type_args))
        return self.instantiation_full_by_dict(type_args_dict)

    def instantiation_full_all(self) -> list["SqDef"]:
        type_args_list: list[tuple[TypeName, ...]] = expression.SYMBOL_TABLE.get_all_to_instantiate_symbols(
            self._src_info, self._decl)
        instances = list(map(lambda t: self.instantiation_full(t), type_args_list))
        return instances

    def instantiation_full_by_dict(self, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        if not self._decl.type.is_generic:
            raise CompilerException("Function is not generic.", self._src_info)
        new_sq = deepcopy(self)
        new_sq._decl = new_sq._decl.instantiation(
            expression.SYMBOL_TABLE.get_generic_func_instance(new_sq._decl, tuple(type_args)).name, type_args
        )
        new_sq._body = new_sq._body.instantiation(type_args)
        return new_sq

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def is_generic(self) -> bool:
        return self._decl.type.is_generic

    @property
    def is_main(self) -> bool:
        return self._is_main

    @property
    def is_method(self) -> bool:
        return self._decl.is_method

    @property
    def name(self) -> str:
        return self._decl.name

    def optimize(self) -> "SqDef":
        self._body = self._body.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return self._body.outer_text

    @property
    def self_name(self) -> str:
        return self._self_name

    def set_as_closure(self, name: str) -> None:
        self._body.set_as_closure(name, self._args)

    @property
    def source(self) -> str:
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([self._source(True), rename_define])

    @property
    def type(self) -> TypeName:
        return self._decl.type

    @property
    def used_variables(self) -> set[VariableName]:
        return self._body.input_variables - set(self._args)

    def _source(self, is_native_func: bool) -> str:
        self._decl: FunctionName
        if is_native_func:
            define_name: str = self._decl.as_define_name()
        else:
            define_name: str = self._decl.as_define_name_raw()
        sync_text: list[str] = [
            define_name + " {",
            self._body.head_text + (
                    "\n\r" + self._body.tail_recursive_mark) if self._body.tail_recursive_mark is not None else "",
            self._body.text,
            "}"
        ]
        arg_tuple_name: TupleTypeName = TupleTypeName(self._src_info, self._decl.arg_types)
        ret_tuple_name: TupleTypeName = TupleTypeName(self._src_info, self._decl.ret_types)
        arg_unpack_expr: UnpackExpr = UnpackExpr(self._src_info, VariableRef(self._src_info, TemporaryVariableName(
            self._src_info, "params", arg_tuple_name
        )))
        arg_unpack_stmt: DeclStmt = DeclStmt(self._src_info, self._namespace)
        arg_unpack_stmt.set_var_value(arg_unpack_expr)
        arg_unpack_stmt.set_vars_with_known_type(self._decl.arg_names, self._decl.arg_types,
                                                 [False] * len(self._decl.arg_names))
        arg_unpack_stmt.finish()
        arg_unpack_stmt.indent()
        ret_unpack_expr: UnpackExpr = UnpackExpr(self._src_info, VariableRef(self._src_info, TemporaryVariableName(
            self._src_info, "returns", ret_tuple_name
        )))
        ret_unpack_stmt: DeclStmt = DeclStmt(self._src_info, self._namespace)
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
        try_stmt: TryStmt = TryStmt(self._src_info)
        try_inner: CStmt = CStmt(self._src_info)
        try_inner.set_text("\n".join([
            arg_unpack_stmt.text,
            ret_unpack_stmt.text,
            sync_call_text,
            f"{STACK_B_POP_FUNC}(listener->currentThreadId);"
        ]))
        try_stmt.set_try_stmt(try_inner)
        catch_stmt: CatchStmt = CatchStmt(self._src_info)
        # noinspection PyTypeChecker
        catch_var: VariableName = TemporaryVariableName(self._src_info, "exc",
                                                        expression.SYMBOL_TABLE[EXCEPTION_T_NAME, None])
        catch_stmt.set_except_decl(catch_var)
        catch_inner: BlockStmt = BlockStmt(self._src_info, self._outer_variables | {catch_var: VariableState.ASSIGNED})
        catch_inner_print: OpStmt = OpStmt(self._src_info)
        catch_inner_print_call: CallOp = CallOp(self._src_info)
        catch_inner_what_attr: AttrOp = AttrOp(self._src_info)
        catch_inner_what_attr.set_attr("what")
        catch_inner_what_attr.set_caller(VariableRef(self._src_info, catch_var))
        catch_inner_what_call: CallOp = CallOp(self._src_info)
        catch_inner_what_call.set_func(catch_inner_what_attr)
        catch_inner_print_call.add_arg(catch_inner_what_call, None)
        # noinspection PyTypeChecker
        catch_inner_print_func: VariableRef = VariableRef(self._src_info, expression.SYMBOL_TABLE[
            PERROR_FUNC_NAME, (ArrayTypeName(self._src_info, StringTypeName),)])
        catch_inner_print_call.set_func(catch_inner_print_func)
        catch_inner_print.set_expr(catch_inner_print_call)
        catch_inner.add_stmt(catch_inner_print)
        catch_inner_assign: CStmt = CStmt(self._src_info)
        catch_inner_assign.set_text("listener->exc = exc;")
        catch_inner.add_stmt(catch_inner_assign)
        catch_inner.finish()
        catch_stmt.set_stmt(catch_inner)
        try_stmt.add_except_stmt(catch_stmt)
        try_stmt.finish()
        try_stmt.indent()
        async_text: list[str] = [
            self._decl.as_async().as_declare() + " {",
            try_stmt.text,
            "}"
        ]
        text = [*sync_text, "", *async_text]
        return "\n".join(text)


class ConstructorDef(SqDef):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], outer_variables_list: list[VariableName],
                 cls_name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, namespace, outer_variables_list, f"{cls_name}.__new__", arg_types)
        cls = expression.SYMBOL_TABLE[cls_name, None]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"Name {cls_name} is not a class.", src_info)
        if len(self._decl.ret_names) != 1:
            raise CompilerException("Constructor must return exactly one value.", self._src_info)
        if self._decl.ret_types[0] != cls:
            raise CompilerException("Constructor must return a value of the same type as the class.", self._src_info)
        this_name: str = "_this"
        this_type: ClassName = cls
        self._this_var: TemporaryVariableName = TemporaryVariableName(self._src_info, this_name, this_type)
        this_alloc_stmt: CStmt = CStmt(src_info)
        this_alloc_stmt.set_text(
            f"{self._this_var.type_name_pair_calling} = ({cls.c_calling_name})malloc(sizeof({cls.c_alloc_name}));")
        self.add_stmt(this_alloc_stmt)

    def add_stmt(self, stmt: Statement) -> None:
        if self._this_var in stmt.input_variables:
            raise CompilerException("Statements in constructor should be static.", stmt._src_info)
        if self._this_var in stmt.new_variables:
            raise CompilerException("The object to be created can not be assigned directly.", stmt._src_info)
        super().add_stmt(stmt)

    @property
    def this_var(self) -> TemporaryVariableName:
        return self._this_var


class DestructorDef(SqDef):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], outer_variables_list: list[VariableName],
                 cls_name: str) -> None:
        super().__init__(src_info, namespace, outer_variables_list, f"{cls_name}.__del__", [])
        cls = expression.SYMBOL_TABLE[cls_name]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"Name {cls_name} is not a class.", src_info)
        self._this_var: TemporaryVariableName = TemporaryVariableName(self._src_info, self._decl.arg_names[0],
                                                                      self._decl.arg_types[0])
        if cls.is_c_part:
            return
        this_free_stmt: CStmt = CStmt(src_info)
        properties_to_free: list[VariableName] = list(filter(lambda y: y.is_object, cls.properties.values()))
        free_texts: list[str] = []
        for x in properties_to_free:
            attr_op: AttrOp = AttrOp(src_info)
            attr_op.set_attr("__del__")
            attr_op.set_caller(VariableRef(src_info, x))
            call_op: CallOp = CallOp(src_info)
            call_op.set_func(attr_op)
            call_op.set_returns([])
            free_call_text = call_op.front_text.split("\n")
            free_call_text = list(map(lambda y: "\t\t\t\t" + y, free_call_text))
            free_text_item: str = "\n".join([
                f"\t\tif ({self._this_var.name}->{x.name}) {{",
                f"\t\t\t{self._this_var.name}->{x.name}->refCount--;",
                f"\t\t\tif ({self._this_var.name}->{x.name}->refCount == 0) {{",
                "\n".join(free_call_text),
                "\t\t\t}"
                "\t\t}"
            ])
            free_texts.append(free_text_item)
        free_text: list[str] = [
            f"if ({self._this_var.name}->refCount == 0) {{",
            f"\tif ({self._this_var.name}->parent) {{",
            f"\t\t{self._this_var.name}->parent->refCount--;",
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

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], outer_variables_list: list[VariableName],
                 name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, namespace, outer_variables_list, name, arg_types)
        self._body: FnBlockStmt = FnBlockStmt(self._src_info, self._outer_variables)


class CPartSqDef(SqDef):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], outer_variables_list: list[VariableName],
                 name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, namespace, outer_variables_list, name, arg_types)

    def add_stmt(self, stmt: CStmt) -> None:
        self._body.add_stmt(stmt)

    @property
    def source(self) -> str:
        outer_text: str = self._body.outer_text if self._body.outer_text is not None else ""
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n".join([outer_text, self._source(False), rename_define])


class GlobalDef(CPartSqDef):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName]) -> None:
        super().__init__(src_info, namespace, [], "__global__", [])

    def add_stmt(self, stmt: CStmt) -> None:
        stmt.remove_mark()
        super().add_stmt(stmt)

    @property
    def header_no_wrap(self) -> str:
        return self._decl.as_declare() + ";"

    @property
    def header(self) -> str:
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

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str,
                 global_variables: dict[VariableName, VariableState]) -> None:
        super().__init__(src_info)
        self._self_name: str = name
        self._namespace: list[NamespaceName] = namespace
        # noinspection PyTypeChecker
        self._decl: ClassName = expression.SYMBOL_TABLE[name]
        if not isinstance(self._decl, ClassName):
            raise CompilerException(f"{name} is not a class.", src_info)
        self._global_vars: dict[VariableName, VariableState] = global_variables
        self._this_var: VariableName = TemporaryVariableName(self._src_info, "_this", self._decl)
        self._methods: dict[str, SqDef] = {}
        self._static_properties: dict[PropertyVariableName, Expression] = {}
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._import_module: str = module_name + "$__module__"
        self.add_method(DestructorDef(self._src_info, self._namespace, list(self._global_vars.keys()), name))
        self._vtable_name: str = self._decl.vtable_name
        self._parent_vtable_name: str = f"{self._decl.parent}$$vtable" if self._decl.parent != "object" else "NULL"
        self._is_finished: bool = False
        self._is_from_generic: bool = False

    def add_method(self, method: SqDef) -> None:
        self._decl: ClassName
        if method.self_name in self._methods:
            raise CompilerException(f"{method.self_name} is already defined.", method._src_info)
        if method.self_name not in self._decl.methods:
            raise CompilerException(f"{method.self_name} is not a method of {self._self_name}.", method._src_info)
        self._methods[method.self_name] = method

    def add_static_prop(self, name: str, value: Expression) -> None:
        if name not in self._decl.properties:
            raise CompilerException(f"{name} is not a property of {self._self_name}.", value.src_info)
        if name in self._decl.properties:
            raise CompilerException(f"{name} is already defined.", value.src_info)
        self._static_properties[self._decl.properties[name]] = value

    @property
    def decl(self) -> ClassName:
        return self._decl

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException("ClassDef is already finished", self._src_info)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
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
        ) + list(
            filter(lambda x: x is not None, map(lambda x: x.front_text, self._decl.properties.values()))
        )
        result: list[str] = [
            f"{self._vtable_name}.parent = {self._parent_vtable_name};",
            f"{self._vtable_name}.vfunc = {vfunc_text};",
            *vfunc_assign,
            *static_props_global_text,
            *methods_global_text
        ]
        return "\n".join(result)

    @property
    def header(self) -> str:
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
        if not self._decl.is_generic:
            raise CompilerException("ClassDef.instantiation called on non-generic class", self._src_info)
        new_cls = deepcopy(self)
        new_cls._decl = expression.SYMBOL_TABLE.get_generic_cls_instance(new_cls._decl, tuple(type_args))
        type_args_dict: dict[GenericArgument, TypeName] = dict(zip(self._decl.generic_args, type_args))
        new_cls._methods = dict(
            map(lambda x: (x.self_name, x.instantiation(self._decl, type_args_dict)), self._methods.values())
        )
        new_cls._is_from_generic = True
        return new_cls

    def instantiation_full_all(self) -> list["ClassDef"]:
        type_args_list: list[tuple[TypeName, ...]] = expression.SYMBOL_TABLE.get_all_to_instantiate_symbols(
            self._src_info, self._decl)
        instances = list(map(lambda t: self.instantiation(t), type_args_list))
        return instances

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def is_generic(self) -> bool:
        return self._decl.is_generic

    def optimize(self) -> "ClassDef":
        for k, v in self._methods.items():
            self._methods[k] = v.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        methods_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._methods.values())))
        props_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._static_properties.values())))
        result: str = "\n".join([methods_result, props_result])
        return result if result != "" else None

    @property
    def source(self) -> str:
        methods_def: list[str] = list(map(lambda x: x.source, self._methods.values()))
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        return "\n\n".join(methods_def + [rename_define])

    @property
    def _vfunc_def(self) -> list[str]:
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


class FromImportDef(Definition):

    def __init__(self, src_info: SourceInfo, root_path: str, module_path: str, def_name: list[str]) -> None:
        super().__init__(src_info)
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
        abs_path: str = os.path.abspath(os.path.join(self._root_path, self._module_path))
        rel_path_about_root: str = os.path.relpath(abs_path, self._root_path)
        return rel_path_about_root.replace(os.pathsep, "$")


class Closure(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._var_name: str = expression.SYMBOL_TABLE.get_counter()
        self._sq_def: Optional[SqDef] = None
        self._inline_mapping: dict[str, str] = {}

    def as_async(self) -> "Expression":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._inline_mapping = inline_mapping
        new_expr._inline_mapping[self._var_name] = expression.SYMBOL_TABLE.get_counter()
        new_expr._var_name = new_expr.inline_mapping[self._var_name]
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    @property
    def front_text(self) -> Optional[str]:
        result: list[str] = [
            self._sq_def.closure_struct_setting_code,
            f"{self._var_name} = ({CLOSURE_T} *)malloc(sizeof({CLOSURE_T}));",
            f"{self._var_name}->func = {self._sq_def.name};",
            f"{self._var_name}->capture = {self._var_name}$$capture;"
        ]
        return "\n".join(result)

    @property
    def global_init_text(self) -> Optional[str]:
        return self._sq_def.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return f"{CLOSURE_T} *{self._var_name};"

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: Closure = deepcopy(self)
        new_expr._sq_def = self._sq_def.instantiation_full_by_dict(type_args)
        return new_expr

    def optimize(self) -> "Expression":
        self._sq_def = self._sq_def.optimize()
        return self

    @property
    def outer_text(self) -> str:
        return self._sq_def.source

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._var_name}->refCount == 0) {{",
            f"\tif ({self._var_name}->parent) {{",
            f"\t\t{self._var_name}->parent->refCount--;",
            "\t} else {",
            f"\t\tfree({self._var_name});",
            f"\t\t{self._var_name} = NULL;",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._sq_def.type

    def set_definition(self, sq_def: "SqDef") -> None:
        sq_def.set_as_closure(self._var_name)
        self._sq_def = sq_def

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        return self._var_name

    @property
    def used_variables(self) -> set[VariableName]:
        return self._sq_def.used_variables

    def validate(self) -> None:
        if not self._sq_def.is_finished:
            raise CompilerException("Closure is not finished.", self._sq_def.src_info)


class GenericCall(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._generic_symbol: Optional[FunctionName | ClassName | MethodName] = None
        self._type_args: list[TypeName] = []
        self._instance: Optional[FunctionName | ClassName | MethodName] = None
        self._is_finished: bool = False

    def add_type_arg(self, t: TypeName) -> None:
        self._type_args.append(t)

    def as_async(self) -> "Expression":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        return self

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    def finish(self) -> None:
        if self._generic_symbol is None:
            raise InternalCompilerException("The generic type is not specified", self._src_info)
        if len(self._type_args) == 0:
            raise CompilerException("Type arguments should not be empty", self._src_info)
        # noinspection PyTypeChecker
        self._instance = expression.SYMBOL_TABLE.get_generic_instance(self._generic_symbol, tuple(self._type_args))
        self._is_finished = True

    @property
    def front_text(self) -> Optional[str]:
        return None

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def inline_mapping(self) -> dict[str, str]:
        return {}

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr = deepcopy(self)
        # noinspection PyTypeChecker
        new_expr._type_args = list(map(lambda t: type_args[t] if t in type_args else t, self._type_args))
        return new_expr

    def optimize(self) -> "Expression":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        if isinstance(self._generic_symbol, ClassName):
            return self._generic_symbol
        return self._generic_symbol.type

    def set_generic_symbol(self, symbol: FunctionName | ClassName | MethodName) -> None:
        self._generic_symbol = symbol

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        return self._instance.name

    @property
    def used_variables(self) -> set[VariableName]:
        return set()

    def validate(self) -> None:
        if not self._is_finished:
            raise CompilerException("Generic call is not finished", self._src_info)


class EnumDef(Definition):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str) -> None:
        super().__init__(src_info)
        self._namespace: list[NamespaceName] = namespace
        self._name: str = name
        self._decl = expression.SYMBOL_TABLE[name, None]
        if not isinstance(self._decl, EnumName):
            raise CompilerException(f"{name} is not an enum.", src_info)
        self._based_type: TypeName = self._decl.based_type
        self._enum: list[tuple[GlobalVariableName, Expression]] = []
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._is_finished: bool = False

    def add_enum(self, name: str, expr: Expression) -> None:
        if not expr.return_type.convertable_to(self._based_type, expression.SYMBOL_TABLE.symbols):
            raise CompilerException(f"{expr.return_type} is not convertable to {self._based_type}.", self._src_info)
        var: GlobalVariableName = GlobalVariableName(self._src_info, self._decl.as_namespace(), name, self._based_type)
        self._enum.append((var, expr))

    def finish(self) -> None:
        if self._is_finished:
            raise CompilerException("Enum is already finished.", self._src_info)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
        front_text: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].front_text, self._enum)))
        result: list[str] = list(map(lambda x: f"{x[0].name} = {x[1].text};", self._enum))
        expr_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x[1].global_init_text, self._enum)))
        return "\n".join(front_text + expr_global_text + result)

    @property
    def header(self) -> str:
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
        result: list[str] = list(map(lambda x: f"extern {x[0].type_name_pair_calling};", self._enum))
        return "\n".join(result)

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    def optimize(self) -> "Definition":
        for i, (name, value) in enumerate(self._enum):
            self._enum[i] = (name, value.optimize())
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n".join(map(lambda x: x[1].outer_text, self._enum))
        return result if result != "" else None

    @property
    def source(self) -> str:
        return f"// ENUM: {self._name}"
