# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import UnpackExpr, VariableRef, Expression, CallOp, AttrOp, ClassRef, TypeRef
from .statement import Statement, BlockStmt, DeclStmt, FnBlockStmt, CStmt, TryStmt, CatchStmt, OpStmt, ReturnStmt, \
    STACK_B_POP_FUNC, STACK_B_PUSH_FUNC, CleanupBlock, THIS_OBJ_NAME, SUPER_NEW_SUFFIX
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
# 接口条目类型（见runtime.h与开发疑问记录170(c)）
INTERFACE_ENTRY_T: str = "viola$dynamic$InterfaceEntry"
# 虚方法槽位类型（同步实现与异步包装各一个函数指针，见开发疑问记录161）
VFUNC_SLOT_T: str = "viola$dynamic$VFuncSlot"
# 引用计数字段与其原子类型：结构体布局中的$refCount以系统原子变量表示
# （见runtime.h"原子引用计数"与versions_dev_plan_zh.md"漏洞修复"）
REFCOUNT_FIELD_NAME: str = "$refCount"
REFCOUNT_T: str = "viola$lang$atomic_uint32"
# 递减引用计数并返回递减后的值（一次原子操作，见runtime.h）
REFCOUNT_DEC_FUNC: str = "viola$lang$refcount_dec"
# perror的Viola名（查找符号表用）与显式C名（io.vla以cname声明，见开发疑问记录103）
PERROR_VIOLA_NAME: str = "perror"
PERROR_FUNC_NAME: str = "viola$io$print$perror"


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
        """获取常量的全局初始化代码文本。

        模块级变量的存储定义写在文件作用域（见outer_text），
        此处只保留初值表达式所需的临时变量声明与赋值语句，
        否则局部声明会遮蔽文件作用域的全局定义（见开发疑问记录167）。
        """
        result: list[str] = list(filter(lambda x: x is not None, [
            self._define_stmt.value_head_text,
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
        ]), self._define_stmt.new_variables_ordered))
        return "\n\n".join(results)

    def optimize(self) -> "Definition":
        """优化常量定义。"""
        self._define_stmt = self._define_stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        """获取常量的外层代码文本（含模块级变量的文件作用域存储定义）。

        带初值的模块级变量在文件作用域给出存储定义：头文件中生成的是extern声明，
        若定义只写在__global__函数体内，则它只是该函数的局部变量，文件作用域上
        没有定义，链接时报undefined reference（见开发疑问记录167）。

        无初值的模块级声明生成的是C的暂定定义，与运行库中的定义按C的共同符号
        合并规则合并（如viola.os的STDIN/STDOUT_FILENO与O_*常量、viola.stat的
        S_*常量：存储与初值由运行库提供）。gcc 10起默认-fno-common、暂定定义不再
        合并，故构建命令需带-fcommon，见开发疑问记录167。
        """
        # 无初值且本模块从未赋值的模块级变量只是"声明"：其存储由其他翻译单元
        # 提供（典型情形是运行库的C实现，如viola.os的STDIN_FILENO与O_*常量、
        # viola.stat的S_*常量），生成extern声明即可，不与那份定义冲突；
        # 其余情形（有初值，或本模块给它赋过值）由本模块提供存储，生成定义
        # （见开发疑问记录168）
        has_initial_value: bool = self._define_stmt.has_initial_value
        storage_text: str = "\n".join(
            var.definition_text
            if (has_initial_value or self._symbol_table.needs_global_storage(var.name))
            else f"extern {var.type_name_pair_calling};"
            for var in self._define_stmt.new_variables_ordered if var.is_global)
        stmt_outer_text: Optional[str] = self._define_stmt.outer_text
        results: list[str] = list(filter(
            lambda x: x is not None and x.strip() != "", [storage_text, stmt_outer_text]))
        if len(results) == 0:
            return None
        return "\n".join(results)

    def set_stmt(self, stmt: Statement) -> None:
        """设置常量定义中的语句。"""
        self._define_stmt = stmt
        self._define_stmt.set_as_const_def()

    @property
    def source(self) -> str:
        """获取常量的源代码文本。"""
        rename_defines: str = "\n".join([
            f"#define {x.self_name} {x.name}" for x in self._define_stmt.new_variables_ordered
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
        # 异步包装函数的声明：原生函数的$async实现由运行库提供
        # （见build_tools/lib_tools/gen_async_wrappers.py与开发疑问记录106）
        text: list[str] = [
            self._decl.as_declare() + ";",
            self._decl.as_async().as_declare() + ";"
        ]
        # 默认参数全局变量的外部声明（其他模块调用默认参数时引用）
        text += [f"extern {v.type_name_pair_calling};" for v in self._decl.default_params.values()]
        return "\n".join(text)

    def _overload_index_in_template(self) -> int:
        """获取本方法在模板类中的重载序号（同名方法中的第几个，从0开始）。

        与ClassName.add_method递增_method_overload_times的顺序一致：按模板类
        方法表的插入顺序统计同名方法。实例化类的同名方法序号与之相同
        （见ClassName.instantiation_full），故实例化时用同一序号取名
        （见开发疑问记录170(b)）。
        """
        template_cls: ClassName = self._method_decl.cls
        bare_name: str = self._method_decl.bare_name
        index: int = 0
        for (_, _), method in template_cls.methods.items():
            if method.name == self._method_decl.name:
                break
            if method.bare_name == bare_name:
                index += 1
        return index

    def instantiation(self, cls_decl: ClassName, type_args: dict[GenericArgument, TypeName]) -> "SqDef":
        """将函数作为类方法进行泛型实例化。"""
        new_sq = deepcopy(self)
        type_args_tuple: tuple[TypeName, ...] = tuple(map(lambda x: type_args[x], cls_decl.generic_args))
        inst_cls = self._symbol_table.get_generic_cls_instance(cls_decl, type_args_tuple)
        # set_cls的序号必须是该方法在模板类中的真实重载序号：原先恒传0，使同名重载
        # 方法（如Array::<T>的切片版__getitem__）的实例化函数名与调用点的名字不一致
        # （调用点按实例化类的真实序号取名），链接时报未定义符号（见开发疑问记录170(b)）
        new_sq._method_decl = self._method_decl.set_cls(inst_cls, self._overload_index_in_template())
        # 将原类到实例化类的映射也加入 type_args，使 this 的类型被替换
        type_args_with_cls = dict(type_args)
        type_args_with_cls[GenericArgument(self._src_info, cls_decl.name)] = inst_cls
        new_sq._decl = self._method_decl.as_function().instantiation(
            new_sq._method_decl.as_function().name, type_args_with_cls
        )
        new_sq._body = new_sq._body.instantiation(type_args_with_cls)
        # 参数与返回值变量的类型同样需要实例化（供清理代码等使用）；
        # 类方法路径原先遗漏，导致方法体内引用泛型类自身实例的返回值在清理代码中
        # 仍使用伪实例名（如Box__0$__del__$_0），链接失败（见开发疑问记录102）
        new_sq._args = [a.instantiation(a.name, type_args_with_cls) for a in new_sq._args]
        new_sq._rets = [r.instantiation(r.name, type_args_with_cls) for r in new_sq._rets]
        new_sq._body._new_variables = [v.instantiation(v.name, type_args_with_cls)
                                       for v in new_sq._body._new_variables]
        # 以文本形式生成的、依赖类成员类型的代码需按实例化的类重建（析构函数的
        # 成员释放代码，见开发疑问记录111）
        new_sq.rebuild_for_class(inst_cls)
        # 异步包装体在finish时以原泛型参数类型构建，实例化后需用具体类型重建
        new_sq._async_body = new_sq._get_async_body()
        return new_sq

    def instantiation_full(self, type_args: tuple[TypeName, ...]) -> "SqDef":
        """使用元组形式的类型参数进行泛型实例化。"""
        type_args_dict: dict[GenericArgument, TypeName] = dict(zip(self._decl.type.generic_args, type_args))
        return self.instantiation_full_by_dict(type_args_dict)

    def rebuild_for_class(self, cls: ClassName) -> None:
        """按实例化后的类重建以文本形式生成的代码。

        默认无操作：只有代码文本中直接内嵌了类成员类型名称的定义需要重建
        （析构函数的成员释放代码，见开发疑问记录111）。
        """

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
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exception;",
            self._body.text,
            CleanupBlock(self._src_info, self._symbol_table, self._var_states, self._body.new_variables_ordered).text,
            "}"
        ]
        async_text: list[str] = [
            async_define_name + " {",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exception;",
            # 异步任务开始执行时压入B栈（记录发起线程与目标线程），
            # 结束时退栈；退栈放在$$cleanup标签之后，使正常返回与异常
            # 跳转两条路径都恰好退栈一次（见开发疑问记录87）
            f"\t{STACK_B_PUSH_FUNC}(listener->currentThreadId);",
            self._async_body.text,
            "$$cleanup: ;",
            f"\t{STACK_B_POP_FUNC}(listener->currentThreadId);",
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
        # 同步调用后刷新本包装体的异常缓存：被调函数抛出且未捕获的异常
        # 记录在其listener中，需要刷新才能被下方的catch感知，进而记入
        # 本任务的listener供调用方取回（见开发疑问记录84）
        sync_call_text: str = f"\t{self._decl.name}({sync_call_params_text});\n" \
                             f"\tif ($$exc == NULL) {{ $$exc = listener->exception; }}"
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
            *ret_write_back_text
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
                PERROR_VIOLA_NAME, (StringTypeName,)
            ])
        except CompilerException:
            # viola.io的内置绑定已移除（开发疑问记录第40条），此处直接构造
            # perror的原生函数符号（实现位于viola_libs/viola/io/print.c）。
            # 显式C名与io.vla声明中的cname一致（见开发疑问记录103）
            perror_func = FunctionName(self._src_info, [], PERROR_FUNC_NAME,
                                       FunctionTypeName(self._src_info, [StringTypeName], []),
                                       ["text"], [], True, False, True)
            catch_inner_print_func = VariableRef(self._src_info, self._symbol_table, perror_func)
        catch_inner_print_call.set_func(catch_inner_print_func)
        catch_inner_print.set_expr(catch_inner_print_call)
        catch_inner.add_stmt(catch_inner_print)
        catch_inner_assign: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
        catch_inner_assign.set_text("listener->exception = exc;")
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
        this_name: str = THIS_OBJ_NAME
        this_type: ClassName = cls
        self._this_var: LocalVariableName = LocalVariableName(self._src_info, this_name, this_type)
        # 父类构造初始化函数（$__new__super）需要排除以下编译器生成语句
        self._alloc_stmt: Optional[CStmt] = None
        self._vtable_stmt: Optional[CStmt] = None
        self._write_back_stmt: Optional[CStmt] = None
        if not self._is_native:
            # 原生构造函数（声明文件中声明的内置类构造）由运行库实现，
            # 不生成分配与vtable初始化代码
            this_alloc_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
            # 使用calloc清零：未被构造函数赋值的成员（尤其是继承自父类、
            # 子类__new__未设置的成员，如Exception.message）保持NULL/0，
            # 避免后续读取未初始化内存（见开发疑问记录84/91）
            this_alloc_stmt.set_text(
                f"{cls.c_calling_name} {self._this_var.name} = "
                f"({cls.c_calling_name})calloc(1, sizeof({cls.c_alloc_name}));")
            self.add_stmt(this_alloc_stmt)
            self._alloc_stmt = this_alloc_stmt
            # 初始化实例的TypeInfo指针，供异常捕获与动态类型转换使用
            this_vtable_stmt: CStmt = CStmt(src_info, self._symbol_table, self._var_states)
            this_vtable_stmt.set_text(
                f"{self._this_var.name}->$refCount = 1;\n"
                f"{self._this_var.name}->$parent = NULL;\n"
                f"{self._this_var.name}->$$vtable = (void *)&{cls.name}$$vtable;")
            self.add_stmt(this_vtable_stmt)
            self._vtable_stmt = this_vtable_stmt

    def finish(self) -> None:
        """完成构造函数，将局部this写回输出参数。"""
        if not self._is_native:
            write_back_stmt: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
            write_back_stmt.set_text(f"*_this = {self._this_var.name};")
            self.add_stmt(write_back_stmt)
            self._write_back_stmt = write_back_stmt
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

    @property
    def super_init_name(self) -> str:
        """获取父类构造初始化函数（$__new__super）的C名称。"""
        return self._decl.name.replace("$__new__", SUPER_NEW_SUFFIX, 1)

    @property
    def super_init_declare(self) -> Optional[str]:
        """获取父类构造初始化函数的C声明。"""
        if self._is_native or self._alloc_stmt is None:
            return None
        return f"void {self.super_init_name}({self._super_init_params_text()});"

    def _super_init_params_text(self) -> str:
        """获取父类构造初始化函数的形参表：本类构造实参 + 待初始化的对象 + listener。"""
        # 类型取自构造函数的返回类型（即本类）：泛型类的构造函数体内
        # _this_var的类型仍是泛型模板，实例化后需用实例类名
        cls: ClassName = self._decl.type.returns[0]
        args_text: str = ", ".join(map(
            lambda t, x: f"{t.c_calling_name} {x}", self._decl.type.args, self._decl.arg_names))
        return ", ".join(filter(lambda x: x != "", [
            args_text, f"{cls.c_calling_name}{self._this_var.name}", f"{LISTENER_T} *listener"]))

    @property
    def super_init_source(self) -> Optional[str]:
        """获取父类构造初始化函数的C源代码。

        供子类以`super = 父类名(...)`调用：与__new__的区别是不分配对象、
        不设置vtable、不写回_this，直接在调用方已分配并已设置子类vtable的
        对象上执行本类构造体，从而初始化父类成员（见开发疑问记录107）。
        """
        if self._is_native or self._alloc_stmt is None:
            return None
        body_stmts: list[Statement] = list(filter(
            lambda stmt: stmt is not self._alloc_stmt and stmt is not self._vtable_stmt and
            stmt is not self._write_back_stmt, self._body._stmt))
        cleanup: str = CleanupBlock(self._src_info, self._symbol_table, self._var_states,
                                    self._body.new_variables_ordered).text
        return "\n".join(filter(lambda line: line != "", [
            f"void {self.super_init_name}({self._super_init_params_text()}) {{",
            self._body.head_text or "",
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exception;",
            "\n".join(map(lambda stmt: stmt.text, body_stmts)),
            cleanup,
            "}"
        ]))

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
        # 同步更新父类构造初始化函数的排除引用（其体由_body语句生成）
        new_def._alloc_stmt = this_alloc_stmt
        new_def._vtable_stmt = this_vtable_stmt
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
        self._free_stmt: Optional[CStmt] = None
        if cls.is_c_part:
            return
        self._free_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        self._free_stmt.set_text(self._forward_text(cls) + self._member_free_text(cls))
        self.add_stmt(self._free_stmt)

    def _forward_text(self, cls: ClassName) -> str:
        """生成虚析构的转发前缀：对象的实际类型不是本类时转交其析构函数。

        以基类类型持有派生类对象时（如`Base b = Derived();`），释放代码按变量的
        静态类型调用Base的析构函数；本前缀据对象的$$vtable判断其实际类型，不同则
        经虚析构入口$del转交实际类型的析构函数，使派生类的成员也被释放。
        实际类型的析构函数（$$vtable即本类的TypeInfo）不会再次转发，故每个对象
        只会执行最派生类的析构函数一次（见开发疑问记录170(a)）。

        $$vtable为NULL的对象（运行库的原生类等未参与虚分派者）沿用本类析构。
        """
        cls: ClassName
        if not cls.has_vtable_property:
            # 结构体中没有$$vtable字段（如编译器内置的string类型），无法分派
            return ""
        del_slot: str = f"(({TYPE_INFO_T} *){self._this_var.name}->$$vtable)"
        return "\n".join([
            f"if ({self._this_var.name}->$$vtable != NULL",
            f"\t\t&& {self._this_var.name}->$$vtable != (void *)&{cls.name}$$vtable",
            f"\t\t&& {del_slot}->$del != NULL) {{",
            f"\t((void (*)(void *, {LISTENER_T} *)){del_slot}->$del)({self._this_var.name}, listener);",
            "\treturn;",
            "}",
            ""
        ])

    def _member_free_text(self, cls: ClassName) -> str:
        """生成释放类实例成员属性的代码文本。

        泛型类的方法体在实例化后由SqDef.instantiation重建，但本段代码是
        在构造时以文本形式生成的，成员类型中的泛型参数不会随之替换
        （如Array::<T>的成员T[]会残留为T$$array，见开发疑问记录111），
        故实例化时以实例化后的类重新生成本文本（rebuild_for_class）。
        """
        src_info = self._src_info
        # 释放实例属性（含继承自父类的，见ordered_properties）：静态属性是模块级
        # 全局变量，不是结构体成员。析构经$$vtable按对象的实际类型分派（虚析构），
        # 每个对象只会执行最派生类的析构函数一次，故此处释放整条继承链上的成员
        # 不会重复释放（见开发疑问记录170(a)）
        properties_to_free: list[VariableName] = list(
            filter(lambda y: y.is_object and not y.is_static, cls.ordered_properties))
        free_texts: list[str] = []
        for x in properties_to_free:
            # 类结构体的成员名为属性的self_name，访问时需要通过_this指针
            prop_var: LocalVariableName = LocalVariableName(
                src_info, f"{self._this_var.name}->{x.self_name}", x.type
            )
            # 成员的静态类型可能是成员对象实际类型的基类：释放时调用静态类型的
            # 析构函数，由其按对象的$$vtable转交实际类型的析构函数（虚析构，
            # 见开发疑问记录170(a)），故此处无需分派
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
                # 递减与"是否归零"的判断合并为一次原子操作：分两步时两个线程
                # 可能各自递减后都读到0，从而重复释放（见versions_dev_plan_zh.md"漏洞修复"）
                f"\t\t\tif ({REFCOUNT_DEC_FUNC}(&{self._this_var.name}->{x.self_name}->$refCount) == 0) {{",
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
        return "\n".join(free_text)

    def rebuild_for_class(self, cls: ClassName) -> None:
        """按实例化后的类重建成员释放代码（泛型类实例化时调用）。"""
        if self._free_stmt is None:
            return
        self._free_stmt.set_text(self._forward_text(cls) + self._member_free_text(cls))


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
            f"\t{EXCEPTION_T_NAME} *$$exc = listener->exception;",
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
        # 虚方法槽位数组：由virtual_slot_impl按槽位给出同步实现与异步包装，
        # 子类重写的方法占用父类的同一槽位，从而实现按对象实际类型的分派
        # （见开发疑问记录161）
        vfunc_text: str = self._vfunc_array_name if self._vfunc_array_text != "" else "NULL"
        vfunc_assign: list[str] = []
        # 虚析构入口（见开发疑问记录170(a)）
        delete_entry_text: list[str] = self._delete_entry_text
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
            *delete_entry_text,
            # 类名：未定义toString的类由其默认转换返回（见开发疑问记录175(b)）
            f"{self._vtable_name}.$name = \"{self._decl.raw_name}\";",
            # 接口实现表：接口类型的接收者据此分派（见开发疑问记录170(c)）
            f"{self._vtable_name}.$interfaces = "
            f"{self._interface_table_name if self._interface_table_text != '' else 'NULL'};",
            *static_props_global_text,
            *methods_global_text
        ]
        return "\n".join(result)

    @property
    def _destructor_name(self) -> Optional[str]:
        """获取本类析构函数的C名称（无则返回None）。"""
        del_method = next(
            (m for (n, _), m in self._decl.methods.items() if n == "__del__"), None)
        return del_method.name if del_method is not None else None

    @property
    def _delete_entry_text(self) -> list[str]:
        """获取虚函数表中析构入口的初始化文本（见开发疑问记录170(a)）。

        以基类类型持有派生类对象时，释放代码经此按对象的实际类型调用析构函数；
        泛型类模板本身不生成C代码，故不设置（泛型实例不参与虚分派）。
        """
        if self._decl.is_generic:
            return []
        del_name: Optional[str] = self._destructor_name
        if del_name is None:
            return []
        return [f"{self._vtable_name}.$del = (void *)&{del_name};"]

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
                lambda x: f"\t{REFCOUNT_T if x.self_name == REFCOUNT_FIELD_NAME else x.type.c_calling_name}"
                          f" {x.self_name};",
                filter(lambda x: not x.is_static, self._decl.ordered_properties)
            )
        )
        # 结构体定义带include guard：wrapper类（如viola.os的Stat/StatVFS、
        # viola.io的file）的“正式”定义位于运行库头文件（runtime.h）中，
        # 供运行库翻译单元与生成代码共用；本TU已包含runtime.h时跳过此处定义，
        # 避免重复定义（见开发疑问记录113）
        struct_guard: str = "_VIOLA_CLASS_T_" + self._decl.name
        struct_def: list[str] = [
            class_info_text,
            f"\n#ifndef {struct_guard}",
            f"#define {struct_guard}",
            f"typedef struct {self._decl.name} {{",
            properties_text,
            "} " + self._decl.name + ";",
            "#endif"
        ]
        static_props_text: str = "\n".join(
            map(
                lambda x: f"extern {x.type_name_pair_calling};",
                filter(lambda x: x.is_static, self._decl.properties.values())
            )
        )
        # 抽象类原先额外输出一个按抽象方法生成的虚函数表结构体typedef
        # （<类名>$$vfunc），该typedef从未被任何地方使用，且其名称与
        # 虚方法槽位数组（见_vfunc_array_text）冲突，故不再输出（见开发疑问记录161）
        result_def: list[str] = struct_def
        result_def.append(static_props_text)
        methods_def: list[str] = list(map(lambda x: x.header_no_wrap, self._methods.values()))
        # 父类构造初始化函数声明：供其他模块的子类调用（super = 本类名(...)）
        methods_def.extend(filter(lambda x: x is not None, map(
            lambda m: m.super_init_declare if isinstance(m, ConstructorDef) else None,
            self._methods.values())))
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
        # 类的TypeInfo全局变量定义（在__global__中初始化$parent、vfunc与接口表）
        vtable_def: str = f"{TYPE_INFO_T} {self._vtable_name} = {{NULL, NULL, NULL, NULL, NULL}};"
        # 虚方法槽位数组：必须在__global__之前定义（__global__中取其地址）
        vfunc_def: str = self._vfunc_array_text
        interface_def: str = self._interface_table_text
        static_props_def: str = "\n".join(map(
            lambda x: f"{x.type.c_calling_name} {x.name};",
            filter(lambda x: x.is_static, self._decl.properties.values())
        ))
        methods_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._methods.values())))
        props_result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._static_properties.values())))
        result: str = "\n".join([vtable_def, vfunc_def, interface_def, static_props_def,
                                 methods_result, props_result])
        return result if result != "" else None

    def _interface_slot_array_name(self, interface: ClassName) -> str:
        """获取本类对某接口的槽位数组C名称。"""
        return f"{self._decl.name}$$iface${interface.name}"

    @property
    def _interface_table_name(self) -> str:
        """获取本类接口条目表的C名称。"""
        return f"{self._decl.name}$$ifaceTable"

    @property
    def _interface_table_text(self) -> str:
        """获取本类对各个接口的槽位数组与接口条目表的定义文本。

        接口不在继承链上（一个类可实现多个接口），故接口的实现单独成表：
        每个接口一个槽位数组（下标由接口自身的方法顺序决定，因而同一个接口在
        所有实现类中下标一致），再由接口条目表把"接口 -> 槽位数组"列出。
        接口类型的接收者据此分派（见开发疑问记录170(c)）。
        原生类与泛型类模板不生成（泛型实例不参与虚分派）。
        """
        if self._is_native or self._decl.is_generic:
            return ""
        interfaces: list[ClassName] = [i for i in self._decl.all_interfaces if not i.is_generic]
        if len(interfaces) == 0:
            return ""
        texts: list[str] = []
        entries: list[str] = []
        for interface in interfaces:
            slots: list[tuple[str, tuple[str, ...]]] = interface.virtual_slots
            impls = self._decl.interface_slots(interface)
            if len(slots) == 0:
                entries.append(f"\t{{&{interface.vtable_name}, NULL}}")
                continue
            slot_lines: list[str] = []
            for impl in impls:
                if impl is None:
                    slot_lines.append("\t{NULL, NULL}")
                    continue
                slot_lines.append(f"\t{{(void *)&{impl.name}, (void *)&{impl.name}$async}}")
            texts.append("\n".join([
                f"static {VFUNC_SLOT_T} {self._interface_slot_array_name(interface)}[] = {{",
                ",\n".join(slot_lines),
                "};"
            ]))
            entries.append(
                f"\t{{&{interface.vtable_name}, {self._interface_slot_array_name(interface)}}}")
        if len(entries) == 0:
            return ""
        texts.append("\n".join([
            f"static const {INTERFACE_ENTRY_T} {self._interface_table_name}[] = {{",
            ",\n".join(entries) + ",",
            "\t{NULL, NULL}",
            "};"
        ]))
        return "\n".join(texts)

    @property
    def _vfunc_array_name(self) -> str:
        """获取虚方法槽位数组的C名称。"""
        return f"{self._decl.name}$$vfunc"

    @property
    def _vfunc_array_text(self) -> str:
        """获取虚方法槽位数组的定义文本（文件作用域，见开发疑问记录161）。

        槽位下标与父类一致，因此子类的数组可直接引用父类的实现（未重写时）
        或自身的重写实现；抽象方法没有实现，对应槽位为NULL，由实现它的子类
        填入。
        """
        if self._is_native or self._decl.is_generic:
            # 原生类的实现由运行库提供；泛型类模板本身不生成C代码
            # （泛型实例不参与虚方法分派，见ClassName.is_generic_instance）
            return ""
        slots: list[tuple[str, tuple[str, ...]]] = self._decl.virtual_slots
        if len(slots) == 0:
            return ""
        entries: list[str] = []
        for index in range(len(slots)):
            impl = self._decl.virtual_slot_impl(index)
            if impl is None:
                entries.append("\t{NULL, NULL}")
                continue
            entries.append(f"\t{{(void *)&{impl.name}, (void *)&{impl.name}$async}}")
        return "\n".join([
            f"static {VFUNC_SLOT_T} {self._vfunc_array_name}[] = {{",
            ",\n".join(entries),
            "};"
        ])

    @property
    def source(self) -> str:
        """获取类的源代码文本。"""
        if self._is_native:
            # 原生绑定类：实现由运行库提供，不生成任何C代码
            return f"// native class {self._decl.raw_name}"
        methods_def: list[str] = list(map(lambda x: x.source, self._methods.values()))
        # 父类构造初始化函数：供子类以super = 本类名(...)在已分配对象上初始化本类成员
        methods_def.extend(filter(lambda x: x is not None, map(
            lambda m: m.super_init_source if isinstance(m, ConstructorDef) else None,
            self._methods.values())))
        rename_define: str = f"#define {self._decl.self_name} {self._decl.name}"
        if self._del_super_body is not None:
            # wrapper类的默认成员清理函数（由del(super)调用）
            helper: str = "\n".join([
                f"void {self._decl.name}$__del__super$_0({self._decl.c_calling_name} _this, "
                f"{LISTENER_T} *listener) {{",
                f"\t{EXCEPTION_T_NAME} *$$exc = listener->exception;",
                self._del_super_body,
                "$$cleanup: ;",
                "}"
            ])
            return "\n\n".join(methods_def + [helper, rename_define])
        return "\n\n".join(methods_def + [rename_define])

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
        """添加枚举值，包含名称和初始值表达式。

        成员按“枚举类型的属性”登记（C名称为<模块>$<枚举>$<成员>），
        使用处（如Color.RED）由AttrOp按静态属性的方式解析（见开发疑问记录160）。
        """
        if not expr.return_type.convertible_to(self._based_type, self._symbol_table.symbols):
            raise CompilerException(f"{expr.return_type} is not convertible to {self._based_type}.", self._src_info)
        var: GlobalVariableName = GlobalVariableName(self._src_info, self._decl.as_namespace(), name, self._decl)
        self._decl.add_property(var)
        self._enum.append((var, expr))

    def finish(self) -> None:
        """完成枚举定义。"""
        if self._is_finished:
            raise CompilerException("Enum is already finished.", self._src_info)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
        """获取枚举的全局初始化代码文本。

        成员的存储定义在文件作用域（见outer_text），此处只做赋值。
        """
        front_text: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].front_text, self._enum)))
        result: list[str] = list(map(lambda x: f"{x[0].name} = {x[1].text};", self._enum))
        expr_global_text: list[str] = list(
            filter(lambda x: x is not None, map(lambda x: x[1].global_init_text, self._enum)))
        return "\n".join(front_text + expr_global_text + result)

    @property
    def header(self) -> str:
        """获取枚举在头文件中的声明文本。"""
        self._decl: EnumName
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
        """获取枚举的外层代码文本（含各成员的文件作用域存储定义）。

        与模块级变量同理：成员的存储必须在文件作用域给出，否则头文件的extern
        声明找不到定义（见开发疑问记录167、160）。
        """
        storage_text: str = "\n".join(map(lambda x: x[0].definition_text, self._enum))
        expr_outer_text: str = "\n".join(
            filter(lambda x: x is not None, map(lambda x: x[1].outer_text, self._enum)))
        result: str = "\n".join(filter(lambda x: x.strip() != "", [storage_text, expr_outer_text]))
        return result if result != "" else None

    @property
    def source(self) -> str:
        """获取枚举的源代码文本。"""
        return f"// ENUM: {self._name}"
