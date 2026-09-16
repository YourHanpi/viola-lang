# -*- coding: utf-8 -*-
from .compiling_item import CompilingItem
from .expression import Expression, VariableRef, AttrOp, CallOp, UnpackExpr, CONVERTIBLE_TO_FUNC, TypeRef, ClassRef, \
    StringLiteral, TupleRef, CExpr, ArrayRef, convert_array_argument, needs_array_conversion, \
    too_few_unpack_targets_error, implicit_cast_prefix, implicit_cast_text
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
    ExceptionTypeName,
    AutoTypeName,
    ArrayTypeName,
    retain_text,
    destructor_name,
    LISTENER_T,
    FUNCTION_DEL_FUNC,
    type_is_fully_concrete,
    REFCOUNT_DEC_FUNC
)
from utils import CompilerException, unreachable_warning, SourceInfo, InternalCompilerException, SUPER_ASSIGN_MARKER

from abc import ABC, abstractmethod
from copy import copy
from enum import Enum
from typing import Optional

from utils.text_utils import renumber_marks as _renumber_marks
from utils.text_utils import sanitize_c_identifier

LISTENER_WAIT_FUNC = "viola$threads$waitListener"
# 函数级清理标签（CleanupBlock与各生成器共用的固定名称）：return语句跳到此处，
# 使函数级统一释放对带return的函数同样生效（见开发疑问记录196）
FUNCTION_CLEANUP_LABEL: str = "$$cleanup"
# 把"与正在传播的异常同时出现"的异常挂到其被抑制异常链上（实现于
# viola_libs/viola/lang/exception.c，见开发疑问记录196）
SUPPRESS_EXC_FUNC = "viola$lang$exception$suppress"
# 构造函数体中代表待构造对象的局部变量名（见ConstructorDef），
# 父类构造调用（super = 父类名(...)）需要在该对象上初始化父类成员
THIS_OBJ_NAME: str = "_thisObj"
# __new__到父类构造初始化函数（$__new__super）的名称映射
SUPER_NEW_SUFFIX: str = "$__new__super"
MARK_T: str = "viola$threads$Mark"
STACK_A_T: str = "viola$threads$StackA"
STACK_B_T: str = "viola$threads$StackB"
STACK_A_PUSH_FUNC: str = "viola$threads$pushStackA"
STACK_A_POP_FUNC: str = "viola$threads$popStackA"
STACK_B_PUSH_FUNC: str = "viola$threads$pushStackB"
STACK_B_POP_FUNC: str = "viola$threads$popStackB"
THREAD_INFO_T: str = "viola$threads$ThreadInfo"


def store_retain_text(target_text: str, target_var: VariableName, value: Expression) -> str:
    """生成把值存入槽位（变量、成员、返回值槽位）后对目标对象的一次retain。

    目标槽位自此持有一个对象，故计一次数；该槽位释放时递减并归零才析构
    （见开发疑问记录190）。非对象类型不计数；值表达式把新对象的所有权直接
    交给槽位时（其临时变量不会被释放）也不计数，否则只增不减而泄漏；
    unsafe变量由用户手动管理内存，同样不计数（见开发疑问记录191第4条）。
    返回含结尾换行的文本。
    """
    if not target_var.type.is_object or value.transfers_ownership or target_var.is_unsafe_managed:
        return ""
    return retain_text(target_text) + "\n"


def infer_array_literal_element_type(value: Optional[Expression], target: TypeName) -> None:
    """已知目标类型时，按目标数组类型的元素类型构造数组字面量（见开发疑问记录155）。

    数组字面量的元素类型默认由元素表达式推断（如[1, 2, 3]为int32），元素类型
    与目标数组不同时不做转换，只是把同一块内存按目标元素类型重解释
    （int32[]的数据按int64[]读取会越界读取堆内存）。此处按目标元素类型改写
    字面量，元素的写入交由C语言按目标类型隐式转换。

    更新表达式（`[1, 2, 3] => { [0] = 9 }`）的结果数组与源数组的元素类型相同，
    但更新项的下标赋值在解析时已按源数组的类型解析为__setitem__调用（其返回
    临时变量的类型也已确定），事后改写字面量的元素类型会使该调用与接收者类型
    不一致（生成的C代码报指针类型警告，结果也不可靠），故不向内层推断；该形式
    的元素类型不一致问题见开发疑问记录158。
    """
    if isinstance(value, ArrayRef) and isinstance(target, ArrayTypeName):
        value.set_inferred_element_type(target.element_type)


def convert_array_value(value: Optional[Expression], target: TypeName,
                        symbol_table: SymbolTable) -> Optional[Expression]:
    """数组字面量与数组转换的处理入口（见开发疑问记录155、158）。

    数组字面量：按目标元素类型改写（无需复制，见infer_array_literal_element_type）。
    其余数组表达式：元素类型不同时包装为逐元素转换（见convert_array_argument）。
    """
    if value is None or isinstance(value, ArrayRef):
        return value
    return convert_array_argument(value, target, symbol_table)


class _Mark:
    """调试标记，用于在生成的代码中插入源代码位置信息。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable) -> None:
        """
        初始化调试标记。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        """
        self._text_text: str = src_info.traceback_no_location + "\tat "
        self._lineno: int = src_info.lineno
        # 编号由符号表（即模块）分配：全局计数器会随并行编译的线程交错
        # 使同一工程的连续编译产出不同文本（见开发疑问记录117）
        self._mark_name: str = symbol_table.get_mark_counter()
        self._is_const_def: bool = False

    @classmethod
    def _utf16_units(cls, text: str) -> list[int]:
        """将Python字符串转换为UTF-16码元序列（含代理对）。"""
        encoded: bytes = text.encode("utf-16-le")
        return [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]

    @property
    def text_var_name(self) -> str:
        """获取标记文本的静态字符串变量名。"""
        return f"{self._mark_name}$text"

    @property
    def mark_declare(self) -> str:
        """获取标记的声明代码（静态结构体与静态文本字符串）。

        path/line为编译期常量，文本以UTF-16码元的静态数组内联展开：
        不分配堆内存、不占用编译器的临时变量计数器，也不参与变量的
        引用计数清理（见开发疑问记录87）。
        """
        units: list[int] = self._utf16_units(self._text_text)
        units_text: str = ", ".join(map(str, units)) if units else "0"
        data_name: str = f"{self._mark_name}$data"
        # 块作用域的静态初始化式必须是常量：码元数组单独声明为静态数组，
        # 其地址才是常量（复合字面量在块作用域为自动存储，不能这样用）
        return "\n".join([
            f"static viola$lang$uint16 {data_name}[] = {{{units_text}}};",
            f"static viola$lang$string {self.text_var_name} = "
            f"{{1, NULL, {len(units)}, {data_name}}};",
            f"static {MARK_T} {self._mark_name} = {{$$_PATH, {self._lineno}, &{self.text_var_name}}};",
        ])

    @property
    def mark_init(self) -> str:
        """标记无需运行时初始化（声明处已完整初始化）。"""
        return ""

    @property
    def mark_init_head(self) -> str:
        """标记无需头代码。"""
        return ""

    @property
    def mark_insert(self) -> str:
        """获取插入标记到栈中的代码。"""
        if self._is_const_def:
            return f"{STACK_A_PUSH_FUNC}(0, &{self._mark_name});"
        return f"{STACK_A_PUSH_FUNC}(listener->currentThreadId, &{self._mark_name});"

    @property
    def mark_pop(self) -> str:
        """获取从栈中弹出标记的代码。"""
        if self._is_const_def:
            return f"{STACK_A_POP_FUNC}(0);"
        return f"{STACK_A_POP_FUNC}(listener->currentThreadId);"

    def set_as_const_def(self) -> None:
        """将当前标记设置为常量定义标记。"""
        self._is_const_def = True


def renumber_marks(text: str) -> str:
    """
    将生成代码中的调试标记占位名按出现顺序重编号为 $$_MARK_0..$$_MARK_N。

    标记的占位名含符号表序号（见symbol.get_mark_counter），从而在进程内唯一；
    但标记是生成代码中的文件级静态变量，一个编译单元（.c）内只需互不相同，
    故写出时按编译单元统一重编号：编号只取决于标记在该文件中的出现顺序，
    与并行编译的线程交错无关（见开发疑问记录117、123）。
    实现见utils.text_utils（不使用re模块，见versions_dev_plan_zh.md"漏洞修复"）。
    :param text: 编译单元的代码文本。
    :return: 重编号后的文本。
    """
    return _renumber_marks(text)


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
        # traceback调试标记：语句执行前压入A栈、执行后弹出；异常时停留在
        # 栈上，供调试输出还原调用路径（见开发疑问记录87）。
        # 标记对象在模块全局初始化阶段创建，语句内只做压栈/退栈。
        self._mark: Optional[_Mark] = _Mark(src_info, symbol_table) if with_mark else None
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
        """获取全局初始化代码文本。"""
        return ""

    @property
    @abstractmethod
    def head_text(self) -> Optional[str]:
        """获取语句的头代码（变量声明等）。"""
        pass

    @property
    def value_expression(self) -> Optional[Expression]:
        """获取本语句携带的值表达式（无则为None）。

        供函数级统一释放收集语句经head_text声明的临时变量（见开发疑问记录191）。
        """
        return None

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

    @property
    def used_variables(self) -> set[VariableName]:
        """获取语句读取的所有变量（含本块/本语句内声明并赋值的变量）。

        与input_variables的区别：input_variables表示“需要由外部提供的变量”，
        语句块会减去自身的内部变量与外层已赋值的变量，用于依赖排序；而判断
        “某变量的最后一次使用”必须用本属性，否则这些变量会被误判为不再使用
        而提前释放（见开发疑问记录115）。
        """
        return self.input_variables

    @property
    def declared_variables(self) -> set[VariableName]:
        """获取本语句（含嵌套语句）声明的变量。

        释放语句只能在变量可见的作用域内插入：读取集合（used_variables）减去
        本属性，即“本语句从外层使用的变量”，其声明位于本语句之外
        （见开发疑问记录115）。
        """
        return set()

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
    def restore_listeners(self) -> dict[str, list[str]]:
        """获取语句创建的监听器对应的返回值复制代码（监听器名 -> 代码行）。

        异步调用的返回值由工作线程写入调用方分配的返回元组，
        在waitListener之后需要把元组成员复制回赋值目标（见CallOp.restore_text）。
        """
        return {}

    @property
    def deferred_listeners(self) -> list[str]:
        """获取本语句创建、且在所在块结束时等待的监听器名。

        语句形式的异步调用（async f();，无赋值目标）没有可据以确定等待位置的
        变量，其结果也无处可取，故登记为"块结束时等待"：否则任务入队后无人等待，
        函数可能在任务执行前结束（见开发疑问记录122）。
        """
        return []

    @property
    @abstractmethod
    def new_variables(self) -> set[VariableName]:
        """获取语句创建的新变量集合。"""
        pass

    @property
    def new_variables_ordered(self) -> list[VariableName]:
        """按声明顺序获取语句新声明的变量（生成确定性输出，见开发疑问记录115）。"""
        return list(self.new_variables)

    @abstractmethod
    def optimize(self) -> "Statement":
        """优化语句。"""
        pass

    @property
    @abstractmethod
    def outer_text(self) -> Optional[str]:
        """获取语句的外层代码文本（标记声明随语句自身输出，见text）。"""
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
            # 标记在语句所在作用域内声明（静态结构体，异常跳转越过它是合法的）
            self._mark.mark_declare,
            self._mark.mark_init,
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

    @property
    def used_variables(self) -> set[VariableName]:
        result: set[VariableName] = set()
        for stmt in self._stmts:
            result |= stmt.used_variables
        return result

    @property
    def declared_variables(self) -> set[VariableName]:
        result: set[VariableName] = set()
        for stmt in self._stmts:
            result |= stmt.declared_variables
        return result

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

    @property
    def new_variables_ordered(self) -> list[VariableName]:
        result: list[VariableName] = []
        for stmt in self._stmts:
            result.extend(stmt.new_variables_ordered)
        return result

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
            # 标记为丢弃变量：其值无人读取，不参与释放逻辑（见VariableName.is_discard）
            var._is_discard = True

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
        # 声明即初始化：把此处仍为“已声明”的变量登记为“已赋值”，
        # 使嵌套块内对已初始化变量的赋值能被重复赋值检查拒绝。
        # 前端命令顺序为SET_VAR_VALUE先于ADD_VAR，set_var_value被调用时
        # _var尚为空，无法在那里登记（见开发疑问记录104）
        if self._var_value is not None:
            to_assign: list[VariableName] = list(filter(
                lambda var: var.raw_name != "_" and var in self._var_states and
                self._var_states[var] == VariableState.DECLARED, self._var))
            if self._is_async:
                self._var_states.set_async_assigned(to_assign)
            else:
                self._var_states.set_assigned(to_assign)
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
                        self._var[i].resolve_auto_type(expr_type.types[i])
                    else:
                        self._var[i].resolve_auto_type(
                            TupleTypeName(self._src_info, expr_type.types[i:]))
                else:
                    if var_names_num > 1:
                        raise CompilerException("Too many variables for unpacking.", self._src_info)
                    self._var[i].resolve_auto_type(expr_type)
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
                    if needs_array_conversion(t1, t0):
                        # 解包处的数组元素类型不同：各目标由元组成员直接写入，没有
                        # 插入转换的位置，按错误元素类型解释同一块内存会读到缓冲之外，
                        # 故显式报出（见开发疑问记录158）
                        raise CompilerException(
                            f"Array element type conversion is not supported when unpacking a tuple: "
                            f"{t1.raw_name} (param {i}) to {t0.raw_name}.", self._src_info)
            else:
                # 目标数少于返回值数即尾部解包：暂不支持（见开发疑问记录147、150）。
                # 原先此处要求最后一个目标的类型为"剩余返回值构成的元组"，而元组
                # 类型的局部变量无法声明，故该形式一律报出"元组不能赋给…"的间接
                # 错误；现直接给出尾部解包不受支持的说明与计划中的显式标记形式
                raise too_few_unpack_targets_error(
                    len(expr_type.types), len(self._var), self._src_info)
        else:
            if len(self._var) > 1:
                raise CompilerException("Too many variables for unpacking.", self._src_info)
            # 数组字面量按声明类型的元素类型构造（推断可能改变字面量类型，
            # 须在类型检查之前进行，见开发疑问记录155）
            infer_array_literal_element_type(self._var_value, self._var[0].type)
            # 元素类型不同的数组值按目标元素类型逐个转换（见开发疑问记录158）；
            # 同样须在类型检查之前进行，使转换后的类型参与检查
            self._var_value = convert_array_value(self._var_value, self._var[0].type, self._symbol_table)
            expr_type = self._var_value.return_type
            if self._var[0].type.name != "auto" and \
                    not expr_type.convertible_to(self._var[0].type, self._symbol_table.symbols):
                raise CompilerException(f"{expr_type.raw_name} cannot be assigned to {self._var[0].type.raw_name}.",
                                        self._src_info)

    def _prepare_value_returns(self) -> None:
        """在获取head_text之前设置返回值目标（与_inner_text一致）。"""
        if self._var_value is not None and len(self._var) > 0 and \
                isinstance(self._var_value, (CallOp, UnpackExpr)):
            # 与_inner_text一致：先设置返回值目标，
            # 使head_text包含调用/解包产生的临时变量声明
            self._var_value.set_returns(self._var)

    @property
    def value_head_text(self) -> str:
        """获取初值表达式所需的临时变量声明文本（不含各变量自身的声明）。

        模块级（全局）变量的声明已移到文件作用域（见开发疑问记录167），
        __global__中只保留这部分临时变量声明与赋值语句。
        """
        self._prepare_value_returns()
        results: str = ""
        if self._var_value is not None and self._var_value.head_text is not None:
            results += "\n" + self._var_value.head_text
        if isinstance(self._var_value, UnpackExpr):
            # 元组解包：解包链的head_text不包含被解包元组的临时变量声明，补上
            to_unpack = getattr(self._var_value, "_to_unpack", None)
            while isinstance(to_unpack, UnpackExpr):
                to_unpack = getattr(to_unpack, "_to_unpack", None)
            if isinstance(to_unpack, TupleRef) and to_unpack.head_text is not None:
                results += "\n" + to_unpack.head_text
        if results.strip() == "":
            return ""
        return self._indent_text(results)

    @property
    def head_text(self) -> Optional[str]:
        self._prepare_value_returns()
        results = "\n".join(map(
            lambda var: var.declaration_text if not isinstance(var.type, GenericArgument) else "",
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

    @property
    def declared_variables(self) -> set[VariableName]:
        return set(self._var)

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
    def restore_listeners(self) -> dict[str, list[str]]:
        if self._var_value is None or self._var_value.listener_name is None:
            return {}
        if isinstance(self._var_value, (CallOp, UnpackExpr)) and len(self._var) > 0:
            # 与head_text/_inner_text一致：先设置返回值目标，
            # 使restore_text能按目标变量定位返回元组中的下标
            self._var_value.set_returns(self._var)
        restores: list[str] = list(filter(
            lambda x: x is not None, map(lambda var: self._var_value.restore_text(var), self._var)))
        # 异步调用的实参元组/返回元组在等待之后释放（见开发疑问记录192）
        deferred_release: Optional[str] = self._var_value.deferred_release_text
        if deferred_release is not None:
            restores.append(deferred_release)
        if len(restores) == 0:
            return {}
        return {self._var_value.listener_name: restores}

    @property
    def new_variables(self) -> set[VariableName]:
        return set(self._var)

    @property
    def new_variables_ordered(self) -> list[VariableName]:
        """按声明顺序获取本语句新增的变量（见开发疑问记录115）。"""
        return list(self._var)

    @property
    def value_expression(self) -> Optional[Expression]:
        """获取本语句携带的值表达式（无则为None，供函数级清理收集变量用）。"""
        return self._var_value

    def optimize(self, foldable: Optional[set[VariableName]] = None) -> "Statement":
        """
        :param foldable: 允许被常量折叠移除声明语句的变量集合（本块内定义的变量）。
        为None时不做限制。
        """
        if self._var_value is not None:
            self._var_value = self._var_value.optimize()
            if self._var_value.is_const and len(self._var) == 1 and not self._is_const_def:
                self._const_vars[self._var[0]] = self._var_value
                if foldable is not None and self._var[0] not in foldable:
                    # 本块外可见的变量（如被闭包捕获者）不删除声明语句：常量表随
                    # 本块结束而丢弃，而闭包体是独立语句块、不经由本块的常量表读取，
                    # 删除声明会使闭包体引用未声明的变量（见开发疑问记录195）
                    return self
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

    @property
    def has_initial_value(self) -> bool:
        """获取这一声明是否带有初值表达式。"""
        return self._var_value is not None

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
                    # 类类型的子类值赋给父类变量时补显式C转换（见开发疑问记录159）
                    front_text += f"{deref}{self._var[0].name} = " \
                                  f"{implicit_cast_text(self._var_value, self._var[0].type)};\n"
                    # 目标槽位自此持有该对象：计一次数（见开发疑问记录190）。
                    # 值来自返回指针形参的调用时（CallOp/UnpackExpr路径）由被调方负责
                    front_text += store_retain_text(deref + self._var[0].name, self._var[0], self._var_value)
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
        # 丢弃变量（赋值目标为_）：不登记符号表，其声明由本语句自行生成
        self._discard_vars: set[VariableName] = set()
        # 无返回值调用的赋值（如 async _ = voidFn();）：不声明变量、不做赋值
        self._is_void_assign: bool = False

    def add_var_name(self, var_name: str) -> None:
        """添加赋值目标变量名。"""
        if var_name == "_":
            # 丢弃变量（0.1要求）：允许在同一作用域内多次赋值，不登记到符号表，
            # 类型在finish时按表达式类型推断（与声明语句中的丢弃变量一致）
            discard_var = LocalVariableName(
                self._src_info,
                "$_discard$" + str(self._symbol_table.get_counter()),
                AutoTypeName(self._src_info)
            )
            discard_var._is_discard = True
            self._var.append(discard_var)
            self._discard_vars.add(discard_var)
            return
        if var_name == SUPER_ASSIGN_MARKER:
            # 父类构造初始化语句（super = 父类名(...);）的赋值目标：
            # 由前端在解析该语句时产生，用户代码无法构造出该名称
            # （原先使用this.super，已按开发疑问记录114移除该形式）
            self._is_super = True
            return
        if self._this_cls is not None and var_name.startswith("this."):
            var_name = var_name[len("this."):]
            if var_name not in self._this_cls.properties:
                raise CompilerException(f"{var_name} is not a property of {self._this_cls.name}.", self._src_info)
            property_symbol = self._this_cls.properties[var_name]
            var_name_type = property_symbol.type
            symbol = LocalVariableName(self._src_info, "_thisObj->" + var_name, var_name_type)
            # 成员自身的unsafe标记需随目标变量带下去：引用计数要按它决定是否
            # retain/release（见开发疑问记录191）
            symbol._is_unsafe = property_symbol.is_unsafe
            # 对象成员的赋值目标：不参与常量折叠（见VariableName.is_member）
            symbol._is_member = True
        else:
            symbol = self._symbol_table[var_name, None]
        if not isinstance(symbol, VariableName):
            raise CompilerException(f"{var_name} is not a variable.", self._src_info)
        self._var.append(symbol)
        self._var_states.set_assigned([symbol])
        if isinstance(symbol, GlobalVariableName):
            # 模块级变量被本模块赋值：本模块需在文件作用域提供其存储
            # （否则按"存储由其他翻译单元提供"生成extern声明，
            #   见SymbolTable.needs_global_storage与开发疑问记录168）
            self._symbol_table.mark_global_assigned(symbol.name)

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
        if len(self._var) == 1:
            # 数组字面量按赋值目标的元素类型构造（见开发疑问记录155）
            infer_array_literal_element_type(self._var_value, self._var[0].type)
            # 元素类型不同的数组值按目标元素类型逐个转换（见开发疑问记录158）
            self._var_value = convert_array_value(self._var_value, self._var[0].type, self._symbol_table)
        expr_type = self._var_value.return_type
        if isinstance(expr_type, TupleTypeName) and len(expr_type.types) == 0:
            # 空元组即无返回值（void）调用：仅允许赋给丢弃变量，此时不声明
            # 变量、不做赋值（调用本身即为副作用，见开发疑问记录121）
            if all(var in self._discard_vars for var in self._var):
                self._is_void_assign = True
                self._is_finished = True
                return
            raise CompilerException("Cannot unpacking an empty tuple.", self._src_info)
        self._infer_discard_types(expr_type)
        if isinstance(expr_type, TupleTypeName):
            if len(self._var) > len(expr_type.types):
                raise CompilerException("Too many variables to unpacking.", self._src_info)
            elif len(self._var) == len(expr_type.types):
                type_list: list[TypeName] = list(map(lambda var: var.type, self._var))
                for i, (t0, t1) in enumerate(zip(type_list, expr_type.types)):
                    if not t1.convertible_to(t0, self._symbol_table.symbols):
                        raise CompilerException(f"{t1.raw_name} (param {i}) cannot be assigned to {t0.raw_name}.",
                                                self._src_info)
                    if needs_array_conversion(t1, t0):
                        # 解包处的数组元素类型不同：各目标由元组成员直接写入，没有
                        # 插入转换的位置，按错误元素类型解释同一块内存会读到缓冲之外，
                        # 故显式报出（见开发疑问记录158）
                        raise CompilerException(
                            f"Array element type conversion is not supported when unpacking a tuple: "
                            f"{t1.raw_name} (param {i}) to {t0.raw_name}.", self._src_info)
            else:
                # 目标数少于返回值数即尾部解包：暂不支持（见开发疑问记录147、150）。
                # 与声明语句同样直接报出，不再间接地以"元组不能赋给…"拒绝
                raise too_few_unpack_targets_error(
                    len(expr_type.types), len(self._var), self._src_info)
        self._is_finished = True

    def _infer_discard_types(self, expr_type: TypeName) -> None:
        """按表达式类型推断丢弃变量（赋值目标为_）的类型。

        丢弃变量不登记到符号表，其C声明由本语句生成（见head_text），
        类型必须在此处确定以便生成声明与赋值代码。
        """
        if len(self._discard_vars) == 0:
            return
        for i, var in enumerate(self._var):
            if var not in self._discard_vars or not isinstance(var.type, AutoTypeName):
                continue
            if isinstance(expr_type, TupleTypeName):
                if i < len(self._var) - 1:
                    var.resolve_auto_type(expr_type.types[i])
                else:
                    var.resolve_auto_type(TupleTypeName(self._src_info, expr_type.types[i:]))
            else:
                var.resolve_auto_type(expr_type)

    @property
    def discard_variables(self) -> set[VariableName]:
        """获取本语句的丢弃变量（赋值目标为`_`，C名形如`$_discard$<n>`）。"""
        return self._discard_vars

    @property
    def head_text(self) -> Optional[str]:
        if not self._is_void_assign and isinstance(self._var_value, (CallOp, UnpackExpr)) and len(self._var) > 0:
            # 与_inner_text一致：先设置返回值目标，
            # 使head_text包含调用/解包产生的临时变量声明。
            # 无返回值调用不能设置返回值目标：否则会为其分配并不存在的返回元组
            # （见开发疑问记录121）
            self._var_value.set_returns(self._var)
        prefix: str = "\n".join(
            var.declaration_text for var in self._var if var in self._discard_vars
        ) if not self._is_void_assign else ""
        result: Optional[str] = self._var_value.head_text if self._var_value is not None else None
        if prefix != "":
            result = prefix if result is None else prefix + "\n" + result
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
    def restore_listeners(self) -> dict[str, list[str]]:
        if self._var_value is None or self._var_value.listener_name is None:
            return {}
        if not self._is_void_assign and isinstance(self._var_value, (CallOp, UnpackExpr)) and len(self._var) > 0:
            # 与head_text/_inner_text一致：先设置返回值目标，
            # 使restore_text能按目标变量定位返回元组中的下标。
            # 无返回值调用不设置返回值目标（见开发疑问记录121）
            self._var_value.set_returns(self._var)
        restores: list[str] = list(filter(
            lambda x: x is not None, map(lambda var: self._var_value.restore_text(var), self._var)))
        # 异步调用的实参元组/返回元组在等待之后释放（见开发疑问记录192）
        deferred_release: Optional[str] = self._var_value.deferred_release_text
        if deferred_release is not None:
            restores.append(deferred_release)
        if len(restores) == 0:
            return {}
        return {self._var_value.listener_name: restores}

    @property
    def new_variables(self) -> set[VariableName]:
        # 无返回值调用的赋值不产生变量（丢弃变量既不声明也不赋值）
        return set() if self._is_void_assign else set(self._var)

    @property
    def new_variables_ordered(self) -> list[VariableName]:
        """按声明顺序获取本语句新增的变量（见开发疑问记录115）。"""
        return [] if self._is_void_assign else list(self._var)

    @property
    def value_expression(self) -> Optional[Expression]:
        """获取本语句携带的值表达式（供函数级清理收集变量用）。"""
        return self._var_value

    def optimize(self, foldable: Optional[set[VariableName]] = None) -> "Statement":
        """
        :param foldable: 允许被常量折叠移除赋值语句的变量集合（本块内定义的变量）。
        为None时不做限制。
        """
        if self._var_value is not None:
            self._var_value = self._var_value.optimize()
            # 返回值变量不参与常量折叠：返回槽位在C层是指针形参，
            # 折叠会删除赋值语句，使函数返回未初始化/旧值。
            # 本块外定义的变量同样只登记常量、不删除语句：常量表随块结束丢弃，
            # 删除语句会静默丢失本块对该变量的赋值（见开发疑问记录104）
            if self._var_value.is_const and len(self._var) == 1 and not self._var[0].is_return:
                self._const_vars[self._var[0]] = self._var_value
                if foldable is not None and self._var[0] not in foldable:
                    return self
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
        if self._is_void_assign:
            # 无返回值调用：只生成调用本身，不做赋值、也不设置返回值目标
            # （设置返回值目标会为其分配并不存在的返回元组，见开发疑问记录121）
            return "\n".join(filter(
                lambda x: x is not None, [self._var_value.front_text, self._var_value.release_text]))
        if self._is_super:
            if self._var_value is None or self._this_cls is None or self._this_cls.parent is None:
                raise CompilerException("this.super requires a parent class constructor call.", self._src_info)
            parent = self._this_cls.parent
            if not isinstance(self._var_value, CallOp):
                raise CompilerException("this.super requires a constructor call.", self._src_info)
            # 使用父类实际注册的__new__方法的C名称，并改写为父类构造初始化函数：
            # 子类对象已由本构造函数分配，super只在其上初始化父类成员（开发疑问记录107）
            parent_new_name = None
            for (m_name, _), m in parent.methods.items():
                if m_name == "__new__" and m.cls.name == parent.name:
                    parent_new_name = m.name
                    break
            if parent_new_name is None:
                raise CompilerException("Parent class has no constructor.", self._src_info)
            super_new_name: str = parent_new_name.replace("$__new__", SUPER_NEW_SUFFIX, 1)
            args: str = ", ".join(map(lambda a: a.text, self._var_value._arg_list))
            if args != "":
                args += ", "
            call_text: str = f"{super_new_name}({args}({parent.c_calling_name}){THIS_OBJ_NAME}, listener);"
            # 实参自身的求值代码必须在此输出：本语句不走常规赋值路径，实参中
            # 作为值使用的调用（如 super = P(a, sqrt(x)); 的sqrt）其返回值先落入
            # 临时变量，若只取实参的text，临时变量只被声明而从未赋值，
            # 父类构造收到的是未初始化的实参（见开发疑问记录196）
            arg_front_text: Optional[str] = self._var_value.front_text
            if arg_front_text is not None and arg_front_text.strip() != "":
                return arg_front_text + "\n" + call_text
            return call_text
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
                # 类类型的子类值赋给父类变量时补显式C转换（见开发疑问记录159）
                front_text += f"{deref}{self._var[0].name} = " \
                              f"{implicit_cast_text(self._var_value, self._var[0].type)};\n"
                # 目标槽位自此持有该对象：计一次数（见开发疑问记录190）
                front_text += store_retain_text(deref + self._var[0].name, self._var[0], self._var_value)
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
        # 语句形式的异步调用没有赋值目标：被调函数有返回值时按返回值类型
        # 建立丢弃目标，使调用方分配返回元组（见开发疑问记录138）
        new_stmt._expr.set_discard_returns()
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
    def value_expression(self) -> Optional[Expression]:
        """获取本语句携带的值表达式（供函数级清理收集变量用）。"""
        return self._expr

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
    def deferred_listeners(self) -> list[str]:
        """语句形式的异步调用：登记为在所在块结束时等待其完成。

        async f();作为语句时不产生赋值目标，监听器无处登记（原先
        new_listeners返回空），入队的任务因而无人等待，函数可能在任务
        执行前结束（见开发疑问记录122）。
        """
        listener: Optional[str] = self._expr.listener_name
        return [listener] if listener is not None else []

    @property
    def restore_listeners(self) -> dict[str, list[str]]:
        """获取等待之后执行的代码：释放异步调用由工作线程使用的临时对象。

        语句形式的异步调用没有返回值目标，其返回值对象由返回元组持有
        （见开发疑问记录192）；实参元组与返回元组的释放同样必须在任务结束后
        （见CallOp.deferred_release_text），故随waitListener之后一并输出。
        """
        listener: Optional[str] = self._expr.listener_name
        if listener is None:
            return {}
        deferred_release: Optional[str] = self._expr.deferred_release_text
        if deferred_release is None:
            return {}
        return {listener: [deferred_release]}

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
        # 跳到函数级清理标签而不是用C的return：函数级统一释放（CleanupBlock）就
        # 输出在该标签处，用C的return会跳过它——只由函数级清理释放的变量（如作为
        # 实参的调用结果临时变量）在带return的函数中不被释放（见开发疑问记录196）。
        # 返回值经指针形参写入，与C的return等价。
        return finally_text + f"goto {FUNCTION_CLEANUP_LABEL};"


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

    @property
    def used_variables(self) -> set[VariableName]:
        return self._to_throw_expr.used_variables | set(
            *map(lambda finally_stmt: finally_stmt.used_variables, self._finally_stmt_list)
        )

    @property
    def declared_variables(self) -> set[VariableName]:
        if len(self._finally_stmt_list) == 0:
            return set()
        return set().union(*map(lambda x: x.declared_variables, self._finally_stmt_list))

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
            f"listener->exception = {self._to_throw_expr.text};",
            # 同步更新本函数的异常缓存，使后续语句的异常检查生效
            "$$exc = listener->exception;"
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


class DeferredReleaseStmt(Statement):
    """类型尚未确定的变量的释放语句（见开发疑问记录195）。

    泛型函数体内声明的变量，其类型可能是泛型参数：解析期无法判定"是否对象"，
    也无法拼写`->$refCount`与析构函数名（前者对基本类型非法）。本语句把判定与
    文本一并推迟到输出期：实例化时变量的类型被替换为具体类型（见instantiation），
    _inner_text据其实际类型渲染（复用VariableName.free_text，非对象类型为空串）；
    仍未实例化的伪实例（其代码不输出）同样不渲染。

    释放语句的守卫与递减计数都包含在free_text中，故本语句代替了普通释放路径的
    四条语句（守卫、释放、守卫结束、置空）。
    """

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 var: VariableName) -> None:
        """
        初始化延迟释放语句。
        :param var: 待释放的变量（其类型在实例化后成为具体类型）。
        """
        super().__init__(src_info, symbol_table, var_states)
        self._var: VariableName = var

    def as_async(self) -> "Statement":
        return super().as_async()

    def as_inline(self, inline_mapping: dict[str, str]) -> "Statement":
        return copy(self)

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

    @property
    def used_variables(self) -> set[VariableName]:
        return set()

    def insert_finally_stmt(self, finally_stmt: "Statement") -> None:
        pass

    def instantiation(self, type_args: dict[GenericArgument, TypeName]) -> "Statement":
        new_stmt = copy(self)
        new_stmt._var = self._var.instantiation(self._var.name, type_args)
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
        return self

    @property
    def outer_text(self) -> Optional[str]:
        return None

    @property
    def variables_states(self) -> dict[VariableName, VariableState]:
        return {}

    @property
    def _inner_text(self) -> str:
        if not type_is_fully_concrete(self._var.type):
            # 仍是泛型参数（伪实例，其代码不输出）：没有可渲染的释放代码
            return ""
        return self._var.free_text


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
            new_branch: CondStmt = branch.check_tail_recursive(func_name)
            # insert_finally_stmt就地修改分支并返回None，不能作为赋值来源
            new_branch.insert_finally_stmt(new_stmt._stmt)
            new_stmt._branches[i] = new_branch
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
    def used_variables(self) -> set[VariableName]:
        return self._cond_expr.used_variables | self._stmt.used_variables | \
            set().union(*map(lambda x: x.used_variables, self._branches))

    @property
    def declared_variables(self) -> set[VariableName]:
        return self._stmt.declared_variables | \
            set().union(*map(lambda x: x.declared_variables, self._branches))

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

    @property
    def used_variables(self) -> set[VariableName]:
        return self._stmt.used_variables

    @property
    def declared_variables(self) -> set[VariableName]:
        """catch子句声明的异常变量与catch体内的变量（其作用域限于catch体）。"""
        return self._stmt.declared_variables | {self._except_decl}

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
            # 捕获成功后清除待处理异常：否则catch块内后续语句的异常检查会
            # 立即跳转到清理标签，catch块无法继续执行
            "\t$$exc = NULL;",
            "\tlistener->exception = NULL;",
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

    @property
    def used_variables(self) -> set[VariableName]:
        return self._stmt.used_variables

    @property
    def declared_variables(self) -> set[VariableName]:
        return self._stmt.declared_variables

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

    @property
    def used_variables(self) -> set[VariableName]:
        """try/catch/finally各分支读取的全部变量。

        释放语句的定位按本属性判断最后一次使用：try块内的调用以及finally块
        读取的变量同样算作使用（原先只统计input_variables，块内已赋值的变量
        被减去，导致释放语句被插到仍在使用该变量的语句之前，
        见开发疑问记录115）。
        """
        result: set[VariableName] = self._try_stmt.used_variables | set(
            *map(lambda except_stmt: except_stmt.used_variables, self._except_stmt)
        )
        if self._finally_stmt is not None:
            result |= self._finally_stmt.used_variables
        return result

    @property
    def declared_variables(self) -> set[VariableName]:
        result: set[VariableName] = self._try_stmt.declared_variables | set(
            *map(lambda except_stmt: except_stmt.declared_variables, self._except_stmt)
        )
        if self._finally_stmt is not None:
            result |= self._finally_stmt.declared_variables
        return result

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
        # 别名的C名加$alias后缀：别名在编译期已解析为被别名的类型，
        # 该typedef只是占位文本，加后缀可避免与头文件中的#定义重名
        # （如用户以string为别名，见开发疑问记录163）
        return f"typedef {self._src_type_decl.name} {self._dst_type_name}$alias;"


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
            if v.is_return:
                # 返回值槽位在C层为指针形参（如string**），不是本函数的局部对象：
                # 按局部对象释放会把形参指针本身当作对象（获取其$refCount/$parent，
                # gcc按类型不符报warning，且可能free/递减到非法地址，见开发疑问
                # 记录144），其对象的所有权也随返回值交给调用方
                continue
            release: str = v.free_text
            if release == "":
                # unsafe变量（由用户手动管理内存）不生成释放代码
                continue
            self.add_text(f"if ({v.name}) {{ {release} }}")

    @property
    def text(self) -> str:
        return self._inner_text


class BlockStmt(Statement):
    """语句块，包含多条子语句。"""

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 introduces_c_scope: bool = False) -> None:
        """
        初始化语句块。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param introduces_c_scope: 本块是否在C层输出`do { ... } while(0);`（即
            引入C作用域）。块内声明的变量在块外不可见，函数级统一释放不得展开
            此类块（见开发疑问记录196）。
        """
        super().__init__(src_info, symbol_table, var_states, single_stmt=False)
        self._stmt: list[Statement] = []
        self._introduces_c_scope: bool = introduces_c_scope
        self._release_stmt_list: list[Statement] = []
        self._is_async: bool = False
        self._is_finished: bool = False
        self._outer_variables: dict[VariableName, VariableState] = var_states.state.copy()
        self._inner_variables: dict[VariableName, VariableState] = {}
        self._listeners: dict[VariableName, str] = {}
        # 无等待触发变量的监听器（语句形式的异步调用），按登记顺序在本块
        # 结束时等待（见Statement.deferred_listeners与开发疑问记录122）
        self._deferred_listeners: list[str] = []
        # 监听器名 -> 异步返回值复制回目标变量的代码（waitListener之后执行）
        self._listener_restores: dict[str, list[str]] = {}
        # 本块创建的全部监听器名（按创建顺序）：块的清理路径（$$N）与退出路径
        # （return/throw）上需要逐一等待尚未等待过的监听器，故不能只记剩余的
        # _listeners（它随首次使用而被移除，见开发疑问记录136）
        self._block_listeners: list[str] = []
        self._input_variables: set[VariableName] = set()
        self._new_variables: list[VariableName] = []
        self._used_outer_variables: list[VariableName] = []
        self._is_closure: bool = False
        self._closure_struct_setting_code: str = ""
        self._closure_struct_def: str = ""
        # 闭包的C名与其捕获结构体的转换语句（见set_as_closure）：捕获变量的
        # 类型可能是外层泛型函数的泛型参数，实例化后需按具体类型重新生成文本
        self._closure_name: str = ""
        self._closure_init_stmt: Optional[CStmt] = None
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
                    if not k.is_global:
                        # 模块级（全局）变量在本块内首次赋值：不在块退出时释放。
                        # 其存储与生命周期属于模块（在文件作用域定义、由__global__
                        # 初始化），在函数退出时释放会使后续使用读到已释放的对象
                        # （见开发疑问记录167）
                        self._new_variables.append(k)
                if current_state > VariableState.DECLARED:
                    raise CompilerException(f"Variable {k.raw_name} is already assigned.", stmt.src_info)
            else:
                self._inner_variables[k] = v
        # 待等待的监听器按登记顺序（即异步调用的书写顺序）遍历：input_variables
        # 是集合，直接遍历会因对象哈希（地址）差异使生成代码中的等待语句顺序
        # 随进程变化（见开发疑问记录117）
        for var in list(self._listeners.keys()):
            if var not in self._listeners:
                # 同一监听器的其余变量已在上一次等待中一并就绪并移除（见下），
                # 遍历的是一开始取得的快照，故此处需跳过
                continue
            if var in stmt.input_variables:
                wait_stmt = CStmt(stmt.src_info, self._symbol_table, self._var_states)
                listener_name: str = self._listeners[var]
                wait_text = "\n".join([
                    # 等待异步任务完成并取回其未捕获的异常，供本函数感知
                    f"$$exc = {LISTENER_WAIT_FUNC}({listener_name});",
                    # 取回的任务异常与throw语句一样发布到本函数的listener：
                    # 本函数若不捕获而退出，调用方据此感知（同步被调函数抛出时
                    # 由其throw语句发布，见开发疑问记录139）
                    "if ($$exc != NULL) { listener->exception = $$exc; }",
                    f"free({listener_name}$$_call);",
                    # 置空调用结构体：块的清理路径与退出路径据此判断该监听器是否
                    # 已被等待（取回的异常会使本语句跳到清理标签，不置空则清理
                    # 路径会对已释放的监听器再次等待，见开发疑问记录136）
                    f"{listener_name}$$_call = NULL;"
                ] + self._listener_restores.pop(listener_name, []))
                wait_stmt.set_text(wait_text)
                self._stmt.append(wait_stmt)
                # 同一监听器可能对应多个变量（多返回值的异步调用，见开发疑问
                # 记录140）：其全部返回值在这一次等待后一并就绪，故这些变量
                # 同时转为已赋值并一并从待等待表中移除，避免对同一监听器重复
                # waitListener（重复等待等于对已回收的任务再次等待）
                waited_variables: list[VariableName] = [
                    v for v, name in self._listeners.items() if name == listener_name]
                for waited_var in waited_variables:
                    if waited_var in self._outer_variables:
                        self._outer_variables[waited_var] = VariableState.ASSIGNED
                    else:
                        self._inner_variables[waited_var] = VariableState.ASSIGNED
                    del self._listeners[waited_var]
        self._listeners.update(stmt.new_listeners)
        self._deferred_listeners += stmt.deferred_listeners
        # 记录本块创建的全部监听器（语句形式的异步调用没有返回值目标，只登记在
        # _deferred_listeners中）：清理路径与退出路径需要按此顺序等待尚未等待过的
        # 监听器（见开发疑问记录133、136）
        for listener in dict.fromkeys(list(stmt.new_listeners.values()) + stmt.deferred_listeners):
            if listener not in self._block_listeners:
                self._block_listeners.append(listener)
        self._listener_restores.update(stmt.restore_listeners)
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

    def _release_variable(self, var: VariableName, src_info: SourceInfo,
                          new_stmt_list: list[Statement], register_cleanup: bool = True) -> None:
        """生成释放一个对象变量的语句，追加到块的语句列表（见finish）。

        释放=递减引用计数，归零才调用析构（见开发疑问记录190）。递减与判断合并在
        同一个条件里：分两步时另一线程可能在同一对象上并发释放，两次都读到0而
        重复析构（见开发疑问记录178）。同一变量的释放代码会输出到多处（正常路径
        的释放点与块的异常清理路径），各处的守卫使重复执行为空操作。

        :param new_stmt_list: 正在按反序拼接的语句列表（末尾整体反转，故此处
            按"先出现者后追加"的顺序追加，反转后为 守卫 → 释放 → 守卫结束 → 置空）
        :param register_cleanup: 是否把同一释放登记到块的异常清理路径
            （_release_stmt_list）。退出路径（return/throw）上的释放按同一变量
            另行调用本方法生成一套独立的语句，此时不再重复登记清理路径。
        """
        if not type_is_fully_concrete(var.type):
            # 类型尚未实例化（泛型函数体内的泛型参数类型）：此处无法判定"是否
            # 对象"、也无法拼写->$refCount与析构函数名（前者对基本类型非法），
            # 故生成一条在输出期按实例化后的类型渲染的释放语句
            # （见开发疑问记录195）
            deferred_stmt = DeferredReleaseStmt(src_info, self._symbol_table, self._var_states, var)
            deferred_stmt.remove_jump_mark()
            deferred_stmt.remove_mark()
            new_stmt_list.append(deferred_stmt)
            if register_cleanup:
                # 异常清理路径上的同一释放：与正常路径的语句分开创建
                cleanup_stmt = DeferredReleaseStmt(src_info, self._symbol_table, self._var_states, var)
                cleanup_stmt.remove_jump_mark()
                cleanup_stmt.remove_mark()
                self._release_stmt_list.append(cleanup_stmt)
            return
        if isinstance(var.type, FunctionTypeName):
            # 函数值（Function结构体）的释放走运行库的固定入口：函数类型没有
            # 方法表，按__del__方法解析会报"Variable to get attribute is not
            # a class type"（见开发疑问记录195）
            release_stmt = CStmt(src_info, self._symbol_table, self._var_states)
            release_stmt.add_text(f"\t{FUNCTION_DEL_FUNC}({var.name}, listener);")
        else:
            release_stmt = OpStmt(src_info, self._symbol_table, self._var_states)
            call_op = CallOp(src_info, self._symbol_table)
            call_op._is_internal = True
            attr_op = AttrOp(src_info, self._symbol_table)
            attr_op.set_attr("__del__")
            attr_op.set_caller(VariableRef(src_info, self._symbol_table, var))
            call_op.set_func(attr_op)
            release_stmt.set_expr(call_op)
            release_stmt.indent()
        # 释放代码位于块的异常清理路径中：异常时不应跳出本块
        # （否则try块的catch分发标签不可达），而是继续执行清理
        release_stmt.remove_jump_mark()
        null_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        null_stmt.remove_jump_mark()
        null_stmt.remove_mark()
        # 文本中一律使用变量的C名（var.name）：改写过的变量（内联重命名、
        # 丢弃变量等）其源码名与C名不同，按源码名输出会引用到未声明的变量
        null_stmt.add_text(f"\t{var.name} = NULL;")
        release_guard: str = f"if ({var.name} && {REFCOUNT_DEC_FUNC}(&{var.name}->$refCount) == 0) {{"
        begin_guard_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        begin_guard_stmt.remove_jump_mark()
        begin_guard_stmt.remove_mark()
        begin_guard_stmt.add_text(release_guard)
        end_guard_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        end_guard_stmt.remove_jump_mark()
        end_guard_stmt.remove_mark()
        end_guard_stmt.add_text("}")
        new_stmt_list.append(null_stmt)
        new_stmt_list.append(end_guard_stmt)
        new_stmt_list.append(release_stmt)
        new_stmt_list.append(begin_guard_stmt)
        if not register_cleanup:
            return
        # 异常清理路径上的同一释放：与正常路径的语句分开创建（同一语句对象
        # 在块内出现两次时，其调试标记与跳转标记的维护会互相影响）
        check_null_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        check_null_stmt.add_text(release_guard)
        check_null_stmt.remove_jump_mark()
        check_null_stmt.remove_mark()
        end_check_null_stmt = CStmt(src_info, self._symbol_table, self._var_states)
        end_check_null_stmt.remove_jump_mark()
        end_check_null_stmt.remove_mark()
        end_check_null_stmt.add_text("}")
        self._release_stmt_list.append(check_null_stmt)
        self._release_stmt_list.append(release_stmt)
        self._release_stmt_list.append(null_stmt)
        self._release_stmt_list.append(end_check_null_stmt)

    def finish(self) -> None:
        """完成语句块的设置，进行变量清理和代码生成。"""
        # 块中任何会导致退出的语句（如return）都意味着其后代码不可达
        self._drops_out = any(map(lambda s: s.drop_out, self._stmt))
        self._stmt.reverse()
        used_variables: set[VariableName] = set()
        # 本块内（含嵌套语句）被读取的全部变量：用于识别"声明后从未被读取"
        # 的变量（见下）
        all_used_variables: set[VariableName] = set()
        for stmt in self._stmt:
            all_used_variables |= stmt.used_variables
        # 异步声明且从未被读取的变量（见下），其在等待之后释放
        unused_async_releases: list[VariableName] = []
        new_stmt_list: list[Statement] = []
        for stmt in self._stmt:
            # 判断“最后一次使用”必须用used_variables（input_variables已减去
            # 块内定义/已赋值的变量，会把仍在使用该变量的语句误判为不使用，
            # 使释放语句插到使用之前）；再减去本语句自身声明的变量，因为那些
            # 变量的作用域在本语句之内，其释放由声明处所在的块负责
            # （见开发疑问记录115）。
            # 迭代顺序按变量名排序，使生成的释放代码与哈希种子无关
            stmt_used_variables: set[VariableName] = \
                stmt.used_variables - stmt.declared_variables
            for var in sorted(stmt_used_variables, key=lambda v: v.name):
                if var not in used_variables and var not in self._outer_variables and not var.is_global:
                    used_variables.add(var)
                    # 变量已在本块内完成最后一次使用并释放，不再向外层传播
                    self._input_variables.discard(var)
                    # unsafe变量由用户手动管理内存，不参与引用计数（见开发疑问记录191）
                    # 类型尚未实例化时也要生成释放语句：泛型函数体内的变量其
                    # "是否对象"须待实例化后才能判定（见开发疑问记录195）
                    if (var.is_object or not type_is_fully_concrete(var.type)) and not var.is_unsafe_managed:
                        self._release_variable(var, stmt.src_info, new_stmt_list)
                elif var in self._outer_variables and var not in self._used_outer_variables and not var.is_global:
                    self._used_outer_variables.append(var)
            # 声明后从未被读取的变量：没有任何语句能触发其"最后一次使用"，
            # 其释放语句因而从不生成（见开发疑问记录192）。此类变量在其声明
            # 语句之后立即释放——尽早释放已分配但未使用的对象。
            # 只处理声明语句本身：复合语句（if/while/try/嵌套块）的
            # declared_variables会递归并入嵌套语句内声明的变量，那些变量的
            # C声明在嵌套C块内，在此处引用会超出作用域（见开发疑问记录115）；
            # 它们的释放由该嵌套块自身的本段逻辑生成。
            if isinstance(stmt, DeclStmt):
                for var in sorted(stmt.declared_variables, key=lambda v: v.name):
                    if var.is_discard:
                        # 丢弃变量（`_`）：其C名与源码名不同（`$_discard$<n>`）、
                        # 由语句自身声明，其值由返回元组或被调方处理，不在此释放
                        continue
                    if var in all_used_variables or var not in self._inner_variables:
                        # 被读取过（由上面的"最后一次使用"处理），或并非本块
                        # 声明的变量
                        continue
                    if not (var.is_object or not type_is_fully_concrete(var.type)) or \
                            var.is_unsafe_managed or var.is_return:
                        # 非对象类型无释放动作（类型未实例化时不能判定，见
                        # 开发疑问记录195）；unsafe变量由用户手动管理内存；
                        # 返回值槽位在C层是指针形参，其对象随返回值交给调用方
                        continue
                    if var in stmt.new_listeners:
                        # 异步声明的变量在等待之后才有值，此处释放会与其后的
                        # 赋值错位（释放时变量仍为NULL，赋值后再无人释放）
                        unused_async_releases.append(var)
                        continue
                    self._release_variable(var, stmt.src_info, new_stmt_list)
            stmt.set_jump_mark(self._cleanup_mark_name)
            new_stmt_list.append(stmt)
        new_stmt_list.reverse()
        self._stmt = new_stmt_list
        # 本块创建的全部监听器（含已在首次使用处等待过的，见开发疑问记录136）：
        # 清理路径与退出路径上的等待都按此顺序生成。按监听器名去重——同一监听器
        # 被等待两次会重复waitListener并重复free其调用结构体
        # （as_async/as_inline的块副本与本体共享_listeners/_deferred_listeners）
        block_listeners: list[str] = list(dict.fromkeys(self._block_listeners))
        wait_texts: dict[str, str] = {}
        # 清理路径/退出路径上的等待文本：与正常路径不同，只在调用结构体仍存在时
        # 才等待（正常路径已等待过的监听器其结构体已置空、监听器已释放）
        cleanup_wait_texts: dict[str, str] = {}
        # 正常路径的等待消费掉的restores：清理路径/退出路径上的等待需要补上
        # 同样的复制（两者互斥，同一处只执行一次）
        restores_of: dict[str, list[str]] = {}
        for listener in dict.fromkeys(list(self._listeners.values()) + self._deferred_listeners):
            wait_stmt = CStmt(self.src_info, self._symbol_table, self._var_states)
            restores: list[str] = self._listener_restores.pop(listener, [])
            restores_of[listener] = restores
            wait_text = "\n".join(
                [f"$$exc = {LISTENER_WAIT_FUNC}({listener});",
                 # 取回的任务异常与throw语句一样发布到本函数的listener：
                 # 本函数若不捕获而退出，调用方据此感知（见开发疑问记录139）
                 "if ($$exc != NULL) { listener->exception = $$exc; }",
                 # 任务已完成，调用结构体不再被引用：释放之（与
                 # BlockStmt.add_stmt的等待路径一致，避免语句形式的异步调用
                 # 在循环中每次泄漏一个结构体）
                 f"free({listener}$$_call);",
                 # 置空调用结构体：取回的异常会使本语句跳到清理标签$$N，而清理
                 # 路径据该指针判断是否已等待过——不置空则那里会对已释放的监听器
                 # 再次waitListener并重复free其结构体（见开发疑问记录136）
                 f"{listener}$$_call = NULL;"] + restores)
            wait_texts[listener] = wait_text
            wait_stmt.set_text(wait_text)
            # 等待语句在finish中追加，未经过上面统一设置跳转标记的循环；
            # 若不设置，取回异常后会跳到函数级$$cleanup，绕过本块所属try的
            # catch分发标签（见开发疑问记录84）
            wait_stmt.set_jump_mark(self._cleanup_mark_name)
            self._stmt.append(wait_stmt)
        for listener in block_listeners:
            # 已在首次使用处等待过的监听器其restores已被该处的等待消费
            # （见BlockStmt.add_stmt），故此处取不到（为空）
            restores: list[str] = restores_of.get(listener, [])
            cleanup_wait_texts[listener] = "\n".join([
                # 只等待尚未等待过的监听器：正常路径的等待会把调用结构体置空，
                # 不做判断会重复waitListener并重复free结构体
                f"if ({listener}$$_call != NULL) {{",
                # 任务自身的异常不能顶掉正在传播的异常（否则本块的异常会被
                # 吞掉、catch不再执行），只在无待传播异常时采用——与同步调用
                # 之后刷新异常缓存的写法一致
                f"\t{EXCEPTION_T} *$$waited_exc = {LISTENER_WAIT_FUNC}({listener});",
                f"\tfree({listener}$$_call);",
                f"\t{listener}$$_call = NULL;",
                # 取回的任务异常同样发布到本函数的listener，使其在
                # "本函数未捕获而退出"时被调用方感知（见开发疑问记录139）。
                # 已有异常正在传播时不丢弃任务异常，而是把它挂到该异常的被抑制
                # 异常链上（见开发疑问记录196）：丢弃会使它既不被报告、也不被
                # 释放（异常对象的内存泄漏）
                "\tif ($$waited_exc != NULL) {",
                "\t\tif ($$exc == NULL) { $$exc = $$waited_exc; listener->exception = $$exc; }",
                f"\t\telse {{ {SUPPRESS_EXC_FUNC}($$exc, $$waited_exc); }}",
                "\t}",
                "}"] + restores)
        # 块内的return/throw会直接退出函数，绕过块末尾的等待语句（return是C的
        # return，既不经过块末尾的等待，也不经过本块的清理路径），故把同一等待
        # 插到块内各退出语句之前，否则入队的任务可能无人等待
        # （见开发疑问记录130）；按变量等待的监听器同样如此——它在变量的首次
        # 使用处等待，若退出语句早于该处，等待被绕过（见开发疑问记录136）
        for listener in block_listeners:
            exit_wait_stmt = CStmt(self.src_info, self._symbol_table, self._var_states)
            exit_wait_stmt.set_text(cleanup_wait_texts[listener])
            # 等待后直接执行退出语句自身：不取回异常、不跳转（退出路径上函数级
            # 清理代码同样不执行，与既有的按变量等待行为一致）
            exit_wait_stmt.remove_jump_mark()
            # 同一等待被插入块内每条退出语句，带调试标记会重复输出标记声明
            exit_wait_stmt.remove_mark()
            self.insert_finally_stmt(exit_wait_stmt)
        # 退出路径上的等待之后，还要释放"异步声明且从未被读取"的变量：其值由
        # 退出路径的等待写入，而退出路径原先只执行等待与返回值复制，这些对象在
        # 该路径上从不释放（见开发疑问记录193第2条的答复）。释放语句按与等待
        # 相同的顺序插入：早于等待则变量尚未有值（守卫为空操作），晚于退出语句
        # 则不会执行。变量声明由块提升到C块开头（见_inner_text），故声明位置
        # 晚于退出语句时也能引用（彼时变量为NULL，守卫为空操作）。
        if len(unused_async_releases) > 0:
            exit_release_list: list[Statement] = []
            for var in unused_async_releases:
                self._release_variable(var, self.src_info, exit_release_list,
                                       register_cleanup=False)
            exit_release_list.reverse()
            for release_stmt in exit_release_list:
                # 同一释放被插入块内每条退出语句：带调试标记会重复输出标记声明
                # （与退出路径上的等待一致）。跳转标记同样移除：退出路径上不再
                # 跳转，与正常路径、清理路径上的同一释放一致。
                release_stmt.remove_mark()
                release_stmt.remove_jump_mark()
                self.insert_finally_stmt(release_stmt)
        # 异步声明且从未被读取的变量（见finish的说明）：其值由上面的等待写入，
        # 故释放语句位于这些等待之后（异常路径上的同一释放已登记在
        # _release_stmt_list中，位于清理路径的等待之后）
        if len(unused_async_releases) > 0:
            late_release_list: list[Statement] = []
            for var in unused_async_releases:
                self._release_variable(var, self.src_info, late_release_list)
            late_release_list.reverse()
            self._stmt.extend(late_release_list)
        cleanup_mark = CStmt(self.src_info, self._symbol_table, self._var_states)
        cleanup_mark.remove_jump_mark()
        cleanup_mark.add_text(f"goto {self._after_cleanup_mark_name};")
        cleanup_mark.add_text(f"{self._cleanup_mark_name}:")
        self._stmt.append(cleanup_mark)
        # 清理标签之后的等待：块内语句末尾的`if ($$exc) goto $$N;`与被调函数抛出
        # 的异常都跳到这里，绕过块末尾的等待语句，入队的任务在这条路径上原先无人
        # 等待（见开发疑问记录133）；按变量等待的监听器在其首次使用前发生异常
        # 跳转时同样被绕过，故一并补上（见开发疑问记录136）。等待须位于释放语句
        # 之前——异步任务可能仍在使用这些局部对象
        for listener in block_listeners:
            cleanup_wait_stmt = CStmt(self.src_info, self._symbol_table, self._var_states)
            cleanup_wait_stmt.set_text(cleanup_wait_texts[listener])
            # 已在异常路径上：等待自身不再跳转（否则取回异常后又跳回$$N），
            # 也不带调试标记（与退出路径上的等待一致）
            cleanup_wait_stmt.remove_jump_mark()
            cleanup_wait_stmt.remove_mark()
            self._stmt.append(cleanup_wait_stmt)
        self._stmt += self._release_stmt_list
        after_cleanup_mark = CStmt(self.src_info, self._symbol_table, self._var_states)
        after_cleanup_mark.remove_jump_mark()
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
    def value_expression(self) -> Optional[Expression]:
        """获取本语句携带的值表达式（无则为None）。"""
        return None

    @property
    def body_statements(self) -> list[Statement]:
        """获取本块直接包含的语句（展开常量折叠产生的_StmtList与不引入C作用域的嵌套块）。

        用于函数级统一释放时收集"本函数体直接声明的变量"：这些变量的C声明位于
        本块自己的C块内，故在本块末尾的清理标签处仍在作用域内；嵌套块内声明的
        变量不在其中（其声明在嵌套C块内，见开发疑问记录115）。

        函数体块本身不引入C作用域，但函数体语句总被包在一个由_parse_block_stmt
        产生的嵌套BlockStmt中（见开发疑问记录195），故须沿"不引入C作用域"的块
        逐层展开，否则函数级统一释放永远收集不到任何变量、从不生效
        （见开发疑问记录196）。引入C作用域的块（`do { ... } while(0);`，即源码中
        以花括号书写的块语句）不展开：其中声明的变量在函数末尾不可见。
        """
        result: list[Statement] = []
        for stmt in self._stmt:
            if isinstance(stmt, _StmtList):
                result.extend(stmt.stmts)
            elif isinstance(stmt, BlockStmt) and not stmt.introduces_c_scope:
                result.extend(stmt.body_statements)
            else:
                result.append(stmt)
        return result

    @property
    def introduces_c_scope(self) -> bool:
        """获取本块是否引入C作用域（在C层输出`do { ... } while(0);`）。

        引入C作用域的块内声明的变量在块外不可见，函数级统一释放不得引用
        （见开发疑问记录196）。
        """
        return self._introduces_c_scope

    @property
    def input_variables(self) -> set[VariableName]:
        return self._input_variables

    @property
    def used_variables(self) -> set[VariableName]:
        """本块从外层读取的变量（供外层块定位“变量的最后一次使用”）。

        不含本块内声明的变量：那些变量由本块自身的释放逻辑处理。
        _input_variables只统计“尚未由外层赋值”的变量，故需并入
        _used_outer_variables（本块内读取到的外层变量）。
        注意不可递归合并嵌套语句的读取集合：嵌套块内声明的变量（含表达式
        临时变量）由嵌套块自行释放，向外层传播会使外层在其作用域之外
        生成释放语句（见开发疑问记录115）。
        """
        return self._input_variables | set(self._used_outer_variables)

    @property
    def declared_variables(self) -> set[VariableName]:
        result: set[VariableName] = set()
        for stmt in self._stmt:
            result |= stmt.declared_variables
        return result

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

    @property
    def new_variables_ordered(self) -> list[VariableName]:
        """按声明顺序获取本块新增的变量。

        用于生成函数级清理代码（释放顺序不确定会使同一源码在不同编译进程下
        生成不同的输出，见开发疑问记录115）。
        """
        return list(self._new_variables)

    def optimize(self) -> "BlockStmt":
        const_vars: dict[VariableName, Expression] = {}
        # 只有本块内定义的变量才允许折叠掉赋值语句：常量表随本块结束而丢弃，
        # 折叠本块外变量的赋值会使其被静默丢弃（见开发疑问记录104）。
        # 模块级（全局）变量同样不允许折叠：其赋值是对模块存储的写入，
        # 折叠掉语句会使全局变量保持未初始化（见开发疑问记录167）。
        # 对象成员（this.X = ...）同样不允许：对象可能在本块之外被读取，
        # 折叠掉赋值语句会使成员保持未初始化（见开发疑问记录193。
        # 实测构造函数中的`this.value = 7;`被删除，构造出的对象成员为0）
        # 被闭包捕获的变量同样不允许折叠：闭包体是独立语句块，其读取不经由本块
        # 的常量表，折叠掉声明/赋值会使闭包体引用未声明的变量（见开发疑问记录195）
        foldable: set[VariableName] = set(
            filter(lambda var: var not in self._outer_variables and not var.is_global and not var.is_member
                               and not self._symbol_table.is_captured(var),
                   self._inner_variables))
        for i, stmt in enumerate(self._stmt):
            stmt = stmt.substitute(const_vars)
            if isinstance(stmt, (AssignStmt, DeclStmt)):
                # 限定可折叠变量的集合：本块外可见的变量（外层变量、模块级变量、
                # 对象成员、被闭包捕获者）不删除赋值/声明语句
                stmt = stmt.optimize(foldable)
            else:
                stmt = stmt.optimize()
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
        self._closure_name = closure_name
        self._used_outer_variables = [v for v in self._used_outer_variables if v not in args]
        # 被捕获的外层变量不参与外层块的常量折叠：闭包体是独立语句块，对捕获
        # 变量的读取不经由外层块的常量表，折叠掉其声明/赋值语句会使闭包体引用
        # 未声明的变量（见开发疑问记录195）
        for var in self._used_outer_variables:
            self._symbol_table.mark_captured(var)
        self._rebuild_closure_texts()
        if self._closure_init_stmt is None:
            self._closure_init_stmt = CStmt(self._src_info, self._symbol_table, self._var_states)
            self._stmt.insert(0, self._closure_init_stmt)
        self._closure_init_stmt.set_text(self._closure_convert_text)

    def _rebuild_closure_texts(self) -> None:
        """按捕获变量的当前类型重新生成捕获结构体的定义与成员赋值文本。

        捕获变量的类型可能是外层泛型函数的泛型参数（如`auto f = sq() -> (T[] r)
        { r = local; };`捕获T[]型的local）：结构体定义与闭包体内的成员转换都要
        用到这些类型的C名，而set_as_closure在解析期调用（彼时类型还是占位符），
        故实例化时按具体类型重新生成（BlockStmt.rebuild_for_instantiation，
        见开发疑问记录194）。
        """
        struct_name: str = f"struct {self._closure_name}$Capture"
        used_outer_variables_decl: list[str] = list(
            map(lambda x: f"\t{x.type_name_pair_calling};", self._used_outer_variables))
        # 捕获结构体的定义输出到模块级（外层函数分配捕获结构体时同样需要它），
        # 闭包体内仅做成员转换；捕获结构体的析构函数与其定义一同输出
        self._closure_struct_def = "\n".join([
            f"{struct_name} {{",
            "\n".join(used_outer_variables_decl),
            "};",
            self._closure_capture_del_text
        ])
        struct_alloc: str = \
            f"{struct_name} *{self._closure_name}$$capture = ({struct_name} *)malloc(sizeof({struct_name}));"
        # 捕获对象成员时retain：捕获结构体自此持有一个引用，闭包因而比被捕获的
        # 局部变量活得更久时不致访问已释放的对象（对象随闭包的释放而释放，
        # 见_closure_capture_del_text；原实现不计数，见开发疑问记录195）
        used_outer_variables_set: list[str] = []
        for x in self._used_outer_variables:
            used_outer_variables_set.append(f"{self._closure_name}$$capture->{x.name} = {x.name};")
            if x.is_object and not x.is_unsafe_managed:
                used_outer_variables_set.append(retain_text(
                    f"{self._closure_name}$$capture->{x.name}"))
        self._closure_struct_setting_code = struct_alloc + "\n" + "\n".join(used_outer_variables_set)

    @property
    def capture_del_name(self) -> str:
        """获取捕获结构体析构函数的C名。

        名字含各捕获变量的类型名：本闭包的捕获结构体按捕获变量的类型生成，
        泛型函数体内实例化后各实例的类型不同（见rebuild_for_instantiation），
        名字必须随之不同，否则同一模块中的多个实例会定义同名函数。
        无捕获变量时不需要类型后缀（各实例的捕获结构体形状相同）。
        """
        suffix: str = "$".join(sanitize_c_identifier(v.type.name) for v in self._used_outer_variables)
        return f"{self._closure_name}$capture$del" + (f"${suffix}" if suffix != "" else "")

    @property
    def _closure_capture_del_text(self) -> str:
        """获取捕获结构体的析构函数文本。

        Function结构体的$captureDel指向本函数：引用计数归零时由
        viola$lang$function$__del__调用，释放捕获的对象成员并free捕获结构体
        自身（原实现只free Function结构体，二者都不释放，见开发疑问记录195）。
        成员类型可能是泛型参数，故本文本在实例化时随捕获结构体一同重建
        （见rebuild_for_instantiation）。
        """
        del_name: str = self.capture_del_name
        member_releases: list[str] = []
        for x in self._used_outer_variables:
            if not x.is_object or x.is_unsafe_managed:
                continue
            if not type_is_fully_concrete(x.type):
                # 捕获变量的类型仍是泛型参数（如T[]）：析构函数名含元素类型名，
                # 此刻拼不出来。实例化时本段文本会随捕获结构体一同重建
                # （见rebuild_for_instantiation），届时类型已是具体类型
                continue
            member_releases.append("\n".join([
                f"\tif ($$p->{x.name} && {REFCOUNT_DEC_FUNC}(&$$p->{x.name}->$refCount) == 0) {{",
                f"\t\t{destructor_name(x.type)}($$p->{x.name}, listener);",
                "\t}"
            ]))
        return "\n".join([
            f"static void {del_name}(void *$$capture, {LISTENER_T} *listener) {{",
            f"\tstruct {self._closure_name}$Capture *$$p = (struct {self._closure_name}$Capture *)$$capture;",
            "\tif ($$p == NULL) { return; }",
            *member_releases,
            "\tfree($$p);",
            "}"
        ])

    @property
    def _closure_convert_text(self) -> str:
        """获取闭包体内把捕获结构体成员转换到局部变量的文本。"""
        struct_name: str = f"struct {self._closure_name}$Capture"
        used_outer_variables_convert: list[str] = list(
            map(lambda x: f"{x.type_name_pair_calling} = $$captureStructPtr->{x.name};",
                self._used_outer_variables))
        return "\n".join([
            f"{struct_name} *$$captureStructPtr = ({struct_name} *)$$capture;",
            "\n".join(used_outer_variables_convert)
        ])

    def rebuild_for_instantiation(self, type_args: dict[GenericArgument, TypeName]) -> None:
        """按实例化后的类型重建捕获结构体的文本（见_rebuild_closure_texts）。

        捕获变量的类型对象要一并实例化：_used_outer_variables原先只被浅拷贝到
        实例化副本，其类型仍是占位类型。
        """
        if not self._is_closure:
            return
        self._used_outer_variables = [v.instantiation(v.name, type_args)
                                      for v in self._used_outer_variables]
        self._rebuild_closure_texts()
        if self._closure_init_stmt is None:
            return
        # 初始化语句各实例一份：CStmt.instantiation返回自身（共享同一对象），
        # 沿用共享对象会使后一个实例的文本覆盖前一个实例（捕获变量的类型不同）
        new_init = CStmt(self._src_info, self._symbol_table, self._var_states)
        new_init.set_text(self._closure_convert_text)
        for i, stmt in enumerate(self._stmt):
            if stmt is self._closure_init_stmt:
                self._stmt[i] = new_init
                break
        self._closure_init_stmt = new_init

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

    def __init__(self, src_info: SourceInfo, symbol_table: SymbolTable, var_states: VariableStateTable,
                 introduces_c_scope: bool = False) -> None:
        """
        初始化函数体语句块。
        :param src_info: 源代码信息。
        :param symbol_table: 符号表。
        :param var_states: 变量状态表。
        :param introduces_c_scope: 见BlockStmt的同名参数。
        """
        super().__init__(src_info, symbol_table, var_states, introduces_c_scope)
        self._stmt_set: set[Statement] = set()
        self._variable_dependencies: dict[VariableName, Statement] = {}
        self._cond_stmt_buffer: list[Statement] = []

    def add_stmt(self, stmt: Statement) -> None:
        """向函数体中添加一条语句，处理条件分支缓冲和变量依赖。"""
        if isinstance(stmt, ReturnStmt):
            # fn函数按需执行，求出所有返回值后自动退出，不允许return
            raise CompilerException("fn functions can not use the return statement.", stmt.src_info)
        if isinstance(stmt, ThrowStmt):
            # fn函数按需执行，不允许抛出异常（throw会被依赖排序丢弃，见开发疑问记录105）
            raise CompilerException("fn functions can not use the throw statement.", stmt.src_info)
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
        if isinstance(stmt, OpStmt | ReturnStmt | CStmt):
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
