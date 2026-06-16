# -*- coding: utf-8 -*-
from utils import CompilerException, InternalCompilerException, SourceInfo, VIOLA_INIT
from utils.fsm import FSM, StateNode, Token

from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum
import os
from typing import Optional, Callable

CLOSURE_T: str = "viola$lang$function$Closure"
LISTENER_T: str = "viola$lang$thread$Listener"
LISTENER_INIT_FUNC: str = "viola$lang$thread$initListener"
EXCEPTION_T: str = "viola$lang$exception$Exception"
EXCEPTION_T_NAME: str = "viola$lang$exception$Exception"
TUPLE_T: str = "viola$collections$Tuple"


class SymbolType(Enum):
    """
    本类用于标记符号的类型。成员分别是：
    - 变量：1
    - 函数：2
    - 方法：3
    - 基本数据类型：4
    - 类：5
    - 枚举：6
    - 命名空间：7
    - 泛型符号：8
    - 泛型参数：9
    """
    VARIABLE = 1
    FUNCTION = 2
    METHOD = 3
    BASE_TYPE = 4
    CLASS = 5
    ENUM = 6
    NAMESPACE = 7
    GENERIC = 8
    GENERIC_ARG = 9


class Symbol(ABC):
    """
    符号类，用于标记一切名称，如标识符、命名空间等。
    """

    def __eq__(self, other: "Symbol") -> bool:
        """
        判断两个符号是否一致。
        """
        return self._name == other._name

    def __hash__(self) -> int:
        """
        获取符号的哈希值。
        """
        return hash(self._name)

    def __init__(self, name: str, kw_type: SymbolType) -> None:
        """
        初始化符号。
        name是符号名称，kw_type是符号类型。
        """
        self._name: str = name
        self._kw_type: SymbolType = kw_type

    def __str__(self) -> str:
        return self._name

    @property
    def kw_type(self) -> SymbolType:
        """
        获取符号类型。
        """
        return self._kw_type

    @property
    def name(self) -> str:
        """
        获取符号名称。
        """
        return self._name

    def rename(self, name: str) -> None:
        """
        重命名符号。
        """
        self._name = name


class Identifier(Symbol):
    """
    标识符类。标识符用于标记变量名、函数名、类名等等。
    """

    def __init__(self, name: str, kw_type: SymbolType) -> None:
        """
        创建标识符。
        """
        super().__init__(name, kw_type)


class NamespaceName(Identifier):
    """
    命名空间名称类。
    """

    def __init__(self, name: str) -> None:
        """
        创建命名空间。
        """
        super().__init__(name, SymbolType.NAMESPACE)


VIOLA_LANG: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("lang")]
VIOLA_COLLECTIONS: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("collections")]
GENERIC_CLASS: list[NamespaceName] = [NamespaceName("__generic"), NamespaceName("class")]
GENERIC_FUNC: list[NamespaceName] = [NamespaceName("__generic"), NamespaceName("function")]


class NamedSymbol(Symbol):
    """
    带命名空间的符号。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, kw_type: SymbolType) -> None:
        """
        创建带命名空间的符号。
        src_info: 源代码信息，用于在出错时定位源代码。
        namespace: 命名空间。
        name: 符号的名称。
        kw_type: 符号类型。
        """
        super().__init__("$".join(list(map(lambda n: n.name, namespace)) + [name]), kw_type)
        self._namespace: list[NamespaceName] = namespace
        self._self_name: str = name
        self._src_info: SourceInfo = deepcopy(src_info)

    def as_namespace(self) -> list[NamespaceName]:
        """
        将符号转换为命名空间。
        """
        return self._namespace + [NamespaceName(self._self_name)]

    @property
    def namespace(self) -> list[NamespaceName]:
        """
        获取符号的命名空间。
        """
        return self._namespace

    @property
    def src_info(self) -> SourceInfo:
        """
        获取源代码信息。
        """
        return self._src_info


class TypeName(NamedSymbol, ABC):
    """
    类型名称。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, kw_type: SymbolType) -> None:
        """
        创建类型。
        src_info: 源代码信息，用于在出错时定位源代码。
        namespace: 命名空间。
        name: 符号的名称。
        kw_type: 符号类型，SymbolType.BASE_TYPE或SymbolType.CLASS。
        """
        super().__init__(src_info, namespace, name, kw_type)
        self._raw_name: str = ".".join(list(map(lambda n: n.name, self._namespace)) + [name])
        self._self_name: str = name

    @property
    @abstractmethod
    def c_alloc_name(self) -> str:
        """
        获取这一类型（如果是类类型）指向的元素的数据类型。
        """
        pass

    @property
    @abstractmethod
    def c_assigning_name(self) -> str:
        """
        获取赋值时的类型名称，一般是self.c_calling_name + "*"。
        """
        pass

    @property
    @abstractmethod
    def c_calling_name(self) -> str:
        """
        获取调用时的类型名称。如果是类类型，则是指针类型；否则不是。
        """
        pass

    @abstractmethod
    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple["TypeName", ...]]], NamedSymbol]) -> bool:
        """
        检查此类型是否可转换为目标类型。
        target: 目标类型。
        symbol_dict: 符号表（self._symbol_table.symbols）。
        """
        pass

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return self

    @property
    @abstractmethod
    def is_generic(self) -> bool:
        """
        获取该类型是否为泛型类型。
        """
        pass

    @property
    def is_object(self) -> bool:
        """
        获取该类型是否为类类型。
        """
        return False

    @property
    def raw_name(self) -> str:
        """
        获取编译前的名称。
        """
        return self._raw_name

    @property
    def self_name(self) -> str:
        """
        获取无命名空间的名称。
        """
        return self._self_name

    @property
    @abstractmethod
    def short_name(self) -> str:
        """
        获取名称的缩写。
        """
        pass

    @property
    @abstractmethod
    def used_types(self) -> set["TypeName"]:
        pass


class AnyTypeName(TypeName):
    """
    任意数据类型。仅用于CExpr。
    """

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, VIOLA_LANG, "any", SymbolType.BASE_TYPE)

    @property
    def c_alloc_name(self) -> str:
        raise CompilerException("Can't allocate any type.", self._src_info)

    @property
    def c_assigning_name(self) -> str:
        raise CompilerException("Can't assign any type.", self._src_info)

    @property
    def c_calling_name(self) -> str:
        raise CompilerException("Can't call any type.", self._src_info)

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple["TypeName", ...]]], NamedSymbol]) -> bool:
        return True

    @property
    def is_generic(self) -> bool:
        return False

    @property
    def short_name(self) -> str:
        return "any"

    @property
    def used_types(self) -> set["TypeName"]:
        return set()


class BaseTypeName(TypeName):
    """
    基本数据类型。
    """

    def __init__(self, name: str, short_name: str) -> None:
        """
        创建基本数据类型。
        name: 类型名称。
        short_name: 类型名称的缩写。
        """
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

    @property
    def used_types(self) -> set["TypeName"]:
        return {self}


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

INT_TYPES: set[BaseTypeName] = {INT, INT8, INT16, INT32, INT64, UINT, UINT8, UINT16, UINT32, UINT64, SIZE_T}

__SHORT_TYPE_CONVERT_CHAIN: list[BaseTypeName] = [INT32, INT64, FLOAT64, FLOAT128]

__BASE_TYPE_CONVERT_CHAIN_BEGINNING: dict[BaseTypeName, int] = {
    BOOL: 0,
    INT: 0,
    INT8: 0,
    INT16: 0,
    INT32: 0,
    INT64: 1,
    UINT: 0,
    UINT8: 0,
    UINT16: 0,
    UINT32: 0,
    UINT64: 1,
    SIZE_T: 1,
    FLOAT: 2,
    FLOAT32: 2,
    FLOAT64: 2,
    FLOAT128: 3,
    DOUBLE: 2,
    LONG_DOUBLE: 3,
    VOID_PTR: 1
}


def base_type_degrade(t1: BaseTypeName, t2: BaseTypeName) -> BaseTypeName:
    """
    对基本数据类型进行退化，并获取退化后的类型。
    t1、t2: 需要退化的类型，将会寻找它们的退化链上的公共类型。
    return: 退化后的类型。
    """
    if t1 == t2:
        return t1
    t1_convert_chain_beginning: int = __BASE_TYPE_CONVERT_CHAIN_BEGINNING[t1]
    t2_convert_chain_beginning: int = __BASE_TYPE_CONVERT_CHAIN_BEGINNING[t2]
    target_type_index: int = max(t1_convert_chain_beginning, t2_convert_chain_beginning)
    return __SHORT_TYPE_CONVERT_CHAIN[target_type_index]


class GenericArgument(TypeName):
    """
    泛型参数类型。
    """

    def __init__(self, src_info: SourceInfo, name: str) -> None:
        """
        创建泛型参数类型。
        src_info: 源代码信息。
        name: 参数名。
        """
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

    def used_types(self) -> set["TypeName"]:
        return {self}


class VariableName(NamedSymbol):
    """
    变量名。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName) -> None:
        """
        创建变量名。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 变量的名称。
        t: 变量的类型。
        """
        super().__init__(src_info, namespace, name, SymbolType.VARIABLE)
        self._type: TypeName = t
        self._is_global: bool = False
        self._namespace: list[NamespaceName] = namespace
        self._self_name: str = name

    def as_ptr(self) -> str:
        """
        获取指向这一变量的指针。
        """
        return f"&{self.name}"

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "VariableName":
        """
        实例化这一变量（如果是泛型参数类型的话）。
        new_name: 新变量名。
        t: 泛型参数的实例化字典。
        """
        new_variable: VariableName = deepcopy(self)
        new_variable._type = new_variable._type.instantiation(t)
        return new_variable

    @property
    def is_global(self) -> bool:
        """
        获取这一变量是否为全局变量。
        """
        return self._is_global

    @property
    def is_object(self) -> bool:
        """
        获取这一变量是否为对象。
        """
        return isinstance(self._type, ClassName)

    @property
    def raw_name(self) -> str:
        """
        获取变量编译前的名称。
        """
        return f"{'.'.join(map(lambda n: n.name, self._namespace))}.{self._self_name}" if len(
            self._namespace) > 0 else self._self_name

    @property
    def self_name(self) -> str:
        """
        获取不带命名空间的变量名。
        """
        return self._self_name

    @property
    def type(self) -> TypeName:
        """
        获取变量的数据类型。
        """
        return self._type

    @property
    def type_name(self) -> str:
        """
        获取变量的数据类型名称。
        """
        return self._type.name

    @property
    def type_name_pair_assigning(self) -> str:
        """
        获取变量在赋值时的声明。
        """
        return f"{self._type.c_assigning_name}{self.name}"

    @property
    def type_name_pair_calling(self) -> str:
        """
        获取变量在调用时的声明。
        """
        return f"{self._type.c_calling_name}{self.name}"


class GlobalVariableName(VariableName):
    """
    全局变量名。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName) -> None:
        """
        创建变量名。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 变量的名称。
        t: 变量的类型。
        """
        super().__init__(src_info, namespace, name, t)
        self._is_global: bool = True


class Modifier(Enum):
    """
    访问权限。
    public: 任意位置都可以访问。
    protected: 只有该类型内及其子类可以访问。
    private: 只有该类型内可以访问。
    """
    PUBLIC = 0
    PROTECTED = 1
    PRIVATE = 2


class PropertyVariableName(VariableName):
    """
    属性变量名。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: TypeName, modifier: Modifier,
                 is_static: bool) -> None:
        """
        创建属性变量名。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 变量的名称。
        t: 变量的类型。
        modifier: 访问权限。
        is_static: 是否为静态。
        """
        super().__init__(src_info, namespace, name, t)
        self._modifier: Modifier = modifier
        self._is_static: bool = is_static

    @property
    def is_static(self) -> bool:
        """
        获取该属性是否为静态属性。
        """
        return self._is_static

    @property
    def modifier(self) -> Modifier:
        """
        获取该属性的访问权限级别。
        """
        return self._modifier

    @property
    def self_name_with_class(self) -> str:
        return self._namespace[-1].name + "$" + self._self_name


class LocalVariableName(VariableName):
    """
    临时变量名。
    """

    def __init__(self, src_info: SourceInfo, name: str, t: TypeName) -> None:
        """
        创建变量名。
        src_info: 源代码信息。
        name: 变量的名称。
        t: 变量的类型。
        """
        super().__init__(src_info, [], name, t)


class ClassName(TypeName):
    """
    类名称。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, parent: Optional[str],
                 is_abstract: bool, is_c_part: bool, generic_args: Optional[list[str]] = None) -> None:
        """
        创建类。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 类的名称。
        parent: 父类，如果为object则写None。
        is_abstract: 是否为抽象类。
        is_c_part: 是否为C结构体。
        generic_args: 泛型参数。
        """
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
        """
        添加方法声明。
        name: 方法的名称。
        method: 方法的声明。
        """
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
        """
        添加属性。
        src_info: 源代码信息。
        name: 属性的名称。
        type_name: 属性的类型。
        modifier: 属性的访问权限。
        is_static: 是否为静态属性。
        """
        if name in self._properties:
            raise CompilerException(f"Property {name} already exists.", self._src_info)
        self._properties[name] = PropertyVariableName(src_info, self.as_namespace(), name, type_name, modifier,
                                                      is_static)

    def add_property_object(self, name: str, prop: PropertyVariableName):
        """
        添加属性对象。
        name: 属性的名称。
        prop: 属性对象。
        """
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
        """
        获取泛型参数列表。如果无此列表，则返回None。
        """
        return list(map(lambda n: GenericArgument(self._src_info, n),
                        self._generic_args)) if self._generic_args is not None else None

    @property
    def generic_args_str(self) -> Optional[list[str]]:
        """
        获取泛型参数名称列表。如果无此列表，则返回None。
        """
        return self._generic_args

    @property
    def generic_methods(self) -> dict["MethodName", dict[tuple[TypeName, ...], "MethodName"]]:
        """
        获取所有泛型方法。
        """
        return self._generic_methods

    def get_generic_method(self, method: "MethodName", types: tuple[TypeName, ...]) -> "MethodName":
        """
        获取一个泛型方法。
        method: 泛型方法。
        types: 类型参数。
        return: 实例化后的泛型方法。
        """
        if method not in self._generic_methods:
            raise CompilerException(f"Method {method.name} is not generic.", method._src_info)
        if types not in self._generic_methods[method]:
            self._generic_methods[method][types] = method.instantiation_full(method.name, list(types))
        return self._generic_methods[method][types]

    def get_generic_method_by_name(self, name: str, types: tuple[TypeName, ...]) -> "MethodName":
        """
        按名称获取一个泛型方法。
        name: 泛型方法名称。
        types: 类型参数。
        return: 实例化后的泛型方法。
        """
        return self.get_generic_method(self._methods[name, ()], types)

    def has_method(self, name: str) -> bool:
        """
        检查是否存在方法。
        name: 需要检查的方法名称。
        """
        return name in map(lambda x: x[0], self._methods.keys())

    def instantiation_full(self, new_name: str, args: list[TypeName]) -> "ClassName":
        """
        完全实例化，也就是将所有泛型参数都替换为实际类型。
        new_name: 新的类名。
        args: 泛型参数的实参。
        """
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
        """
        获取该类是否为抽象类。
        """
        return self._is_abstract

    @property
    def is_c_part(self) -> bool:
        """
        获取该类是否为C结构体。
        """
        return self._is_c_part

    @property
    def is_generic(self) -> bool:
        return self._generic_args is not None and len(self._generic_args) > 0

    @property
    def is_object(self) -> bool:
        return True

    @property
    def methods(self) -> dict[tuple[str, tuple[TypeName, ...]], "MethodName"]:
        """
        获取所有方法。
        """
        return self._methods

    @property
    def parent(self) -> str:
        """
        获取父类名称。
        """
        return self._parent

    @property
    def properties(self) -> dict[str, PropertyVariableName]:
        """
        获取所有属性。
        """
        return self._properties

    def shared_parent(
            self,
            other: TypeName,
            symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]
    ) -> Optional["ClassName"]:
        """
        获取公共父类。
        """
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
    def used_types(self) -> set["TypeName"]:
        return {self}

    @property
    def vtable_name(self) -> str:
        """
        获取类表中对应的变量名。
        """
        return f"{self.name}$$vtable"


class ArrayTypeName(ClassName):
    """
    数组类型名称。
    """

    def __init__(self, src_info: SourceInfo, element_type: TypeName) -> None:
        """
        创建数组类型。
        src_info: 源代码信息。
        element_type: 元素类型。
        """
        super().__init__(src_info, element_type.namespace, element_type.self_name + "$array", None, False, False)
        self._element_type: TypeName = element_type

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if target.name == "object":
            return True
        if not isinstance(target, ArrayTypeName):
            return False
        return self._element_type.convertable_to(target.element_type, symbol_dict)

    @property
    def element_type(self) -> TypeName:
        """
        获取元素类型。
        """
        return self._element_type

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return ArrayTypeName(self._src_info, self.element_type.instantiation(real_types))

    @property
    def used_types(self) -> set["TypeName"]:
        return {self._element_type}


class EmptyArrayTypeName(ArrayTypeName):
    """
    空列表类型。
    """

    def __init__(self, src_info: SourceInfo) -> None:
        super().__init__(src_info, BaseTypeName("empty", "_"))

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        return super().convertable_to(target, symbol_dict) or isinstance(target, ArrayTypeName)

    @property
    def element_type(self) -> TypeName:
        raise CompilerException("Element type not specified", self._src_info)

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return self

    @property
    def used_types(self) -> set["TypeName"]:
        return set()


class TupleTypeName(ClassName):
    """
    元组类型名称。
    """

    def __init__(self, src_info: SourceInfo, types: list[TypeName]) -> None:
        super().__init__(src_info, VIOLA_COLLECTIONS, f"({', '.join(list(map(lambda t: t.name, types)))})", None,
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
    def name(self) -> str:
        return TUPLE_T

    @property
    def type_names(self) -> list[str]:
        """
        元组中所有类型的名称。
        """
        return list(map(lambda t: t.name, self.types))

    @property
    def types(self) -> list[TypeName]:
        """
        元组中的所有类型。
        """
        return self._type_args

    @property
    def used_types(self) -> set["TypeName"]:
        return set.union(*list(map(lambda t: t.used_types, self._type_args)))


class AutoTypeName(TypeName):
    """
    自动推断类型名称。
    """

    def __init__(self, src_info: SourceInfo) -> None:
        """
        创建自动推断类型名称。
        src_info: 源代码信息。
        """
        super().__init__(src_info, [], "auto", SymbolType.BASE_TYPE)
        self._real_type: Optional[TypeName] = None

    @property
    def c_alloc_name(self) -> str:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.c_alloc_name

    @property
    def c_assigning_name(self) -> str:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.c_assigning_name

    @property
    def c_calling_name(self) -> str:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.c_calling_name

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple["TypeName", ...]]], NamedSymbol]) -> bool:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.convertable_to(target, symbol_dict)

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.instantiation(real_types)

    @property
    def is_generic(self) -> bool:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.is_generic

    @property
    def is_object(self) -> bool:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.is_generic

    def set_real_type(self, real_type: TypeName) -> None:
        self._real_type = real_type

    @property
    def short_name(self) -> str:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.short_name

    @property
    def used_types(self) -> set["TypeName"]:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.used_types


class FunctionTypeName(TypeName):
    """
    函数类型名称。
    """

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName],
                 generic_args: Optional[list[str]] = None) -> None:
        """
        创建函数类型名称。
        src_info: 源代码信息。
        args: 参数类型。
        returns: 返回类型。
        generic_args: 泛型参数。
        """
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
        """
        获取参数类型。
        """
        return self._args

    @property
    def arg_names(self) -> list[str]:
        """
        获取参数类型的名称。
        """
        return list(map(lambda t: t.raw_name, self._args))

    def as_header(self, func_name: str) -> str:
        """
        转换为头文件中的声明。
        """
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        return f"void {func_name}({', '.join(filter(lambda x: x != "", [args_text, returns_text, LISTENER_T + ' *']))})"

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
        return f"void(*)({', '.join([args_text, returns_text, LISTENER_T + ' *'])})"

    def c_calling_name_with_var(self, var_name: str) -> str:
        """
        函数类型变量声明。
        """
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
        """
        获取泛型参数。
        """
        return list(map(lambda t: GenericArgument(self._src_info, t),
                        self._generic_args)) if self._generic_args is not None else None

    @property
    def generic_args_str(self) -> Optional[list[str]]:
        """
        获取泛型参数的名称。
        """
        return self._generic_args

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "FunctionTypeName":
        if self._generic_args is None:
            return self
        result = FunctionTypeName(
            self._src_info,
            list(map(lambda t: t.instantiation(real_types), self._args)),
            list(map(lambda t: t.instantiation(real_types), self._returns))
        )
        real_type_names: list[str] = list(map(lambda t: t.name, real_types))
        result._generic_args = list(filter(lambda t: t not in real_type_names, self._generic_args))
        return result

    def instantiation_func_t(self, real_types: list[TypeName]) -> "FunctionTypeName":
        """
        完全实例化。
        real_types: 类型实参。
        """
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
        """
        获取返回类型列表。
        """
        return self._returns

    @property
    def short_name(self) -> str:
        return "obj"

    @property
    def used_types(self) -> set["TypeName"]:
        return self._args_tuple.used_types | self._returns_tuple.used_types


class AsyncFuncTypeName(FunctionTypeName):
    """
    异步函数类型。
    """

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName],
                 generic_args: Optional[list[str]]) -> None:
        """
        创建异步函数类型名称。
        src_info: 源代码信息。
        args: 参数类型。
        returns: 返回类型。
        generic_args: 泛型参数。
        """
        super().__init__(src_info, args, returns, generic_args)

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
        """
        从同步函数类型创建异步函数类型。
        """
        return cls(function_type_name._src_info, function_type_name.args, function_type_name.returns,
                   function_type_name.generic_args_str)


class ClosureTypeName(FunctionTypeName):
    """
    闭包类型名称。
    """

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName]) -> None:
        """
        创建闭包类型名称。
        src_info: 源代码信息。
        args: 参数类型。
        returns: 返回类型。
        """
        super().__init__(src_info, args, returns)

    @property
    def c_alloc_name(self) -> str:
        return f"{CLOSURE_T} "

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
    """
    枚举名称。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, based_type: TypeName) -> None:
        """
        创建枚举名称。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 枚举类型名称。
        based_type: 枚举类型所基于的类型。
        """
        super().__init__(src_info, namespace, name, SymbolType.ENUM)
        self._based_type: TypeName = based_type

    @property
    def based_type(self) -> TypeName:
        """
        获取该枚举类型所基于的类型。
        """
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

    @property
    def used_types(self) -> set["TypeName"]:
        return {self._based_type}


class FunctionName(GlobalVariableName):
    """
    函数名称。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: FunctionTypeName,
                 arg_names: list[str], ret_names: list[str], export: bool, is_method: bool = False) -> None:
        """
        创建函数名称。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 函数名。
        t: 函数类型。
        arg_names: 参数名称。
        ret_names: 返回值名称。
        export: 是否导出。
        """
        if len(arg_names) != len(t.args):
            raise CompilerException("Invalid number of arguments.", self._src_info)
        super().__init__(src_info, namespace, name, t)
        self._arg_names: list[str] = arg_names
        self._ret_names: list[str] = ret_names
        self._export: bool = export
        self._default_params: dict[str, Optional[GlobalVariableName]] = {k: None for k in arg_names}
        self._arg_types: dict[str, TypeName] = {k: v for k, v in zip(arg_names, t.args)}
        self._kw_type = SymbolType.FUNCTION
        self._is_method = is_method

    @property
    def arg_names(self) -> list[str]:
        """
        获取参数名称。
        """
        return self._arg_names

    @property
    def arg_types(self) -> list[TypeName]:
        """
        获取参数类型。
        """
        return self.type.args

    @property
    def arg_types_dict(self) -> dict[str, TypeName]:
        """
        获取从参数名称到参数类型的字典。
        """
        return self._arg_types

    @property
    def args(self) -> list[LocalVariableName]:
        """
        获取参数列表。
        """
        return list(map(lambda t, x: LocalVariableName(self._src_info, x, t), self.type.args, self._arg_names))

    def as_async(self) -> "FunctionName":
        """
        转换为异步函数。
        """
        return AsyncFuncName.from_function_name(self)

    def as_declare(self) -> str:
        """
        转换为声明。
        """
        return self.type.as_header(self._name)

    def as_define_name(self) -> str:
        """
        转换为定义时的名称。
        """
        return "void " + self._name + "(" + ", ".join(
            list(map(lambda t, x: f"{t.name}${x}", self.type.args, self._arg_names)) + [
                f"{LISTENER_T} *listener"]) + ")"

    def as_define_name_raw(self) -> str:
        """
        转换为定义时的名称（不带$符号）。
        """
        return "void " + self._name + "(" + ", ".join(
            list(map(lambda t, x: f"{t.name}{x}", self.type.args, self._arg_names))
            + [f"{LISTENER_T} *listener"]
        ) + ")"

    def as_method(self, cls: ClassName) -> "MethodName":
        """
        转换为方法。
        """
        # noinspection PyUnresolvedReferences
        return cls.methods[self._name, tuple(self._type.args)]

    def as_sync(self) -> "FunctionName":
        """
        转换为同步函数。
        """
        return FunctionName(self._src_info, self._namespace, self._self_name + "$sync", self.type, self._arg_names,
                            self._ret_names, self._export)

    def as_tuple(self) -> GlobalVariableName:
        """
        转换为同步函数和异步函数组成的元组。
        """
        t = TupleTypeName(self._src_info, [self.type, self.type])
        name: str = f"{self._self_name}$tuple"
        return GlobalVariableName(self._src_info, self._namespace, name, t)

    def as_type_name_pair(self) -> str:
        """
        转换为变量声明。
        """
        self._type: FunctionTypeName
        # noinspection PyUnresolvedReferences
        return self._type.c_calling_name_with_var(self._name)

    @property
    def default_params(self) -> dict[str, Optional[GlobalVariableName]]:
        """
        获取参数默认值。
        """
        return self._default_params

    @property
    def export(self) -> bool:
        """
        获取该函数是否导出。
        """
        return self._export

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "FunctionName":
        new_type: FunctionTypeName = self.type.instantiation(t)
        result: FunctionName = FunctionName(self._src_info, GENERIC_FUNC, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    def instantiation_full(self, new_name: str, real_types: list[TypeName]) -> "FunctionName":
        """
        完全实例化这一函数声明。
        new_name: 函数的新名称。
        real_types: 类型实参。
        """
        new_type: FunctionTypeName = self.type.instantiation_func_t(real_types)
        result: FunctionName = FunctionName(self._src_info, GENERIC_FUNC, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    @property
    def is_method(self) -> bool:
        """
        获取该函数是否为方法。
        """
        return self._is_method

    @property
    def ret_names(self) -> list[str]:
        """
        获取该函数返回值的名称。
        """
        return self._ret_names

    @property
    def ret_types(self) -> list[TypeName]:
        """
        获取该函数返回值的类型。
        """
        return self.type.returns

    def set_default_params(self, default_param_names: list[str]) -> None:
        """
        将一部分参数设置为带有默认值的参数。
        """
        default_param_names: list[str] = list(filter(lambda x: x.strip() != "", default_param_names))
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
    """
    异步函数名。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, t: AsyncFuncTypeName,
                 arg_names: list[str], ret_names: list[str], export: bool) -> None:
        """
        创建函数名称。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 函数名。
        t: 函数类型。
        arg_names: 参数名称。
        ret_names: 返回值名称。
        export: 是否导出。
        """
        super().__init__(src_info, namespace, name, t, arg_names, ret_names, export)

    def as_define_name(self) -> str:
        return f"void {self._name}({TUPLE_T} *params, {TUPLE_T} *returns, {LISTENER_T} *listener)"

    def as_define_name_raw(self) -> str:
        return f"void {self._name}({TUPLE_T} *params, {TUPLE_T} *returns, {LISTENER_T} *listener)"

    @classmethod
    def from_function_name(cls, function_name: FunctionName) -> "AsyncFuncName":
        """
        从同步函数名创建。
        """
        return cls(function_name._src_info, function_name._namespace, function_name._self_name + "$async",
                   AsyncFuncTypeName.from_function_type_name(function_name.type), function_name._arg_names,
                   function_name._ret_names, function_name._export)


class MethodName(PropertyVariableName):
    """
    方法名称。
    """

    def __init__(self, src_info: SourceInfo, cls: ClassName, name: str, t: FunctionTypeName, is_abstract: bool,
                 is_static: bool, arg_names: list[str], ret_names: list[str], modifier: Modifier, export: bool) -> None:
        """
        创建方法名称。
        src_info: 源代码信息。
        cls: 方法所在的类。
        namespace: 命名空间。
        name: 方法名。
        t: 方法类型。
        is_abstract: 是否为抽象方法。
        is_static: 是否为静态方法。
        arg_names: 参数名称。
        ret_names: 返回值名称。
        modifier: 访问权限。
        export: 是否导出。
        """
        cls_generic_args: list[str] = cls.generic_args_str if cls.generic_args_str is not None else []
        t_generic_args: list[str] = t.generic_args_str if t.generic_args_str is not None else []
        if not is_static:
            arg_types: list[TypeName] = [cls] + t.args
            t = FunctionTypeName(src_info, arg_types, t.returns, cls_generic_args + t_generic_args)
            arg_names: list[str] = ["_this"] + arg_names
        function_name: FunctionName = FunctionName(src_info, [NamespaceName(cls.raw_name)], name, t, arg_names,
                                                   ret_names, export, True)
        super().__init__(src_info, cls.namespace, function_name.name, t, modifier, is_static)
        func_type_name: str = "$".join(list(map(lambda ty: ty.name, t.args)))
        self._cls: ClassName = cls
        self._is_abstract: bool = is_abstract
        self._modifier: Modifier = modifier
        self._method_name: str = name + "$" + func_type_name
        self._function_name: FunctionName = function_name
        self._function_name._kw_type = SymbolType.METHOD
        self._kw_type = SymbolType.METHOD

    def as_async(self) -> "MethodName":
        """
        转换为异步方法。
        """
        self._type: FunctionTypeName
        # noinspection PyTypeChecker
        return MethodName(self._src_info, self._cls, self._self_name + "$async",
                          AsyncFuncTypeName.from_function_type_name(self._type), self._is_abstract,
                          self._is_static, self._function_name.arg_names, self._function_name.ret_names, self._modifier,
                          self._function_name.export)

    def as_function(self) -> FunctionName:
        """
        转换为函数名。
        """
        return self._function_name

    @property
    def as_method_type_name_pair(self) -> str:
        """
        转换为变量声明。
        """
        return self._function_name.type.c_calling_name_with_var(self._name)

    def as_sync(self) -> "MethodName":
        """
        转换为同步方法。
        """
        # noinspection PyTypeChecker
        return MethodName(self._cls, self._self_name + "$sync", self.type, self._is_abstract, self._is_static,
                          self._function_name.arg_names, self._function_name.ret_names, self._modifier,
                          self._function_name.export, self._src_info)

    def as_tuple(self) -> GlobalVariableName:
        """
        转换为同步方法和异步方法组成的元组。
        """
        t = TupleTypeName(self._src_info, [self.type, self.type])
        name: str = f"{self._self_name}$tuple"
        return GlobalVariableName(self._src_info, self._cls.as_namespace(), name, t)

    @property
    def cls(self) -> ClassName:
        """
        获取方法所在的类。
        """
        return self._cls

    @property
    def default_params(self) -> dict[str, Optional[GlobalVariableName]]:
        """
        获取方法的默认参数。
        """
        return self._function_name.default_params

    @property
    def kw_type(self) -> SymbolType:
        return SymbolType.METHOD

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "MethodName":
        """
        创建实例化方法名称。
        new_name: 实例化后的方法名。
        t: 从类型形参到类型实参的字典。
        """
        result: MethodName = deepcopy(self)
        result._function_name = self._function_name.instantiation(new_name, t)
        result.rename(result._function_name.name)
        return result

    def instantiation_full(self, new_name: str, t: list[TypeName]) -> "MethodName":
        """
        完全实例化该方法。
        new_name: 实例化后的方法名。
        t: 类型实参。
        """
        result: MethodName = deepcopy(self)
        result._function_name = self._function_name.instantiation_full(new_name, t)
        result.rename(result._function_name.name)
        return result

    @property
    def is_abstract(self) -> bool:
        """
        获取该方法是否为抽象方法。
        """
        return self._is_abstract

    @property
    def is_generic(self) -> bool:
        """
        获取该方法是否为泛型方法。
        """
        return self._type.is_generic

    @property
    def method_name(self) -> str:
        """
        获取方法名。
        """
        return self._method_name

    def rebuild(self, func: FunctionName) -> "MethodName":
        """
        用另一个函数声明重建方法。
        """
        return MethodName(self._src_info, self._cls, self._self_name, func.type, self._is_abstract, self._is_static,
                          func.arg_names, func.ret_names, self._modifier, func.export)

    def set_cls(self, cls: ClassName, overloaded_times: int) -> "MethodName":
        """
        设置方法所在的类。
        """
        self._type: FunctionTypeName
        # noinspection PyTypeChecker
        return MethodName(self._src_info, cls, f"{self._self_name}$_{overloaded_times}", self._type,
                          self._is_abstract, self._is_static, self._function_name.arg_names,
                          self._function_name.ret_names, self._modifier, self._function_name.export)

    def set_default_params(self, default_param_names: list[str]) -> None:
        """
        设置具有默认值的参数。
        """
        self._function_name.set_default_params(default_param_names)

    @property
    def type(self) -> FunctionTypeName:
        return self._function_name.type


# 切片类型名称
SliceTypeName = ClassName(VIOLA_INIT, VIOLA_LANG, "slice", None, False, False)
SliceTypeName.add_property(VIOLA_INIT, "start", SIZE_T, Modifier.PUBLIC, False)
SliceTypeName.add_property(VIOLA_INIT, "end", SIZE_T, Modifier.PUBLIC, False)
SliceTypeName.add_property(VIOLA_INIT, "step", SIZE_T, Modifier.PUBLIC, False)

# 字符串类型名称
StringTypeName = ClassName(VIOLA_INIT, VIOLA_LANG, "string", None, False, False)
StringTypeName.add_property(VIOLA_INIT, "length", SIZE_T, Modifier.PUBLIC, False)
StringTypeName.add_property(VIOLA_INIT, "data", ArrayTypeName(VIOLA_INIT, UINT16), Modifier.PUBLIC, False)
StringTypeName.add_method(
    "__new__",
    MethodName(
        VIOLA_INIT,
        StringTypeName,
        "__new__",
        FunctionTypeName(
            VIOLA_INIT, [VOID_PTR], [StringTypeName]
        ),
        False,
        False,
        ["data"],
        ["this"],
        Modifier.PUBLIC,
        True
    )
)


class GenericTable:
    """
    泛型符号表。
    """

    def __contains__(self, item: tuple[FunctionName | ClassName, Optional[tuple[TypeName, ...]]]) -> bool:
        """
        检查一个实例化后的泛型对象是否存在于表中。
        item: 需要检查的实例化后的泛型对象。
        """
        key, types = item
        if key.kw_type == SymbolType.FUNCTION:
            if key in self._function_instances:
                return types in self._function_instances[key] or types is None
            return False
        if key.kw_type == SymbolType.CLASS:
            return key in self._class_instances and (types in self._class_instances[key] or types is None)
        raise InternalCompilerException("Unexpected item type.", self._source_info)

    def __getitem__(self, key: FunctionName | ClassName, types: tuple[TypeName, ...]) -> FunctionName | ClassName:
        """
        获取一个泛型对象。
        key: 泛型对象的声明。
        types: 类型实参。
        """
        if key.kw_type == SymbolType.FUNCTION:
            return self._function_instances[key][types]
        if key.kw_type == SymbolType.CLASS:
            return self._class_instances[key][types]
        raise InternalCompilerException("Unexpected item type.", self._source_info)

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName]) -> None:
        """
        创建泛型符号表。
        """
        self._namespace: list[NamespaceName] = namespace
        self._function_instances: dict[FunctionName, dict[tuple[TypeName, ...], FunctionName]] = {}
        self._class_instances: dict[ClassName, dict[tuple[TypeName, ...], ClassName]] = {}
        self._source_info: SourceInfo = src_info

    def add_cls_def(self, class_name: ClassName) -> None:
        """
        添加一个未实例化的泛型类。
        """
        if class_name in self._class_instances:
            raise InternalCompilerException("Class already exists.", self._source_info)
        self._class_instances[class_name] = {}

    def add_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> None:
        """
        添加一个已实例化的泛型类。
        """
        if class_name in self._class_instances:
            if t in self._class_instances[class_name]:
                raise InternalCompilerException("Class already exists.", self._source_info)
            self._class_instances[class_name][t] = class_name.instantiation_full(
                f"{class_name.name}$_{len(self._class_instances[class_name])}", list(t)
            )
        else:
            raise InternalCompilerException("Class does not exist.", self._source_info)

    def add_func_def(self, function_name: FunctionName) -> None:
        """
        添加一个未实例化的泛型函数。
        """
        if function_name in self._function_instances:
            raise InternalCompilerException("Function already exists.", self._source_info)
        self._function_instances[function_name] = {}

    def add_func_instance(self, function_name: FunctionName, t: tuple[TypeName, ...]) -> None:
        """
        添加一个已实例化的泛型函数。
        """
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
        """
        获取一个符号的所有实例化对象。
        """
        if isinstance(symbol, ClassName):
            instances = self._class_instances
        elif isinstance(symbol, FunctionName):
            instances = self._function_instances
        else:
            raise InternalCompilerException("Unexpected type of symbol.", src_info)
        return list(instances[symbol].keys())

    def get_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        """
        获取一个实例化的泛型类，如果不存在则创建一个。
        """
        if class_name in self._class_instances:
            if t in self._class_instances[class_name]:
                return self._class_instances[class_name][t]
            self.add_cls_instance(class_name, t)
            result = deepcopy(self._class_instances[class_name][t])
            if result.is_generic:
                del self._class_instances[class_name][t]
            return result
        raise CompilerException("Class does not exist.", self._source_info)

    def get_func_instance(self, function_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        """
        获取一个实例化的泛型函数，如果不存在则创建一个。
        """
        if function_name in self._function_instances:
            if t in self._function_instances[function_name]:
                return self._function_instances[function_name][t]
            self.add_func_instance(function_name, t)
            result = deepcopy(self._function_instances[function_name][t])
            if result.type.is_generic:
                del self._function_instances[function_name][t]
            return result
        raise CompilerException("Function does not exist.", self._source_info)


class _TypeNameLexer(FSM):

    def __init__(self) -> None:
        super().__init__()

    def lex(self, src_info: SourceInfo, type_string: str) -> list[Token]:
        text = type_string
        self.reset()
        tokens: list[Token] = []
        char_buf: list[str] = []
        current_loc: int = 0
        text_length: int = len(text)
        while current_loc < text_length:
            char: str = text[current_loc]
            token: Token = self._get_char_token(char)
            next_state = self.transfer(token)
            char_buf.append(char)
            if next_state is None:
                if self._current.output is None:
                    raise CompilerException(f"Unexpected character {char}", deepcopy(src_info))
                tokens.append(Token("".join(char_buf[:-1]), [self._current.output], 0))
                char_buf.clear()
                current_loc -= 1
                self.reset()
                self.transfer(token)
            else:
                self._current = next_state
            current_loc += 1
        tokens.append(Token("".join(char_buf), [self._current.output], 0))
        return tokens

    @staticmethod
    def _get_char_token(char: str) -> Token:
        type_list: list[str] = []
        if char.isdigit():
            type_list.append("DIGIT")
        if char.isalpha() or char == "_" or char == "$":
            type_list.append("LETTER")
        type_list.append(char)
        return Token(char, type_list)

    def _set_states_list(self) -> StateNode:
        first: StateNode = StateNode()
        first.add_transfer(" ", first)
        first = _TypeNameLexer.__identifier_states_list(first)
        first = _TypeNameLexer.__punctuation_states_list(first)
        return first

    @staticmethod
    def __identifier_states_list(first: StateNode) -> StateNode:
        identifier_state: StateNode = StateNode()
        first.add_transfer("LETTER", identifier_state)
        first.add_transfer("_", identifier_state)
        identifier_state.add_transfer("DIGIT", identifier_state)
        identifier_state.add_transfer("LETTER", identifier_state)
        identifier_state.add_transfer("_", identifier_state)
        identifier_state.set_output("IDENTIFIER")
        return first

    @staticmethod
    def __punctuation_states_list(first: StateNode) -> StateNode:
        sub: StateNode = StateNode()
        arrow: StateNode = StateNode()
        l_square_bracket: StateNode = StateNode()
        array_symbol: StateNode = StateNode()
        l_bracket: StateNode = StateNode()
        r_bracket: StateNode = StateNode()
        colon: StateNode = StateNode()
        double_colon: StateNode = StateNode()
        generic_start: StateNode = StateNode()
        r_angle_bracket: StateNode = StateNode()
        first.add_transfer("-", sub)
        first.add_transfer("[", l_square_bracket)
        first.add_transfer("(", l_bracket)
        first.add_transfer(")", r_bracket)
        first.add_transfer(":", colon)
        colon.add_transfer(":", double_colon)
        double_colon.add_transfer("<", generic_start)
        first.add_transfer(">", r_angle_bracket)
        sub.add_transfer(">", arrow)
        l_square_bracket.add_transfer("]", array_symbol)
        arrow.set_output("->")
        array_symbol.set_output("[]")
        l_bracket.set_output("(")
        r_bracket.set_output(")")
        generic_start.set_output("::<")
        r_angle_bracket.set_output(">")
        return first


class _TypeNameParser:
    """
    类型分析器，通过类型字符串得到具体类型。语法规则如下：
    type_name: IDENTIFIER
        | IDENTIFIER "<" type_name_list ">"
        | tuple_type_name
        | function_type_name
        | array_type_name
        ;
    function_type_name: tuple_type_name "->" tuple_type_name
        ;
    tuple_type_name: "(" type_name_list ")"
        ;
    array_type_name: type_name "[]"
        ;
    type_name_list: type_name
        | type_name "," type_name_list
        |
        ;
    消除左递归之后，type_name可以化为：
    type_name: IDENTIFIER type_name_2
        | IDENTIFIER "<" type_name_list ">" type_name_2
        | tuple_type_name type_name_2
        | function_type_name type_name_2
        ;
    type_name_2: "[]" type_name_2
        |
        ;
    """

    def __init__(self, real_type_getter: Callable[[str], TypeName], generic_table: GenericTable) -> None:
        self._tokens: list[Token] = []
        self._current: int = -1
        self._tokens_num: int = 0
        self._src_info: SourceInfo = VIOLA_INIT
        self._real_type_getter: Callable[[str], TypeName] = real_type_getter
        self._generic_table: GenericTable = generic_table
        self._lexer: _TypeNameLexer = _TypeNameLexer()

    def parse(self, src_info: SourceInfo, type_str: str) -> TypeName:
        self._src_info = src_info
        self._current: int = -1
        self._tokens = self._lexer.lex(src_info, type_str)
        self._tokens_num = len(self._tokens)
        result = self._parse_type_name()
        self._tokens.clear()
        return result

    def _back(self) -> None:
        self._current -= 1
        while self._current >= 0 and self._tokens[self._current].type == "_BLANK":
            self._current -= 1

    def _match_type(self, token_type: str) -> bool:
        return token_type in self._tokens[self._current].type

    def _next(self) -> None:
        self._current += 1
        while self._current < self._tokens_num and self._match_type("_BLANK"):
            self._current += 1

    def _parse_function_type_name(self) -> FunctionTypeName | TupleTypeName:
        args: TupleTypeName = self._parse_tuple_type_name()
        self._next()
        if self._match_type("->"):
            rets: TupleTypeName = self._parse_tuple_type_name()
            return FunctionTypeName(self._src_info, args.types, rets.types)
        self._back()
        return args

    def _parse_tuple_type_name(self) -> TupleTypeName:
        self._next()
        if not self._match_type("("):
            raise CompilerException(f"Unexpected token: {self._tokens[self._current]}", self._src_info)
        children_types: list[TypeName] = self._parse_type_list(")")
        return TupleTypeName(self._src_info, children_types)

    def _parse_type_list(self, end_symbol: str) -> list[TypeName]:
        self._next()
        children_types: list[TypeName] = []
        expect_comma: bool = False
        while True:
            if self._current >= self._tokens_num:
                raise CompilerException("Unexpected end of type", self._src_info)
            elif self._match_type(end_symbol):
                break
            elif self._match_type(",") and expect_comma:
                self._next()
                expect_comma = False
            elif not self._match_type(",") and not expect_comma:
                self._back()
                child = self._parse_type_name()
                children_types.append(child)
                expect_comma = True
            else:
                raise CompilerException(f"Unexpected token: {self._tokens[self._current]}", self._src_info)
        return children_types

    def _parse_type_name(self) -> TypeName:
        if self._real_type_getter is None:
            raise CompilerException("real_type_getter not set", self._src_info)
        self._next()
        if self._match_type("IDENTIFIER"):
            result: TypeName = self._real_type_getter(self._tokens[self._current].text)
            if self._current >= self._tokens_num - 1:
                return result
            self._next()
            if self._match_type("::<"):
                if not isinstance(result, ClassName):
                    raise CompilerException(f"Expected class type, but got {result.raw_name}", self._src_info)
                type_args: list[TypeName] = self._parse_type_list(">")
                result = self._generic_table.get_cls_instance(result, tuple(type_args))
        elif self._match_type("("):
            self._back()
            result = self._parse_function_type_name()
        else:
            raise CompilerException(f"Unexpected token: {self._tokens[self._current].text}", self._src_info)
        while self._current < self._tokens_num:
            if self._match_type("[]"):
                result = ArrayTypeName(self._src_info, result)
                self._next()
            else:
                raise CompilerException(f"Unexpected token: {self._tokens[self._current]}", self._src_info)
        return result


class SymbolTable:
    """
    符号表。
    """

    def __contains__(self, item: tuple[NamedSymbol | str, Optional[tuple[TypeName, ...]]]) -> bool:
        """
        判断一个符号是否存在于表中。
        """
        if isinstance(item[0], TypeName):
            return all(t in self.symbols for t in item[0].used_types)
        if isinstance(item[0], NamedSymbol):
            if item[0].name.startswith(self._namespace_name + "$"):
                return (item[0].name[len(self._namespace_name) + 1:], item[1]) in self.symbols
            return item[0] in self.symbols.values()
        if item[0].startswith(self._namespace_name + "$"):
            return (item[0][len(self._namespace_name + "$"):], item[1]) in self
        return item in self.symbols

    def __delitem__(self, key: tuple[str, Optional[tuple[TypeName, ...]]]) -> None:
        for i, sym in self._symbols:
            if key in sym:
                del self._symbols[i][key]
                break

    def __getitem__(self, items: tuple[str, Optional[tuple[TypeName, ...]]]) -> NamedSymbol:
        """
        获取一个符号。
        item: 符号名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        item: str = items[0]
        types: Optional[tuple[TypeName, ...]] = items[1]
        if item.startswith(self._namespace_name + "$"):
            return self[item[len(self._namespace_name + "$"):], types]
        if item.startswith("$tuple(") and item.endswith(")"):
            it = item[7:-1].split(", ")
            result = list(map(lambda x: self[x], it))
            # noinspection PyTypeChecker
            return TupleTypeName(self._src_info, result)
        if items not in self.symbols and types is None:
            result = self._type_name_parser.parse(self._src_info, item)
            for t in result.used_types:
                if (t.name, None) not in self:
                    raise CompilerException(f"Type {t.name} not found", self._src_info)
            return result
        return self.symbols[item, types]

    def __init__(self, src_path: str = "", workspace: str = "") -> None:
        """
        创建全局符号表。
        path: 源代码路径。
        workspace: 根目录。
        """
        self._symbols: list[dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]] = [{}]
        self._func_overload_times: dict[str, int] = {}
        if not src_path == "" and not workspace == "":
            src_path = os.path.splitext(src_path)[0]
            dir_list: list[str] = os.path.relpath(src_path, workspace).replace("-", "_").split(os.sep)
        else:
            dir_list = []
        self._namespace: list[NamespaceName] = list(map(lambda x: NamespaceName(x), dir_list))
        self._namespace_name: str = ".".join(map(lambda x: x.name, self._namespace))
        self._counter: int = 0
        self._class_info_list_name: str = "$".join(map(lambda x: x.name, self._namespace)) + "$classInfoList"
        self._src_info: SourceInfo = SourceInfo(src_path)
        self._generic_table: GenericTable = GenericTable(self._src_info, self._namespace)

        def __real_type_getter(name: str) -> TypeName:
            if (name, None) in self:
                return self[name, None]
            raise CompilerException(f"Type {name} not found.", self._src_info)

        self._type_name_parser: _TypeNameParser = _TypeNameParser(__real_type_getter, self._generic_table)

    def add(self, symbol: NamedSymbol, name: str, types: Optional[list[TypeName]]) -> None:
        """
        添加一个符号。
        symbol: 需要添加的符号。
        name: 查找符号时使用的名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        if types is not None:
            if (symbol.name, tuple(types)) in self.symbols:
                raise CompilerException(f"Symbol {name} already exists.", self._src_info)
        if (symbol.kw_type == SymbolType.FUNCTION or symbol.kw_type == SymbolType.METHOD) and types is None:
            raise InternalCompilerException("Function must have types.", self._src_info)
        elif symbol.kw_type != SymbolType.FUNCTION and symbol.kw_type != SymbolType.METHOD and types is not None:
            raise InternalCompilerException("Symbol must not have types.", self._src_info)
        self._symbols[-1][name, tuple(types) if types is not None else None] = symbol

    def add_scope(self) -> None:
        """
        添加一个作用域。
        """
        self._symbols.append({})

    def clear_temporaries(self) -> None:
        """
        清除临时符号。
        """
        self._symbols.pop()

    def contains_method(self, cls_name: str, name: str, args: list[str], kwargs: dict[str, str]) -> bool:
        """
        检查方法是否存在。
        cls_name: 方法所在的类型。
        name: 方法的名称。
        args: 方法的参数类型名称列表。
        kwargs: 方法的关键字参数类型字典。
        """
        return len(self.find_methods(cls_name, name, args, kwargs)) > 0

    def find_function(self, src_info: SourceInfo, name: str, args: list[str], kwargs: dict[str, str]) -> FunctionName:
        """
        搜索一个函数，如果找到多个则会报错。
        src_info: 源代码信息。
        name: 函数名。
        args: 参数类型名称列表。
        kwargs: 关键字参数类型名称列表。
        """
        results = self.find_functions(name, args, kwargs)
        if len(results) > 1:
            raise CompilerException("Ambiguous function symbol", src_info)
        if len(results) == 0:
            raise CompilerException("Function not found", src_info)
        return results[0]

    def find_functions(self, name: str, args: list[str], kwargs: dict[str, str], find_method: bool = False) -> (
            list[FunctionName] | list[MethodName]
    ):
        """
        搜索符合条件的所有函数和方法。
        src_info: 源代码信息。
        name: 函数名。
        args: 参数类型名称列表。
        kwargs: 关键字参数类型名称列表。
        find_method: 如果为True，则只搜索方法，否则只搜索普通函数。
        """
        # noinspection PyTypeChecker
        args_declaration: list[TypeName] = list(map(lambda x: self[x, None], args))
        # noinspection PyTypeChecker
        kwargs_declaration: dict[str, TypeName] = dict(map(lambda x: (x, self[kwargs[x], None]), kwargs.keys()))
        args_length: int = len(args_declaration)
        args_tuple: tuple[TypeName, ...] = tuple(args_declaration)
        matches: dict[tuple[str, tuple[TypeName, ...]], FunctionName | MethodName] = dict(
            filter(
                lambda x: (x[0][0] == name or x[1].name == name) and len(x[0][1]) >= args_length and all(
                    map(lambda i: args_tuple[i].convertable_to(x[0][1][i], self.symbols), range(args_length))
                ),
                self.symbols.items()
            )
        )
        matches = dict(filter(lambda x: all(y in x[1].arg_names for y in kwargs.keys()), matches.items()))
        matches = dict(filter(
            lambda x: all(x[1].arg_types_dict[y].convertable_to(kwargs_declaration[y])
                          for y in kwargs_declaration.keys()),
            matches.items()
        ))
        matches = dict(
            filter(
                lambda x: x[1].kw_type == (SymbolType.METHOD if find_method else SymbolType.FUNCTION),
                matches.items()
            )
        )
        matches = dict(map(
            lambda x: (x[0][0], x[1]) if not x[1].kw_type == SymbolType.FUNCTION else x, matches.items()
        ))
        return list(matches.values())

    def find_method(self, src_info: SourceInfo, cls_name: str, name: str, args: Optional[list[str]],
                    kwargs: Optional[dict[str, str]]) -> MethodName:
        """
        搜索一个方法，如果找到多个则会报错。
        src_info: 源代码信息。
        cls_name: 方法所在的类名。
        name: 方法名。
        args: 参数类型名称列表。
        kwargs: 关键字参数类型名称列表。
        """
        if args is None or kwargs is None:
            result = self.symbols[cls_name + "." + name, None]
            if not isinstance(result, MethodName):
                raise CompilerException("Method not found", src_info)
            return result
        results = self.find_methods(cls_name, name, args, kwargs)
        if len(results) > 1:
            raise CompilerException("Ambiguous method symbol", src_info)
        if len(results) == 0:
            raise CompilerException("Function not found", src_info)
        return results[0]

    def find_methods(self, cls_name: str, name: str, args: list[str], kwargs: dict[str, str]) -> list[MethodName]:
        """
        搜索符合条件的所有方法。
        src_info: 源代码信息。
        name: 函数名。
        args: 参数类型名称列表。
        kwargs: 关键字参数类型名称列表。
        """
        func_name: str = cls_name + "." + name
        return self.find_functions(func_name, args, kwargs, True)

    def get_all_to_instantiate_symbols(self, src_info: SourceInfo,
                                       symbol: ClassName | FunctionName) -> list[tuple[TypeName, ...]]:
        """
        获取符号的所有实例化对象。
        """
        return self._generic_table.get_all_to_instantiate_symbols(src_info, symbol)

    def get_counter(self) -> str:
        """
        获取匿名符号计数。
        """
        result: str = f"$$_{self._counter}"
        self._counter += 1
        return result

    def get_generic_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        """
        获取泛型类的实例化对象。
        """
        cls = self._generic_table.get_cls_instance(class_name, t)
        for method in cls.methods.values():
            if method.is_generic and method not in self._generic_table:
                self._generic_table.add_func_def(method.as_function())
        return cls

    def get_generic_func_instance(self, func_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        """
        获取泛型函数的实例化对象。
        """
        return self._generic_table.get_func_instance(func_name, t)

    def get_generic_instance(self, name: ClassName | FunctionName | MethodName,
                             t: tuple[TypeName, ...]) -> ClassName | FunctionName | MethodName:
        """
        获取任意泛型符号的实例化对象。
        """
        if isinstance(name, ClassName):
            return self.get_generic_cls_instance(name, t)
        if isinstance(name, FunctionName):
            return self.get_generic_func_instance(name, t)
        if isinstance(name, MethodName):
            return self.get_generic_method_instance(name, t)
        raise InternalCompilerException("Unexpected symbol type", name.src_info)

    def get_generic_method_instance(self, method_name: MethodName, t: tuple[TypeName, ...]) -> MethodName:
        """
        获取方法的实例化对象。
        """
        func = self._generic_table.get_func_instance(method_name.as_function(), t)
        return method_name.rebuild(func)

    @property
    def namespace(self) -> list[NamespaceName]:
        """
        获取符号表的命名空间。
        """
        return self._namespace

    @classmethod
    def read_from(cls, path: str) -> "SymbolTable":
        """
        读取符号表文件，并创建符号表。符号表文件格式如下：
        ```
        <源文件路径>
        <工作目录>
        ---
        <符号1>
        ---
        <符号2>
        ---
        <......>
        ```
        path: 符号表文件的路径。
        """
        with open(path, "r") as f:
            data: list[str] = f.read().split("---")[:-1]
        metadata: list[str] = data[0].split("\n")
        self = cls(metadata[0], metadata[1])
        for item in data[1:]:
            self._read_item(item)
        self.add(FunctionName(
            self._src_info,
            self.namespace,
            "__global__",
            FunctionTypeName(self._src_info, [], []),
            [],
            [],
            False
        ), "__global__", [])
        return self

    @property
    def symbols(self) -> dict[tuple[str, tuple[TypeName, ...] | None], NamedSymbol]:
        """
        获取符号字典。
        """
        result: dict[tuple[str, tuple[TypeName, ...] | None], NamedSymbol] = {}
        for d in self._symbols:
            result.update(d)
        return result

    def _read_item(self, item: str) -> None:
        """
        读取一个符号。每个符号的记载格式如下：
        ```
        <符号类型> <开始行>:<开始列>:<结束行>:<结束列>
        <符号信息>
        ```
        item: 符号的文本。
        """
        item_args: list[str] = item.split("\n")[1:]
        item_type: str = item_args[0].split(" ")[0]
        loc_str: list[str] = item_args[0].split(" ")[1].split(":")
        loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
        self._src_info.set_loc(*loc_tuple)
        item_args = item_args[1:]
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
        """
        读取基本数据类型。记载格式如下：
        ```
        <类型名称> <类型缩写>
        ```
        """
        item = item[0].split(" ")
        t = BaseTypeName(item[0], item[1])
        if (t, None) in self:
            raise CompilerException(f"Type {t.name} already exists.", self._src_info)
        self.add(t, item[0], None)

    def _read_func_decl(self, item: list[str]) -> None:
        """
        读取函数。记载格式如下：
        ```
        <函数名> [\"export\"]
        <泛型参数列表>
        <参数1类型>%<参数1名称>%<参数2类型>%<参数2名称>%<......>
        <返回1类型>%<返回1名称>%<返回2类型>%<返回2名称>%<......>
        <有默认值的参数1名称> <有默认值的参数2名称> <......>
        ```
        """
        item_name: str = item[0].split(" ")[0]
        export: bool = "export" in item[0].split(" ")[1:]
        generic_args: list[str] = item[1].split(" ")
        item_args: list[str] = item[2].split("%")
        item_returns: list[str] = item[3].split("%")
        item_default_args: list[str] = item[4].split(" ")
        # noinspection PyTypeChecker
        args = list(map(lambda arg: self[arg, None], item_args[::2])) if len(item_args) > 1 else []
        if any(map(lambda arg: not isinstance(arg, TypeName), args)):
            raise CompilerException("Function arguments must be types.", self._src_info)
        if (item_name, tuple(args)) in self:
            raise CompilerException(f"Function {item_name} already exists.", self._src_info)
        args: list[TypeName]
        # noinspection PyTypeChecker
        returns: list[TypeName] = list(map(lambda ret: self[ret], item_returns[::2])) if len(item_returns) > 1 else []
        if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
            raise CompilerException("Function returns must be types.", self._src_info)
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        if item_name not in self._func_overload_times:
            self._func_overload_times[item_name] = 0
        func = FunctionName(self._src_info, self.namespace,
                            f"{item_name}$_{self._func_overload_times[item_name]}", func_type,
                            item_args[1::2] if len(item_args) > 1 else [],
                            item_returns[1::2] if len(item_returns) > 1 else [], export)
        self._func_overload_times[item_name] += 1
        if self._func_overload_times[item_name] == 1:
            self.add(func, item_name, None)
        elif self._func_overload_times[item_name] == 2:
            del self[item_name, None]
        func.set_default_params(item_default_args)
        for k, v in func.default_params.items():
            if v is not None:
                self.add(v, item_name + "$default$" + k, None)
        self.add(func, item_name, args)

    def _read_global_var_decl(self, item: list[str]) -> None:
        """
        读取全局变量。记载格式如下：
        <变量类型>%<变量名>
        """
        item: list[str] = item[0].split("%")
        item_name: str = item[1]
        item_type: str = item[0]
        # noinspection PyTypeChecker
        self.add(GlobalVariableName(self.namespace, item_name, self[item_type], self._src_info), item_name, None)

    def _read_method_decl(self, item: list[str]) -> None:
        """
        读取方法。记载格式如下：
        <类名> <方法名> [\"abstract\"] [\"static\"] [\"export\"] [\"public\" | \"protected\" | \"private\"]
        <泛型参数列表>
        <参数1类型>%<参数1名称>%<参数2类型>%<参数2名称>%<......>
        <返回1类型>%<返回1名称>%<返回2类型>%<返回2名称>%<......>
        <有默认值的参数1名称> <有默认值的参数2名称> <......>
        """
        item_name: list[str] = item[0].split(" ")
        generic_args: list[str] = item[1].split(" ")
        cls_name: str = item_name[0]
        method_name: str = item_name[1]
        if (cls_name, None) not in self:
            raise CompilerException(f"Class {cls_name} not found.", self._src_info)
        cls = self[cls_name, None]
        if not isinstance(cls, ClassName):
            raise CompilerException(f"{cls_name} is not a class.", self._src_info)
        is_abstract: bool = "abstract" in item_name[2:]
        is_static: bool = "static" in item_name[2:]
        export: bool = "export" in item_name[2:]
        item_args: list[str] = item[2].split("%")
        item_returns: list[str] = item[3].split("%")
        item_default_args: list[str] = item[4].split(" ")
        # noinspection PyTypeChecker
        args = list(map(lambda arg: self[arg], item_args[::2])) if len(item_args) > 1 else []
        if any(map(lambda arg: not isinstance(arg, TypeName), args)):
            raise CompilerException("Function arguments must be types.", self._src_info)
        # noinspection PyTypeChecker
        returns = list(map(lambda ret: self[ret], item_returns[::2])) if len(item_returns) > 1 else []
        if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
            raise CompilerException("Function returns must be types.", self._src_info)
        args: list[TypeName]
        returns: list[TypeName]
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        modifier = self.__get_modifier(item_name[2:])
        if f"{cls.name}.{method_name}" not in self._func_overload_times:
            self._func_overload_times[f"{cls.name}.{method_name}"] = 0
        method = MethodName(
            self._src_info, cls, f"{method_name}$_{self._func_overload_times[f'{cls.name}.{method_name}']}",
            func_type, is_abstract, is_static, item_args[1::2] if len(item_args) > 1 else [],
            item_returns[1::2] if len(item_returns) > 1 else [], modifier, export
        )
        self._func_overload_times[f"{cls.name}.{method_name}"] += 1
        method.set_default_params(item_default_args)
        for k, v in method.default_params.items():
            if v is not None:
                self.add(v, f"{cls_name}.{method_name}$default$" + k, None)
        self.add(method, f"{cls_name}.{method_name}", args if is_static else [cls] + args)
        cls.add_method(method_name, method)

    def _read_class_decl(self, item: list[str]) -> None:
        """
        读取类。记载格式如下：
        <类名>%<父类名> [\"abstract\"] [\"c\"]
        <泛型参数列表>
        <开始行>:<开始列>:<结束行>:<结束列> <属性1类型>%<属性1名称> [\"static\"] [\"public\" | \"protected\" | \"private\"]
        <开始行>:<开始列>:<结束行>:<结束列> <属性2类型>%<属性2名称> [\"static\"] [\"public\" | \"protected\" | \"private\"]
        <......>
        END CLASS
        """
        cls_name: str = item[0].split(" ")[0].split("%")[0]
        if (cls_name, None) in self:
            raise CompilerException(f"Class {cls_name} already exists.", self._src_info)
        parent: Optional[ClassName] = None
        if item[0].split(" ")[1] != "object":
            parent_name = item[0].split(" ")[0].split("%")[1]
            # noinspection PyTypeChecker
            parent = self[parent_name]
            if not isinstance(parent, ClassName):
                raise CompilerException(f"Parent class {parent_name} is not a class.", self._src_info)
        else:
            parent_name = None
        is_abstract: bool = "abstract" in item[0].split(" ")[1:]
        is_c_part: bool = "c" in item[0].split(" ")[1:]
        generic_args: list[str] = item[1].split(" ")
        cls = ClassName(self._src_info, self.namespace, cls_name, parent_name, is_abstract, is_c_part, generic_args)
        if parent is not None:
            for name, prop in parent.properties.items():
                cls.add_property_object(name, prop)
            vtable: ClassName = ClassName(self._src_info, [], cls.name + "$$vtable", None, False,
                                          False)
            self.add(vtable, cls.name + ".$$vtable", None)
            cls.add_property(self._src_info, "$$vtable", vtable, Modifier.PUBLIC, True)
        item_loc: int = 2
        while not item[item_loc] == "END CLASS":
            item_text: list[str] = item[item_loc].split(" ")
            loc_str: list[str] = item_text[0].split(":")
            loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
            self._src_info.set_loc(*loc_tuple)
            type_name: str = item_text[1].split("%")[0]
            property_name: str = item_text[1].split("%")[0]
            # noinspection PyTypeChecker
            t: TypeName = self[type_name]
            cls.add_property(self._src_info, property_name, t, self.__get_modifier(item_text[2].split(" ")),
                             "static" in item_text[2].split(" "))
            if item_loc == len(item) - 1:
                raise CompilerException(f"Unexpected end of class {cls_name}", self._src_info)
            item_loc += 1
        if cls_name + ".__del__" not in self and not cls.is_c_part:
            cls.add_method(
                "__del__", MethodName(
                    self._src_info, cls, "__del__", FunctionTypeName(self._src_info, [], []),
                    False, False, [], [], Modifier.PUBLIC, False
                )
            )
        self.add(cls, cls_name, None)

    def _read_enum_decl(self, item: list[str]) -> None:
        """
        读取枚举类。记载格式如下：
        <枚举类名称>%<枚举类所基于的类名>
        """
        item_name: str = item[0].split("%")[0]
        based_type: str = item[0].split("%")[1]
        if based_type not in self:
            raise CompilerException(f"Based type {based_type} not found.", self._src_info)
        if (item_name, None) in self:
            raise CompilerException(f"Enum {item_name} already exists.", self._src_info)
        # noinspection PyTypeChecker
        enum = EnumName(self.namespace, item_name, self[based_type], self._src_info)
        self.add(enum, item_name, None)

    def __get_modifier(self, item: list[str]) -> Modifier:
        """
        获取访问权限级别。
        """
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
    """
    变量状态枚举类。
    UNDECLARED: 未声明。
    DECLARED: 已声明。
    ASYNC_ASSIGNED: 异步赋值。
    ASSIGNED: 已赋值。
    """
    UNDECLARED = 0
    DECLARED = 1
    ASYNC_ASSIGNED = 2
    ASSIGNED = 3


class VariableStateTable:
    """
    变量状态表。
    """

    def __contains__(self, item: VariableName) -> bool:
        """
        检查表是否包含某个变量。
        """
        return item in self.state

    def __getitem__(self, item: VariableName) -> VariableState:
        """
        获取变量的状态。
        """
        if item not in self:
            raise InternalCompilerException(f"Variable {item.name} not found.", SourceInfo(""))
        return self.state[item]

    def __init__(self, path: str = "", workspace: str = "") -> None:
        """
        创建表。
        path: 源代码目录。
        workspace: 根目录。
        """
        self._path: str = path
        dir_list: list[str] = os.path.relpath(path, workspace).replace("-", "_").split(os.sep)
        self._namespace: list[NamespaceName] = list(map(lambda x: NamespaceName(x), dir_list))
        self._state: list[dict[VariableName, VariableState]] = [{}]

    def __setitem__(self, key: VariableName, value: VariableState) -> None:
        """
        设置变量状态。
        """
        self._state[-1][key] = value

    def add_scope(self) -> None:
        """
        添加作用域。
        """
        self._state.append({})

    @property
    def assigned_variables(self) -> list[VariableName]:
        """
        获取所有已赋值变量。
        """
        return [k for k, v in self.state.items() if v == VariableState.ASSIGNED]

    def pop_scope(self) -> None:
        """
        弹出作用域。
        """
        self._state.pop()

    def set_assigned(self, variables: list[VariableName]) -> None:
        for variable in variables:
            if variable in self and self[variable] == VariableState.ASSIGNED:
                raise CompilerException(f"Variable {variable.name} is already assigned.", variable.src_info)
            self[variable] = VariableState.ASSIGNED

    def set_async_assigned(self, variables: list[VariableName]) -> None:
        for variable in variables:
            if variable in self and self[variable].value == VariableState.ASYNC_ASSIGNED.value:
                raise CompilerException(f"Variable {variable.name} is already async assigned.", variable.src_info)
            self[variable] = VariableState.ASYNC_ASSIGNED

    def set_declared(self, variables: list[VariableName]) -> None:
        for variable in variables:
            if variable in self and self[variable].value >= VariableState.DECLARED.value:
                raise CompilerException(f"Variable {variable.name} is already declared.", variable.src_info)
            self[variable] = VariableState.DECLARED

    @property
    def state(self) -> dict[VariableName, VariableState]:
        """
        获取变量状态字典。
        """
        result = {}
        for state in self._state:
            result.update(state)
        return result

    def update(self, other: dict[VariableName, VariableState]) -> None:
        """
        更新变量状态。
        """
        self._state[-1].update(other)
