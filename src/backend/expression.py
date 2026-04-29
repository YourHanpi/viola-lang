# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .symbol import (
    TypeName,
    GenericArgument,
    VariableName,
    SymbolTable,
    ArrayTypeName,
    ClassName,
    TupleTypeName,
    TemporaryVariableName,
    BaseTypeName,
    FunctionTypeName,
    BOOL,
    INT32,
    DOUBLE,
    GlobalVariableName,
    FunctionName,
    MethodName,
    LISTENER_T,
    LISTENER_INIT_FUNC
)
from utils import CompilerException, InternalCompilerException, COMPILER_PARAMS, SourceInfo

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional

SYMBOL_TABLE: Optional[SymbolTable] = None

CONVERTIBLE_TO_FUNC = "viola$lang$convertibleTo"
FUNC_CALL_T: str = "viola$lang$thread$FuncCall"
FUNC_ENQUEUE_FUNC: str = "viola$lang$thread$enqueue"


class Expression(CompilingItem, ABC):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)

    @abstractmethod
    def as_async(self) -> "Expression":
        pass

    @abstractmethod
    def as_inline(self, inline_mapping: dict[str, str]) -> "Expression":
        pass

    @abstractmethod
    def check_tail_recursive(self, func_name: str) -> "Expression":
        pass

    @abstractmethod
    @property
    def front_text(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def global_init_text(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def head_text(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def inline_mapping(self) -> dict[str, str]:
        pass

    @abstractmethod
    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        pass

    @property
    def listener_name(self) -> Optional[str]:
        return None

    @abstractmethod
    @property
    def outer_text(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def release_text(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def return_type(self) -> TypeName:
        pass

    def set_returns(self, returns: list[VariableName]) -> None:
        pass

    @abstractmethod
    @property
    def tail_recursive_mark(self) -> Optional[str]:
        pass

    @abstractmethod
    @property
    def text(self) -> str:
        pass

    @abstractmethod
    @property
    def used_variables(self) -> set[VariableName]:
        pass

    @abstractmethod
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
            f"\t\tfree({self._var.name});",
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._to_unpack.return_type

    def set_returns(self, returns: list[VariableName]) -> None:
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

    def set_to_unpack(self, to_unpack: Expression) -> None:
        self._to_unpack = to_unpack

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None

    @property
    def text(self) -> str:
        if self._var is None:
            return self._to_unpack.text
        return self._var.name

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

    def set_returns(self, returns: list[VariableName]) -> None:
        self._returns = returns
        if len(returns) > 1:
            self._unpack_expr = UnpackExpr(self._src_info, self)
            self._unpack_expr.set_returns(returns)

    @property
    def tail_recursive_mark(self) -> Optional[str]:
        return None


class VariableRef(ValueRef):

    def __init__(self, src_info: SourceInfo, var: VariableName) -> None:
        super().__init__(src_info)
        self._var: VariableName = var

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

    @property
    def end_text(self) -> Optional[str]:
        return None

    @classmethod
    def from_function(cls, src_info: SourceInfo, name: str, arg_types: list[str], kwarg_types: dict[str, str]) -> "VariableRef":
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
            "\t}"
            "}"
        ]
        return "\n".join(result)

    @property
    def return_type(self) -> TypeName:
        return self._var.type

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
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        return self._type

    @property
    def text(self) -> str:
        return self._value

    @property
    def used_variables(self) -> set[VariableName]:
        return set()


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
        super().__init__(src_info, value, SYMBOL_TABLE["string", None])
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
            f"{self._var_name}->data[{i}] = memcpy({self._var_name}->data + {index}, (uint16_t[]){{ {', '.join(map(lambda x: str(x), chunk))} }}, {size};"
            for (i, chunk), index, size in zip(enumerate(chunks), chunk_indices, chunk_sizes)
        ]
        lines: list[str] = [
            f"{self._var_name} = ({self._type.c_calling_name})malloc(sizeof({self._type.c_alloc_name}));",
            f"{self._var_name}->data = malloc(sizeof(uint16_t) * {len(self._value) - 2});",
            f"{self._var_name}->size = {len(self._value) - 2};",
            "\n".join(chunks_copy_string)
        ]
        if len(self._value) == 2:
            lines[1] = f"{self._var_name}->data = NULL;"
        return "\n".join(lines)

    @property
    def head_text(self) -> Optional[str]:
        return f"{self._type.name} *{self._var_name};"

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
        unicode_data: list[int] = list(map(ord, self._value[1:-1]))
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


class IntegerLiteral(Literal):

    def __init__(self, src_info: SourceInfo, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, value, INT32)

    def validate(self) -> None:
        pass


class FloatLiteral(Literal):

    def __init__(self, src_info: SourceInfo, value: str) -> None:
        # noinspection PyTypeChecker
        super().__init__(src_info, value, DOUBLE)

    def validate(self) -> None:
        pass


class ArrayRef(ValueRef):

    def __init__(self, src_info: SourceInfo, element_type: TypeName) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._values_loc: list[str] = []
        self._type: TypeName = ArrayTypeName(src_info, element_type)
        self._temp_var: Optional[TemporaryVariableName] = None

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

    def append(self, value: Expression, loc: str) -> None:
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        self._values.append(value)
        self._values_loc.append(loc)

    def finish(self) -> None:
        if self._is_finished:
            raise InternalCompilerException("ArrayRef is already finished", self._src_info)
        var_name: str = SYMBOL_TABLE.get_counter()
        self._temp_var = TemporaryVariableName(self._src_info, var_name, self._type)
        self._is_finished = True

    @property
    def front_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("ArrayRef is not finished", self._src_info)
        lines: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.front_text, self._values)))
        self._type: ArrayTypeName
        # noinspection PyUnresolvedReferences
        lines.append(
            f"{self._temp_var.name}->data = malloc(sizeof({self._type.element_type.c_alloc_name}) * {len(self._values)});")
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

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info)
        self._is_finished: bool = False
        self._values: list[Expression] = []
        self._values_loc: list[SourceInfo] = []
        self._type: Optional[TypeName] = None
        self._temp_var: Optional[VariableName] = None

    def append(self, value: Expression, src_info: SourceInfo) -> None:
        if self._is_finished:
            raise InternalCompilerException("TupleRef is already finished", self._src_info)
        self._values.append(value)
        self._values_loc.append(src_info)

    def append_left(self, value: Expression, source_info: SourceInfo) -> None:
        self._values.insert(0, value)
        self._values_loc.insert(0, source_info)

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

    @property
    def release_text(self) -> Optional[str]:
        return None

    @property
    def return_type(self) -> TypeName:
        return self._type

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
    def is_finished(self) -> bool:
        return all(map(lambda x: x is not None, self._expr_list))

    @property
    def outer_text(self) -> Optional[str]:
        result = "\n\n".join(filter(lambda x: x is not None, map(lambda x: x.outer_text, self._expr_list)))
        return result if result != "" else None

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
        self._expected_type: Optional[FunctionTypeName] = None
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
        if self._expected_type is None:
            raise CompilerException("Unknown method types.", self._src_info)
        return SYMBOL_TABLE.find_method(
            caller_type.raw_name,
            self._attr,
            self._expected_type.arg_names
        )

    @property
    def attr(self) -> str:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._attr

    @property
    def caller(self) -> Expression:
        if not self.is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        return self._caller

    def check_tail_recursive(self, func_name: str) -> "Expression":
        return self

    def find_method(self, arg_type_list: list[str], kwarg_type_dict: dict[str, str]) -> FunctionName:
        method_name: str = self._caller.return_type.name + "$" + self._attr
        dynamic_arg_type_list: list[str] = [self._caller.return_type.name] + arg_type_list
        dynamic_methods: list[FunctionName] = SYMBOL_TABLE.find_functions(
            method_name, dynamic_arg_type_list, kwarg_type_dict
        )
        static_methods: list[FunctionName] = SYMBOL_TABLE.find_functions(
            method_name, arg_type_list, kwarg_type_dict
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
        new_expr._expected_type = self._expected_type.instantiation(type_args)
        return new_expr

    @property
    def is_finished(self) -> bool:
        return self._attr is not None and self._caller is not None

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

    def set_expected_type(self, expected_type: FunctionTypeName) -> None:
        self._expected_type = expected_type

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
            return f"{self._caller.text}->{self._attr}"
        if self._expected_type is None:
            raise CompilerException("Unknown method types.", self._src_info)
        return SYMBOL_TABLE.find_method(
            caller_type.raw_name,
            self._attr,
            self._expected_type.arg_names
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
        if self._expected_type is None:
            raise CompilerException("Unknown method types.", self._src_info)
        if self._attr not in caller_type.properties and not SYMBOL_TABLE.contains_method(
            caller_type.raw_name, self._attr, self._expected_type.arg_names
        ):
            raise CompilerException("Unknown attribute", self._src_info)


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
                                           "\n" + self._func_expr.front_text) if self._func_expr.front_text is not None else ""
        listener_text: list[str] = [
            f"{self._listener_name} = ({LISTENER_T} *)malloc(sizeof({LISTENER_T}));",
            f"{LISTENER_INIT_FUNC}({self._listener_name}, listener->executingThreadId);"
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
        if isinstance(expr, ClassRef):
            attr_op = AttrOp(self._src_info)
            attr_op.set_caller(expr)
            attr_op.set_attr("__new__")
            self._func = attr_op.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            )
            self._func_expr = attr_op
        elif isinstance(expr.return_type, ClassName):
            attr_op = AttrOp(self._src_info)
            attr_op.set_caller(expr)
            attr_op.set_attr("__call__")
            self._func = attr_op.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            )
            self._func_expr = attr_op
            self._call_dynamic = True
            self._arg_list = [expr] + self._arg_list
        elif isinstance(expr, VariableRef):
            new_expr: VariableRef = VariableRef.from_function(
                self._src_info, expr.var.name, list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            )
            # noinspection PyTypeChecker
            self._func = new_expr.var
            self._func_expr = new_expr
        elif isinstance(expr, AttrOp):
            self._func = expr.find_method(
                list(map(lambda x: x.return_type.name, self._arg_list)),
                dict(map(lambda x: (x[0], x[1].return_type.name), self._kwarg_dict.items()))
            )
            self._func_expr = expr
            # noinspection PyUnresolvedReferences
            self._call_dynamic = not self._func.is_static
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

    def set_returns(self, returns: Optional[list[VariableName]]) -> None:
        self._returns_list = returns
        self._returns_tuple = TupleRef(self._src_info)
        for ret in self._returns_list:
            self._returns_tuple.append(VariableRef(self._src_info, ret), self._src_info)
        if len(returns) > 1:
            self._unpack_expr = UnpackExpr(self._src_info, self)
            self._unpack_expr.set_returns(returns)

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
                 right_magic_method: Optional[str], default_return_type: Optional[TypeName]) -> None:
        super().__init__(src_info)
        self._op: Optional[str] = op
        self._left_magic_method: Optional[str] = left_magic_method
        self._right_magic_method: Optional[str] = right_magic_method
        self._default_return_type: Optional[TypeName] = default_return_type
        self._returns_list: list[VariableName] = []
        self._call_op: Optional[CallOp] = None

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
    def listener_name(self) -> Optional[str]:
        return self._call_op.listener_name if self._call_op is not None else None

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

    def set_returns(self, returns: list[VariableName]) -> None:
        self._returns_list = returns
        if self._call_op is not None:
            self._call_op.set_returns(returns)

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
        super().__init__(src_info, "+", "__add__", "__radd__", None)


class SubOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "-", "__sub__", "__rsub__", None)


class MulOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "*", "__mul__", "__rmul__", None)


class DivOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "/", "__div__", "__rdiv__", None)


class ModOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "%", "__mod__", "__rmod__", None)


class MatMulOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, None, "__matmul__", "__rmatmul__", None)


class PowOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, None, "__pow__", "__rpow__", None)


class LeftShiftOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<<", "__lshift__", "__rlshift__", None)


class RightShiftOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">>", "__rshift__", "__rrshift__", None)


class BitAndOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "&", "__and__", "__rand__", None)


class BitOrOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "|", "__or__", "__ror__", None)


class BitXorOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "^", "__xor__", "__rxor__", None)


class LogicalAndOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "&&", None, None, BOOL)


class LogicalOrOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "||", None, None, BOOL)


class GreaterThanOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">", "__gt__", "__lt__", BOOL)


class LessThanOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<", "__lt__", "__gt__", BOOL)


class GreaterThanOrEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, ">=", "__ge__", "__le__", BOOL)


class LessThanOrEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "<=", "__le__", "__ge__", BOOL)


class EqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "==", "__eq__", "__eq__", BOOL)


class NotEqualOp(BinaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "!=", "__ne__", "__ne__", BOOL)


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
        self._returns_list: list[tuple[str, TypeName]] = []

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

    def set_returns(self, returns: list[tuple[str, TypeName]]) -> None:
        self._returns_list = returns

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

    def __init__(self, src_info: SourceInfo, op: str, magic_method: Optional[str]) -> None:
        super().__init__(src_info)
        self._op: str = op
        self._magic_method: Optional[str] = magic_method
        self._returns_list: list[VariableName] = []
        self._call_op: Optional[CallOp] = None

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
    def listener_name(self) -> Optional[str]:
        return self._call_op.listener_name if self._call_op is not None else None

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

    def set_returns(self, returns: list[VariableName]) -> None:
        self._returns_list = returns
        if self._call_op is not None:
            self._call_op.set_returns(returns)

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
        super().__init__(src_info, "+", "__pos__")


class NegativeOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "-", "__neg__")


class BitNotOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "~", "__invert__")


class LogicalNotOp(UnaryMathOp):

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, "!", None)


def _indent(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    result = "\n".join(["\t" + line for line in text.split("\n")])
    return result if result != "" else None


class ConditionalOp(Operator):

    def __init__(self, src_info: SourceInfo, t: TypeName) -> None:
        super().__init__(src_info, 3)
        self._temp_name: str = SYMBOL_TABLE.get_counter()
        self._type_name: TypeName = t

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
            f"{self._type_name.c_calling_name}{self._temp_name};",
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
        return self._expr_list[0].head_text

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Expression":
        new_expr = deepcopy(self)
        new_expr._expr_list[0] = self._expr_list[0].instantiation(type_args)
        new_expr._expr_list[1] = self._expr_list[1].instantiation(type_args)
        new_expr._expr_list[2] = self._expr_list[2].instantiation(type_args)
        new_expr._type_name = self._type_name.instantiation(type_args)
        return new_expr

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

    @property
    def front_text(self) -> Optional[str]:
        if not self._is_finished:
            raise CompilerException("Operator is not finished", self._src_info)
        lines0: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[0].front_text, self._expr_list)))
        lines1: list[str] = list(filter(lambda x: x is not None, map(lambda x: x[1].front_text, self._expr_list)))
        new_src_lines: list[str] = [
            f"{self._src_expr.return_type.c_calling_name}{self._temp_name} = ({self._src_expr.return_type.c_calling_name})malloc(sizeof({self._src_expr.return_type}));",
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
            f"{self._src_expr.return_type.c_calling_name}{self._temp_name};",
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
            filter(lambda x: x is not None, map(lambda x: x[0], self._expr_list))) + list(
            map(lambda x: x[1], self._expr_list))
        result_list: list[str] = list(filter(lambda x: x is not None, map(lambda x: x.outer_text, expr_list)))
        result: str = "\n\n".join(result_list)
        return result if result != "" else None

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

    def set_item(self, index: list[Expression], value: Expression, src_info: SourceInfo) -> None:
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
        self._expr_loc.append(src_info)

    def set_property(self, property_name: str, expr: Expression, src_info: SourceInfo) -> None:
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not isinstance(self._src_expr.return_type, ClassName):
            raise CompilerException(
                f"Type {self._src_expr.return_type.raw_name} (expression: {self._src_expr.text}) "
                f"is not a class.", src_info)
        # noinspection PyUnresolvedReferences
        if property_name not in self._src_expr.return_type.properties:
            raise CompilerException(
                f"Property {property_name} is not defined in class {self._src_expr.return_type.raw_name}.",
                src_info)
        attr_op = AttrOp(self._src_info)
        attr_op.set_caller(self._src_expr)
        attr_op.set_attr(property_name)
        self._expr_list.append((attr_op, expr))
        self._expr_loc.append(src_info)

    def set_src_expr(self, src_expr: Expression) -> None:
        if self._is_finished:
            raise CompilerException("Operator is finished", self._src_info)
        if not src_expr.return_type.is_object:
            raise CompilerException(
                f"Type {src_expr.return_type.raw_name} (expression: {src_expr.text}) "
                f"is not an object.", self._src_info)
        self._src_expr = src_expr

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
