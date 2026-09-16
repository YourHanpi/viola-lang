# -*- coding: utf-8 -*-

from utils import CompilerException, InternalCompilerException, SourceInfo, VIOLA_INIT
from utils.fsm import FSM, StateNode, Token

from abc import ABC, abstractmethod
from copy import copy, deepcopy
from enum import Enum
import heapq
import os
import threading
from typing import Optional, Callable

from utils.logger import Logger
from utils.text_utils import sanitize_c_identifier, strip_trailing_overload_suffix, find_placeholder

# 函数值结构体（0.1起原Closure更名为Function，见versions_dev_plan_zh.md）
FUNCTION_T: str = "viola$lang$function$Function"
# 兼容旧名称（部分生成代码仍引用Closure结构体时使用的别名）
CLOSURE_T: str = FUNCTION_T
FUNCTION_SYNC_PTR_T: str = "viola$lang$function$SyncPtr"
FUNCTION_ASYNC_PTR_T: str = "viola$lang$function$AsyncPtr"
LISTENER_T: str = "viola$threads$Listener"
LISTENER_INIT_FUNC: str = "viola$threads$initListener"
EXCEPTION_T: str = "viola$lang$exception$Exception"
EXCEPTION_T_NAME: str = "viola$lang$exception$Exception"
TUPLE_T: str = "viola$collections$Tuple"
# 元组结构体的析构函数指针成员（位于size之后、元素成员之前）：由分配处写入该
# 元组类型按元素类型单态化的析构函数，释放时代码只调用TUPLE_T$__del__转发
# （见destructor_name与开发疑问记录192）
TUPLE_DEL_FIELD_T: str = f"void (*$del)(void *_this, {LISTENER_T} *listener);"
# 数组方法的$async包装（见array_type_impl_texts）所用的运行库符号：
# 与definition.py/expression.py/statement.py中的同名常量一致，因模块依赖方向
# （definition/statement引用symbol）无法跨模块引用，故在此重复声明
STRING_T: str = "viola$lang$string"
CONVERTIBLE_TO_FUNC: str = "viola$lang$convertibleTo"
EXCEPTION_VTABLE: str = EXCEPTION_T + "$$vtable"
EXCEPTION_WHAT_FUNC: str = EXCEPTION_T + "$what$_0"
EXCEPTION_DEL_FUNC: str = EXCEPTION_T + "$__del__$_0"
PERROR_FUNC: str = "viola$io$print$perror"
STACK_B_PUSH_FUNC: str = "viola$threads$pushStackB"
STACK_B_POP_FUNC: str = "viola$threads$popStackB"

# 引用计数（原子操作，定义见runtime.h"原子引用计数"）。0.1的模型：
# 每个持有对象指针的槽位（局部变量、临时变量、类成员、返回值槽位）都算一次持有，
# 分配处计数为1（由接收它的槽位持有）；把既有对象存入槽位时retain（计数递增），
# 槽位不再持有时release（计数递减，归零则调用析构/释放）。
# 与definition.py的同名常量一致，因模块依赖方向（definition引用symbol）在此重复声明。
REFCOUNT_INC_FUNC: str = "viola$lang$refcount_inc"
REFCOUNT_DEC_FUNC: str = "viola$lang$refcount_dec"


def retain_text(var_text: str) -> str:
    """生成把var_text所指对象多记一个持有者的C文本（retain）。

    var_text为对象指针表达式（可能为NULL）：为空时不计数。
    """
    return f"if ({var_text}) {{ {REFCOUNT_INC_FUNC}(&({var_text})->$refCount); }}"


def destructor_name(var_type: TypeName) -> str:
    """获取释放该类型对象所用析构函数的C名（不含实参与结尾分号）。

    泛型实例化的类其析构方法名带额外的重载序号（如Box__1$__del__$_0$_0），
    按类型实际注册的析构方法取名，避免与定义不一致（见开发疑问记录102）。
    """
    if isinstance(var_type, TupleTypeName):
        # 元组一律经运行库的固定名字转发到具体类型的析构函数（该函数由元组的
        # $del成员指出，见TupleTypeName.c_typedef_text）：按元素类型单态化的
        # 析构函数名含元素类型名，而释放代码的文本可能在泛型函数体中提前渲染
        # （彼时类型还是占位符，如Tuple$U，见开发疑问记录192）
        return f"{TUPLE_T}$__del__"
    if isinstance(var_type, ArrayTypeName):
        # 数组的C名称使用$$array形式
        return f"{var_type.c_alloc_name}$__del__$_0"
    if isinstance(var_type, ClassName):
        del_method = next(
            (m for (n, _), m in var_type.methods.items() if n == "__del__"), None)
        if del_method is not None:
            return del_method.name
    return f"{var_type.name}$__del__$_0"


def tuple_del_name(tuple_c_name: str) -> str:
    """获取元组类型按元素类型单态化的析构函数的C名（由分配处写入元组的$del）。"""
    return f"{tuple_c_name}$__del__$_0"


def tuple_del_decl_text(tuple_c_name: str) -> str:
    """获取元组类型析构函数的声明文本（与元组结构体一同输出到模块头文件）。

    首形参为void *：所有元组析构共用同一函数指针类型，分配处写入$del时无需
    强制转换（见TupleTypeName.c_typedef_text）。
    """
    return f"void {tuple_del_name(tuple_c_name)}(void *_this, " \
           f"{LISTENER_T} *listener);"


def tuple_del_assign_text(tuple_text: str, tuple_type: TypeName) -> str:
    """获取把元组的$del指向其具体类型析构函数的赋值文本（在元组分配处输出）。"""
    return f"{tuple_text}->$del = {tuple_del_name(tuple_type.c_alloc_name)};"


def release_text(var_text: str, free_stmts: str) -> str:
    """生成"递减计数、归零则执行free_stmts"的C文本（release）。

    free_stmts为计数归零后要执行的释放语句（析构调用或free），可为多行。
    var_text为NULL时不做任何事。
    """
    body: str = "\n".join("\t\t" + line for line in free_stmts.split("\n"))
    return "\n".join([
        f"if ({var_text}) {{",
        f"\tif ({REFCOUNT_DEC_FUNC}(&({var_text})->$refCount) == 0) {{",
        body,
        "\t}",
        "}"
    ])


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
VIOLA_LANG_FUNCTION: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("lang"), NamespaceName("function")]
VIOLA_LANG_GRM: list[NamespaceName] = [NamespaceName("viola"), NamespaceName("lang"), NamespaceName("global_resource_manager")]
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

    # 是否按身份比较（泛型参数为True：不同泛型函数的同名类型参数
    # 如两个T不是同一类型，其余类型按名称比较实现语义去重）
    _IDENTITY_EQUALS: bool = False

    def __eq__(self, other: object) -> bool:
        """类型按名称比较（语义等价）。泛型参数（GenericArgument）保持身份比较。"""
        if isinstance(other, TypeName) and \
                not self._IDENTITY_EQUALS and not other._IDENTITY_EQUALS:
            return self.name == other.name
        return self is other

    def __hash__(self) -> int:
        if self._IDENTITY_EQUALS:
            return id(self)
        return hash(self.name)

    def __deepcopy__(self, memo: dict) -> "TypeName":
        """类型在深拷贝中共享（视为不可变）：深拷贝返回自身。

        类型之间相互引用（ClassName->methods->FunctionTypeName->args、
        ArrayTypeName->element等）形成巨大的连通图；若随定义深拷贝
        逐实例复制，泛型实例化的深拷贝会退化为对整张类型图的重复
        遍历（实测14亿次调用）。类型的实例化一律通过instantiation
        创建新对象，不原地修改，共享是安全的。
        """
        memo[id(self)] = self
        return self

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
    def convertible_to(self, target: "TypeName",
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

    def convertible_to(self, target: "TypeName",
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

    def convertible_to(self, target: "TypeName",
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

INT32: BaseTypeName = BaseTypeName("int32", "i32")
# int是int32的别名：两者为同一个TypeName对象，完全等价（见开发疑问记录151）。
# 因此生成的C类型名为viola$lang$int32，int不再有自己的C类型
# （原先的viola$lang$int仍保留在runtime.h中，供手写C代码使用）。
INT: BaseTypeName = INT32
INT8: BaseTypeName = BaseTypeName("int8", "i8")
INT16: BaseTypeName = BaseTypeName("int16", "i16")
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

    与TypeName一致按名称比较：类型替换表（real_types）以泛型参数
    为键，同一泛型函数的参数在替换表内外以名称匹配。
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

    def convertible_to(self, target: "TypeName",
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
        # 函数返回值槽位：C层为指向返回变量的指针形参，
        # 赋值与读取时需要解引用
        self._is_return: bool = False

    @property
    def is_return(self) -> bool:
        """
        获取该变量是否为函数返回值槽位（C层为指针形参）。
        """
        return self._is_return

    @is_return.setter
    def is_return(self, value: bool) -> None:
        """
        设置该变量是否为函数返回值槽位。
        """
        self._is_return = value

    def as_ptr(self) -> str:
        """
        获取指向这一变量的指针。
        """
        return f"&{self.name}"

    @property
    def is_unsafe_managed(self) -> bool:
        """该变量是否由用户手动管理内存（unsafe成员，或其类型为unsafe的类）。

        unsafe变量不参与引用计数：既不retain也不release，其内存由用户在
        wrapper类的__del__中手动清理（手册"unsafe与wrapper"，
        见开发疑问记录191第4条）。
        """
        return getattr(self, "is_unsafe", False) or \
            (isinstance(self._type, ClassName) and self._type.is_unsafe)

    @property
    def is_member(self) -> bool:
        """该变量是否表示对象成员（`this.X = ...`形式的赋值目标，C名为`_thisObj->X`）。

        成员赋值不参与常量折叠：本块内对该成员的读取虽可由常量表替代，但对象
        可能在本块之外被读取（如构造函数把对象交给调用方、对象存入成员或数组），
        折叠掉赋值语句会使这些读取得到未初始化的值（见开发疑问记录193）。
        """
        return getattr(self, "_is_member", False)

    @property
    def is_discard(self) -> bool:
        """该变量是否为丢弃变量（赋值目标为`_`，C名形如`$_discard$<n>`）。

        丢弃变量的C名与源码名不同（源码名为`_`），其值无人读取、由返回元组或
        被调方处理，故既不参与常量折叠也不参与释放逻辑。
        """
        return getattr(self, "_is_discard", False)

    @property
    def free_text(self) -> str:
        """
        获取这一变量的释放文本。

        释放=递减引用计数，归零才真正析构（见开发疑问记录190）。变量持有一个对象
        即计一次数（分配处计1，赋值/传参写入返回值槽位时retain），故此处递减与
        持有成对；递减后不为0说明仍有其他槽位持有，由最后释放者负责析构。
        """
        if not self.is_object or self.is_unsafe_managed:
            # unsafe变量由用户手动管理内存，不参与引用计数（见开发疑问记录191）
            return ""
        del_call: str = f"{destructor_name(self._type)}({self.name}, listener);"
        return f"{release_text(self.name, del_call)} {self.name} = NULL;"

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
    def declaration_text(self) -> str:
        """获取将该变量作为局部变量声明的代码文本。

        对象类型的局部变量初始化为NULL：块的清理代码以`if (var)`判断变量
        是否持有对象，若声明处不给初值，异常路径上尚未赋值的变量会保留栈上
        的垃圾值，清理时被误判为有效对象而崩溃（见开发疑问记录84）。
        """
        if self.is_object:
            return f"{self.type_name_pair_calling} = NULL;"
        return f"{self.type_name_pair_calling};"

    @property
    def definition_text(self) -> str:
        """获取将该变量定义在文件作用域（模块级全局变量）的代码文本。

        不带初值：文件作用域的静态存储本就零初始化，故无需declaration_text中
        对象类型的"= NULL"。存储确实由本模块提供的模块级变量（有初值，或本模块
        给它赋过值）使用本形式；其余（无初值且本模块从未赋值）只是声明，其存储
        由其他翻译单元提供（典型情形是运行库的C实现），生成extern声明而非定义，
        以免与那份定义重复（见开发疑问记录168）。
        """
        return f"{self.type_name_pair_calling};"

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
        # 模块级访问修饰符（0.1起，默认public）
        self._modifier: Modifier = Modifier.PUBLIC

    @property
    def modifier(self) -> Modifier:
        """
        获取该全局变量的模块级访问修饰符。
        """
        return self._modifier

    @modifier.setter
    def modifier(self, value: Modifier) -> None:
        """
        设置该全局变量的模块级访问修饰符。
        """
        self._modifier = value


class Modifier(Enum):
    """
    访问权限（0.1起按模块语义解释）。
    public: 任何其他模块都可以访问。
    protected: 只能被同一模块中的其他成员访问。
    private: 只能被自身（类成员为类自身，模块成员为模块自身）访问。
    无访问修饰符的默认情况为public。
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
        # 模块级访问修饰符（0.1起，默认public）
        self._modifier: Modifier = Modifier.PUBLIC
        # 泛型实例的来源信息：用于在泛型类的成员签名中出现"本类/其他泛型类
        # 以泛型参数实例化"的类型（如Array<T>中的Array::<T>）时，在所属泛型类
        # 实例化后替换为具体实例（见开发疑问记录102）
        self._generic_origin: Optional["ClassName"] = None
        self._generic_actual_args: tuple[TypeName, ...] = ()
        self._generic_table: Optional["GenericTable"] = None

    @property
    def modifier(self) -> Modifier:
        """
        获取该类的模块级访问修饰符。
        """
        return self._modifier

    @modifier.setter
    def modifier(self, value: Modifier) -> None:
        """
        设置该类的模块级访问修饰符。
        """
        self._modifier = value

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

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, ClassName):
            if target.name == self.name or target.self_name == "object":
                return True
            self_parent: Optional["ClassName"] = self._parent
            while self_parent is not None:
                if self_parent == target:
                    return True
                self_parent = self_parent.parent
            if target.is_interface:
                # 接口实现的检查：本类（含祖先类）实现该接口即可赋值
                # （接口不在父类链上，见开发疑问记录170(c)）
                return any(interface.name == target.name for interface in self.all_interfaces)
            return False
        return False

    def instantiation(self, real_types: dict["GenericArgument", TypeName]) -> TypeName:
        # 检查是否有从原类到实例化类的映射（泛型实例化时添加）
        key = GenericArgument(self._src_info, self.name)
        if key in real_types:
            return real_types[key]
        if self._generic_origin is not None and self._generic_table is not None:
            # 泛型实例（可能是类型实参仍为泛型参数的伪实例）：
            # 先替换类型实参，再解析为具体实例
            new_args: tuple[TypeName, ...] = tuple(
                arg.instantiation(real_types) for arg in self._generic_actual_args)
            if any(isinstance(arg, GenericArgument) for arg in new_args):
                # 类型实参尚未完全确定：保持伪实例，待所属泛型类实例化后再替换
                return self
            origin_key = GenericArgument(self._src_info, self._generic_origin.name)
            if origin_key in real_types:
                # 本类自身的实例（如Array<T>内签名中的Array::<T>）：
                # 直接取本次实例化的目标类，避免重入实例化
                return real_types[origin_key]
            return self._generic_table.get_cls_instance(self._generic_origin, new_args)
        return self

    def mark_generic_instance(self, origin: "ClassName", actual_args: tuple[TypeName, ...],
                              generic_table: "GenericTable") -> None:
        """标记为泛型实例，记录其来源泛型类与类型实参。

        用于成员签名中引用泛型类（含本类）自身实例的类型替换，
        以及尚未实例化的伪实例（类型实参仍为泛型参数）的后续解析。
        """
        self._generic_origin = origin
        self._generic_actual_args = actual_args
        self._generic_table = generic_table

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

    def instantiation_full(self, new_name: str, args: list[TypeName],
                           on_shell: Optional[Callable[["ClassName"], None]] = None) -> "ClassName":
        """
        完全实例化，也就是将所有泛型参数都替换为实际类型。
        new_name: 新的类名。
        args: 泛型参数的实参。
        on_shell: 可选的壳回调；在成员填充前以新实例调用，
            使调用方可以先登记该实例（打破成员签名中的自引用递归，
            见开发疑问记录102）。
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
        if on_shell is not None:
            on_shell(result)
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
    def all_interfaces(self) -> list["ClassName"]:
        """获取该类（含其祖先类）实现的全部接口，以及这些接口自身继承的接口。

        接口只由声明它的类以`impl`/`extends`列出，不随继承自动复制到子类的
        _interfaces中，故此处沿父类链与接口自身的父链/接口表求并集：
        - 声明接口变量的赋值检查（convertible_to）需要它；
        - 该类为虚方法分派生成的"接口->槽位数组"表（见ClassDef）需要为
          继承自父类的接口同样提供条目。
        以访问集合防止接口之间循环继承时无限递归。
        """
        result: list["ClassName"] = []
        visited: set[str] = set()
        self._collect_interfaces(result, visited)
        return result

    def _collect_interfaces(self, result: list["ClassName"], visited: set[str]) -> None:
        """把本类、祖先类与各接口所继承的接口依次加入result（去重，见all_interfaces）。"""
        visited.add(self.name)
        # 接口的父链也是接口（接口的extends列表中首个为父接口，见_read_class_decl）
        if self._parent is not None and self._parent.is_interface \
                and self._parent.name not in visited:
            visited.add(self._parent.name)
            result.append(self._parent)
            self._parent._collect_interfaces(result, visited)
        for interface in self._interfaces:
            if interface.name in visited:
                continue
            visited.add(interface.name)
            result.append(interface)
            interface._collect_interfaces(result, visited)
        # 类的父类是类：沿父链收集祖先类实现的接口
        if self._parent is not None and not self._parent.is_interface \
                and self._parent.name not in visited:
            visited.add(self._parent.name)
            self._parent._collect_interfaces(result, visited)

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

    @property
    def ordered_properties(self) -> list[PropertyVariableName]:
        """获取按C结构体布局排序的属性列表（父类属性在前）。

        子类实例在C层必须与其父类具有相同的字段前缀布局，否则以父类类型
        （如Exception、或泛型父类）操作子类对象时会按父类的字段偏移读写，
        得到错误的字段（异常捕获时的$$vtable读取即依赖该布局）。
        同名属性（属性遮蔽）保留父类中的位置，类型以子类的声明为准。
        继承链一直到object（$refCount、$parent位于最前）：运行库以
        viola$lang$object*操作对象（以及运行库为wrapper类提供结构体定义）
        时依赖该布局，见开发疑问记录113。
        """
        ordered: dict[str, PropertyVariableName] = {}
        if self._parent is not None:
            for prop in self._parent.ordered_properties:
                ordered[prop.self_name] = prop
        for name, prop in self._properties.items():
            ordered[name] = prop
        return list(ordered.values())

    @property
    def is_generic_instance(self) -> bool:
        """获取本类是否为泛型类实例化得到的类（如Array::<int>的Array__1）。

        泛型实例的方法其C名称由实例化过程产生，同一方法在符号表中可能同时存在
        实例化前后的多个名字（见开发疑问记录102），按名称引用其实现不可靠，
        故泛型实例不参与虚方法分派（见开发疑问记录161）。
        """
        return self._generic_origin is not None

    @property
    def has_vtable_property(self) -> bool:
        """获取本类的实例结构体是否含$$vtable字段。

        编译器生成的类（含异常类）都有该字段（由_read_class_decl添加，
        见symbol.py中"实例中保存其类型的TypeInfo指针"）；编译器内置的
        string等类型与运行库共用C结构体，其布局中没有该字段，故不能经
        $$vtable分派（见开发疑问记录170(a)）。
        """
        return "$$vtable" in self._properties

    @property
    def virtual_slots(self) -> list[tuple[str, tuple[str, ...]]]:
        """获取虚方法槽位表（父类槽位在前，其后为本类新增的槽位）。

        槽位身份为（方法名，不含接收者的形参类型名元组）：子类重写的方法与
        父类方法身份相同，占用同一槽位。因此派生类的槽位表以父类的槽位表为
        前缀，二者的同一下标指向同一虚方法（见开发疑问记录161）。

        不缓存结果：泛型实例化先登记空壳、再填充成员（见开发疑问记录102），
        缓存会在成员填充之前形成错误（偏少）的槽位表。

        泛型实例不参与虚方法分派：其方法名与调用点不一致的问题（实例化时恒用
        重载序号0）已修复（见开发疑问记录170(b)），但直接放开会让
        Array::<int>这类实例在运行期崩溃（$$vtable尚未就绪），故保持现状，
        待虚函数表对泛型实例一并就绪后再放开。
        """
        if self.is_generic_instance:
            return []
        slots: list[tuple[str, tuple[str, ...]]] = []
        if self._parent is not None:
            slots.extend(self._parent.virtual_slots)
        for (name, _), method in self._methods.items():
            if not method.is_virtual:
                continue
            identity: tuple[str, tuple[str, ...]] = (name, method.virtual_arg_types)
            if identity not in slots:
                slots.append(identity)
        return slots

    def virtual_slot_index(self, identity: tuple[str, tuple[str, ...]]) -> Optional[int]:
        """获取虚方法身份对应的槽位下标（不参与虚方法分派时为None）。"""
        slots: list[tuple[str, tuple[str, ...]]] = self.virtual_slots
        if identity not in slots:
            return None
        return slots.index(identity)

    def virtual_slot_impl(self, index: int) -> Optional["MethodName"]:
        """获取本类中实现指定槽位的方法（本类与父类都未实现时为None）。

        本类的实现优先；否则取父类同一下标的实现（继承链上父类的槽位表
        是本类槽位表的前缀）。抽象方法没有实现，返回None——该槽位在虚函数
        表中为NULL，由实现它的子类填入。

        "本类的实现"按方法的C名称判断是否属于本类：泛型实例化的方法其cls仍指向
        泛型类模板（见开发疑问记录102），不能按cls判断；而继承自父类的副本其
        C名称以父类开头，故按名称前缀区分。
        """
        identity: tuple[str, tuple[str, ...]] = self.virtual_slots[index]
        own_prefix: str = self.name + "$"
        # noinspection PyUnresolvedReferences
        for (name, _), method in self._methods.items():
            if not method.is_virtual or method.is_abstract:
                continue
            if method.cls is not self and not method.name.startswith(own_prefix):
                continue
            if (name, method.virtual_arg_types) == identity:
                return method
        if self._parent is not None and not self._parent.is_generic:
            parent_slots: list[tuple[str, tuple[str, ...]]] = self._parent.virtual_slots
            if index < len(parent_slots) and parent_slots[index] == identity:
                return self._parent.virtual_slot_impl(index)
        return None

    def method_implementation(self, identity: tuple[str, tuple[str, ...]]) -> Optional["MethodName"]:
        """按虚方法身份获取本类（含祖先类）的实现（无则返回None）。

        与virtual_slot_impl的区别是按下标查找，本方法按身份查找：
        接口的槽位表由接口自身的方法顺序决定，与实现类的槽位表无关，
        故实现类需要按身份找到自己对该方法的实现（见开发疑问记录170(c)）。
        """
        own_prefix: str = self.name + "$"
        # noinspection PyUnresolvedReferences
        for (name, _), method in self._methods.items():
            if not method.is_virtual or method.is_abstract:
                continue
            if method.cls is not self and not method.name.startswith(own_prefix):
                continue
            if (name, method.virtual_arg_types) == identity:
                return method
        if self._parent is not None:
            return self._parent.method_implementation(identity)
        return None

    def interface_slots(self, interface: "ClassName") -> list[Optional["MethodName"]]:
        """获取本类对某接口各槽位的实现列表（未实现的位置为None）。

        下标与接口自身的virtual_slots一致，故同一个接口在所有实现类中的
        下标相同，接口类型的接收者据此分派（见开发疑问记录170(c)）。
        """
        return [self.method_implementation(identity) for identity in interface.virtual_slots]

    def shared_parent(
            self,
            other: TypeName
    ) -> Optional["ClassName"]:
        """
        获取公共父类（继承链上最近的公共祖先），没有则返回None。

        原先两处循环都追加固定的self.parent/other.parent而不是继承链的下一项：
        父类不为None时（即类有父类）循环永不结束，追加到内存耗尽
        （MemoryError，见开发疑问记录156——混合基类对象与子类对象的数组字面量
        即会触发）。
        """
        if not isinstance(other, ClassName):
            return None
        self_parents: list[Optional[ClassName]] = [self]
        while self_parents[-1] is not None:
            self_parents.append(self_parents[-1].parent)
        self_parents.pop()
        other_parents: list[Optional[ClassName]] = [other]
        while other_parents[-1] is not None:
            other_parents.append(other_parents[-1].parent)
        other_parents.pop()
        common: list[ClassName] = list(filter(lambda x: x in other_parents, self_parents))
        return common[0] if len(common) > 0 else None

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
# 数组类型定义注册表：C类型名 -> 数组类型对象（生成typedef与各方法的C实现；
# 数组类型对象本身也要参与生成——方法的形参/返回值类型由_array_method_descs
# 给出TypeName对象，见开发疑问记录153）
_ARRAY_TYPE_DEFS: dict[str, ArrayTypeName] = {}

# 泛型函数实例化请求的全局注册表（按函数的C名 -> 类型参数元组集合）。
# 实例化请求发生在调用方模块，而泛型函数的定义位于其所在模块，
# 定义方实例化时需合并其他模块发起的请求。
_GENERIC_FUNC_INSTANCE_REQUESTS: dict[str, set[tuple[TypeName, ...]]] = {}

# 泛型类实例化请求的全局注册表（按类的C名 -> 类型参数元组集合）。
# 与泛型函数同理：调用方模块只能提出请求，实例的定义必须由定义该泛型类的
# 模块生成（见开发疑问记录111）。
_GENERIC_CLS_INSTANCE_REQUESTS: dict[str, set[tuple[TypeName, ...]]] = {}

# 泛型实例的C名序号注册表（泛型符号C名 -> {(类型实参C名, ...): 序号}）。
# 实例的C名形如Array__0、lib$identity$_0，序号原先取决于“该模块内第几个
# 被实例化”，因此调用方模块与定义方模块会各自按自己的顺序编号，得到
# 不同的C名（实测跨模块泛型函数会因此调用到错误的实例，见开发疑问记录111）。
# 改用进程内共享的注册表按（泛型符号C名, 类型实参）分配序号，使所有模块
# 对同一实例得到相同的C名。
_GENERIC_INSTANCE_INDEXES: dict[str, dict[tuple[str, ...], int]] = {}
# 泛型注册表（上述请求表与序号表）在并行编译的多个线程间共享，需互斥访问：
# 1) 两个线程同时登记不同的类型实参时会读到相同的len()，使不同实例取得
#    同一序号（C名冲突）；
# 2) 一个线程遍历请求集合（合并请求、排序）时另一个线程可能正在登记新请求，
#    遍历中集合被修改会抛RuntimeError，使编译偶发失败。
_GENERIC_REGISTRY_LOCK: threading.Lock = threading.Lock()

# 符号表在调试标记占位名中的区分序号。
# 标记名中的编号按符号表（即按模块）分配，以保证生成产物与编译线程的调度
# 无关（见开发疑问记录117）；但一个编译单元中可能混入由其他符号表生成的
# 标记（例如泛型实例以调用方的符号表生成、却写入了定义方的文件），两个
# 符号表的编号会重名。故占位名中加入符号表序号使其在进程内唯一，写出时
# 再按编译单元统一重编号（见开发疑问记录123）。
_MARK_TABLE_INDEXES_LOCK: threading.Lock = threading.Lock()
_MARK_TABLE_INDEXES: int = 0


def _next_mark_table_index() -> int:
    """分配一个进程内唯一的符号表序号（用于调试标记占位名）。"""
    global _MARK_TABLE_INDEXES
    with _MARK_TABLE_INDEXES_LOCK:
        result: int = _MARK_TABLE_INDEXES
        _MARK_TABLE_INDEXES += 1
        return result


def _generic_instance_index(symbol_c_name: str, arg_names: tuple[str, ...]) -> int:
    """获取泛型实例的C名序号（同一进程内对同一实例始终返回同一序号）。"""
    with _GENERIC_REGISTRY_LOCK:
        index_table: dict[tuple[str, ...], int] = _GENERIC_INSTANCE_INDEXES.setdefault(symbol_c_name, {})
        if arg_names not in index_table:
            index_table[arg_names] = len(index_table)
        return index_table[arg_names]


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
    _ARRAY_TYPE_DEFS[t.c_alloc_name] = t


def _collect_class_names(t: TypeName, result: set[str]) -> None:
    """递归收集类型中引用的类类型C名称（用于生成头文件前置声明）。"""
    if isinstance(t, ArrayTypeName):
        # 数组类型的结构体定义自带include guard，无需前置声明
        _collect_class_names(t.element_type, result)
    elif isinstance(t, ClassName):
        result.add(t.name)
    elif isinstance(t, TupleTypeName):
        for e in t.types:
            _collect_class_names(e, result)
    elif isinstance(t, FunctionTypeName):
        for e in t.args + t.returns:
            _collect_class_names(e, result)


# 类型定义在头文件中的类别优先级（仅用于同层排序）：
# 数组 -> 同步函数指针 -> 元组 -> 异步函数指针
_TYPEDEF_CATEGORY_ARRAY: int = 0
_TYPEDEF_CATEGORY_FUNC_SYNC: int = 1
_TYPEDEF_CATEGORY_TUPLE: int = 2
_TYPEDEF_CATEGORY_FUNC_ASYNC: int = 3

_TYPE_DEF_ORDER_LOGGER: Logger = Logger("Type Def Order")


def _referenced_type_def_names(t: TypeName) -> set[str]:
    """获取类型t的C声明所直接引用的其他类型定义名。

    类类型的结构体由各模块头文件提供（调用方已按type_def_class_names()生成
    前置声明），同步函数类型的C表示为Function结构体指针，二者都不属于本文件
    的类型定义注册表，因此返回空集。
    """
    if isinstance(t, ArrayTypeName):
        # 元素的C声明形如"<元素名>$$array *"，元素为数组时引用其typedef
        return {t.c_alloc_name}
    if isinstance(t, TupleTypeName):
        return {t.name}
    if isinstance(t, AsyncFuncTypeName):
        return {t.name}
    return set()


def _type_def_dependencies(category: int, name: str) -> set[str]:
    """获取某个已注册类型定义所直接引用的其他类型定义名。"""
    result: set[str] = set()
    if category == _TYPEDEF_CATEGORY_ARRAY:
        # 数组结构体的元素字段形如"<元素类型> data;"
        return _referenced_type_def_names(_ARRAY_TYPE_DEFS[name].element_type)
    if category == _TYPEDEF_CATEGORY_TUPLE:
        for e in _TUPLE_TYPE_DEFS[name].types:
            result |= _referenced_type_def_names(e)
        return result
    func: FunctionTypeName = _FUNCTION_TYPE_DEFS[name]
    if category == _TYPEDEF_CATEGORY_FUNC_SYNC:
        # 同步函数指针的参数与返回类型直接出现在其typedef中
        for e in func.args + func.returns:
            result |= _referenced_type_def_names(e)
        return result
    # 异步函数指针的参数为参数元组与返回元组
    return {TupleTypeName.c_name_of(func.args), TupleTypeName.c_name_of(func.returns)}


def ordered_type_def_keys() -> list[tuple[int, str]]:
    """按“先定义后引用”的确定性顺序获取全部类型定义（类别序号, 名称）。

    各注册表的插入顺序取决于并行编译的线程交错（见开发疑问记录117），直接
    遍历会使生成的头文件随线程调度而变。这里对类型定义做拓扑排序：被引用的
    定义先于引用者输出；同层按类别优先级（数组 -> 同步函数指针 -> 元组 ->
    异步函数指针）再按名称排序，因而输出与线程调度无关。
    """
    keys: set[tuple[int, str]] = set()
    for name, t in _FUNCTION_TYPE_DEFS.items():
        keys.add((_TYPEDEF_CATEGORY_FUNC_ASYNC if t._IS_ASYNC else _TYPEDEF_CATEGORY_FUNC_SYNC, name))
    keys |= {(_TYPEDEF_CATEGORY_TUPLE, name) for name in _TUPLE_TYPE_DEFS}
    keys |= {(_TYPEDEF_CATEGORY_ARRAY, name) for name in _ARRAY_TYPE_DEFS}
    # 类型定义的名称在各类别间前缀不同，不会重复；仍以（类别, 名称）为键以确保唯一
    name_to_key: dict[str, tuple[int, str]] = {key[1]: key for key in keys}
    deps: dict[tuple[int, str], set[tuple[int, str]]] = {}
    for key in keys:
        # 引用自身（如异步函数指针的参数元组为其自身）不构成依赖
        deps[key] = {name_to_key[n] for n in _type_def_dependencies(*key)
                     if n in name_to_key} - {key}
    dependents: dict[tuple[int, str], set[tuple[int, str]]] = {k: set() for k in keys}
    for key, key_deps in deps.items():
        for d in key_deps:
            dependents[d].add(key)
    remaining: dict[tuple[int, str], int] = {k: len(deps[k]) for k in keys}
    # 就绪队列按（类别, 名称）排序，使同层输出确定
    ready: list[tuple[int, str]] = [k for k in keys if remaining[k] == 0]
    heapq.heapify(ready)
    pushed: set[tuple[int, str]] = set(ready)
    result: list[tuple[int, str]] = []
    while len(ready) > 0:
        key = heapq.heappop(ready)
        result.append(key)
        for nxt in sorted(dependents[key]):
            remaining[nxt] -= 1
            if remaining[nxt] == 0 and nxt not in pushed:
                pushed.add(nxt)
                heapq.heappush(ready, nxt)
    if len(result) < len(keys):
        # 互为前提的类型定义在C层无法表示（如函数类型以自身为参数）。此时
        # 按（类别, 名称）追加剩余项，保证输出仍然确定，便于复现问题。
        rest: list[tuple[int, str]] = sorted(keys - set(result))
        _TYPE_DEF_ORDER_LOGGER.warning(
            f"Circular reference among type definitions, emitting {len(rest)} item(s) "
            f"in name order: {', '.join(map(lambda k: k[1], rest))[:200]}"
        )
        result.extend(rest)
    return result


def type_def_class_names() -> set[str]:
    """获取全局注册的类型定义（元组/函数指针/数组）所引用的类类型C名称。

    每个模块的头文件都会输出这些类型定义（带include guard），
    它们可能引用其他模块定义的类，因此需要在每个头文件中
    生成这些类的前置声明（typedef struct X X;）。
    """
    result: set[str] = set()
    for t in _TUPLE_TYPE_DEFS.values():
        for e in t.types:
            _collect_class_names(e, result)
    for t in _FUNCTION_TYPE_DEFS.values():
        for e in t.args + t.returns:
            _collect_class_names(e, result)
    for arr_type in _ARRAY_TYPE_DEFS.values():
        _collect_class_names(arr_type.element_type, result)
    return result


class ArrayMethodDesc:
    """内置数组类型的一个方法的描述（方法注册、同步声明、同步实现与$async包装
    的唯一来源，见开发疑问记录148、153）。

    args/rets的元素为二元组(TypeName对象, 形参/返回值名)：
    - TypeName对象：既用于构造方法的FunctionTypeName（供调用解析），
      也用于生成C文本（c_calling_name）与异步实参/返回元组的成员类型名
      （TypeName.name，见expression.py的CallOp._async_arg_types/_async_ret_types）。
    表中只引用已存在的TypeName对象（SIZE_T、SliceTypeName、INT64、元素类型与
    数组类型自身），不构造新的类型对象，故在输出阶段求值也不会注册新类型、
    影响已生成的类型定义顺序（见开发疑问记录117）。

    body为同步实现的C语句模板（不含函数首行与结尾的"}"）；与元素类型相关的
    文本写作占位符，由SymbolTable._array_method_body_text替换（表因此同时是同步
    声明的来源：声明与实现的首行由同一个_array_sync_signature_text生成）。
    新增方法时只需在此表添加一项。
    """

    def __init__(self, suffix: str, args: Optional[list[tuple[TypeName, str]]] = None,
                 rets: Optional[list[tuple[TypeName, str]]] = None,
                 body: Optional[list[str]] = None,
                 modifier: Modifier = Modifier.PUBLIC) -> None:
        self.suffix: str = suffix
        self.args: list[tuple[TypeName, str]] = args if args is not None else []
        self.rets: list[tuple[TypeName, str]] = rets if rets is not None else []
        self.body: list[str] = body if body is not None else []
        self.modifier: Modifier = modifier

    @property
    def name(self) -> str:
        """获取方法名（不含重载序号，如__getitem__；序号在suffix中）。"""
        return self.suffix.split("$_")[0]


def _array_method_descs(arr_type: "ArrayTypeName") -> list[ArrayMethodDesc]:
    """获取内置数组类型的方法表（方法注册、同步声明、同步实现与$async包装的
    唯一来源，见开发疑问记录148、153）。

    接收者（_this）不在表中：它总是形参元组的第一个成员，类型即数组类型自身。
    方法的先后顺序即$this$_{重载序号}的序号来源：ArrayTypeName构造时按本表的
    顺序注册方法，故两者不会错配，不可随意调换本表的顺序。
    定义在模块级而非SymbolTable中：ArrayTypeName的构造（模块导入期间即会发生，
    如StringTypeName的data属性为uint16[]）要调用本表，此时SymbolTable尚未定义。
    """
    elem: TypeName = arr_type.raw_element_type
    return [
        ArrayMethodDesc(
            "__getitem__$_0", [(SIZE_T, "item")],
            [(elem, "element")],
            body=[
                "@check_index_get@",
                "\t*element = _this->data[item];",
                # 取出的元素交给调用方的槽位持有：该槽位释放时会递减，
                # 故此处先计一次数（见开发疑问记录190）
                "@elem_retain@(*element);",
            ]),
        ArrayMethodDesc(
            "__getitem__$_1", [(SliceTypeName, "s")],
            [(arr_type, "subarray")],
            body=[
                "\tviola$lang$uint64 start = s->start;",
                "\tviola$lang$uint64 end = s->end > _this->size ? _this->size : s->end;",
                "\tviola$lang$uint64 step = s->step;",
                # 结果对象先分配：步长为0的上报路径上也要给出确定值（空切片），
                # 因为调用方的表达式求值可能有后续语句先于异常跳转执行
                # （越界下标检查同理给出确定的元素值，见开发疑问记录124）
                "\t@new_result@",
                "@check_slice_step@",
                "\tviola$lang$uint64 count = start < end ? (end - start + step - 1) / step : 0;",
                "\tnewResult->size = count;",
                "\tnewResult->data = count == 0 ? NULL : (@elem_assigning@)malloc(@elem_size@ * count);",
                "\tviola$lang$uint64 j = 0;",
                "\tfor (viola$lang$uint64 i = start; i < end; i += step) "
                "{ newResult->data[j] = _this->data[i]; @elem_retain@(newResult->data[j]); j++; }",
                "\t*subarray = newResult;",
            ]),
        ArrayMethodDesc(
            "concat$_0", [(arr_type, "other")],
            [(arr_type, "result")],
            body=[
                "\t@new_result@",
                "\tnewResult->size = _this->size + other->size;",
                "\tnewResult->data = newResult->size == 0 ? NULL : "
                "(@elem_assigning@)malloc(@elem_size@ * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) "
                "{ newResult->data[i] = _this->data[i]; @elem_retain@(newResult->data[i]); }",
                "\tfor (viola$lang$uint64 i = 0; i < other->size; i++) "
                "{ newResult->data[_this->size + i] = other->data[i]; "
                "@elem_retain@(newResult->data[_this->size + i]); }",
                "\t*result = newResult;",
            ]),
        ArrayMethodDesc(
            "append$_0", [(elem, "newElement")],
            [(arr_type, "newArray")],
            body=[
                "\t@new_result@",
                "\tnewResult->size = _this->size + 1;",
                "\tnewResult->data = (@elem_assigning@)malloc(@elem_size@ * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) "
                "{ newResult->data[i] = _this->data[i]; @elem_retain@(newResult->data[i]); }",
                "\tnewResult->data[_this->size] = newElement;",
                "\t@elem_retain@(newElement);",
                "\t*newArray = newResult;",
            ]),
        ArrayMethodDesc(
            "insert$_0", [(INT64, "location"), (elem, "newElement")],
            [(arr_type, "newArray")],
            body=[
                "\tviola$lang$uint64 loc = location < 0 ? 0 : (viola$lang$uint64)location;",
                "\tloc = loc > _this->size ? _this->size : loc;",
                "\t@new_result@",
                "\tnewResult->size = _this->size + 1;",
                "\tnewResult->data = (@elem_assigning@)malloc(@elem_size@ * newResult->size);",
                "\tfor (viola$lang$uint64 i = 0; i < loc; i++) "
                "{ newResult->data[i] = _this->data[i]; @elem_retain@(newResult->data[i]); }",
                "\tnewResult->data[loc] = newElement;",
                "\t@elem_retain@(newElement);",
                "\tfor (viola$lang$uint64 i = loc; i < _this->size; i++) "
                "{ newResult->data[i + 1] = _this->data[i]; @elem_retain@(newResult->data[i + 1]); }",
                "\t*newArray = newResult;",
            ]),
        ArrayMethodDesc(
            "length$_0", [],
            [(SIZE_T, "result")],
            body=[
                "\t*result = _this->size;",
            ]),
        ArrayMethodDesc(
            "__setitem__$_0", [(SIZE_T, "index"), (elem, "newElement")],
            [(arr_type, "newArray")],
            # 越界检查置于分配之前，越界时不分配新数组
            body=[
                "@check_index_set@",
                "\t@new_result@",
                "\tnewResult->size = _this->size;",
                "\tnewResult->data = newResult->size == 0 ? NULL : "
                "(@elem_assigning@)malloc(@elem_size@ * newResult->size);",
                # 下标处的旧元素随即被newElement取代，故该位置不计数（避免只增不减）
                "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) "
                "{ newResult->data[i] = _this->data[i]; "
                "if (i != index) { @elem_retain@(newResult->data[i]); } }",
                "\tnewResult->data[index] = newElement;",
                "\t@elem_retain@(newElement);",
                "\t*newArray = newResult;",
            ]),
        ArrayMethodDesc(
            "__setitem__$_1", [(SliceTypeName, "s"), (arr_type, "newSubarray")],
            [(arr_type, "newArray")],
            body=[
                "\tviola$lang$uint64 start = s->start;",
                "\tviola$lang$uint64 end = s->end > _this->size ? _this->size : s->end;",
                "@check_slice_range@",
                "\t@new_result@",
                "\tnewResult->size = _this->size - (end - start) + newSubarray->size;",
                "\tnewResult->data = newResult->size == 0 ? NULL : "
                "(@elem_assigning@)malloc(@elem_size@ * newResult->size);",
                "\tviola$lang$uint64 j = 0;",
                "\tfor (viola$lang$uint64 i = 0; i < start; i++) "
                "{ newResult->data[j] = _this->data[i]; @elem_retain@(newResult->data[j]); j++; }",
                "\tfor (viola$lang$uint64 i = 0; i < newSubarray->size; i++) "
                "{ newResult->data[j] = newSubarray->data[i]; @elem_retain@(newResult->data[j]); j++; }",
                "\tfor (viola$lang$uint64 i = end; i < _this->size; i++) "
                "{ newResult->data[j] = _this->data[i]; @elem_retain@(newResult->data[j]); j++; }",
                "\t*newArray = newResult;",
            ]),
        ArrayMethodDesc(
            "__del__$_0",
            body=[
                # 调用方已递减至0（见开发疑问记录190），此处逐个释放元素后回收数组
                "\tif (_this->$refCount == 0) {",
                "\t\tif (_this->$parent) { ((viola$lang$uint32 *)_this->$parent)[0]--; }",
                "\t\telse {",
                "@elem_release_loop@",
                "\t\t\tfree(_this->data); _this->data = NULL;",
                "\t\t\tfree(_this); _this = NULL;",
                "\t\t}",
                "\t}",
            ],
            modifier=Modifier.PRIVATE),
    ]


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
        # 方法注册（调用解析所用）由方法表生成：形参/返回值的类型取自表中给出的
        # TypeName对象，重载序号由注册顺序决定（见开发疑问记录153）。原先这里与
        # 同步声明/实现各自维护一份方法列表，新增方法时两处易错配。
        for desc in _array_method_descs(self):
            self.add_method(desc.name, MethodName(
                src_info, c_cls, desc.name, FunctionTypeName(
                    src_info, [t for t, _ in desc.args], [t for t, _ in desc.rets]
                ), False, False, [n for _, n in desc.args], [n for _, n in desc.rets],
                desc.modifier, True, True
            ))
        register_array_type(self)
        self._check_method_names()

    def _check_method_names(self) -> None:
        """校验方法表给出的C名后缀（含重载序号）与注册结果一致。

        方法注册、同步声明、同步实现与$async包装都由方法表生成（见开发疑问记录
        148、153），但注册的C名中的重载序号由*注册顺序*决定，而声明/实现/包装
        的C名直接取自表中的suffix：若表中同一方法名的两项与序号不符（如把
        __getitem__$_0与$_1互换位置），生成代码与调用解析会按不同的函数名互相
        调用（要到gcc阶段才报出）。此处显式报出该情况。

        元素类型尚无法给出C名时（泛型参数如T[]、any等）跳过：此时表中同样无
        可比之名。
        """
        try:
            descs: list[ArrayMethodDesc] = _array_method_descs(self)
        except CompilerException:
            return
        methods: list["MethodName"] = list(self.methods.values())
        if len(methods) != len(descs):
            raise InternalCompilerException(
                f"Array type {self.c_alloc_name} registers {len(methods)} method(s), "
                f"but the method table has {len(descs)}.", self._src_info)
        for method, desc in zip(methods, descs):
            expected_name: str = f"{self.c_alloc_name}${desc.suffix}"
            if method.name != expected_name:
                raise InternalCompilerException(
                    f"Array type {self.c_alloc_name} registers method {method.name}, "
                    f"but the method table expects {expected_name}.", self._src_info)

    @property
    def c_alloc_name(self) -> str:
        return f"{self._element_type.name}$$array"

    @property
    def c_assigning_name(self) -> str:
        return f"{self._element_type.name}$$array **"

    @property
    def c_calling_name(self) -> str:
        return f"{self._element_type.name}$$array *"

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if target.name == "object":
            return True
        if not isinstance(target, ArrayTypeName):
            return False
        return self._element_type.convertible_to(target.element_type, symbol_dict)

    @property
    def element_type(self) -> TypeName:
        """
        获取元素类型。
        """
        return self._element_type

    @property
    def raw_element_type(self) -> TypeName:
        """获取元素类型，不校验其是否已知。

        EmptyArrayTypeName（空数组字面量）的element_type属性会报错（元素类型
        尚待推断），而方法表与方法注册在推断之前就要构建（空数组字面量在推断
        出元素类型前也要能解析其方法，见开发疑问记录153）。
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

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        return super().convertible_to(target, symbol_dict) or isinstance(target, ArrayTypeName)

    @property
    def element_type(self) -> TypeName:
        raise CompilerException("Element type not specified", self._src_info)

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return self

    @property
    def used_types(self) -> set["TypeName"]:
        return set()


class TypeAliasName(TypeName):
    """类型别名（using 别名 = 类型;，见开发疑问记录157）。

    别名在符号表中是独立条目：以别名自身的限定名注册，并保存被别名类型的名称
    （target_name），因此可以查询"这个别名指向哪个类型"，便于调试（见
    SymbolTable.type_aliases）。

    类型名的查找一律解析到被别名的类型（SymbolTable._resolve_alias），因此别名
    在编译期完全透明：类型检查、方法查找与生成的C代码都按被别名的类型进行，
    别名自身不生成任何C代码。解析结果缓存于_resolved（同一别名对象可能被反复
    查找），各类型接口委托给它，使得即便别名未被解析也不会静默地按错误类型处理。
    """

    def __init__(self, src_info: SourceInfo, namespace: list[NamespaceName], name: str, target_name: str,
                 modifier: Modifier = Modifier.PUBLIC) -> None:
        """
        创建类型别名。
        src_info: 源代码信息。
        namespace: 命名空间。
        name: 别名的名称。
        target_name: 被别名类型的名称（限定名）。
        modifier: 模块级访问修饰符。
        """
        super().__init__(src_info, namespace, name, SymbolType.CLASS)
        self._target_name: str = target_name
        self._resolved: Optional[TypeName] = None
        self._is_resolving: bool = False
        self._modifier: Modifier = modifier

    @property
    def modifier(self) -> Modifier:
        """
        获取该别名的模块级访问修饰符。
        """
        return self._modifier

    @modifier.setter
    def modifier(self, value: Modifier) -> None:
        """
        设置该别名的模块级访问修饰符。
        """
        self._modifier = value

    @property
    def target_name(self) -> str:
        """
        获取被别名类型的名称（解析前的记载，供调试查询）。
        """
        return self._target_name

    @property
    def resolved(self) -> Optional["TypeName"]:
        """
        获取已解析的被别名类型（尚未解析时为None）。
        """
        return self._resolved

    @property
    def is_resolving(self) -> bool:
        """
        获取本别名是否正在解析中（用于检出循环别名）。
        """
        return self._is_resolving

    def set_resolving(self) -> None:
        """
        标记本别名开始解析（由SymbolTable在查找时调用）。
        """
        self._is_resolving = True

    def set_resolved(self, target: "TypeName") -> None:
        """
        记录解析结果（由SymbolTable在查找时调用）。
        """
        self._resolved = target
        self._is_resolving = False

    @property
    def _target(self) -> "TypeName":
        """
        获取被别名的类型，未解析时报错。
        """
        if self._resolved is None:
            raise InternalCompilerException(f"Type alias {self.raw_name} is not resolved.", self._src_info)
        return self._resolved

    @property
    def c_alloc_name(self) -> str:
        return self._target.c_alloc_name

    @property
    def c_assigning_name(self) -> str:
        return self._target.c_assigning_name

    @property
    def c_calling_name(self) -> str:
        return self._target.c_calling_name

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        return self._target.convertible_to(target, symbol_dict)

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return self._target.instantiation(real_types)

    @property
    def is_generic(self) -> bool:
        return self._target.is_generic

    @property
    def is_object(self) -> bool:
        return self._target.is_object

    @property
    def short_name(self) -> str:
        return self._target.short_name

    @property
    def used_types(self) -> set["TypeName"]:
        return self._target.used_types


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

    def convertible_to(self, target: "TypeName",
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
            viola$lang$atomic_uint32 $refCount;
            viola$lang$ptr $parent;
            viola$lang$uint64 size;
            <元素0的c_calling_type> $0;
            ...
        } viola$collections$Tuple$<元素0名>$<元素1名>$...;
    结构体定义由编译器在模块头文件中生成（带include guard）。
    成员名为$0、$1……（下标从0开始），类类型元素的成员类型为T *，
    基本类型元素的成员类型为T。
    """

    @staticmethod
    def c_name_of(types: list[TypeName]) -> str:
        """获取元组类型的C名称（不构造对象，因而不产生注册等副作用）。"""
        return TUPLE_T + "$" + "$".join(list(map(lambda t: t.name, types)))

    def __init__(self, src_info: SourceInfo, types: list[TypeName]) -> None:
        c_name: str = TupleTypeName.c_name_of(types)
        super().__init__(src_info, [], c_name, None, False, False)
        self._type_args: list[TypeName] = types
        # 注册到符号表，以便在头文件中生成结构体定义
        register_tuple_type(self)

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
        $del（析构函数指针，位于成员之前）由分配处写入本类型按元素类型单态化的
        析构函数；释放元组的代码只调用运行库的固定名字转发（见destructor_name），
        故释放代码的文本不含元素类型名（见开发疑问记录192）。析构函数的声明
        一并输出（实现位于__main__.c），供分配处与运行库之外的调用方使用。
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
            "\tviola$lang$atomic_uint32 $refCount;",
            "\tviola$lang$ptr $parent;",
            "\tviola$lang$uint64 size;",
            f"\t{TUPLE_DEL_FIELD_T}",
            members,
            f"}} {self.name};",
            tuple_del_decl_text(self.name),
            "#endif"
        ])

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, TupleTypeName):
            if len(self.types) != len(target.types):
                return False
            return all(list(map(lambda t, u: t.convertible_to(u, symbol_dict), self._type_args, target.types)))
        if isinstance(target, ClassName) and target.self_name == "object":
            # 0.1起：所有元组均为object类的子类
            return True
        return False

    def has_method(self, name: str) -> bool:
        """元组的析构方法由编译器按元素类型生成（单态化，见开发疑问记录192）。"""
        if name == "__del__":
            return True
        return super().has_method(name)

    def instantiation(self, real_types: dict["GenericArgument", "TypeName"]) -> "TypeName":
        return TupleTypeName(self._src_info, list(map(lambda t: t.instantiation(real_types), self.types)))

    @property
    def methods(self) -> dict[tuple[str, tuple[TypeName, ...]], "MethodName"]:
        """获取方法表。元组的__del__方法为按元素类型生成的析构（单态化）。"""
        result: dict[tuple[str, tuple[TypeName, ...]], MethodName] = dict(self._methods)
        if "__del__" not in map(lambda x: x[0], result.keys()):
            result[("__del__", ())] = _get_tuple_del_method(self)
        return result

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

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple["TypeName", ...]]], NamedSymbol]) -> bool:
        if self._real_type is None:
            raise CompilerException("Can not infer type.", self._src_info)
        return self._real_type.convertible_to(target, symbol_dict)

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
        return sanitize_c_identifier(t.name)

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
        # 函数类型的值以Function结构体表示；返回值槽为指向Function的指针
        return f"{FUNCTION_T} **"

    @property
    def c_calling_name(self) -> str:
        # 函数类型的值（参数、变量）在C层为Function结构体指针
        return f"{FUNCTION_T} *"

    def c_calling_name_with_var(self, var_name: str) -> str:
        """
        函数类型变量声明。
        """
        return f"{FUNCTION_T} *{var_name}"

    @property
    def call_ptr_cast_text(self) -> str:
        """获取按本签名直接调用普通函数时使用的函数指针类型转换文本。

        形如：void (*)(参数c_calling_name..., 返回c_assigning_name..., Listener *)
        与sync_ptr_cast_text的区别是不含末尾的捕获环境形参：虚方法槽位中存放的
        是普通函数（见开发疑问记录161）。
        """
        if len(self._args) == 0:
            args_text: str = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text: str = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        params: str = ", ".join(filter(lambda x: x != "", [args_text, returns_text, LISTENER_T + " *"]))
        return f"void (*)({params})"

    @property
    def sync_ptr_cast_text(self) -> str:
        """通过Function结构体syncPtr调用时使用的函数指针类型转换文本。

        形如：void (*)(参数c_calling_name..., 返回c_assigning_name..., Listener *, void *)
        末尾的void *为捕获环境参数（无捕获的静态函数包装入口会忽略它）。
        """
        if len(self._args) == 0:
            args_text: str = ""
        else:
            args_text = ", ".join(map(lambda t: t.c_calling_name, self._args))
        if len(self._returns) == 0:
            returns_text: str = ""
        else:
            returns_text = ", ".join(map(lambda t: t.c_assigning_name, self._returns))
        params: str = ", ".join(filter(lambda x: x != "", [args_text, returns_text, LISTENER_T + " *", "void *"]))
        return f"void (*)({params})"

    @property
    def async_ptr_cast_text(self) -> str:
        """通过Function结构体asyncPtr调用时使用的函数指针类型转换文本。

        形如：void (*)(参数元组（含末尾捕获元素）*, 返回元组*, Listener *)
        """
        args_tuple_name: str = TupleTypeName(self._src_info, self._args + [VOID_PTR]).c_calling_name
        returns_tuple_name: str = TupleTypeName(self._src_info, self._returns).c_calling_name
        return f"void (*)({args_tuple_name}, {returns_tuple_name}, {LISTENER_T} *)"

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, FunctionTypeName):
            return (self._args_tuple.convertible_to(target._args_tuple, symbol_dict) and
                    self._returns_tuple.convertible_to(target._returns_tuple, symbol_dict))
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
        # 枚举成员（如Color.RED）：按名称登记的全局变量，
        # 供AttrOp以静态属性的方式解析（见开发疑问记录160）
        self._properties: dict[str, VariableName] = {}

    @property
    def based_type(self) -> TypeName:
        """
        获取该枚举类型所基于的类型。
        """
        return self._based_type

    def add_property(self, prop: VariableName) -> None:
        """登记一个枚举成员。"""
        if prop.self_name in self._properties:
            raise CompilerException(f"Enum item {prop.self_name} already exists.", prop.src_info)
        self._properties[prop.self_name] = prop

    @property
    def properties(self) -> dict[str, VariableName]:
        """获取枚举成员表（成员名 -> 成员变量名）。"""
        return self._properties

    @property
    def c_alloc_name(self) -> str:
        return self._based_type.c_alloc_name

    @property
    def c_assigning_name(self) -> str:
        return self._based_type.c_assigning_name

    @property
    def c_calling_name(self) -> str:
        return self._based_type.c_calling_name

    def convertible_to(self, target: "TypeName",
                       symbol_dict: dict[tuple[str, Optional[tuple[TypeName, ...]]], NamedSymbol]) -> bool:
        if isinstance(target, EnumName):
            # 枚举之间按名称判断：基于类型相同的不同枚举是不同类型
            return self.name == target.name
        return self._based_type.convertible_to(target, symbol_dict)

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
        # 模块级访问修饰符（0.1起，默认public）
        self._modifier: Modifier = Modifier.PUBLIC

    @property
    def modifier(self) -> Modifier:
        """
        获取该函数的模块级访问修饰符。
        """
        return self._modifier

    @modifier.setter
    def modifier(self, value: Modifier) -> None:
        """
        设置该函数的模块级访问修饰符。
        """
        self._modifier = value

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
        returns_text = ", ".join(
            list(map(lambda t, r: f"{t.c_assigning_name} {r}", self.type.returns, self._ret_names)))
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
            self._default_params[name] = GlobalVariableName(self._src_info, self.as_namespace(), "$default$" + name,
                                                            var_type)

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
        # 注意：FunctionName.name已是含命名空间的全名，若直接当裸名传入会
        # 导致命名空间被重复拼接（viola$math$viola$math$dist$async）。
        # 此处按命名空间前缀剥离出裸名；self_name不能使用：方法经
        # MethodName.as_function()重命名后，self_name仍是重命名前的短名。
        namespace_prefix: str = "$".join(map(lambda n: n.name, function_name._namespace))
        full_name: str = function_name.name
        if namespace_prefix == "":
            local_name: str = full_name
        elif full_name.startswith(namespace_prefix + "$"):
            local_name = full_name[len(namespace_prefix) + 1:]
        else:
            local_name = full_name
        return cls(function_name._src_info, function_name._namespace, local_name + "$async",
                   AsyncFuncTypeName.from_function_type_name(function_name.type), function_name._arg_names,
                   function_name._ret_names, function_name._export, function_name._is_method,
                   function_name._is_native)


class MethodName(PropertyVariableName):
    """
    方法名称。
    """

    def __init__(self, src_info: SourceInfo, cls: ClassName, name: str, t: FunctionTypeName, is_abstract: bool,
                 is_static: bool, arg_names: list[str], ret_names: list[str], modifier: Modifier, export: bool,
                 is_native: bool = False, is_final: bool = False,
                 own_generic_args: Optional[list[str]] = None) -> None:
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
        own_generic_args: 方法自身声明的泛型参数（不含所在泛型类的泛型参数）；
            缺省时按函数类型中的泛型参数推断。
        """
        cls_generic_args: list[str] = cls.generic_args_str if cls.generic_args_str is not None else []
        t_generic_args: list[str] = t.generic_args_str if t.generic_args_str is not None else []
        # 方法自身声明的泛型参数：泛型类中的所有方法都会携带类的泛型参数，
        # 若以函数类型中的泛型参数判定，会把它们误当作泛型方法
        # （导致方法按空实参表登记而无法按参数类型查找，见开发疑问记录102）
        self._own_generic_args: list[str] = list(own_generic_args) if own_generic_args is not None \
            else list(t_generic_args)
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
                          self._function_name.export, own_generic_args=self._own_generic_args)

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
    def arg_names(self) -> list[str]:
        """
        获取方法的参数名称。
        """
        return self._function_name.arg_names

    @property
    def arg_types_dict(self) -> dict[str, TypeName]:
        """
        获取从参数名称到参数类型的字典。
        """
        return self._function_name.arg_types_dict

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
        获取该方法是否为泛型方法（自身声明了泛型参数）。

        注意：泛型类的方法类型中同样带有该类的泛型参数，但那不表示方法
        自身是泛型方法（见开发疑问记录102）。
        """
        return len(self._own_generic_args) > 0

    @property
    def method_name(self) -> str:
        """
        获取方法名。
        """
        return self._method_name

    @property
    def bare_name(self) -> str:
        """获取不含重载序号的方法名（如speak）。

        重载序号可能出现两次（声明时的前置序号与set_cls追加的序号），
        故需去掉末尾连续的序号。
        """
        return strip_trailing_overload_suffix(self._method_name)

    @property
    def virtual_arg_types(self) -> tuple[str, ...]:
        """获取虚方法身份中的形参类型名元组（不含接收者）。

        接收者在C层是首个形参，但它在基类与子类中分别是各自的类类型，
        故不能参与身份判定。
        """
        self._type: FunctionTypeName
        args: list[TypeName] = self._type.args if self._is_static else self._type.args[1:]
        return tuple(map(lambda t: t.name, args))

    @property
    def virtual_identity(self) -> tuple[str, tuple[str, ...]]:
        """获取虚方法身份（方法名 + 不含接收者的形参类型名）。

        子类重写的方法与父类方法身份相同，因而占用同一虚方法槽位
        （见开发疑问记录161）。
        """
        return self.bare_name, self.virtual_arg_types

    @property
    def is_virtual(self) -> bool:
        """获取该方法是否参与虚方法分派。

        以下方法不参与（保持按静态类型直接调用）：
        - 静态方法（含构造函数，其调用处的对象类型已由类型名确定）；
        - 析构函数：释放代码由编译器按静态类型生成，虚分派会与引用计数
          路径相互影响；
        - 原生方法：实现由运行库提供，不进入编译器生成的虚函数表；
        - 泛型方法：实现按实例化产生，C名称需在实例化后确定。
        见开发疑问记录161。
        """
        if self._is_static or self.is_native or self.is_generic:
            return False
        bare_name: str = self.bare_name
        return bare_name not in ("__new__", "__del__", "__new__super", "__del__super")

    def rebuild(self, func: FunctionName) -> "MethodName":
        """
        用另一个函数声明重建方法。
        """
        return MethodName(self._src_info, self._cls, self._self_name, func.type, self._is_abstract, self._is_static,
                          func.arg_names, func.ret_names, self._modifier, func.export,
                          own_generic_args=self._own_generic_args)

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
                          self._is_final,
                          own_generic_args=self._own_generic_args)

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

# 元组类型各自的析构方法（按C类型名缓存，惰性创建，避免与类型定义的循环依赖）
_TUPLE_DEL_METHODS: dict[str, MethodName] = {}


def _get_tuple_del_method(tuple_type: "TupleTypeName") -> MethodName:
    """获取（必要时创建）某个元组类型的析构方法。

    元组按元素类型单态化（见开发疑问记录192）：方法所在类以元组的C类型名为名，
    故C名称为`<元组C名>$__del__$_0`，实现由编译器按元素类型生成。
    """
    cached: Optional[MethodName] = _TUPLE_DEL_METHODS.get(tuple_type.name)
    if cached is not None:
        return cached
    src_info: SourceInfo = tuple_type.src_info
    c_cls: ClassName = ClassName(src_info, [], tuple_type.name, None, False, False)
    # 方法名以__del__$_0给出（重载序号由注册顺序决定，此处只有这一个析构）
    method: MethodName = MethodName(
        src_info, c_cls, "__del__$_0", FunctionTypeName(src_info, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
    _TUPLE_DEL_METHODS[tuple_type.name] = method
    return method


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
# 注意（开发疑问记录第38条）：内置构造函数的注册已移除，
# 构造函数在viola/language.vla等声明文件中声明（如string的__new__）。
StringTypeName.add_method(
    "__del__", MethodName(
        VIOLA_INIT, StringTypeName, "__del__", FunctionTypeName(VIOLA_INIT, [], []), False,
        False, [], [], Modifier.PRIVATE, True, True
    )
)


def _add_native_method(
        cls: ClassName, name: str, arg_types: list[TypeName], ret_types: list[TypeName],
        arg_names: list[str], ret_names: list[str], modifier: Modifier = Modifier.PUBLIC,
        is_static: bool = False
) -> None:
    """向内置类注册一个原生方法（实现由运行库提供）。"""
    cls.add_method(name, MethodName(
        VIOLA_INIT, cls, name, FunctionTypeName(VIOLA_INIT, arg_types, ret_types), False,
        is_static, arg_names, ret_names, modifier, True, True
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
# 0.1新增方法（实现于viola_libs/viola/lang/string.c，注册顺序决定重载序号）
_add_native_method(StringTypeName, "count", [StringTypeName], [UINT32], ["sub"], ["result"])
_add_native_method(StringTypeName, "find", [StringTypeName], [UINT32], ["sub"], ["result"])
_add_native_method(StringTypeName, "rfind", [StringTypeName], [UINT32], ["sub"], ["result"])
_add_native_method(StringTypeName, "index", [StringTypeName], [UINT32], ["sub"], ["result"])
_add_native_method(StringTypeName, "rindex", [StringTypeName], [UINT32], ["sub"], ["result"])
_add_native_method(StringTypeName, "float", [], [FLOAT64], [], ["result"])
_add_native_method(StringTypeName, "int", [], [INT64], [], ["result"])
_add_native_method(StringTypeName, "int", [UINT8], [INT64], ["base"], ["result"])
_add_native_method(StringTypeName, "fromInt", [INT64], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "fromInt", [INT64, UINT8], [StringTypeName], ["value", "base"], ["result"], is_static=True)
_add_native_method(StringTypeName, "fromFloat", [FLOAT64], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "isalnum", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isalpha", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isdecimal", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isdigit", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isidentifier", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "islower", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isnumeric", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isprintable", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isspace", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "isupper", [], [BOOL], [], ["result"])
_add_native_method(StringTypeName, "ljust", [UINT32, StringTypeName], [StringTypeName],
                   ["length", "fillChar"], ["result"])
_add_native_method(StringTypeName, "lstrip", [], [StringTypeName], [], ["result"])
_add_native_method(StringTypeName, "lstrip", [StringTypeName], [StringTypeName], ["toRemove"], ["result"])
_add_native_method(StringTypeName, "rjust", [UINT32, StringTypeName], [StringTypeName],
                   ["length", "fillChar"], ["result"])
_add_native_method(StringTypeName, "rstrip", [], [StringTypeName], [], ["result"])
_add_native_method(StringTypeName, "rstrip", [StringTypeName], [StringTypeName], ["toRemove"], ["result"])
_add_native_method(StringTypeName, "strip", [], [StringTypeName], [], ["result"])
_add_native_method(StringTypeName, "strip", [StringTypeName], [StringTypeName], ["toRemove"], ["result"])
_add_native_method(StringTypeName, "swapcase", [], [StringTypeName], [], ["result"])
_add_native_method(StringTypeName, "zfill", [UINT32], [StringTypeName], ["length"], ["result"])
_add_native_method(StringTypeName, "replace", [StringTypeName, StringTypeName, UINT32], [StringTypeName],
                   ["oldSub", "newSub", "count"], ["result"])

# 值到字符串的转换（见开发疑问记录166）：基本类型不是类、没有方法表，
# 故x.toString()按x的静态类型解析到这里的静态转换函数（_TO_STRING_HELPERS）。
# 注册顺序决定C名称中的重载序号，故新增项应追加在末尾。
_add_native_method(StringTypeName, "_int32ToString", [INT32], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_int64ToString", [INT64], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_uint32ToString", [UINT32], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_uint64ToString", [UINT64], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_float64ToString", [FLOAT64], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_boolToString", [BOOL], [StringTypeName], ["value"], ["result"], is_static=True)
_add_native_method(StringTypeName, "_stringToString", [StringTypeName], [StringTypeName], ["value"], ["result"],
                   is_static=True)
# 未定义toString的类的默认转换：返回"<类名>"（见开发疑问记录175(b)）
_add_native_method(StringTypeName, "_objectToString", [VOID_PTR], [StringTypeName], ["value"], ["result"],
                   is_static=True)

# x.toString()的类型映射：基本类型名 -> (string类上的静态转换函数名, 该函数的形参类型)。
# 较窄的整型/浮点型按C的隐式转换传给更宽的形参（见开发疑问记录166）。
_TO_STRING_HELPERS: dict[str, tuple[str, TypeName]] = {
    INT8.name: ("_int32ToString", INT32),
    INT16.name: ("_int32ToString", INT32),
    INT32.name: ("_int32ToString", INT32),
    INT64.name: ("_int64ToString", INT64),
    UINT8.name: ("_uint32ToString", UINT32),
    UINT16.name: ("_uint32ToString", UINT32),
    UINT32.name: ("_uint32ToString", UINT32),
    UINT64.name: ("_uint64ToString", UINT64),
    FLOAT.name: ("_float64ToString", FLOAT64),
    DOUBLE.name: ("_float64ToString", FLOAT64),
    FLOAT128.name: ("_float64ToString", FLOAT64),
    BOOL.name: ("_boolToString", BOOL),
    StringTypeName.name: ("_stringToString", StringTypeName),
}


def get_to_string_method(caller_type: TypeName) -> Optional[MethodName]:
    """获取把caller_type类型的值转换为字符串的静态方法（无则返回None）。

    见开发疑问记录166：基本类型不是类、没有方法表，x.toString()由编译器按
    x的静态类型解析到string类上的静态转换函数。

    见开发疑问记录175(b)：类类型的toString约定——类自身（含继承）定义了
    `fn toString() -> (string result);`时由其方法表解析（此处返回None），
    否则用默认转换返回类名。
    """
    helper: Optional[tuple[str, TypeName]] = _TO_STRING_HELPERS.get(caller_type.name)
    if helper is not None:
        return StringTypeName.methods.get((helper[0], (helper[1],)))
    if isinstance(caller_type, ClassName) and not caller_type.is_generic \
            and not caller_type.is_c_part:
        # 继承了toString的类由常规方法查找解析（含继承来的方法）
        if any(name == "toString" for (name, _) in caller_type.methods):
            return None
        return StringTypeName.methods.get(("_objectToString", (VOID_PTR,)))
    return None

# 函数值类型（viola.lang.function，0.1起，见versions_dev_plan_zh.md）。
# 所有函数（无论静态还是动态）作为值使用时均封装为
# viola$lang$function$Function结构体（见viola_libs/viola/runtime.h）。
# SyncPtr/AsyncPtr为不透明函数指针类型（cpart类，不生成结构体）。
SyncPtrTypeName: ClassName = ClassName(VIOLA_INIT, VIOLA_LANG_FUNCTION, "SyncPtr", None, False, True)
AsyncPtrTypeName: ClassName = ClassName(VIOLA_INIT, VIOLA_LANG_FUNCTION, "AsyncPtr", None, False, True)
FunctionTypeClsName: ClassName = ClassName(VIOLA_INIT, VIOLA_LANG_FUNCTION, "Function", None, False, False)
FunctionTypeClsName.add_property(VIOLA_INIT, "asyncPtr", AsyncPtrTypeName, Modifier.PUBLIC, False)
FunctionTypeClsName.add_property(VIOLA_INIT, "syncPtr", SyncPtrTypeName, Modifier.PUBLIC, False)
FunctionTypeClsName.add_property(VIOLA_INIT, "$capture", VOID_PTR, Modifier.PUBLIC, False)
FunctionTypeClsName.add_property(VIOLA_INIT, "argNames", ArrayTypeName(VIOLA_INIT, StringTypeName),
                                Modifier.PUBLIC, False)

# 全局资源管理器请求类型（viola.lang.global_resource_manager._Request，0.1起）。
# C结构体为viola$lang$global_resource_manager$Request（第一个成员为请求类型编码）。
RequestTypeClsName: ClassName = ClassName(VIOLA_INIT, [], "viola$lang$global_resource_manager$Request",
                                          None, False, True)
RequestTypeClsName.add_property(VIOLA_INIT, "type", UINT32, Modifier.PUBLIC, False)

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
# 注意（开发疑问记录第38条）：内置构造函数的注册已移除，
# 构造函数在viola/lang/exception.vla声明文件中声明。
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

    def __deepcopy__(self, memo: dict) -> "GenericTable":
        """泛型表在实例化期间共享：深拷贝返回自身。

        泛型实例化通过deepcopy复制定义（SqDef.instantiation_full_by_dict），
        复制体的表达式仍引用本表；若本表被一并复制，实例化期间注册的
        实例会落在各私有副本上、跨副本无法查重，导致重复实例化与
        内存无界增长。
        """
        memo[id(self)] = self
        return self

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

    def _instance_index(self, symbol: "ClassName | FunctionName", t: tuple[TypeName, ...]) -> int:
        """获取实例C名中的序号。

        具体类型实参的实例按全局注册表编号（跨模块一致，见
        _GENERIC_INSTANCE_INDEXES）；含泛型参数的伪实例不产生定义，
        按本表的登记数量编号即可。
        """
        if all(not isinstance(x, GenericArgument) for x in t):
            return _generic_instance_index(symbol.name, tuple(x.name for x in t))
        return len(self._class_instances[symbol] if isinstance(symbol, ClassName)
                   else self._function_instances[symbol])

    def add_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> None:
        """
        添加一个已实例化的泛型类。
        """
        if class_name not in self._class_instances:
            raise InternalCompilerException("Class does not exist.", self._source_info)
        if t in self._class_instances[class_name]:
            raise InternalCompilerException("Class already exists.", self._source_info)
        new_name: str = f"{class_name.self_name}__{self._instance_index(class_name, t)}"

        def register_shell(shell: ClassName) -> None:
            # 先登记实例再填充成员：成员签名中对本实例的引用
            # （如Array<T>方法签名中的Array::<T>）可解析到同一对象
            shell.mark_generic_instance(class_name, t, self)
            self._class_instances[class_name][t] = shell

        result = class_name.instantiation_full(new_name, list(t), register_shell)
        if t not in self._class_instances[class_name]:
            # 未触发壳回调（如内置指针类型的实例化返回指针类型而非类）
            self._class_instances[class_name][t] = result

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
                f"{function_name.self_name}$_{self._instance_index(function_name, t)}", list(t)
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
        # 在锁内取请求集合的副本：本函数可能在编译线程中被调用（模块完成时
        # 实例化其泛型定义），而其他线程可能正在登记新请求
        with _GENERIC_REGISTRY_LOCK:
            if isinstance(symbol, FunctionName):
                requests = set(_GENERIC_FUNC_INSTANCE_REQUESTS.get(symbol.name, set()))
            else:
                requests = set(_GENERIC_CLS_INSTANCE_REQUESTS.get(symbol.name, set()))
        # 合并其他模块发起的实例化请求（实例化发生在调用方模块）。
        # 请求存放在set中，迭代顺序依赖类型名的哈希（随PYTHONHASHSEED变化），
        # 故按类型名排序后再合并，使实例的生成顺序确定（见开发疑问记录115）
        for t in sorted(requests, key=lambda x: tuple(y.name for y in x)):
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
            if any(isinstance(x, GenericArgument) for x in t):
                # 泛型参数实参：伪实例，不注册（不占用重载序号）
                return function_name.instantiation_full(
                    f"{function_name.self_name}$pseudo", list(t))
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

    def __init__(self, real_type_getter: Callable[[str], Optional[TypeName]],
                 generic_table: GenericTable,
                 cls_instance_getter: Optional[Callable[[ClassName, tuple[TypeName, ...]], ClassName]] = None) -> None:
        self._tokens: list[Token] = []
        self._current: int = -1
        self._tokens_num: int = 0
        self._src_info: SourceInfo = VIOLA_INIT
        self._real_type_getter: Callable[[str], Optional[TypeName]] = real_type_getter
        self._generic_table: GenericTable = generic_table
        # 泛型类实例的获取方式：默认直接取实例表；符号表传入其get_generic_cls_instance
        # （额外登记跨模块实例化请求，见开发疑问记录111）
        self._cls_instance_getter: Callable[[ClassName, tuple[TypeName, ...]], ClassName] = \
            cls_instance_getter if cls_instance_getter is not None else generic_table.get_cls_instance
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
                result = self._cls_instance_getter(result, tuple(type_args))
            else:
                self._back()
                break
        return result


class SymbolTable:
    """
    符号表。
    """

    def __deepcopy__(self, memo: dict) -> "SymbolTable":
        """符号表在实例化期间共享：深拷贝返回自身。

        泛型实例化通过deepcopy复制定义，复制体的表达式仍引用本表；
        若本表被一并复制（每个实例一份），随实例数增长将导致内存
        爆炸与跨副本的重复注册。
        """
        memo[id(self)] = self
        return self

    _NAMESPACES_WITHOUT_IMPORT: tuple[list[NamespaceName], ...] = (
        VIOLA_LANG_EXCEPTION,
        VIOLA_LANG,
        VIOLA_IO,
        VIOLA_COLLECTIONS
    )
    # 类型别名解析的最大链长（见_resolve_alias）：别名可以指向别名，
    # 超过此长度即判定为循环定义
    _MAX_ALIAS_DEPTH: int = 32
    # viola.math绑定：一元与二元浮点函数（名称，参数类型，返回类型）
    _MATH_BINDINGS: list[tuple[str, list[TypeName], list[TypeName]]] = [
                                                                           (name, [FLOAT64], [FLOAT64]) for name in [
            "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
            "exp", "log", "log10", "log2", "fabs", "floor", "ceil", "round", "trunc"
        ]
                                                                       ] + [
                                                                           (name, [FLOAT64, FLOAT64], [FLOAT64]) for
                                                                           name in [
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
    def type_def_texts(cls) -> list[str]:
        """按确定性顺序获取全部类型定义文本（结构体定义与函数指针typedef）。

        顺序由ordered_type_def_keys()给出：被引用的定义先于引用者输出，同层
        按类别（数组 -> 同步函数指针 -> 元组 -> 异步函数指针）与名称排序。
        各注册表的插入顺序取决于并行编译的线程交错，不能直接遍历（见开发
        疑问记录117）。
        """
        texts: list[str] = []
        for category, name in ordered_type_def_keys():
            if category == _TYPEDEF_CATEGORY_ARRAY:
                texts.append(cls._array_type_decl_text(_ARRAY_TYPE_DEFS[name]))
            elif category == _TYPEDEF_CATEGORY_TUPLE:
                texts.append(_TUPLE_TYPE_DEFS[name].c_typedef_text)
            else:
                texts.append(_FUNCTION_TYPE_DEFS[name].c_typedef_text)
        return texts


    @staticmethod
    def _array_method_substitutions(arr_name: str) -> dict[str, str]:
        """获取数组方法体模板中占位符的替换文本（见ArrayMethodDesc.body）。

        替换文本与元素类型无关的部分在此给出；元素类型相关的占位符见
        _array_method_body_text的两个参数。模板中出现的每个占位符都必须在此
        有对应项，否则_array_method_body_text报错（避免新增方法时漏替换）。
        """
        return {
            # 检查代码：越界/非法范围时上报异常并提前返回，不写出结果
            # （调用方的表达式求值可能有后续语句先于异常跳转执行）
            "@check_index_get@": SymbolTable._array_bounds_check_text(
                "item", ["memset(element, 0, sizeof(*element));"]),
            "@check_index_set@": SymbolTable._array_bounds_check_text(
                "index", ["*newArray = _this;"]),
            "@check_slice_step@": SymbolTable._array_check_text(
                "step == 0", "viola$lang$exception$sliceStepError(step, listener);",
                ["newResult->size = 0;", "newResult->data = NULL;", "*subarray = newResult;"]),
            "@check_slice_range@": SymbolTable._array_slice_range_check_text(),
            # 结果数组的分配（各方法在此之后填充data与size）
            "@new_result@": f"{arr_name} *newResult = ({arr_name} *)malloc(sizeof({arr_name})); "
                            f"newResult->$refCount = 1; newResult->$parent = NULL;",
        }

    @staticmethod
    def _array_elem_release_loop_text(elem: TypeName) -> str:
        """获取数组析构中逐个释放元素的循环文本（元素非对象类型时为空）。

        数组持有其元素（元素存入时retain，见各方法体中的@elem_retain@），
        故析构时逐个递减并调用元素自身的析构函数。元素类型可能是类、元组或
        另一个数组（见开发疑问记录190）。

        计数按"$refCount位于对象首字段"直接取址，而不按成员名访问：数组方法的
        实现生成在__main__.c中，彼时元素类型通常只有前向声明。
        """
        if not elem.is_object:
            return ""
        return "\n".join([
            "\tfor (viola$lang$uint64 i = 0; i < _this->size; i++) {",
            "\t\tif (_this->data[i] && viola$lang$refcount_dec("
            "(viola$lang$atomic_uint32 *)(void *)_this->data[i]) == 0) {",
            f"\t\t\t{destructor_name(elem)}(_this->data[i], listener);",
            "\t\t}",
            "\t}",
        ])

    @staticmethod
    def _array_method_body_text(arr_name: str, elem: TypeName, desc: ArrayMethodDesc) -> list[str]:
        """获取数组方法体的C语句行（替换模板中的占位符）。

        元素类型相关的占位符在此替换：@elem_assigning@为元素的赋值形式
        （c_assigning_name，用于内存分配的转换与data的写回）、@elem_size@为
        sizeof(元素类型)。替换后若仍留有占位符（表中写错名字）则报错，避免
        生成无法编译的C代码。
        """
        substitutions: dict[str, str] = SymbolTable._array_method_substitutions(arr_name)
        elem_call: str = elem.c_calling_name
        substitutions["@elem_assigning@"] = elem.c_assigning_name
        substitutions["@elem_size@"] = f"sizeof({elem_call.strip()})"
        # 元素的所有权：元素存入容器时计一次数（基本类型无$refCount，用空操作版本），
        # 容器析构时递减并调用元素自身的析构函数（见开发疑问记录190）
        if elem.is_object:
            substitutions["@elem_retain@"] = "VIOLA_ELEM_RETAIN"
        else:
            substitutions["@elem_retain@"] = "VIOLA_ELEM_RETAIN_NOOP"
        substitutions["@elem_release_loop@"] = SymbolTable._array_elem_release_loop_text(elem)
        lines: list[str] = []
        for template in desc.body:
            text: str = template
            for token, value in substitutions.items():
                text = text.replace(token, value)
            remaining: str = find_placeholder(text)
            if remaining != "":
                raise InternalCompilerException(
                    f"Unknown placeholder {remaining} in the body of array method {desc.suffix}.",
                    SourceInfo(""))
            lines.append(text)
        return lines

    @staticmethod
    def _array_param_text(c_type: str, name: str, is_return_slot: bool = False) -> str:
        """拼接数组方法形参的类型与名字。

        基本类型的c_calling_name带尾随空格（如"viola$lang$int "）、类类型以"*"
        结尾（如"viola$lang$string *"），故不能一律插入空格：类型以标识符字符
        结尾时补空格（避免类型与形参名粘连成同一个标识符），否则直接相接。
        返回值槽位在其后附加"*"（声明返回类型的指针形式，见
        _array_sync_signature_text），总是跟着空格。
        """
        if is_return_slot:
            return f"{c_type}* {name}"
        if c_type != "" and (c_type[-1].isalnum() or c_type[-1] in "_$"):
            return f"{c_type} {name}"
        return f"{c_type}{name}"

    @staticmethod
    def _array_sync_signature_text(arr_name: str, desc: ArrayMethodDesc, terminator: str) -> str:
        """获取数组方法同步声明/实现的首行文本（两者的形参表一致，仅结尾不同）。

        接收者为第一个形参；返回值以指针形参接收，其C类型为声明返回类型的
        指针形式（c_calling_name加"*"，对基本类型与类类型均即c_assigning_name）。
        """
        params: list[str] = [f"{arr_name} *_this"]
        params += [SymbolTable._array_param_text(t.c_calling_name, name) for t, name in desc.args]
        params += [SymbolTable._array_param_text(t.c_calling_name, name, True) for t, name in desc.rets]
        params.append(f"{LISTENER_T} *listener")
        return f"void {arr_name}${desc.suffix}({', '.join(params)}){terminator}"

    @staticmethod
    def _array_sync_decl_text(arr_name: str, desc: ArrayMethodDesc) -> str:
        """获取数组方法同步声明的文本（与同步实现同源，见开发疑问记录148）。"""
        return SymbolTable._array_sync_signature_text(arr_name, desc, ";")

    @staticmethod
    def _tuple_type_name(type_names: list[str]) -> str:
        """获取元组结构体的C名称（与编译器按成员类型名生成的元组一致）。"""
        return TUPLE_T + "$" + "$".join(type_names)

    @staticmethod
    def _array_type_decl_text(arr_type: "ArrayTypeName") -> str:
        """获取数组类型的结构体定义与方法声明文本。

        方法声明由方法表生成（见_array_sync_decl_text），与同步实现、$async包装
        及方法注册同源，不再各自维护一份文本（见开发疑问记录148、153）。

        方法声明与$async声明都置于结构体定义之外（见开发疑问记录154）：string[]、
        uint8[]等数组类型的结构体由运行库头文件runtime.h定义（同名include guard），
        其guard在包含本文件的编译单元中已定义，guard内的声明会被整块跳过，模块内
        调用其数组方法（如viola$lang$string$$array$length$_0）便没有原型（gcc隐式
        声明警告）。结构体本身不能重复定义，故只把声明移出guard；声明所需的
        结构体由runtime.h或紧随其前的guard块给出。
        """
        arr_name: str = arr_type.c_alloc_name
        elem: TypeName = arr_type.element_type
        elem_asg: str = elem.c_assigning_name
        descs: list[ArrayMethodDesc] = _array_method_descs(arr_type)
        return "\n".join([
            f"#ifndef _VIOLA_ARRAY_T_{arr_name}",
            f"#define _VIOLA_ARRAY_T_{arr_name}",
            "typedef struct {",
            "\tviola$lang$atomic_uint32 $refCount;",
            "\tviola$lang$ptr $parent;",
            f"\t{elem_asg} data;",
            "\tviola$lang$uint64 size;",
            f"}} {arr_name};",
            "#endif",
            *map(lambda desc: SymbolTable._array_sync_decl_text(arr_name, desc), descs),
            # $async包装所需的实参/返回元组结构体与$async声明（见开发疑问记录146）。
            # 元组结构体自带include guard，函数声明重复出现不影响语义。
            "\n\n".join(map(lambda desc: SymbolTable._array_async_tuple_defs_text(arr_name, desc),
                            descs)),
            "\n".join(map(lambda desc: SymbolTable._array_async_decl_text(arr_name, desc), descs))
        ])

    @staticmethod
    def _array_async_tuple_defs_text(arr_name: str, desc: ArrayMethodDesc) -> str:
        """获取一个数组方法的$async实参/返回元组的结构体定义文本（见开发疑问记录146）。

        元组结构体随方法声明一同输出到模块头文件（带include guard，与
        type_def_texts生成的同名定义不冲突）：异步调用的实参/返回元组按被调
        方法声明的类型构造，这些元组类型未必由编译器按需注册。
        """
        return "\n".join([
            SymbolTable._tuple_typedef_text(
                SymbolTable._tuple_type_name([arr_name] + [t.name for t, _ in desc.args]),
                [f"{arr_name} *"] + [t.c_calling_name for t, _ in desc.args]),
            SymbolTable._tuple_typedef_text(
                SymbolTable._tuple_type_name([t.name for t, _ in desc.rets]),
                [t.c_calling_name for t, _ in desc.rets])
        ])

    @staticmethod
    def _array_async_decl_text(arr_name: str, desc: ArrayMethodDesc) -> str:
        """获取一个数组方法的$async声明文本（见开发疑问记录146）。"""
        args_tuple: str = SymbolTable._tuple_type_name([arr_name] + [t.name for t, _ in desc.args])
        rets_tuple: str = SymbolTable._tuple_type_name([t.name for t, _ in desc.rets])
        return f"void {arr_name}${desc.suffix}$async({args_tuple} * params, " \
               f"{rets_tuple} * returns, viola$threads$Listener *listener);"

    @staticmethod
    def _array_check_text(condition: str, report: str,
                          extra: Optional[list[str]] = None) -> str:
        """
        获取数组范围检查的C代码（越界下标、非法切片范围等共用）。

        检查由运行库的VIOLA_ARRAY_BOUNDS_CHECK宏控制，默认开启，条件成立时
        上报异常（可被catch捕获）；以-DVIOLA_ARRAY_BOUNDS_CHECK=0编译可关闭
        （见开发疑问记录124）。

        条件成立时提前返回，不写出结果：调用方的表达式求值可能有后续语句先于
        异常跳转执行，故extra给出把结果置于确定值的语句（该值在异常路径上
        被丢弃，但不应是未初始化的值）。
        :param condition: 触发检查的C条件表达式。
        :param report: 条件成立时上报异常的C语句。
        :param extra: 条件成立时在返回前执行的语句列表。
        :return: 检查代码文本。
        """
        lines: list[str] = [
            "#if VIOLA_ARRAY_BOUNDS_CHECK",
            f"\tif ({condition}) {{",
            f"\t\t{report}",
        ]
        lines += [f"\t\t{line}" for line in (extra if extra is not None else [])]
        lines += ["\t\treturn;", "\t}", "#endif"]
        return "\n".join(lines)

    @staticmethod
    def _array_bounds_check_text(index_var: str, extra: Optional[list[str]] = None) -> str:
        """
        获取数组下标越界检查的C代码。

        数组的__getitem__/__setitem__原先直接读写data[index]，越界时静默读取
        相邻堆内存（见开发疑问记录124）。越界时上报IndexError。
        :param index_var: 下标形参的名字（__getitem__为item，__setitem__为index）。
        :param extra: 越界时在返回前执行的语句列表。
        :return: 检查代码文本。
        """
        return SymbolTable._array_check_text(
            f"{index_var} >= _this->size",
            f"viola$lang$exception$indexError({index_var}, _this->size, listener);",
            extra)

    @staticmethod
    def _array_slice_range_check_text() -> str:
        """
        获取数组切片赋值（__setitem__$_1）的范围检查C代码。

        切片赋值原先以_this->size - (end - start) + newSubarray->size计算新长度，
        其中end被截断到size而start未做上界截断；start > end时（如a[3:1] = [...]）
        end - start按uint64下溢为极大值，随后的malloc通常失败并解引用空指针
        （见开发疑问记录129）。与下标越界检查同样由VIOLA_ARRAY_BOUNDS_CHECK
        控制，范围非法时上报viola$lang$exception$sliceError。
        :return: 检查代码文本。
        """
        return SymbolTable._array_check_text(
            "start > end",
            "viola$lang$exception$sliceError(start, end, listener);",
            ["*newArray = _this;"])

    @classmethod
    def _array_async_impl_texts(cls, arr_type: "ArrayTypeName") -> list[str]:
        """获取一个数组类型全部方法的$async实现文本（见开发疑问记录146）。

        包装体与编译器为有函数体的函数生成的$async包装等价（声明式原生函数的
        包装见build_tools/lib_tools/gen_async_wrappers.py）：解包实参元组
        （接收者为$0）→ 调用同步实现 → 把返回值写回返回元组；同步实现上报的
        异常经Exception$what()/perror报告后交回调用线程。
        实参/返回元组按被调方法声明的形参/返回类型构造（见CallOp的
        _async_arg_types/_async_ret_types），故包装体按声明类型解包/写回即可。

        元组结构体的typedef在此一并输出（带与编译器一致的include guard，
        与头文件中的同名定义不冲突）：本方法在类型定义文本生成之后调用，
        此时再注册元组类型来不及输出到（已生成的）头文件。
        """
        results: list[str] = []
        arr_name: str = arr_type.c_alloc_name
        for desc in _array_method_descs(arr_type):
            args_desc: list[tuple[str, str]] = [("_this", f"{arr_name} *")] + \
                [(name, t.c_calling_name) for t, name in desc.args]
            rets_desc: list[tuple[str, str]] = [(name, t.c_calling_name) for t, name in desc.rets]
            args_tuple: str = cls._tuple_type_name([arr_name] + [t.name for t, _ in desc.args])
            rets_tuple: str = cls._tuple_type_name([t.name for t, _ in desc.rets])
            results.append(cls._tuple_typedef_text(
                args_tuple, [c_type for _, c_type in args_desc]))
            results.append(cls._tuple_typedef_text(
                rets_tuple, [c_type for _, c_type in rets_desc]))
            indent: str = "\t\t"
            lines: list[str] = [
                f"void {arr_name}${desc.suffix}$async({args_tuple} * params, "
                f"{rets_tuple} * returns, viola$threads$Listener *listener) {{",
                f"\t{EXCEPTION_T} *$$exc = listener->exception;",
                # 异步任务开始执行时压入B栈，结束时退栈（与编译器生成的包装体一致，
                # 见开发疑问记录87）
                f"\t{STACK_B_PUSH_FUNC}(listener->currentThreadId);",
                "\tdo {",
            ]
            # 无实参/无返回值时不使用对应的元组，显式标记以避免-Wunused-parameter
            if len(desc.args) == 0:
                lines.append(f"{indent}(void)params;")
            if len(desc.rets) == 0:
                lines.append(f"{indent}(void)returns;")
            # 形参/返回值的局部变量：对象的初值为NULL，其余为0
            for name, c_type in args_desc + rets_desc:
                zero: str = "NULL" if "*" in c_type else "0"
                lines.append(f"{indent}{c_type}{name} = {zero};")
            for i, (name, _) in enumerate(args_desc):
                lines.append(f"{indent}{name} = params->${i};")
            lines.append(f"{indent}if ($$exc) goto $$_async_err;")
            call_args: list[str] = [name for name, _ in args_desc] + \
                [f"&{name}" for name, _ in rets_desc] + ["listener"]
            lines.append(f"{indent}{arr_name}${desc.suffix}({', '.join(call_args)});")
            # 同步实现可能通过listener上报异常
            lines.append(f"{indent}if ($$exc == NULL) {{ $$exc = listener->exception; }}")
            for i, (name, _) in enumerate(rets_desc):
                lines.append(f"{indent}returns->${i} = {name};")
            lines.append(f"{indent}if ($$exc) goto $$_async_err;")
            lines.append(f"{indent}goto $$_async_done;")
            lines.append("\t} while (0);")
            lines.extend([
                "$$_async_err:",
                f"\tif ({CONVERTIBLE_TO_FUNC}($$exc->$$vtable, "
                f"&{EXCEPTION_VTABLE})) {{",
                f"\t\t{EXCEPTION_T} *exc = $$exc;",
                "\t\t$$exc = NULL;",
                "\t\tlistener->exception = NULL;",
                f"\t\t{STRING_T} *$$_msg = NULL;",
                f"\t\t{EXCEPTION_WHAT_FUNC}(exc, &$$_msg, listener);",
                "\t\tif ($$exc == NULL) { $$exc = listener->exception; }",
                f"\t\t{PERROR_FUNC}($$_msg, listener);",
                "\t\tif ($$exc == NULL) { $$exc = listener->exception; }",
                "\t\tlistener->exception = exc;",
                f"\t\t{EXCEPTION_DEL_FUNC}(exc, listener);",
                "\t\texc = NULL;",
                "\t}",
                "$$_async_done:",
                "$$_async_cleanup: ;",
                "\tif ($$exc) { goto $$_async_cleanup; }",
                f"\t{STACK_B_POP_FUNC}(listener->currentThreadId);",
                "}"
            ])
            results.append("\n".join(lines))
        return results

    @staticmethod
    def _tuple_typedef_text(name: str, member_c_types: list[str]) -> str:
        """获取元组结构体的typedef文本（不构造元组对象，避免注册新类型）。

        与TupleTypeName.c_typedef_text一致（含include guard与析构函数声明），
        保证两处生成的文本同名时互相兼容。
        """
        members: str = "\n".join(
            f"\t{c_type} ${i};" for i, c_type in enumerate(member_c_types))
        if members != "":
            members += "\n"
        return "\n".join([
            f"#ifndef _VIOLA_TUPLE_T_{name}",
            f"#define _VIOLA_TUPLE_T_{name}",
            "typedef struct {",
            "\tviola$lang$atomic_uint32 $refCount;",
            "\tviola$lang$ptr $parent;",
            "\tviola$lang$uint64 size;",
            f"\t{TUPLE_DEL_FIELD_T}",
            members,
            f"}} {name};",
            tuple_del_decl_text(name),
            "#endif"
        ])

    @staticmethod
    def _tuple_elem_release_text(tuple_name: str, index: int, member: TypeName) -> str:
        """获取元组析构中释放一个对象成员的C文本（成员非对象类型时为空）。

        元组持有其元素（元素存入时retain，见TupleRef.front_text），析构时逐个
        递减并调用元素自身的析构函数（与数组同一做法，见开发疑问记录190、192）。
        计数按"$refCount位于对象首字段（偏移0）"直接取址，不按成员名访问：
        元素类型可能是只有前向声明的类。
        """
        if not member.is_object:
            return ""
        member_text: str = f"_this->${index}"
        return "\n".join([
            f"\t\t\tif ({member_text} && {REFCOUNT_DEC_FUNC}("
            f"(viola$lang$atomic_uint32 *)(void *)({member_text})) == 0) {{",
            f"\t\t\t\t{destructor_name(member)}({member_text}, listener);",
            "\t\t\t}",
        ])

    @classmethod
    def tuple_type_impl_texts(cls) -> list[str]:
        """获取所有已注册元组类型的析构函数实现文本（生成到唯一编译单元__main__.c中）。

        元组按元素类型单态化（见开发疑问记录192）：每个元组类型有自己的析构函数，
        逐个释放其持有的对象成员后回收结构体。按类型名排序，避免输出随并行编译的
        线程交错变化（见开发疑问记录117）。
        """
        results: list[str] = []
        for name in sorted(_TUPLE_TYPE_DEFS.keys()):
            tuple_type: TupleTypeName = _TUPLE_TYPE_DEFS[name]
            members: list[str] = list(filter(
                lambda x: x != "",
                (cls._tuple_elem_release_text(name, i, t)
                 for i, t in enumerate(tuple_type.types))))
            results.append("\n".join([
                # 首形参为void *：元组的$del成员与运行库的转发函数共用同一
                # 函数指针类型，分配处写入时无需强制转换（见tuple_del_decl_text）
                f"void {tuple_del_name(name)}(void *$$this, {LISTENER_T} *listener) {{",
                f"\t{name} *_this = ({name} *)$$this;",
                # 调用方已递减至0（见开发疑问记录190），此处释放成员后回收元组
                "\tif (_this == NULL) { return; }",
                "\tif (_this->$refCount == 0) {",
                "\t\tif (_this->$parent) { ((viola$lang$uint32 *)_this->$parent)[0]--; }",
                "\t\telse {",
                *members,
                "\t\t\tfree(_this); _this = NULL;",
                "\t\t}",
                "\t}",
                "}"]))
        return results

    @classmethod
    def array_type_impl_texts(cls) -> list[str]:
        """获取所有已注册数组类型方法的C实现文本（生成到唯一编译单元__main__.c中）。

        同步实现由方法表生成（与同步声明、$async包装同源，见开发疑问记录148），
        含各方法的同步实现与$async包装（后者见开发疑问记录146）。
        按类型名排序，避免输出随并行编译的线程交错变化（见开发疑问记录117）。
        """
        results: list[str] = []
        for arr_name in sorted(_ARRAY_TYPE_DEFS.keys()):
            arr_type: ArrayTypeName = _ARRAY_TYPE_DEFS[arr_name]
            for desc in _array_method_descs(arr_type):
                results.append("\n".join(
                    [cls._array_sync_signature_text(arr_name, desc, " {")]
                    + cls._array_method_body_text(arr_name, arr_type.element_type, desc)
                    + ["}"]))
        # 各方法的$async包装（见开发疑问记录146）置于全部同步实现之后，
        # 使其调用的同步函数已在本单元内定义：即使某数组类型的方法声明未出现在
        # 模块头文件中，也能靠先行的定义避免隐式声明警告
        for arr_name in sorted(_ARRAY_TYPE_DEFS.keys()):
            results.extend(cls._array_async_impl_texts(_ARRAY_TYPE_DEFS[arr_name]))
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
        if item not in self.symbols and (original_name, item[1]) in self.symbols:
            # 命名空间清理后的名称未命中，但原始限定名存在（import导入的符号）
            item = (original_name, item[1])
        if item not in self.symbols:
            functions: list[tuple[str, Optional[tuple[TypeName, ...]]]] = [k for k in self.symbols.keys() if
                                                                           k[0] == item[0]]
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
        获取一个符号（类型别名会解析为被别名的类型，见_resolve_alias）。
        item: 符号名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        return self._resolve_alias(self._lookup_symbol(items))

    def _lookup_symbol(self, items: tuple[str, Optional[tuple[TypeName, ...]]]) -> NamedSymbol:
        """
        按名称查找一个符号（不解析类型别名）。
        item: 符号名称。
        types: 符号的参数类型列表（如果不是函数则为None）。
        """
        item: str = items[0]
        types: Optional[tuple[TypeName, ...]] = items[1]
        orig_item: str = item
        item = self.clean_namespace(item)
        if (item, types) not in self.symbols and (orig_item, types) in self.symbols:
            # 命名空间清理后的名称未命中，但原始限定名存在（import导入的
            # viola.*等内置命名空间模块的符号以限定名注册）
            item = orig_item
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
                raise CompilerException(
                    f"Ambiguous method call: {cls_name}.{attr_name}({', '.join(t.raw_name for t in types)})",
                    self._src_info)
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
                raise CompilerException(
                    f"Ambiguous method call: {cls_name}.{attr_name}({', '.join(t.raw_name for t in types)})",
                    self._src_info)
        # item = item.replace(".", "$")
        if (item, types) not in self.symbols:
            if types is None and (item, None) in self.symbols:
                return self.symbols[item, None]
            if types is None:
                functions = [v for k, v in self.symbols.items() if k[0] == item]
                if len(functions) == 1:
                    return functions[0]
                item2 = item.replace(".", "$")
                if "$$array" in item2:
                    # 数组类型C名（如viola$lang$int$$array）：按元素类型重建。
                    # 元素名优先按限定名解析（如viola.os.Stat），
                    # 失败时按末段裸名解析（如内置类型int）
                    element_name = item2.split("$$array", 1)[0]
                    if element_name != "":
                        try:
                            element = self[self.clean_namespace(element_name.replace("$", ".")), None]
                        except CompilerException:
                            element = self[element_name.split("$")[-1], None]
                        return ArrayTypeName(self._src_info, element)
                if (item2, None) in self.symbols:
                    return self.symbols[item2, None]
                if item2.startswith("viola$lang$Pointer$") or item2.startswith("Pointer$"):
                    # 指针类型：按指向的元素类型重建
                    element_name = item2.split("Pointer$", 1)[1]
                    element = self[element_name, None]
                    if isinstance(element, TypeName):
                        return PointerTypeName(self._src_info, element)
                result = self._type_name_parser.parse(self._src_info, item2)
                if result is not None and isinstance(result, ClassName) and (result.self_name,
                                                                             None) not in self.symbols:
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
        # 类型别名条目（别名键 -> 别名对象）：别名在_symbols中另有独立条目，
        # 这里另行保留，供调试时查询"别名指向哪个类型"（见type_aliases）
        self._type_aliases: dict[str, TypeAliasName] = {}
        # 本模块定义的、待解析校验的别名（见read_from与_read_type_alias_decl）
        self._pending_aliases: list[TypeAliasName] = []
        self._current_cls: Optional[ClassName] = None
        # 被本编译单元赋值/读取过的模块级变量（按限定后的C名称记录）。
        # 模块级变量的存储由定义它的模块提供：无初值且本模块既未赋值也未读取时，
        # 它只是"声明"（存储由运行库的C实现等其他翻译单元提供，如viola.os的
        # STDIN_FILENO与O_*常量），文件作用域上生成extern声明而非定义，从而
        # 无需依赖C的共同符号合并（见开发疑问记录168）。
        # 键为变量的限定C名称（含模块前缀），故跨模块也不会混淆。
        self._assigned_globals: set[str] = set()
        self._read_globals: set[str] = set()
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
        # 调试标记的计数器单独计数（编号按符号表，即按模块，使生成产物与
        # 编译线程的调度无关，见开发疑问记录117）；表序号用于让不同符号表
        # 生成的占位名互不相同，写出时再按编译单元统一重编号（见开发疑问记录123）
        self._mark_counter: int = 0
        self._mark_table_index: int = _next_mark_table_index()
        self._class_info_list_name: str = "$".join(map(lambda x: x.name, self._namespace)) + "$classInfoList"
        self._src_info: SourceInfo = SourceInfo(src_path)
        self._generic_table: GenericTable = GenericTable(self._src_info, self._namespace)
        self._namespace_without_import: tuple[str, ...] = \
            tuple([*map(lambda x: ".".join(y.name for y in x) + ".", SymbolTable._NAMESPACES_WITHOUT_IMPORT),
                   self._namespace_name + "."])
        self._init_builtin_types()

        def __real_type_getter(name: str) -> Optional[TypeName]:
            name = name.strip()
            if (name, None) in self.symbols:
                # 类型别名同样在符号表中，解析为被别名的类型（见开发疑问记录157）
                resolved = self._resolve_alias(self.symbols[name, None])
                return resolved if isinstance(resolved, TypeName) else None
            cleaned_name: str = self.clean_namespace(name)
            if (cleaned_name, None) in self.symbols:
                resolved = self._resolve_alias(self.symbols[cleaned_name, None])
                return resolved if isinstance(resolved, TypeName) else None
            # 未限定的类名（如导入后使用的Array）：按自身名唯一匹配已注册的类。
            # 导入的符号按限定名注册（如viola.util.array.Array），仅当匹配唯一时
            # 才解析，避免歧义（见开发疑问记录102）
            matches: list[NamedSymbol] = [v for v in self.symbols.values()
                                          if isinstance(v, (ClassName, TypeAliasName)) and v.self_name == name]
            resolved_matches: list[TypeName] = []
            for match in matches:
                resolved_match: NamedSymbol = self._resolve_alias(match)
                if isinstance(resolved_match, TypeName):
                    resolved_matches.append(resolved_match)
            if len(resolved_matches) == 1:
                return resolved_matches[0]
            return None

        self._type_name_parser: _TypeNameParser = _TypeNameParser(
            __real_type_getter, self._generic_table, self.get_generic_cls_instance)

    def _init_builtin_types(self) -> None:
        builtin_types = [
            BOOL,
            # INT不在列表中：它与INT32是同一个对象，其名称"int"在下方单独注册
            INT8, INT16, INT32, INT64,
            UINT, UINT8, UINT16, UINT32, UINT64,
            SIZE_T,
            FLOAT, FLOAT32, FLOAT64, FLOAT128,
            DOUBLE, LONG_DOUBLE,
            VOID_PTR,
        ]
        for t in builtin_types:
            self.add(t, t.self_name, None)
        # size_t与uint64、int与int32分别是同一个类型：以别名（第二个查找名）
        # 注册，使源码中的这两个名字都解析到同一个TypeName对象（见开发疑问记录151）
        self.add(SIZE_T, "size_t", None)
        self.add(INT, "int", None)
        self.add(PointerGenericClassName, PointerGenericClassName.self_name, None)
        self._generic_table.add_cls_def(PointerGenericClassName)
        self.add(Object, Object.self_name, None)
        self.add(StringTypeName, StringTypeName.self_name, None)
        self.add(SliceTypeName, SliceTypeName.self_name, None)
        self.add(ExceptionTypeName, ExceptionTypeName.self_name, None)
        # 函数值类型（viola.lang.function，0.1起）
        self.add(FunctionTypeClsName, FunctionTypeClsName.self_name, None)
        self.add(FunctionTypeClsName, "viola.lang.function.Function", None)
        self.add(SyncPtrTypeName, SyncPtrTypeName.self_name, None)
        self.add(SyncPtrTypeName, "viola.lang.function.SyncPtr", None)
        self.add(AsyncPtrTypeName, AsyncPtrTypeName.self_name, None)
        self.add(AsyncPtrTypeName, "viola.lang.function.AsyncPtr", None)
        # 全局资源管理器请求类型（Viola名_Request，C名为viola$lang$global_resource_manager$Request）
        self.add(RequestTypeClsName, "_Request", None)
        self.add(RequestTypeClsName, "viola.lang.global_resource_manager._Request", None)
        self.add(RequestTypeClsName, RequestTypeClsName.name, None)
        # 文件类型（viola.io.file）作为内置类保留：viola/io.vla中的wrapper class
        # 依赖此绑定复用运行库的viola$io$file结构体（见开发疑问记录第37条）。
        self.add(FileTypeName, FileTypeName.self_name, None)
        # 注意（开发疑问记录第40条）：仅保留viola.lang（及上述基础设施）的内置绑定，
        # viola.io/math/os/threads的函数绑定已移除，需通过
        # `import viola.xxx;` / `from viola.xxx import *;`显式导入（见各自的.vla声明文件）。

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

    def mark_global_assigned(self, name: str) -> None:
        """记录本编译单元给某个模块级变量赋过值（见_assigned_globals）。"""
        self._assigned_globals.add(name)

    def mark_global_read(self, name: str) -> None:
        """记录本编译单元读取过某个模块级变量（见_read_globals）。"""
        self._read_globals.add(name)

    def needs_global_storage(self, name: str) -> bool:
        """判断本模块是否要为某个模块级变量提供存储（否则只生成extern声明）。

        有初值（由调用方另行判断）、被本模块赋值、或被本模块读取时都需要存储：
        读取意味着该模块确实把它当作本模块的变量使用，生成定义（零初始化）
        与改动前的行为一致；只有"既无初值、又从未在本模块出现"的变量才是
        纯粹的声明（其存储由其他翻译单元提供，见_assigned_globals的说明）。
        """
        return name in self._assigned_globals or name in self._read_globals

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

    def check_module_access(self, symbol: NamedSymbol) -> None:
        """检查模块级访问修饰符（0.1起）。

        public放行；protected与private的模块级成员只能被其所在模块
        （含自身）访问，跨模块访问报编译时错误。
        模块以符号的命名空间与当前符号表的命名空间是否一致来判定
        （导入符号以限定名注册，命名空间即其来源模块）。
        """
        modifier: Modifier = getattr(symbol, "modifier", None)
        if modifier is None or modifier == Modifier.PUBLIC:
            return
        symbol_ns: list[NamespaceName] = getattr(symbol, "namespace", None)
        if symbol_ns is not None and list(symbol_ns) == self._namespace:
            return
        raise CompilerException(
            f"Can not access {'private' if modifier == Modifier.PRIVATE else 'protected'} "
            f"member {symbol.raw_name} from another module.", self._src_info)

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

        查询用的类型不是类（基本类型、枚举等，见开发疑问记录160）或未定义时
        返回False，而不是抛出异常：本方法用于判断“是否按方法调用渲染”，
        此类类型没有方法表，按属性路径渲染即可。
        """
        cleaned_name: str = self.clean_namespace(cls_name)
        lookup_name: str = cleaned_name if (cleaned_name, None) in self.symbols else cls_name
        if (lookup_name, None) not in self.symbols:
            return False
        if not isinstance(self[lookup_name, None], ClassName):
            return False
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
        orig_name: str = name
        name = self.clean_namespace(name)
        args_declaration: list[TypeName] = list(map(lambda x: self[x, None], args))
        # noinspection PyTypeChecker
        kwargs_declaration: dict[str, TypeName] = dict(map(lambda x: (x, self[kwargs[x], None]), kwargs.keys()))
        args_length: int = len(args_declaration)
        args_tuple: tuple[TypeName, ...] = tuple(args_declaration)
        matches: dict[tuple[str, tuple[TypeName, ...]], FunctionName | MethodName] = dict(
            filter(
                lambda x: (x[0][0] == name or x[0][0] == orig_name or x[1].name == name) and len(x[0][1]) >= args_length and all(
                    map(lambda i: args_tuple[i].convertible_to(x[0][1][i], self.symbols), range(args_length))
                ),
                self.symbols.items()
            )
        )
        matches = dict(filter(lambda x: all(y in x[1].arg_names for y in kwargs.keys()), matches.items()))
        matches = dict(filter(
            lambda x: all(x[1].arg_types_dict[y].convertible_to(kwargs_declaration[y])
                          for y in kwargs_declaration.keys()),
            matches.items()
        ))
        # 实参个数校验：未被实参（位置或关键字）覆盖的形参必须带有默认值，
        # 否则生成的C调用会因实参个数不足而由gcc报错（见开发疑问记录99）
        matches = dict(filter(
            lambda x: all(
                name in kwargs or name in x[1].default_params
                for i, name in enumerate(x[1].arg_names) if i >= args_length
            ),
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
        # 参数数量精确匹配优先：形参个数与实参个数相同的重载，优先于依靠
        # 默认参数接收该调用的重载（如log(x)同时匹配log(x)与log(x, base)时
        # 应选择单参数重载；与find_methods的重载解析规则一致）
        arity_matches = dict(filter(lambda x: len(x[0][1]) == args_length, matches.items()))
        if len(arity_matches) > 0:
            matches = arity_matches
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
        orig_cls_name: str = cls_name
        cls_name = self.clean_namespace(cls_name)
        if (cls_name, None) not in self.symbols and (orig_cls_name, None) in self.symbols:
            cls_name = orig_cls_name
        cls = self[cls_name, None]
        name = self.clean_namespace(name)
        # 含$$的名字是编译器生成的组合类型C名（如数组viola$lang$int$$array），
        # 不能经clean_namespace把$替换为.，否则会被破坏成"int..array"
        args = list(map(lambda x: x if "$$" in x else self.clean_namespace(x), args))
        kwargs = dict(map(lambda k, v: (k, v if "$$" in v else self.clean_namespace(v)), kwargs.items()))
        if not isinstance(cls, ClassName):
            raise CompilerException(f"{cls_name} is not a class", self._src_info)

        def lookup_type(type_name: str) -> TypeName:
            """解析方法查找用的类型名。

            泛型类的方法查找可能使用该类的泛型参数名（如Array::<T>的T）；
            此时泛型参数不在符号表中（类声明结束后已被移除），
            按泛型参数构造类型名即可。泛型类的实例上同理：成员签名中的
            泛型参数名按实例来源的泛型类（模板）的参数名解析（开发疑问记录102）。
            """
            try:
                return self[type_name, None]
            except CompilerException:
                generic_names: Optional[list[str]] = cls.generic_args_str
                if generic_names is None and cls._generic_origin is not None:
                    # 实例化的泛型类：退回到模板的泛型参数名
                    generic_names = cls._generic_origin.generic_args_str
                if generic_names is not None and type_name in generic_names:
                    return GenericArgument(self._src_info, type_name)
                raise

        arg_types: list[TypeName] = list(map(lookup_type, args))
        kwargs_types: dict[str, TypeName] = dict(map(lambda x: (x, lookup_type(kwargs[x])), kwargs.keys()))
        methods = dict(filter(lambda x: x[0][0] == name, cls.methods.items()))
        methods = dict(filter(lambda x: len(x[0][1]) >= len(arg_types), methods.items()))
        methods = dict(filter(lambda x: all(map(lambda i: arg_types[i].convertible_to(x[0][1][i], self.symbols),
                                                range(len(arg_types)))), methods.items()))
        methods = dict(filter(lambda x: all(
            x[1].arg_types_dict[y].convertible_to(kwargs_types[y], self.symbols) for y in kwargs_types.keys()
        ), methods.items()))
        # 实参个数校验：未被实参（位置或关键字）覆盖的形参必须带有默认值，
        # 否则生成的C调用会因实参个数不足而由gcc报错（见开发疑问记录99）
        methods = dict(filter(
            lambda x: all(
                name in kwargs or name in x[1].default_params
                for i, name in enumerate(x[1].arg_names) if i >= len(arg_types)
            ),
            methods.items()
        ))
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

    def get_mark_counter(self) -> str:
        """
        获取调试标记的占位名（按符号表独立编号）。

        若改用进程内的全局计数器，编号会随并行编译的线程交错变化，使同一
        工程的连续编译产出不同文本（见开发疑问记录117），故编号按符号表
        （即按模块）分配；再冠以符号表序号，使不同符号表在同一编译单元中
        也不会重名（泛型实例可能以调用方的符号表生成、却写入定义方的文件，
        见开发疑问记录123）。该名称只是占位名，写出时会按编译单元统一
        重编号为 $$_MARK_0..$$_MARK_N（见statement.renumber_marks）。
        """
        result: str = f"$$_MARK_{self._mark_table_index}_{self._mark_counter}"
        self._mark_counter += 1
        return result

    def get_generic_cls_instance(self, class_name: ClassName, t: tuple[TypeName, ...]) -> ClassName:
        """
        获取泛型类的实例化对象。
        """
        if all(not isinstance(x, GenericArgument) for x in t):
            # 仅具体类型实参注册为实例化请求：实例的定义只能在定义该泛型类的
            # 模块中生成（本模块的泛型定义表中没有它），由Project.finish的
            # 不动点迭代把请求交给定义方（见开发疑问记录111）
            with _GENERIC_REGISTRY_LOCK:
                _GENERIC_CLS_INSTANCE_REQUESTS.setdefault(class_name.name, set()).add(t)
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
        if all(not isinstance(x, GenericArgument) for x in t):
            # 仅具体类型实参注册为实例化请求；泛型参数实参（泛型函数体内的
            # 递归调用）为伪实例，不产生定义
            with _GENERIC_REGISTRY_LOCK:
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
        # 全部条目读入后解析本模块的类型别名：指向本模块之后才定义的类型的别名
        # 同样可以解析，指向未知类型的别名在此报出（见开发疑问记录157）
        for alias in self._pending_aliases:
            self._resolve_alias(alias)
        self._pending_aliases.clear()
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
            case "TYPE_ALIAS":
                self._read_type_alias_decl(item_args)

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

    @staticmethod
    def _is_valid_c_name(name: str) -> bool:
        """检查是否为合法的显式C名（C标识符，允许$作为命名空间分隔符）。"""
        if name == "":
            return False
        return all(char.isalnum() or char == "_" or char == "$" for char in name) and \
            not name[0].isdigit()

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
        # 显式C名（cname "..."）：声明可脱离.vla命名空间指定C名称，
        # 使C名与实现所在的.c文件路径一致（见开发疑问记录103）
        explicit_c_name: str = item[5] if len(item) > 5 else ""
        if not self._is_valid_c_name(explicit_c_name):
            explicit_c_name = ""
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
            returns: list[TypeName] = list(map(lambda ret: self[ret, None], item_returns[::2])) if len(
                item_returns) > 1 else []
            if any(map(lambda ret: not isinstance(ret, TypeName), returns)):
                raise CompilerException("Function returns must be types.", self._src_info)
        finally:
            for arg in generic_arg_objs:
                self.remove(arg.name)
        if existing_native is not None:
            if list(existing_native.type.returns) != returns:
                raise CompilerException(
                    f"Native function {item_name} does not match the builtin binding.", self._src_info)
            existing_native.modifier = self.__get_modifier(name_parts)
            return
        func_type = FunctionTypeName(self._src_info, args, returns, generic_args)
        if item_name not in self._func_overload_times:
            self._func_overload_times[item_name] = 0
        func_namespace, func_self_name = SymbolTable._split_qualified_name(item_name)
        if explicit_c_name != "":
            if not is_native:
                raise CompilerException(
                    f"cname is only allowed on native function declarations ({item_name}).", self._src_info)
            # 显式C名：以空命名空间构造，使C名与默认参数全局变量名
            # 均直接使用该名称（如viola$io$file$open$$default$mode）
            func_namespace = []
            func_self_name = explicit_c_name
        elif len(func_namespace) == 0:
            # 未限定的函数名使用本模块的命名空间
            func_namespace = self._namespace
        if is_native:
            # 原生函数通常不使用重载序号（C名称与运行库一致，如viola$math$sqrt）；
            # 同名重载的原生函数（如log(x)与log(x, base)）使用$_N后缀区分
            # （运行库以相同后缀提供实现，如viola$math$log$_1）
            if self._func_overload_times[item_name] > 0:
                func_self_name = f"{func_self_name}$_{self._func_overload_times[item_name]}"
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
        func.modifier = self.__get_modifier(name_parts)
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
        <变量类型>%<变量名> [public | protected | private]
        """
        item: list[str] = item[0].split("%")
        name_parts: list[str] = item[1].split(" ")
        item_name: str = name_parts[0]
        item_type: str = item[0]
        var_namespace, var_self_name = SymbolTable._split_qualified_name(item_name)
        if len(var_namespace) == 0:
            # 未限定的变量名使用本模块的命名空间
            var_namespace = self._namespace
        # noinspection PyTypeChecker
        var = GlobalVariableName(self._src_info, var_namespace, var_self_name, self[item_type, None])
        if len(name_parts) > 1:
            var.modifier = self.__get_modifier(name_parts[1:])
        self.add(var, item_name, None)

    def _read_type_alias_decl(self, item: list[str]) -> None:
        """
        读取类型别名（using 别名 = 类型;，见开发疑问记录157）。记载格式如下：
        <别名>%<被别名的类型> [public | protected | private]

        别名以独立条目注册（可在符号表中查到它，并由type_aliases查询其定义），
        但类型名的查找会解析到被别名的类型（见_resolve_alias），因此别名不需要
        被别名的类型在本条目读入时已经注册：解析在查找时按名称进行，故
        using MyClass = Later; 这样"先别名后定义"的写法同样可用。
        """
        if item[0].strip() == "":
            raise CompilerException("Type alias entry is empty.", self._src_info)
        name_parts: list[str] = item[0].split(" ")
        alias_parts: list[str] = name_parts[0].split("%")
        item_name: str = alias_parts[0]
        if len(alias_parts) < 2 or alias_parts[1] == "":
            raise CompilerException(f"Type alias {item_name} has no target type.", self._src_info)
        alias_namespace, alias_self_name = SymbolTable._split_qualified_name(item_name)
        if len(alias_namespace) == 0:
            # 未限定的别名使用本模块的命名空间
            alias_namespace = self._namespace
        alias = TypeAliasName(self._src_info, alias_namespace, alias_self_name, alias_parts[1],
                              self.__get_modifier(name_parts[1:]))
        alias_key_name: str = alias.self_name if alias.raw_name.startswith(self._namespace_without_import) \
            else alias.raw_name
        if (alias_key_name, None) in self.symbols:
            # 同一模块同时以import与from...import导入时，符号表中会出现同一别名的
            # 重复条目（与类同样）：指向同一类型时忽略，指向不同类型才是冲突
            existing = self.symbols[alias_key_name, None]
            if isinstance(existing, TypeAliasName) and existing.target_name == alias.target_name:
                return
            raise CompilerException(f"Type alias {alias_key_name} already exists.", self._src_info)
        self.add(alias, alias_key_name, None)
        self._type_aliases[alias_key_name] = alias
        if alias_key_name == alias.self_name:
            # 本模块定义的别名：模块的条目读完后统一解析校验（见read_from），
            # 使指向本模块之后才定义的类型的别名同样可用，"指向未知类型"的别名
            # 则即便从未使用也报出（导入的别名不校验：其目标未必随导入条目一同
            # 加载，与类一样只在真正使用时报“找不到类型”）
            self._pending_aliases.append(alias)

    @property
    def type_aliases(self) -> dict[str, str]:
        """
        获取本符号表中的类型别名（别名 -> 被别名的类型），供调试查询其定义。
        """
        return dict(map(lambda kv: (kv[1].raw_name, kv[1].target_name), self._type_aliases.items()))

    def _resolve_alias(self, symbol: NamedSymbol) -> NamedSymbol:
        """
        把类型别名解析为被别名的类型（见开发疑问记录157）。

        别名在符号表中是独立条目，但类型名的查找一律返回被别名的类型，使别名
        在编译期完全透明（类型检查、方法查找与生成的C代码都按被别名的类型进行）。
        别名可以指向另一个别名（using A = B;），故沿链解析；解析结果缓存在别名
        对象上。链上的别名在此记录，同一别名再次出现即为循环定义（如
        using A = B; using B = A;），报出而不进入无限解析。
        """
        seen: set[int] = set()
        while isinstance(symbol, TypeAliasName):
            if id(symbol) in seen:
                raise CompilerException(f"Type alias {symbol.raw_name} is defined in a cycle.", self._src_info)
            seen.add(id(symbol))
            if symbol.resolved is not None:
                symbol = symbol.resolved
                continue
            # 解析自身的目标类型时再次进入本别名（如using A = A[];）：判定为循环
            if symbol.is_resolving or len(seen) > SymbolTable._MAX_ALIAS_DEPTH:
                raise CompilerException(f"Type alias {symbol.raw_name} is defined in a cycle.", self._src_info)
            symbol.set_resolving()
            try:
                target: NamedSymbol = self._lookup_symbol((symbol.target_name, None))
            except CompilerException:
                raise CompilerException(
                    f"Type alias {symbol.raw_name} refers to unknown type {symbol.target_name}.",
                    self._src_info)
            symbol.set_resolved(target)
            symbol = target
        return symbol

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
                    key: str = f"{self.clean_namespace(cls.raw_name)}.{method_name}"
                    if (key, tuple(args)) not in self.symbols:
                        self.add(existing, key, args)
                    for arg in generic_arg_obj_cls:
                        self.remove(arg.name)
                    return
        if f"{cls.name}.{method_name}" not in self._func_overload_times:
            self._func_overload_times[f"{cls.name}.{method_name}"] = 0
        symbol_key: str = f"{self.clean_namespace(cls.raw_name)}.{method_name}"
        if (symbol_key, tuple(args)) in self.symbols:
            existing = self.symbols[symbol_key, tuple(args)]
            if isinstance(existing, MethodName) and existing.cls.name == cls.name and \
                    [t.name for t in existing.type.args] == [t.name for t in args] and \
                    [t.name for t in existing.type.returns] == [t.name for t in returns]:
                # 相同的方法经多个导入路径重复注册（如多个模块都导入了同一模块），跳过
                for arg in generic_arg_obj_cls:
                    self.remove(arg.name)
                return
            raise CompilerException(f"Symbol {symbol_key} already exists.", self._src_info)
        # 原生方法（运行库提供实现）的C名称必须与运行库一致，重载序号由
        # ClassName.add_method（set_cls）统一追加一次；若此处再追加一次会得到
        # 双重后缀（如__new__$_0$_0），与运行库的__new__$_0不符导致链接失败。
        # 非原生方法沿用原有的“前置序号”命名（与set_cls的序号共同构成名称）。
        method_self_name: str = method_name if is_native else \
            f"{method_name}$_{self._func_overload_times[f'{cls.name}.{method_name}']}"
        method = MethodName(
            self._src_info, cls, method_self_name,
            func_type, is_abstract, is_static, item_args[1::2] if len(item_args) > 1 else [],
            item_returns[1::2] if len(item_returns) > 1 else [], modifier, export, is_native, is_final
        )
        self._func_overload_times[f"{cls.name}.{method_name}"] += 1
        method.set_default_params(item_default_args)
        for k, v in method.default_params.items():
            if v is not None:
                self.add(v, k, None)
        self.add(method, symbol_key, args)
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
        # impl声明的接口以"!"与父类型列表分隔（0.1起）
        extends_text, _, impl_text = parents_text.partition("!")
        parent_names: list[str] = []
        interfaces: list[ClassName] = []
        cls_interfaces: list[ClassName] = []
        if extends_text != "object":
            parent_names = extends_text.split(",")
            # noinspection PyTypeChecker
            parent = self[parent_names[0], None]
            if not isinstance(parent, ClassName):
                raise CompilerException(f"$parent class {parent_names[0]} is not a class.", self._src_info)
            if parent.is_final:
                raise CompilerException(f"Class {parent_names[0]} is final and can not be inherited.", self._src_info)
            # 其余父类型为接口（接口允许多继承）
            for interface_name in parent_names[1:]:
                interfaces.append(self.__get_interface(interface_name))
        # impl声明的接口
        for interface_name in filter(lambda x: x != "", impl_text.split(",")):
            interfaces.append(self.__get_interface(interface_name))
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
        cls.modifier = self.__get_modifier(modifiers)
        if len(cls_interfaces) > 0:
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
            if cls.is_interface and "static" not in item_text[2:] and property_name != "$$vtable":
                # 接口只允许方法和静态属性（$$vtable为编译器内部字段）
                raise CompilerException("Interfaces only allow static properties.", self._src_info)
            if "unsafe" in item_text[2:] and not cls.is_wrapper:
                # unsafe成员只允许存在于wrapper类
                raise CompilerException("unsafe properties are only allowed in wrapper classes.",
                                        self._src_info)
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
        if item[0].strip() == "":
            raise CompilerException("Enum entry is empty.", self._src_info)
        name_parts: list[str] = item[0].split(" ")
        enum_parts: list[str] = name_parts[0].split("%")
        if len(enum_parts) < 2 or enum_parts[1] == "":
            raise CompilerException(f"Enum {enum_parts[0]} has no based type.", self._src_info)
        item_name: str = enum_parts[0]
        based_type: str = enum_parts[1]
        if (based_type, None) not in self:
            raise CompilerException(f"Based type {based_type} not found.", self._src_info)
        if (item_name, None) in self:
            raise CompilerException(f"Enum {item_name} already exists.", self._src_info)
        enum_namespace, enum_self_name = SymbolTable._split_qualified_name(item_name)
        if len(enum_namespace) == 0:
            # 未限定的枚举名使用本模块的命名空间
            enum_namespace = self._namespace
        # noinspection PyTypeChecker
        enum = EnumName(self._src_info, enum_namespace, enum_self_name, self[based_type, None])
        # 本模块的枚举同时以裸名注册（与类的处理一致）：模块内的使用处
        # （Color.RED、Color c = ...）按裸名解析（见开发疑问记录160）
        enum_key_name: str = enum.self_name if enum.raw_name.startswith(self._namespace_without_import) \
            else enum.raw_name
        if (enum_key_name, None) in self:
            existing = self[enum_key_name, None]
            if isinstance(existing, EnumName) and existing.name == enum.name:
                enum_key_name = enum.raw_name
            else:
                raise CompilerException(f"Enum {enum_key_name} already exists.", self._src_info)
        self.add(enum, enum_key_name, None)

    def __get_interface(self, interface_name: str) -> ClassName:
        """获取接口类（用于extends的多个父类型与impl的接口列表）。

        接口名必须是已声明的接口，否则报编译时错误。
        """
        # noinspection PyTypeChecker
        interface = self[interface_name, None]
        if not isinstance(interface, ClassName) or not interface.is_interface:
            raise CompilerException(f"{interface_name} is not an interface.", self._src_info)
        return interface

    def __get_modifier(self, item: list[str]) -> Modifier:
        """
        获取访问权限级别。

        0.1起：无访问修饰符的默认情况为public（原为protected）。
        """
        is_public: bool = "public" in item
        is_private: bool = "private" in item
        is_protected: bool = "protected" in item
        if not is_public and not is_private and not is_protected:
            is_public = True
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
