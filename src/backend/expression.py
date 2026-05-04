# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .symbol import (
    TypeName, GenericArgument, VariableName, SymbolTable, ArrayTypeName, ClassName, TupleTypeName,
    TemporaryVariableName, BaseTypeName, FunctionTypeName, BOOL, INT8, INT16, UINT8, UINT16, INT32, UINT32, INT64,
    UINT64, FLOAT, DOUBLE, GlobalVariableName, FunctionName, MethodName, LISTENER_T, LISTENER_INIT_FUNC,
    EmptyArrayTypeName, base_type_degrade, SliceTypeName, INT_TYPES, StringTypeName, AnyTypeName, AutoTypeName
)
from utils import CompilerException, InternalCompilerException, COMPILER_PARAMS, SourceInfo

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional, Callable

SYMBOL_TABLE: SymbolTable = SymbolTable()

CONVERTIBLE_TO_FUNC = "viola$lang$convertibleTo"
FUNC_CALL_T: str = "viola$lang$thread$FuncCall"
FUNC_ENQUEUE_FUNC: str = "viola$lang$thread$enqueue"


class Expression(CompilingItem, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._returns: list[VariableName] = []

    @abstractmethod
    def as_async(self) -> "Expression":
        pass

    @abstractmethod
    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        pass

    @abstractmethod
    def check_tail_recursive(self, func_name: str) -> "Expression":
        pass

    @property
    @abstractmethod
    def front_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def global_init_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def head_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def inline_mapping(self) -> dict[str, str]:
        pass

    @abstractmethod
    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        pass

    @property
    def is_const(self) -> bool:
        return False

    @property
    def listener_name(self) -> Optional[str]:
        return None

    @abstractmethod
    def optimize(self) -> "Expression":
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def release_text(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def return_type(self) -> TypeName:
        pass

    def set_returns(self, returns: list[VariableName]) -> bool:
        return False

    @abstractmethod
    def substitute(self, expr: dict[VariableName, "Expression"]) -> "Expression":
        pass

    @property
    @abstractmethod
    def tail_recursive_mark(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def text(self) -> str:
        pass

    @property
    @abstractmethod
    def used_variables(self) -> set[VariableName]:
        pass

    @abstractmethod
    def validate(self) -> None:
        pass


class CExpr(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._text: list[str] = []
        self._inline_mapping: dict[str, str] = {}
        self._var: Optional[TemporaryVariableName] = None

    def add_text(self, text: str) -> None:
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

    def __init__(self, src_info: SourceInfo, to_unpack: Optional[Expression] = None) -> None:
        super().__init__(src_info)
        if to_unpack is not None and not isinstance(to_unpack.return_type, TupleTypeName):
            raise CompilerException("Cannot unpack non-tuple.", src_info)
        self._to_unpack: Optional[Expression] = to_unpack
        self._var: Optional[TemporaryVariableName] = None
        self._returns: list[VariableName] = []
        self._inline_mapping: dict[str, str] = {}

    def as_async(self) -> "Expression":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._to_unpack = self._to_unpack.as_inline(inline_mapping)
        new_expr._inline_mapping = new_expr._to_unpack.inline_mapping
        for i, ret in enumerate(self._returns):
            new_expr._inline_mapping[ret.name] = SYMBOL_TABLE.get_counter()
            new_expr._returns[i].rename(new_expr._inline_mapping[ret.name])
        new_expr._inline_mapping[new_expr._var.name] = SYMBOL_TABLE.get_counter()
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
            f"\t\t{self._var.name}->parent->refCount --;",
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

    def set_returns(self, returns: list[VariableName]) -> bool:
        # noinspection PyTypeChecker
        expr_type: TupleTypeName = self._to_unpack.return_type
        if len(returns) > len(expr_type.types):
            raise CompilerException(
                f"Too many returns: {len(returns)} > {len(expr_type.types)}.",
                self._src_info
            )
        for ret, expected_type in zip(returns[:-1], expr_type.types[:len(returns) - 1]):
            if not ret.type.convertable_to(expected_type, SYMBOL_TABLE.symbols):
                raise CompilerException(
                    f"Type mismatch: {ret.type.raw_name} can not convert to {expected_type.raw_name}.",
                    self._src_info
                )
        last_expected_type: TupleTypeName = TupleTypeName(self._src_info, expr_type.types[-1:])
        if not returns[-1].type.convertable_to(last_expected_type, SYMBOL_TABLE.symbols):
            raise CompilerException(
                f"Type mismatch: {returns[-1].type.raw_name} can not convert to {last_expected_type.raw_name}.",
                self._src_info
            )
        self._returns = returns
        self._var = TemporaryVariableName(
            self._src_info,
            SYMBOL_TABLE.get_counter(),
            self._to_unpack.return_type
        )
        return True

    def set_to_unpack(self, to_unpack: Expression) -> None:
        self._to_unpack = to_unpack

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
        return self._to_unpack

    @property
    def used_variables(self) -> set[VariableName]:
        return self._to_unpack.used_variables

    def validate(self) -> None:
        self._to_unpack.validate()


class ValueRef(Expression, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
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
            self._unpack_expr = UnpackExpr(self._src_info, self)
            self._unpack_expr.set_returns(returns)
        return True

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None


class VariableRef(ValueRef):

    def __init__(self, src_info: SourceInfo, var: VariableName) -> None:
        super().__init__(src_info)
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
                inline_mapping[self._var.name] = SYMBOL_TABLE.get_counter()
        new_expr._var.rename(inline_mapping[self._var.name])
        return new_expr

    def bind_value(self, value: Expression) -> None:
        self._value = value

    @classmethod
    def from_function(cls, src_info: SourceInfo, name: str, arg_types: list[str],
                      kwarg_types: dict[str, str]) -> "VariableRef":
        func = SYMBOL_TABLE.find_functions(name, arg_types, kwarg_types)
        if len(func) == 0:
            raise CompilerException(f"Function {name} not found.", src_info)
        if len(func) > 1:
            raise CompilerException(f"Function {name} overloads with same arguments.", src_info)
        return cls(src_info, func[0])

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
        return self._var


class Literal(ValueRef, ABC):

    def __init__(self, src_info: SourceInfo, value: str, t: TypeName) -> None:
        super().__init__(src_info)
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
        return None


class StringLiteral(Literal):
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

    def __init__(self, src_info: SourceInfo, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, value, StringTypeName)
        self._var_name: str = SYMBOL_TABLE.get_counter()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: StringLiteral = super().as_inline(inline_mapping)
        inline_mapping[self._var_name] = SYMBOL_TABLE.get_counter()
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
        return f"{TemporaryVariableName(self._src_info, self._var_name, self._type).type_name_pair_calling};"

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
        return {TemporaryVariableName(self._src_info, self._var_name, self._type)}

    def _as_unicode(self) -> list[list[int]]:
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

    def __init__(self, src_info: SourceInfo, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, value, BOOL)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> bool:
        return self._value == "true"


class IntegerLiteral(Literal):

    def __init__(self, src_info: SourceInfo, value: str, lexing_type: str = "INT32") -> None:
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
        super().__init__(src_info, value, t)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> int:
        return int(self._value)


class FloatLiteral(Literal):

    def __init__(self, src_info: SourceInfo, value: str) -> None:
        if value.endswith("f"):
            t = FLOAT
        else:
            t = DOUBLE
        # noinspection PyTypeChecker
        super().__init__(src_info, value, t)

    def validate(self) -> None:
        pass

    @property
    def value(self) -> float:
        return float(self._value)


class SliceRef(ValueRef):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._start: Expression = IntegerLiteral(src_info, "0")
        self._end: Expression = IntegerLiteral(src_info, "0")
        self._step: Expression = IntegerLiteral(src_info, "1")
        self._temp_var: TemporaryVariableName = TemporaryVariableName(src_info, SYMBOL_TABLE.get_counter(),
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
        self._end = end

    def set_start(self, start: Expression) -> None:
        self._start = start

    def set_step(self, step: Expression) -> None:
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

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._type: Optional[ArrayTypeName] = None
        self._element_type: Optional[TypeName] = None
        self._temp_var: Optional[TemporaryVariableName] = None

    def add_value(self, value: Expression) -> None:
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        self._values.append(value)
        if self._element_type is None:
            self._element_type = value.return_type
        elif isinstance(self._element_type, ClassName):
            if not isinstance(value.return_type, ClassName):
                raise InternalCompilerException("ArrayRef element type mismatch", self._src_info)
            if self._element_type != value.return_type:
                self._element_type = self._element_type.shared_parent(value.return_type, SYMBOL_TABLE)
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
        new_expr._inline_mapping[self._temp_var.name] = SYMBOL_TABLE.get_counter()
        new_expr._temp_var.rename(new_expr._inline_mapping[self._temp_var.name])
        return new_expr

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        if self._element_type is None:
            self._type = EmptyArrayTypeName(self._src_info)
        else:
            self._type = ArrayTypeName(self._src_info, self._element_type)
        var_name: str = SYMBOL_TABLE.get_counter()
        self._temp_var = TemporaryVariableName(self._src_info, var_name, self._type)
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

    def __getitem__(self, item: slice | int) -> Expression:
        if isinstance(item, int):
            return self._values[item]
        result = TupleRef(self._src_info)
        for v in self._values[item]:
            result.add_value(v)
        result.finish()
        return result

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._type: Optional[TypeName] = None
        self._temp_var: Optional[VariableName] = None

    def __len__(self) -> int:
        return len(self._values)

    def add_value(self, value: Expression) -> None:
        if self._is_finished:
            raise InternalCompilerException("TupleRef is already finished", self._src_info)
        self._values.append(value)

    def append_left(self, value: Expression) -> None:
        self._values.insert(0, value)

    def as_async(self) -> "ValueRef":
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: TupleRef = super().as_inline(inline_mapping)
        for i, value in enumerate(self._values):
            new_expr._values[i] = value.as_inline(new_expr._inline_mapping)
            new_expr._inline_mapping.update(new_expr._values[i].inline_mapping)
        new_expr._inline_mapping[self._temp_var.name] = SYMBOL_TABLE.get_counter()
        new_expr._temp_var.rename(new_expr._inline_mapping[self._temp_var.name])
        return new_expr

    @property
    def expressions(self) -> list[Expression]:
        return self._values

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException("TupleRef is already finished", self._src_info)
        self._is_finished = True
        self._type = TupleTypeName(self._src_info, list(map(lambda x: x.return_type, self._values)))
        var_name: str = SYMBOL_TABLE.get_counter()
        self._temp_var = TemporaryVariableName(self._src_info, var_name, self._type)

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


class TypeRef(ValueRef):

    def __init__(self, src_info: SourceInfo, type_symbol: TypeName) -> None:
        super().__init__(src_info)
        self._type: TypeName = type_symbol

    def as_async(self) -> "Expression":
        return self

    @classmethod
    def from_name(cls, src_info: SourceInfo, type_name: str) -> "TypeRef":
        # noinspection PyTypeChecker
        t: TypeName = SYMBOL_TABLE[type_name, None]
        if not isinstance(t, TypeName):
            raise CompilerException("TypeRef is not a type", src_info)
        return cls(src_info, t)

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

    def __init__(self, src_info: SourceInfo, cls_name: str) -> None:
        # noinspection PyTypeChecker
        t: ClassName = SYMBOL_TABLE[cls_name, None]
        if not isinstance(t, ClassName):
            raise CompilerException("ClassRef is not a class type", src_info)
        super().__init__(src_info, t)


class ArrayTypeRef(TypeRef):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, EmptyArrayTypeName(src_info))

    def set_type(self, type_ref: TypeRef) -> None:
        self._type = ArrayTypeName(self._src_info, type_ref.return_type)


class TupleTypeRef(TypeRef):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, TupleTypeName(src_info, []))
        self._types: list[TypeName] = []

    def add_type(self, type_ref: TypeRef) -> None:
        self._types.append(type_ref.return_type)

    def finish(self) -> None:
        self._type = TupleTypeName(self._src_info, self._types)


# TODO: 增加字典和集合的实现（推迟一个小版本）


class AutoTypeRef(TypeRef):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, AutoTypeName(src_info))


class Operator(Expression, ABC):

    def __init__(self, src_info: SourceInfo, expr_num: int) -> None:
        super().__init__(src_info)
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
        if self._expr_list[index] is not None:
            raise InternalCompilerException("Expression is already set", self._src_info)
        self._expr_list[index] = expr


class BinaryOperator(Operator, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, 2)

    @property
    def front_text(self) -> Optional[str]:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        ret: str = self._expr_list[0].front_text if self._expr_list[0].front_text is not None else ""
        ret += self._expr_list[1].front_text if self._expr_list[1].front_text is not None else ""
        return ret if ret != "" else None

    def set_expr_left(self, expr: Expression) -> None:
        self._set_expr(0, expr)

    def set_expr_right(self, expr: Expression) -> None:
        self._set_expr(1, expr)


class AttrOp(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
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
        # noinspection PyTypeChecker
        caller_type: ClassName = self._caller.return_type
        if self._arg_types is None:
            raise CompilerException("Unknown method types.", self._src_info)
        return SYMBOL_TABLE.find_method(
            self._src_info,
            caller_type.name,
            self._attr,
            self._arg_types,
            self._kwarg_types
        )

    @property
    def attr(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._attr

    def bind_parent(self, parent_item: "CompilingItem") -> None:
        super().bind_parent(parent_item)
        self._set_expected_type()

    @property
    def caller(self) -> Expression:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    def find_method(self, arg_type_list: list[str], kwarg_type_dict: dict[str, str]) -> MethodName:
        dynamic_arg_type_list: list[str] = [self._caller.return_type.name] + arg_type_list
        dynamic_methods: list[MethodName] = SYMBOL_TABLE.find_methods(
            self._caller.return_type.name, self._attr, dynamic_arg_type_list, kwarg_type_dict
        )
        static_methods: list[MethodName] = SYMBOL_TABLE.find_methods(
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
        self._attr = "$" + attr

    def set_caller(self, caller: Expression) -> None:
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
        return SYMBOL_TABLE.find_method(
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
        if self._attr not in caller_type.properties and not SYMBOL_TABLE.contains_method(
                caller_type.raw_name, self._attr, self._arg_types, self._kwarg_types
        ):
            raise CompilerException("Unknown attribute", self._src_info)

    def _set_expected_type(self) -> None:
        if isinstance(self._parent_item, CallOp):
            self._arg_types = list(map(lambda x: x.name, self._parent_item.arg_types))
            self._kwarg_types = dict(map(lambda x: (x[0], x[1].name), self._parent_item.kwarg_types.items()))


class CallOp(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
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
        return [arg.return_type for arg in self._arg_list]

    def as_async(self) -> "Expression":
        result: CallOp = deepcopy(self)
        result._is_async = True
        result._listener_name = SYMBOL_TABLE.get_counter()
        result._call_name = result._listener_name + "$$_call"
        result._args_tuple = TupleRef(self._src_info)
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
        if isinstance(expr, VariableRef) and (expr.var.name, None) in SYMBOL_TABLE:
            expr = ClassRef(self._src_info, expr.var.name)
            attr_op = AttrOp(self._src_info)
            attr_op.set_caller(expr)
            attr_op.set_attr("__new__")
            self._func = attr_op.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            ).as_function()
            self._func_expr = attr_op
        elif isinstance(expr.return_type, ClassName):
            attr_op = AttrOp(self._src_info)
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
                    self._arg_list.append(VariableRef(self._src_info, default_value))

    def set_returns(self, returns: Optional[list[VariableName]]) -> bool:
        self._returns_list = returns
        self._returns_tuple = TupleRef(self._src_info)
        for ret in self._returns_list:
            self._returns_tuple.add_value(VariableRef(self._src_info, ret))
        if len(returns) > 1:
            self._unpack_expr = UnpackExpr(self._src_info, self)
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
        if self._is_async:
            result = "$async"
        else:
            result = "$sync"
        if self._call_struct:
            result = "->" + result
        return result


class TailRecursiveCall(CallOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._mark_name: Optional[str] = None
        self._decl: Optional[FunctionName] = None

    @classmethod
    def from_call_op(cls, call_op: CallOp) -> "TailRecursiveCall":
        result = cls(call_op._src_info)
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
            del_var: VariableRef = VariableRef(self._src_info, arg_expr)
            del_call: CallOp = CallOp(self._src_info)
            del_method: AttrOp = AttrOp(self._src_info)
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

    def __init__(self, src_info: SourceInfo, op: Optional[str], left_magic_method: Optional[str],
                 right_magic_method: Optional[str], default_return_type: Optional[TypeName],
                 optimizer: Optional[Callable[[int | float, int | float], int | float]] = None) -> None:
        super().__init__(src_info)
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
                return IntegerLiteral(self._src_info, str(new_value))
            return FloatLiteral(self._src_info, str(new_value))
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
        expr_left: Expression = self._expr_list[0]
        expr_right: Expression = self._expr_list[1]
        if expr_left.return_type not in SYMBOL_TABLE:
            raise CompilerException(f"Type {expr_left.return_type} is not defined", self._src_info)
        if expr_right.return_type not in SYMBOL_TABLE:
            raise CompilerException(f"Type {expr_right.return_type} is not defined", self._src_info)
        if isinstance(expr_left.return_type, BaseTypeName) and isinstance(expr_right.return_type, BaseTypeName):
            if self._op is None:
                raise CompilerException("This operator is not defined for two base types.", self._src_info)
            return
        if self._left_magic_method is None and self._right_magic_method is None:
            raise CompilerException("This operator is not defined for two class types.", self._src_info)
        # noinspection PyUnresolvedReferences
        if isinstance(expr_left.return_type, ClassName) and self._left_magic_method in expr_left.return_type.methods:
            self._call_op = CallOp(self._src_info)
            self._call_op.add_arg(expr_left, None)
            self._call_op.add_arg(expr_right, None)
            self._call_op.set_func(self._expr_list[0])
            self._call_op.set_returns(self._returns_list)
            return
        # noinspection PyUnresolvedReferences
        if isinstance(expr_right.return_type, ClassName) and self._right_magic_method in expr_right.return_type.methods:
            self._call_op = CallOp(self._src_info)
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

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "+", "__add__", "__radd__", None, lambda x, y: x + y)


class SubOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "-", "__sub__", "__rsub__", None, lambda x, y: x - y)


class MulOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "*", "__mul__", "__rmul__", None, lambda x, y: x * y)


class DivOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "/", "__div__", "__rdiv__", None, lambda x, y: x // y)


class ModOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "%", "__mod__", "__rmod__", None, lambda x, y: x % y)


class MatMulOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, None, "__matmul__", "__rmatmul__", None)


class PowOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, None, "__pow__", "__rpow__", None, lambda x, y: x ** y)

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

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<<", "__lshift__", "__rlshift__", None, lambda x, y: x << y)


class RightShiftOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">>", "__rshift__", "__rrshift__", None, lambda x, y: x >> y)


class BitAndOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "&", "__and__", "__rand__", None, lambda x, y: x & y)


class BitOrOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "|", "__or__", "__ror__", None, lambda x, y: x | y)


class BitXorOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "^", "__xor__", "__rxor__", None, lambda x, y: x ^ y)


class LogicalAndOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "&&", None, None, BOOL, lambda x, y: x and y)


class LogicalOrOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "||", None, None, BOOL, lambda x, y: x or y)


class GreaterThanOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">", "__gt__", "__lt__", BOOL, lambda x, y: x > y)


class LessThanOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<", "__lt__", "__gt__", BOOL, lambda x, y: x < y)


class GreaterThanOrEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">=", "__ge__", "__le__", BOOL, lambda x, y: x >= y)


class LessThanOrEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<=", "__le__", "__ge__", BOOL, lambda x, y: x <= y)


class EqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "==", "__eq__", "__eq__", BOOL, lambda x, y: x == y)


class NotEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "!=", "__ne__", "__ne__", BOOL, lambda x, y: x != y)


class ItemOp(CallOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)

    def set_expr_left(self, expr: Expression) -> None:
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
        new_expr: AttrOp = AttrOp(self._src_info)
        new_expr.set_caller(expr)
        new_expr.set_attr("__getitem__")
        super().set_func(new_expr)


class UnaryOperator(Operator, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, 1)

    def set_expr(self, expr: Expression) -> None:
        self._set_expr(0, expr)


class BracketsOp(UnaryOperator):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        new_op: BracketsOp = BracketsOp(self._src_info)
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

    def __init__(self, src_info: SourceInfo, op: str, magic_method: Optional[str],
                 optimizer: Optional[Callable[[int | float], int | float]] = None) -> None:
        super().__init__(src_info)
        self._op: str = op
        self._magic_method: Optional[str] = magic_method
        self._returns_list: list[VariableName] = []
        self._call_op: Optional[CallOp] = None
        self._optimizer: Optional[Callable[[int | float], int | float]] = optimizer

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        expr: Expression = self._expr_list[0]
        if expr.return_type not in SYMBOL_TABLE:
            raise CompilerException(f"Type {expr.return_type} is not defined", self._src_info)
        if isinstance(expr.return_type, ClassName):
            if self._magic_method is None:
                raise CompilerException(
                    f"This operator can only be used with basic types, but {expr.return_type.raw_name} is given.",
                    self._src_info
                )
            # noinspection PyUnresolvedReferences
            if self._magic_method in expr.return_type.methods:
                result = CallOp(self._src_info)
                caller_op: AttrOp = AttrOp(self._src_info)
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
        if isinstance(optimized._expr_list[0],
                      Literal) and optimized._expr_list is not None and self._optimizer is not None:
            return Literal(self._src_info, self._optimizer(optimized._expr_list[0].value))
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
        if isinstance(self._expr_list[0].return_type, BaseTypeName):
            return
        # noinspection PyUnresolvedReferences
        if (isinstance(self._expr_list[0].return_type, ClassName)
                and self._magic_method in self._expr_list[0].return_type.methods):
            self._call_op = CallOp(self._src_info)
            caller_op: AttrOp = AttrOp(self._src_info)
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

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "+", "__pos__", lambda x: x)


class NegativeOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "-", "__neg__", lambda x: -x)


class BitNotOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "~", "__invert__", lambda x: ~x)


class LogicalNotOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "!", None, lambda x: not x)


def _indent(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = "\n".join(["\t" + line for line in text.split("\n")])
    return result if result != "" else None


class ConditionalOp(Operator):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, 3)
        self._temp_name: str = SYMBOL_TABLE.get_counter()
        self._type_name: Optional[TypeName] = None

    def as_async(self) -> "Expression":
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self

    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        # noinspection PyTypeChecker
        new_expr: ConditionalOp = super().as_inline(inline_mapping)
        new_expr._inline_mapping[self._temp_name] = SYMBOL_TABLE.get_counter()
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
        temp_name_decl = TemporaryVariableName(self._src_info, self._temp_name, self._type_name).type_name_pair_calling
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
        self._expr_list[0] = expr

    def set_expr_else(self, expr: "Expression") -> None:
        self._expr_list[2] = expr
        self._type_name = self._get_return_type()

    def set_expr_then(self, expr: "Expression") -> None:
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
            {TemporaryVariableName(self._src_info, self._temp_name, self._type_name)}
        )

    def validate(self) -> None:
        super().validate()
        if not isinstance(self._expr_list[0].return_type, BaseTypeName):
            raise CompilerException(
                f"Type {self._expr_list[0].return_type.raw_name} (expression: {self._expr_list[0].text}) "
                f"is not a base type.", self._src_info)
        if not self._expr_list[1].return_type.convertable_to(self._type_name, SYMBOL_TABLE.symbols):
            raise CompilerException(
                f"Type {self._expr_list[1].return_type.raw_name} (expression: {self._expr_list[1].text}) "
                f"can not convert to {self._type_name.raw_name}.", self._src_info)
        if not self._expr_list[2].return_type.convertable_to(self._type_name, SYMBOL_TABLE.symbols):
            raise CompilerException(
                f"Type {self._expr_list[2].return_type.raw_name} (expression: {self._expr_list[2].text}) "
                f"can not convert to {self._type_name.raw_name}.", self._src_info)

    def _get_return_type(self) -> Optional[TypeName]:
        if self._expr_list[1] is None or self._expr_list[2] is None:
            return None
        if isinstance(self._expr_list[1].return_type, BaseTypeName) and \
                isinstance(self._expr_list[2].return_type, BaseTypeName):
            return base_type_degrade(self._expr_list[1].return_type, self._expr_list[2].return_type)
        if isinstance(self._expr_list[1].return_type, ClassName) and \
                isinstance(self._expr_list[2].return_type, ClassName):
            return self._expr_list[1].return_type.shared_parent(self._expr_list[2].return_type, SYMBOL_TABLE)
        raise CompilerException("The branches of conditinal operator have not shared parent type.", self._src_info)


class UpdateExpr(Expression):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._src_expr: Optional[Expression] = None
        self._expr_list: list[tuple[Optional[Expression], Expression]] = []
        self._expr_loc: list[SourceInfo] = []
        self._temp_name: str = SYMBOL_TABLE.get_counter()
        self._is_async: bool = False
        self._inline_mapping: dict[str, str] = {}

    def add_item(self, index: list[Expression], value: Expression) -> None:
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not isinstance(self._src_expr.return_type, ClassName):
            raise CompilerException(
                f"Type {self._src_expr.return_type.raw_name} (expression: {self._src_expr.text}) "
                f"is not a class.", self._src_info)
        attr_expr = AttrOp(self._src_info)
        attr_expr.set_caller(self._src_expr)
        attr_expr.set_attr("__setitem__")
        call_op = CallOp(self._src_info)
        for i in index:
            call_op.add_arg(i, None)
        call_op.add_arg(value, None)
        if self._is_async:
            call_op = call_op.as_async()
        self._expr_list.append((None, call_op))
        self._expr_loc.append(value.src_info)

    def add_property(self, property_name: str, expr: Expression) -> None:
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
        attr_op = AttrOp(self._src_info)
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
            f"{TemporaryVariableName(self._src_info, self._temp_name, self._src_expr.return_type).type_name_pair_calling};",
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
            {TemporaryVariableName(self._src_info, self._temp_name, self._src_expr.return_type)}
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
