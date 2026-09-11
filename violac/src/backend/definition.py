# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import UnpackExpr, VariableRef, Expression, CallOp, AttrOp, ClassRef, TypeRef
from .statement import Statement, BlockStmt, DeclStmt, FnBlockStmt, CStmt, TryStmt, CatchStmt, OpStmt, ReturnStmt, \
    STACK_B_POP_FUNC, CleanupBlock
from .symbol import FunctionName, VariableName, LocalVariableName, VariableState, TupleTypeName, NamespaceName, \
    ClassName, MethodName, FUNCTION_T, FUNCTION_ASYNC_PTR_T, FUNCTION_SYNC_PTR_T, TypeName, EXCEPTION_T_NAME, \
    EnumName, GlobalVariableName, GenericArgument, \
    StringTypeName, PropertyVariableName, SymbolTable, VariableStateTable, FunctionTypeName, Object, LISTENER_T, \
    VIOLA_IO, VOID_PTR
from utils import CompilerException, SourceInfo, InternalCompilerException

from abc import ABC, abstractmethod
from copy import copy, deepcopy
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

    def finish(self) -> None:
        """完成常量定义的构建（语句已在set_stmt时完整构建）。"""
        if self._define_stmt is None:
            raise InternalCompilerException("ConstDef has not been set with a statement.", self._src_info)

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
        return rename_defines


class SqDef(Definition):
    """函数定义，表示一个可执行的函数（含参数和函数体）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str],
                 decl: Optional[FunctionName] = None) -> None:
        """
        初始化函数定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param name: 函数名。
        :param arg_types: 参数类型列表。
        :param decl: 可选的函数声明。匿名函数（闭包）没有符号表条目，
            由调用方直接提供声明，跳过符号表查找。
        """
        super().__init__(src_info, symbol_table)
        arg_types_decl: list[TypeName] = []
        # 泛型函数/泛型类方法的泛型参数：在解析参数类型前注册（如T[]需要T可用）
        generic_names: list[str] = []
        name_decl = None
        if decl is None:
            try:
                name_decl = symbol_table[name, None]
            except CompilerException:
                name_decl = None
            if name_decl is None:
                # 重载函数没有按名称的查找键：从类型键中取第一个同名声明
                for (k_name, _), v in symbol_table.symbols.items():
                    if k_name == name and isinstance(v, (FunctionName, MethodName)) and \
                            v.type.generic_args_str is not None:
                        name_decl = v
                        break
        if name_decl is not None and isinstance(name_decl, (FunctionName, MethodName)) and \
                name_decl.type.generic_args_str is not None:
            generic_names = list(filter(lambda x: x != "", name_decl.type.generic_args_str))
        elif decl is None and "." in name:
            try:
                cls_decl = symbol_table[name.split(".")[0], None]
                if isinstance(cls_decl, ClassName) and cls_decl.is_generic:
                    generic_names = list(map(lambda g: g.name, cls_decl.generic_args))
            except CompilerException:
                pass
        registered_args: list[GenericArgument] = []
        for generic_name in generic_names:
            arg_obj = GenericArgument(src_info, generic_name)
            symbol_table.add(arg_obj, arg_obj.name, None)
            registered_args.append(arg_obj)
        try:
            for arg_type in arg_types:
                try:
                    # 符号表查找支持复合类型名（如T[]、函数类型）的类型名解析器回退
                    arg_type = self._symbol_table[arg_type, None]
                except CompilerException:
                    raise CompilerException(f"Name {arg_type} is not defined.", src_info)
                if not isinstance(arg_type, TypeName):
                    raise CompilerException(f"Argument {arg_type} is not a type.", src_info)
                arg_types_decl.append(arg_type)
        finally:
            for arg_obj in registered_args:
                symbol_table.remove(arg_obj.name)
        if decl is None:
            decl = self._symbol_table[name, tuple(arg_types_decl)]
        self._method_decl: Optional[MethodName] = decl if isinstance(decl, MethodName) else None
        if not isinstance(decl, FunctionName | MethodName):
            raise CompilerException(f"Name {name} is not a function.", src_info)
        self._self_name: str = decl.self_name
        self._decl = decl if isinstance(decl, FunctionName) else decl.as_function()
        self._is_native: bool = self._decl.is_native
        self._var_states: VariableStateTable = var_states
        self._outer_variables: dict[VariableName, VariableState] = var_states.state
        self._args: list[LocalVariableName] = list(
            map(lambda n, t: LocalVariableName(src_info, n, t), self._decl.arg_names, self._decl.arg_types)
        )
        for arg in self._args:
            symbol_table.add(arg, arg.name, None)
            # 参数与返回值注册到变量状态表，使函数体语句块的外层变量快照
            # 包含它们（fn的依赖排序与块内释放逻辑依赖该快照）
            var_states[arg] = VariableState.ASSIGNED
        self._rets: list[LocalVariableName] = list(
            map(lambda n, t: LocalVariableName(src_info, n, t), self._decl.ret_names, self._decl.ret_types)
        )
        for ret in self._rets:
            # 返回值槽位在C层为指针形参，赋值与读取时解引用
            ret.is_return = True
            symbol_table.add(ret, ret.name, None)
            var_states[ret] = VariableState.DECLARED
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
        self._is_closure: bool = False
        self._async_body = None
        self._default_params: dict[str, Expression] = {}
        # noinspection PyTypeChecker
        generic_args: list[GenericArgument] = self._decl.type.generic_args if self._decl.type.generic_args is not None else []
        for arg in generic_args:
            self._symbol_table.add(arg, arg.name, None)

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
        if not self._is_native and \
                list(self._default_params.keys()) != list(self._decl.default_params.keys()):
            raise InternalCompilerException("Some default parameters has not been set.", self._src_info)
        self._check_return_stmts()
        self._var_states.add_scope()
        if self._is_native or (self._method_decl is not None and self._method_decl.cls is not None and
                               self._method_decl.cls.is_generic):
            # 原生函数的实现由运行库提供，不生成同步函数体与异步包装体；
            # 泛型类的方法：泛型参数未实例化，异步包装体推迟到实例化时构建
            self._async_body = None
        else:
            self._async_body = self._get_async_body()
        self._var_states.pop_scope()
        if not self._is_native and not isinstance(self._body, FnBlockStmt) and len(self._rets) <= 1 and \
                len(getattr(self._body, "_stmt", [])) > 0:
            # 尾递归优化（0.1起）：顺序执行体中的尾递归调用转换为goto循环
            # （fn的按需执行体经依赖排序后无固定顺序，不适用）
            self._body = self._body.check_tail_recursive(self._decl.name)
        self._body.indent()
        self._body.finish()
        self._is_finished = True

    def _check_return_stmts(self) -> None:
        """检查每个return语句处所有返回值变量是否均已赋值（0.1要求），
        并检查返回值不得为unsafe变量。"""
        if len(self._rets) == 0:
            return
        # unsafe变量不得被返回（0.1要求）：unsafe成员、unsafe类实例
        # 与指针（Pointer类型天然unsafe）均不可作为返回值。
        # 例外：构造函数返回的this即新建的实例本身——unsafe类的对象必须
        # 经由构造函数创建，否则unsafe类无法实例化（与计划的类前缀语义冲突）
        if isinstance(self, ConstructorDef):
            return
        for ret in self._rets:
            is_unsafe_var: bool = getattr(ret, "is_unsafe", False) or \
                getattr(ret.type, "is_unsafe", False)
            if is_unsafe_var:
                raise CompilerException(
                    f"unsafe variable {ret.name} can not be returned.", self._src_info)
        states: dict[VariableName, VariableState] = {}

        def walk(stmt: Statement) -> None:
            if isinstance(stmt, ReturnStmt):
                for ret in self._rets:
                    state: VariableState = states.get(ret, VariableState.UNDECLARED)
                    if state in (VariableState.UNDECLARED, VariableState.DECLARED):
                        raise CompilerException(
                            f"Return value {ret.name} is not assigned when returning.", stmt.src_info)
                return
            states.update(stmt.variables_states)
            for attr_name in ("_stmt", "_try_stmt", "_except_stmt", "_finally_stmt", "_branches"):
                children = getattr(stmt, attr_name, None)
                if children is None:
                    continue
                if isinstance(children, list):
                    for child in children:
                        if isinstance(child, Statement):
                            walk(child)
                elif isinstance(children, Statement):
                    walk(children)

        for stmt in self._body._stmt:
            walk(stmt)

    @property
    def global_init_text(self) -> Optional[str]:
        """获取函数的全局初始化代码文本。"""
        if self._async_body is None:
            # 原生函数或泛型类方法：不生成异步包装体的初始化文本
            results = list(filter(lambda x: x is not None, [self._body.global_init_text]))
        else:
            results = list(filter(lambda x: x is not None, [self._body.global_init_text, self._async_body.global_init_text]))
        # 默认参数的初始化赋值（原生函数的默认值由运行库定义）
        default_init: str = "" if self._is_native else self._get_default_params_init()
        if default_init.strip() != "":
            results.append(default_init)
        return "\n".join(results)

    @property
    def header(self) -> str:
        """获取函数在头文件中的声明文本。"""
        if self._is_from_generic:
            return "// GENERIC FUNCTION"
        if self._decl.export:
            # export声明的符号可被链接：直接在头文件中暴露
            return self.header_no_wrap
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
        if self._is_native:
            # 原生函数只输出同步声明（运行库未提供异步变体）
            text: list[str] = [self._decl.as_declare() + ";"]
        else:
            text: list[str] = [
                self._decl.as_declare() + ";",
                self._decl.as_async().as_declare() + ";"
            ]
        # 默认参数全局变量的外部声明（其他模块调用默认参数时引用）
        text += [f"extern {v.type_name_pair_calling};" for v in self._decl.default_params.values()]
        return "\n".join(text)

    def instantiation(self, cls_decl: ClassName, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        """将函数作为类方法进行泛型实例化。"""
        new_sq = deepcopy(self)
        type_args_tuple: tuple[TypeName, ...] = tuple(map(lambda x: type_args[x], cls_decl.generic_args))
        inst_cls = self._symbol_table.get_generic_cls_instance(cls_decl, type_args_tuple)
        new_sq._method_decl = self._method_decl.set_cls(inst_cls, 0)
        # 将原类到实例化类的映射也加入 type_args，使 this 的类型被替换
        type_args_with_cls = dict(type_args)
        type_args_with_cls[GenericArgument(self._src_info, cls_decl.name)] = inst_cls
        new_sq._decl = self._method_decl.as_function().instantiation(
            new_sq._method_decl.as_function().name, type_args_with_cls
        )
        new_sq._body = new_sq._body.instantiation(type_args_with_cls)
        # 异步包装体在finish时以原泛型参数类型构建，实例化后需用具体类型重建
        new_sq._async_body = new_sq._get_async_body()
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
            self._symbol_table.get_generic_func_instance(new_sq._decl, tuple(type_args.values())).self_name,
            type_args
        )
        # 参数与返回值变量的类型同样需要实例化（供清理代码等使用）
        new_sq._args = [a.instantiation(a.name, type_args) for a in new_sq._args]
        new_sq._rets = [r.instantiation(r.name, type_args) for r in new_sq._rets]
        new_sq._body = new_sq._body.instantiation(type_args)
        # 语句块的新变量列表同样需要实例化（供清理代码使用）
        new_sq._body._new_variables = [v.instantiation(v.name, type_args)
                                       for v in new_sq._body._new_variables]
        # 异步包装体在finish时以原泛型参数类型构建，实例化后需用具体类型重建
        new_sq._async_body = new_sq._get_async_body()
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
        async_outer: Optional[str] = self._async_body.outer_text if self._async_body is not None else None
        # 原生函数的默认参数全局变量由运行库定义，不生成声明
        default_decl: str = "" if self._is_native else self._get_default_params_decl()
        results = list(filter(lambda x: x is not None, [self._body.outer_text, async_outer, default_decl]))
        return "\n".join(results)

    @property
    def self_name(self) -> str:
        """获取函数在 Viola 中的别名。"""
        return self._self_name

    def set_as_closure(self, name: str) -> None:
        """将函数设置为闭包，绑定捕获结构体。"""
        self._is_closure = True
        self._body.set_as_closure(name, self._args)
        if self._async_body is not None:
            # 异步包装体在finish时先于闭包标记生成，需要按闭包约定
            # （捕获环境作为参数元组末尾元素）重建
            self._async_body = self._get_async_body()

    def set_default_param(self, param_name: str, default_value: Expression) -> None:
        if param_name not in self._decl.default_params:
            raise InternalCompilerException(f"Parameter '{param_name}' is not a default parameter.", self._src_info)
        if param_name in self._default_params:
            raise CompilerException(f"Default parameter '{param_name}' has already been set.", self._src_info)
        self._default_params[param_name] = default_value

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

    def _get_default_params_decl(self) -> str:
        # noinspection PyTypeChecker
        return "\n".join(
            [v.outer_text for v in self._default_params.values() if v.outer_text is not None] +
            [v.type_name_pair_calling + ";" for v in self._decl.default_params.values()]
        )

    def _get_default_params_init(self) -> str:
        """获取函数的默认参数初始化文本。"""
        results: list[str] = []
        for k in self._decl.default_params:
            global_init_text = self._default_params[k].global_init_text
            if global_init_text is not None:
                results.append(global_init_text)
            head_text = self._default_params[k].head_text
            if head_text is not None:
                results.append(head_text)
            front_text = self._default_params[k].front_text
            if front_text is not None:
                results.append(front_text)
            results.append(f"{self._decl.default_params[k].name} = {self._default_params[k].text};")
        return "\n".join(results)

    def _source(self, is_native_func: bool) -> str:
        """生成函数的 C 源代码文本。"""
        self._decl: FunctionName
        if self._is_native:
            # 原生函数：实现由运行库提供，不生成函数体
            return f"// native function {self._decl.raw_name}"
        if is_native_func:
            define_name: str = self._decl.as_define_name()
        else:
            define_name: str = self._decl.as_define_name_raw()
        async_define_name: str = self._decl.as_async().as_define_name()
        if self._is_closure:
            # 闭包函数额外接收捕获结构体指针形参；
            # 异步包装函数的捕获环境作为参数元组的末尾元素传入
            # （与Function结构体的asyncPtr调用约定一致）
            define_name = define_name[:-1] + ", void *$$capture)"
            closure_args_tuple: TupleTypeName = TupleTypeName(self._src_info, self._decl.arg_types + [VOID_PTR])
            closure_rets_tuple: TupleTypeName = TupleTypeName(self._src_info, self._decl.ret_types)
            async_define_name = f"void {self._decl.name}$async({closure_args_tuple.c_calling_name} params, " \
                                f"{closure_rets_tuple.c_calling_name} returns, {LISTENER_T} *listener)"
        sync_text: list[str] = [
            define_name + " {",
            (self._body.head_text or "") + ("\n\r" + self._body.tail_recursive_mark)
            if self._body.tail_recursive_mark is not None else self._body.head_text or "",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exc;",
            self._body.text,
            CleanupBlock(self._src_info, self._symbol_table, self._var_states, list(self._body.new_variables)).text,
            "}"
        ]
        async_text: list[str] = [
            async_define_name + " {",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exc;",
            self._async_body.text,
            "$$cleanup: ;",
            "}"
        ]
        text = [*sync_text, "", *async_text]
        return "\n".join(text)

    def _get_async_body(self) -> TryStmt:
        """生成异步函数体，包含参数解包、同步函数调用和异常处理。

        闭包的异步包装函数按Function结构体的asyncPtr调用约定生成：
        捕获环境作为参数元组的末尾元素传入。
        """
        if self._is_closure:
            async_arg_types: list[TypeName] = self._decl.arg_types + [VOID_PTR]
            async_arg_names: list[str] = self._decl.arg_names + ["$$capture"]
        else:
            async_arg_types = self._decl.arg_types
            async_arg_names = self._decl.arg_names
        arg_tuple_name: TupleTypeName = TupleTypeName(self._src_info, async_arg_types)
        ret_tuple_name: TupleTypeName = TupleTypeName(self._src_info, self._decl.ret_types)
        arg_unpack_expr: UnpackExpr = UnpackExpr(self._src_info, self._symbol_table,
                                                 VariableRef(self._src_info, self._symbol_table, LocalVariableName(
                                                     self._src_info, "params", arg_tuple_name
                                                 )))
        arg_unpack_stmt: DeclStmt = DeclStmt(self._src_info, self._symbol_table, self._var_states, self._namespace)
        arg_unpack_stmt.set_var_value(arg_unpack_expr)
        arg_unpack_stmt.set_vars_with_known_type(async_arg_names, async_arg_types,
                                                 [False] * len(async_arg_names))
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
        sync_call_args_text: str = ", ".join(self._decl.arg_names)
        sync_call_rets_text: str = ", ".join(map(lambda x: f"&{x}", self._decl.ret_names))
        if sync_call_args_text != "" and sync_call_rets_text != "":
            sync_call_params_text: str = f"{sync_call_args_text}, {sync_call_rets_text}"
        else:
            sync_call_params_text: str = sync_call_args_text + sync_call_rets_text
        if sync_call_params_text != "":
            sync_call_params_text: str = f"{sync_call_params_text}, listener"
        else:
            sync_call_params_text: str = "listener"
        if self._is_closure:
            # 闭包函数需要传递捕获结构体指针
            sync_call_params_text += ", $$capture"
        sync_call_text: str = f"\t{self._decl.name}({sync_call_params_text});"
        # 将返回值写回返回元组，供调用方在waitListener之后取回
        # （返回值元组的成员与_decl.ret_names一一对应）
        ret_write_back_text: list[str] = [
            f"\treturns->${i} = {ret_name};"
            for i, ret_name in enumerate(self._decl.ret_names)
        ]
        try_stmt: TryStmt = TryStmt(self._src_info, self._symbol_table, self._var_states)
        try_inner: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
        # 解包语句的临时变量（params/returns元组指针）声明在head_text中，需一并输出。
        # 注意：text的求值会触发set_returns，因此必须先求值text再求值head_text，
        # 但输出时声明必须位于使用之前
        arg_unpack_text: str = arg_unpack_stmt.text
        ret_unpack_text: str = ret_unpack_stmt.text
        try_inner.set_text("\n".join(list(filter(lambda x: x is not None and x.strip() != "", [
            arg_unpack_stmt.head_text,
            ret_unpack_stmt.head_text,
            arg_unpack_text,
            ret_unpack_text,
            sync_call_text,
            *ret_write_back_text,
            f"{STACK_B_POP_FUNC}(listener->currentThreadId);"
        ]))))
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
        try:
            catch_inner_print_func: VariableRef = VariableRef(self._src_info, self._symbol_table, self._symbol_table[
                PERROR_FUNC_NAME, (StringTypeName,)
            ])
        except CompilerException:
            # viola.io的内置绑定已移除（开发疑问记录第40条），此处直接构造
            # perror的原生函数符号（实现位于viola_libs/viola/io/print.c）
            perror_func = FunctionName(self._src_info, VIOLA_IO, "perror",
                                       FunctionTypeName(self._src_info, [StringTypeName], []),
                                       ["text"], [], True, False, True)
            catch_inner_print_func = VariableRef(self._src_info, self._symbol_table, perror_func)
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
        this_name: str = "_thisObj"
        this_type: ClassName = cls
        self._this_var: LocalVariableName = LocalVariableName(self._src_info, this_name, this_type)
        if not self._is_native:
            # 原生构造函数（声明文件中声明的内置类构造）由运行库实现，
            # 不生成分配与vtable初始化代码
            this_alloc_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
            this_alloc_stmt.set_text(
                f"{cls.c_calling_name} {self._this_var.name} = ({cls.c_calling_name})malloc(sizeof({cls.c_alloc_name}));")
            self.add_stmt(this_alloc_stmt)
            # 初始化实例的TypeInfo指针，供异常捕获与动态类型转换使用
            this_vtable_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
            this_vtable_stmt.set_text(
                f"{self._this_var.name}->$refCount = 1;\n"
                f"{self._this_var.name}->$parent = NULL;\n"
                f"{self._this_var.name}->$$vtable = (void *)&{cls.name}$$vtable;")
            self.add_stmt(this_vtable_stmt)

    def finish(self) -> None:
        """完成构造函数，将局部this写回输出参数。"""
        if not self._is_native:
            write_back_stmt: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
            write_back_stmt.set_text(f"*_this = {self._this_var.name};")
            self.add_stmt(write_back_stmt)
        super().finish()

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

    def instantiation(self, cls_decl: ClassName, type_args: dict[GenericArgument, TypeName]) -> "ConstructorDef":
        """实例化构造函数：重建分配语句与vtable初始化语句（使用实例类的C名称）。"""
        new_def = super().instantiation(cls_decl, type_args)
        inst_cls: TypeName = new_def._decl.type.returns[0]
        this_alloc_stmt = CStmt(new_def._src_info, new_def._symbol_table, new_def._var_states)
        this_alloc_stmt.set_text(
            f"{inst_cls.c_calling_name} {new_def._this_var.name} = "
            f"({inst_cls.c_calling_name})malloc(sizeof({inst_cls.c_alloc_name}));")
        this_vtable_stmt = CStmt(new_def._src_info, new_def._symbol_table, new_def._var_states)
        this_vtable_stmt.set_text(
            f"{new_def._this_var.name}->$refCount = 1;\n"
            f"{new_def._this_var.name}->$parent = NULL;\n"
            f"{new_def._this_var.name}->$$vtable = (void *)&{inst_cls.name}$$vtable;")
        new_def._body._stmt[0] = this_alloc_stmt
        new_def._body._stmt[1] = this_vtable_stmt
        return new_def


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
        # 仅释放实例属性：静态属性是模块级全局变量，不是结构体成员
        properties_to_free: list[VariableName] = list(
            filter(lambda y: y.is_object and not y.is_static, cls.properties.values()))
        free_texts: list[str] = []
        for x in properties_to_free:
            # 类结构体的成员名为属性的self_name，访问时需要通过_this指针
            prop_var: LocalVariableName = LocalVariableName(
                src_info, f"{self._this_var.name}->{x.self_name}", x.type
            )
            attr_op: AttrOp = AttrOp(src_info, self._symbol_table)
            attr_op.set_attr("__del__")
            attr_op.set_caller(VariableRef(src_info, self._symbol_table, prop_var))
            call_op: CallOp = CallOp(src_info, self._symbol_table)
            call_op._is_internal = True
            call_op.set_func(attr_op)
            call_op.set_returns([])
            free_call_text = call_op.front_text.split("\n")
            free_call_text = list(map(lambda y: "\t\t\t\t" + y, free_call_text))
            free_text_item: str = "\n".join([
                f"\t\tif ({self._this_var.name}->{x.self_name}) {{",
                f"\t\t\t{self._this_var.name}->{x.self_name}->$refCount--;",
                f"\t\t\tif ({self._this_var.name}->{x.self_name}->$refCount == 0) {{",
                "\n".join(free_call_text),
                "\t\t\t}"
                "\t\t}"
            ])
            free_texts.append(free_text_item)
        free_text: list[str] = [
            f"if ({self._this_var.name}->$refCount == 0) {{",
            f"\tif ({self._this_var.name}->$parent) {{",
            f"\t\t((viola$lang$uint32 *){self._this_var.name}->$parent)[0]--;",
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
                 namespace: list[NamespaceName], name: str, arg_types: list[str],
                 decl: Optional[FunctionName] = None) -> None:
        """
        初始化函数定义。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        :param name: 函数名。
        :param arg_types: 参数类型列表。
        :param decl: 可选的函数声明（匿名闭包）。
        """
        super().__init__(src_info, symbol_table, var_states, namespace, name, arg_types, decl)
        self._body: FnBlockStmt = FnBlockStmt(self._src_info, self._symbol_table, var_states)


class CPartSqDef(SqDef):
    """C 语言兼容的函数定义（与 extern "C" 配合使用）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 namespace: list[NamespaceName], name: str, arg_types: list[str]) -> None:
        super().__init__(src_info, symbol_table, var_states, namespace, name, arg_types)

    def add_stmt(self, stmt: CStmt) -> None:
        """向函数体中添加 C 语句。"""
        self._body.add_stmt(stmt)

    def finish(self) -> None:
        super().finish()
        self._body.remove_mark()
        self._body.remove_jump_mark()

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
        """向全局初始化函数中添加语句，移除其调试标记与异常跳转。"""
        stmt.remove_mark()
        stmt.remove_jump_mark()
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
        define_name: str = f"void {namespace_name}$__global__(viola$threads$Listener *listener)"
        sync_text: list[str] = [
            define_name + " {",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exc;",
            self._body.text,
            "$$cleanup: ;",
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
        self._is_native: bool = self._symbol_table.is_native_class(name)
        self._global_vars: dict[VariableName, VariableState] = var_states.state
        self._this_var: VariableName = LocalVariableName(self._src_info, "_this", self._decl)
        self._methods: dict[str, SqDef] = {}
        self._static_properties: dict[PropertyVariableName, Expression] = {}
        module_name: str = "$".join(map(lambda x: x.name, self._namespace))
        self._import_name: str = module_name + "$" + name
        self._import_all: str = module_name + "$__all__"
        self._import_module: str = module_name + "$__module__"
        # wrapper类必须由用户实现__del__（export=False的__del__为用户定义；
        # 编译器自动注册的析构标记为export=True）。原生绑定类由运行库实现析构，
        # 无需检查。
        if self._decl.is_wrapper and not self._is_native:
            has_user_del: bool = any(
                m_name == "__del__" and not m.export
                for (m_name, _), m in self._decl.methods.items()
            )
            if not has_user_del:
                raise CompilerException(f"Wrapper class {name} must define sq __del__() -> ();.", self._src_info)
        # 实现接口的类必须实现接口的所有抽象方法（接口本身除外）
        if not self._decl.is_interface:
            for interface in self._decl.interfaces:
                for (m_name, _), m in interface.methods.items():
                    if not m.is_abstract or m_name == "__del__":
                        continue
                    implemented: bool = any(
                        own_name == m_name and not own_m.is_abstract
                        for (own_name, _), own_m in self._decl.methods.items()
                    )
                    if not implemented:
                        raise CompilerException(
                            f"Class {name} does not implement the abstract method "
                            f"{interface.raw_name}.{m_name}().", self._src_info)
        # 为每个类自动生成默认析构函数（释放动态属性并回收内存）。
        # c语言部分（cpart类）除外，其析构由用户通过cpart实现；
        # wrapper类由用户实现__del__，编译器生成__del__super供del(super)调用；
        # 原生绑定类的类型结构体与析构均由运行库提供，不生成任何C代码。
        self._del_super_body: Optional[str] = None
        if self._is_native:
            pass
        elif self._decl.is_wrapper:
            del_super_def = DestructorDef(self._src_info, self._symbol_table, var_states, self._namespace, name)
            del_super_def.finish()
            self._del_super_body = del_super_def._body.text
        elif not self._decl.is_c_part:
            destructor = DestructorDef(self._src_info, self._symbol_table, var_states, self._namespace, name)
            destructor.finish()
            self.add_method(destructor)
        self._vtable_name: str = self._decl.vtable_name
        # 内置类（如string）的parent为None，与object同样没有父虚函数表
        self._parent_vtable_name: str = f"{self._decl.parent.name}$$vtable" \
            if self._decl.parent is not None and self._decl.parent != Object else "NULL"
        self._is_finished: bool = False
        self._is_from_generic: bool = False
        # noinspection PyTypeChecker
        generic_args: list[GenericArgument] = self._decl.generic_args if self._decl.generic_args is not None else []
        for arg in generic_args:
            self._symbol_table.add(arg, arg.name, None)

    def add_method(self, method: SqDef) -> None:
        """向类中添加方法定义。"""
        self._decl: ClassName
        if method.self_name in self._methods:
            raise CompilerException(f"{method.self_name} is already defined.", method._src_info)
        self._methods[method.self_name] = method

    def add_static_prop(self, name: str, value: Expression) -> None:
        """向类中添加静态属性的初始值。"""
        if name not in self._decl.properties:
            raise CompilerException(f"{name} is not a property of {self._self_name}.", value.src_info)
        if self._decl.properties[name] in self._static_properties:
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
        if self._is_native:
            # 原生绑定类：虚函数表与静态属性由运行库定义
            return ""
        # 0.1：虚函数表仅提供类型链信息（convertibleTo），不进行虚方法分发
        vfunc_text: str = "NULL"
        vfunc_assign: list[str] = []
        # noinspection PyUnresolvedReferences
        methods_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x.global_init_text, self._methods.values()))
        )
        static_props_global_text: list[str] = list(filter(
            lambda x: x is not None,
            [text for prop, value in self._static_properties.items()
             for text in [
                 value.global_init_text,
                 value.head_text,
                 value.front_text,
                 f"{prop.name} = {value.text};"
             ]]
        ))
        if self._parent_vtable_name == "NULL" or \
                (self._decl.parent is not None and self._decl.parent.is_generic):
            # 泛型基类的TypeInfo全局变量不会生成，其运行时父指针置空
            parent_vtable_ref: str = "NULL"
        else:
            parent_vtable_ref = f"&{self._parent_vtable_name}"
        result: list[str] = [
            f"{self._vtable_name}.$parent = {parent_vtable_ref};",
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
        if self._is_native:
            # 原生绑定类：结构体定义由运行库头文件提供，仅输出方法声明
            return "\n".join(list(map(lambda x: x.header_no_wrap, self._methods.values())))
        if self._is_from_generic:
            # 泛型实例化类：直接输出结构体定义与方法声明（其C类型名由实例化产生，
            # 无需导入守卫）
            return self.header_no_wrap
        if self._decl.export:
            # export声明的类可被链接：直接在头文件中暴露
            return self.header_no_wrap
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
        if self._is_native:
            # 原生绑定类：结构体定义由运行库头文件提供，仅输出方法声明
            return "\n".join(list(map(lambda x: x.header_no_wrap, self._methods.values())))
        class_info_text: str = f"extern {TYPE_INFO_T} {self._vtable_name};"
        # noinspection PyUnresolvedReferences
        properties_text: str = "\n".join(
            map(
                lambda x: f"\t{x.type.c_calling_name} {x.self_name};",
                filter(lambda x: not x.is_static, self._decl.ordered_properties)
            )
        )
        struct_def: list[str] = [
            class_info_text,
            f"\ntypedef struct {self._decl.name} {{",
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
            # 结构体typedef在前，虚函数表结构体（引用类类型）在后
            result_def = struct_def
            vfunc_def = self._vfunc_def.copy()
            if len(vfunc_def) > 0:
                result_def.append("")
                result_def.extend(vfunc_def)
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
        # 虚函数表名随实例化的类名变化，需重新计算
        new_cls._vtable_name = new_cls._decl.vtable_name
        new_cls._parent_vtable_name = f"{new_cls._decl.parent.name}$$vtable" \
            if new_cls._decl.parent != Object else "NULL"
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
        """获取类的外层代码文本（虚函数表定义、方法和静态属性的外层声明）。"""
        if self._is_native:
            # 原生绑定类：虚函数表等全局定义由运行库提供
            return None
        # 类的TypeInfo全局变量定义（在__global__中初始化$parent与vfunc）
        vtable_def: str = f"{TYPE_INFO_T} {self._vtable_name} = {{NULL, NULL}};"
        static_props_def: str = "\n".join(map(
            lambda x: f"{x.type.c_calling_name} {x.name};",
            filter(lambda x: x.is_static, self._decl.properties.values())
        ))
        methods_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._methods.values())))
        props_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._static_properties.values())))
        result: str = "\n".join([vtable_def, static_props_def, methods_result, props_result])
        return result if result != "" else None

    @property
    def source(self) -> str:
        """获取类的源代码文本。"""
        if self._is_native:
            # 原生绑定类：实现由运行库提供，不生成任何C代码
            return f"// native class {self._decl.raw_name}"
        methods_def: list[str] = list(map(lambda x: x.source, self._methods.values()))
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        if self._del_super_body is not None:
            # wrapper类的默认成员清理函数（由del(super)调用）
            helper: str = "\n".join([
                f"void {self._decl.name}$__del__super$_0({self._decl.c_calling_name} _this, "
                f"{LISTENER_T} *listener) {{",
                f"\t{EXCEPTION_T_NAME} *$$exc = listener->exc;",
                self._del_super_body,
                "$$cleanup: ;",
                "}"
            ])
            return "\n\n".join(methods_def + [helper, rename_define])
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
        self._module_abs: Optional[str] = None
        self._get_include_path()
        self._namespace = self._get_namespace()

    @property
    def imported_src_path(self) -> Optional[str]:
        """获取被导入模块的源文件路径（无扩展名部分的绝对路径+.vla）。"""
        if self._module_abs is None:
            return None
        return self._module_abs + ".vla"

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def header(self) -> str:
        include_path: str = self._module_path.replace(os.sep, "/")
        result: list[str] = [
            *[f"#define _VIOLA_IMPORT_{self._namespace}${def_name} 1" for def_name in self._def_name],
            f"#include \"{include_path}.vla.h\""
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
        # 处理相对导入（以点开头，如.from_import的相对模块）
        rel_dots: int = 0
        while self._module_path.startswith("."):
            self._module_path = self._module_path[1:]
            rel_dots += 1
        module_rel: str = self._module_path.replace(".", os.sep)
        # 在项目根与VIOLA_HOME根中寻找模块
        roots: list[str] = [self._root_path]
        if "VIOLA_HOME" in os.environ:
            roots += [r for r in os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":") if r.strip() != ""]
        module_abs: Optional[str] = None
        module_root: Optional[str] = None
        if rel_dots > 0:
            base: str = os.path.dirname(self._src_info.path)
            for _ in range(rel_dots - 1):
                base = os.path.dirname(base)
            candidate: str = os.path.join(base, module_rel)
            if os.path.exists(candidate + ".vla"):
                module_abs = candidate
                module_root = self._root_path
        if module_abs is None:
            for root in roots:
                candidate = os.path.join(root, module_rel)
                if os.path.exists(candidate + ".vla"):
                    module_abs = candidate
                    module_root = root
                    break
        if module_abs is None:
            raise CompilerException(f"{self._module_path} is not a valid module path.", self._src_info)
        self._module_abs = os.path.abspath(module_abs)
        if module_root is not None and os.path.abspath(module_root) != os.path.abspath(self._root_path):
            # 运行库模块：输出到输出目录下相对VIOLA_HOME的路径，include使用该相对路径
            self._module_path = os.path.relpath(module_abs, module_root)
        else:
            # 项目内模块：输出目录镜像项目布局，include相对于当前源文件目录
            self._module_path = os.path.relpath(module_abs, os.path.dirname(self._src_info.path))

    def _get_namespace(self) -> str:
        """获取模块路径对应的命名空间字符串。"""
        abs_path: str = os.path.abspath(os.path.join(self._root_path, self._module_path))
        rel_path_about_root: str = os.path.relpath(abs_path, self._root_path)
        return rel_path_about_root.replace(os.sep, "$")


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
        new_expr = copy(self)
        new_expr._inline_mapping = inline_mapping
        new_expr._inline_mapping[self._var_name] = self._symbol_table.get_counter()
        new_expr._var_name = new_expr.inline_mapping[self._var_name]
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        """闭包不参与尾递归优化。"""
        return self

    @property
    def front_text(self) -> Optional[str]:
        """获取闭包的前置代码（分配Function结构体）。

        0.1起闭包结构体更名为viola.lang.function.Function（原Closure），
        包含asyncPtr/syncPtr/capture/argNames四个成员。
        """
        arg_names: list[str] = self._sq_def._decl.arg_names
        arg_names_setting: list[str] = [
            f"{self._var_name}->argNames = "
            f"(viola$lang$string$$array *)malloc(sizeof(viola$lang$string$$array));",
            f"{self._var_name}->argNames->$refCount = 1;",
            f"{self._var_name}->argNames->$parent = NULL;",
            f"{self._var_name}->argNames->size = {len(arg_names)};",
            f"{self._var_name}->argNames->data = (viola$lang$string **)malloc("
            f"sizeof(viola$lang$string *) * {len(arg_names) if len(arg_names) > 0 else 1});",
        ]
        for i, n in enumerate(arg_names):
            arg_names_setting.append(
                f"{self._var_name}->argNames->data[{i}] = viola$lang$string$fromCharString(\"{n}\");")
        result: list[str] = [
            self._sq_def.closure_struct_setting_code,
            f"{self._var_name} = ({FUNCTION_T} *)malloc(sizeof({FUNCTION_T}));",
            f"{self._var_name}->$refCount = 1;",
            f"{self._var_name}->$parent = NULL;",
            f"{self._var_name}->asyncPtr = ({FUNCTION_ASYNC_PTR_T} *){self._sq_def.name}$async;",
            f"{self._var_name}->syncPtr = ({FUNCTION_SYNC_PTR_T} *){self._sq_def.name};",
            f"{self._var_name}->$capture = {self._var_name}$$capture;",
            *arg_names_setting
        ]
        return "\n".join(result)

    @property
    def global_init_text(self) -> Optional[str]:
        """获取闭包的全局初始化代码。"""
        return self._sq_def.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        """获取闭包的头代码（声明Function结构体变量）。"""
        return f"{FUNCTION_T} *{self._var_name};"

    @property
    def inline_mapping(self) -> dict[str, str]:
        """获取内联变量映射。"""
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        """泛型实例化闭包内部的函数定义。"""
        new_expr: Closure = copy(self)
        new_expr._sq_def = self._sq_def.instantiation_full_by_dict(type_args)
        return new_expr

    def optimize(self) -> "Expression":
        """优化闭包内部的函数定义。"""
        self._sq_def = self._sq_def.optimize()
        return self

    @property
    def outer_text(self) -> str:
        """获取闭包的外层代码（函数定义的源代码与外层代码）。"""
        outer: Optional[str] = self._sq_def.outer_text
        source: str = self._sq_def.source
        if outer is not None and outer.strip() != "":
            return outer + "\n\n" + source
        return source

    @property
    def release_text(self) -> Optional[str]:
        """获取闭包的释放代码（引用计数减一）。"""
        result: list[str] = [
            f"if ({self._var_name}->$refCount == 0) {{",
            f"\tif ({self._var_name}->$parent) {{",
            f"\t\t((viola$lang$uint32 *){self._var_name}->$parent)[0]--;",
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
            # 重载的泛型函数：按类型参数数量选择匹配的声明
            raw_name: str = self._generic_symbol.var.raw_name
            candidates = [v for (k_name, _), v in self._symbol_table.symbols.items()
                          if k_name == raw_name and isinstance(v, FunctionName) and
                          v.type.generic_args_str is not None and
                          len(v.type.generic_args_str) == len(self._type_args)]
            if len(candidates) == 1:
                func = candidates[0]
            base_func: FunctionName = func
            func = self._symbol_table.get_generic_func_instance(func, tuple(self._type_args))
            inst_ref = VariableRef(self._src_info, self._symbol_table, func)
            if any(isinstance(t, GenericArgument) for t in self._type_args):
                # 泛型函数体内的递归调用（如forEachEach::<T>）：类型参数仍是泛型参数，
                # 记录原泛型函数与类型参数，实例化时按具体类型重新解析
                inst_ref.generic_call_info = (base_func, tuple(self._type_args))
            self._instance = inst_ref
        elif isinstance(self._generic_symbol, AttrOp):
            method = self._generic_symbol.as_method()
            if not isinstance(method, MethodName):
                raise CompilerException(f"{method} is not a method.", self._src_info)
            method = self._symbol_table.get_generic_method_instance(method, tuple(self._type_args))
            self._instance: AttrOp = AttrOp(self._src_info, self._symbol_table)
            self._instance.set_caller(self._generic_symbol.caller)
            self._instance.set_attr(method.self_name)
        elif isinstance(self._generic_symbol, TypeRef):
            cls = self._generic_symbol.return_type
            # noinspection PyTypeChecker
            if isinstance(cls, ClassName):
                cls = self._symbol_table.get_generic_cls_instance(cls, tuple(self._type_args))
                self._instance = ClassRef(self._src_info, self._symbol_table, cls)
            else:
                raise CompilerException(f"{cls.raw_name} is not a class.", self._src_info)
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
        if not expr.return_type.convertible_to(self._based_type, self._symbol_table.symbols):
            raise CompilerException(f"{expr.return_type} is not convertible to {self._based_type}.", self._src_info)
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
