# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import Expression, VariableRef, AttrOp, CallOp, UnpackExpr, CONVERTIBLE_TO_FUNC, TypeRef, ClassRef, \
    StringLiteral, TupleRef, CExpr
from .symbol import (
    VariableName,
    TypeName,
    VariableState,
    NamespaceName,
    VariableStateTable,
    LocalVariableName,
    GlobalVariableName,
    TupleTypeName,
    FunctionTypeName,
    EXCEPTION_T,
    ClassName,
    GenericArgument,
    SymbolTable,
    ExceptionTypeName
)
from utils import CompilerException, unreachable_warning, SourceInfo, InternalCompilerException

from abc import ABC, abstractmethod
from copy import copy
from enum import Enum
from typing import Optional

LISTENER_WAIT_FUNC = "viola$threads$waitListener"
MARK_T: str = "viola$threads$Mark"
STACK_A_T: str = "viola$threads$StackA"
STACK_B_T: str = "viola$threads$StackB"
STACK_A_PUSH_FUNC: str = "viola$threads$pushStackA"
STACK_A_POP_FUNC: str = "viola$threads$popStackA"
STACK_B_PUSH_FUNC: str = "viola$threads$pushStackB"
STACK_B_POP_FUNC: str = "viola$threads$popStackB"
THREAD_INFO_T: str = "viola$threads$ThreadInfo"


class _Mark:
    """调试标记，用于在生成的代码中插入源代码位置信息。"""

    _mark_counter: int = 0

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """
        初始化调试标记。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        """
        self._text: StringLiteral = StringLiteral(src_info, symbol_table, src_info.traceback_no_location + "\tat ")
        self._lineno: int = src_info.lineno
        self._mark_name: str = f"$$_MARK_{_Mark._mark_counter}"
        self._is_const_def: bool = False
        _Mark._mark_counter += 1

    @property
    def mark_declare(self) -> str:
        """获取标记变量的声明代码。"""
        return f"{MARK_T} *{self._mark_name};"

    @property
    def mark_init(self) -> str:
        """获取标记的初始化代码。"""
        result = [
            self._text.head_text,
            f"{self._mark_name} = ({MARK_T} *)malloc(sizeof({MARK_T}));",
            f"{self._mark_name}->path = $$_PATH;",
            f"{self._mark_name}->line = {self._lineno};",
            self._text.front_text,
            f"{self._mark_name}->text = {self._text.text};",
        ]
        return "\n".join(result)

    @property
    def mark_init_head(self) -> str:
        """获取标记初始化的头代码。"""
        return self._text.head_text

    @property
    def mark_insert(self) -> str:
        """获取插入标记到栈中的代码。"""
        if self._is_const_def:
            return f"{STACK_A_PUSH_FUNC}(0, {self._mark_name});"
        return f"{STACK_A_PUSH_FUNC}(listener->currentThreadId, {self._mark_name});"

    @property
    def mark_pop(self) -> str:
        """获取从栈中弹出标记的代码。"""
        if self._is_const_def:
            return f"{STACK_A_PUSH_FUNC}(0);"
        return f"{STACK_A_POP_FUNC}(listener->currentThreadId);"

    def set_as_const_def(self) -> None:
        """将当前标记设置为常量定义标记。"""
        self._is_const_def = True


class Statement(CompilingItem, ABC):
    """语句基类，所有语句类型的抽象基类。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 single_stmt: bool = True, with_mark: bool = True) -> None:
        """
        初始化语句对象。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param single_stmt: 是否为单条语句（默认为 True）。
        """
        super().__init__(src_info)
        self._indent: int = 0
        self._is_async: bool = False
        self._inline_mapping: dict[str, str] = {}
        # 0.1：暂不生成traceback调试标记（大量冗余代码与重复初始化问题，
        # 且违反0.1“减少冗余”的要求）。保留_jump_mark用于异常跳转。
        self._mark = None
        self._jump_mark: Optional[str] = "$$cleanup" if single_stmt else None
        self._tail_recursive_mark: Optional[str] = None
        self._is_const_def: bool = False
        self._symbol_table: SymbolTable = symbol_table
        self._var_states: VariableStateTable = var_states

    @abstractmethod
    def as_async(self) -> "Statement":
        """将语句转换为异步版本。"""
        new_stmt = copy(self)
        new_stmt._is_async = True
        return new_stmt

    @abstractmethod
    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        """将语句转换为内联版本。"""
        pass

    @abstractmethod
    def check_tail_recursive(self, func_name: str) -> "Statement":
        """检查并处理尾递归优化。"""
        pass

    @property
    def drop_out(self) -> bool:
        """获取该语句是否会导致函数退出。"""
        return False

    @property
    @abstractmethod
    def global_init_text(self) -> str:
        """获取全局初始化代码文本（包含标记初始化）。"""
        return self._mark.mark_init if self._mark is not None else ""

    @property
    @abstractmethod
    def head_text(self) -> Optional[str]:
        """获取语句的头代码（变量声明等）。"""
        pass

    def indent(self) -> None:
        """增加语句的缩进级别。"""
        self._indent += 1

    @property
    def inline_mapping(self) -> dict[str, str]:
        """获取内联变量映射。"""
        return self._inline_mapping

    @property
    @abstractmethod
    def input_variables(self) -> set[VariableName]:
        """获取语句作为输入使用的变量集合。"""
        pass

    @abstractmethod
    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        """对语句进行泛型实例化。"""
        pass

    @abstractmethod
    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        """插入 finally 语句以进行资源清理。"""
        pass

    @property
    @abstractmethod
    def is_finished(self) -> bool:
        """获取语句是否已完成。"""
        pass

    @property
    @abstractmethod
    def new_listeners(self) -> dict[VariableName, str]:
        """获取语句创建的新监听器映射。"""
        pass

    @property
    @abstractmethod
    def new_variables(self) -> set[VariableName]:
        """获取语句创建的新变量集合。"""
        pass

    @abstractmethod
    def optimize(self) -> "Statement":
        """优化语句。"""
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        """获取语句的外层代码文本（包含标记声明）。"""
        if self._mark is not None:
            return self._mark.mark_declare
        return None

    def remove_jump_mark(self) -> None:
        """移除跳转标记。"""
        self._jump_mark = None

    def remove_mark(self) -> None:
        """移除调试标记。"""
        self._mark = None

    def set_as_const_def(self) -> None:
        """将当前语句标记为常量定义。"""
        self._is_const_def = True
        if self._mark is not None:
            self._mark.set_as_const_def()

    def set_jump_mark(self, jump_mark: str) -> None:
        """设置语句的跳转目标标记。"""
        self._jump_mark = jump_mark

    @property
    def src_info(self) -> SourceInfo:
        """获取源代码信息。"""
        return self._src_info

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        """用常量值替换语句中的变量引用。"""
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        """获取尾递归优化标记。"""
        return self._tail_recursive_mark

    @property
    def text(self) -> str:
        """获取语句的完整 C 代码文本（含异常跳转检查和缩进）。"""
        if self._mark is None:
            inner: str = self._inner_text
            if self._jump_mark is not None and inner.strip() != "":
                return self._indent_text(inner + "\n" + f"if ($$exc) goto {self._jump_mark};")
            return self._indent_text(inner)
        result: list[str] = [
            self._mark.mark_insert,
            self._inner_text,
            f"if ($$exc) goto {self._jump_mark};" if self._jump_mark is not None else "// jump passed",
            self._mark.mark_pop
        ]
        return self._indent_text("\n".join(result))

    def update_const_vars(self, const_vars: dict[VariableName, Expression]) -> dict[VariableName, Expression]:
        """更新语句中的常量变量映射。"""
        return const_vars

    @property
    @abstractmethod
    def variables_states(self) -> dict[VariableName, VariableState]:
        """获取语句修改变量的状态映射。"""
        pass

    def _indent_text(self, text: Optional[str]) -> str:
        """为每行代码添加缩进前缀。"""
        if text is None:
            return ""
        lines: list[str] = text.split("\n")
        lines = list(map(lambda line: "\t" * self._indent + line, lines))
        return "\n".join(lines)

    @property
    @abstractmethod
    def _inner_text(self) -> str:
        """获取语句的内部文本（不含标记和缩进）。"""
        pass


class _StmtList(Statement):
    """语句列表容器，用于优化时合并多条语句。"""

    def __getitem__(self, item: int) -> Statement:
        """获取指定索引处的语句。"""
        return self._stmts[item]

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable, stmts: list[Statement],
                 const_vars: Optional[dict[VariableName, Expression]] = None) -> None:
        """
        初始化语句列表容器。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param stmts: 语句列表。
        :param const_vars: 被替换语句产生的常量变量映射（如常量声明语句被移除时）。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._stmts: list[Statement] = stmts
        self._extra_const_vars: dict[VariableName, Expression] = const_vars if const_vars is not None else {}

    def as_async(self) -> "Statement":
        raise InternalCompilerException("Not implemented", self._src_info)

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        raise InternalCompilerException("Not implemented", self._src_info)

    def check_tail_recursive(self, func_name: str) -> "Statement":
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    def global_init_text(self) -> str:
        return "\n".join(filter(lambda line: line is not None, map(lambda stmt: stmt.global_init_text, self._stmts)))

    @property
    def head_text(self) -> Optional[str]:
        return "\n".join(filter(lambda line: line is not None, map(lambda stmt: stmt.head_text, self._stmts)))

    @property
    def input_variables(self) -> set[VariableName]:
        raise InternalCompilerException("Not implemented", self._src_info)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        raise InternalCompilerException("Not implemented", self._src_info)

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    def is_finished(self) -> bool:
        return True

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    def new_variables(self) -> set[VariableName]:
        raise InternalCompilerException("Not implemented", self._src_info)

    def optimize(self) -> "Statement":
        raise InternalCompilerException("Not implemented", self._src_info)

    @property
    def outer_text(self) -> Optional[str]:
        return "\n".join(filter(lambda line: line is not None, map(lambda stmt: stmt.outer_text, self._stmts)))

    @property
    def stmts(self) -> list[Statement]:
        """获取内部的语句列表。"""
        return self._stmts

    @property
    def text(self) -> str:
        return "\n".join(map(lambda stmt: stmt.text, self._stmts))

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        raise InternalCompilerException("Not implemented", self._src_info)

    def update_const_vars(self, const_vars: dict[VariableName, Expression]) -> dict[VariableName, Expression]:
        """更新所有子语句的常量变量映射（含被替换语句产生的映射）。"""
        const_vars.update(self._extra_const_vars)
        for stmt in self._stmts:
            const_vars = stmt.update_const_vars(const_vars)
        return const_vars

    @property
    def _inner_text(self) -> str:
        raise InternalCompilerException("Not implemented", self._src_info)


class DeclStmt(Statement):
    """变量声明语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable, namespace: list[NamespaceName]) -> None:
        """
        初始化变量声明语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param namespace: 命名空间路径。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._var_value: Optional[Expression] = None
        self._var: list[VariableName] = []
        self._namespace: list[NamespaceName] = namespace
        self._is_finished: bool = False
        self._const_vars: dict[VariableName, Expression] = {}

    def add_var(self, var_name: str, var_type_ref: TypeRef, is_global: bool) -> None:
        """添加一个变量声明。"""
        if not is_global:
            var = LocalVariableName(self._src_info, var_name, var_type_ref.return_type)
        else:
            var = GlobalVariableName(self._src_info, self._namespace, var_name, var_type_ref.return_type)
        self._var.append(var)
        if var_name != "_":
            # 丢弃变量不登记到符号表中，允许在同一作用域内多次声明
            self._var_states.set_declared([var])
            self._symbol_table.add(var, var_name, None)
        else:
            # 丢弃变量的C名称需要唯一，避免同一作用域内多次声明冲突
            var.rename("$_discard$" + str(self._symbol_table.get_counter()))

    def as_async(self) -> "Statement":
        for var in self._var:
            if getattr(var, "is_unsafe", False) or \
                    (isinstance(var.type, ClassName) and var.type.is_unsafe):
                # 对unsafe变量的写操作强制串行化（0.1要求）：
                # 该语句退化为同步执行，不做异步转换
                return self
        new_stmt = super().as_async()
        if self._var_value is not None:
            new_stmt._var_value = self._var_value.as_async()
            self._var_states.set_async_assigned(self._var)
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        if self._var_value is not None:
            new_stmt._var_value = self._var_value.as_inline(inline_mapping)
            new_stmt._inline_mapping.update(new_stmt._var_value.inline_mapping)
        for i, var in enumerate(self._var):
            new_stmt._inline_mapping[var.name] = self._symbol_table.get_counter()
            new_stmt._var[i].rename(new_stmt.inline_mapping[var.name])
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        if isinstance(self._var_value, CallOp):
            new_stmt = copy(self)
            new_stmt._var_value = self._var_value.check_tail_recursive(func_name)
            new_stmt._tail_recursive_mark = new_stmt._var_value.tail_recursive_mark
            return new_stmt
        return self

    @property
    def global_init_text(self) -> str:
        result = super().global_init_text
        return result + "\n" + self._var_value.global_init_text if \
            self._var_value is not None and self._var_value.global_init_text is not None else result

    def finish(self) -> None:
        """完成变量声明，进行类型检查和收包处理。"""
        self._is_finished = True
        if self._var_value is None:
            return
        expr_type = self._var_value.return_type
        var_names_num: int = len(self._var)
        if var_names_num > 1 and self._var_value is not None:
            self._var_value = UnpackExpr(self._src_info, self._symbol_table, self._var_value)
        for i, var in enumerate(self._var):
            if var.type.name == "auto":
                if self._var_value is None:
                    raise CompilerException("Can not infer variable type.", self._src_info)
                expr_type = self._var_value.return_type
                if isinstance(expr_type, TupleTypeName):
                    if i < var_names_num - 1:
                        self._var[i].type.set_real_type(expr_type.types[i])
                    else:
                        self._var[i].type.set_real_type(TupleTypeName(self._src_info, expr_type.types[i:]))
                else:
                    if var_names_num > 1:
                        raise CompilerException("Too many variables for unpacking.", self._src_info)
                    self._var[i].type.set_real_type(expr_type)
            else:
                if not isinstance(var.type, (FunctionTypeName, TupleTypeName, GenericArgument)) and \
                        (var.type.name, None) not in self._symbol_table:
                    # 函数类型与元组类型为匿名组合类型，无需注册为符号；
                    # 泛型参数在实例化时替换为具体类型
                    raise CompilerException(f"{var.type.raw_name} is not defined.", self._src_info)
        if isinstance(expr_type, TupleTypeName):
            if len(self._var) > len(expr_type.types):
                raise CompilerException("Too many variables for unpacking.", self._src_info)
            elif len(self._var) == len(expr_type.types):
                type_list: list[TypeName] = list(map(lambda var: var.type, self._var))
                for i, (t0, t1) in enumerate(zip(type_list, expr_type.types)):
                    if not t1.convertible_to(t0, self._symbol_table.symbols):
                        raise CompilerException(f"{t1.raw_name} (param {i}) cannot be assigned to {t0.raw_name}.",
                                                self._src_info)
            else:
                type_list: list[TypeName] = list(map(lambda var: var.type, self._var[:-1]))
                for i, (t0, t1) in enumerate(zip(type_list, expr_type.types[:len(type_list)])):
                    if not t1.convertible_to(t0, self._symbol_table.symbols):
                        raise CompilerException(f"{t1.raw_name} (param {i}) cannot be assigned to {t0.raw_name}.",
                                                self._src_info)
                if not TupleTypeName(self._src_info, expr_type.types[len(type_list):]).convertible_to(
                        self._var[-1].type, self._symbol_table.symbols):
                    raise CompilerException(
                        f"{TupleTypeName(self._src_info, expr_type.types[len(type_list):]).raw_name} cannot be assigned to {self._var[-1].type.raw_name}.",
                        self._src_info)
        else:
            if len(self._var) > 1:
                raise CompilerException("Too many variables for unpacking.", self._src_info)
            if self._var[0].type.name != "auto" and \
                    not expr_type.convertible_to(self._var[0].type, self._symbol_table.symbols):
                raise CompilerException(f"{expr_type.raw_name} cannot be assigned to {self._var[0].type.raw_name}.",
                                        self._src_info)

    @property
    def head_text(self) -> Optional[str]:
        if self._var_value is not None and len(self._var) > 0 and \
                isinstance(self._var_value, (CallOp, UnpackExpr)):
            # 与_inner_text一致：先设置返回值目标，
            # 使head_text包含调用/解包产生的临时变量声明
            self._var_value.set_returns(self._var)
        results = "\n".join(map(
            lambda var: f"{var.type_name_pair_calling};" if not isinstance(var.type, GenericArgument) else "",
            self._var
        ))
        results = "\n".join(filter(lambda x: x.strip() != "", results.split("\n")))
        if self._var_value is not None and self._var_value.head_text is not None:
            results += "\n" + self._var_value.head_text
        if isinstance(self._var_value, UnpackExpr):
            # 元组解包：解包链的head_text不包含被解包元组的临时变量声明，补上
            to_unpack = getattr(self._var_value, "_to_unpack", None)
            while isinstance(to_unpack, UnpackExpr):
                to_unpack = getattr(to_unpack, "_to_unpack", None)
            if isinstance(to_unpack, TupleRef) and to_unpack.head_text is not None:
                results += "\n" + to_unpack.head_text
        return self._indent_text(results)

    @property
    def input_variables(self) -> set[VariableName]:
        return self._var_value.used_variables if self._var_value is not None else set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._var_value = self._var_value.instantiation(type_args)
        new_stmt._var = list(map(lambda var: var.instantiation(var.name, type_args), self._var))
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        if self._var_value is not None and self._var_value.listener_name is not None:
            return dict(map(lambda var: (var, self._var_value.listener_name), self._var))
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set(self._var)

    def optimize(self) -> "Statement":
        if self._var_value is not None:
            self._var_value = self._var_value.optimize()
            if self._var_value.is_const and len(self._var) == 1 and not self._is_const_def:
                self._const_vars[self._var[0]] = self._var_value
                return _StmtList(self._src_info, self._symbol_table, self._var_states, [], self._const_vars)
        if isinstance(self._var_value, UnpackExpr):
            to_unpack = self._var_value.to_unpack
            if len(self._var) == 1:
                result = DeclStmt(self._src_info, self._symbol_table, self._var_states, self._namespace)
                result.set_var_value(to_unpack)
                result._add_var_object(self._var[0])
                return result
            if isinstance(to_unpack, TupleRef) and not self._is_const_def:
                to_unpack_const: list[Expression] = list(map(lambda expr: expr.optimize().is_const, to_unpack.expressions))
                results: list[DeclStmt] = [DeclStmt(self._src_info, self._symbol_table, self._var_states, self._namespace)
                                           for _ in range(len(self._var) - len(to_unpack_const))]
                result_count: int = 0
                expr_count: int = 0
                for i, var in enumerate(self._var[:-1]):
                    var_tuple_length: int = -1
                    if isinstance(self._var[i].type, TupleTypeName):
                        var_tuple_length = len(self._var[i].type.types)
                    if to_unpack[i].is_const and not self._is_const_def:
                        if var_tuple_length == -1:
                            self._const_vars[self._var[i]] = to_unpack[expr_count]
                            expr_count += 1
                        else:
                            self._const_vars[self._var[i]] = to_unpack[expr_count:expr_count + var_tuple_length]
                            expr_count += var_tuple_length
                        continue
                    result = results[result_count]
                    if var_tuple_length == -1:
                        result.set_var_value(to_unpack[expr_count])
                        expr_count += 1
                    else:
                        result.set_var_value(to_unpack[expr_count + var_tuple_length])
                        expr_count += var_tuple_length
                    result._add_var_object(self._var[i])
                    result_count += 1
                if len(self._var) == len(to_unpack):
                    if to_unpack[-1].is_const and not self._is_const_def:
                        self._const_vars[self._var[-1]] = to_unpack[-1]
                    else:
                        results[-1].set_var_value(to_unpack[-1])
                        results[-1]._add_var_object(self._var[-1])
                else:
                    results[-1].set_var_value(to_unpack[len(self._var):])
                    results[-1]._add_var_object(self._var[-1])
                return _StmtList(self._src_info, self._symbol_table, self._var_states, results, self._const_vars)
        return self

    @property
    def outer_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("Declaration is not finished.", self._src_info)
        if self._var_value is not None:
            return "\n".join(filter(lambda x: x is not None, [super().outer_text, self._var_value.outer_text]))
        return super().outer_text

    def set_var_value(self, var_value: Expression) -> None:
        """设置变量的初始值表达式。"""
        var_value.validate()
        self._var_value = var_value
        self._var_states.set_assigned(self._var)

    def set_vars_with_known_type(self, var_name_list: list[str], var_type_name_list: list[TypeName],
                                 is_global_list: list[bool]):
        """使用已知类型设置声明的变量列表。"""
        if not len(var_name_list) == len(var_type_name_list) or not len(var_type_name_list) == len(is_global_list):
            raise CompilerException("Invalid variable declaration.", self._src_info)
        var_names_num: int = len(var_name_list)
        if var_names_num > 1 and self._var_value is not None:
            self._var_value = UnpackExpr(self._src_info, self._symbol_table, self._var_value)
        for i, (var_name, var_type, is_global) in enumerate(zip(var_name_list, var_type_name_list, is_global_list)):
            if is_global:
                self._var.append(GlobalVariableName(self._src_info, self._namespace, var_name, var_type))
            else:
                self._var.append(LocalVariableName(self._src_info, var_name, var_type))

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        if self._var_value is not None:
            self._var_value = self._var_value.substitute(const_vars)
        return self

    def update_const_vars(self, const_vars: dict[VariableName, Expression]) -> dict[VariableName, Expression]:
        const_vars.update(self._const_vars)
        return const_vars

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        if self._var_value is not None:
            if not self._is_async:
                state = VariableState.ASSIGNED
            else:
                state = VariableState.ASYNC_ASSIGNED
        else:
            state = VariableState.DECLARED
        return dict(map(lambda var: (var, state), self._var))

    @property
    def var_types(self) -> TypeName:
        """获取声明的变量类型。"""
        if not self._is_finished:
            raise InternalCompilerException("Statement is not finished.", self._src_info)
        if len(self._var) > 1:
            return TupleTypeName(self._src_info, list(map(lambda var: var.type, self._var)))
        return self._var[0].type

    def _add_var_object(self, var: VariableName) -> None:
        """添加变量对象到内部列表。"""
        self._var.append(var)

    @property
    def _inner_text(self) -> str:
        if len(self._var) == 0:
            return ""
        if self._var_value is not None:
            if len(self._var) == 1:
                # 单变量声明：构造值表达式后直接赋值（函数调用已通过返回指针形参直接写入）
                if isinstance(self._var_value, (CallOp, UnpackExpr)):
                    self._var_value.set_returns(self._var)
                if self._var_value.front_text is not None:
                    front_text: str = self._var_value.front_text + "\n"
                else:
                    front_text = ""
                if not isinstance(self._var_value, (CallOp, UnpackExpr)):
                    deref: str = "*" if self._var[0].is_return else ""
                    front_text += f"{deref}{self._var[0].name} = {self._var_value.text};\n"
            else:
                self._var_value.set_returns(self._var)
                # 头声明统一由语句块（或异步包装）的head_text输出，避免重复声明
                if self._var_value.front_text is not None:
                    front_text: str = self._var_value.front_text + "\n"
                else:
                    front_text = ""
        else:
            front_text = ""
        return front_text


class AssignStmt(Statement):
    """赋值语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable, this_cls: Optional[ClassName] = None) -> None:
        """
        初始化赋值语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param this_cls: 当前类的类名（可选）。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._var: list[VariableName] = []
        self._var_value: Optional[Expression] = None
        self._is_async: bool = False
        self._is_finished: bool = False
        self._var_types: Optional[TypeName] = None
        self._const_vars: dict[VariableName, Expression] = {}
        self._this_cls: Optional[ClassName] = this_cls
        self._is_super: bool = False

    def add_var_name(self, var_name: str) -> None:
        """添加赋值目标变量名。"""
        if self._this_cls is not None and var_name == "this.super":
            # 调用父类的构造函数初始化this
            self._is_super = True
            return
        if self._this_cls is not None and var_name.startswith("this."):
            var_name = var_name[len("this."):]
            if var_name not in self._this_cls.properties:
                raise CompilerException(f"{var_name} is not a property of {self._this_cls.name}.", self._src_info)
            var_name_type = self._this_cls.properties[var_name].type
            symbol = LocalVariableName(self._src_info, "_thisObj->" + var_name, var_name_type)
        else:
            symbol = self._symbol_table[var_name, None]
        if not isinstance(symbol, VariableName):
            raise CompilerException(f"{var_name} is not a variable.", self._src_info)
        self._var.append(symbol)
        self._var_states.set_assigned([symbol])

    def as_async(self) -> "Statement":
        for var in self._var:
            if getattr(var, "is_unsafe", False) or \
                    (isinstance(var.type, ClassName) and var.type.is_unsafe):
                # 对unsafe变量的写操作强制串行化（0.1要求）：
                # 该语句退化为同步执行，不做异步转换
                return self
        new_stmt = super().as_async()
        new_stmt._var_value = self._var_value.as_async()
        new_stmt._is_async = True
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._var_value = self._var_value.as_inline(inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._var_value.inline_mapping)
        for i, var in enumerate(self._var):
            new_stmt._inline_mapping[var.name] = self._symbol_table.get_counter() if not var.is_global else var.name
            new_stmt._var[i].rename(new_stmt._inline_mapping[var.name])
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        if isinstance(self._var_value, CallOp):
            new_stmt = copy(self)
            new_stmt._var_value = self._var_value.check_tail_recursive(func_name)
            new_stmt._tail_recursive_mark = new_stmt._var_value.tail_recursive_mark
            return new_stmt
        return self

    @property
    def global_init_text(self) -> Optional[str]:
        result = super().global_init_text
        return result + "\n" + self._var_value.global_init_text if self._var_value.global_init_text is not None else result

    def finish(self) -> None:
        """完成赋值语句，进行类型检查和收包处理。"""
        expr_type = self._var_value.return_type
        if isinstance(expr_type, TupleTypeName):
            if len(expr_type.types) == 0:
                raise CompilerException("Cannot unpacking an empty tuple.", self._src_info)
            if len(self._var) > len(expr_type.types):
                raise CompilerException("Too many variables to unpacking.", self._src_info)
            elif len(self._var) == len(expr_type.types):
                type_list: list[TypeName] = list(map(lambda var: var.type, self._var))
                for i, (t0, t1) in enumerate(zip(type_list, expr_type.types)):
                    if not t1.convertible_to(t0, self._symbol_table.symbols):
                        raise CompilerException(f"{t1.raw_name} (param {i}) cannot be assigned to {t0.raw_name}.",
                                                self._src_info)
            else:
                type_list: list[TypeName] = list(map(lambda var: var.type, self._var[:-1]))
                for i, (t0, t1) in enumerate(zip(type_list, expr_type.types[:len(type_list)])):
                    if not t1.convertible_to(t0, self._symbol_table.symbols):
                        raise CompilerException(f"{t1.raw_name} (param {i}) cannot be assigned to {t0.raw_name}.",
                                                self._src_info)
                if not TupleTypeName(self._src_info, expr_type.types[len(type_list):]).convertible_to(
                        self._var[-1].type, self._symbol_table.symbols):
                    raise CompilerException(
                        f"{TupleTypeName(self._src_info, expr_type.types[len(type_list):]).raw_name} cannot be assigned to {self._var[-1].type.raw_name}.",
                        self._src_info)
        self._is_finished = True

    @property
    def head_text(self) -> Optional[str]:
        if isinstance(self._var_value, (CallOp, UnpackExpr)) and len(self._var) > 0:
            # 与_inner_text一致：先设置返回值目标，
            # 使head_text包含调用/解包产生的临时变量声明
            self._var_value.set_returns(self._var)
        result: Optional[str] = self._var_value.head_text if self._var_value is not None else None
        if isinstance(self._var_value, UnpackExpr):
            # 元组解包：解包链的head_text不包含被解包元组的临时变量声明，补上
            to_unpack = getattr(self._var_value, "_to_unpack", None)
            while isinstance(to_unpack, UnpackExpr):
                to_unpack = getattr(to_unpack, "_to_unpack", None)
            if isinstance(to_unpack, TupleRef) and to_unpack.head_text is not None:
                result = (result + "\n" + to_unpack.head_text) if result is not None else to_unpack.head_text
        if result is None:
            return None
        return self._indent_text(result)

    @property
    def input_variables(self) -> set[VariableName]:
        return self._var_value.used_variables

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._var_value = self._var_value.instantiation(type_args)
        new_stmt._var = list(map(lambda var: var.instantiation(var.name, type_args), self._var))
        if self._var_types is not None:
            new_stmt._var_types = self._var_types.instantiation(type_args)
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        if self._var_value is not None and self._var_value.listener_name is not None:
            return dict(map(lambda var: (var, self._var_value.listener_name), self._var))
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set(self._var)

    def optimize(self) -> "Statement":
        if self._var_value is not None:
            self._var_value = self._var_value.optimize()
            if self._var_value.is_const and len(self._var) == 1:
                self._const_vars[self._var[0]] = self._var_value
                return _StmtList(self._src_info, self._symbol_table, self._var_states, [], self._const_vars)
        if isinstance(self._var_value, UnpackExpr):
            to_unpack = self._var_value.to_unpack
            if len(self._var) == 1:
                result = AssignStmt(self._src_info, self._symbol_table, self._var_states)
                result.set_var_value(to_unpack)
                result._add_var_object(self._var[0])
                return result
            if isinstance(to_unpack, TupleRef):
                to_unpack_const: list[Expression] = list(
                    map(lambda expr: expr.optimize().is_const, to_unpack.expressions))
                results: list[AssignStmt] = [AssignStmt(self._src_info, self._symbol_table, self._var_states)] * (
                            len(self._var) - len(to_unpack_const))
                result_count: int = 0
                for i, var in enumerate(self._var[:-1]):
                    if to_unpack[i].is_const:
                        self._const_vars[self._var[i]] = to_unpack[i]
                        continue
                    result = results[result_count]
                    result.set_var_value(to_unpack[i])
                    result._add_var_object(self._var[i])
                    result_count += 1
                if len(self._var) == len(to_unpack):
                    if to_unpack[-1].is_const:
                        self._const_vars[self._var[-1]] = to_unpack[-1]
                    else:
                        results[-1].set_var_value(to_unpack[-1])
                        results[-1]._add_var_object(self._var[-1])
                else:
                    results[-1].set_var_value(to_unpack[len(self._var):])
                    results[-1]._add_var_object(self._var[-1])
                return _StmtList(self._src_info, self._symbol_table, self._var_states, results, self._const_vars)
        return self

    @property
    def outer_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("AssignStmt is not finished.", self._src_info)
        result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._var_value.outer_text]))
        if result == "":
            return None
        return result

    def set_var_value(self, var_value: Expression) -> None:
        """设置赋值表达式的值。"""
        var_value.validate()
        self._var_value = var_value

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        self._var_value = self._var_value.substitute(const_vars)
        return self

    def update_const_vars(self, const_vars: dict[VariableName, Expression]) -> dict[VariableName, Expression]:
        const_vars.update(self._const_vars)
        return const_vars

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        if not self._is_async:
            state = VariableState.ASSIGNED
        else:
            state = VariableState.ASYNC_ASSIGNED
        return dict(map(lambda var: (var, state), self._var))

    def _add_var_object(self, var: VariableName) -> None:
        """添加赋值目标变量对象到内部列表。"""
        self._var.append(var)

    @property
    def _inner_text(self) -> str:
        if self._is_super:
            if self._var_value is None or self._this_cls is None or self._this_cls.parent is None:
                raise CompilerException("this.super requires a parent class constructor call.", self._src_info)
            parent = self._this_cls.parent
            if not isinstance(self._var_value, CallOp):
                raise CompilerException("this.super requires a constructor call.", self._src_info)
            # 使用父类实际注册的__new__方法的C名称
            parent_new_name = None
            for (m_name, _), m in parent.methods.items():
                if m_name == "__new__" and m.cls.name == parent.name:
                    parent_new_name = m.name
                    break
            if parent_new_name is None:
                raise CompilerException("Parent class has no constructor.", self._src_info)
            args: str = ", ".join(map(lambda a: a.text, self._var_value._arg_list))
            if args != "":
                args += ", "
            return f"{parent_new_name}({args}&_this, listener);"
        if self._var_value is None:
            return ""
        if len(self._var) == 1:
            # 单变量赋值：构造值表达式后直接赋值
            # （函数调用已通过返回指针形参直接写入）
            if isinstance(self._var_value, (CallOp, UnpackExpr)):
                self._var_value.set_returns(self._var)
            if self._var_value.front_text is not None:
                front_text: str = self._var_value.front_text + "\n"
            else:
                front_text = ""
            if not isinstance(self._var_value, (CallOp, UnpackExpr)):
                deref: str = "*" if self._var[0].is_return else ""
                front_text += f"{deref}{self._var[0].name} = {self._var_value.text};\n"
            return front_text
        # 多变量赋值（元组解包）
        self._var_value.set_returns(self._var)
        if self._var_value.front_text is not None:
            return self._var_value.front_text + "\n"
        return ""


class OpStmt(Statement):
    """操作语句（表达式语句）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化操作语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._expr: Expression = CExpr(src_info, symbol_table)

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        new_stmt._expr = self._expr.as_async()
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._expr = self._expr.as_inline(inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._expr.inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        if isinstance(self._expr, CallOp):
            new_stmt = copy(self)
            new_stmt._expr = self._expr.check_tail_recursive(func_name)
            new_stmt._tail_recursive_mark = new_stmt._expr.tail_recursive_mark
            return new_stmt
        return self

    @property
    def global_init_text(self) -> str:
        result = super().global_init_text
        return result + "\n" + self._expr.global_init_text if self._expr.global_init_text is not None else result

    @property
    def head_text(self) -> Optional[str]:
        return self._indent_text(self._expr.head_text) if self._expr.head_text is not None else None

    @property
    def input_variables(self) -> set[VariableName]:
        return self._expr.used_variables

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._expr = self._expr.instantiation(type_args)
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return True

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set()

    def optimize(self) -> "Statement":
        self._expr = self._expr.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        if self._expr is None:
            raise CompilerException("OpStmt is not finished.", self._src_info)
        result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._expr.outer_text]))
        if result == "":
            return None
        return result

    def set_expr(self, expr: Expression) -> None:
        """设置操作语句的表达式。"""
        expr.validate()
        self._expr = expr

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        self._expr = self._expr.substitute(const_vars)
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        results = list(filter(lambda x: x is not None, [self._expr.front_text, self._expr.release_text]))
        return "\n".join(results)


class DelSuperStmt(Statement):
    """del(super);语句：调用编译器为包装类生成的默认成员清理函数。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 this_cls: Optional[ClassName] = None) -> None:
        super().__init__(src_info, symbol_table, var_states)
        self._this_cls: Optional[ClassName] = this_cls

    def as_async(self) -> "Statement":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        return self

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def global_init_text(self) -> str:
        return ""

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return set()

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        return self

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    @property
    def is_finished(self) -> bool:
        return True

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set()

    def optimize(self) -> "Statement":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        if self._this_cls is None:
            raise CompilerException("del(super) can only be used in wrapper class destructors.", self._src_info)
        return f"{self._this_cls.name}$__del__super$_0(_this, listener);"


class ReturnStmt(Statement):
    """返回语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化返回语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._finally_stmt_list: list[Statement] = []

    def as_async(self) -> "Statement":
        return super().as_async()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._inline_mapping = inline_mapping
        for i, finally_stmt in enumerate(self._finally_stmt_list):
            self._finally_stmt_list[i] = finally_stmt.as_inline(new_stmt.inline_mapping)
            new_stmt.inline_mapping.update(new_stmt._finally_stmt_list[i].inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def drop_out(self) -> bool:
        return True

    @property
    def global_init_text(self) -> str:
        return super().global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        self._finally_stmt_list.append(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._finally_stmt_list = list(map(lambda finally_stmt: finally_stmt.instantiation(type_args), self._finally_stmt_list))
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return True

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set()

    def optimize(self) -> "Statement":
        self._finally_stmt_list = list(map(lambda finally_stmt: finally_stmt.optimize(), self._finally_stmt_list))
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        finally_text: str = "\n".join(map(lambda finally_stmt: finally_stmt.text, self._finally_stmt_list))
        if finally_text != "":
            finally_text += "\n"
        return finally_text + "return;"


class ThrowStmt(Statement):
    """抛出异常语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化抛出异常语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._to_throw_expr: Optional[Expression] = None
        self._finally_stmt_list: list[Statement] = []

    def as_async(self) -> "Statement":
        return super().as_async()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._to_throw_expr = self._to_throw_expr.as_inline(inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._to_throw_expr.inline_mapping)
        for i, finally_stmt in enumerate(self._finally_stmt_list):
            self._finally_stmt_list[i] = finally_stmt.as_inline(new_stmt.inline_mapping)
            new_stmt.inline_mapping.update(new_stmt._finally_stmt_list[i].inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def drop_out(self) -> bool:
        return True

    @property
    def global_init_text(self) -> str:
        result = super().global_init_text
        return result + "\n" + self._to_throw_expr.global_init_text if self._to_throw_expr.global_init_text is not None else result

    @property
    def head_text(self) -> Optional[str]:
        return self._indent_text(self._to_throw_expr.head_text)

    @property
    def input_variables(self) -> set[VariableName]:
        return self._to_throw_expr.used_variables | set(
            *map(lambda finally_stmt: finally_stmt.input_variables, self._finally_stmt_list)
        )

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        self._finally_stmt_list.append(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "ThrowStmt":
        new_stmt = copy(self)
        new_stmt._to_throw_expr = self._to_throw_expr.instantiation(type_args)
        new_stmt._finally_stmt_list = list(map(lambda finally_stmt: finally_stmt.instantiation(type_args), self._finally_stmt_list))
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return self._to_throw_expr is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        result = {}
        result.update(map(lambda var: var.new_listeners, self._finally_stmt_list))
        return result

    @property
    def new_variables(self) -> set[VariableName]:
        return set.union(*map(lambda finally_stmt: finally_stmt.new_variables, self._finally_stmt_list))

    def optimize(self) -> "Statement":
        self._finally_stmt_list = list(map(lambda finally_stmt: finally_stmt.optimize(), self._finally_stmt_list))
        return self

    @property
    def outer_text(self) -> Optional[str]:
        if self._to_throw_expr is None:
            raise CompilerException("ThrowStmt is not finished.", self._src_info)
        result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._to_throw_expr.outer_text]))
        if result == "":
            return None
        return result

    def set_expr(self, expr: Expression) -> None:
        """设置抛出的异常表达式。"""
        expr.validate()
        # noinspection PyTypeChecker
        if not expr.return_type.convertible_to(ExceptionTypeName, self._symbol_table.symbols):
            raise CompilerException(f"Type {expr.return_type.raw_name} cannot be thrown.", self._src_info)
        self._to_throw_expr = expr

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        self._to_throw_expr = self._to_throw_expr.substitute(const_vars)
        self._finally_stmt_list = list(map(lambda finally_stmt: finally_stmt.substitute(const_vars), self._finally_stmt_list))
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        finally_text: str = "\n".join(map(lambda finally_stmt: finally_stmt.text, self._finally_stmt_list))
        if finally_text != "":
            finally_text += "\n"
        result: list[str] = list(filter(lambda x: x is not None, [
            self._to_throw_expr.front_text,
            f"listener->exc = {self._to_throw_expr.text};",
            # 同步更新本函数的异常缓存，使后续语句的异常检查生效
            "$$exc = listener->exc;"
        ]))
        return finally_text + "\n".join(result)


class CStmt(Statement):
    """原生 C 代码语句，用于直接嵌入 C 代码片段。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化原生 C 代码语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._text: Optional[str] = None

    def add_text(self, text: str) -> None:
        """追加 C 代码文本。"""
        if self._text is None:
            self._text = text
        else:
            self._text += "\n" + text

    def finish(self) -> None:
        """完成 C 代码语句的构建。"""

    def as_async(self) -> "Statement":
        return super().as_async()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_expr = copy(self)
        new_expr._inline_mapping = inline_mapping
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def global_init_text(self) -> str:
        return super().global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        return self

    @property
    def is_finished(self) -> bool:
        return self._text is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set()

    def optimize(self) -> "Statement":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return super().outer_text

    def set_text(self, text: str) -> None:
        """设置 C 代码文本。"""
        self._text = text

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        return self._text if self._text is not None else ""


class _CondKw(Enum):
    """条件关键字枚举，表示 if、elif 和 else。"""
    IF = "if"
    ELIF = "else if"
    ELSE = "else"


class CondStmt(Statement):
    """条件语句基类，表示 if、elif 或 else 分支。"""

    def __init__(self, kw: _CondKw, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化条件语句。
        :param kw: 条件关键字。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._cond_expr: Optional[Expression] = None
        self._stmt: Optional[Statement] = None
        self._cond_kw: _CondKw = kw

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        if self._cond_expr is not None:
            new_stmt._cond_expr = self._cond_expr.as_async()
        new_stmt._stmt = self._stmt.as_async()
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        if self._cond_expr is not None:
            new_stmt._cond_expr = self._cond_expr.as_inline(inline_mapping)
            new_stmt._inline_mapping.update(new_stmt._cond_expr.inline_mapping)
        new_stmt._stmt = self._stmt.as_inline(new_stmt.inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._stmt.inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.check_tail_recursive(func_name)
        return new_stmt

    @property
    def cond_kw(self) -> _CondKw:
        """获取条件关键字（if、elif 或 else）。"""
        return self._cond_kw

    @property
    def global_init_text(self) -> str:
        # else分支无条件表达式；防御_stmt未设置的情况
        parts: list[Optional[str]] = [super().global_init_text]
        if self._cond_expr is not None:
            parts.append(self._cond_expr.global_init_text)
        if self._stmt is not None:
            parts.append(self._stmt.global_init_text)
        result = "\n".join(filter(lambda x: x is not None, parts))
        return result

    @property
    def head_text(self) -> Optional[str]:
        # else分支无条件表达式
        if self._cond_expr is None:
            return None
        return self._indent_text(self._cond_expr.head_text)

    @property
    def input_variables(self) -> set[VariableName]:
        return self._cond_expr.used_variables if self._cond_kw != _CondKw.ELSE else set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        self._stmt.insert_finally_stmt(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        if self._cond_expr is not None:
            new_stmt._cond_expr = self._cond_expr.instantiation(type_args)
        if self._stmt is not None:
            new_stmt._stmt = self._stmt.instantiation(type_args)
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return (self._cond_expr is not None or self._cond_kw == _CondKw.ELSE) and self._stmt is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return self._stmt.new_listeners

    @property
    def new_variables(self) -> set[VariableName]:
        return self._stmt.new_variables

    def optimize(self) -> "Statement":
        if self._cond_expr is not None:
            self._cond_expr = self._cond_expr.optimize()
        if self._stmt is not None:
            self._stmt = self._stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        # else分支无条件表达式
        if self._cond_expr is None:
            result = super().outer_text
        else:
            result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._cond_expr.outer_text]))
        if result is None or result == "":
            return None
        return result

    def set_expr_cond(self, expr: Expression) -> None:
        """设置条件表达式。"""
        expr.validate()
        self._cond_expr = expr

    def set_stmt(self, stmt: Statement) -> None:
        """设置条件分支内的语句。"""
        stmt.indent()
        self._stmt = stmt

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        if self._cond_expr is not None:
            self._cond_expr = self._cond_expr.substitute(const_vars)
        self._stmt = self._stmt.substitute(const_vars)
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return self._stmt.variables_states

    @property
    def _inner_text(self) -> str:
        head_text: Optional[str] = self._stmt.head_text
        if head_text is not None:
            head_text += "\n"
        else:
            head_text = ""
        if self._cond_kw == _CondKw.ELSE:
            front_text: str = ""
            stmt_begin = "else"
        else:
            front_text = self._cond_expr.front_text + "\n" if self._cond_expr.front_text is not None else ""
            stmt_begin = f"{self._cond_kw.value} ({self._cond_expr.text})"
        return front_text + stmt_begin + "{\n" + head_text + self._stmt.text + "\n}"


class ElifStmt(CondStmt):
    """Elif 分支语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化 elif 分支语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(_CondKw.ELIF, src_info, symbol_table, var_states)


class ElseStmt(CondStmt):
    """Else 分支语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化 else 分支语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(_CondKw.ELSE, src_info, symbol_table, var_states)

    def set_cond_expr(self, expr: Expression) -> None:
        """重写父类方法，else 分支不能有条件表达式。"""
        raise CompilerException("ElseStmt can't have a condition.", self._src_info)


class IfStmt(CondStmt):
    """If 条件分支语句，可包含多条 elif 和 else 分支。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化 if 语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(_CondKw.IF, src_info, symbol_table, var_states)
        self._branches: list[CondStmt] = []

    def add_branch(self, branch: CondStmt) -> None:
        """添加 elif 或 else 分支。"""
        self._branches.append(branch)

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        new_stmt._branches = list(map(lambda b: b.as_async(), self._branches))
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = super().as_inline(inline_mapping)
        new_stmt._branches = list(map(lambda b: b.as_inline(new_stmt.inline_mapping), self._branches))
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.check_tail_recursive(func_name)
        for i, branch in enumerate(self._branches):
            # noinspection PyTypeChecker
            new_stmt._branches[i] = branch.check_tail_recursive(func_name).insert_finally_stmt(new_stmt._stmt)
        marks: list[Optional[str]] = list(map(lambda x: x.tail_recursive_mark, self._branches)) + [self._stmt.tail_recursive_mark]
        mark: list[str] = list(filter(lambda x: x is not None, marks))
        new_stmt._tail_recursive_mark = mark[0] if len(mark) > 0 else None
        return new_stmt

    @property
    def global_init_text(self) -> str:
        return "\n".join(filter(lambda x: x is not None and x.strip() != "", [
            super().global_init_text,
            *map(lambda b: b.global_init_text, self._branches)
        ]))

    @property
    def head_text(self) -> Optional[str]:
        result = "\n".join(filter(lambda x: x is not None and x.strip() != "", [
            super().head_text,
            *map(lambda b: b.head_text, self._branches)
        ]))
        return result if result.strip() != "" else None

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        super().insert_finally_stmt(finally_stmt)
        for branch in self._branches:
            branch.insert_finally_stmt(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = super().instantiation(type_args)
        new_stmt._branches = list(map(lambda b: b.instantiation(type_args), self._branches))
        return new_stmt

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        result: dict[VariableName, str] = dict(self._stmt.new_listeners)
        for branch in self._branches:
            result.update(branch.new_listeners)
        return result

    @property
    def new_variables(self) -> set[VariableName]:
        return self._stmt.new_variables | set().union(*map(lambda b: b.new_variables, self._branches))

    def optimize(self) -> "Statement":
        super().optimize()
        for i, branch in enumerate(self._branches):
            self._branches[i] = branch.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n".join(filter(lambda x: x is not None and x.strip() != "", [
            super().outer_text,
            *map(lambda b: b.outer_text, self._branches)
        ]))
        return result if result.strip() != "" else None

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        super().substitute(const_vars)
        for i, branch in enumerate(self._branches):
            self._branches[i] = branch.substitute(const_vars)
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        result: dict[VariableName, VariableState] = dict(self._stmt.variables_states)
        for branch in self._branches:
            result.update(branch.variables_states)
        return result

    @property
    def input_variables(self) -> set[VariableName]:
        return self._cond_expr.used_variables | self._stmt.input_variables | set().union(*map(lambda x: x.input_variables, self._branches))

    @property
    def _inner_text(self) -> str:
        """渲染if及其全部elif/else分支。"""
        result: str = super()._inner_text
        for branch in self._branches:
            result += "\n" + branch._inner_text
        return result


class CatchStmt(Statement):
    """异常捕获语句（catch 块）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化异常捕获语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._except_decl: Optional[VariableName] = None
        self._stmt: Optional[Statement] = None
        self._success_jump_to: str = ""
        self._jump_mark = ""

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        new_stmt._stmt = self._stmt.as_async()
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.as_inline(new_stmt.inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._stmt.inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.check_tail_recursive(func_name)
        new_stmt._tail_recursive_mark = new_stmt._stmt.tail_recursive_mark
        return new_stmt

    @property
    def global_init_text(self) -> str:
        result = super().global_init_text
        return result + "\n" + self._stmt.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return self._indent_text(self._except_decl.type_name_pair_calling + ";")

    @property
    def input_variables(self) -> set[VariableName]:
        return self._stmt.input_variables

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        self._stmt.insert_finally_stmt(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "CatchStmt":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.instantiation(type_args)
        new_stmt._except_decl = self._except_decl.instantiation(self._except_decl.name, type_args)
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return self._stmt is not None and self._except_decl is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return self._stmt.new_listeners

    @property
    def new_variables(self) -> set[VariableName]:
        return self._stmt.new_variables | {self._except_decl}

    def optimize(self) -> "Statement":
        self._stmt = self._stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._stmt.outer_text]))
        if result == "":
            return None
        return result

    def remove_mark(self) -> None:
        super().remove_mark()
        self._stmt.remove_mark()

    def set_except_decl(self, except_decl: VariableName) -> None:
        """设置异常捕获变量声明。"""
        self._except_decl = except_decl
        self._symbol_table.add(except_decl, except_decl.name, None)
        self._var_states.set_assigned([except_decl])

    def set_stmt(self, stmt: Statement) -> None:
        """设置 catch 块内的语句。"""
        stmt.indent()
        self._stmt = stmt

    def set_success_jump_to(self, jump_to: str) -> None:
        """设置异常处理成功后的跳转目标标签。"""
        self._success_jump_to = jump_to

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        self._stmt = self._stmt.substitute(const_vars)
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return self._stmt.variables_states

    @property
    def _inner_text(self) -> str:
        except_vtable_name: str = self._except_decl.type.name + "$$vtable"
        result: list[Optional[str]] = [
            f"if ({CONVERTIBLE_TO_FUNC}($$exc->$$vtable, &{except_vtable_name})) {{",
            self._stmt.head_text,
            f"\t{self._except_decl.type_name_pair_calling} = $$exc;",
            self._stmt.text,
            f"\t{self._except_decl.type.name}$__del__$_0({self._except_decl.name}, listener);",
            f"\t{self._except_decl.name} = NULL;",
            f"\tgoto {self._success_jump_to};",
            "}"
        ]
        return "\n".join(list(filter(lambda x: x is not None, result)))


class FinallyStmt(Statement):
    """Finally 语句（资源清理块）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化 finally 语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._stmt: Optional[Statement] = None

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        new_stmt._stmt = self._stmt.as_async()
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.as_inline(new_stmt.inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._stmt.inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def global_init_text(self) -> Optional[str]:
        return self._stmt.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return self._stmt.input_variables

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._stmt = self._stmt.instantiation(type_args)
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return self._stmt is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return self._stmt.new_listeners

    @property
    def new_variables(self) -> set[VariableName]:
        return self._stmt.new_variables

    def optimize(self) -> "Statement":
        self._stmt = self._stmt.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n".join(filter(lambda x: x is not None, [super().outer_text, self._stmt.outer_text]))
        if result == "":
            return None
        return result

    def remove_mark(self) -> None:
        super().remove_mark()
        self._stmt.remove_mark()

    def set_stmt(self, stmt: Statement) -> None:
        """设置 finally 块内的语句。"""
        stmt.indent()
        self._stmt = stmt

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "FinallyStmt":
        self._stmt = self._stmt.substitute(const_vars)
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return self._stmt.variables_states

    @property
    def _inner_text(self) -> str:
        result: list[str] = [
            "do {",
            self._stmt.text,
            "} while (0);"
        ]
        return "\n".join(result)


class TryStmt(Statement):
    """Try 异常处理语句，包含 try、catch 和 finally 块。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化 try 语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._try_stmt: Optional[Statement] = None
        self._except_stmt: list[CatchStmt] = []
        self._finally_stmt: Optional[FinallyStmt] = None
        self._exc_mark_name: str = self._symbol_table.get_counter()
        self._finally_mark_name: str = self._symbol_table.get_counter()
        self._is_finished: bool = False

    def add_except_stmt(self, except_stmt: CatchStmt) -> None:
        """添加一个 catch 异常捕获子句。"""
        except_stmt.indent()
        except_stmt.indent()
        except_stmt.set_success_jump_to(self._finally_mark_name)
        except_stmt.set_jump_mark(self._finally_mark_name)
        self._except_stmt.append(except_stmt)

    def as_async(self) -> "Statement":
        # noinspection PyTypeChecker
        new_stmt: TryStmt = super().as_async()
        new_stmt._try_stmt = self._try_stmt.as_async()
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._try_stmt = self._try_stmt.as_inline(new_stmt.inline_mapping)
        new_stmt._inline_mapping.update(new_stmt._try_stmt.inline_mapping)
        for i, except_stmt in enumerate(new_stmt._except_stmt):
            # noinspection PyTypeChecker
            new_stmt._except_stmt[i] = except_stmt.as_inline(new_stmt.inline_mapping)
            new_stmt._inline_mapping.update(except_stmt.inline_mapping)
        if new_stmt._finally_stmt is not None:
            # noinspection PyTypeChecker
            new_stmt._finally_stmt = new_stmt._finally_stmt.as_inline(new_stmt.inline_mapping)
            new_stmt._inline_mapping.update(new_stmt._finally_stmt.inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        new_stmt = copy(self)
        new_stmt._try_stmt = self._try_stmt.check_tail_recursive(func_name)
        mark: Optional[str] = None
        for i, except_stmt in enumerate(new_stmt._except_stmt):
            # noinspection PyTypeChecker
            new_stmt._except_stmt[i] = except_stmt.check_tail_recursive(func_name)
            if mark is None:
                mark = new_stmt._except_stmt[i].tail_recursive_mark
        self._tail_recursive_mark = mark
        return new_stmt

    @property
    def global_init_text(self) -> Optional[str]:
        result: str = self._try_stmt.global_init_text
        return result if result is not None and result.strip() != "" else None

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return self._try_stmt.input_variables | set(
            *map(lambda except_stmt: except_stmt.input_variables, self._except_stmt)
        )

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        self._try_stmt.insert_finally_stmt(finally_stmt)
        for exc in self._except_stmt:
            exc.insert_finally_stmt(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._try_stmt = self._try_stmt.instantiation(type_args)
        new_stmt._except_stmt = list(map(lambda except_stmt: except_stmt.instantiation(type_args), self._except_stmt))
        return new_stmt

    @property
    def is_finished(self) -> bool:
        return len(self._except_stmt) > 0

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return self._try_stmt.new_variables | set.union(
            *map(lambda except_stmt: except_stmt.new_variables, self._except_stmt))

    def optimize(self) -> "Statement":
        self._try_stmt = self._try_stmt.optimize()
        self._except_stmt = list(map(lambda except_stmt: except_stmt.optimize(), self._except_stmt))
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return "\n".join(filter(lambda x: x is not None, [
            super().outer_text,
            self._try_stmt.outer_text,
            *map(lambda except_stmt: except_stmt.outer_text, self._except_stmt)
        ]))

    def remove_mark(self) -> None:
        super().remove_mark()
        self._try_stmt.remove_mark()
        for except_stmt in self._except_stmt:
            except_stmt.remove_mark()
        if self._finally_stmt is not None:
            self._finally_stmt.remove_mark()

    def set_finally_stmt(self, finally_stmt: "Statement") -> None:
        """设置 finally 块语句。"""
        if not isinstance(finally_stmt, FinallyStmt):
            raise CompilerException("The statement should to be a finally statement.", self._src_info)
        self._finally_stmt = finally_stmt

    def set_stmt(self, stmt: Statement) -> None:
        """设置 try 块内的语句。"""
        stmt.indent()
        self._try_stmt = stmt
        self._try_stmt.set_jump_mark(self._exc_mark_name)

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        self._try_stmt = self._try_stmt.substitute(const_vars)
        self._except_stmt = list(map(lambda except_stmt: except_stmt.substitute(const_vars), self._except_stmt))
        self._finally_stmt = self._finally_stmt.substitute(const_vars) if self._finally_stmt is not None else None
        return self

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        result = self._try_stmt.variables_states
        for except_stmt in self._except_stmt:
            result.update(except_stmt.variables_states)
        return result

    @property
    def _inner_text(self) -> str:
        finally_text: list[str] = [
            *map(lambda x: "\t" + x, self._finally_stmt.text.split("\n"))
        ] if self._finally_stmt is not None else []
        result: str = "\n".join(list(filter(lambda x: x is not None, [
            "do {",
            self._try_stmt.text,
            f"goto {self._finally_mark_name};",
            "} while (0);",
            f"{self._exc_mark_name}:",
            *map(lambda except_stmt: except_stmt.text, self._except_stmt),
            f"{self._finally_mark_name}:",
            *finally_text
        ])))
        return result


class TypeDefStmt(Statement):
    """类型定义语句（typedef）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable, dst_type_name: str) -> None:
        """
        初始化类型定义语句。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param dst_type_name: 目标类型名称。
        """
        super().__init__(src_info, symbol_table, var_states)
        # noinspection PyTypeChecker
        self._src_type_decl: Optional[TypeName] = None
        self._dst_type_name: str = dst_type_name

    def as_async(self) -> "Statement":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        return self

    def check_tail_recursive(self, func_name: str) -> "Statement":
        return self

    @property
    def global_init_text(self) -> str:
        return super().global_init_text

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        if self._src_type_decl is None:
            raise CompilerException("TypeDefStmt must have a type.", self._src_info)
        result = copy(self)
        result._src_type_decl = self._src_type_decl.instantiation(type_args)
        return result

    @property
    def is_finished(self) -> bool:
        return self._src_type_decl is not None

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set()

    def optimize(self) -> "Statement":
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    def set_type(self, t: TypeRef) -> None:
        """设置要定义的源类型。"""
        self._src_type_decl = t.return_type
        self._symbol_table.add(t.return_type, self._dst_type_name, None)

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        if self._src_type_decl is None:
            raise CompilerException("TypeDefStmt must have a type.", self._src_info)
        return f"typedef {self._src_type_decl.name} {self._dst_type_name};"


class _ProcessingMode(Enum):
    """语句块处理模式枚举，表示普通、条件分支或异常处理模式。"""
    NORMAL = 0
    CONDITIONAL = 1
    TRY_CATCH = 2


class CleanupBlock(CStmt):

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 to_released_vars: list[VariableName], jump_label: str = "$$cleanup:") -> None:
        super().__init__(src_info, symbol_table, var_states)
        self._to_released_vars: list[VariableName] = to_released_vars
        self.add_text(jump_label)
        for v in self._to_released_vars:
            self.add_text(f"if ({v.name}) {{ {v.free_text} }}")

    @property
    def text(self) -> str:
        return self._inner_text


class BlockStmt(Statement):
    """语句块，包含多条子语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化语句块。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states, single_stmt=False)
        self._stmt: list[Statement] = []
        self._release_stmt_list: list[Statement] = []
        self._is_async: bool = False
        self._is_finished: bool = False
        self._outer_variables: dict[VariableName, VariableState] = var_states.state.copy()
        self._inner_variables: dict[VariableName, VariableState] = {}
        self._listeners: dict[VariableName, str] = {}
        self._input_variables: set[VariableName] = set()
        self._new_variables: list[VariableName] = []
        self._used_outer_variables: list[VariableName] = []
        self._is_closure: bool = False
        self._closure_struct_setting_code: str = ""
        self._closure_struct_def: str = ""
        self._processing_mode: _ProcessingMode = _ProcessingMode.NORMAL
        self._drops_out: bool = False
        self._cleanup_mark_name: str = self._symbol_table.get_counter()
        self._after_cleanup_mark_name: str = self._cleanup_mark_name + "_after"

    @property
    def drop_out(self) -> bool:
        """获取语句块是否在所有路径上都会导致函数退出。"""
        return self._drops_out

    def add_stmt(self, stmt: Statement) -> None:
        """向语句块中添加一条子语句。"""
        if not stmt.is_finished:
            if not isinstance(stmt, TryStmt):
                raise CompilerException("Statement is not finished.", stmt.src_info)
        if isinstance(stmt, CondStmt) and stmt.cond_kw == _CondKw.IF:
            self._processing_mode = _ProcessingMode.CONDITIONAL
        elif isinstance(stmt, TryStmt):
            self._processing_mode = _ProcessingMode.TRY_CATCH
        elif isinstance(stmt, CondStmt) and stmt.cond_kw != _CondKw.IF:
            self._validate_conditional_mode(stmt)
            return
        elif isinstance(stmt, CatchStmt) or isinstance(stmt, FinallyStmt):
            self._validate_try_catch_mode(stmt)
            return
        if isinstance(stmt, CondStmt) and stmt._stmt is not None and stmt._stmt.drop_out:
            # 提前退出（return/throw）的分支：其赋值只发生在提前退出路径上，
            # 不参与外层的线性赋值状态（return模式）
            var_states: dict[VariableName, VariableState] = {}
        else:
            var_states: dict[VariableName, VariableState] = stmt.variables_states
        for k, v in var_states.items():
            if k.name == "_":
                # 丢弃变量可以在同一作用域内被多次声明和赋值
                continue
            if k in self._inner_variables:
                current_state = self._inner_variables[k]
                if current_state == VariableState.DECLARED and v == VariableState.DECLARED:
                    raise CompilerException(f"Variable {k.raw_name} is already declared.", stmt.src_info)
                if current_state == VariableState.DECLARED and v > VariableState.DECLARED:
                    self._inner_variables[k] = v
                if current_state > VariableState.DECLARED:
                    raise CompilerException(f"Variable {k.raw_name} is already assigned.", stmt.src_info)
            elif k in self._outer_variables:
                current_state = self._outer_variables[k]
                if v == VariableState.DECLARED:
                    raise CompilerException(f"Variable {k.raw_name} is already declared.", stmt.src_info)
                if current_state == VariableState.DECLARED and v > VariableState.DECLARED:
                    self._inner_variables[k] = v
                    self._new_variables.append(k)
                if current_state > VariableState.DECLARED:
                    raise CompilerException(f"Variable {k.raw_name} is already assigned.", stmt.src_info)
            else:
                self._inner_variables[k] = v
        for var in stmt.input_variables:
            if var in self._listeners:
                wait_stmt = CStmt(stmt.src_info, self._symbol_table, self._var_states)
                wait_text = "\n".join([
                    f"{LISTENER_WAIT_FUNC}({self._listeners[var]});",
                    f"free({self._listeners[var]}$$_call);"
                ])
                wait_stmt.set_text(wait_text)
                self._stmt.append(wait_stmt)
                if var in self._outer_variables:
                    self._outer_variables[var] = VariableState.ASSIGNED
                else:
                    self._inner_variables[var] = VariableState.ASSIGNED
                del self._listeners[var]
        self._listeners.update(stmt.new_listeners)
        self._stmt.append(stmt)
        self._input_variables |= stmt.input_variables
        # 仅减去块内已产生（inner）与外部已赋值（ASSIGNED）的变量；
        # 外部已声明但尚未赋值的变量保留在输入集合中，使fn函数体的
        # 依赖排序（_sort_stmt）能找到其在本块兄弟语句中的生产者，
        # 否则声明语句会被当作无用语句丢弃
        self._input_variables -= self._inner_variables.keys()
        self._input_variables -= set(
            k for k, v in self._outer_variables.items() if v == VariableState.ASSIGNED)

    def as_async(self) -> "Statement":
        new_stmt = super().as_async()
        new_stmt._stmt = list(map(lambda stmt: stmt.as_async(), self._stmt))
        new_stmt._is_async = True
        return new_stmt

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        new_stmt = copy(self)
        for i, stmt in enumerate(self._stmt):
            new_stmt._stmt[i] = stmt.as_inline(inline_mapping)
            new_stmt._inline_mapping.update(new_stmt._stmt[i].inline_mapping)
        return new_stmt

    def check_tail_recursive(self, func_name: str) -> "Statement":
        new_stmt = copy(self)
        # 标记/跳转标签C语句属于结构性代码，从后向前找最后一条实质语句
        for i in range(len(self._stmt) - 1, -1, -1):
            if isinstance(self._stmt[i], CStmt):
                continue
            new_stmt._stmt[i] = self._stmt[i].check_tail_recursive(func_name)
            new_stmt._tail_recursive_mark = new_stmt._stmt[i].tail_recursive_mark
            break
        return new_stmt

    @property
    def closure_struct_setting_code(self) -> str:
        """获取闭包结构体设置代码。"""
        return self._closure_struct_setting_code

    def finish(self) -> None:
        """完成语句块的设置，进行变量清理和代码生成。"""
        # 块中任何会导致退出的语句（如return）都意味着其后代码不可达
        self._drops_out = any(map(lambda s: s.drop_out, self._stmt))
        self._stmt.reverse()
        used_variables: set[VariableName] = set()
        new_stmt_list: list[Statement] = []
        for stmt in self._stmt:
            stmt_used_variables: set[VariableName] = stmt.input_variables
            if isinstance(stmt, BlockStmt):
                # 嵌套语句块使用的外层变量同样属于本块（供闭包捕获等使用）
                stmt_used_variables = stmt_used_variables | set(stmt._used_outer_variables)
            for var in stmt_used_variables:
                if var not in used_variables and var not in self._outer_variables and not var.is_global:
                    used_variables.add(var)
                    # 变量已在本块内完成最后一次使用并释放，不再向外层传播
                    self._input_variables.discard(var)
                    if var.is_object:
                        release_stmt = OpStmt(stmt.src_info, self._symbol_table, self._var_states)
                        call_op = CallOp(stmt.src_info, self._symbol_table)
                        call_op._is_internal = True
                        attr_op = AttrOp(stmt.src_info, self._symbol_table)
                        attr_op.set_attr("__del__")
                        attr_op.set_caller(VariableRef(stmt.src_info, self._symbol_table, var))
                        call_op.set_func(attr_op)
                        release_stmt.set_expr(call_op)
                        release_stmt.indent()
                        null_stmt = CStmt(stmt.src_info, self._symbol_table, self._var_states)
                        null_stmt.remove_jump_mark()
                        null_stmt.remove_mark()
                        null_stmt.add_text(f"\t{var} = NULL;")
                        new_stmt_list.append(null_stmt)
                        new_stmt_list.append(release_stmt)
                        check_null_stmt = CStmt(stmt.src_info, self._symbol_table, self._var_states)
                        check_null_stmt.add_text(f"if ({var}) {{")
                        check_null_stmt.remove_jump_mark()
                        check_null_stmt.remove_mark()
                        end_check_null_stmt = CStmt(stmt.src_info, self._symbol_table, self._var_states)
                        end_check_null_stmt.remove_jump_mark()
                        end_check_null_stmt.remove_mark()
                        end_check_null_stmt.add_text("}")
                        self._release_stmt_list.append(check_null_stmt)
                        self._release_stmt_list.append(release_stmt)
                        self._release_stmt_list.append(null_stmt)
                        self._release_stmt_list.append(end_check_null_stmt)
                elif var in self._outer_variables and var not in self._used_outer_variables and not var.is_global:
                    self._used_outer_variables.append(var)
            stmt.set_jump_mark(self._cleanup_mark_name)
            new_stmt_list.append(stmt)
        new_stmt_list.reverse()
        self._stmt = new_stmt_list
        for listener in self._listeners.values():
            wait_stmt = CStmt(self.src_info, self._symbol_table, self._var_states)
            wait_text = f"{LISTENER_WAIT_FUNC}({listener});"
            wait_stmt.set_text(wait_text)
            self._stmt.append(wait_stmt)
        cleanup_mark = CStmt(self.src_info, self._symbol_table, self._var_states)
        cleanup_mark.add_text(f"goto {self._after_cleanup_mark_name};")
        cleanup_mark.add_text(f"{self._cleanup_mark_name}:")
        self._stmt.append(cleanup_mark)
        self._stmt += self._release_stmt_list
        after_cleanup_mark = CStmt(self.src_info, self._symbol_table, self._var_states)
        after_cleanup_mark.add_text(f"{self._after_cleanup_mark_name}:")
        self._stmt.append(after_cleanup_mark)
        self._is_finished = True

    @property
    def global_init_text(self) -> str:
        result: str = super().global_init_text
        stmts_text: str = "\n".join(filter(
            lambda x: x is not None and x.strip() != "",
            map(lambda x: x.global_init_text, self._stmt)
        ))
        return result + "\n" + stmts_text if stmts_text != "" else result

    @property
    def head_text(self) -> Optional[str]:
        return None

    @property
    def input_variables(self) -> set[VariableName]:
        return self._input_variables

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        for stmt in self._stmt:
            stmt.insert_finally_stmt(finally_stmt)

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "BlockStmt":
        new_stmt = copy(self)
        new_stmt._stmt = list(map(lambda stmt: stmt.instantiation(type_args), self._stmt))
        return new_stmt

    def substitute(self, const_vars: dict[VariableName, Expression]) -> "Statement":
        for i, stmt in enumerate(self._stmt):
            self._stmt[i] = stmt.substitute(const_vars)
        return self

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def new_listeners(self) -> dict[VariableName, str]:
        return {}

    @property
    def new_variables(self) -> set[VariableName]:
        return set(self._new_variables)

    def optimize(self) -> "BlockStmt":
        const_vars: dict[VariableName, Expression] = {}
        for i, stmt in enumerate(self._stmt):
            stmt = stmt.substitute(const_vars).optimize()
            const_vars = stmt.update_const_vars(const_vars)
            self._stmt[i] = stmt
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result: str = "\n\n".join(list(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._stmt))))
        if self._is_closure and self._closure_struct_def != "":
            # 捕获结构体定义输出到模块级，供外层函数与闭包体共同使用
            result = self._closure_struct_def + "\n\n" + result if result != "" else self._closure_struct_def
        return result if result != "" else None

    def remove_mark(self) -> None:
        super().remove_mark()
        for stmt in self._stmt:
            stmt.remove_mark()

    def set_as_closure(self, closure_name: str, args: list[VariableName]) -> None:
        """将当前语句块设置为闭包，生成捕获结构体代码。"""
        self._is_closure = True
        self._used_outer_variables = [v for v in self._used_outer_variables if v not in args]
        struct_name: str = f"struct {closure_name}$Capture"
        used_outer_variables_decl: list[str] = list(
            map(lambda x: f"\t{x.type_name_pair_calling};", self._used_outer_variables))
        struct_def: list[str] = [
            f"{struct_name} {{",
            "\n".join(used_outer_variables_decl),
            "};"
        ]
        # 捕获结构体的定义输出到模块级（外层函数分配捕获结构体时同样需要它），
        # 闭包体内仅做成员转换
        self._closure_struct_def = "\n".join(struct_def)
        used_outer_variables_convert: list[str] = list(
            map(lambda x: f"{x.type_name_pair_calling} = $$captureStructPtr->{x.name};", self._used_outer_variables))
        ptr_convert_def: list[str] = [
            f"{struct_name} *$$captureStructPtr = ({struct_name} *)$$capture;",
            "\n".join(used_outer_variables_convert)
        ]
        closure_init_stmt: CStmt = CStmt(self._src_info, self._symbol_table, self._var_states)
        closure_init_stmt.set_text("\n".join(ptr_convert_def))
        self._stmt.insert(0, closure_init_stmt)
        struct_alloc: str = f"{struct_name} *{closure_name}$$capture = ({struct_name} *)malloc(sizeof({struct_name}));"
        used_outer_variables_set: list[str] = list(
            map(lambda x: f"{closure_name}$$capture->{x.name} = {x.name};", self._used_outer_variables))
        self._closure_struct_setting_code = struct_alloc + "\n" + "\n".join(used_outer_variables_set)

    def set_as_const_def(self) -> None:
        self._is_const_def = True
        for stmt in self._stmt:
            stmt.set_as_const_def()

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        result: dict[VariableName, VariableState] = {}
        for stmt in self._stmt:
            result.update(stmt.variables_states)
        return result

    @property
    def _inner_text(self) -> str:
        head_texts: list[str] = list(
            filter(lambda x: x is not None and x != "", map(lambda x: x.head_text, self._stmt)))
        # 去重：嵌套表达式可能重复输出相同的临时变量声明
        seen: set[str] = set()
        deduped: list[str] = []
        for head in head_texts:
            for line in head.split("\n"):
                stripped = line.strip()
                if stripped == "" or stripped in seen:
                    continue
                seen.add(stripped)
                deduped.append(line)
        return "\n".join(
            deduped +
            list(filter(lambda x: x != "", map(lambda stmt: stmt.text, self._stmt)))
        )

    def _validate_conditional_mode(self, stmt: Statement) -> None:
        if self._processing_mode != _ProcessingMode.CONDITIONAL:
            raise CompilerException(
                "Elif statement and else statement should be after an if statement.", stmt.src_info
            )
        if isinstance(stmt, CondStmt) and stmt.cond_kw == _CondKw.ELSE:
            self._processing_mode = _ProcessingMode.NORMAL
        elif not isinstance(stmt, CondStmt):
            self._processing_mode = _ProcessingMode.NORMAL
            return
        # noinspection PyTypeChecker
        if_stmt: IfStmt = self._stmt[-1]
        if_stmt.add_branch(stmt)

    def _validate_try_catch_mode(self, stmt: Statement) -> None:
        if self._processing_mode != _ProcessingMode.TRY_CATCH:
            raise CompilerException(
                "Except statement and finally statement should be after a try statement.", stmt.src_info
            )
        if isinstance(stmt, CatchStmt):
            # noinspection PyTypeChecker
            try_stmt: TryStmt = self._stmt[-1]
            try_stmt.add_except_stmt(stmt)
        elif isinstance(stmt, FinallyStmt):
            # noinspection PyTypeChecker
            try_stmt: TryStmt = self._stmt[-1]
            try_stmt.set_finally_stmt(stmt)
            self._processing_mode = _ProcessingMode.NORMAL
        else:
            self._processing_mode = _ProcessingMode.NORMAL


class FnBlockStmt(BlockStmt):
    """函数体语句块，支持变量依赖排序和条件语句缓冲。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化函数体语句块。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._stmt_set: set[Statement] = set()
        self._variable_dependencies: dict[VariableName, Statement] = {}
        self._cond_stmt_buffer: list[Statement] = []

    def add_stmt(self, stmt: Statement) -> None:
        """向函数体中添加一条语句，处理条件分支缓冲和变量依赖。"""
        if isinstance(stmt, ReturnStmt):
            # fn函数按需执行，求出所有返回值后自动退出，不允许return
            raise CompilerException("fn functions can not use the return statement.", stmt.src_info)
        if isinstance(stmt, CondStmt):
            if stmt.cond_kw in (_CondKw.ELIF, _CondKw.ELSE):
                if len(self._cond_stmt_buffer) == 0:
                    raise CompilerException(
                        "Elif statement and else statement should be after an if statement or elif statement.",
                        stmt.src_info)
                last_stmt = self._cond_stmt_buffer[-1]
                if not isinstance(last_stmt, CondStmt):
                    raise CompilerException(
                        "Elif statement and else statement should be after an if statement or elif statement.",
                        stmt.src_info)
                if last_stmt.cond_kw == _CondKw.ELSE:
                    raise CompilerException(
                        "Elif statement and else statement should be after an if statement or elif statement.",
                        stmt.src_info)
                self._cond_stmt_buffer.append(stmt)
            else:
                if len(self._cond_stmt_buffer) > 0:
                    new_stmt = BlockStmt(stmt.src_info, self._symbol_table, self._var_states)
                    for buffer_stmt in self._cond_stmt_buffer:
                        new_stmt.add_stmt(buffer_stmt)
                    new_stmt.finish()
                    self._cond_stmt_buffer.clear()
                    self.add_stmt(new_stmt)
                self._cond_stmt_buffer.append(stmt)
            return
        if len(self._cond_stmt_buffer) > 0:
            new_stmt = BlockStmt(stmt.src_info, self._symbol_table, self._var_states)
            for buffer_stmt in self._cond_stmt_buffer:
                new_stmt.add_stmt(buffer_stmt)
            new_stmt.finish()
            self._cond_stmt_buffer.clear()
            self.add_stmt(new_stmt)
        if isinstance(stmt, OpStmt | ReturnStmt | ThrowStmt | CStmt):
            unreachable_warning(
                "Function call without return will be depreciated in any function defined with keyword \"fn\". Try to use \"sq\" for instead.",
                stmt.src_info
            )
            return
        self._stmt_set.add(stmt)
        self._variable_dependencies.update(map(lambda var: (var, stmt), stmt.new_variables))

    def finish(self) -> None:
        """完成函数体的设置，进行语句排序和条件分支处理。"""
        if len(self._cond_stmt_buffer) > 0:
            new_stmt = BlockStmt(self._cond_stmt_buffer[0].src_info, self._symbol_table, self._var_states)
            for buffer_stmt in self._cond_stmt_buffer:
                new_stmt.add_stmt(buffer_stmt)
            new_stmt.finish()
            self._cond_stmt_buffer.clear()
            self.add_stmt(new_stmt)
        new_stmt_list: list[Statement] = self._sort_stmt()
        for stmt in new_stmt_list:
            super().add_stmt(stmt)
        super().finish()

    def _sort_stmt(self) -> list[Statement]:
        """按依赖顺序排列语句（fn按需执行：仅保留返回值计算所需的语句）。

        根语句为给返回值（外层变量表中状态为DECLARED的变量）赋值的语句；
        每个根语句的输入变量定义语句递归地排在其前面。
        """
        roots: list[Statement] = []
        for stmt in self._stmt_set:
            to_return_vars = list(filter(
                lambda v: v in self._outer_variables and self._outer_variables[v] == VariableState.DECLARED,
                stmt.new_variables))
            if len(to_return_vars) > 0:
                roots.append(stmt)
        # 按源代码位置排序，保证输出确定
        roots.sort(key=lambda s: s.src_info.location_tuple)
        result: list[Statement] = []
        visited: set[Statement] = set()

        def walk(stmt: Statement) -> None:
            if stmt in visited:
                return
            visited.add(stmt)
            for var in sorted(stmt.input_variables, key=lambda v: v.name):
                dep: Optional[Statement] = self._variable_dependencies.get(var)
                if dep is not None and var not in self._outer_variables:
                    walk(dep)
            result.append(stmt)

        for stmt in roots:
            walk(stmt)
        return result


class CastOp(Expression):
    """类型转换表达式（包括静态转换和动态转换）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable) -> None:
        """
        初始化类型转换表达式。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        """
        super().__init__(src_info, symbol_table)
        self._type_name: Optional[TypeName] = None
        self._expr: Optional[Expression] = None
        self._is_dynamic_cast: bool = False
        self._temp_var_name: Optional[str] = None
        self._throw_stmt: Optional[ThrowStmt] = None
        self._var_states: VariableStateTable = var_states

    def as_async(self) -> "Expression":
        self._expr = self._expr.as_async()
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        result = CastOp(self._src_info, self._symbol_table, self._var_states)
        result._type_name = self._type_name
        result.set_expr(self._expr.as_inline(inline_mapping))
        return result

    def check_tail_recursive(self, func_name: str) -> "Expression":
        new_expr = copy(self)
        new_expr._expr = self._expr.check_tail_recursive(func_name)
        return new_expr

    @property
    def front_text(self) -> Optional[str]:
        expr_front_text = self._expr.front_text
        if expr_front_text is None:
            expr_front_text = ""
        else:
            expr_front_text += "\n"
        if self._is_dynamic_cast:
            expr_front_text += self.__dynamic_cast_front_text
        return expr_front_text if expr_front_text != "" else None

    @property
    def global_init_text(self) -> str:
        result: str = super().global_init_text
        if self._throw_stmt is not None:
            result += "\n" + self._throw_stmt.global_init_text
        return result + "\n" + self._expr.global_init_text if self._expr.global_init_text is not None else result

    @property
    def head_text(self) -> Optional[str]:
        if self._is_dynamic_cast:
            result: list[str] = [self._throw_stmt.head_text, self._expr.head_text, f"{self._type_name.c_calling_name}{self._temp_var_name};"]
        else:
            result = [self._expr.head_text]
        result_str: str = "\n".join(filter(lambda x: x is not None, result))
        return result_str if result_str != "" else None

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._expr.inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr = copy(self)
        new_expr._expr = self._expr.instantiation(type_args)
        new_expr._type_name = self._type_name.instantiation(type_args)
        new_expr._throw_stmt = self._throw_stmt.instantiation(type_args)
        return new_expr

    def optimize(self) -> "Expression":
        self._expr = self._expr.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return self._expr.outer_text

    @property
    def release_text(self) -> Optional[str]:
        return self._expr.release_text

    @property
    def return_type(self) -> TypeName:
        return self._type_name

    def set_expr(self, expr: Expression) -> None:
        """设置要转换的表达式。"""
        self._expr = expr
        if self._type_name is not None:
            self._is_dynamic_cast = self.__check_dynamic_cast()

    def set_type(self, type_name: TypeRef) -> None:
        """设置转换的目标类型。"""
        self._type_name = type_name.return_type
        if self._expr is not None:
            self._is_dynamic_cast = self.__check_dynamic_cast()

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        self._expr = self._expr.substitute(expr)
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return self._expr.tail_recursive_mark

    @property
    def text(self) -> str:
        if self._is_dynamic_cast:
            return f"({self._type_name.name}){self._temp_var_name}"
        return f"({self._type_name.name}){self._expr.text}"

    @property
    def used_variables(self) -> set[VariableName]:
        return self._expr.used_variables

    def validate(self) -> None:
        self._expr.validate()

    def __check_dynamic_cast(self) -> bool:
        """检查是否需要进行动态类型转换。"""
        result = not self._expr.return_type.convertible_to(self._type_name, self._symbol_table.symbols)
        if result:
            self._temp_var_name = self._symbol_table.get_counter()
            self._throw_stmt = ThrowStmt(self._src_info, self._symbol_table, self._var_states)
            to_throw_expr = CallOp(self._src_info, self._symbol_table)
            to_throw_expr.set_func(ClassRef.from_name(self._src_info, self._symbol_table, "RuntimeException"))
            to_throw_expr.add_arg(StringLiteral(self._src_info, self._symbol_table, f"Cannot cast {self._expr.return_type} to {self._type_name}"), None)
            self._throw_stmt.set_expr(to_throw_expr)
            self._throw_stmt.indent()
        return result

    @property
    def __dynamic_cast_front_text(self) -> str:
        """获取动态类型转换的前置代码。"""
        if not isinstance(self._type_name, ClassName) or not self._expr.return_type.is_object:
            raise CompilerException("Dynamic cast is not allowed on this expression", self._src_info)
        result: list[str] = [
            f"{self._temp_var_name} = {self._expr.text};",
            "#ifdef $__VIOLA_debug_type_dynamicCheck",
            f"if (!{CONVERTIBLE_TO_FUNC}({self._temp_var_name}->$$vtable, &{self._type_name.vtable_name})) {{",
            "\t" + self._throw_stmt.text,
            "}",
            "#endif"
        ]
        return "\n".join(result)
