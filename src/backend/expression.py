# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .symbol import (
    TypeName, GenericArgument, VariableName, SymbolTable, ArrayTypeName, ClassName, TupleTypeName,
    LocalVariableName, BaseTypeName, FunctionTypeName, BOOL, INT8, INT16, UINT8, UINT16, INT32, UINT32, INT64,
    UINT64, FLOAT, DOUBLE, GlobalVariableName, FunctionName, MethodName, LISTENER_T, LISTENER_INIT_FUNC,
    EmptyArrayTypeName, base_type_degrade, SliceTypeName, INT_TYPES, StringTypeName, AnyTypeName, AutoTypeName
)
from utils import CompilerException, InternalCompilerException, COMPILER_PARAMS, SourceInfo

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional, Callable

CONVERTIBLE_TO_FUNC = "viola$lang$convertibleTo"
FUNC_CALL_T: str = "viola$lang$thread$FuncCall"
FUNC_ENQUEUE_FUNC: str = "viola$lang$thread$enqueue"


class Expression(CompilingItem, ABC):
    """表达式抽象基类。

    所有表达式节点（字面量、变量引用、运算符、函数调用等）的基类，
    定义了编译器生成 C 代码所需的核心接口。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """初始化表达式。

        Args:
            src_info: 源代码位置信息，用于错误报告。
            symbol_table: 符号表。
        """
        super().__init__(src_info)
        self._returns: list[VariableName] = []
        self._symbol_table: SymbolTable = symbol_table

    @abstractmethod
    def as_async(self) -> "Expression":
        """将此表达式转换为异步版本。

        Returns:
            异步版本的表达式。
        """
        pass

    @abstractmethod
    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        """将表达式内联化，用于函数内联展开。

        Args:
            inline_mapping: 变量名到新名称的映射，确保内联后变量名不冲突。

        Returns:
            内联化后的表达式。
        """
        pass

    @abstractmethod
    def check_tail_recursive(self, func_name: str) -> "Expression":
        """检查是否为尾递归调用，如果是则转换为 TailRecursiveCall。

        Args:
            func_name: 当前函数名称。

        Returns:
            如果是尾递归调用则返回 TailRecursiveCall，否则返回自身。
        """
        pass

    @property
    @abstractmethod
    def front_text(self) -> Optional[str]:
        """生成需要在调用之前放置的 C 代码文本。

        Returns:
            C 代码文本，如果没有则返回 None。
        """
        pass

    @property
    @abstractmethod
    def global_init_text(self) -> Optional[str]:
        """生成需要在全局初始化区域的 C 代码文本。

        Returns:
            全局初始化 C 代码文本，如果没有则返回 None。
        """
        pass

    @property
    @abstractmethod
    def head_text(self) -> Optional[str]:
        """生成需要在函数头部（变量声明区域）放置的 C 代码文本。

        Returns:
            头部声明 C 代码文本，如果没有则返回 None。
        """
        pass

    @property
    @abstractmethod
    def inline_mapping(self) -> dict[str, str]:
        """获取内联化过程中产生的变量名映射表。

        Returns:
            原始变量名到内联化后变量名的映射字典。
        """
        pass

    @abstractmethod
    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        """用具体类型参数实例化泛型表达式。

        Args:
            type_args: 泛型参数到具体类型的映射。

        Returns:
            实例化后的表达式。
        """
        pass

    @property
    def is_const(self) -> bool:
        """判断表达式是否为编译时常量。

        Returns:
            是否为常量，默认为 False。
        """
        return False

    @property
    def listener_name(self) -> Optional[str]:
        """获取异步调用时监听器的变量名。

        Returns:
            监听器名称，默认为 None 表示非异步。
        """
        return None

    @abstractmethod
    def optimize(self) -> "Expression":
        """对表达式进行优化（常量折叠等）。

        Returns:
            优化后的表达式。
        """
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        """生成需要在函数外部（全局作用域）放置的 C 代码文本。

        Returns:
            外部 C 代码文本，如果没有则返回 None。
        """
        pass

    @property
    @abstractmethod
    def release_text(self) -> Optional[str]:
        """生成用于释放表达式所分配内存的 C 代码文本。

        处理引用计数检查和 free() 调用。

        Returns:
            释放内存的 C 代码文本，如果没有则返回 None。
        """
        pass

    @property
    @abstractmethod
    def return_type(self) -> TypeName:
        """获取表达式的返回类型。

        Returns:
            表达式的类型名称。
        """
        pass

    def set_returns(self, returns: list[VariableName]) -> bool:
        """设置表达式的返回值变量列表。

        Args:
            returns: 接收返回值的变量列表。

        Returns:
            是否成功设置，默认为 False。
        """
        return False

    @abstractmethod
    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        """用给定的表达式替换子表达式中的变量引用。

        Args:
            expr: 变量名到替换表达式的映射。

        Returns:
            替换后的新表达式。
        """
        pass

    @property
    @abstractmethod
    def tail_recursive_mark(self) -> Optional[str]:
        """获取尾递归标记标签文本。

        用于生成 goto 跳转标签。

        Returns:
            尾递归标签文本，如果不是尾递归返回 None。
        """
        pass

    @property
    @abstractmethod
    def text(self) -> str:
        """获取表达式对应的 C 代码文本（使用位置的值）。"""
        pass

    @property
    @abstractmethod
    def used_variables(self) -> set[VariableName]:
        """获取此表达式使用的所有变量的集合。"""
        pass

    @abstractmethod
    def validate(self) -> None:
        """验证表达式的类型正确性和语义合法性。

        Raises:
            CompilerException: 验证失败时抛出。
        """
        pass


class CExpr(Expression):
    """自定义 C 代码表达式。

    允许直接嵌入原始 C 代码片段的表达式节点，编译器不对其做类型检查或语义处理。
    主要用于实现内建函数、运行时支持代码等需要直接操作底层 C 代码的场景。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._text: list[str] = []
        self._inline_mapping: dict[str, str] = {}
        self._var: Optional[LocalVariableName] = None

    def add_text(self, text: str) -> None:
        """添加一行 C 代码文本到表达式中。

        Args:
            text: 要添加的 C 代码行。
        """
        self._text.append(text)

    def as_async(self) -> "Expression":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        self._inline_mapping = inline_mapping
        return self

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

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
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        return self

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
        return AnyTypeName(self._src_info)

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        return self

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        return "\n".join(self._text)

    @property
    def used_variables(self) -> set[VariableName]:
        return set()

    def validate(self) -> None:
        pass


class UnpackExpr(Expression):
    """元组解包表达式。

    用于将元组类型的表达式解包为多个独立的返回值变量。
    例如：a, b = (1, 2) 中的解包操作。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, to_unpack: Optional[Expression] = None) -> None:
        super().__init__(src_info, symbol_table)
        if to_unpack is not None and not isinstance(to_unpack.return_type, TupleTypeName):
            raise CompilerException("Cannot unpack non-tuple.", src_info)
        self._to_unpack: Optional[Expression] = to_unpack
        self._var: Optional[LocalVariableName] = None
        self._returns: list[VariableName] = []
        self._inline_mapping: dict[str, str] = {}

    def as_async(self) -> "Expression":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._to_unpack = self._to_unpack.as_inline(inline_mapping)
        new_expr._inline_mapping = new_expr._to_unpack.inline_mapping
        for i, ret in enumerate(self._returns):
            new_expr._inline_mapping[ret.name] = self._symbol_table.get_counter()
            new_expr._returns[i].rename(new_expr._inline_mapping[ret.name])
        new_expr._inline_mapping[new_expr._var.name] = self._symbol_table.get_counter()
        new_expr._var.rename(new_expr._inline_mapping[new_expr._var.name])
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    @property
    def front_text(self) -> Optional[str]:
        to_unpack_front_text: Optional[str] = self._to_unpack.front_text
        if len(self._returns) == 0:
            return to_unpack_front_text
        if to_unpack_front_text is None:
            to_unpack_front_text = ""
        else:
            to_unpack_front_text += "\n"
        result: str = to_unpack_front_text + f"{self._var.name} = {self._to_unpack.text};"
        for i, ret in enumerate(self._returns[:-1]):
            result += f"\n{ret.name} = *{self._var.name}[{i}];"
        # noinspection PyTypeChecker
        expr_type: TupleTypeName = self._to_unpack.return_type
        if len(expr_type.types) > len(self._returns):
            result += f"\n{self._returns[-1].name}->data = {self._var.name} + {len(expr_type.types) - 1};"
            result += f"\n{self._returns[-1].name}->size = {len(expr_type.types) - 1};"
        return result

    @property
    def global_init_text(self) -> Optional[str]:
        return self._to_unpack.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        to_unpack_head_text: Optional[str] = self._to_unpack.head_text
        if len(self._returns) == 0:
            return to_unpack_head_text
        if to_unpack_head_text is None:
            to_unpack_head_text = ""
        else:
            to_unpack_head_text += "\n"
        result: str = to_unpack_head_text + f"{self._var.type_name_pair_calling};"
        return result

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._to_unpack = self._to_unpack.instantiation(type_args)
        # noinspection PyTypeChecker
        new_expr._var = self._var.instantiation(self._var.name, type_args)
        new_expr._returns = list(map(lambda ret: ret.instantiation(ret.name, type_args), self._returns))
        return new_expr

    def optimize(self) -> "Expression":
        self._to_unpack = self._to_unpack.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return self._to_unpack.outer_text

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._var.name}->refCount == 0) {{",
            f"\tif ({self._var.name}->parent) {{",
            f"\t\t{self._var.name}->parent->refCount--;",
            "\t} else {",
            f"\t\tfree({self._var.name}->data);",
            f"\t\t{self._var.name}->data = NULL;",
            f"\t\tfree({self._var.name});",
            f"\t\t{self._var.name} = NULL;",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._to_unpack.return_type

    def set_expr(self, to_unpack: Expression) -> None:
        """设置要被解包的表达式。

        Args:
            to_unpack: 需要解包的表达式（必须是元组类型）。
        """
        self._to_unpack = to_unpack

    def set_returns(self, returns: list[VariableName]) -> bool:
        # noinspection PyTypeChecker
        expr_type: TupleTypeName = self._to_unpack.return_type
        if len(returns) > len(expr_type.types):
            raise CompilerException(
                f"Too many returns: {len(returns)} > {len(expr_type.types)}.",
                self._src_info
            )
        for ret, expected_type in zip(returns[:-1], expr_type.types[:len(returns) - 1]):
            if not ret.type.convertable_to(expected_type, self._symbol_table.symbols):
                raise CompilerException(
                    f"Type mismatch: {ret.type.raw_name} can not convert to {expected_type.raw_name}.",
                    self._src_info
                )
        last_expected_type: TupleTypeName = TupleTypeName(self._src_info, expr_type.types[-1:])
        if not returns[-1].type.convertable_to(last_expected_type, self._symbol_table.symbols):
            raise CompilerException(
                f"Type mismatch: {returns[-1].type.raw_name} can not convert to {last_expected_type.raw_name}.",
                self._src_info
            )
        self._returns = returns
        self._var = LocalVariableName(
            self._src_info,
            self._symbol_table.get_counter(),
            self._to_unpack.return_type
        )
        return True

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._to_unpack = self._to_unpack.substitute(expr)
        return new_expr

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        if self._var is None:
            return self._to_unpack.text
        return self._var.name

    @property
    def to_unpack(self) -> Expression:
        """获取要被解包的表达式。"""
        return self._to_unpack

    @property
    def used_variables(self) -> set[VariableName]:
        return self._to_unpack.used_variables

    def validate(self) -> None:
        self._to_unpack.validate()


class ValueRef(Expression, ABC):
    """值引用抽象基类。

    表示对某个值（变量、字面量等）的引用。继承自 Expression，
    为此类表达式提供了解包（unpack）支持，当返回值数量大于 1 时自动创建 UnpackExpr。
    不直接定义 as_async，由子类决定是否支持异步。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._returns: Optional[list[VariableName]] = None
        self._unpack_expr: Optional[UnpackExpr] = None
        self._inline_mapping: dict[str, str] = {}

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr = deepcopy(self)
        # noinspection PyTypeChecker
        new_expr._unpack_expr = self.as_inline(self._unpack_expr.inline_mapping)
        new_expr._inline_mapping = new_expr._unpack_expr.inline_mapping
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    @property
    def front_text(self) -> Optional[str]:
        if self._unpack_expr is not None:
            return self._unpack_expr.front_text
        return None

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    @property
    def outer_text(self) -> Optional[str]:
        return self._unpack_expr.outer_text

    def set_returns(self, returns: list[VariableName]) -> bool:
        self._returns = returns
        if len(returns) > 1:
            self._unpack_expr = UnpackExpr(self._src_info, self._symbol_table, self)
            self._unpack_expr.set_returns(returns)
        return True

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None


class VariableRef(ValueRef):
    """变量引用表达式。

    表示对源代码中某个变量（局部变量、全局变量、函数名等）的引用。
    在优化阶段可以通过 bind_value 绑定编译时已知的值，从而进行常量传播优化。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var: VariableName) -> None:
        super().__init__(src_info, symbol_table)
        self._var: VariableName = var
        self._value: Optional[Expression] = None

    def as_async(self) -> "VariableRef":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: VariableRef = super().as_inline(inline_mapping)
        if self._var.name not in inline_mapping:
            if self._var.is_global:
                inline_mapping[self._var.name] = self._var.name
            else:
                inline_mapping[self._var.name] = self._symbol_table.get_counter()
        new_expr._var.rename(inline_mapping[self._var.name])
        return new_expr

    def bind_value(self, value: Expression) -> None:
        """绑定编译时已知的值，用于常量传播优化。

        Args:
            value: 编译时已知的常量表达式。
        """
        self._value = value

    @classmethod
    def from_function(cls, src_info: SourceInfo, name: str, arg_types: list[str],
                      kwarg_types: dict[str, str], symbol_table: SymbolTable) -> "VariableRef":
        """通过函数名和参数类型查找函数，创建对应的变量引用。

        根据函数名、位置参数类型列表和关键字参数类型字典，在符号表中查找匹配的函数。
        要求恰好匹配一个函数，零个或超过一个都会报错。

        Args:
            src_info: 源代码位置信息。
            name: 函数名称。
            arg_types: 位置参数的类型名列表。
            kwarg_types: 关键字参数名到类型名的映射。
            symbol_table: 符号表。

        Returns:
            匹配函数的 VariableRef 实例。

        Raises:
            CompilerException: 找不到函数或找到多个重载时抛出。
        """
        func = symbol_table.find_functions(name, arg_types, kwarg_types)
        if len(func) == 0:
            raise CompilerException(f"Function {name} not found.", src_info)
        if len(func) > 1:
            raise CompilerException(f"Function {name} overloads with same arguments.", src_info)
        return cls(src_info, symbol_table, func[0])

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def head_text(self) -> Optional[str]:
        return None

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: VariableRef = deepcopy(self)
        new_expr._var = new_expr._var.instantiation(new_expr._var.name, type_args)
        return new_expr

    def optimize(self) -> "Expression":
        if self._value is not None:
            self._value = self._value.optimize()
            if self._value.is_const:
                return self._value
            return self
        return self

    @property
    def release_text(self) -> Optional[str]:
        if not self.return_type.is_object:
            return None
        result: list[str] = [
            f"if ({self._var.name}->refCount == 0) {{",
            f"\tif ({self._var.name}->parent) {{",
            f"\t\t{self._var.name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._var.name});",
            f"\t\t{self._var.name} = NULL;"
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._var.type

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        if self._var in expr:
            return expr[self._var]
        return self

    @property
    def text(self) -> str:
        return self._var.name

    @property
    def used_variables(self) -> set[VariableName]:
        return {self._var}

    def validate(self) -> None:
        pass

    @property
    def var(self) -> VariableName:
        """获取此变量引用指向的变量名对象。"""
        return self._var


class Literal(ValueRef, ABC):
    """字面量表达式抽象基类。

    表示编译时常量值（数字、字符串、布尔值等）。
    所有字面量都被视为常量（is_const 返回 True），在优化阶段可用于常量折叠。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, value: str, t: TypeName) -> None:
        super().__init__(src_info, symbol_table)
        self._value: str = value
        self._type: TypeName = t

    def as_async(self) -> "Literal":
        return self

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def head_text(self) -> Optional[str]:
        return None

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        return self

    @property
    def is_const(self) -> bool:
        return True

    def optimize(self) -> "Expression":
        return self

    @property
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        return self._type

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        return self

    @property
    def text(self) -> str:
        return self._value

    @property
    def used_variables(self) -> set[VariableName]:
        return set()

    @property
    def value(self) -> Optional[int | float]:
        """字面量对应的 Python 原生值（用于常量折叠优化）。

        Returns:
            Python int 或 float 值，如果不是数值类型则返回 None。
        """
        return None


class StringLiteral(Literal):
    """字符串字面量表达式。

    将源语言中的字符串字面量编译为 C 代码中的运行时字符串对象。
    支持转义字符处理，使用 UTF-16 编码，通过 _STRING_CHUNK_SIZE 控制分块大小。
    """
    _REPLACEMENTS: list[tuple[str, str]] = [
        ("\\\\", "\\"),
        ("\\\"", "\""),
        ("\\'", "\'"),
        ("\\n", "\n"),
        ("\\r", "\r"),
        ("\\t", "\t"),
        ("\\b", "\b"),
        ("\\f", "\f"),
        ("\\v", "\v"),
        ("\\0", "\0"),
        ("\\a", "\a")
    ]
    _STRING_CHUNK_SIZE: int = COMPILER_PARAMS["runtime-stringChunkSize"]

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, symbol_table, value, StringTypeName)
        self._var_name: str = self._symbol_table.get_counter()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: StringLiteral = super().as_inline(inline_mapping)
        inline_mapping[self._var_name] = self._symbol_table.get_counter()
        new_expr._var_name = inline_mapping[self._var_name]
        return new_expr

    @property
    def front_text(self) -> str:
        chunks: list[list[int]] = self._as_unicode()
        chunk_indices: list[int] = [0]
        chunk_sizes: list[int] = list(map(len, chunks))
        for i, chunk in enumerate(chunks[:-1]):
            chunk_indices.append(chunk_indices[i] + len(chunk))
        chunks_copy_string: list[str] = [
            f"memcpy({self._var_name}->data + {index}, (uint16_t[]){{ {', '.join(map(lambda x: str(x), chunk))} }}, {size} * sizeof(uint16_t));"
            for (i, chunk), index, size in zip(enumerate(chunks), chunk_indices, chunk_sizes)
        ]
        lines: list[str] = [
            f"{self._var_name} = ({self._type.c_calling_name})malloc(sizeof({self._type.c_alloc_name}));",
            f"{self._var_name}->data = (uint16_t *)malloc(sizeof(uint16_t) * {len(self._value) - 2});",
            f"if (!{self._var_name}->data) raise(SIGSEGV);",
            f"{self._var_name}->size = {len(self._value) - 2};",
            "\n".join(chunks_copy_string)
        ]
        if len(self._value) == 2:
            lines[1] = f"{self._var_name}->data = NULL;"
        return "\n".join(lines)

    @property
    def head_text(self) -> Optional[str]:
        return f"{LocalVariableName(self._src_info, self._var_name, self._type).type_name_pair_calling};"

    @property
    def is_const(self) -> bool:
        return False

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._var_name}->refCount == 0) {{",
            f"\tif ({self._var_name}->parent) {{",
            f"\t\t{self._var_name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._var_name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def text(self) -> str:
        return self._var_name

    def validate(self) -> None:
        pass

    @property
    def used_variables(self) -> set[VariableName]:
        return {LocalVariableName(self._src_info, self._var_name, self._type)}

    def _as_unicode(self) -> list[list[int]]:
        """将字符串转换为分块后的 Unicode 码点列表。

        先处理转义字符替换，再将每个字符转为 Unicode 码点（ord），
        最后按照 _STRING_CHUNK_SIZE 分块以适配 C 编译器的数组初始化限制。

        Returns:
            分块后的 Unicode 码点列表，每个块长度为 _STRING_CHUNK_SIZE（最后一块可能更短）。
        """
        for old, new in self._REPLACEMENTS:
            self._value = self._value.replace(old, new)
        unicode_data: list[int] = list(map(ord, self._value))
        chunks_num: int = len(unicode_data) // self._STRING_CHUNK_SIZE + 1
        chunk_sizes: list[int] = [self._STRING_CHUNK_SIZE] * (chunks_num - 1) + [
            len(unicode_data) % self._STRING_CHUNK_SIZE]
        return list(
            map(lambda i: unicode_data[i * self._STRING_CHUNK_SIZE:i * self._STRING_CHUNK_SIZE + chunk_sizes[i]],
                range(chunks_num)))


class BoolLiteral(Literal):
    """布尔字面量表达式。

    表示 true 或 false，编译为 C 代码中的 BOOL 类型值。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, symbol_table, value, BOOL)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> bool:
        return self._value == "true"


class IntegerLiteral(Literal):
    """整数字面量表达式。

    支持多种整数类型：INT32、UINT32、INT_N（有符号自定义位宽）、UINT_N（无符号自定义位宽）。
    位宽通过后缀语法指定，例如 42i8 表示 INT8，42u16 表示 UINT16。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, value: str, lexing_type: str = "INT32") -> None:
        match lexing_type:
            case "INT32":
                t = INT32
            case "UINT32":
                t = UINT32
            case "INT_N":
                if "i" in value:
                    bits_num: str = value.split("i")[1]
                else:
                    bits_num = value.split("I")[1]
                match bits_num:
                    case "8":
                        t = INT8
                    case "16":
                        t = INT16
                    case "32":
                        t = INT32
                    case "64":
                        t = INT64
                    case _:
                        raise CompilerException(f"Invalid bits number: {bits_num}", src_info)
            case "UINT_N":
                if "u" in value:
                    bits_num: str = value.split("u")[1]
                else:
                    bits_num = value.split("U")[1]
                match bits_num:
                    case "8":
                        t = UINT8
                    case "16":
                        t = UINT16
                    case "32":
                        t = UINT32
                    case "64":
                        t = UINT64
                    case _:
                        raise CompilerException(f"Invalid bits number: {bits_num}", src_info)
            case _:
                raise CompilerException(f"Invalid lexing type: {lexing_type}", src_info)
        super().__init__(src_info, symbol_table, value, t)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> int:
        return int(self._value)


class FloatLiteral(Literal):
    """浮点数字面量表达式。

    以 'f' 结尾的为 FLOAT（单精度），否则为 DOUBLE（双精度）。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, value: str) -> None:
        if value.endswith("f"):
            t = FLOAT
        else:
            t = DOUBLE
        # noinspection PyTypeChecker
        super().__init__(src_info, symbol_table, value, t)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> float:
        return float(self._value)


class SliceRef(ValueRef):
    """切片表达式。

    表示 [start:end:step] 形式的切片操作，编译为运行时 SliceTypeName 对象。
    默认值为 start=0、end=0、step=1。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._is_finished: bool = False
        self._start: Expression = IntegerLiteral(src_info, symbol_table, "0")
        self._end: Expression = IntegerLiteral(src_info, symbol_table, "0")
        self._step: Expression = IntegerLiteral(src_info, symbol_table, "1")
        self._temp_var: LocalVariableName = LocalVariableName(src_info, self._symbol_table.get_counter(),
                                                              SliceTypeName)

    def as_async(self) -> "Expression":
        return self

    @property
    def front_text(self) -> Optional[str]:
        results: list[Optional[str]] = [
            self._start.front_text if self._start else None,
            self._end.front_text if self._end else None,
            self._step.front_text,
            f"{self._temp_var.name} = ({SliceTypeName.c_calling_name})malloc(sizeof({SliceTypeName.c_alloc_name}));",
            f"{self._temp_var.name}->start = {self._start.text};",
            f"{self._temp_var.name}->end = {self._end.text};",
            f"{self._temp_var.name}->step = {self._step.text};"
        ]
        return "\n".join(filter(lambda x: x is not None, results))

    @property
    def global_init_text(self) -> Optional[str]:
        expr: list[Optional[Expression]] = [
            self._start,
            self._end,
            self._step
        ]
        results: list[Optional[str]] = list(map(lambda x: x.global_init_text if x else None, expr))
        return "\n".join(filter(lambda x: x is not None, results))

    @property
    def head_text(self) -> Optional[str]:
        expr: list[Optional[Expression]] = [
            self._start,
            self._end,
            self._step
        ]
        results: list[Optional[str]] = list(map(lambda x: x.head_text if x else None, expr)) + [
            self._temp_var.type_name_pair_calling + ";"]
        return "\n".join(filter(lambda x: x is not None, results))

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        return self

    @property
    def is_const(self) -> bool:
        return False

    def optimize(self) -> "Expression":
        self._start = self._start.optimize()
        self._end = self._end.optimize()
        self._step = self._step.optimize()
        return self

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._temp_var.name}->refCount == 0) {{",
            f"\tif ({self._temp_var.name}->parent) {{",
            f"\t\t{self._temp_var.name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._temp_var.name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return SliceTypeName

    def set_end(self, end: Expression) -> None:
        """设置切片结束索引。

        Args:
            end: 结束索引表达式（必须为整数类型）。
        """
        self._end = end

    def set_start(self, start: Expression) -> None:
        """设置切片起始索引。

        Args:
            start: 起始索引表达式（必须为整数类型）。
        """
        self._start = start

    def set_step(self, step: Expression) -> None:
        """设置切片步长。

        Args:
            step: 步长表达式（必须为整数类型）。
        """
        self._step = step

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        new_expr: SliceRef = deepcopy(self)
        new_expr._start = self._start.substitute(expr)
        new_expr._end = self._end.substitute(expr)
        new_expr._step = self._step.substitute(expr)
        return new_expr

    @property
    def text(self) -> str:
        return self._temp_var.name

    @property
    def used_variables(self) -> set[VariableName]:
        result: set[VariableName] = {self._temp_var}
        for expr in [self._start, self._end, self._step]:
            if expr:
                result.update(expr.used_variables)
        return result

    def validate(self) -> None:
        if self._start.return_type not in INT_TYPES:
            raise InternalCompilerException("SliceRef start should be int", self._src_info)
        if self._end.return_type not in INT_TYPES:
            raise InternalCompilerException("SliceRef end should be int", self._src_info)
        if self._step.return_type not in INT_TYPES:
            raise InternalCompilerException("SliceRef step should be int", self._src_info)
        self._start.validate()
        self._end.validate()
        self._step.validate()


class ArrayRef(ValueRef):
    """数组字面量表达式。

    表示 [v1, v2, ...] 形式的数组构造，编译为运行时数组对象。
    自动推导元素类型：类类型取公共父类，基本类型取降级类型。
    通过 add_value 逐步填充元素，最后调用 finish 完成构建。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._type: Optional[ArrayTypeName] = None
        self._element_type: Optional[TypeName] = None
        self._temp_var: Optional[LocalVariableName] = None

    def add_value(self, value: Expression) -> None:
        """向数组中添加一个元素表达式。

        自动更新元素类型：第一个元素确定初始类型，后续元素通过
        shared_parent（类类型）或 base_type_degrade（基本类型）统一类型。

        Args:
            value: 要添加的元素表达式。

        Raises:
            InternalCompilerException: 数组已完成构建后调用。
        """
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        self._values.append(value)
        if self._element_type is None:
            self._element_type = value.return_type
        elif isinstance(self._element_type, ClassName):
            if not isinstance(value.return_type, ClassName):
                raise InternalCompilerException("ArrayRef element type mismatch", self._src_info)
            if self._element_type != value.return_type:
                self._element_type = self._element_type.shared_parent(value.return_type, self._symbol_table)
        elif isinstance(self._element_type, BaseTypeName):
            if not isinstance(value.return_type, BaseTypeName):
                raise InternalCompilerException("ArrayRef element type mismatch", self._src_info)
            # noinspection PyTypeChecker
            self._element_type = base_type_degrade(self._element_type, value.return_type)

    def as_async(self) -> "ValueRef":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: ArrayRef = super().as_inline(inline_mapping)
        for i, value in enumerate(self._values):
            new_expr._values[i] = value.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._values[i].inline_mapping)
        new_expr._inline_mapping[self._temp_var.name] = self._symbol_table.get_counter()
        new_expr._temp_var.rename(new_expr._inline_mapping[self._temp_var.name])
        return new_expr

    def finish(self) -> None:
        """完成数组构建，确定最终类型并分配临时变量。

        如果未添加任何元素，数组类型为 EmptyArrayTypeName；
        否则根据推断的 element_type 创建对应的 ArrayTypeName。

        Raises:
            InternalCompilerException: 数组已完成构建后重复调用。
        """
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        if self._element_type is None:
            self._type = EmptyArrayTypeName(self._src_info)
        else:
            self._type = ArrayTypeName(self._src_info, self._element_type)
        var_name: str = self._symbol_table.get_counter()
        self._temp_var = LocalVariableName(self._src_info, var_name, self._type)
        self._is_finished = True

    @property
    def front_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("ArrayRef is not finished", self._src_info)
        lines: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.front_text, self._values)))
        lines.append(f"{self._temp_var.name}->parent = NULL;")
        lines.append(f"{self._temp_var.name}->refCount = 1;")
        if len(self._values) == 0:
            lines.append(f"{self._temp_var.name}->data = NULL;")
            lines.append(f"{self._temp_var.name}->size = 0;")
            return "\n".join(lines)
        lines.append(
            f"{self._temp_var.name}->data = malloc(sizeof({self._type.element_type.c_alloc_name}) * {len(self._values)});"
        )
        lines.append(f"{self._temp_var.name}->size = {len(self._values)};")
        for i, value in enumerate(self._values):
            lines.append(f"{self._temp_var.name}->data[{i}] = {value.text};")
        return "\n".join(lines)

    @property
    def global_init_text(self) -> Optional[str]:
        result = "\n".join(filter(lambda x: x is not None, map(lambda x: x.global_init_text, self._values)))
        return result if result != "" else None

    @property
    def head_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("ArrayRef is not finished", self._src_info)
        return f"{self._temp_var.type_name_pair_calling};"

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: ArrayRef = deepcopy(self)
        new_expr._type = self._type.instantiation(type_args)
        new_expr._values = list(map(lambda x: x.instantiation(type_args), self._values))
        return new_expr

    def optimize(self) -> "Expression":
        for i, v in enumerate(self._values):
            self._values[i] = v.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._values)))
        return result if result != "" else None

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._temp_var.name}->refCount == 0) {{",
            f"\tif ({self._temp_var.name}->parent) {{",
            f"\t\t{self._temp_var.name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._temp_var.name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        if not self._is_finished:
            raise CompilerException("ArrayRef is not finished", self._src_info)
        return self._type

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        result: ArrayRef = deepcopy(self)
        result._values = list(map(lambda x: x.substitute(expr), self._values))
        return result

    @property
    def text(self) -> str:
        return self._temp_var.name

    @property
    def used_variables(self) -> set[VariableName]:
        if not self._is_finished:
            raise CompilerException("ArrayRef is not finished", self._src_info)
        return set.union(*map(lambda x: x.used_variables, self._values))

    def validate(self) -> None:
        if not self._is_finished:
            raise InternalCompilerException("ArrayRef is not finished", self._src_info)
        exceptions_text: list[str] = []
        for value in self._values:
            try:
                value.validate()
            except CompilerException as e:
                exceptions_text.append(str(e))
        if len(exceptions_text) > 0:
            raise CompilerException("\n\n".join(exceptions_text), self._src_info)


class TupleRef(ValueRef):
    """元组字面量表达式。

    表示 (v1, v2, ...) 形式的元组构造，编译为运行时元组对象。
    支持索引和切片访问、左侧追加元素等操作。
    """

    def __getitem__(self, item: slice | int) -> Expression:
        """通过索引或切片访问元组中的元素。

        Args:
            item: 整数索引（返回单个元素）或 slice 对象（返回子元组）。

        Returns:
            单个元素表达式或新的 TupleRef 子元组。
        """
        if isinstance(item, int):
            return self._values[item]
        result = TupleRef(self._src_info, self._symbol_table)
        for v in self._values[item]:
            result.add_value(v)
        result.finish()
        return result

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._type: Optional[TypeName] = None
        self._temp_var: Optional[VariableName] = None

    def __len__(self) -> int:
        """返回元组中元素的数量。"""
        return len(self._values)

    def add_value(self, value: Expression) -> None:
        """向元组末尾添加一个元素表达式。

        Args:
            value: 要添加的元素表达式。

        Raises:
            InternalCompilerException: 元组已完成构建后调用。
        """
        if self._is_finished:
            raise InternalCompilerException("TupleRef is already finished", self._src_info)
        self._values.append(value)

    def append_left(self, value: Expression) -> None:
        """向元组开头插入一个元素表达式。

        Args:
            value: 要插入到最前面的元素表达式。
        """
        self._values.insert(0, value)

    def as_async(self) -> "ValueRef":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: TupleRef = super().as_inline(inline_mapping)
        for i, value in enumerate(self._values):
            new_expr._values[i] = value.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._values[i].inline_mapping)
        new_expr._inline_mapping[self._temp_var.name] = self._symbol_table.get_counter()
        new_expr._temp_var.rename(new_expr._inline_mapping[self._temp_var.name])
        return new_expr

    @property
    def expressions(self) -> list[Expression]:
        """获取元组中所有元素表达式的列表。"""
        return self._values

    def finish(self) -> None:
        """完成元组构建，确定最终类型并分配临时变量。

        根据所有元素的返回类型创建 TupleTypeName，
        并从符号表获取唯一名称创建临时变量。

        Raises:
            InternalCompilerException: 元组已完成构建后重复调用。
        """
        if self._is_finished:
            raise InternalCompilerException("TupleRef is already finished", self._src_info)
        self._is_finished = True
        self._type = TupleTypeName(self._src_info, list(map(lambda x: x.return_type, self._values)))
        var_name: str = self._symbol_table.get_counter()
        self._temp_var = LocalVariableName(self._src_info, var_name, self._type)

    @property
    def front_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("TupleRef is not finished", self._src_info)
        lines: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.front_text, self._values)))
        lines.append(f"{self._temp_var.name} = ({self._type.name} *)malloc(sizeof({self._type.name}));")
        lines.append(f"{self._temp_var.name}->data = malloc(sizeof(void *) * {len(self._values)});")
        lines.append(f"{self._temp_var.name}->size = {len(self._values)};")
        for i, value in enumerate(self._values):
            lines.append(f"{self._temp_var.name}->data[{i}] = {value.text};")
        return "\n".join(lines)

    @property
    def global_init_text(self) -> Optional[str]:
        result: str = "\n".join(filter(lambda x: x is not None, map(lambda x: x.global_init_text, self._values)))
        return result if result != "" else None

    @property
    def head_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("TupleRef is not finished", self._src_info)
        return f"{self._temp_var.type_name_pair_calling};"

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "TupleRef":
        new_expr: TupleRef = deepcopy(self)
        new_expr._type = self._type.instantiation(type_args)
        new_expr._values = list(map(lambda x: x.instantiation(type_args), self._values))
        return new_expr

    def optimize(self) -> "TupleRef":
        for i, v in enumerate(self._values):
            self._values[i] = v.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._values)))
        return result if result != "" else None

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._temp_var.name}->refCount == 0) {{",
            f"\tif ({self._temp_var.name}->parent) {{",
            f"\t\t{self._temp_var.name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._temp_var.name});",
            f"\t\t{self._temp_var.name} = NULL;",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        if not self._is_finished:
            raise CompilerException("TupleRef is not finished", self._src_info)
        return self._type

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "TupleRef":
        result: TupleRef = deepcopy(self)
        result._values = list(map(lambda x: x.substitute(expr), self._values))
        return result

    @property
    def text(self) -> str:
        if not self._is_finished:
            raise CompilerException("TupleRef is not finished", self._src_info)
        return self._temp_var.name

    @property
    def used_variables(self) -> set[VariableName]:
        if not self._is_finished:
            raise CompilerException("TupleRef is not finished", self._src_info)
        return set.union(*map(lambda x: x.used_variables, self._values))

    def validate(self) -> None:
        if not self._is_finished:
            raise InternalCompilerException("TupleRef is not finished", self._src_info)
        exceptions_text: list[str] = []
        for value in self._values:
            try:
                value.validate()
            except CompilerException as e:
                exceptions_text.append(str(e))
        if len(exceptions_text) > 0:
            raise CompilerException("\n\n".join(exceptions_text), self._src_info)


# TODO: 增加字典和集合的实现（推迟一个小版本）


class TypeRef(ValueRef):
    """类型引用表达式。

    表示对类型本身的引用（而非类型的值），用于泛型实例化等场景。
    例如：Array<Int> 中的 Int。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, type_symbol: TypeName) -> None:
        super().__init__(src_info, symbol_table)
        self._type: TypeName = type_symbol

    def as_async(self) -> "Expression":
        return self

    @classmethod
    def from_name(cls, src_info: SourceInfo, symbol_table: SymbolTable, type_name: str) -> "TypeRef":
        """通过类型名从符号表中查找类型，创建 TypeRef。

        Args:
            src_info: 源代码位置信息。
            type_name: 类型名称字符串。
            symbol_table: 符号表。

        Returns:
            查找到类型的 TypeRef 实例。

        Raises:
            CompilerException: 名称在符号表中不是类型时抛出。
        """
        # noinspection PyTypeChecker
        t: TypeName = symbol_table[type_name, None]
        if not isinstance(t, TypeName):
            raise CompilerException("TypeRef is not a type", src_info)
        return cls(src_info, symbol_table, t)

    @property
    def front_text(self) -> Optional[str]:
        return None

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def head_text(self) -> Optional[str]:
        return None

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: TypeRef = deepcopy(self)
        new_expr._type = self._type.instantiation(type_args)
        return new_expr

    def optimize(self) -> "Expression":
        return self

    @property
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        return self._type

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        return self

    @property
    def text(self) -> str:
        return self._type.name

    @property
    def used_variables(self) -> set[VariableName]:
        return set()

    def validate(self) -> None:
        pass


class ClassRef(TypeRef):
    """类类型引用表达式。

    通过类名从符号表查找 ClassName 类型，用于类构造函数调用（__new__）等场景。
    与 TypeRef 的区别在于它专门用于类类型，会在构造时验证名称必须是 ClassName。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, cls: ClassName) -> None:
        # noinspection PyTypeChecker
        if not isinstance(cls, ClassName):
            raise CompilerException(f"{cls.raw_name} is not a ClassName", src_info)
        super().__init__(src_info, symbol_table, cls)


class ArrayTypeRef(TypeRef):
    """数组类型引用表达式。

    表示 Array<T> 形式的数组类型，初始为 EmptyArrayTypeName，
    通过 set_type 设置元素类型后变为对应的 ArrayTypeName。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, EmptyArrayTypeName(src_info))

    def set_type(self, type_ref: TypeRef) -> None:
        """设置数组的元素类型。

        Args:
            type_ref: 元素类型的 TypeRef 引用。
        """
        self._type = ArrayTypeName(self._src_info, type_ref.return_type)


class TupleTypeRef(TypeRef):
    """元组类型引用表达式。

    表示 (T1, T2, ...) 形式的元组类型，通过 add_type 逐步收集元素类型，
    最后调用 finish 构建最终的 TupleTypeName。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, TupleTypeName(src_info, []))
        self._types: list[TypeName] = []

    def add_type(self, type_ref: TypeRef) -> None:
        """向元组类型中添加一个元素类型。

        Args:
            type_ref: 元素类型的 TypeRef 引用。
        """
        self._types.append(type_ref.return_type)

    def finish(self) -> None:
        """完成元组类型构建，用收集到的所有元素类型创建最终的 TupleTypeName。"""
        self._type = TupleTypeName(self._src_info, self._types)

    @property
    def types(self) -> list[TypeName]:
        """获取元组类型中的所有元素类型。"""
        return self._type.types


class AutoTypeRef(TypeRef):
    """自动类型引用表达式。

    表示源语言中的 auto/自动类型推导标记，编译时由编译器根据上下文自动推断具体类型。
    对应 AutoTypeName。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, AutoTypeName(src_info))


class FunctionTypeRef(TypeRef):
    """函数类型引用表达式。

    对应 FunctionTypeName。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, FunctionTypeName(src_info, [], []))
        self._arg_types: list[TypeName] = []
        self._return_types: list[TypeName] = []

    def finish(self) -> None:
        """结束对函数类型引用的设置。"""
        self._type = FunctionTypeName(self._src_info, self._arg_types, self._return_types)

    def set_arg_types(self, arg_types: TupleTypeRef) -> None:
        """设置参数类型。"""
        self._arg_types = arg_types.types

    def set_return_types(self, return_types: TupleTypeRef) -> None:
        """设置返回值类型。"""
        self._return_types = return_types.types


class Operator(Expression, ABC):
    """运算符表达式抽象基类。

    管理一个表达式操作数列表（_expr_list），支持操作数的逐步设置和完成检查。
    派生出 BinaryOperator（二元运算符）和 UnaryOperator（一元运算符）。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, expr_num: int) -> None:
        super().__init__(src_info, symbol_table)
        self._expr_list: list[Optional[Expression]] = [None] * expr_num
        self._inline_mapping: dict[str, str] = {}

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr: Operator = deepcopy(self)
        for i, expr in enumerate(self._expr_list):
            new_expr._expr_list[i] = expr.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._expr_list[i].inline_mapping)
        return new_expr

    @property
    def head_text(self) -> Optional[str]:
        return "\n".join(filter(lambda x: x is not None, map(lambda x: x.head_text, self._expr_list)))

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    @property
    def is_const(self) -> bool:
        return all(map(lambda x: x.is_const, self._expr_list))

    @property
    def is_finished(self) -> bool:
        """检查运算符的所有操作数是否已设置完成。

        Returns:
            所有操作数均不为 None 时返回 True。
        """
        return all(map(lambda x: x is not None, self._expr_list))

    def optimize(self) -> "Expression":
        for i, v in enumerate(self._expr_list):
            self._expr_list[i] = v.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._expr_list)))
        return result if result != "" else None

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        result: Operator = deepcopy(self)
        result._expr_list = [e.substitute(expr) for e in self._expr_list]
        return result

    @property
    def used_variables(self) -> set[VariableName]:
        if not self.is_finished:
            raise InternalCompilerException("Operator is not finished", self._src_info)
        return set.union(*map(lambda x: x.used_variables, self._expr_list))

    @abstractmethod
    def validate(self) -> None:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        for expr in self._expr_list:
            try:
                expr.validate()
            except CompilerException as e:
                raise CompilerException(str(e), self._src_info)

    def _set_expr(self, index: int, expr: Expression) -> None:
        """设置指定位置的操作数表达式。

        Args:
            index: 操作数位置索引。
            expr: 要设置的操作数表达式。

        Raises:
            InternalCompilerException: 该位置已有操作数时抛出。
        """
        if self._expr_list[index] is not None:
            raise InternalCompilerException("Expression is already set", self._src_info)
        self._expr_list[index] = expr


class BinaryOperator(Operator, ABC):
    """二元运算符抽象基类。

    固定有两个操作数（左和右），提供 set_expr_left / set_expr_right 方法设置操作数，
    以及 front_text 的默认实现。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, 2)

    @property
    def front_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        ret: str = self._expr_list[0].front_text if self._expr_list[0].front_text is not None else ""
        ret += self._expr_list[1].front_text if self._expr_list[1].front_text is not None else ""
        return ret if ret != "" else None

    def set_expr_left(self, expr: Expression) -> None:
        """设置二元运算符的左操作数。

        Args:
            expr: 左操作数表达式。
        """
        self._set_expr(0, expr)

    def set_expr_right(self, expr: Expression) -> None:
        """设置二元运算符的右操作数。

        Args:
            expr: 右操作数表达式。
        """
        self._set_expr(1, expr)


class AttrOp(Expression):
    """属性访问 / 方法调用运算符。

    表示 obj.attr 或 obj.method(...) 形式的操作。既可以访问属性（property），
    也可以查找并调用方法。属性名在内部以 "$" 前缀存储以区分属性和方法。
    如果父节点是 CallOp，会自动推断方法的参数类型信息。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._attr: Optional[str] = None
        self._caller: Optional[Expression] = None
        self._arg_types: Optional[list[str]] = None
        self._kwarg_types: Optional[dict[str, str]] = None
        self._inline_mapping: dict[str, str] = {}

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr: AttrOp = deepcopy(self)
        new_expr._caller = self._caller.as_inline(inline_mapping)
        new_expr._inline_mapping.update(self._caller.inline_mapping)
        return new_expr

    def as_method(self) -> MethodName:
        """将当前属性访问表达式作为方法名返回。

        在符号表中查找调用者类型的对应方法。

        Returns:
            匹配的 MethodName。

        Raises:
            CompilerException: 参数类型未知时抛出。
        """
        # noinspection PyTypeChecker
        caller_type: ClassName = self._caller.return_type
        if self._arg_types is None:
            raise CompilerException("Unknown method types.", self._src_info)
        return self._symbol_table.find_method(
            self._src_info,
            caller_type.name,
            self._attr,
            self._arg_types,
            self._kwarg_types
        )

    @property
    def attr(self) -> str:
        """获取属性名（内部以 "$" 前缀存储）。"""
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._attr

    def bind_parent(self, parent_item: "CompilingItem") -> None:
        super().bind_parent(parent_item)
        self._set_expected_type()

    @property
    def caller(self) -> Expression:
        """获取调用者表达式（即 `obj.attr` 中的 `obj`）。"""
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    def find_method(self, arg_type_list: list[str], kwarg_type_dict: dict[str, str]) -> MethodName:
        """查找匹配的方法。

        先尝试动态方法（第一个参数为调用者自身），再尝试静态方法。
        恰好匹配一个时返回，否则抛出异常。

        Args:
            arg_type_list: 参数类型名列表。
            kwarg_type_dict: 关键字参数类型名映射。

        Returns:
            匹配的 MethodName。

        Raises:
            CompilerException: 找不到方法或存在歧义时抛出。
        """
        dynamic_arg_type_list: list[str] = [self._caller.return_type.name] + arg_type_list
        dynamic_methods: list[MethodName] = self._symbol_table.find_methods(
            self._caller.return_type.name, self._attr, dynamic_arg_type_list, kwarg_type_dict
        )
        static_methods: list[MethodName] = self._symbol_table.find_methods(
            self._caller.return_type.name, self._attr, arg_type_list, kwarg_type_dict
        )
        if len(dynamic_methods) == 1:
            return dynamic_methods[0]
        if len(dynamic_methods) == 0 and len(static_methods) == 1:
            return static_methods[0]
        if len(dynamic_methods) > 1:
            raise CompilerException(
                f"Ambiguous method call: {self._caller.return_type.raw_name}.{self._attr}",
                self._src_info
            )
        raise CompilerException(
            f"Method not found: {self._caller.return_type.raw_name}.{self._attr}",
            self._src_info
        )

    @property
    def front_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller.front_text

    @property
    def global_init_text(self) -> Optional[str]:
        return self._caller.global_init_text

    @property
    def head_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller.head_text

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: AttrOp = deepcopy(self)
        new_expr._caller = self._caller.instantiation(type_args)
        new_expr._arg_types = list(map(lambda x: x.instantiation(type_args), self._arg_types))
        new_expr._kwarg_types = dict(map(lambda x: (x[0], x[1].instantiation(type_args)), self._kwarg_types.items()))
        return new_expr

    @property
    def is_finished(self) -> bool:
        """检查属性名和调用者是否都已设置。"""
        return self._attr is not None and self._caller is not None

    def optimize(self) -> "Expression":
        self._caller = self._caller.optimize()
        return self

    @property
    def outer_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller.outer_text

    @property
    def release_text(self) -> Optional[str]:
        return self._caller.release_text

    @property
    def return_type(self) -> Optional[TypeName]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        # noinspection PyTypeChecker
        caller_type: ClassName = self._caller.return_type
        if self._attr not in caller_type.properties:
            return None
        return caller_type.properties[self._attr].type

    def set_attr(self, attr: str) -> None:
        """设置属性名（内部自动添加 "$" 前缀以区分属性和方法）。

        Args:
            attr: 属性名（不含前缀）。
        """
        self._attr = "$" + attr

    def set_caller(self, caller: Expression) -> None:
        """设置调用者表达式。

        Args:
            caller: 调用者表达式（即 obj.attr 中的 obj）。
        """
        self._caller = caller

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        result = deepcopy(self)
        result._caller = result._caller.substitute(expr)
        result._set_expected_type()
        return result

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        # noinspection PyTypeChecker
        caller_type: ClassName = self._caller.return_type
        if self._attr in caller_type.properties:
            if caller_type.properties[self._attr].is_static:
                return self._caller.text + "$" + self._attr
            return f"{self._caller.text}->{self._attr}"
        return self._symbol_table.find_method(
            self._src_info,
            caller_type.raw_name,
            self._attr,
            self._arg_types,
            self._kwarg_types
        ).name

    @property
    def used_variables(self) -> set[VariableName]:
        return self._caller.used_variables

    def validate(self) -> None:
        super().validate()
        if not isinstance(self._caller.return_type, ClassName):
            raise CompilerException("Variable to get attribute is not a class type", self._src_info)
        # noinspection PyTypeChecker
        caller_type: ClassName = self._caller.return_type
        if self._arg_types is None:
            raise CompilerException("Unknown method types.", self._src_info)
        if self._attr not in caller_type.properties and not self._symbol_table.contains_method(
                caller_type.raw_name, self._attr, self._arg_types, self._kwarg_types
        ):
            raise CompilerException("Unknown attribute", self._src_info)

    def _set_expected_type(self) -> None:
        """从父节点推断方法的参数类型信息。

        如果父节点是 CallOp，则从 CallOp 的实际参数类型中提取 arg_types
        和 kwarg_types，用于后续方法查找。
        """
        if isinstance(self._parent_item, CallOp):
            self._arg_types = list(map(lambda x: x.name, self._parent_item.arg_types))
            self._kwarg_types = dict(map(lambda x: (x[0], x[1].name), self._parent_item.kwarg_types.items()))


class CallOp(Expression):
    """函数调用表达式。

    表示 func(args, kwargs) 形式的函数/方法调用。支持：
    - 同步和异步调用（as_async 转换）
    - 位置参数和关键字参数
    - 构造调用（ClassName(...) → __new__）
    - 可调用对象（obj(...) → __call__）
    - 动态/静态方法分发
    - 尾递归优化
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._is_async: bool = False
        self._call_dynamic: bool = False
        self._listener_name: Optional[str] = None
        self._call_name: Optional[str] = None
        self._func_expr: Optional[Expression] = None
        self._func: Optional[FunctionName] = None
        self._arg_list: list[Optional[Expression]] = []
        self._kwarg_dict: dict[str, Optional[Expression]] = {}
        self._had_set_args_num: Optional[int] = 0
        self._args_tuple: Optional[TupleRef] = None
        self._returns_list: list[VariableName] = []
        self._returns_tuple: Optional[TupleRef] = None
        self._unpack_expr: Optional[UnpackExpr] = None
        self._call_struct: bool = False
        self._inline_mapping: dict[str, str] = {}

    def add_arg(self, expr: Expression, arg_name: Optional[str]) -> None:
        """添加一个调用参数。

        关键字参数必须放在位置参数之后——一旦出现关键字参数，
        后续不能再添加位置参数。

        Args:
            expr: 参数表达式。
            arg_name: 关键字参数名，None 表示位置参数。

        Raises:
            CompilerException: 在关键字参数之后尝试添加位置参数。
        """
        if arg_name is not None:
            self._had_set_args_num = None
            self._kwarg_dict[arg_name] = expr
        else:
            if self._had_set_args_num is None:
                raise CompilerException("Trying to set an argument without name after keyword arguments.",
                                        self._src_info)
            self._arg_list.append(expr)
            self._had_set_args_num += 1

    @property
    def arg_types(self) -> list[TypeName]:
        """获取位置参数的类型列表。"""
        return [arg.return_type for arg in self._arg_list]

    def as_async(self) -> "Expression":
        result: CallOp = deepcopy(self)
        result._is_async = True
        result._listener_name = self._symbol_table.get_counter()
        result._call_name = result._listener_name + "$$_call"
        result._args_tuple = TupleRef(self._src_info, self._symbol_table)
        for arg in self._arg_list:
            result._args_tuple.append(arg, self._src_info)
        return result

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr: CallOp = deepcopy(self)
        new_expr._func_expr = new_expr._func_expr.as_inline(inline_mapping)
        new_expr._inline_mapping = inline_mapping
        for i, arg in enumerate(new_expr._arg_list):
            new_expr._arg_list[i] = arg.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._arg_list[i].inline_mapping)
        for k, arg in new_expr._kwarg_dict.items():
            new_expr._kwarg_dict[k] = arg.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._kwarg_dict[k].inline_mapping)
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "CallOp":
        if func_name == self._func.name:
            return TailRecursiveCall.from_call_op(self)
        return self

    @property
    def front_text(self) -> str:
        children_front_text: str = ("\n".join(
            filter(lambda x: x is not None, map(lambda x: x.front_text, self._arg_list))) + "\n" + "\n".join(
            filter(lambda x: x is not None, map(lambda x: x.front_text, self._kwarg_dict.values())))) + (
                                           "\n" + self._func_expr.front_text
                                   ) if self._func_expr.front_text is not None else ""
        listener_text: list[str] = [
            f"{self._listener_name} = ({LISTENER_T} *)malloc(sizeof({LISTENER_T}));",
            f"{LISTENER_INIT_FUNC}({self._listener_name}, listener->currentThreadId);"
        ]
        result: list[str] = [children_front_text] if children_front_text != "" else []
        if self._is_async:
            result.append("\n".join(listener_text))
            if len(self._returns_list) == 0:
                ret_text: str = "NULL"
            else:
                ret_text = "&" + self._returns_tuple.text
            if len(self._arg_list) + len(self._kwarg_dict.keys()) == 0:
                arg_text: str = "NULL"
            else:
                arg_text = self._args_tuple.text
            # call = self._func_expr.as_async().text + self._get_func_extend + f"({arg_text}, {ret_text}, {self._listener_name});"
            call = "\n".join([
                f"{self._call_name} = ({FUNC_CALL_T} *)malloc(sizeof({FUNC_CALL_T}));",
                f"{self._call_name}->args = {arg_text};",
                f"{self._call_name}->rets = {ret_text};",
                f"{self._call_name}->func = {self._func_expr.as_async().text + self._get_func_extend};",
                f"{self._call_name}->listener = {self._listener_name};",
                f"{FUNC_ENQUEUE_FUNC}({self._call_name});",
            ])
        else:
            args_str: str = ", ".join(map(lambda x: x.text, self._arg_list)) + ", " if len(self._arg_list) > 0 else ""
            rets_str: str = ", ".join(map(lambda x: x.text, self._returns_list)) + ", " if len(
                self._returns_list) > 0 else ""
            call = self._func_expr.text + self._get_func_extend + f"({args_str}{rets_str}listener);"
        result.append(call)
        if len(self._returns_list) > 1:
            if self._is_async:
                result.append(self._unpack_expr.front_text)
        return "\n".join(result)

    @property
    def global_init_text(self) -> Optional[str]:
        return None

    @property
    def head_text(self) -> Optional[str]:
        results: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.head_text, self._arg_list)))
        results.extend(filter(lambda x: x is not None, map(lambda x: x.head_text, self._kwarg_dict.values())))
        if self._func_expr.head_text is not None:
            results.append(self._func_expr.head_text)
        if self._is_async:
            results.append(f"{LISTENER_T} *{self._listener_name};")
            results.append(f"{FUNC_CALL_T} *{self._call_name};")
        if len(results) == 0:
            return None
        return "\n".join(results)

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "CallOp":
        new_expr: CallOp = deepcopy(self)
        new_expr._func_expr = new_expr._func_expr.instantiation(type_args)
        new_expr._arg_list = list(map(lambda x: x.instantiation(type_args), self._arg_list))
        new_expr._kwarg_dict = {k: v.instantiation(type_args) for k, v in self._kwarg_dict.items()}
        new_expr._returns_list = list(map(lambda x: x.instantiation(x.name, type_args), self._returns_list))
        new_expr._returns_tuple = self._returns_tuple.instantiation(type_args)
        return new_expr

    @property
    def listener_name(self) -> Optional[str]:
        return self._listener_name if self._is_async else None

    @property
    def kwarg_types(self) -> dict[str, TypeName]:
        """获取关键字参数的类型映射（参数名 → TypeName）。"""
        return {k: v.type_name for k, v in self._kwarg_dict.items()}

    def optimize(self) -> "Expression":
        for i, arg in enumerate(self._arg_list):
            self._arg_list[i] = arg.optimize()
        for k, arg in self._kwarg_dict.items():
            self._kwarg_dict[k] = arg.optimize()
        self._func_expr = self._func_expr.optimize()
        self._returns_tuple = self._returns_tuple.optimize() if self._returns_tuple is not None else None
        self._args_tuple = self._args_tuple.optimize() if self._args_tuple is not None else None
        return self

    @property
    def outer_text(self) -> Optional[str]:
        func_outer_text: Optional[str] = self._func_expr.outer_text
        args_outer_text: str = "\n\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._arg_list)))
        kwargs_outer_text: str = "\n\n".join(
            filter(lambda x: x is not None, map(lambda x: x.outer_text, self._kwarg_dict.values())))
        result: list[str] = list(filter(
            lambda x: x is not None,
            [func_outer_text, args_outer_text if args_outer_text != "" else None,
             kwargs_outer_text if kwargs_outer_text != "" else None]
        ))
        result_str: str = "\n\n".join(result)
        return result_str if result_str != "" else None

    @property
    def release_text(self) -> Optional[str]:
        result: list[Optional[str]] = [
            self._args_tuple.release_text if self._args_tuple is not None else None,
            self._unpack_expr.release_text if self._unpack_expr is not None else None,
            self._returns_tuple.release_text if self._returns_tuple is not None else None
        ]
        result_str: str = "\n".join(filter(lambda x: x is not None, result))
        return result_str if result_str != "" else None

    @property
    def return_type(self) -> TypeName:
        if len(self._func.type.returns) == 1:
            return self._func.type.returns[0]
        return TupleTypeName(self._src_info, self._func.type.returns)

    def set_func(self, expr: Expression) -> None:
        """设置被调用的函数表达式，根据表达式类型自动处理分发逻辑。

        支持四种调用形式：
        - 类构造：ClassRef → 调用 __new__
        - 可调用对象：return_type 是 ClassName → 调用 __call__
        - 普通函数：VariableRef 直接引用函数
        - 方法调用：AttrOp → 动态/静态方法分发

        同时处理默认参数填充：将未提供的位置参数用默认值补全。

        Args:
            expr: 表示被调用函数的表达式。

        Raises:
            CompilerException: 缺少参数且无默认值时抛出。
        """
        if isinstance(expr, ClassRef):
            attr_op = AttrOp(self._src_info, self._symbol_table)
            attr_op.set_caller(expr)
            attr_op.set_attr("__new__")
            self._func = attr_op.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            ).as_function()
            self._func_expr = attr_op
        elif isinstance(expr.return_type, ClassName):
            attr_op = AttrOp(self._src_info, self._symbol_table)
            attr_op.set_caller(expr)
            attr_op.set_attr("__call__")
            self._func = attr_op.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            ).as_function()
            self._func_expr = attr_op
            self._call_dynamic = True
            self._arg_list = [expr] + self._arg_list
        elif isinstance(expr, VariableRef):
            self._func = expr.var
            self._func_expr = expr
        elif isinstance(expr, AttrOp):
            method = expr.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            )
            # noinspection PyUnresolvedReferences
            self._call_dynamic = not method.is_static
            self._func = method.as_function()
            self._func_expr = expr
            if self._call_dynamic:
                self._arg_list = [expr.caller] + self._arg_list
        else:
            self._func_expr = expr
            self._call_struct = True
        if self._func is not None:
            func_arg_names: list[str] = self._func.arg_names[len(self._arg_list):]
            for n in func_arg_names:
                if n in self._kwarg_dict:
                    self._arg_list.append(self._kwarg_dict[n])
                else:
                    default_value: Optional[GlobalVariableName] = self._func.default_params[n]
                    if default_value is None:
                        raise CompilerException(f"Missing argument: {n}", self._src_info)
                    self._arg_list.append(VariableRef(self._src_info, self._symbol_table, default_value))

    def set_returns(self, returns: Optional[list[VariableName]]) -> bool:
        self._returns_list = returns
        self._returns_tuple = TupleRef(self._src_info, self._symbol_table)
        for ret in self._returns_list:
            self._returns_tuple.add_value(VariableRef(self._src_info, self._symbol_table, ret))
        if len(returns) > 1:
            self._unpack_expr = UnpackExpr(self._src_info, self._symbol_table, self)
            self._unpack_expr.set_returns(returns)
        return True

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        result = deepcopy(self)
        result._func_expr = result._func_expr.substitute(expr)
        result._arg_list = list(map(lambda x: x.substitute(expr), result._arg_list))
        result._kwarg_dict = dict(map(lambda x: (x[0], x[1].substitute(expr)), result._kwarg_dict.items()))
        result._args_tuple = result._args_tuple.substitute(expr)
        result._returns_tuple = result._returns_tuple.substitute(expr)
        return result

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        return_types: TypeName = self.return_type
        if not isinstance(return_types, TupleTypeName):
            return self._returns_list[0].name
        if len(return_types.types) == 0:
            return "NULL"
        if not self._is_async:
            return self._returns_tuple.text
        return self._unpack_expr.text

    @property
    def used_variables(self) -> set[VariableName]:
        result = set.union(
            *map(lambda x: x.used_variables, self._arg_list),
            self._func_expr.used_variables
        )
        return result

    def validate(self) -> None:
        if not isinstance(self._func_expr.return_type, ClassName) and not isinstance(self._func_expr.return_type,
                                                                                     FunctionTypeName):
            raise CompilerException("Function call is not allowed on this expression", self._src_info)

    @property
    def _get_func_extend(self) -> str:
        """获取函数名的 C 调用后缀。

        生成如 "$sync"、"$async" 的后缀用于查找对应的 C 函数变体。
        结构体调用（_call_struct）以 "->" 前缀（如 "->$sync"）区分调用约定。
        """
        if self._is_async:
            result = "$async"
        else:
            result = "$sync"
        if self._call_struct:
            result = "->" + result
        return result


class TailRecursiveCall(CallOp):
    """尾递归调用表达式。

    将满足尾递归条件的函数调用转换为 goto 循环，避免栈溢出。
    通过 from_call_op 工厂方法从普通 CallOp 转换而来。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._mark_name: Optional[str] = None
        self._decl: Optional[FunctionName] = None

    @classmethod
    def from_call_op(cls, call_op: CallOp) -> "TailRecursiveCall":
        """从普通 CallOp 转换创建尾递归调用。

        会将参数和返回值信息从原始 CallOp 复制到新 TailRecursiveCall 实例。

        Args:
            call_op: 原始函数调用表达式。

        Returns:
            尾递归调用表达式实例。

        Raises:
            InternalCompilerException: 被调用者不是 VariableRef 时抛出。
        """
        result = cls(call_op._src_info, call_op._symbol_table)
        if not isinstance(call_op._func_expr, VariableRef):
            raise InternalCompilerException("Tail recursive call is not allowed on this expression", call_op._src_info)
        result.set_func(call_op._func_expr)
        result.set_returns(call_op._returns_list)
        for arg in call_op._arg_list:
            result.add_arg(arg, None)
        for name, kwarg in call_op._kwarg_dict.items():
            result.add_arg(kwarg, name)
        return result

    @property
    def front_text(self) -> Optional[str]:
        super_text = super().front_text
        arg_free: list[str] = []

        def free_arg(arg_expr: VariableName) -> None:
            del_var: VariableRef = VariableRef(self._src_info, self._symbol_table, arg_expr)
            del_call: CallOp = CallOp(self._src_info, self._symbol_table)
            del_method: AttrOp = AttrOp(self._src_info, self._symbol_table)
            del_method.set_caller(del_var)
            del_method.set_attr("__del__")
            del_call.set_func(del_method)
            del_call.set_returns([])
            del_call.validate()
            arg_free.append(del_call.front_text + ";")

        for arg in self._decl.args:
            if arg.type.is_object and arg not in self.used_variables:
                free_arg(arg)
        arg_changes: list[str] = list(map(lambda src, dst: f"{src.text} = {dst.text};",
                                          self._arg_list, self._decl.arg_names[:len(self._arg_list)]))
        kwarg_changes: list[str] = list(map(lambda k, v: f"{k} = {v};", *self._kwarg_dict.items()))
        goto_text = f"goto {self._mark_name};"
        return "\n".join([super_text, *arg_changes, *kwarg_changes, goto_text])

    def set_func(self, expr: VariableRef) -> None:
        if not isinstance(expr.return_type, FunctionName):
            raise InternalCompilerException("Tail recursive call is not allowed on this expression", self._src_info)
        super().set_func(expr)
        self._mark_name = expr.text + "$$tailRecursive"
        # noinspection PyTypeChecker
        self._decl = expr.var

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return self._mark_name + ":"


class BinaryMathOp(BinaryOperator):
    """二元数学/逻辑运算符基类。

    处理运算符重载的核心逻辑：如果操作数类型定义了对应的魔术方法（如 __add__），
    则转换为 CallOp 调用；否则对基本类型直接生成 C 运算符代码。
    支持常量折叠优化（通过 optimizer lambda）。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, op: Optional[str], left_magic_method: Optional[str],
                 right_magic_method: Optional[str], default_return_type: Optional[TypeName],
                 optimizer: Optional[Callable[[int | float, int | float], int | float]] = None) -> None:
        super().__init__(src_info, symbol_table)
        self._op: Optional[str] = op
        self._left_magic_method: Optional[str] = left_magic_method
        self._right_magic_method: Optional[str] = right_magic_method
        self._default_return_type: Optional[TypeName] = default_return_type
        self._returns_list: list[VariableName] = []
        self._call_op: Optional[CallOp] = None
        self._optimizer: Optional[Callable[[int | float, int | float], int | float]] = optimizer

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.as_async()
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        if self._call_op is not None:
            return self._call_op.as_inline(inline_mapping)
        return super().as_inline(inline_mapping)

    def check_tail_recursive(self, func_name: str) -> "Expression":
        if self._call_op is not None:
            new_expr = deepcopy(self)
            return new_expr._call_op.check_tail_recursive(func_name)
        return self

    @property
    def front_text(self) -> Optional[str]:
        result = super().front_text
        if result is None:
            result = ""
        if self._call_op is not None:
            result += self._call_op.front_text
        return result if result != "" else None

    @property
    def global_init_text(self) -> Optional[str]:
        return self._call_op.global_init_text if self._call_op is not None else None

    @property
    def head_text(self) -> Optional[str]:
        result = super().head_text
        if result is None:
            result = ""
        if self._call_op is not None:
            result += self._call_op.head_text
        return result if result != "" else None

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "BinaryMathOp":
        new_expr = deepcopy(self)
        if self._call_op is not None:
            new_expr._call_op = self._call_op.instantiation(type_args)
        new_expr._expr_list = list(map(lambda expr: expr.instantiation(type_args), self._expr_list))
        return new_expr

    @property
    def is_const(self) -> bool:
        return self._call_op is None and super().is_const

    @property
    def listener_name(self) -> Optional[str]:
        return self._call_op.listener_name if self._call_op is not None else None

    def optimize(self) -> "Expression":
        optimized = super().optimize()
        if self._call_op is not None:
            return optimized._call_op.optimize()
        if all(isinstance(expr, Literal) and expr.value is not None for expr in optimized._expr_list):
            new_value: int | float = self._optimizer(self._expr_list[0].value, self._expr_list[1].value)
            if isinstance(new_value, int):
                return IntegerLiteral(self._src_info, self._symbol_table, str(new_value))
            return FloatLiteral(self._src_info, self._symbol_table, str(new_value))
        return optimized

    @property
    def release_text(self) -> Optional[str]:
        if self._call_op is not None:
            return self._call_op.release_text
        return None

    @property
    def return_type(self) -> TypeName:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.as_async().return_type
        if self._default_return_type is not None:
            return self._default_return_type
        return self._expr_list[0].return_type

    def set_expr_left(self, expr: Expression) -> None:
        super().set_expr_left(expr)
        if self._expr_list[1] is not None:
            self._set_call_op()

    def set_expr_right(self, expr: Expression) -> None:
        super().set_expr_right(expr)
        if self._expr_list[0] is not None:
            self._set_call_op()

    def set_returns(self, returns: list[VariableName]) -> bool:
        self._returns_list = returns
        if self._call_op is not None:
            self._call_op.set_returns(returns)
        return self._call_op is not None

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        if self._call_op is not None:
            return self._call_op.substitute(expr)
        result = super().substitute(expr)
        return result

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return self._call_op.tail_recursive_mark if self._call_op is not None else None

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.text
        if len(self._returns_list) == 1:
            return f"{self._returns_list[0].name} = {self._expr_list[0].text} {self._op} {self._expr_list[1].text};"
        return f"{self._expr_list[0].text} {self._op} {self._expr_list[1].text}"

    def validate(self) -> None:
        super().validate()
        expr_left: Expression = self._expr_list[0]
        expr_right: Expression = self._expr_list[1]
        # noinspection PyUnresolvedReferences
        if (not (isinstance(expr_left.return_type,
                            ClassName) and self._left_magic_method in expr_left.return_type.methods) and not (
                isinstance(expr_right.return_type,
                           ClassName) and self._right_magic_method in expr_right.return_type.methods)):
            raise CompilerException(
                f"Method {expr_left.return_type}.{self._left_magic_method}({expr_right.return_type.raw_name} other) "
                f"and {expr_right.return_type}.{self._right_magic_method}({expr_left.return_type.raw_name} other) "
                f"are not defined.", self._src_info
            )
        if isinstance(expr_left.return_type, BaseTypeName) and isinstance(expr_right.return_type,
                                                                          BaseTypeName) and self._op is None:
            raise CompilerException("This operator is not defined for two base types", self._src_info)

    def _set_call_op(self) -> None:
        """尝试将二元运算符转换为魔术方法调用（运算符重载）。

        检查左右操作数类型是否定义了对应的魔术方法：
        - 基本类型之间：直接使用 C 运算符
        - 类类型定义了左侧魔术方法：转换为左侧操作数的 CallOp
        - 类类型定义了右侧魔术方法：转换为右侧操作数的 CallOp
        - 均不支持：抛出异常
        """
        expr_left: Expression = self._expr_list[0]
        expr_right: Expression = self._expr_list[1]
        if expr_left.return_type not in self._symbol_table:
            raise CompilerException(f"Type {expr_left.return_type} is not defined", self._src_info)
        if expr_right.return_type not in self._symbol_table:
            raise CompilerException(f"Type {expr_right.return_type} is not defined", self._src_info)
        if isinstance(expr_left.return_type, BaseTypeName) and isinstance(expr_right.return_type, BaseTypeName):
            if self._op is None:
                raise CompilerException("This operator is not defined for two base types.", self._src_info)
            return
        if self._left_magic_method is None and self._right_magic_method is None:
            raise CompilerException("This operator is not defined for two class types.", self._src_info)
        # noinspection PyUnresolvedReferences
        if isinstance(expr_left.return_type, ClassName) and self._left_magic_method in expr_left.return_type.methods:
            self._call_op = CallOp(self._src_info, self._symbol_table)
            self._call_op.add_arg(expr_left, None)
            self._call_op.add_arg(expr_right, None)
            self._call_op.set_func(self._expr_list[0])
            self._call_op.set_returns(self._returns_list)
            return
        # noinspection PyUnresolvedReferences
        if isinstance(expr_right.return_type, ClassName) and self._right_magic_method in expr_right.return_type.methods:
            self._call_op = CallOp(self._src_info, self._symbol_table)
            self._call_op.add_arg(expr_left, None)
            self._call_op.add_arg(expr_right, None)
            self._call_op.set_func(self._expr_list[1])
            self._call_op.set_returns(self._returns_list)
            return
        raise CompilerException(
            f"Method {expr_left.return_type}.{self._left_magic_method}({expr_right.return_type.raw_name} other) "
            f"and {expr_right.return_type}.{self._right_magic_method}({expr_left.return_type.raw_name} other) "
            f"are not defined.", self._src_info)


class AddOp(BinaryMathOp):
    """加法运算符 `+`，魔术方法 `__add__` / `__radd__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "+", "__add__", "__radd__", None, lambda x, y: x + y)


class SubOp(BinaryMathOp):
    """减法运算符 `-`，魔术方法 `__sub__` / `__rsub__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "-", "__sub__", "__rsub__", None, lambda x, y: x - y)


class MulOp(BinaryMathOp):
    """乘法运算符 `*`，魔术方法 `__mul__` / `__rmul__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "*", "__mul__", "__rmul__", None, lambda x, y: x * y)


class DivOp(BinaryMathOp):
    """除法运算符 `/`，魔术方法 `__div__` / `__rdiv__`（C 中为整数除法 `//`）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "/", "__div__", "__rdiv__", None, lambda x, y: x // y)


class ModOp(BinaryMathOp):
    """取模运算符 `%`，魔术方法 `__mod__` / `__rmod__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "%", "__mod__", "__rmod__", None, lambda x, y: x % y)


class MatMulOp(BinaryMathOp):
    """矩阵乘法运算符 `@`，魔术方法 `__matmul__` / `__rmatmul__`（无 C 运算符，只能类重载）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, None, "__matmul__", "__rmatmul__", None)


class PowOp(BinaryMathOp):
    """幂运算符 `**`，魔术方法 `__pow__` / `__rpow__`。

    基本类型编译为 C 的 pow() 函数调用而非中缀运算符。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, None, "__pow__", "__rpow__", None, lambda x, y: x ** y)

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.text
        if len(self._returns_list) == 1:
            return f"{self._returns_list[0].name} = pow({self._expr_list[0].text}, {self._expr_list[1].text});"
        return f"pow({self._expr_list[0].text}, {self._expr_list[1].text})"


class LeftShiftOp(BinaryMathOp):
    """左移运算符 `<<`，魔术方法 `__lshift__` / `__rlshift__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "<<", "__lshift__", "__rlshift__", None, lambda x, y: x << y)


class RightShiftOp(BinaryMathOp):
    """右移运算符 `>>`，魔术方法 `__rshift__` / `__rrshift__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, ">>", "__rshift__", "__rrshift__", None, lambda x, y: x >> y)


class BitAndOp(BinaryMathOp):
    """按位与运算符 `&`，魔术方法 `__and__` / `__rand__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "&", "__and__", "__rand__", None, lambda x, y: x & y)


class BitOrOp(BinaryMathOp):
    """按位或运算符 `|`，魔术方法 `__or__` / `__ror__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "|", "__or__", "__ror__", None, lambda x, y: x | y)


class BitXorOp(BinaryMathOp):
    """按位异或运算符 `^`，魔术方法 `__xor__` / `__rxor__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "^", "__xor__", "__rxor__", None, lambda x, y: x ^ y)


class LogicalAndOp(BinaryMathOp):
    """逻辑与运算符 `&&`，返回 BOOL，仅支持基本类型（无魔术方法）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "&&", None, None, BOOL, lambda x, y: x and y)


class LogicalOrOp(BinaryMathOp):
    """逻辑或运算符 `||`，返回 BOOL，仅支持基本类型（无魔术方法）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "||", None, None, BOOL, lambda x, y: x or y)


class GreaterThanOp(BinaryMathOp):
    """大于运算符 `>`，魔术方法 `__gt__` / `__lt__`，返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, ">", "__gt__", "__lt__", BOOL, lambda x, y: x > y)


class LessThanOp(BinaryMathOp):
    """小于运算符 `<`，魔术方法 `__lt__` / `__gt__`，返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "<", "__lt__", "__gt__", BOOL, lambda x, y: x < y)


class GreaterThanOrEqualOp(BinaryMathOp):
    """大于等于运算符 `>=`，魔术方法 `__ge__` / `__le__`，返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, ">=", "__ge__", "__le__", BOOL, lambda x, y: x >= y)


class LessThanOrEqualOp(BinaryMathOp):
    """小于等于运算符 `<=`，魔术方法 `__le__` / `__ge__`，返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "<=", "__le__", "__ge__", BOOL, lambda x, y: x <= y)


class EqualOp(BinaryMathOp):
    """等于运算符 `==`，魔术方法 `__eq__`（两侧相同），返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "==", "__eq__", "__eq__", BOOL, lambda x, y: x == y)


class NotEqualOp(BinaryMathOp):
    """不等于运算符 `!=`，魔术方法 `__ne__`（两侧相同），返回 BOOL。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "!=", "__ne__", "__ne__", BOOL, lambda x, y: x != y)


class ItemOp(CallOp):
    """下标访问运算符 `obj[index]`。

    将下标操作转换为 `__getitem__` 魔术方法调用。继承自 CallOp，
    通过 set_expr_left 设置被索引的容器对象并自动绑定 `__getitem__` 方法。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)

    def set_expr_left(self, expr: Expression) -> None:
        """设置被索引的容器对象，并自动绑定 `__getitem__` 方法。

        Args:
            expr: 容器对象表达式（必须是类类型且定义了 __getitem__）。

        Raises:
            CompilerException: 类型不是类类型或未定义 __getitem__ 时抛出。
        """
        if not isinstance(expr.return_type, ClassName):
            raise CompilerException(
                f"Item operator can only be used with class types, but {expr.return_type.raw_name} is given.",
                self._src_info
            )
        # noinspection PyTypeChecker
        expr_type: ClassName = expr.return_type
        if "__getitem__" not in expr_type.methods:
            raise CompilerException(
                f"Method {expr.return_type}.__getitem__(...) is not defined.", self._src_info
            )
        new_expr: AttrOp = AttrOp(self._src_info, self._symbol_table)
        new_expr.set_caller(expr)
        new_expr.set_attr("__getitem__")
        super().set_func(new_expr)


class UnaryOperator(Operator, ABC):
    """一元运算符抽象基类。

    固定有一个操作数，提供 set_expr 方法设置操作数。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, 1)

    def set_expr(self, expr: Expression) -> None:
        """设置一元运算符的操作数。

        Args:
            expr: 唯一的操作数表达式。
        """
        self._set_expr(0, expr)


class BracketsOp(UnaryOperator):
    """括号运算符 `(expr)`。

    仅用于改变运算优先级，不做任何额外操作，
    直接透传内部表达式的所有属性和行为。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        new_op: BracketsOp = BracketsOp(self._src_info, self._symbol_table)
        new_op.set_expr(self._expr_list[0].as_async())
        return new_op

    def check_tail_recursive(self, func_name: str) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._expr_list[0] = self._expr_list[0].check_tail_recursive(func_name)
        return new_expr

    @property
    def front_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._expr_list[0].front_text

    @property
    def global_init_text(self) -> Optional[str]:
        return self._expr_list[0].global_init_text

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: BracketsOp = deepcopy(self)
        new_expr._expr_list[0] = self._expr_list[0].instantiation(type_args)
        return new_expr

    @property
    def listener_name(self) -> Optional[str]:
        return self._expr_list[0].listener_name

    @property
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._expr_list[0].return_type

    def set_returns(self, returns: list[VariableName]) -> bool:
        return self._expr_list[0].set_returns(returns)

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return self._expr_list[0].tail_recursive_mark

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return f"({self._expr_list[0].text})"

    def validate(self) -> None:
        super().validate()


class UnaryMathOp(UnaryOperator):
    """一元数学/逻辑运算符基类。

    处理一元运算符重载：如果操作数类型定义了对应的魔术方法（如 __neg__），
    则转换为 CallOp 调用；否则对基本类型直接生成 C 运算符代码。
    支持常量折叠优化（通过 optimizer lambda）。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, op: str, magic_method: Optional[str],
                 optimizer: Optional[Callable[[int | float], int | float]] = None) -> None:
        super().__init__(src_info, symbol_table)
        self._op: str = op
        self._magic_method: Optional[str] = magic_method
        self._returns_list: list[VariableName] = []
        self._call_op: Optional[CallOp] = None
        self._optimizer: Optional[Callable[[int | float], int | float]] = optimizer

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        expr: Expression = self._expr_list[0]
        if expr.return_type not in self._symbol_table:
            raise CompilerException(f"Type {expr.return_type} is not defined", self._src_info)
        if isinstance(expr.return_type, ClassName):
            if self._magic_method is None:
                raise CompilerException(
                    f"This operator can only be used with basic types, but {expr.return_type.raw_name} is given.",
                    self._src_info
                )
            # noinspection PyUnresolvedReferences
            if self._magic_method in expr.return_type.methods:
                result = CallOp(self._src_info, self._symbol_table)
                caller_op: AttrOp = AttrOp(self._src_info, self._symbol_table)
                caller_op.set_caller(expr)
                caller_op.set_attr(self._magic_method)
                result.set_func(caller_op)
                result.set_returns(self._returns_list)
                return result.as_async()
        if isinstance(expr.return_type, BaseTypeName):
            return self
        raise CompilerException(f"Method {expr.return_type.raw_name}.{self._magic_method}() is not defined.",
                                self._src_info)

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        if self._call_op is not None:
            return self._call_op.as_inline(inline_mapping)
        return super().as_inline(inline_mapping)

    def check_tail_recursive(self, func_name: str) -> "Expression":
        new_expr = deepcopy(self)
        if self._call_op is not None:
            new_expr._call_op = self._call_op.check_tail_recursive(func_name)
        return new_expr

    @property
    def front_text(self) -> Optional[str]:
        return super().front_text

    @property
    def global_init_text(self) -> Optional[str]:
        return self._call_op.global_init_text if self._call_op is not None else None

    @property
    def head_text(self) -> Optional[str]:
        result: Optional[str] = super().head_text
        if result is None:
            result = ""
        else:
            result += "\n"
        if self._call_op is not None:
            result += self._call_op.head_text
        return result if result != "" else None

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: UnaryMathOp = deepcopy(self)
        new_expr._expr_list[0] = self._expr_list[0].instantiation(type_args)
        if self._call_op is not None:
            new_expr._call_op = self._call_op.instantiation(type_args)
        new_expr._returns_list = list(map(lambda x: x.instantiation(x.name, type_args), self._returns_list))
        return new_expr

    @property
    def is_const(self) -> bool:
        return self._call_op is None and super().is_const

    @property
    def listener_name(self) -> Optional[str]:
        return self._call_op.listener_name if self._call_op is not None else None

    def optimize(self) -> "Expression":
        optimized = super().optimize()
        if self._call_op is not None:
            return optimized._call_op.optimize()
        if isinstance(optimized._expr_list[0], Literal) and optimized._expr_list is not None and self._optimizer is not None:
            if isinstance(optimized._expr_list[0], IntegerLiteral):
                return IntegerLiteral(self._src_info, self._symbol_table, str(self._optimizer(optimized._expr_list[0].value)))
            return FloatLiteral(self._src_info, self._symbol_table, str(self._optimizer(optimized._expr_list[0].value)))
        return optimized

    @property
    def release_text(self) -> Optional[str]:
        if self._call_op is not None:
            return self._call_op.release_text
        return None

    @property
    def return_type(self) -> TypeName:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.return_type
        return self._expr_list[0].return_type

    def set_call_op(self) -> None:
        """尝试将一元运算符转换为魔术方法调用（运算符重载）。

        检查操作数类型是否定义了对应的魔术方法：
        - 基本类型：直接使用 C 运算符，不做转换
        - 类类型定义了魔术方法：转换为 CallOp 调用
        - 类类型未定义魔术方法：抛出异常
        """
        if isinstance(self._expr_list[0].return_type, BaseTypeName):
            return
        # noinspection PyUnresolvedReferences
        if (isinstance(self._expr_list[0].return_type, ClassName)
                and self._magic_method in self._expr_list[0].return_type.methods):
            self._call_op = CallOp(self._src_info, self._symbol_table)
            caller_op: AttrOp = AttrOp(self._src_info, self._symbol_table)
            caller_op.set_caller(self._expr_list[0])
            caller_op.set_attr(self._magic_method)
            self._call_op.set_func(caller_op)
            self._call_op.set_returns(self._returns_list)
            return
        raise CompilerException(f"Method {self._expr_list[0].return_type}.{self._magic_method}() is not defined.",
                                self._src_info)

    def set_expr(self, expr: Expression) -> None:
        super().set_expr(expr)
        self.set_call_op()

    def set_returns(self, returns: list[VariableName]) -> bool:
        self._returns_list = returns
        if self._call_op is not None:
            self._call_op.set_returns(returns)
        return self._call_op is not None

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        if self._call_op is not None:
            return self._call_op.substitute(expr)
        result = super().substitute(expr)
        return result

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return self._call_op.tail_recursive_mark if self._call_op is not None else None

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        if self._call_op is not None:
            return self._call_op.text
        if len(self._returns_list) == 1:
            return f"{self._returns_list[0].name} = {self._op}{self._expr_list[0].text};"
        return f"{self._op}{self._expr_list[0].text}"

    def validate(self) -> None:
        super().validate()
        # noinspection PyUnresolvedReferences
        if (isinstance(self._expr_list[0].return_type, ClassName)
                and self._magic_method not in self._expr_list[0].return_type.methods):
            raise CompilerException(f"Method {self._expr_list[0].return_type}.{self._magic_method}() is not defined.",
                                    self._src_info)


class PositiveOp(UnaryMathOp):
    """正号运算符 `+`，魔术方法 `__pos__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "+", "__pos__", lambda x: x)


class NegativeOp(UnaryMathOp):
    """负号运算符 `-`，魔术方法 `__neg__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "-", "__neg__", lambda x: -x)


class BitNotOp(UnaryMathOp):
    """按位取反运算符 `~`，魔术方法 `__invert__`。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "~", "__invert__", lambda x: ~x)


class LogicalNotOp(UnaryMathOp):
    """逻辑非运算符 `!`，仅支持基本类型（无魔术方法）。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, "!", None, lambda x: not x)


def _indent(text: Optional[str]) -> Optional[str]:
    """对多行文本每行添加一个制表符缩进，用于生成嵌套的 C 代码。

    Args:
        text: 需要缩进的文本，可为 None。

    Returns:
        缩进后的文本，如果输入为 None 或空字符串则返回 None。
    """
    if text is None:
        return None
    result = "\n".join(["\t" + line for line in text.split("\n")])
    return result if result != "" else None


class ConditionalOp(Operator):
    """三元条件运算符 `cond ? then : else`。

    编译为 C 的 if-else 语句块。自动推导两个分支的公共返回类型：
    基本类型取降级类型，类类型取公共父类。支持常量条件优化。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table, 3)
        self._temp_name: str = self._symbol_table.get_counter()
        self._type_name: Optional[TypeName] = None

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: ConditionalOp = super().as_inline(inline_mapping)
        new_expr._inline_mapping[self._temp_name] = self._symbol_table.get_counter()
        new_expr._temp_name = new_expr._inline_mapping[self._temp_name]
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._expr_list[1] = self._expr_list[1].check_tail_recursive(func_name)
        new_expr._expr_list[2] = self._expr_list[2].check_tail_recursive(func_name)
        return new_expr

    @property
    def front_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        result: list[Optional[str]] = [
            self._expr_list[0].front_text,
            f"if ({self._expr_list[0].text}) {{",
            _indent(self._expr_list[1].head_text),
            _indent(self._expr_list[1].front_text),
            f"\t{self._temp_name} = {self._expr_list[1].text};",
            "} else {",
            _indent(self._expr_list[2].head_text),
            _indent(self._expr_list[2].front_text),
            f"\t{self._temp_name} = {self._expr_list[2].text};",
            "}"
        ]
        return "\n".join(list(filter(lambda x: x is not None, result)))

    @property
    def global_init_text(self) -> Optional[str]:
        result: str = "\n".join(filter(lambda x: x is not None, [
            self._expr_list[0].global_init_text,
            self._expr_list[1].global_init_text,
            self._expr_list[2].global_init_text
        ]))
        return result if result != "" else None

    @property
    def head_text(self) -> Optional[str]:
        temp_name_decl = LocalVariableName(self._src_info, self._temp_name, self._type_name).type_name_pair_calling
        return "\n".join(filter(lambda x: x is not None, [temp_name_decl, self._expr_list[0].head_text]))

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._expr_list[0] = self._expr_list[0].instantiation(type_args)
        new_expr._expr_list[1] = self._expr_list[1].instantiation(type_args)
        new_expr._expr_list[2] = self._expr_list[2].instantiation(type_args)
        new_expr._type_name = self._type_name.instantiation(type_args)
        return new_expr

    @property
    def is_const(self) -> bool:
        if isinstance(self._expr_list[0], Literal) and self._expr_list[0].value is not None:
            if self._expr_list[0].value:
                return self._expr_list[1].is_const
            return self._expr_list[2].is_const
        return False

    def optimize(self) -> "Expression":
        optimized = super().optimize()
        if isinstance(optimized._expr_list[0], Literal) and optimized._expr_list[0].value is not None:
            return optimized._expr_list[1] if optimized._expr_list[0].value else optimized._expr_list[2]
        return optimized

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._temp_name}->refCount == 0) {{",
            f"\tif ({self._temp_name}->parent) {{",
            f"\t\t{self._temp_name}->parent->refCount--;",
            "\t} else {",
            f"\t\tfree({self._temp_name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._type_name

    def set_expr_cond(self, expr: "Expression") -> None:
        """设置条件表达式（即 cond ? then : else 中的 cond）。

        Args:
            expr: 条件表达式（必须是基本类型/布尔类型）。
        """
        self._expr_list[0] = expr

    def set_expr_else(self, expr: "Expression") -> None:
        """设置 else 分支表达式，并自动推导返回类型。

        Args:
            expr: else 分支的表达式。
        """
        self._expr_list[2] = expr
        self._type_name = self._get_return_type()

    def set_expr_then(self, expr: "Expression") -> None:
        """设置 then 分支表达式，并自动推导返回类型。

        Args:
            expr: then 分支的表达式。
        """
        self._expr_list[1] = expr
        self._type_name = self._get_return_type()

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        result: list[Optional[str]] = list(filter(lambda x: x is not None, [self._expr_list[1].tail_recursive_mark,
                                                                            self._expr_list[2].tail_recursive_mark]))
        return result[0] if len(result) > 0 else None

    @property
    def text(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._temp_name

    @property
    def used_variables(self) -> set[VariableName]:
        return set.union(
            self._expr_list[0].used_variables,
            self._expr_list[1].used_variables,
            self._expr_list[2].used_variables,
            {LocalVariableName(self._src_info, self._temp_name, self._type_name)}
        )

    def validate(self) -> None:
        super().validate()
        if not isinstance(self._expr_list[0].return_type, BaseTypeName):
            raise CompilerException(
                f"Type {self._expr_list[0].return_type.raw_name} (expression: {self._expr_list[0].text}) "
                f"is not a base type.", self._src_info)
        if not self._expr_list[1].return_type.convertable_to(self._type_name, self._symbol_table.symbols):
            raise CompilerException(
                f"Type {self._expr_list[1].return_type.raw_name} (expression: {self._expr_list[1].text}) "
                f"can not convert to {self._type_name.raw_name}.", self._src_info)
        if not self._expr_list[2].return_type.convertable_to(self._type_name, self._symbol_table.symbols):
            raise CompilerException(
                f"Type {self._expr_list[2].return_type.raw_name} (expression: {self._expr_list[2].text}) "
                f"can not convert to {self._type_name.raw_name}.", self._src_info)

    def _get_return_type(self) -> Optional[TypeName]:
        """推导条件表达式的返回类型。

        基本类型之间取 base_type_degrade（降级到较大类型），
        类类型之间取 shared_parent（公共父类），
        混合类型无法推导则抛出异常。

        Returns:
            推导出的类型，如果任一分支还未设置则返回 None。
        """
        if self._expr_list[1] is None or self._expr_list[2] is None:
            return None
        if isinstance(self._expr_list[1].return_type, BaseTypeName) and \
                isinstance(self._expr_list[2].return_type, BaseTypeName):
            return base_type_degrade(self._expr_list[1].return_type, self._expr_list[2].return_type)
        if isinstance(self._expr_list[1].return_type, ClassName) and \
                isinstance(self._expr_list[2].return_type, ClassName):
            return self._expr_list[1].return_type.shared_parent(self._expr_list[2].return_type, self._symbol_table)
        raise CompilerException("The branches of conditional operator have not shared parent type.", self._src_info)


class UpdateExpr(Expression):
    """复制并更新表达式 `obj => { .prop = val, [idx] = val }`。

    不修改原有对象，而是先 malloc + memcpy 创建一个副本，
    再在副本上逐条应用指定的属性/元素修改，最终返回新对象。
    语法：`=>` 左侧为源对象，`{}` 内为一条或多条更新项。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        super().__init__(src_info, symbol_table)
        self._is_finished: bool = False
        self._src_expr: Optional[Expression] = None
        self._expr_list: list[tuple[Optional[Expression], Expression]] = []
        self._expr_loc: list[SourceInfo] = []
        self._temp_name: str = self._symbol_table.get_counter()
        self._is_async: bool = False
        self._inline_mapping: dict[str, str] = {}

    def add_item(self, index: list[Expression], value: Expression) -> None:
        """添加一项下标更新 `[idx] = value`。

        转换为 __setitem__ 方法调用。

        Args:
            index: 索引表达式列表。
            value: 新值表达式。

        Raises:
            CompilerException: 表达式已完成后调用，或源对象不是类类型。
        """
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not isinstance(self._src_expr.return_type, ClassName):
            raise CompilerException(
                f"Type {self._src_expr.return_type.raw_name} (expression: {self._src_expr.text}) "
                f"is not a class.", self._src_info)
        attr_expr = AttrOp(self._src_info, self._symbol_table)
        attr_expr.set_caller(self._src_expr)
        attr_expr.set_attr("__setitem__")
        call_op = CallOp(self._src_info, self._symbol_table)
        for i in index:
            call_op.add_arg(i, None)
        call_op.add_arg(value, None)
        if self._is_async:
            call_op = call_op.as_async()
        self._expr_list.append((None, call_op))
        self._expr_loc.append(value.src_info)

    def add_property(self, property_name: str, expr: Expression) -> None:
        """添加一项属性更新 `.prop = value`。

        Args:
            property_name: 属性名。
            expr: 新值表达式。

        Raises:
            CompilerException: 表达式已完成、源对象不是类类型、或属性不存在。
        """
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not isinstance(self._src_expr.return_type, ClassName):
            raise CompilerException(
                f"Type {self._src_expr.return_type.raw_name} (expression: {self._src_expr.text}) "
                f"is not a class.", self._src_expr.src_info)
        # noinspection PyUnresolvedReferences
        if property_name not in self._src_expr.return_type.properties:
            raise CompilerException(
                f"Property {property_name} is not defined in class {self._src_expr.return_type.raw_name}.",
                expr.src_info)
        attr_op = AttrOp(self._src_info, self._symbol_table)
        attr_op.set_caller(self._src_expr)
        attr_op.set_attr(property_name)
        self._expr_list.append((attr_op, expr))
        self._expr_loc.append(expr.src_info)

    def as_async(self) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._is_async = True
        return new_expr

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: UpdateExpr = super().as_inline(inline_mapping)
        for i, (expr1, expr2) in enumerate(self._expr_list):
            if expr1 is not None:
                expr1 = expr1.as_inline(new_expr._inline_mapping)
                new_expr._inline_mapping = expr1.inline_mapping
            expr2 = expr2.as_inline(new_expr._inline_mapping)
            new_expr._expr_list[i] = (expr1, expr2)
        new_expr._src_expr = self._src_expr.as_inline(inline_mapping)
        new_expr._inline_mapping = new_expr._src_expr.inline_mapping
        return new_expr

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    def finish(self) -> None:
        """标记更新项收集完毕，之后不能再添加新的更新项。"""
        self._is_finished = True

    @property
    def front_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        lines0: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[0].front_text, self._expr_list)))
        lines1: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].front_text, self._expr_list)))
        new_src_lines: list[str] = [
            f"{self._temp_name} = ({self._src_expr.return_type.c_calling_name})malloc(sizeof({self._src_expr.return_type}));",
            f"memcpy({self._temp_name}, {self._src_expr.text}, sizeof({self._src_expr.return_type}));"
        ]
        setting_lines: list[str] = [
            f"{self._temp_name}->{x[0].text} = {x[1].text};"
            if x[0] is not None else x[1].text + ";"
            for x in self._expr_list
        ]
        return "\n".join(lines0 + lines1 + new_src_lines + setting_lines)

    @property
    def global_init_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        lines0: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[0].global_init_text, self._expr_list)))
        lines1: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].global_init_text, self._expr_list)))
        return "\n".join(lines0 + lines1)

    @property
    def head_text(self) -> Optional[str]:
        results: list[str] = [
            f"{LocalVariableName(self._src_info, self._temp_name, self._src_expr.return_type).type_name_pair_calling};",
            *list(filter(lambda x: x is not None,
                         map(lambda x: x[0].head_text if x[0] is not None else None, self._expr_list))),
            *list(filter(lambda x: x is not None, map(lambda x: x[1].head_text, self._expr_list)))
        ]
        return "\n".join(results)

    @property
    def inline_mapping(self) -> dict[str, str]:
        return self._inline_mapping

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr: UpdateExpr = deepcopy(self)
        new_expr._src_expr = self._src_expr.instantiation(type_args)
        new_expr._expr_list = [
            (x[0].instantiation(type_args) if x[0] is not None else None, x[1].instantiation(type_args))
            for x in self._expr_list
        ]
        return new_expr

    @property
    def outer_text(self) -> Optional[str]:
        expr_list: list[Expression] = [self._src_expr] + list(
            filter(lambda x: x is not None, map(lambda x: x[0], self._expr_list))
        ) + list(
            map(lambda x: x[1], self._expr_list)
        )
        result_list: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.outer_text, expr_list)))
        result: str = "\n\n".join(result_list)
        return result if result != "" else None

    def optimize(self) -> "Expression":
        for i, (expr1, expr2) in enumerate(self._expr_list):
            if expr1 is not None:
                self._expr_list[i] = (expr1.optimize(), expr2.optimize())
            self._expr_list[i] = (expr1, expr2.optimize())
        return self

    @property
    def release_text(self) -> Optional[str]:
        result: list[str] = [
            f"if ({self._temp_name}->refCount == 0) {{",
            f"\tif ({self._temp_name}->parent) {{",
            f"\t\t{self._temp_name}->parent->refCount --;",
            "\t} else {",
            f"\t\tfree({self._temp_name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._src_expr.return_type

    def set_src_expr(self, src_expr: Expression) -> None:
        """设置被复制更新的源对象表达式（`=>` 左侧的 `obj`）。

        Args:
            src_expr: 源对象表达式（必须为对象类型）。

        Raises:
            CompilerException: 表达式已完成或源对象不是对象类型。
        """
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not src_expr.return_type.is_object:
            raise CompilerException(
                f"Type {src_expr.return_type.raw_name} (expression: {src_expr.text}) "
                f"is not an object.", self._src_info)
        self._src_expr = src_expr

    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        result = deepcopy(self)
        result._src_expr = self._src_expr.substitute(expr)
        result._expr_list = [
            (x[0].substitute(expr) if x[0] is not None else None, x[1].substitute(expr))
            for x in self._expr_list
        ]
        return result

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        if not self._is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._temp_name

    @property
    def used_variables(self) -> set[VariableName]:
        return set.union(
            *map(lambda x: x[0].used_variables, filter(lambda x: x[0] is not None, self._expr_list)),
            *map(lambda x: x[1].used_variables, self._expr_list),
            {LocalVariableName(self._src_info, self._temp_name, self._src_expr.return_type)}
        )

    def validate(self) -> None:
        if not self._is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        errors: list[str] = []
        try:
            self._src_expr.validate()
        except CompilerException as e:
            errors.append(str(e))
        for expr in self._expr_list:
            try:
                expr[1].validate()
            except CompilerException as e:
                errors.append(str(e))
            if expr[0] is not None:
                try:
                    expr[0].validate()
                except CompilerException as e:
                    errors.append(str(e))
        if len(errors) > 0:
            raise CompilerException("\n\n".join(errors), self._src_info)
