# -*- coding: utf-8 -*-

from utils import CompilerException, InternalCompilerException, SourceInfo, VIOLA_INIT
from utils.fsm import FSM, StateNode, Token

from abc import ABC, abstractmethod
from copy import copy
from enum import Enum
import os
import re
from typing import Optional, Callable

CLOSURE_T: str = "viola$lang$function$Closure"
LISTENER_T: str = "viola$threads$Listener"
LISTENER_INIT_FUNC: str = "viola$threads$initListener"
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
        # deepcopy 期间 _name 可能尚未设置，回退到 id
        try:
            return hash(self._name)
        except AttributeError:
            return id(self)

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
VIOLA_LANG_EXCEPTION: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("lang"), NamespaceName("exception")]
VIOLA_COLLECTIONS: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("collections")]
VIOLA_IO: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("io")]


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
        self._src_info: SourceInfo = copy(src_info)
        self._raw_name: str = ".".join(list(map(lambda n: n.name, namespace)) + [name])

    def __str__(self) -> str:
        return self._raw_name

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
    def raw_name(self) -> str:
        """
        获取编译前的名称。
        """
        return self._raw_name

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
SIZE_T: BaseTypeName = UINT64

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

    def __hash__(self) -> int:
        return hash("$generic$" + self.name)

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
        # raise CompilerException("Generic argument is not instantiated.", self._src_info)
        return True

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

    @property
    def free_text(self) -> str:
        """
        获取这一变量的释放文本。
        """
        if not self.is_object:
            return ""
        if isinstance(self._type, TupleTypeName):
            # 所有元组类型共享同一C名称的析构函数
            return f"{TUPLE_T}$__del__({self.name}, listener); {self.name} = NULL;"
        if isinstance(self._type, ArrayTypeName):
            # 数组的C名称使用$$array形式
            return f"{self._type.c_alloc_name}$__del__$_0({self.name}, listener); {self.name} = NULL;"
        return f"{self._type.name}$__del__$_0({self.name}, listener); {self.name} = NULL;"

    def instantiation(self, new_name: str, t: dict["GenericArgument", TypeName]) -> "VariableName":
        """
        实例化这一变量（如果是泛型参数类型的话）。
        new_name: 新变量名。
        t: 泛型参数的实例化字典。
        """
        new_variable: VariableName = copy(self)
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
        return isinstance(self._type, ClassName) and self._type.is_object

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
        self._is_unsafe: bool = False

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
    def is_unsafe(self) -> bool:
        """
        获取该属性是否为非安全成员（允许重新赋值）。
        """
        return self._is_unsafe

    @property
    def self_name_with_class(self) -> str:
        return self._namespace[-1].name + "." + self._self_name


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

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, parent: Optional["ClassName"],
                 is_abstract: bool, is_c_part: bool, generic_args: Optional[list[str]] = None,
                 is_final: bool = False, is_wrapper: bool = False, is_unsafe: bool = False,
                 is_interface: bool = False) -> None:
        """
        创建类。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 类的名称。
        parent: 父类，如果为object则写None。
        is_abstract: 是否为抽象类。
        is_c_part: 是否为C结构体。
        generic_args: 泛型参数。
        is_final: 是否为最终类（不可继承）。
        is_wrapper: 是否为包装类（需要用户实现__del__）。
        is_unsafe: 是否所有对象均为非安全对象。
        is_interface: 是否为接口。
        """
        super().__init__(src_info, namespace, name, SymbolType.CLASS)
        self._parent: Optional["ClassName"] = parent
        self._children: list[str] = []
        self._properties: dict[str, PropertyVariableName] = {}
        self._methods: dict[tuple[str, tuple[TypeName, ...]], MethodName] = {}
        self._generic_methods: dict[MethodName, dict[tuple[TypeName, ...], MethodName]] = {}
        self._method_overload_times: dict[str, int] = {}
        self._is_abstract: bool = is_abstract
        self._is_c_part: bool = is_c_part
        self._generic_args: Optional[list[str]] = generic_args
        self._generic_real_types: list[TypeName] = []
        self._is_final: bool = is_final
        self._is_wrapper: bool = is_wrapper
        self._is_unsafe: bool = is_unsafe
        self._is_interface: bool = is_interface
        self._interfaces: list["ClassName"] = []
        self._export: bool = False

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
                     is_static: bool, is_unsafe: bool = False) -> None:
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
        prop: PropertyVariableName = PropertyVariableName(src_info, self.as_namespace(), name, type_name, modifier,
                                                          is_static)
        prop._is_unsafe = is_unsafe
        self._properties[name] = prop

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
            if target.name == self.name or target.self_name == "object":
                return True
            self_parent: Optional["ClassName"] = self._parent
            while self_parent is not None:
                if self_parent == target:
                    return True
                self_parent = self_parent.parent
            return False
        return False

    def instantiation(self, real_types: dict["GenericArgument", TypeName]) -> TypeName:
        # 检查是否有从原类到实例化类的映射（泛型实例化时添加）
        key = GenericArgument(self._src_info, self.name)
        if key in real_types:
            return real_types[key]
        return self

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
        if self.name == "viola$lang$Pointer":
            # 内置指针类型：实例化为原始指针
            return PointerTypeName(self._src_info, args[0])
        if self._generic_args is None:
            raise CompilerException("Class is not generic.", self._src_info)
        if len(args) != len(self._generic_args):
            raise CompilerException("Instantiation arguments number is not equal to generic arguments number.",
                                    self._src_info)
        generic_dict: dict[GenericArgument, TypeName] = dict(
            zip(map(lambda n: GenericArgument(self._src_info, n), self._generic_args), args)
        )
        result: ClassName = ClassName(self._src_info, [], new_name, self._parent,
                                      self._is_abstract, False, None)
        # 将原类自身加入替换字典，使方法中 this 的类型指向新的实例化类
        generic_dict[GenericArgument(self._src_info, self.name)] = result
        for name, prop in self._properties.items():
            # $refCount与$parent同样需要出现在实例的结构体布局中
            result.add_property_object(name, prop.instantiation("", generic_dict))
        for (name, _), method in self._methods.items():
            result.add_method(name, method.instantiation(f"{new_name}${method.name}", generic_dict))
        return result

    @property
    def is_final(self) -> bool:
        """
        获取该类是否为最终类（不可继承）。
        """
        return self._is_final

    @property
    def is_wrapper(self) -> bool:
        """
        获取该类是否为包装类（需要用户实现__del__）。
        """
        return self._is_wrapper

    @property
    def is_unsafe(self) -> bool:
        """
        获取该类的对象是否全部为非安全对象。
        """
        return self._is_unsafe

    @property
    def is_interface(self) -> bool:
        """
        获取该类是否为接口（不可实例化，方法均为抽象方法）。
        """
        return self._is_interface

    @property
    def export(self) -> bool:
        """
        获取该类是否导出为库。
        """
        return self._export

    @property
    def interfaces(self) -> list["ClassName"]:
        """
        获取该类实现的接口列表。
        """
        return self._interfaces

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
    def parent(self) -> Optional[ClassName]:
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
            other: TypeName
    ) -> Optional["ClassName"]:
        """
        获取公共父类。
        """
        if not isinstance(other, ClassName):
            return None
        self_parents: list[Optional[ClassName]] = [self]
        while self_parents[-1] is not None:
            self_parents.append(self.parent)
        self_parents.pop()
        other_parents: list[Optional[ClassName]] = [other]
        while other_parents[-1] is not None:
            other_parents.append(other.parent)
        other_parents.pop()
        cls: Optional[ClassName] = list(filter(lambda x: x in other_parents, self_parents))[0]
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


# 元组类型定义注册表：C类型名 -> 元组类型对象（typedef文本在输出头文件时惰性生成，
# 避免泛型参数未实例化时过早求值c_typedef_text）
_TUPLE_TYPE_DEFS: dict[str, "TupleTypeName"] = {}
# 函数类型定义注册表：C类型名 -> 函数类型对象（函数指针typedef，惰性生成）
_FUNCTION_TYPE_DEFS: dict[str, "FunctionTypeName"] = {}
# 数组类型定义注册表：C类型名 -> 元素类型（生成typedef与各方法的C实现）
_ARRAY_TYPE_DEFS: dict[str, TypeName] = {}

# 泛型函数实例化请求的全局注册表（按函数的C名 -> 类型参数元组集合）。
# 实例化请求发生在调用方模块，而泛型函数的定义位于其所在模块，
# 定义方实例化时需合并其他模块发起的请求。
_GENERIC_FUNC_INSTANCE_REQUESTS: dict[str, set[tuple[TypeName, ...]]] = {}






def _type_is_fully_concrete(t: TypeName) -> bool:
    """判断类型是否完全实例化（不含泛型参数、空数组或数组方法类占位类型）。"""
    if isinstance(t, GenericArgument):
        return False
    if isinstance(t, ArrayTypeName):
        return not isinstance(t, EmptyArrayTypeName) and _type_is_fully_concrete(t.element_type)
    if isinstance(t, FunctionTypeName):
        return all(_type_is_fully_concrete(x) for x in t.args + t.returns)
    if isinstance(t, TupleTypeName):
        return all(_type_is_fully_concrete(x) for x in t.types)
    if isinstance(t, ClassName):
        return not t.is_generic and not getattr(t, "_is_array_method_cls", False)
    if isinstance(t, BaseTypeName) and t.name == "viola$lang$empty":
        # 空数组字面量的占位元素类型
        return False
    return True

def register_tuple_type(t: "TupleTypeName") -> None:
    """注册元组类型，使编译器在模块头文件中生成其结构体定义。

    含未实例化类型（泛型参数或泛型类）的占位元组不注册：
    实例化后会以具体类型重新创建并注册。
    """
    if not all(_type_is_fully_concrete(e) for e in t.types):
        # 含未实例化类型的占位元组不注册
        return
    _TUPLE_TYPE_DEFS[t.name] = t


def register_function_type(t: "FunctionTypeName") -> None:
    """注册函数类型，使编译器在模块头文件中生成其函数指针typedef。

    含未实例化类型（泛型参数、泛型类或元素为泛型参数的数组）的占位函数类型不注册。
    """
    if not all(_type_is_fully_concrete(e) for e in t.args + t.returns):
        # 含未实例化类型的占位函数类型不注册
        return
    _FUNCTION_TYPE_DEFS[t.name] = t


def register_array_type(t: "ArrayTypeName") -> None:
    """注册数组类型，使编译器生成其结构体定义与方法实现。"""
    if isinstance(t, EmptyArrayTypeName):
        # 空数组字面量的元素类型由调用上下文推断，不注册
        return
    if isinstance(t.element_type, GenericArgument):
        # 泛型参数元素的数组（如T[]）在实例化后以具体元素类型重新注册
        return
    _ARRAY_TYPE_DEFS[t.c_alloc_name] = t.element_type


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
        super().__init__(src_info, [], element_type.name + "$$array", None, False, False)
        self._element_type: TypeName = element_type
        # 方法的C名称基于c_alloc_name（如viola$lang$string$$array），
        # 因为带[]的名称不是合法C标识符。方法实现由编译器按元素类型生成。
        c_cls: ClassName = ClassName(src_info, [], self.c_alloc_name, None, False, False)
        c_cls._is_array_method_cls = True
        self.add_method("__getitem__", MethodName(
            src_info, c_cls, "__getitem__", FunctionTypeName(
                src_info, [SIZE_T], [element_type]
            ), False, False, ["item"], ["element"], Modifier.PUBLIC, True, True
        ))
        self.add_method("__getitem__", MethodName(
            src_info, c_cls, "__getitem__", FunctionTypeName(
                src_info, [SliceTypeName], [self]
            ), False, False, ["s"], ["subarray"], Modifier.PUBLIC, True, True
        ))
        self.add_method("concat", MethodName(
            src_info, c_cls, "concat", FunctionTypeName(
                src_info, [self], [self]
            ), False, False, ["other"], ["result"], Modifier.PUBLIC, True, True
        ))
        self.add_method("append", MethodName(
            src_info, c_cls, "append", FunctionTypeName(
                src_info, [element_type], [self]
            ), False, False, ["newElement"], ["newArray"], Modifier.PUBLIC, True, True
        ))
        self.add_method("insert", MethodName(
            src_info, c_cls, "insert", FunctionTypeName(
                src_info, [INT64, element_type], [self]
            ), False, False, ["location", "newElement"], ["newArray"], Modifier.PUBLIC, True, True
        ))
        self.add_method("length", MethodName(
            src_info, c_cls, "length", FunctionTypeName(
                src_info, [], [SIZE_T]
            ), False, False, [], ["result"], Modifier.PUBLIC, True, True
        ))
        self.add_method("__setitem__", MethodName(
            src_info, c_cls, "__setitem__", FunctionTypeName(
                src_info, [SIZE_T, element_type], [self]
            ), False, False, ["index", "newElement"], ["newArray"], Modifier.PUBLIC, True, True
        ))
        self.add_method("__setitem__", MethodName(
            src_info, c_cls, "__setitem__", FunctionTypeName(
                src_info, [SliceTypeName, self], [self]
            ), False, False, ["s", "newSubarray"], ["newArray"], Modifier.PUBLIC, True, True
        ))
        self.add_method(
            "__del__", MethodName(
                src_info, c_cls, "__del__", FunctionTypeName(src_info, [], []), False,
                False, [], [], Modifier.PRIVATE, True, True
            )
        )
        register_array_type(self)

    @property
    def c_alloc_name(self) -> str:
        return f"{self._element_type.name}$$array"

    @property
    def c_assigning_name(self) -> str:
        return f"{self._element_type.name}$$array **"

    @property
    def c_calling_name(self) -> str:
        return f"{self._element_type.name}$$array *"

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


class PointerTypeName(ClassName):
    """
    指针类型名称（unsafe Pointer::<T>）。

    C语言层表示为原始指针 void *，由用户手动管理内存。
    """

    def __init__(self, src_info: SourceInfo, element_type: TypeName) -> None:
        super().__init__(src_info, VIOLA_LANG, "Pointer", None, False, False)
        self._element_type: TypeName = element_type
        self._is_unsafe = True
        # 名称按元素类型参数化，保持符号唯一性
        self.rename(f"viola$lang$Pointer${element_type.name}")

    @property
    def c_alloc_name(self) -> str:
        return "void *"

    @property
    def c_assigning_name(self) -> str:
        return "void **"

    @property
    def c_calling_name(self) -> str:
        return "void *"

    @property
    def element_type(self) -> TypeName:
        """
        获取指针指向的元素类型。
        """
        return self._element_type

    @property
    def is_object(self) -> bool:
        # 指针由用户手动管理内存，不参与自动释放
        return False

    def convertable_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, PointerTypeName):
            return True
        return False

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return PointerTypeName(self._src_info, self._element_type.instantiation(real_types))

    @property
    def used_types(self) -> set["TypeName"]:
        # 指针类型的组成类型是其指向的元素类型
        return {self._element_type}


class TupleTypeName(ClassName):
    """
    元组类型名称。

    C语言层的表示为按元素类型生成唯一名称的结构体（$为合法C标识符字符）：
        typedef struct {
            viola$lang$uint32 $refCount;
            viola$lang$ptr $parent;
            viola$lang$uint64 size;
            <元素0的c_calling_type> _0;
            ...
        } viola$collections$Tuple$<元素0名>$<元素1名>$...;
    结构体定义由编译器在模块头文件中生成（带include guard）。
    """

    def __init__(self, src_info: SourceInfo, types: list[TypeName]) -> None:
        c_name: str = TUPLE_T + "$" + "$".join(list(map(lambda t: t.name, types)))
        super().__init__(src_info, [], c_name, None, False, False)
        self._type_args: list[TypeName] = types
        # 注册到符号表，以便在头文件中生成结构体定义
        register_tuple_type(self)

    def has_method(self, name: str) -> bool:
        """所有元组类型共享同一C名称的析构方法，由运行库提供。"""
        if name == "__del__":
            return True
        return super().has_method(name)

    @property
    def methods(self) -> dict[tuple[str, tuple[TypeName, ...]], "MethodName"]:
        """获取方法表。元组的__del__方法为惰性共享的原生方法。"""
        result: dict[tuple[str, tuple[TypeName, ...]], MethodName] = dict(self._methods)
        if "__del__" not in map(lambda x: x[0], result.keys()):
            result[("__del__", ())] = _get_tuple_del_method(self._src_info)
        return result

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
    def c_typedef_text(self) -> str:
        """获取元组结构体的typedef文本（用于生成到模块头文件中）。

        第n个元素的字段名为$n：类类型为T *$n，基本类型为T $n。
        """
        members: str = "\n".join(list(map(
            lambda i, t: f"\t{t.c_calling_name} ${i};", range(len(self._type_args)), self._type_args
        )))
        if members != "":
            members += "\n"
        return "\n".join([
            f"#ifndef _VIOLA_TUPLE_T_{self.name}",
            f"#define _VIOLA_TUPLE_T_{self.name}",
            "typedef struct {",
            "\tviola$lang$uint32 $refCount;",
            "\tviola$lang$ptr $parent;",
            "\tviola$lang$uint64 size;",
            members,
            f"}} {self.name};",
            "#endif"
        ])

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

    C语言层的表示为按签名生成的唯一函数指针typedef（符合C语法）：
        typedef void (*viola$lang$function$S$<参数类型们>$$R$<返回类型们>)(
            <参数0的c_calling_type>, ..., <返回0的c_assigning_type>, ..., listener);
    返回值在C层通过“传入期望赋值的变量的指针，然后解引用赋值”实现，
    因此返回类型使用c_assigning_type（指向返回变量的指针类型）。
    typedef由编译器在模块头文件中生成（带include guard）。
    """

    _IS_ASYNC: bool = False

    def __init__(self, src_info: SourceInfo, args: list[TypeName], returns: list[TypeName],
                 generic_args: Optional[list[str]] = None) -> None:
        """
        创建函数类型名称。
        src_info: 源代码信息。
        args: 参数类型。
        returns: 返回类型。
        generic_args: 泛型参数。
        """
        super().__init__(src_info, [], self._make_c_name(args, returns), SymbolType.FUNCTION)
        self._args: list[TypeName] = args
        self._returns: list[TypeName] = returns
        self._args_tuple: TupleTypeName = TupleTypeName(SourceInfo(""), args)
        self._returns_tuple: TupleTypeName = TupleTypeName(SourceInfo(""), returns)
        self._generic_args: Optional[list[str]] = generic_args
        if isinstance(self._generic_args, list):
            self._generic_args = list(filter(lambda x: x != "", self._generic_args))
        register_function_type(self)

    @staticmethod
    def _c_safe_type_name(t: TypeName) -> str:
        """将类型名转换为合法的C标识符片段。"""
        return re.sub(r"[^A-Za-z0-9_$]", "$", t.name)

    @classmethod
    def _make_c_name(cls, args: list[TypeName], returns: list[TypeName]) -> str:
        """生成唯一的C类型名（按参数与返回类型签名）。"""
        if cls._IS_ASYNC:
            # 异步函数指针的参数为参数元组与返回元组
            prefix: str = "viola$lang$function$A$"
            args_part: str = TupleTypeName(VIOLA_INIT, args).c_alloc_name
            rets_part: str = TupleTypeName(VIOLA_INIT, returns).c_alloc_name
        else:
            prefix = "viola$lang$function$S$"
            args_part = "$".join(map(FunctionTypeName._c_safe_type_name, args))
            rets_part = "$".join(map(FunctionTypeName._c_safe_type_name, returns))
        return prefix + args_part + "$$R$" + rets_part

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

    @property
    def c_typedef_text(self) -> str:
        """获取函数指针typedef文本（用于生成到模块头文件中）。"""
        if len(self._args) == 0:
            args_text = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        params: str = ", ".join(filter(lambda x: x != "", [args_text, returns_text, LISTENER_T + " *"]))
        return "\n".join([
            f"#ifndef _VIOLA_FUNC_T_{self.name}",
            f"#define _VIOLA_FUNC_T_{self.name}",
            f"typedef void (*{self.name})({params});",
            "#endif"
        ])

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
        return f"{self.name} *"

    @property
    def c_calling_name(self) -> str:
        return f"{self.name} "

    def c_calling_name_with_var(self, var_name: str) -> str:
        """
        函数类型变量声明。
        """
        return f"{self.name} {var_name}"

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
        # 始终创建新类型，替换所有参数和返回值中的泛型参数
        new_args = list(map(lambda t: t.instantiation(real_types), self._args))
        new_returns = list(map(lambda t: t.instantiation(real_types), self._returns))
        if new_args == self._args and new_returns == self._returns:
            return self
        result = FunctionTypeName(self._src_info, new_args, new_returns)
        if self._generic_args is not None:
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
    def raw_name(self) -> str:
        return f"({', '.join(map(lambda t: t.raw_name, self._args))}) -> ({', '.join(map(lambda t: t.raw_name, self._returns))})"

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

    C语言层的表示为按签名生成的唯一函数指针typedef，
    参数为参数元组与返回元组（与编译器生成的异步包装函数一致）。
    """

    _IS_ASYNC: bool = True

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

    @property
    def _tuple_c_names(self) -> tuple[str, str]:
        """获取参数元组与返回元组的C类型名称。"""
        return (
            TupleTypeName(self._src_info, self._args).c_calling_name,
            TupleTypeName(self._src_info, self._returns).c_calling_name
        )

    @property
    def c_typedef_text(self) -> str:
        """获取异步函数指针typedef文本（参数为参数元组与返回元组）。"""
        args_tuple_name, returns_tuple_name = self._tuple_c_names
        params: str = ", ".join(filter(lambda x: x != "", [args_tuple_name, returns_tuple_name, LISTENER_T + " *"]))
        return "\n".join([
            f"#ifndef _VIOLA_FUNC_T_{self.name}",
            f"#define _VIOLA_FUNC_T_{self.name}",
            f"typedef void (*{self.name})({params});",
            "#endif"
        ])

    def as_header(self, func_name: str) -> str:
        args_tuple_name, returns_tuple_name = self._tuple_c_names
        return f"void {func_name}({args_tuple_name}, {returns_tuple_name}, {LISTENER_T} *)"

    @property
    def c_assigning_name(self) -> str:
        return f"{self.name} *"

    @property
    def c_calling_name(self) -> str:
        return f"{self.name} "

    def c_calling_name_with_var(self, var_name: str) -> str:
        return f"{self.name} {var_name}"

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
                 arg_names: list[str], ret_names: list[str], export: bool, is_method: bool = False,
                 is_native: bool = False) -> None:
        """
        创建函数名称。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 函数名。
        t: 函数类型。
        arg_names: 参数名称。
        ret_names: 返回值名称。
        export: 是否导出。
        is_method: 是否为方法。
        is_native: 是否为运行库提供的原生函数（编译器不生成其实现，调用时附加$sync后缀）。
        """
        super().__init__(src_info, namespace, name, t)
        if len(arg_names) != len(t.args):
            raise CompilerException("Invalid number of arguments.", self._src_info)
        self._arg_names: list[str] = arg_names
        self._ret_names: list[str] = ret_names
        self._export: bool = export
        self._default_params: dict[str, GlobalVariableName] = {}
        self._arg_types: dict[str, TypeName] = {k: v for k, v in zip(arg_names, t.args)}
        self._kw_type = SymbolType.FUNCTION
        self._is_method = is_method
        self._is_native: bool = is_native

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
        # 若类型参数含未实例化的泛型，返回注释占位
        for t in self.type.args:
            if isinstance(t, GenericArgument):
                return f"// GENERIC FUNCTION {self._name}"
        for t in self.type.returns:
            if isinstance(t, GenericArgument):
                return f"// GENERIC FUNCTION {self._name}"
        args_text = ", ".join(list(map(lambda t, a: f"{t.c_calling_name} {a}", self.type.args, self._arg_names)))
        returns_text = ", ".join(list(map(lambda t, r: f"{t.c_assigning_name} {r}", self.type.returns, self._ret_names)))
        return f"void {self.name}({', '.join(filter(lambda x: x != '', [args_text, returns_text, LISTENER_T + ' *listener']))})"

    def as_define_name(self) -> str:
        """
        转换为定义时的名称。
        定义与声明保持一致：参数为c_calling_name类型、返回值为c_assigning_name
        类型（输出指针）的形参，最后是listener。形参名与函数体内的引用一致。
        """
        args_text: str = ", ".join(list(map(
            lambda t, x: f"{t.c_calling_name} {x}", self.type.args, self._arg_names)))
        rets_text: str = ", ".join(list(map(
            lambda t, x: f"{t.c_assigning_name} {x}", self.type.returns, self._ret_names)))
        params: list[str] = list(filter(lambda x: x != "", [args_text, rets_text, f"{LISTENER_T} *listener"]))
        return "void " + self._name + "(" + ", ".join(params) + ")"

    def as_define_name_raw(self) -> str:
        """
        转换为定义时的名称（与as_define_name相同，保留以兼容cpart函数）。
        """
        return self.as_define_name()

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
    def default_params(self) -> dict[str, GlobalVariableName]:
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
        result: FunctionName = FunctionName(self._src_info, self._namespace, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    def instantiation_full(self, new_name: str, real_types: list[TypeName]) -> "FunctionName":
        """
        完全实例化这一函数声明。
        new_name: 函数的新名称。
        real_types: 类型实参。
        """
        new_type: FunctionTypeName = self.type.instantiation_func_t(real_types)
        result: FunctionName = FunctionName(self._src_info, self._namespace, new_name,
                                            new_type, self._arg_names, self._ret_names, self._export)
        return result

    @property
    def is_method(self) -> bool:
        """
        获取该函数是否为方法。
        """
        return self._is_method

    @property
    def is_native(self) -> bool:
        """
        获取该函数是否为运行库提供的原生函数。
        """
        return self._is_native

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
            raise CompilerException(f"{', '.join(not_in_args)} not in arguments.", self._src_info)
        for name in default_param_names:
            # noinspection PyUnresolvedReferences
            var_type: TypeName = self._type.args[self._arg_names.index(name)]
            self._default_params[name] = GlobalVariableName(self._src_info, self.as_namespace(), "$default$" + name, var_type)

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
                 arg_names: list[str], ret_names: list[str], export: bool, is_method: bool = False,
                 is_native: bool = False) -> None:
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
        super().__init__(src_info, namespace, name, t, arg_names, ret_names, export, is_method, is_native)

    def as_define_name(self) -> str:
        return self._tuple_define_name()

    def as_define_name_raw(self) -> str:
        return self._tuple_define_name()

    def as_declare(self) -> str:
        return self._tuple_define_name() + ";"

    def _tuple_define_name(self) -> str:
        """生成异步函数以元组为形参的定义（或声明）名称。"""
        args_tuple: TupleTypeName = TupleTypeName(self._src_info, self.type.args)
        returns_tuple: TupleTypeName = TupleTypeName(self._src_info, self.type.returns)
        return f"void {self._name}({args_tuple.c_calling_name} params, {returns_tuple.c_calling_name} returns, " \
               f"{LISTENER_T} *listener)"

    @classmethod
    def from_function_name(cls, function_name: FunctionName) -> "AsyncFuncName":
        """
        从同步函数名创建。
        """
        return cls(function_name._src_info, function_name._namespace, function_name.name + "$async",
                   AsyncFuncTypeName.from_function_type_name(function_name.type), function_name._arg_names,
                   function_name._ret_names, function_name._export, function_name._is_method,
                   function_name._is_native)


class MethodName(PropertyVariableName):
    """
    方法名称。
    """

    def __init__(self, src_info: SourceInfo, cls: ClassName, name: str, t: FunctionTypeName, is_abstract: bool,
                 is_static: bool, arg_names: list[str], ret_names: list[str], modifier: Modifier, export: bool,
                 is_native: bool = False, is_final: bool = False) -> None:
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
        is_native: 是否为运行库提供的原生方法。
        """
        cls_generic_args: list[str] = cls.generic_args_str if cls.generic_args_str is not None else []
        t_generic_args: list[str] = t.generic_args_str if t.generic_args_str is not None else []
        is_static = is_static or name == "__new__" or name.startswith("__new__$")
        if not is_static:
            arg_types: list[TypeName] = [cls] + t.args
            t = FunctionTypeName(src_info, arg_types, t.returns, cls_generic_args + t_generic_args)
            arg_names: list[str] = ["_this"] + arg_names
        function_name: FunctionName = FunctionName(src_info, [], name, t, arg_names,
                                                   ret_names, export, True, is_native)
        super().__init__(src_info, cls.as_namespace(), function_name.name, t, modifier, is_static)
        self._cls: ClassName = cls
        self._is_abstract: bool = is_abstract
        self._modifier: Modifier = modifier
        self._method_name: str = name
        self._is_final: bool = is_final
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
        转换为函数名（使用包含类命名空间的完整C名称）。
        """
        self._function_name.rename(self.name)
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
        result: MethodName = copy(self)
        result._function_name = self._function_name.instantiation(new_name, t)
        result._type = result._function_name.type
        result.rename(result._function_name.name)
        return result

    def instantiation_full(self, new_name: str, t: list[TypeName]) -> "MethodName":
        """
        完全实例化该方法。
        new_name: 实例化后的方法名。
        t: 类型实参。
        """
        result: MethodName = copy(self)
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
    def is_native(self) -> bool:
        """
        获取该方法是否为运行库提供的原生方法。
        """
        return self._function_name.is_native

    @property
    def is_final(self) -> bool:
        """
        获取该方法是否为最终方法（不可重写）。
        """
        return self._is_final

    @property
    def export(self) -> bool:
        """
        获取该方法是否导出（编译器自动生成的方法标记为True）。
        """
        return self._function_name.export

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
        return MethodName(self._src_info, cls, f"{self._self_name}$_{overloaded_times}",
                          self._type if self._is_static else FunctionTypeName(
                              self._src_info,
                              self._type.args if self._is_static else self._type.args[1:], self._type.returns
                          ),
                          self._is_abstract, self._is_static,
                          self._function_name.arg_names if self._is_static else self._function_name.arg_names[1:],
                          self._function_name.ret_names, self._modifier, self._function_name.export,
                          self._function_name.is_native,
                          self._is_final)

    def set_default_params(self, default_param_names: list[str]) -> None:
        """
        设置具有默认值的参数。
        """
        self._function_name.set_default_params(default_param_names)

    @property
    def type(self) -> FunctionTypeName:
        return self._function_name.type


Object: ClassName = ClassName(VIOLA_INIT, VIOLA_LANG, "object", None, False, False)
object_destructor: MethodName = MethodName(
    VIOLA_INIT,
    Object,
    "__del__",
    FunctionTypeName(
        VIOLA_INIT,
        [],
        [],
        []
    ),
    False,
    False,
    [],
    [],
    Modifier.PUBLIC,
    True
)

# 所有元组类型共享的原生析构方法（惰性创建，避免与类型定义的循环依赖）
_TUPLE_DEL_METHOD: Optional[MethodName] = None


def _get_tuple_del_method(src_info: SourceInfo) -> MethodName:
    """获取（必要时创建）元组共享的原生析构方法。C名称为viola$collections$Tuple$__del__。"""
    global _TUPLE_DEL_METHOD
    if _TUPLE_DEL_METHOD is None:
        shared_cls: ClassName = ClassName(src_info, VIOLA_COLLECTIONS, "Tuple", None, False, False)
        _TUPLE_DEL_METHOD = MethodName(
            src_info, shared_cls, "__del__", FunctionTypeName(src_info, [], []), False,
            False, [], [], Modifier.PRIVATE, True, True
        )
    return _TUPLE_DEL_METHOD
Object.add_property(VIOLA_INIT, "$refCount", UINT32, Modifier.PRIVATE, False)
Object.add_property(VIOLA_INIT, "$parent", VOID_PTR, Modifier.PRIVATE, False)
Object.add_method("__del__", object_destructor)


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
        True,
        True
    )
)
StringTypeName.add_method(
    "__del__", MethodName(
        VIOLA_INIT, StringTypeName, "__del__", FunctionTypeName(VIOLA_INIT, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
)


def _add_native_method(
        cls: ClassName, name: str, arg_types: list[TypeName], ret_types: list[TypeName],
        arg_names: list[str], ret_names: list[str], modifier: Modifier = Modifier.PUBLIC
) -> None:
    """向内置类注册一个原生方法（实现由运行库提供）。"""
    cls.add_method(name, MethodName(
        VIOLA_INIT, cls, name, FunctionTypeName(VIOLA_INIT, arg_types, ret_types), False,
        False, arg_names, ret_names, modifier, True, True
    ))


# 字符串方法（0.1运行库，实现于viola_libs/viola/lang/string.c）。
# 注册顺序决定C名称中的重载序号（$_0、$_1等）。
_add_native_method(StringTypeName, "__add__", [StringTypeName], [StringTypeName], ["s"], ["result"])
_add_native_method(StringTypeName, "__eq__", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "__getitem__", [INT64], [StringTypeName], ["index"], ["ch"])
_add_native_method(StringTypeName, "__getitem__", [SliceTypeName], [StringTypeName], ["s"], ["result"])
_add_native_method(StringTypeName, "__mul__", [UINT64], [StringTypeName], ["times"], ["result"])
_add_native_method(StringTypeName, "__ne__", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "__rmul__", [UINT64], [StringTypeName], ["times"], ["result"])
_add_native_method(StringTypeName, "concat", [StringTypeName], [StringTypeName], ["s"], ["result"])
_add_native_method(StringTypeName, "endswith", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "endsWith", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "isascii", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "join", [ArrayTypeName(VIOLA_INIT, StringTypeName)], [StringTypeName],
                   ["s"], ["result"])
_add_native_method(StringTypeName, "length", [], [SIZE_T], [], ["result"])
_add_native_method(StringTypeName, "lower", [], [StringTypeName], [], ["result"])
_add_native_method(StringTypeName, "replace", [StringTypeName, StringTypeName], [StringTypeName],
                   ["old", "new"], ["result"])
_add_native_method(StringTypeName, "repeat", [UINT64], [StringTypeName], ["times"], ["result"])
_add_native_method(StringTypeName, "rsplit", [StringTypeName], [ArrayTypeName(VIOLA_INIT, StringTypeName)],
                   ["s"], ["results"])
_add_native_method(StringTypeName, "rsplit", [StringTypeName, UINT64], [ArrayTypeName(VIOLA_INIT, StringTypeName)],
                   ["s", "maxsplit"], ["results"])
_add_native_method(StringTypeName, "slice", [INT64, INT64], [StringTypeName], ["start", "end"], ["result"])
_add_native_method(StringTypeName, "split", [StringTypeName], [ArrayTypeName(VIOLA_INIT, StringTypeName)],
                   ["s"], ["results"])
_add_native_method(StringTypeName, "split", [StringTypeName, UINT64], [ArrayTypeName(VIOLA_INIT, StringTypeName)],
                   ["s", "maxsplit"], ["results"])
_add_native_method(StringTypeName, "startswith", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "startsWith", [StringTypeName], [BOOL], ["s"], ["result"])
_add_native_method(StringTypeName, "unicode", [], [ArrayTypeName(VIOLA_INIT, UINT16)], [], ["result"])
_add_native_method(StringTypeName, "upper", [], [StringTypeName], [], ["result"])

SliceTypeName.add_method(
    "__del__", MethodName(
        VIOLA_INIT, SliceTypeName, "__del__", FunctionTypeName(VIOLA_INIT, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
)

ExceptionTypeName = ClassName(VIOLA_INIT, VIOLA_LANG_EXCEPTION, "Exception", None, False, False)
# 与运行库viola$lang$exception$Exception结构体一致的字段
ExceptionTypeName.add_property(VIOLA_INIT, "$refCount", UINT32, Modifier.PRIVATE, False)
ExceptionTypeName.add_property(VIOLA_INIT, "$parent", VOID_PTR, Modifier.PRIVATE, False)
ExceptionTypeName.add_property(VIOLA_INIT, "$$vtable", VOID_PTR, Modifier.PUBLIC, False)
ExceptionTypeName.add_property(VIOLA_INIT, "message", StringTypeName, Modifier.PUBLIC, False)
ExceptionTypeName.add_method(
    "__new__",
    MethodName(
        VIOLA_INIT,
        ExceptionTypeName,
        "__new__",
        FunctionTypeName(
            VIOLA_INIT, [StringTypeName], [ExceptionTypeName]
        ),
        False,
        False,
        ["message"],
        ["this"],
        Modifier.PUBLIC,
        True,
        True
    )
)
_exception_what = MethodName(
    VIOLA_INIT,
    ExceptionTypeName,
    "what",
    FunctionTypeName(
        VIOLA_INIT, [], [StringTypeName]
    ),
    False,
    False,
    [],
    ["result"],
    Modifier.PUBLIC,
    True,
    True
)
ExceptionTypeName.add_method(
    "what",
    _exception_what
)
ExceptionTypeName.add_method(
    "__del__", MethodName(
        VIOLA_INIT, ExceptionTypeName, "__del__", FunctionTypeName(VIOLA_INIT, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
)
# 内置泛型指针类型（unsafe Pointer::<T>），C层表示为void *
PointerGenericClassName: ClassName = ClassName(VIOLA_INIT, VIOLA_LANG, "Pointer", None, False, False, ["T"])

_perror = FunctionName(
    VIOLA_INIT,
    VIOLA_IO,
    "perror",
    FunctionTypeName(VIOLA_INIT, [StringTypeName], []),
    ["text"],
    [],
    True,
    False,
    True
)
_print = FunctionName(
    VIOLA_INIT, VIOLA_IO, "print", FunctionTypeName(VIOLA_INIT, [StringTypeName], []),
    ["text"], [], True, False, True
)
_input = FunctionName(
    VIOLA_INIT, VIOLA_IO, "input", FunctionTypeName(VIOLA_INIT, [], [StringTypeName]),
    [], ["result"], True, False, True
)

# 文件类型与文件操作（0.1运行库，实现于viola_libs/viola/io/file.c）
FileTypeName = ClassName(VIOLA_INIT, VIOLA_IO, "file", None, False, False)
FileTypeName.add_method(
    "__del__", MethodName(
        VIOLA_INIT, FileTypeName, "__del__", FunctionTypeName(VIOLA_INIT, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
)
_open = FunctionName(
    VIOLA_INIT, VIOLA_IO, "open",
    FunctionTypeName(VIOLA_INIT, [StringTypeName, StringTypeName, StringTypeName], [FileTypeName]),
    ["path", "mode", "encoding"], ["f"], True, False, True
)
# open的默认参数：mode = "r"，encoding = "utf-8"。
# 原生函数的默认参数全局变量由运行库viola_libs/viola/io/file.c定义
_open.set_default_params(["mode", "encoding"])
_read = FunctionName(
    VIOLA_INIT, VIOLA_IO, "read",
    FunctionTypeName(VIOLA_INIT, [FileTypeName], [StringTypeName]),
    ["f"], ["result"], True, False, True
)
_read_bytes = FunctionName(
    VIOLA_INIT, VIOLA_IO, "readBytes",
    FunctionTypeName(VIOLA_INIT, [FileTypeName], [ArrayTypeName(VIOLA_INIT, UINT8)]),
    ["f"], ["result"], True, False, True
)
_write = FunctionName(
    VIOLA_INIT, VIOLA_IO, "write",
    FunctionTypeName(VIOLA_INIT, [FileTypeName, StringTypeName], []),
    ["f", "content"], [], True, False, True
)
_write_bytes = FunctionName(
    VIOLA_INIT, VIOLA_IO, "writeBytes",
    FunctionTypeName(VIOLA_INIT, [FileTypeName, ArrayTypeName(VIOLA_INIT, UINT8)], []),
    ["f", "content"], [], True, False, True
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
                f"{class_name.self_name}__{len(self._class_instances[class_name])}", list(t)
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
                f"{function_name.self_name}$_{len(self._function_instances[function_name])}", list(t)
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
        result: list[tuple[TypeName, ...]] = []
        if symbol in instances:
            for t in instances[symbol].keys():
                # 泛型函数体内的递归调用（类型参数仍为泛型参数）不产生具体实例
                if all(not isinstance(x, GenericArgument) for x in t):
                    result.append(t)
        if isinstance(symbol, FunctionName):
            # 合并其他模块发起的实例化请求（调用发生在调用方模块）
            for t in _GENERIC_FUNC_INSTANCE_REQUESTS.get(symbol.name, set()):
                if all(not isinstance(x, GenericArgument) for x in t) and t not in result:
                    result.append(t)
        return result

    def get_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        """
        获取一个实例化的泛型类，如果不存在则创建一个。
        """
        if class_name in self._class_instances:
            if t in self._class_instances[class_name]:
                return self._class_instances[class_name][t]
            self.add_cls_instance(class_name, t)
            result = copy(self._class_instances[class_name][t])
            if result.is_generic:
                del self._class_instances[class_name][t]
            return result
        raise CompilerException(f"Class {class_name.raw_name} does not exist.", self._source_info)

    def get_func_instance(self, function_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        """
        获取一个实例化的泛型函数，如果不存在则创建一个。
        """
        if function_name in self._function_instances:
            if t in self._function_instances[function_name]:
                return self._function_instances[function_name][t]
            self.add_func_instance(function_name, t)
            result = copy(self._function_instances[function_name][t])
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
                    raise CompilerException(f"Unexpected character {char}", copy(src_info))
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
        comma: StateNode = StateNode()
        first.add_transfer("-", sub)
        first.add_transfer("[", l_square_bracket)
        first.add_transfer("(", l_bracket)
        first.add_transfer(")", r_bracket)
        first.add_transfer(":", colon)
        first.add_transfer(",", comma)
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
        comma.set_output(",")
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

    def __init__(self, real_type_getter: Callable[[str], Optional[TypeName]], generic_table: GenericTable) -> None:
        self._tokens: list[Token] = []
        self._current: int = -1
        self._tokens_num: int = 0
        self._src_info: SourceInfo = VIOLA_INIT
        self._real_type_getter: Callable[[str], Optional[TypeName]] = real_type_getter
        self._generic_table: GenericTable = generic_table
        self._lexer: _TypeNameLexer = _TypeNameLexer()

    def parse(self, src_info: SourceInfo, type_str: str) -> Optional[TypeName]:
        if type_str.strip() == "void":
            # void类型等效于()类型（空元组）
            return TupleTypeName(src_info, [])
        self._src_info = src_info
        self._current: int = -1
        self._tokens = self._lexer.lex(src_info, type_str) + [Token("", ["_EOF"], src_info)]
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

    def _parse_function_type_name(self) -> Optional[FunctionTypeName | TupleTypeName]:
        args = self._parse_tuple_type_name()
        if args is None:
            return None
        self._next()
        if self._match_type("->"):
            rets = self._parse_tuple_type_name()
            if rets is None:
                return None
            return FunctionTypeName(self._src_info, args.types, rets.types)
        self._back()
        return args

    def _parse_tuple_type_name(self) -> Optional[TupleTypeName]:
        self._next()
        if not self._match_type("("):
            raise CompilerException(f"Unexpected token: {self._tokens[self._current]}", self._src_info)
        children_types: Optional[list[TypeName]] = self._parse_type_list(")")
        if children_types is None:
            return None
        return TupleTypeName(self._src_info, children_types)

    def _parse_type_list(self, end_symbol: str) -> Optional[list[TypeName]]:
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
                if child is None:
                    return None
                children_types.append(child)
                expect_comma = True
                # 前进到子类型之后（逗号或结束符号）
                self._next()
            else:
                return None
        return children_types

    def _parse_type_name(self) -> Optional[TypeName]:
        if self._real_type_getter is None:
            raise CompilerException("real_type_getter not set", self._src_info)
        self._next()
        if self._match_type("IDENTIFIER"):
            result: Optional[TypeName] = self._real_type_getter(self._tokens[self._current].text)
            if result is None:
                return None
        elif self._match_type("("):
            self._back()
            result = self._parse_function_type_name()
            if result is None:
                return None
        else:
            return None
        # 数组后缀（[]）与泛型参数（::<...>）可以依次出现
        while self._current < self._tokens_num - 1:
            self._next()
            if self._match_type("[]"):
                result = ArrayTypeName(self._src_info, result)
            elif self._match_type("::<"):
                if not isinstance(result, ClassName):
                    return None
                type_args: Optional[list[TypeName]] = self._parse_type_list(">")
                if type_args is None:
                    return None
                result = self._generic_table.get_cls_instance(result, tuple(type_args))
            else:
                self._back()
                break
        return result


class SymbolTable:
    """
    符号表。
    """
    _NAMESPACES_WITHOUT_IMPORT: tuple[list[NamespaceName], ...] = (
        VIOLA_LANG_EXCEPTION,
        VIOLA_LANG,
        VIOLA_IO,
        VIOLA_COLLECTIONS
    )
    # viola.math绑定：一元与二元浮点函数（名称，参数类型，返回类型）
    _MATH_BINDINGS: list[tuple[str, list[TypeName], list[TypeName]]] = [
        (name, [FLOAT64], [FLOAT64]) for name in [
            "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
            "exp", "log", "log10", "log2", "fabs", "floor", "ceil", "round", "trunc"
        ]
    ] + [
        (name, [FLOAT64, FLOAT64], [FLOAT64]) for name in [
            "pow", "atan2", "fmod", "fmin", "fmax"
        ]
    ] + [
        ("pi", [], [FLOAT64]),
        ("e", [], [FLOAT64])
    ]
    # viola.os绑定
    _OS_BINDINGS: list[tuple[str, list[TypeName], list[TypeName]]] = [
        ("sleep", [UINT64], []),
        ("exit", [INT32], []),
        ("getEnv", [StringTypeName], [StringTypeName]),
        ("time", [], [UINT64]),
        ("system", [StringTypeName], [INT32])
    ]
    # viola.threads的Viola接口
    _THREADS_BINDINGS: list[tuple[str, list[TypeName], list[TypeName]]] = [
        ("addThread", [UINT32], []),
        ("delThread", [UINT32], []),
        ("getThreadsNum", [], [UINT32]),
        ("setThreadsNum", [UINT32], [])
    ]

    @property
    def current_cls(self) -> Optional[ClassName]:
        """
        获取当前正在编译的类（用于访问权限检查）。
        """
        return self._current_cls

    @current_cls.setter
    def current_cls(self, cls: Optional[ClassName]) -> None:
        self._current_cls = cls

    def is_native_class(self, cls_name: str) -> bool:
        """
        判断类是否为原生绑定类（wrapper声明绑定到编译器内置类，实现由运行库提供）。
        :param cls_name: 类名。
        :return: 是否为原生绑定类。
        """
        return cls_name in self._native_class_names

    @staticmethod
    def _prefer_exact_arity(methods: list["MethodName"], types: tuple[TypeName, ...]) -> list["MethodName"]:
        """
        在重载方法中优先保留参数个数与实参完全一致的方法（前缀匹配仅在
        无法精确匹配时使用，用于支持带默认值参数的调用）。
        """
        exact = list(filter(
            lambda m: (len(m.type.args) - (0 if m.is_static else 1)) == len(types), methods))
        return exact if len(exact) > 0 else methods

    @staticmethod
    def _type_lookup_name(t: TypeName) -> str:
        """
        获取类型在符号表中可解析的名称（数组类型使用元素类型+[]，
        因为数组的C名称形如viola$lang$string$$array无法按名称解析）。
        """
        if isinstance(t, ArrayTypeName):
            return SymbolTable._type_lookup_name(t.element_type) + "[]"
        return t.raw_name

    @classmethod
    def tuple_type_defs(cls) -> list[str]:
        """获取所有已注册元组类型的typedef文本（惰性生成）。"""
        return list(map(lambda t: t.c_typedef_text, _TUPLE_TYPE_DEFS.values()))

    @classmethod
    def function_type_defs(cls) -> list[str]:
        """获取所有已注册函数类型的函数指针typedef文本（惰性生成）。"""
        sync_defs: list[str] = []
        async_defs: list[str] = []
        for t in _FUNCTION_TYPE_DEFS.values():
            if t._IS_ASYNC:
                async_defs.append(t.c_typedef_text)
            else:
                sync_defs.append(t.c_typedef_text)
        return sync_defs + async_defs

    @classmethod
    def function_type_defs_sync(cls) -> list[str]:
        """获取同步函数类型的typedef文本（不依赖元组类型定义）。"""
        return [t.c_typedef_text for t in _FUNCTION_TYPE_DEFS.values() if not t._IS_ASYNC]

    @classmethod
    def function_type_defs_async(cls) -> list[str]:
        """获取异步函数类型的typedef文本（引用参数/返回元组类型）。"""
        return [t.c_typedef_text for t in _FUNCTION_TYPE_DEFS.values() if t._IS_ASYNC]

    @classmethod
    def array_type_decl_texts(cls) -> list[str]:
        """获取所有已注册数组类型的结构体定义与方法声明文本。"""
        results: list[str] = []
        for arr_name, elem in _ARRAY_TYPE_DEFS.items():
            elem_asg: str = elem.c_assigning_name
            elem_call: str = elem.c_calling_name
            results.append("\n".join([
                f"#ifndef _VIOLA_ARRAY_T_{arr_name}",
                f"#define _VIOLA_ARRAY_T_{arr_name}",
                "typedef struct {",
                "\tviola$lang$uint32 $refCount;",
                "\tviola$lang$ptr $parent;",
                f"\t{elem_asg} data;",
                "\tviola$lang$uint64 size;",
                f"}} {arr_name};",
                f"void {arr_name}$__getitem__$_0({arr_name} *_this, viola$lang$uint64 item, "
                f"{elem_asg} element, viola$threads$Listener *listener);",
                f"void {arr_name}$__getitem__$_1({arr_name} *_this, viola$lang$slice *s, "
                f"{arr_name} ** subarray, viola$threads$Listener *listener);",
                f"void {arr_name}$concat$_0({arr_name} *_this, {arr_name} *other, "
                f"{arr_name} ** result, viola$threads$Listener *listener);",
                f"void {arr_name}$append$_0({arr_name} *_this, {elem_call} newElement, "
                f"{arr_name} ** newArray, viola$threads$Listener *listener);",
                f"void {arr_name}$insert$_0({arr_name} *_this, viola$lang$int64 location, "
                f"{elem_call} newElement, {arr_name} ** newArray, viola$threads$Listener *listener);",
                f"void {arr_name}$length$_0({arr_name} *_this, viola$lang$uint64 * result, "
                f"viola$threads$Listener *listener);",
                f"void {arr_name}$__setitem__$_0({arr_name} *_this, viola$lang$uint64 index, "
                f"{elem_call} newElement, {arr_name} ** newArray, viola$threads$Listener *listener);",
                f"void {arr_name}$__setitem__$_1({arr_name} *_this, viola$lang$slice *s, "
                f"{arr_name} *newSubarray, {arr_name} ** newArray, viola$threads$Listener *listener);",
                f"void {arr_name}$__del__({arr_name} *_this, viola$threads$Listener *listener);",
                "#endif"
            ]))
        return results

    @classmethod
    def array_type_impl_texts(cls) -> list[str]:
        """获取所有已注册数组类型方法的C实现文本（生成到唯一编译单元__main__.c中）。"""
        results: list[str] = []
        for arr_name, elem in _ARRAY_TYPE_DEFS.items():
            elem_asg: str = elem.c_assigning_name
            elem_call: str = elem.c_calling_name
            elem_size: str = f"sizeof({elem_call.strip()})"
            new_arr: str = (
                f"{arr_name} *newResult = ({arr_name} *)malloc(sizeof({arr_name})); "
                f"newResult->$refCount = 1; newResult->$parent = NULL;"
            )
            results.append("\n".join([
                # 下标访问
                f"void {arr_name}$__getitem__$_0({arr_name} *_this, viola$lang$uint64 item, "
                f"{elem_asg} element, viola$threads$Listener *listener) {{",
                "\t*element = _this->data[item];",
                "}",
                # 切片访问
                f"void {arr_name}$__getitem__$_1({arr_name} *_this, viola$lang$slice *s, "
                f"{arr_name} ** subarray, viola$threads$Listener *listener) {{",
                "\tviola$lang$uint64 start = s->start;",
                "\tviola$lang$uint64 end = s->end > _this->size ? _this->size : s->end;",
                "\tviola$lang$uint64 step = s->step;",
                "\tviola$lang$uint64 count = start < end ? (end - start + step - 1) / step : 0;",
                f"\t{new_arr}",
                "\tnewResult->size = count;",
                f"\tnewResult->data = count == 0 ? NULL : ({elem_asg})malloc({elem_size} * count);",
                "\tviola$lang$uint64 j = 0;",
                "\tfor (viola$lang$uint64 i = start; i < end; i += step) { newResult->data[j++] = _this->data[i]; }",
                "\t*subarray = newResult;",
                "}",
                # 连接
                f"void {arr_name}$concat$_0({arr_name} *_this, {arr_name} *other, "
                f"{arr_name} ** result, viola$threads$Listener *listener) {{",
                f"\t{new_arr}",
                "\tnewResult->size = _this->size + other->size;",
                f"\tnewResult->data = newResult->size == 0 ? NULL : ({elem_asg})malloc({elem_size} * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) { newResult->data[i] = _this->data[i]; }",
                "\tfor (viola$lang$uint64 i = 0; i < other->size; i++) { newResult->data[_this->size + i] = other->data[i]; }",
                "\t*result = newResult;",
                "}",
                # 追加
                f"void {arr_name}$append$_0({arr_name} *_this, {elem_call} newElement, "
                f"{arr_name} ** newArray, viola$threads$Listener *listener) {{",
                f"\t{new_arr}",
                "\tnewResult->size = _this->size + 1;",
                f"\tnewResult->data = ({elem_asg})malloc({elem_size} * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) { newResult->data[i] = _this->data[i]; }",
                "\tnewResult->data[_this->size] = newElement;",
                "\t*newArray = newResult;",
                "}",
                # 插入
                f"void {arr_name}$insert$_0({arr_name} *_this, viola$lang$int64 location, "
                f"{elem_call} newElement, {arr_name} ** newArray, viola$threads$Listener *listener) {{",
                "\tviola$lang$uint64 loc = location < 0 ? 0 : (viola$lang$uint64)location;",
                "\tloc = loc > _this->size ? _this->size : loc;",
                f"\t{new_arr}",
                "\tnewResult->size = _this->size + 1;",
                f"\tnewResult->data = ({elem_asg})malloc({elem_size} * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < loc; i++) { newResult->data[i] = _this->data[i]; }",
                "\tnewResult->data[loc] = newElement;",
                "\tfor (viola$lang$uint64 i = loc; i < _this->size; i++) { newResult->data[i + 1] = _this->data[i]; }",
                "\t*newArray = newResult;",
                "}",
                # 长度
                f"void {arr_name}$length$_0({arr_name} *_this, viola$lang$uint64 * result, "
                f"viola$threads$Listener *listener) {{",
                "\t*result = _this->size;",
                "}",
                # 索引赋值
                f"void {arr_name}$__setitem__$_0({arr_name} *_this, viola$lang$uint64 index, "
                f"{elem_call} newElement, {arr_name} ** newArray, viola$threads$Listener *listener) {{",
                f"\t{new_arr}",
                "\tnewResult->size = _this->size;",
                f"\tnewResult->data = newResult->size == 0 ? NULL : ({elem_asg})malloc({elem_size} * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) { newResult->data[i] = _this->data[i]; }",
                "\tnewResult->data[index] = newElement;",
                "\t*newArray = newResult;",
                "}",
                # 切片赋值
                f"void {arr_name}$__setitem__$_1({arr_name} *_this, viola$lang$slice *s, "
                f"{arr_name} *newSubarray, {arr_name} ** newArray, viola$threads$Listener *listener) {{",
                "\tviola$lang$uint64 start = s->start;",
                "\tviola$lang$uint64 end = s->end > _this->size ? _this->size : s->end;",
                f"\t{new_arr}",
                "\tnewResult->size = _this->size - (end - start) + newSubarray->size;",
                f"\tnewResult->data = newResult->size == 0 ? NULL : ({elem_asg})malloc({elem_size} * newResult->size);",
                "\tviola$lang$uint64 j = 0;",
                "\tfor (viola$lang$uint64 i = 0; i < start; i++) { newResult->data[j++] = _this->data[i]; }",
                "\tfor (viola$lang$uint64 i = 0; i < newSubarray->size; i++) { newResult->data[j++] = newSubarray->data[i]; }",
                "\tfor (viola$lang$uint64 i = end; i < _this->size; i++) { newResult->data[j++] = _this->data[i]; }",
                "\t*newArray = newResult;",
                "}",
                # 析构
                f"void {arr_name}$__del__$_0({arr_name} *_this, viola$threads$Listener *listener) {{",
                "\tif (_this->$refCount == 0) {",
                "\t\tif (_this->$parent) { ((viola$lang$uint32 *)_this->$parent)[0]--; }",
                "\t\telse {",
                "\t\t\tfree(_this->data); _this->data = NULL;",
                "\t\t\tfree(_this); _this = NULL;",
                "\t\t}",
                "\t}",
                "}"
            ]))
        return results

    def __contains__(self, item: tuple[NamedSymbol | str, Optional[tuple[TypeName, ...]]]) -> bool:
        """
        判断一个符号是否存在于表中。
        """
        if isinstance(item[0], TypeName):
            # 组合类型（元组、数组、函数等）检查其成员类型是否都已定义
            for t in item[0].used_types:
                if (t.name, None) in self.symbols or (self.clean_namespace(t.name), None) in self.symbols:
                    continue
                if isinstance(t, (TupleTypeName, ArrayTypeName, FunctionTypeName, ClassName)):
                    if not self.__contains__((t, None)):
                        return False
                    continue
                return False
            return True
        if isinstance(item[0], NamedSymbol):
            if item[0].name.startswith(self._namespace_name + "$"):
                return (item[0].name[len(self._namespace_name):], item[1]) in self.symbols
            return item[0] in self.symbols.values()
        original_name: str = item[0] if isinstance(item[0], str) else item[0].name
        if original_name.startswith(TUPLE_T + "$") or original_name.endswith("$$array"):
            # 组合类型（元组/数组）由编译器按需生成结构体定义
            return True
        if original_name.startswith("viola$lang$Pointer$") or original_name.startswith("Pointer$"):
            # 指针类型
            return True
        item = self.clean_namespace(original_name), item[1]
        if item not in self.symbols:
            functions: list[tuple[str, Optional[tuple[TypeName, ...]]]] = [k for k in self.symbols.keys() if k[0] == item[0]]
            if isinstance(item[0], str) and item[1] is None:
                if len(functions) > 0:
                    return True
                item2 = item[0].replace(".", "$")
                result = self._type_name_parser.parse(self._src_info, item2)
                if result is None:
                    return False
                for t in result.used_types:
                    if (self.clean_namespace(t.name), None) not in self.symbols:
                        return False
                return True
            for f in functions:
                if f[1] is None or len(item[1]) > len(f[1]):
                    continue
                contains: bool = True
                for i, t0 in enumerate(item[1]):
                    if t0 != f[1][i]:
                        contains = False
                        break
                if contains:
                    return True
            return False
        return item in self.symbols

    def __delitem__(self, key: tuple[str, Optional[tuple[TypeName, ...]]]) -> None:
        for i, sym in enumerate(self._symbols):
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
        item = self.clean_namespace(item)
        if "." in item and types is not None:
            names = item.rsplit(".", 1)
            attr_name = names[1]
            cls_name = names[0]
            result = self.find_methods(cls_name, attr_name, [cls_name] + [
                SymbolTable._type_lookup_name(t) for t in types], {})
            if len(result) == 1:
                return result[0]
            elif len(result) > 1:
                # 重载方法优先按参数个数精确匹配（如rsplit(string)与rsplit(string, uint64)）
                result = SymbolTable._prefer_exact_arity(result, types)
                if len(result) == 1:
                    return result[0]
                # 子类重写的方法优先于继承的抽象方法；自身定义的方法优先于继承的方法
                concrete = list(filter(lambda m: not m.is_abstract, result))
                if len(concrete) == 1:
                    return concrete[0]
                if len(concrete) > 1:
                    own = list(filter(lambda m: m.cls.name == self[cls_name, None].name, concrete))
                    if len(own) == 1:
                        return own[0]
                raise CompilerException(f"Ambiguous method call: {cls_name}.{attr_name}({', '.join(t.raw_name for t in types)})", self._src_info)
            result = self.find_methods(cls_name, attr_name, [
                SymbolTable._type_lookup_name(t) for t in types], {})
            if len(result) == 1:
                return result[0]
            elif len(result) > 1:
                # 重载方法优先按参数个数精确匹配
                result = SymbolTable._prefer_exact_arity(result, types)
                if len(result) == 1:
                    return result[0]
                concrete = list(filter(lambda m: not m.is_abstract, result))
                if len(concrete) == 1:
                    return concrete[0]
                if len(concrete) > 1:
                    own = list(filter(lambda m: m.cls.name == self[cls_name, None].name, concrete))
                    if len(own) == 1:
                        return own[0]
                raise CompilerException(f"Ambiguous method call: {cls_name}.{attr_name}({', '.join(t.raw_name for t in types)})", self._src_info)
        # item = item.replace(".", "$")
        if (item, types) not in self.symbols:
            if types is None and (item, None) in self.symbols:
                return self.symbols[item, None]
            if types is None:
                functions = [v for k, v in self.symbols.items() if k[0] == item]
                if len(functions) == 1:
                    return functions[0]
                item2 = item.replace(".", "$")
                if (item2, None) in self.symbols:
                    return self.symbols[item2, None]
                if item2.startswith("viola$lang$Pointer$") or item2.startswith("Pointer$"):
                    # 指针类型：按指向的元素类型重建
                    element_name = item2.split("Pointer$", 1)[1]
                    element = self[element_name, None]
                    if isinstance(element, TypeName):
                        return PointerTypeName(self._src_info, element)
                result = self._type_name_parser.parse(self._src_info, item2)
                if result is not None and isinstance(result, ClassName) and (result.self_name, None) not in self.symbols:
                    self.add_to_root(result, result.self_name, None)
                if result is None:
                    raise CompilerException(f"Type {item} not found", self._src_info)
                return result
            raise CompilerException(f"Symbol {item} not found", self._src_info)
        return self.symbols[item, types]

    def __init__(self, src_path: str = "", workspace: str = "") -> None:
        """
        创建全局符号表。
        path: 源代码路径。
        workspace: 根目录。
        """
        self._symbols: list[dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]] = [{}]
        self._func_overload_times: dict[str, int] = {}
        # 原生绑定类：wrapper类声明绑定到编译器内置类（实现由运行库提供，不生成C代码）
        self._native_class_names: set[str] = set()
        self._current_cls: Optional[ClassName] = None
        if not src_path == "" and not workspace == "":
            # 元数据中的路径为缓存路径（含__viola_cache__与..段），
            # 还原为真实的源文件路径
            src_path = os.path.normpath(src_path)
            workspace = os.path.normpath(workspace)
            src_path = os.path.splitext(src_path)[0]
            rel: str = os.path.relpath(src_path, workspace)
            if rel.startswith(".."):
                # 模块位于工作区之外（如运行库viola_libs）：相对VIOLA_HOME计算命名空间
                if "VIOLA_HOME" in os.environ:
                    for lib_root in os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":"):
                        lib_root = lib_root.strip()
                        if lib_root == "":
                            continue
                        try:
                            rel_in_lib: str = os.path.relpath(src_path, lib_root)
                        except ValueError:
                            continue
                        if not rel_in_lib.startswith(".."):
                            rel = rel_in_lib
                            break
            if rel == "":
                # 元数据还原后无法推导：尝试相对VIOLA_HOME
                if "VIOLA_HOME" in os.environ:
                    for lib_root in os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":"):
                        lib_root = lib_root.strip()
                        if lib_root == "":
                            continue
                        try:
                            rel_in_lib: str = os.path.relpath(src_path, lib_root)
                        except ValueError:
                            continue
                        if not rel_in_lib.startswith(".."):
                            rel = rel_in_lib
                            break
            dir_list: list[str] = rel.replace("-", "_").split(os.sep)
        else:
            dir_list = []
        self._namespace: list[NamespaceName] = list(map(lambda x: NamespaceName(x), dir_list))
        self._namespace_name: str = ".".join(map(lambda x: x.name, self._namespace))
        self._counter: int = 0
        self._class_info_list_name: str = "$".join(map(lambda x: x.name, self._namespace)) + "$classInfoList"
        self._src_info: SourceInfo = SourceInfo(src_path)
        self._generic_table: GenericTable = GenericTable(self._src_info, self._namespace)
        self._namespace_without_import: tuple[str, ...] = \
            tuple([*map(lambda x: ".".join(y.name for y in x) + ".", SymbolTable._NAMESPACES_WITHOUT_IMPORT), self._namespace_name + "."])
        self._init_builtin_types()

        def __real_type_getter(name: str) -> Optional[TypeName]:
            name = name.strip()
            if (name, None) in self.symbols:
                return self.symbols[name, None]
            name = self.clean_namespace(name)
            if (name, None) in self.symbols:
                return self.symbols[name, None]
            return None

        self._type_name_parser: _TypeNameParser = _TypeNameParser(__real_type_getter, self._generic_table)

    def _init_builtin_types(self) -> None:
        builtin_types = [
            BOOL,
            INT, INT8, INT16, INT32, INT64,
            UINT, UINT8, UINT16, UINT32, UINT64,
            SIZE_T,
            FLOAT, FLOAT32, FLOAT64, FLOAT128,
            DOUBLE, LONG_DOUBLE,
            VOID_PTR,
        ]
        for t in builtin_types:
            self.add(t, t.self_name, None)
        self.add(SIZE_T, "size_t", None)
        self.add(PointerGenericClassName, PointerGenericClassName.self_name, None)
        self._generic_table.add_cls_def(PointerGenericClassName)
        self.add(Object, Object.self_name, None)
        self.add(StringTypeName, StringTypeName.self_name, None)
        self.add(SliceTypeName, SliceTypeName.self_name, None)
        self.add(ExceptionTypeName, ExceptionTypeName.self_name, None)
        self.add(FileTypeName, FileTypeName.self_name, None)
        self.add(_perror, _perror.self_name, [StringTypeName])
        self.add(_print, _print.self_name, [StringTypeName])
        self.add(_input, _input.self_name, [])
        self.add(_open, _open.self_name, [StringTypeName, StringTypeName, StringTypeName])
        self.add(_read, _read.self_name, [FileTypeName])
        self.add(_read_bytes, _read_bytes.self_name, [FileTypeName])
        self.add(_write, _write.self_name, [FileTypeName, StringTypeName])
        self.add(_write_bytes, _write_bytes.self_name, [FileTypeName, ArrayTypeName(VIOLA_INIT, UINT8)])
        # viola.math 与 viola.os 的绑定函数（原生，实现于运行库）
        for name, args, rets in SymbolTable._MATH_BINDINGS:
            func = FunctionName(VIOLA_INIT, [NamespaceName("viola"), NamespaceName("math")], name,
                                FunctionTypeName(VIOLA_INIT, args, rets),
                                [f"arg{i}" for i in range(len(args))],
                                [f"ret{i}" for i in range(len(rets))], True, False, True)
            self.add(func, func.self_name, args)
        for name, args, rets in SymbolTable._OS_BINDINGS:
            func = FunctionName(VIOLA_INIT, [NamespaceName("viola"), NamespaceName("os")], name,
                                FunctionTypeName(VIOLA_INIT, args, rets),
                                [f"arg{i}" for i in range(len(args))],
                                [f"ret{i}" for i in range(len(rets))], True, False, True)
            self.add(func, func.self_name, args)
        # viola.threads 的Viola接口
        for name, args, rets in SymbolTable._THREADS_BINDINGS:
            func = FunctionName(VIOLA_INIT, [NamespaceName("viola"), NamespaceName("threads")], name,
                                FunctionTypeName(VIOLA_INIT, args, rets),
                                [f"arg{i}" for i in range(len(args))],
                                [f"ret{i}" for i in range(len(rets))], True, False, True)
            self.add(func, func.self_name, args)

    def add(self, symbol: NamedSymbol, name: str, types: Optional[list[TypeName]]) -> None:
        """
        添加一个符号。
        symbol: 需要添加的符号。
        name: 查找符号时使用的名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        if types is not None:
            if (name, tuple(types)) in self.symbols:
                raise CompilerException(f"Symbol {name} already exists.", self._src_info)
        if symbol.kw_type != SymbolType.FUNCTION and symbol.kw_type != SymbolType.METHOD and types is not None:
            raise InternalCompilerException("Symbol must not have types.", self._src_info)
        self._symbols[-1][name, tuple(types) if types is not None else None] = symbol

    def add_to_root(self, symbol: NamedSymbol, name: str, types: Optional[list[TypeName]]) -> None:
        """
        添加一个符号到最底层作用域。
        symbol: 需要添加的符号。
        name: 查找符号时使用的名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        if types is not None:
            if (name, tuple(types)) in self.symbols:
                raise CompilerException(f"Symbol {name} already exists.", self._src_info)
        if symbol.kw_type != SymbolType.FUNCTION and symbol.kw_type != SymbolType.METHOD and types is not None:
            raise InternalCompilerException("Symbol must not have types.", self._src_info)
        self._symbols[0][name, tuple(types) if types is not None else None] = symbol

    def add_scope(self) -> None:
        """
        添加一个作用域。
        """
        self._symbols.append({})

    def clean_namespace(self, name: str) -> str:
        item = name.replace("$", ".")
        for namespace in self._namespace_without_import:
            if item.startswith(namespace):
                item = item[len(namespace):]
                return item
        return item

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
        name = self.clean_namespace(name)
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
        # 精确匹配优先：参数数量相同且每个参数类型名称完全一致时，优先选择精确匹配的重载
        exact_matches = dict(filter(
            lambda x: len(x[0][1]) == args_length and all(
                args_tuple[i].name == x[0][1][i].name for i in range(args_length)
            ) and all(
                x[1].arg_types_dict[y].name == kwargs_declaration[y].name for y in kwargs_declaration.keys()
            ),
            matches.items()
        ))
        if len(exact_matches) > 0:
            return list(exact_matches.values())
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
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
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
        cls = self[cls_name, None]
        name = self.clean_namespace(name)
        args = list(map(lambda x: self.clean_namespace(x), args))
        kwargs = dict(map(lambda k, v: (k, self.clean_namespace(v)), kwargs.items()))
        if not isinstance(cls, ClassName):
            raise CompilerException(f"{cls_name} is not a class", self._src_info)
        arg_types: list[TypeName] = list(map(lambda x: self[x, None], args))
        kwargs_types: dict[str, TypeName] = dict(map(lambda x: (x, self[kwargs[x], None]), kwargs.keys()))
        methods = dict(filter(lambda x: x[0][0] == name, cls.methods.items()))
        methods = dict(filter(lambda x: len(x[0][1]) >= len(arg_types), methods.items()))
        methods = dict(filter(lambda x: all(map(lambda i: arg_types[i].convertable_to(x[0][1][i], self.symbols),
                                                range(len(arg_types)))), methods.items()))
        methods = dict(filter(lambda x: all(
            x[1].arg_types_dict[y].convertable_to(kwargs_types[y], self.symbols) for y in kwargs_types.keys()
        ), methods.items()))
        return list(methods.values())

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
        if (cls.self_name, None) not in self.symbols:
            self.add_to_root(cls, cls.self_name, None)
        for method in cls.methods.values():
            if method.is_generic and method not in self._generic_table:
                self._generic_table.add_func_def(method.as_function())
        return cls

    def get_generic_func_instance(self, func_name: FunctionName, t: tuple[TypeName, ...]) -> FunctionName:
        """
        获取泛型函数的实例化对象。
        """
        _GENERIC_FUNC_INSTANCE_REQUESTS.setdefault(func_name.name, set()).add(t)
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
            if item.strip():
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

    def remove(self, name: str) -> None:
        """
        删除符号。
        """
        for i, sym in enumerate(self._symbols):
            self._symbols[i] = dict(filter(lambda x: x[0][0] != name, sym.items()))

    def set_src_info(self, src_info: SourceInfo) -> None:
        """
        设置源代码信息。
        """
        self._src_info = src_info.copy()

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
        item_type_parts = item_args[0].split(" ")
        item_type: str = item_type_parts[0]
        if len(item_type_parts) > 1 and ":" in item_type_parts[1]:
            loc_str: list[str] = item_type_parts[1].split(":")
            loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
            self._src_info.set_loc(*loc_tuple)
        item_args = item_args[1:]
        while len(item_args) < 5:
            item_args.append("")
        match item_type:
            case "BASE":
                self._read_base_type_def(item_args)
            case "FUNC" | "FUNCTION":
                self._read_func_decl(item_args)
            case "CLASS":
                self._read_class_decl(item_args)
            case "VAR":
                self._read_global_var_decl(item_args)
            case "METHOD":
                self._read_method_decl(item_args)
            case "ENUM":
                self._read_enum_decl(item_args)

    @staticmethod
    def _split_qualified_name(name: str) -> tuple[list[NamespaceName], str]:
        """
        拆分点号限定的符号名，返回其命名空间与自身名。
        name: 点号限定的符号名。
        """
        parts: list[str] = name.split(".")
        return [NamespaceName(p) for p in parts[:-1]], parts[-1]

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
        name_parts: list[str] = item[0].split(" ")[1:]
        export: bool = "export" in name_parts
        is_native: bool = "native" in name_parts
        if "%" in item[1]:
            generic_args: list[str] = []
            item_args: list[str] = item[1].split("%")
            item_returns: list[str] = item[2].split("%") if len(item) > 2 else []
            item_default_args: list[str] = item[3].split(" ") if len(item) > 3 else []
        else:
            generic_args: list[str] = item[1].split(" ")
            item_args: list[str] = item[2].split("%") if len(item) > 2 else []
            item_returns: list[str] = item[3].split("%") if len(item) > 3 else []
            item_default_args: list[str] = item[4].split(" ") if len(item) > 4 else []
        # 泛型参数在解析参数/返回类型期间临时注册为符号
        generic_arg_objs: list[GenericArgument] = [GenericArgument(self._src_info, g) for g in generic_args if g != ""]
        for arg in generic_arg_objs:
            self.add(arg, arg.name, None)
        existing_native: Optional[FunctionName] = None
        try:
            # noinspection PyTypeChecker
            args = list(map(lambda arg: self[arg, None], item_args[::2])) if len(item_args) > 1 else []
            if any(map(lambda arg: not isinstance(arg, TypeName), args)):
                raise CompilerException("Function arguments must be types.", self._src_info)
            existing = self.symbols.get((item_name, tuple(args)))
            if existing is not None:
                if is_native and isinstance(existing, FunctionName) and existing.is_native:
                    # 原生声明与编译器内置绑定一致时复用内置声明（保持运行库C名称）
                    existing_native = existing
                else:
                    raise CompilerException(f"Function {item_name} already exists.", self._src_info)
            elif not is_native and (item_name, tuple(args)) in self:
                # 非原生定义不允许与其他符号（含命名空间清理后的模糊匹配）冲突
                raise CompilerException(f"Function {item_name} already exists.", self._src_info)
            args: list[TypeName]
            # noinspection PyTypeChecker
            returns: list[TypeName] = list(map(lambda ret: self[ret, None], item_returns[::2])) if len(item_returns) > 1 else []
            if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
                raise CompilerException("Function returns must be types.", self._src_info)
        finally:
            for arg in generic_arg_objs:
                self.remove(arg.name)
        if existing_native is not None:
            if list(existing_native.type.returns) != returns:
                raise CompilerException(
                    f"Native function {item_name} does not match the builtin binding.", self._src_info)
            return
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        if item_name not in self._func_overload_times:
            self._func_overload_times[item_name] = 0
        func_namespace, func_self_name = SymbolTable._split_qualified_name(item_name)
        if len(func_namespace) == 0:
            # 未限定的函数名使用本模块的命名空间
            func_namespace = self._namespace
        if is_native:
            # 原生函数不使用重载序号（C名称与运行库一致，如viola$math$sqrt）
            func = FunctionName(self._src_info, func_namespace, func_self_name, func_type,
                                item_args[1::2] if len(item_args) > 1 else [],
                                item_returns[1::2] if len(item_returns) > 1 else [], export, False, True)
        else:
            func = FunctionName(self._src_info, func_namespace,
                                f"{func_self_name}$_{self._func_overload_times[item_name]}", func_type,
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
                self.add(v, k, None)
        self.add(func, item_name, args)
        if len(generic_args) > 0:
            # 泛型函数注册到泛型表，供泛型调用实例化
            self._generic_table.add_func_def(func)

    def _read_global_var_decl(self, item: list[str]) -> None:
        """
        读取全局变量。记载格式如下：
        <变量类型>%<变量名>
        """
        item: list[str] = item[0].split("%")
        item_name: str = item[1]
        item_type: str = item[0]
        var_namespace, var_self_name = SymbolTable._split_qualified_name(item_name)
        if len(var_namespace) == 0:
            # 未限定的变量名使用本模块的命名空间
            var_namespace = self._namespace
        # noinspection PyTypeChecker
        self.add(GlobalVariableName(self._src_info, var_namespace, var_self_name, self[item_type, None]), item_name, None)

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
        # noinspection PyTypeChecker
        generic_arg_obj_cls: list[GenericArgument] = cls.generic_args if cls.generic_args is not None else []
        for arg in generic_arg_obj_cls:
            self.add(arg, arg.name, None)
        is_abstract: bool = "abstract" in item_name[2:] or cls.is_interface
        # 接口/抽象类的无体方法按抽象方法处理（abstract优先于native）
        is_native: bool = "native" in item_name[2:] and not is_abstract
        is_static: bool = "static" in item_name[2:] or method_name.endswith(".__new__") or method_name == "__new__"
        export: bool = "export" in item_name[2:]
        is_final: bool = "final" in item_name[2:]
        # 父类的final方法不可重写
        if cls.parent is not None and cls.parent != Object:
            for (p_name, _), p_method in cls.parent.methods.items():
                if p_name == method_name and p_method.is_final:
                    raise CompilerException(
                        f"Method {cls.raw_name}.{method_name} can not override final method.", self._src_info)
        item_args: list[str] = item[2].split("%")
        item_returns: list[str] = item[3].split("%")
        item_default_args: list[str] = item[4].split(" ")
        # noinspection PyTypeChecker
        args = list(map(lambda arg: self[arg, None], item_args[::2])) if len(item_args) > 1 else []
        if any(map(lambda arg: not isinstance(arg, TypeName), args)):
            raise CompilerException("Function arguments must be types.", self._src_info)
        # noinspection PyTypeChecker
        returns = list(map(lambda ret: self[ret, None], item_returns[::2])) if len(item_returns) > 1 else []
        if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
            raise CompilerException("Function returns must be types.", self._src_info)
        args: list[TypeName]
        returns: list[TypeName]
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        modifier = self.__get_modifier(item_name[2:])
        if is_native:
            # 原生方法与类上已有的同名原生方法一致时复用（保持其C名称中的重载序号，
            # 如viola$lang$string$length$_0）
            lookup_args: tuple[TypeName, ...] = tuple([cls] + args) if not is_static else tuple(args)
            if (method_name, lookup_args) in cls.methods:
                existing = cls.methods[method_name, lookup_args]
                if existing.is_native:
                    self.add(existing, f"{self.clean_namespace(cls.raw_name)}.{method_name}", args)
                    for arg in generic_arg_obj_cls:
                        self.remove(arg.name)
                    return
        if f"{cls.name}.{method_name}" not in self._func_overload_times:
            self._func_overload_times[f"{cls.name}.{method_name}"] = 0
        method = MethodName(
            self._src_info, cls, f"{method_name}$_{self._func_overload_times[f'{cls.name}.{method_name}']}",
            func_type, is_abstract, is_static, item_args[1::2] if len(item_args) > 1 else [],
            item_returns[1::2] if len(item_returns) > 1 else [], modifier, export, is_native, is_final
        )
        self._func_overload_times[f"{cls.name}.{method_name}"] += 1
        method.set_default_params(item_default_args)
        for k, v in method.default_params.items():
            if v is not None:
                self.add(v, k, None)
        self.add(method, f"{self.clean_namespace(cls.raw_name)}.{method_name}", args)
        cls.add_method(method_name, method)
        for arg in generic_arg_obj_cls:
            self.remove(arg.name)

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
            existing_cls = self[cls_name, None]
            if "wrapper" in item[0].split(" ")[1:] and isinstance(existing_cls, ClassName):
                # wrapper类声明与编译器内置类同名：绑定到内置类，实现由运行库提供。
                # 类体中的属性与父类信息以内置类为准，故跳过类体解析。
                self._native_class_names.add(cls_name)
                return
            raise CompilerException(f"Class {cls_name} already exists.", self._src_info)
        cls_namespace, cls_self_name = SymbolTable._split_qualified_name(cls_name)
        if len(cls_namespace) == 0:
            # 未限定的类名使用本模块的命名空间
            cls_namespace = self._namespace
        modifiers: list[str] = item[0].split(" ")[1:]
        parent: ClassName = Object
        parents_text: str = item[0].split(" ")[0].split("%")[1]
        if parents_text != "object":
            parent_names: list[str] = parents_text.split(",")
            # noinspection PyTypeChecker
            parent = self[parent_names[0], None]
            if not isinstance(parent, ClassName):
                raise CompilerException(f"$parent class {parent_names[0]} is not a class.", self._src_info)
            if parent.is_final:
                raise CompilerException(f"Class {parent_names[0]} is final and can not be inherited.", self._src_info)
            # 其余父类型为实现的接口
            interfaces: list[ClassName] = []
            for interface_name in parent_names[1:]:
                # noinspection PyTypeChecker
                interface = self[interface_name, None]
                if not isinstance(interface, ClassName) or not interface.is_interface:
                    raise CompilerException(f"{interface_name} is not an interface.", self._src_info)
                interfaces.append(interface)
            cls_interfaces = interfaces
        is_abstract: bool = "abstract" in modifiers
        is_c_part: bool = "c" in modifiers
        is_final: bool = "final" in modifiers
        is_wrapper: bool = "wrapper" in modifiers
        is_unsafe: bool = "unsafe" in modifiers
        is_interface: bool = "interface" in modifiers
        if is_interface:
            # 接口不可实例化，方法均为抽象方法
            is_abstract = True
        generic_args: list[str] = list(filter(lambda x: x != "", item[1].split(" ")))
        cls = ClassName(self._src_info, cls_namespace, cls_self_name, parent, is_abstract, is_c_part, generic_args,
                        is_final, is_wrapper, is_unsafe, is_interface)
        cls._export = "export" in modifiers
        if parents_text != "object" and len(parent_names) > 1:
            cls._interfaces = cls_interfaces
        if len(generic_args) > 0:
            self._generic_table.add_cls_def(cls)
        # noinspection PyTypeChecker
        generic_arg_obj: list[GenericArgument] = cls.generic_args if cls.generic_args is not None else []
        for arg in generic_arg_obj:
            self.add(arg, arg.name, None)
        if parent is not None:
            # 继承父类的方法：将父类方法并入子类的方法表，使子类实例
            # 可以直接调用继承的方法。__del__ 不复制，每个类都会生成
            # 自己的析构方法。
            for key, method in parent.methods.items():
                if key[0] == "__del__" or key in cls._methods:
                    continue
                cls._methods[key] = method
            vtable: ClassName = ClassName(self._src_info, [], cls.name + "$$vtable", None, False,
                                          False)
            self.add(vtable, self.clean_namespace(cls.raw_name) + ".$$vtable", None)
            # 实例中保存其类型的TypeInfo指针，供catch与动态转换使用（由构造函数赋值）
            if "$$vtable" not in cls.properties:
                cls.add_property(self._src_info, "$$vtable", VOID_PTR, Modifier.PUBLIC, False)
        item_loc: int = 2
        while not item[item_loc] == "END CLASS":
            item_text: list[str] = item[item_loc].split(" ")
            loc_str: list[str] = item_text[0].split(":")
            loc_tuple: tuple[int, int, int, int] = int(loc_str[0]), int(loc_str[1]), int(loc_str[2]), int(loc_str[3])
            self._src_info.set_loc(*loc_tuple)
            type_name: str = item_text[1].split("%")[0]
            property_name: str = item_text[1].split("%")[1]
            # noinspection PyTypeChecker
            t: TypeName = self[type_name, None]
            cls.add_property(self._src_info, property_name, t, self.__get_modifier(item_text[2:]),
                             "static" in item_text[2:], "unsafe" in item_text[2:])
            if item_loc == len(item) - 1:
                raise CompilerException(f"Unexpected end of class {cls_name}", self._src_info)
            item_loc += 1
        if parent is not None:
            # 在解析完类体后复制父类属性（含object的$refCount、$parent），
            # 子类重新声明的同名属性优先（属性遮蔽）
            for name, prop in parent.properties.items():
                if name not in cls.properties:
                    cls.add_property_object(name, prop)
        cls_key_name = cls.self_name if cls.raw_name.startswith(self._namespace_without_import) else cls.raw_name
        if (cls_key_name, None) in self:
            existing_cls = self[cls_key_name, None]
            if isinstance(existing_cls, ClassName) and existing_cls.name == cls.name:
                # 导入条目与已有类C名称一致（如viola.lang.string与编译器内置string）：
                # 仅按限定名注册，保留已有类的裸名注册
                cls_key_name = cls.raw_name
            else:
                raise CompilerException(f"Class {cls_key_name} already exists.", self._src_info)
        if not cls.is_c_part and not cls.is_wrapper:
            # 普通类自动注册析构方法；wrapper类由用户实现__del__（并用del(super)释放普通成员）
            del_method = MethodName(
                self._src_info, cls, "__del__", FunctionTypeName(self._src_info, [], []),
                False, False, [], [], Modifier.PUBLIC, True
            )
            cls.add_method("__del__", del_method)
            self.add(del_method, cls_key_name + ".__del__", [cls])
        self.add(cls, cls_key_name, None)
        for arg in generic_args:
            self.remove(arg)

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
    def __gt__(self, other: "VariableState") -> bool:
        return self.value > other.value

    def __lt__(self, other: "VariableState") -> bool:
        return self.value < other.value

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
        if path and workspace:
            dir_list: list[str] = os.path.relpath(path, workspace).replace("-", "_").split(os.sep)
        else:
            dir_list: list[str] = []
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

    @property
    def last_scope(self) -> dict[VariableName, VariableState]:
        return self._state[-1]

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
