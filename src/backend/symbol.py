# -*- coding: utf-8 -*-
from utils import CompilerException, InternalCompilerException, SourceInfo

from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum
import os
from typing import Optional

CLOSURE_T: str = "viola$lang$function$Closure"
LISTENER_T: str = "viola$lang$thread$Listener"
LISTENER_INIT_FUNC: str = "viola$lang$thread$initListener"
EXCEPTION_T: str = "viola$lang$exception$Exception"
EXCEPTION_T_NAME: str = "viola.lang.exception.Exception"
TUPLE_T: str = "viola$collections$Tuple"


class SymbolType(Enum):
    VARIABLE = 1
    FUNCTION = 2
    SEQUENCE = 3
    BASE_TYPE = 4
    CLASS = 5
    ENUM = 6
    NAMESPACE = 7
    GENERIC = 8
    GENERIC_ARG = 9


class Symbol(ABC):

    def __eq__(self, other: "Symbol") -> bool:
        return self._name == other._name

    def __hash__(self) -> int:
        return hash(self._name)

    def __init__(self, name: str, kw_type: SymbolType) -> None:
        self._name: str = name
        self._kw_type: SymbolType = kw_type

    @property
    def kw_type(self) -> SymbolType:
        return self._kw_type

    @property
    def name(self) -> str:
        return self._name

    def rename(self, name: str) -> None:
        self._name = name


class Identifier(Symbol):

    def __init__(self, name: str, kw_type: SymbolType) -> None:
        super().__init__(name, kw_type)


class NamespaceName(Identifier):

    def __init__(self, name: str) -> None:
        super().__init__(name, SymbolType.NAMESPACE)


VIOLA_LANG: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("lang")]
VIOLA_COLLECTIONS: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("collections")]
GENERIC_CLASS: list[NamespaceName] = [NamespaceName("__generic"), NamespaceName("class")]
GENERIC_FUNC: list[NamespaceName] = [NamespaceName("__generic"), NamespaceName("function")]


class NamedSymbol(Symbol):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, kw_type: SymbolType) -> None:
        super().__init__("$".join(list(map(lambda n: n.name, namespace))) + "$" + name, kw_type)
        self._namespace: list[NamespaceName] = namespace
        self._self_name: str = name
        self._src_info: SourceInfo = deepcopy(src_info)

    def as_namespace(self) -> list[NamespaceName]:
        return self._namespace + [NamespaceName(self._self_name)]

    @property
    def loc_info(self) -> SourceInfo:
        return self._src_info

    @property
    def namespace(self) -> list[NamespaceName]:
        return self._namespace

    @property
    def src_info(self) -> SourceInfo:
        return self._src_info


class TypeName(NamedSymbol, ABC):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, kw_type: SymbolType) -> None:
        super().__init__(src_info, namespace, name, kw_type)
        self._raw_name: str = ".".join(map(lambda n: n.name, self._namespace)) + "." + name

    @abstractmethod
    @property
    def c_alloc_name(self) -> str:
        pass

    @abstractmethod
    @property
    def c_assigning_name(self) -> str:
        pass

    @abstractmethod
    @property
    def c_calling_name(self) -> str:
        pass

    @abstractmethod
    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, tuple["TypeName", ...]], NamedSymbol]) -> bool:
        pass

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return self

    @abstractmethod
    @property
    def is_generic(self) -> bool:
        pass

    @property
    def is_object(self) -> bool:
        return False

    @property
    def raw_name(self) -> str:
        return self._raw_name

    @abstractmethod
    @property
    def short_name(self) -> str:
        pass


class BaseTypeName(TypeName):

    def __init__(self, name: str, short_name: str) -> None:
        super().__init__(SourceInfo(""), VIOLA_LANG, name, SymbolType.BASE_TYPE)
        self._short_name: str = short_name

    @property
    def c_alloc_name(self) -> str:
        raise CompilerException("Can't allocate base type.", self._src_info)

    @property
    def c_assigning_name(self) -> str:
        return f"{self.name} *"

    @property
    def c_calling_name(self) -> str:
        return f"{self.name} "

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        return isinstance(target, BaseTypeName)

    @property
    def is_generic(self) -> bool:
        return False

    @property
    def short_name(self) -> str:
        return self._short_name


BOOL: BaseTypeName = BaseTypeName("bool", "b")

INT: BaseTypeName = BaseTypeName("int", "i")
INT8: BaseTypeName = BaseTypeName("int8", "i8")
INT16: BaseTypeName = BaseTypeName("int16", "i16")
INT32: BaseTypeName = BaseTypeName("int32", "i32")
INT64: BaseTypeName = BaseTypeName("int64", "i64")

UINT: BaseTypeName = BaseTypeName("uint", "u")
UINT8: BaseTypeName = BaseTypeName("uint8", "u8")
UINT16: BaseTypeName = BaseTypeName("uint16", "u16")
UINT32: BaseTypeName = BaseTypeName("uint32", "u32")
UINT64: BaseTypeName = BaseTypeName("uint64", "u64")
SIZE_T: BaseTypeName = BaseTypeName("size_t", "sz")

FLOAT: BaseTypeName = BaseTypeName("float", "f")
FLOAT32: BaseTypeName = BaseTypeName("float32", "f32")
FLOAT64: BaseTypeName = BaseTypeName("float64", "f64")
FLOAT128: BaseTypeName = BaseTypeName("float128", "f128")
DOUBLE: BaseTypeName = BaseTypeName("double", "d")
LONG_DOUBLE: BaseTypeName = BaseTypeName("long_double", "ld")

VOID_PTR: BaseTypeName = BaseTypeName("ptr", "p")


class GenericArgument(TypeName):

    def __init__(self, src_info: SourceInfo, name: str) -> None:
        super().__init__(src_info, [], name, SymbolType.GENERIC_ARG)

    @property
    def c_alloc_name(self) -> str:
        raise CompilerException("Can't allocate generic argument.", self._src_info)

    @property
    def c_assigning_name(self) -> str:
        raise CompilerException("Generic argument is not instantiated.", self._src_info)

    @property
    def c_calling_name(self) -> str:
        raise CompilerException("Generic argument is not instantiated.", self._src_info)

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        raise CompilerException("Generic argument is not instantiated.", self._src_info)

    def instantiation(self, real_types: dict["GenericArgument", TypeName]) -> TypeName:
        return real_types[self]

    @property
    def is_generic(self) -> bool:
        return True

    @property
    def short_name(self) -> str:
        raise CompilerException("Generic argument is not instantiated.", self._src_info)


class VariableName(NamedSymbol):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName) -> None:
        super().__init__(src_info, namespace, "$" + name, SymbolType.VARIABLE)
        self._type: TypeName = t
        self._is_global: bool = False
        self._namespace: list[NamespaceName] = namespace
        self._self_name: str = name

    @property
    def as_ptr(self) -> str:
        return f"&{self.name}"

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "VariableName":
        new_variable: VariableName = deepcopy(self)
        new_variable._type = new_variable._type.instantiation(t)
        return new_variable

    @property
    def is_global(self) -> bool:
        return self._is_global

    @property
    def is_object(self) -> bool:
        return isinstance(self._type, ClassName)

    @property
    def raw_name(self) -> str:
        return f"{'.'.join(map(lambda n: n.name, self._namespace))}.{self._self_name}"

    @property
    def self_name(self) -> str:
        return self._self_name

    @property
    def type(self) -> TypeName:
        return self._type

    @property
    def type_name(self) -> str:
        return self._type.name

    @property
    def type_name_pair_assigning(self) -> str:
        return f"{self._type.c_assigning_name}{self.name}"

    @property
    def type_name_pair_calling(self) -> str:
        return f"{self._type.c_calling_name}{self.name}"


class GlobalVariableName(VariableName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName) -> None:
        super().__init__(src_info, namespace, name, t)
        self._is_global: bool = True


class Modifier(Enum):
    PUBLIC = 0
    PROTECTED = 1
    PRIVATE = 2


class PropertyVariableName(VariableName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName, modifier: Modifier,
                 is_static: bool) -> None:
        super().__init__(src_info, namespace, name, t)
        self._modifier: Modifier = modifier
        self._is_static: bool = is_static

    @property
    def is_static(self) -> bool:
        return self._is_static

    @property
    def modifier(self) -> Modifier:
        return self._modifier


class TemporaryVariableName(VariableName):

    def __init__(self, src_info: SourceInfo, name: str, t: TypeName) -> None:
        super().__init__(src_info, [], name, t)


class ClassName(TypeName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, parent: Optional[str],
                 is_abstract: bool, is_c_part: bool, generic_args: Optional[list[str]] = None) -> None:
        super().__init__(src_info, namespace, name, SymbolType.CLASS)
        self._parent: str = parent if parent is not None else "object"
        self._children: list[str] = []
        self._properties: dict[str, PropertyVariableName] = {}
        self._methods: dict[tuple[str, tuple[TypeName, ...]], MethodName] = {}
        self._generic_methods: dict[MethodName, dict[tuple[TypeName, ...], MethodName]] = {}
        self._method_overload_times: dict[str, int] = {}
        self._is_abstract: bool = is_abstract
        self._is_c_part: bool = is_c_part
        self._generic_args: Optional[list[str]] = generic_args
        self._generic_real_types: list[TypeName] = []
        self.add_property(self._src_info, "refCount", UINT32, Modifier.PRIVATE, False)
        self.add_property(self._src_info, "parent", VOID_PTR, Modifier.PRIVATE, False)

    def add_method(self, name: str, method: "MethodName") -> None:
        if name not in self._method_overload_times:
            self._method_overload_times[name] = 0
        method = method.set_cls(self, self._method_overload_times[name])
        if method.is_generic:
            self._generic_methods[method] = {}
            self._methods[name, ()] = method
        else:
            self._methods[name, tuple(method.type.args)] = method
        self._method_overload_times[name] += 1

    def add_property(self, src_info: SourceInfo, name: str, type_name: TypeName, modifier: Modifier,
                     is_static: bool) -> None:
        if name in self._properties:
            raise CompilerException(f"Property {name} already exists.", self._src_info)
        self._properties[name] = PropertyVariableName(src_info, self.as_namespace(), name, type_name, modifier,
                                                      is_static)

    def add_property_object(self, name: str, prop: PropertyVariableName):
        if name in self._properties:
            raise CompilerException(f"Property {name} already exists.", self._src_info)
        self._properties[name] = prop

    @property
    def c_alloc_name(self) -> str:
        return self.name

    @property
    def c_assigning_name(self) -> str:
        return f"{self.name} **"

    @property
    def c_calling_name(self) -> str:
        return f"{self.name} *"

    @property
    def children(self) -> list[str]:
        return self._children

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, ClassName):
            if target.name == self.name or target.name == "object":
                return True
            self_parent_name: str = self._parent
            while self_parent_name != "object":
                if self_parent_name == target.name:
                    return True
                parent = symbol_dict[self_parent_name, None]
                if not isinstance(parent, ClassName):
                    raise InternalCompilerException("Parent is not a class.", self._src_info)
                self_parent_name = parent.parent
            return False
        return False

    @property
    def generic_args(self) -> Optional[list[GenericArgument]]:
        return list(map(lambda n: GenericArgument(self._src_info, n),
                        self._generic_args)) if self._generic_args is not None else None

    @property
    def generic_args_str(self) -> Optional[list[str]]:
        return self._generic_args

    @property
    def generic_methods(self) -> dict["MethodName", dict[tuple[TypeName, ...], "MethodName"]]:
        return self._generic_methods

    def get_generic_method(self, method: "MethodName", types: tuple[TypeName, ...]) -> "MethodName":
        if method not in self._generic_methods:
            raise CompilerException(f"Method {method.name} is not generic.", method._src_info)
        if types not in self._generic_methods[method]:
            self._generic_methods[method][types] = method.instantiation_full(method.name, list(types))
        return self._generic_methods[method][types]

    def get_generic_method_by_name(self, name: str, types: tuple[TypeName, ...]) -> "MethodName":
        return self.get_generic_method(self._methods[name, ()], types)

    def has_method(self, name: str) -> bool:
        return name in self._methods

    def instantiation_full(self, new_name: str, args: list[TypeName]) -> "ClassName":
        if self._generic_args is None:
            raise CompilerException("Class is not generic.", self._src_info)
        if len(args) != len(self._generic_args):
            raise CompilerException("Instantiation arguments number is not equal to generic arguments number.",
                                    self._src_info)
        generic_dict: dict[GenericArgument, TypeName] = dict(
            zip(map(lambda n: GenericArgument(self._src_info, n), self._generic_args), args)
        )
        result: ClassName = ClassName(self._src_info, GENERIC_CLASS, new_name, self._parent,
                                      self._is_abstract, False, self._generic_args)
        for name, prop in self._properties.items():
            if name in ["refCount", "parent"]:
                continue
            result.add_property_object(name, prop.instantiation("", generic_dict))
        for (name, _), method in self._methods.items():
            result.add_method(name, method.instantiation(f"{new_name}${method.name}", generic_dict))
        return result

    @property
    def is_abstract(self) -> bool:
        return self._is_abstract

    @property
    def is_c_part(self) -> bool:
        return self._is_c_part

    @property
    def is_generic(self) -> bool:
        return self._generic_args is not None and len(self._generic_args) > 0

    @property
    def is_object(self) -> bool:
        return True

    @property
    def methods(self) -> dict[tuple[str, tuple[TypeName, ...]], "MethodName"]:
        return self._methods

    @property
    def parent(self) -> str:
        return self._parent

    @property
    def properties(self) -> dict[str, PropertyVariableName]:
        return self._properties

    def shared_parent(
            self,
            other: TypeName,
            symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]
    ) -> Optional["ClassName"]:
        if not isinstance(other, ClassName):
            return None
        self_parents: list[str] = [self.name]
        while self_parents[-1] != "object":
            self_parent = symbol_dict[self_parents[-1], None]
            if not isinstance(self_parent, ClassName):
                raise InternalCompilerException(f"{self_parents[-1]} is not a class.", self._src_info)
            self_parents.append(self_parent.parent)
        other_parents: list[str] = [other.name]
        while other_parents[-1] != "object":
            other_parent = symbol_dict[other_parents[-1], None]
            if not isinstance(other_parent, ClassName):
                raise InternalCompilerException(f"{other_parents[-1]} is not a class.", self._src_info)
            other_parents.append(other_parent.parent)
        cls_name: str = list(filter(lambda x: x in other_parents, self_parents))[0]
        cls = symbol_dict[cls_name, None]
        if not isinstance(cls, ClassName):
            raise InternalCompilerException(f"{cls_name} is not a class.", self._src_info)
        return cls

    @property
    def short_name(self) -> str:
        return "obj"

    @property
    def vtable_name(self) -> str:
        return f"{self.name}$$vtable"


class ArrayTypeName(ClassName):

    def __init__(self, src_info: SourceInfo, element_type: TypeName) -> None:
        super().__init__(src_info, element_type.namespace, "array$" + element_type.name, None, False, False)
        self._element_type: TypeName = element_type

    @property
    def element_type(self) -> TypeName:
        return self._element_type

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return ArrayTypeName(self._src_info, self.element_type.instantiation(real_types))


class TupleTypeName(ClassName):

    def __init__(self, src_info: SourceInfo, types: list[TypeName]) -> None:
        super().__init__(src_info, VIOLA_COLLECTIONS, f"$tuple({', '.join(list(map(lambda t: t.name, types)))})", None,
                         False, False)
        self._type_args: list[TypeName] = types

    @property
    def c_alloc_name(self) -> str:
        return TUPLE_T

    @property
    def c_assigning_name(self) -> str:
        return f"{TUPLE_T} **"

    @property
    def c_calling_name(self) -> str:
        return f"{TUPLE_T} *"

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, TupleTypeName):
            if len(self.types) != len(target.types):
                return False
            return all(list(map(lambda t, u: t.convertable_to(u, symbol_dict), self._type_args, target.types)))
        return False

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return TupleTypeName(self._src_info, list(map(lambda t: t.instantiation(real_types), self.types)))

    @property
    def type_names(self) -> list[str]:
        return list(map(lambda t: t.name, self.types))

    @property
    def types(self) -> list[TypeName]:
        return self._type_args


class FunctionTypeName(TypeName):

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName],
                 generic_args: Optional[list[str]] = None) -> None:
        super().__init__(src_info, [],
                         f"({', '.join(map(lambda t: t.name, args))}) -> ({', '.join(map(lambda t: t.name, returns))})",
                         SymbolType.FUNCTION)
        self._args: list[TypeName] = args
        self._returns: list[TypeName] = returns
        self._args_tuple: TupleTypeName = TupleTypeName(SourceInfo(""), args)
        self._returns_tuple: TupleTypeName = TupleTypeName(SourceInfo(""), returns)
        self._generic_args: Optional[list[str]] = generic_args

    @property
    def args(self) -> list[TypeName]:
        return self._args

    @property
    def arg_names(self) -> list[str]:
        return list(map(lambda t: t.raw_name, self._args))

    def as_header(self, func_name: str) -> str:
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        return f"void {func_name}({', '.join([args_text, returns_text, LISTENER_T + ' *'])})"

    @property
    def c_alloc_name(self) -> str:
        raise CompilerException("Can't allocate function type.", self._src_info)

    @property
    def c_assigning_name(self) -> str:
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        return f"void(**)({', '.join([args_text, returns_text, LISTENER_T + ' *'])})"

    @property
    def c_calling_name(self) -> str:
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        return f"void(**)({', '.join([args_text, returns_text, LISTENER_T + ' *'])})"

    def c_calling_name_with_var(self, var_name: str) -> str:
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        return f"void(*{var_name})({', '.join([args_text, returns_text, LISTENER_T + ' *'])})"

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, FunctionTypeName):
            return (self._args_tuple.convertable_to(target._args_tuple, symbol_dict) and
                    self._returns_tuple.convertable_to(target._returns_tuple, symbol_dict))
        return False

    @property
    def generic_args(self) -> Optional[list[GenericArgument]]:
        return list(map(lambda t: GenericArgument(self._src_info, t),
                        self._generic_args)) if self._generic_args is not None else None

    @property
    def generic_args_str(self) -> Optional[list[str]]:
        return self._generic_args

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "FunctionTypeName":
        result = FunctionTypeName(
            self._src_info,
            list(map(lambda t: t.instantiation(real_types), self._args)),
            list(map(lambda t: t.instantiation(real_types), self._returns))
        )
        result._generic_args = list(filter(lambda t: t not in real_types, self._generic_args))
        return result

    def instantiation_func_t(self, real_types: list[TypeName]) -> "FunctionTypeName":
        if self._generic_args is None:
            raise CompilerException("This function type is not generic.", self._src_info)
        if len(real_types) != len(self._generic_args):
            raise CompilerException("Generic arguments number is not equal to generic arguments number.",
                                    self._src_info)
        generic_dict = dict(zip(map(lambda t: GenericArgument(self._src_info, t), self._generic_args), real_types))
        return FunctionTypeName(
            self._src_info,
            list(map(lambda t: t.instantiation(generic_dict), self._args)),
            list(map(lambda t: t.instantiation(generic_dict), self._returns))
        )

    @property
    def is_generic(self) -> bool:
        return self._generic_args is not None and len(self._generic_args) > 0

    @property
    def returns(self) -> list[TypeName]:
        return self._returns

    @property
    def short_name(self) -> str:
        return "obj"


class AsyncFuncTypeName(FunctionTypeName):

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName]) -> None:
        super().__init__(src_info, args, returns)

    def as_header(self, func_name: str) -> str:
        return f"void {func_name}({TUPLE_T} *, {TUPLE_T} *, {LISTENER_T} *)"

    @property
    def c_assigning_name(self) -> str:
        return f"void(**)({TUPLE_T} *, {TUPLE_T} *, {LISTENER_T} *)"

    @property
    def c_calling_name(self) -> str:
        return f"void(*)({TUPLE_T} *, {TUPLE_T} *, {LISTENER_T} *)"

    def c_calling_name_with_var(self, var_name: str) -> str:
        return f"void(*{var_name})({TUPLE_T} *, {TUPLE_T} *, {LISTENER_T} *)"

    @classmethod
    def from_function_type_name(cls, function_type_name: FunctionTypeName) -> "AsyncFuncTypeName":
        return cls(function_type_name._src_info, function_type_name.args, function_type_name.returns)


class ClosureTypeName(FunctionTypeName):

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName]) -> None:
        super().__init__(src_info, args, returns)

    @property
    def c_assigning_name(self) -> str:
        return f"{CLOSURE_T} **"

    @property
    def c_calling_name(self) -> str:
        return f"{CLOSURE_T} *"

    def c_calling_name_with_var(self, var_name: str) -> str:
        return f"{CLOSURE_T} *{var_name}"

    @property
    def is_object(self) -> bool:
        return True


class EnumName(TypeName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, based_type: TypeName) -> None:
        super().__init__(src_info, namespace, name, SymbolType.ENUM)
        self._based_type: TypeName = based_type

    @property
    def based_type(self) -> TypeName:
        return self._based_type

    @property
    def c_alloc_name(self) -> str:
        return self._based_type.c_alloc_name

    @property
    def c_assigning_name(self) -> str:
        return self._based_type.c_assigning_name

    @property
    def c_calling_name(self) -> str:
        return self._based_type.c_calling_name

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        return self._based_type.convertable_to(target, symbol_dict)

    @property
    def is_generic(self) -> bool:
        return False

    @property
    def short_name(self) -> str:
        return self._based_type.short_name


class FunctionName(GlobalVariableName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: FunctionTypeName,
                 arg_names: list[str], ret_names: list[str], export: bool) -> None:
        if len(arg_names) != len(t.args):
            raise CompilerException("Invalid number of arguments.", self._src_info)
        func_type_name: str = "$".join(list(map(lambda ty: ty.name, t.args)))
        super().__init__(src_info, namespace, name + "$" + func_type_name, t)
        self._arg_names: list[str] = arg_names
        self._ret_names: list[str] = ret_names
        self._export: bool = export
        self._default_params: dict[str, Optional[GlobalVariableName]] = {k: None for k in arg_names}
        self._arg_types: dict[str, TypeName] = {k: v for k, v in zip(arg_names, t.args)}

    @property
    def arg_names(self) -> list[str]:
        return self._arg_names

    @property
    def arg_types(self) -> list[TypeName]:
        return self.type.args

    @property
    def arg_types_dict(self) -> dict[str, TypeName]:
        return self._arg_types

    @property
    def args(self) -> list[TemporaryVariableName]:
        return list(map(lambda t, x: TemporaryVariableName(self._src_info, x, t), self.type.args, self._arg_names))

    def as_async(self) -> "FunctionName":
        return AsyncFuncName.from_function_name(self)

    def as_declare(self) -> str:
        return self.type.as_header(self._name)

    def as_define_name(self) -> str:
        return "void " + self._name + "(" + ", ".join(
            list(map(lambda t, x: f"{t.name}${x}", self.type.args, self._arg_names)) + [
                f"{LISTENER_T} *listener"]) + ")"

    def as_define_name_raw(self) -> str:
        return "void " + self._name + "(" + ", ".join(
            list(map(lambda t, x: f"{t.name}{x}", self.type.args, self._arg_names)) + [
                f"{LISTENER_T} *listener"]) + ")"

    def as_method(self, cls: ClassName) -> "MethodName":
        # noinspection PyUnresolvedReferences
        return cls.methods[self._name, tuple(self._type.args)]

    def as_sync(self) -> "FunctionName":
        return FunctionName(self._src_info, self._namespace, self._self_name + "$sync", self.type, self._arg_names,
                            self._ret_names, self._export)

    def as_tuple(self) -> GlobalVariableName:
        t = TupleTypeName(self._src_info, [self.type, self.type])
        name: str = f"{self._self_name}$tuple"
        return GlobalVariableName(self._src_info, self._namespace, name, t)

    def as_type_name_pair(self) -> str:
        self._type: FunctionTypeName
        # noinspection PyUnresolvedReferences
        return self._type.c_calling_name_with_var(self._name)

    @property
    def default_params(self) -> dict[str, Optional[GlobalVariableName]]:
        return self._default_params

    @property
    def export(self) -> bool:
        return self._export

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "FunctionName":
        new_type: FunctionTypeName = self.type.instantiation(t)
        result: FunctionName = FunctionName(self._src_info, GENERIC_FUNC, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    def instantiation_full(self, new_name: str, real_types: list[TypeName]) -> "FunctionName":
        new_type: FunctionTypeName = self.type.instantiation_func_t(real_types)
        result: FunctionName = FunctionName(self._src_info, GENERIC_FUNC, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    @property
    def ret_names(self) -> list[str]:
        return self._ret_names

    @property
    def ret_types(self) -> list[TypeName]:
        return self.type.returns

    def set_default_params(self, default_param_names: list[str]) -> None:
        not_in_args: list[str] = list(filter(lambda n: n not in self._arg_names, default_param_names))
        if len(not_in_args) != 0:
            raise CompilerException(f"Default parameter {', '.join(not_in_args)} is not in arguments.",
                                    self._src_info)
        for name in default_param_names:
            # noinspection PyUnresolvedReferences
            var_type: TypeName = self._type.args[self._arg_names.index(name)]
            self._default_params[name] = GlobalVariableName(self._src_info, self.as_namespace(), name, var_type)

    @property
    def type(self) -> FunctionTypeName:
        self._type: FunctionTypeName
        # noinspection PyTypeChecker
        return self._type


class AsyncFuncName(FunctionName):

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: AsyncFuncTypeName,
                 arg_names: list[str],
                 ret_names: list[str], export: bool) -> None:
        super().__init__(src_info, namespace, name, t, arg_names, ret_names, export)

    def as_define_name(self) -> str:
        return f"void {self._name}({TUPLE_T} *params, {TUPLE_T} *returns, {LISTENER_T} *listener)"

    def as_define_name_raw(self) -> str:
        return f"void {self._name}({TUPLE_T} *params, {TUPLE_T} *returns, {LISTENER_T} *listener)"

    @classmethod
    def from_function_name(cls, function_name: FunctionName) -> "AsyncFuncName":
        return cls(function_name._src_info, function_name._namespace, function_name._self_name + "$async",
                   AsyncFuncTypeName.from_function_type_name(function_name.type), function_name._arg_names,
                   function_name._ret_names, function_name._export)


class MethodName(PropertyVariableName):

    def __init__(self, src_info: SourceInfo, cls: ClassName, name: str, t: FunctionTypeName, is_abstract: bool,
                 is_static: bool, arg_names: list[str], ret_names: list[str], modifier: Modifier, export: bool) -> None:
        cls_generic_args: list[str] = cls.generic_args_str if cls.generic_args_str is not None else []
        t_generic_args: list[str] = t.generic_args_str if t.generic_args_str is not None else []
        if not is_static:
            arg_types: list[TypeName] = [cls] + t.args
            t = FunctionTypeName(src_info, arg_types, t.returns, cls_generic_args + t_generic_args)
            arg_names: list[str] = ["_this"] + arg_names
        function_name: FunctionName = FunctionName(src_info, cls.as_namespace(), name, t, arg_names, ret_names, export)
        super().__init__(src_info, [], function_name.name, t, modifier, is_static)
        func_type_name: str = "$".join(list(map(lambda ty: ty.name, t.args)))
        self._cls: ClassName = cls
        self._is_abstract: bool = is_abstract
        self._modifier: Modifier = modifier
        self._method_name: str = name + "$" + func_type_name
        self._function_name: FunctionName = function_name

    def as_async(self) -> "MethodName":
        self._type: FunctionTypeName
        # noinspection PyTypeChecker
        return MethodName(self._src_info, self._cls, self._self_name + "$async", self._type, self._is_abstract,
                          self._is_static, self._function_name.arg_names, self._function_name.ret_names, self._modifier,
                          self._function_name.export)

    def as_function(self) -> FunctionName:
        return self._function_name

    @property
    def as_method_type_name_pair(self) -> str:
        return f"{self._function_name.type_name}{self._method_name}"

    def as_sync(self) -> "MethodName":
        # noinspection PyTypeChecker
        return MethodName(self._cls, self._self_name + "$sync", self.type, self._is_abstract, self._is_static,
                          self._function_name.arg_names, self._function_name.ret_names, self._modifier,
                          self._function_name.export, self._src_info)

    def as_tuple(self) -> GlobalVariableName:
        t = TupleTypeName(self._src_info, [self.type, self.type])
        name: str = f"{self._self_name}$tuple"
        return GlobalVariableName(self._src_info, self._cls.as_namespace(), name, t)

    @property
    def cls(self) -> ClassName:
        return self._cls

    @property
    def default_params(self) -> dict[str, Optional[GlobalVariableName]]:
        return self._function_name.default_params

    @property
    def kw_type(self) -> SymbolType:
        return SymbolType.FUNCTION

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "MethodName":
        result: MethodName = deepcopy(self)
        result._function_name = self._function_name.instantiation(new_name, t)
        result.rename(result._function_name.name)
        return result

    def instantiation_full(self, new_name: str, t: list[TypeName]) -> "MethodName":
        result: MethodName = deepcopy(self)
        result._function_name = self._function_name.instantiation_full(new_name, t)
        result.rename(result._function_name.name)
        return result

    @property
    def is_abstract(self) -> bool:
        return self._is_abstract

    @property
    def is_generic(self) -> bool:
        return self._type.is_generic

    @property
    def method_name(self) -> str:
        return self._method_name

    def rebuild(self, func: FunctionName) -> "MethodName":
        return MethodName(self._src_info, self._cls, self._self_name, func.type, self._is_abstract, self._is_static,
                          func.arg_names, func.ret_names, self._modifier, func.export)

    def set_cls(self, cls: ClassName, overloaded_times: int) -> "MethodName":
        self._type: FunctionTypeName
        # noinspection PyTypeChecker
        return MethodName(self._src_info, cls, f"{self._self_name}$_{overloaded_times}", self._type,
                          self._is_abstract, self._is_static, self._function_name.arg_names,
                          self._function_name.ret_names, self._modifier, self._function_name.export)

    def set_default_params(self, default_param_names: list[str]) -> None:
        self._function_name.set_default_params(default_param_names)

    @staticmethod
    def to_name_str(cls: ClassName, name: str) -> str:
        return "$".join(list(map(lambda n: n.name, cls.as_namespace()))) + "$" + name

    @property
    def type(self) -> FunctionTypeName:
        return self._function_name.type


class GenericTable:

    def __contains__(self, item: tuple[FunctionName | ClassName | MethodName, Optional[tuple[TypeName, ...]]]) -> bool:
        key, types = item
        if key.kw_type == SymbolType.FUNCTION:
            if key in self._function_instances:
                return types in self._function_instances[key] or types is None
            return False
        if key.kw_type == SymbolType.CLASS:
            return key in self._class_instances and (types in self._class_instances[key] or types is None)
        raise InternalCompilerException("Unknown item type.", self._source_info)

    def __getitem__(self, key: FunctionName | ClassName,
                    types: tuple[TypeName, ...]) -> FunctionName | ClassName:
        if key.kw_type == SymbolType.FUNCTION:
            return self._function_instances[key][types]
        if key.kw_type == SymbolType.CLASS:
            return self._class_instances[key][types]
        raise InternalCompilerException("Unknown item type.", self._source_info)

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName]) -> None:
        self._namespace: list[NamespaceName] = namespace
        self._function_instances: dict[FunctionName, dict[tuple[TypeName, ...], FunctionName]] = {}
        self._class_instances: dict[ClassName, dict[tuple[TypeName, ...], ClassName]] = {}
        self._source_info: SourceInfo = src_info

    def add_cls_def(self, class_name: ClassName) -> None:
        if class_name in self._class_instances:
            raise InternalCompilerException("Class already exists.", self._source_info)
        self._class_instances[class_name] = {}

    def add_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> None:
        if class_name in self._class_instances:
            if t in self._class_instances[class_name]:
                raise InternalCompilerException("Class already exists.", self._source_info)
            self._class_instances[class_name][t] = class_name.instantiation_full(
                f"{class_name.name}$_{len(self._class_instances[class_name])}", list(t)
            )
        else:
            raise InternalCompilerException("Class does not exist.", self._source_info)

    def add_func_def(self, function_name: FunctionName) -> None:
        if function_name in self._function_instances:
            raise InternalCompilerException("Function already exists.", self._source_info)
        self._function_instances[function_name] = {}

    def add_func_instance(self, function_name: FunctionName, t: tuple[TypeName, ...]) -> None:
        if function_name in self._function_instances:
            if t in self._function_instances[function_name]:
                raise InternalCompilerException("Function already exists.", self._source_info)
            self._function_instances[function_name][t] = function_name.instantiation_full(
                f"{function_name.name}$_{len(self._function_instances[function_name])}", list(t)
            )
        else:
            raise InternalCompilerException("Function does not exist.", self._source_info)

    def get_all_to_instantiate_symbols(self, src_info: SourceInfo,
                                       symbol: ClassName | FunctionName) -> list[tuple[TypeName, ...]]:
        if isinstance(symbol, ClassName):
            instances = self._class_instances
        elif isinstance(symbol, FunctionName):
            instances = self._function_instances
        else:
            raise InternalCompilerException("Unknown type of symbol.", src_info)
        return list(instances[symbol].keys())

    def get_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        if class_name in self._class_instances:
            if t in self._class_instances[class_name]:
                return self._class_instances[class_name][t]
            self.add_cls_instance(class_name, t)
            return self._class_instances[class_name][t]
        raise CompilerException("Class does not exist.", self._source_info)

    def get_func_instance(self, function_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        if function_name in self._function_instances:
            if t in self._function_instances[function_name]:
                return self._function_instances[function_name][t]
            self.add_func_instance(function_name, t)
            return self._function_instances[function_name][t]
        raise CompilerException("Function does not exist.", self._source_info)


class SymbolTable:

    def __contains__(self, item: tuple[NamedSymbol | str, Optional[tuple[TypeName, ...]]]) -> bool:
        if isinstance(item[0], NamedSymbol):
            return item[0].name in self._symbols.values()
        if item[0].startswith(self._namespace_name):
            return item[len(self._namespace_name):] in self._symbols
        if item[0].startswith("$tuple(") and item[0].endswith(")"):
            return True
        return item in self._symbols

    def __getitem__(self, item: str, types: Optional[tuple[TypeName, ...]]) -> NamedSymbol:
        if item.startswith(self._namespace_name):
            return self._symbols[item[len(self._namespace_name):], types]
        if item.startswith("$tuple(") and item.endswith(")"):
            items = item[7:-1].split(", ")
            result = list(map(lambda x: self[x], items))
            # noinspection PyTypeChecker
            return TupleTypeName(self._src_info, result)
        if item not in self._symbols:
            raise CompilerException(f"Symbol {item} not found.", self._src_info)
        return self._symbols[item, types]

    def __init__(self, path: str, workspace: str) -> None:
        self._symbols: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol] = {}
        self._func_overload_times: dict[str, int] = {}
        dir_list: list[str] = os.path.relpath(path, workspace).replace("-", "_").split(os.sep)
        self._namespace: list[NamespaceName] = list(map(lambda x: NamespaceName(x), dir_list))
        self._namespace_name: str = ".".join(map(lambda x: x.name, self._namespace)) + "."
        self._counter: int = 0
        self._class_info_list_name: str = "$".join(map(lambda x: x.name, self._namespace)) + "$classInfoList"
        self._src_info: SourceInfo = SourceInfo(path)
        self._generic_table: GenericTable = GenericTable(self._src_info, self._namespace)

    def add(self, symbol: NamedSymbol, name: str, types: Optional[tuple[TypeName, ...]]) -> None:
        if symbol.name in self._symbols:
            raise CompilerException(f"Symbol {name} already exists.", self._src_info)
        if symbol.kw_type == SymbolType.FUNCTION and types is None:
            raise InternalCompilerException("Function must have types.", self._src_info)
        elif symbol.kw_type != SymbolType.FUNCTION and types is not None:
            raise InternalCompilerException("Symbol must not have types.", self._src_info)
        self._symbols[name, types] = symbol

    def clear_temporaries(self) -> None:
        for k, v in self._symbols.items():
            if isinstance(v, VariableName) and not v.is_global:
                del self._symbols[k]

    def contains_method(self, cls_name: str, name: str, types: list[str]) -> bool:
        cls = self[cls_name]
        if not isinstance(cls, ClassName):
            return False
        types_declaration: list[TypeName] = []
        for t in types:
            to_append = self[t, None]
            if not isinstance(to_append, TypeName):
                raise InternalCompilerException(f"{to_append} must be a type.", self._src_info)
            types_declaration.append(to_append)
        return (name, tuple(types_declaration)) in cls.methods.keys()

    def find_function(self, name: str, types: list[str]) -> FunctionName:
        func_name: str = name + "$" + "$".join(types)
        result = self[func_name]
        if not isinstance(result, FunctionName):
            raise CompilerException(f"Symbol {name} is not a function.", self._src_info)
        return result

    def find_functions(self, name: str, args: list[str], kwargs: dict[str, str]) -> list[FunctionName]:
        # noinspection PyTypeChecker
        args_declaration: list[TypeName] = list(map(lambda x: self[x, None], args))
        # noinspection PyTypeChecker
        kwargs_declaration: dict[str, TypeName] = dict(map(lambda x: (x, self[kwargs[x], None]), kwargs.keys()))
        args_length: int = len(args_declaration)
        args_tuple: tuple[TypeName, ...] = tuple(args_declaration)
        matches: dict[tuple[str, tuple[TypeName, ...]], FunctionName | MethodName] = dict(
            filter(
                lambda x: (x[0][0] == name or x[1].name == name) and all(
                    map(lambda i: args_tuple[i].convertable_to(x[0][1][i]), range(args_length))
                ),
                self._symbols.items()
            )
        )
        matches = dict(filter(lambda x: all(y in x[1].arg_names for y in kwargs.keys()), matches.items()))
        matches = dict(filter(
            lambda x: all(x[1].arg_types_dict[y].convertable_to(kwargs_declaration[y])
                          for y in kwargs_declaration.keys()),
            matches.items()
        ))
        matches = dict(map(
            lambda x: (x[0][0], x[1].as_function()) if not x[1].kw_type == SymbolType.FUNCTION else x, matches.items()
        ))
        return list(matches.values())

    def find_method(self, cls_name: str, name: str, types: list[str]) -> MethodName:
        types_declaration: list[TypeName] = []
        for t in types:
            to_append = self[t, None]
            if not isinstance(to_append, TypeName):
                raise InternalCompilerException(f"{to_append} must be a type.", self._src_info)
            types_declaration.append(to_append)
        cls = self[cls_name, None]
        if not isinstance(cls, ClassName):
            raise InternalCompilerException(f"{cls} must be a class.", self._src_info)
        func_name: MethodName = cls.methods[name, tuple(types_declaration)]
        result = self[func_name]
        if not isinstance(result, MethodName):
            raise CompilerException(f"Symbol {name} is not a method.", self._src_info)
        return result

    def find_methods(self, cls_name: str, name: str, known_types: list[str]) -> list[MethodName]:
        new_types: list[str] = list(map(
            lambda x: x[len(self._namespace_name):] if x.startswith(self._namespace_name) else x, known_types
        ))
        func_name: str = cls_name + "." + name + "$" + "$".join(new_types)
        result_keys: list[str] = list(filter(lambda x: x.startswith(func_name), self._symbols.keys()))
        return list(filter(lambda x: isinstance(x, MethodName), map(lambda x: self[x], result_keys)))

    def get_all_to_instantiate_symbols(self, src_info: SourceInfo,
                                       symbol: ClassName | FunctionName) -> list[tuple[TypeName, ...]]:
        return self._generic_table.get_all_to_instantiate_symbols(src_info, symbol)

    def get_counter(self) -> str:
        result: str = f"$$_{self._counter}"
        self._counter += 1
        return result

    def get_generic_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        cls = self._generic_table.get_cls_instance(class_name, t)
        for method in cls.methods.values():
            if method.is_generic and method not in self._generic_table:
                self._generic_table.add_func_def(method.as_function())
        return cls

    def get_generic_func_instance(self, func_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        return self._generic_table.get_func_instance(func_name, t)

    def get_generic_instance(self, name: ClassName | FunctionName | MethodName, t: tuple[[TypeName, ...]]) -> ClassName | FunctionName | MethodName:
        if isinstance(name, ClassName):
            return self.get_generic_cls_instance(name, t)
        if isinstance(name, FunctionName):
            return self.get_generic_func_instance(name, t)
        if isinstance(name, MethodName):
            return self.get_generic_method_instance(name, t)
        raise InternalCompilerException("Unknown symbol type", name.src_info)

    def get_generic_method_instance(self, method_name: MethodName, t: tuple[TypeName, ...]) -> MethodName:
        func = self._generic_table.get_func_instance(method_name.as_function(), t)
        return method_name.rebuild(func)

    def mix(self, other: "SymbolTable") -> None:
        self._symbols.update(other._symbols)

    @property
    def namespace(self) -> list[NamespaceName]:
        return self._namespace

    @classmethod
    def read(cls, path: str) -> "SymbolTable":
        with open(path, "r") as f:
            data: list[str] = f.read().split("---")
        metadata: list[str] = data[0].split("\n")
        self = cls(metadata[0], metadata[1])
        for item in data[1:]:
            self._read_item(item)
        self.add(FunctionName(
            self._src_info,
            self.namespace,
            "_global",
            FunctionTypeName(self._src_info, [], []),
            [],
            [],
            False
        ), "$_global", ())
        return self

    @property
    def symbols(self) -> dict[tuple[str, tuple[TypeName, ...] | None], NamedSymbol]:
        return self._symbols

    def _read_item(self, item: str) -> None:
        item_args: list[str] = item.split("\n")
        item_type: str = item_args[0].split(" ")[1]
        loc_str: list[str] = item_args[0].split(" ")[0].split(":")
        loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
        self._src_info.set_loc(*loc_tuple)
        match item_type:
            case "BASE":
                self._read_base_type_def(item_args)
            case "FUNC":
                self._read_func_decl(item_args)
            case "CLASS":
                self._read_class_decl(item_args)
            case "VAR":
                self._read_global_var_decl(item_args)
            case "METHOD":
                self._read_method_decl(item_args)
            case "ENUM":
                self._read_enum_decl(item_args)

    def _read_base_type_def(self, item: list[str]) -> None:
        item = item[0].split(" ")
        t = BaseTypeName(item[2], item[3])
        if (t, None) in self:
            raise CompilerException(f"Type {t.name} already exists.", self._src_info)
        self.add(t, item[2], None)

    def _read_func_decl(self, item: list[str]) -> None:
        item_name: str = item[0].split(" ")[2]
        export: bool = "export" in item[0].split(" ")[3:]
        generic_args: list[str] = item[1].split(" ")
        item_args: list[str] = item[2].split(" ")
        item_returns: list[str] = item[3].split(" ")
        item_default_args: list[str] = item[4].split(" ")
        # noinspection PyTypeChecker
        args = list(map(lambda arg: self[arg], item_args[::2]))
        if any(map(lambda arg: not isinstance(arg, TypeName), args)):
            raise CompilerException("Function arguments must be types.", self._src_info)
        if (item_name, tuple(args)) in self:
            raise CompilerException(f"Function {item_name} already exists.", self._src_info)
        args: list[TypeName]
        # noinspection PyTypeChecker
        returns: list[TypeName] = list(map(lambda ret: self[ret], item_returns[::2]))
        if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
            raise CompilerException("Function returns must be types.", self._src_info)
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        if item_name not in self._func_overload_times:
            self._func_overload_times[item_name] = 0
        func = FunctionName(self._src_info, self.namespace,
                            f"{item_name}$_{self._func_overload_times[item_name]}", func_type,
                            item_args[1::2], item_returns[1::2], export)
        self._func_overload_times[item_name] += 1
        func.set_default_params(item_default_args)
        for k, v in func.default_params.items():
            if v is not None:
                self.add(v, item_name + "$default$" + k, None)
        self.add(func, item_name, tuple(args))

    def _read_global_var_decl(self, item: list[str]) -> None:
        item: list[str] = item[0].split(" ")
        item_name: str = item[2]
        item_type: str = item[1]
        # noinspection PyTypeChecker
        self.add(GlobalVariableName(self.namespace, item_name, self[item_type], self._src_info), item_name, None)

    def _read_method_decl(self, item: list[str]) -> None:
        item_name: list[str] = item[0].split(" ")
        generic_args: list[str] = item[1].split(" ")
        cls_name: str = item_name[2]
        method_name: str = item_name[3]
        if cls_name not in self:
            raise CompilerException(f"Class {cls_name} not found.", self._src_info)
        cls = self[cls_name]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"{cls_name} is not a class.", self._src_info)
        is_abstract: bool = "abstract" in item_name[4:]
        is_static: bool = "static" in item_name[4:]
        export: bool = "export" in item_name[4:]
        item_args: list[str] = item[2].split(" ")
        method_name: str = method_name + "$" + "$".join(item_args[::2])
        item_returns: list[str] = item[3].split(" ")
        item_default_args: list[str] = item[4].split(" ")
        # noinspection PyTypeChecker
        args = list(map(lambda arg: self[arg], item_args[::2]))
        if any(map(lambda arg: not isinstance(arg, TypeName), args)):
            raise CompilerException("Function arguments must be types.", self._src_info)
        # noinspection PyTypeChecker
        returns = list(map(lambda ret: self[ret], item_returns[::2]))
        if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
            raise CompilerException("Function returns must be types.", self._src_info)
        args: list[TypeName]
        returns: list[TypeName]
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        modifier = self.__get_modifier(item_name[4:])
        if f"{cls.name}.{method_name}" not in self._func_overload_times:
            self._func_overload_times[f"{cls.name}.{method_name}"] = 0
        method = MethodName(
            self._src_info, cls, f"{method_name}$_{self._func_overload_times[f'{cls.name}.{method_name}']}",
            func_type, is_abstract, is_static, item_args[1::2], item_returns[1::2], modifier, export
        )
        self._func_overload_times[f"{cls.name}.{method_name}"] += 1
        method.set_default_params(item_default_args)
        for k, v in method.default_params.items():
            if v is not None:
                self.add(v, f"{cls_name}.{method_name}$default$" + k, None)
        self.add(method, f"{cls_name}.{method_name}", tuple(args))
        cls.add_method(method_name, method)

    def _read_class_decl(self, item: list[str]) -> None:
        cls_name: str = item[0].split(" ")[2]
        if (cls_name, None) in self:
            raise CompilerException(f"Class {cls_name} already exists.", self._src_info)
        parent: Optional[ClassName] = None
        if len(item[0].split(" ")) == 4:
            parent_name = item[0].split(" ")[3]
            # noinspection PyTypeChecker
            parent = self[parent_name]
            if not isinstance(parent, ClassName):
                raise CompilerException(f"Parent class {parent_name} is not a class.", self._src_info)
        else:
            parent_name = None
        is_abstract: bool = "abstract" in item[0].split(" ")[3:]
        is_c_part: bool = "c" in item[0].split(" ")[3:]
        cls = ClassName(self._src_info, self.namespace, cls_name, parent_name, is_abstract, is_c_part)
        cls_array: ArrayTypeName = ArrayTypeName(self._src_info, cls)
        if parent is not None:
            for name, prop in parent.properties.items():
                cls.add_property_object(name, prop)
            vtable: ClassName = ClassName(self._src_info, [], cls.name + "$$vtable", None, False,
                                          False)
            self.add(vtable, cls.name + ".$$vtable", None)
            cls.add_property(self._src_info, "$$vtable", vtable, Modifier.PUBLIC, True)
        item_loc: int = 1
        while not item[item_loc] == "END CLASS":
            item_text: list[str] = item[item_loc].split(" ")
            loc_str: list[str] = item_text[0].split(":")
            loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
            self._src_info.set_loc(*loc_tuple)
            type_name: str = item_text[1]
            property_name: str = item_text[2]
            # noinspection PyTypeChecker
            t: TypeName = self[type_name]
            cls.add_property(self._src_info, property_name, t, self.__get_modifier(item_text[3:]),
                             "static" in item_text[3:])
            if item_loc == len(item) - 1:
                raise CompilerException(f"Unexpected end of class {cls_name}", self._src_info)
            item_loc += 1
        if cls_name + ".__del__" not in self:
            if is_c_part:
                raise CompilerException(f"C part class {cls_name} must have a destructor.", self._src_info)
            cls.add_method("__del__",
                           MethodName(self._src_info, cls, "__del__", FunctionTypeName(self._src_info, [], []), False,
                                      False, [], [], Modifier.PUBLIC, False))
        self.add(cls, cls_name, None)
        self.add(cls_array, cls_name + "[]", None)

    def _read_enum_decl(self, item: list[str]) -> None:
        item_name: str = item[0].split(" ")[2]
        based_type: str = item[0].split(" ")[3]
        if based_type not in self:
            raise CompilerException(f"Based type {based_type} not found.", self._src_info)
        if (item_name, None) in self:
            raise CompilerException(f"Enum {item_name} already exists.", self._src_info)
        # noinspection PyTypeChecker
        enum = EnumName(self.namespace, item_name, self[based_type], self._src_info)
        self.add(enum, item_name, None)

    def __get_modifier(self, item: list[str]) -> Modifier:
        is_public: bool = "public" in item
        is_private: bool = "private" in item
        is_protected: bool = "protected" in item or not is_public and not is_private
        if is_public and is_private:
            raise CompilerException("Method cannot be both public and private at the same time.", self._src_info)
        if is_public and is_protected:
            raise CompilerException("Method cannot be both public and protected at the same time.", self._src_info)
        if is_private and is_protected:
            raise CompilerException("Method cannot be both private and protected at the same time.", self._src_info)
        if not is_public and not is_private and not is_protected:
            raise CompilerException("Method must be either public, private or protected.", self._src_info)
        if is_public:
            modifier: Modifier = Modifier.PUBLIC
        elif is_private:
            modifier = Modifier.PRIVATE
        else:
            modifier = Modifier.PROTECTED
        return modifier


class VariableState(Enum):
    UNDECLARED = 0
    DECLARED = 1
    ASYNC_ASSIGNED = 2
    ASSIGNED = 3


class VariableStateTable:

    def __contains__(self, item: VariableName) -> bool:
        return item in self._state

    def __getitem__(self, item: VariableName) -> VariableState:
        if item not in self:
            raise InternalCompilerException(f"Variable {item.name} not found.", SourceInfo(""))
        return self._state[item]

    def __init__(self, path: str, workspace: str) -> None:
        self._path: str = path
        dir_list: list[str] = os.path.relpath(path, workspace).replace("-", "_").split(os.sep)
        self._namespace: list[NamespaceName] = list(map(lambda x: NamespaceName(x), dir_list))
        self._state: dict[VariableName, VariableState] = {}

    def __setitem__(self, key: VariableName, value: VariableState) -> None:
        self._state[key] = value

    @property
    def assigned_variables(self) -> list[VariableName]:
        return [k for k, v in self._state.items() if v == VariableState.ASSIGNED]

    def clear(self) -> None:
        self._state = {k: v for k, v in self._state.items() if k.is_global}

    @property
    def state(self) -> dict[VariableName, VariableState]:
        return self._state
