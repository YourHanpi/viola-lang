# -*- coding: utf-8 -*-
from backend.compiling_item import CompilingItem
import backend.definition as definition
import backend.expression as expression
import backend.project as project
import backend.statement as statement
import backend.symbol as symbol
from utils import SourceInfo, InternalCompilerException, VIOLA_INIT, COMPILER_PARAMS, CompilerException
from utils.file_marks import SYMBOL_TABLE_POSTFIX, COMMAND_POSTFIX, CACHE_DIR
from utils.logger import Logger
from utils.task import TaskResult, TaskResultState

from enum import Enum
import os
from traceback import format_exc
from typing import Callable, Optional


class _ExecMode(Enum):
    """执行模式枚举：SQ 表示语句块模式，FN 表示函数模式。"""
    SQ = 0
    FN = 1


class _ScopeCount(Enum):
    """作用域计数枚举：HOLD 表示保持作用域，INC 表示增加作用域。"""
    HOLD = 0
    INC = 1


class CompilerVM:
    """编译器虚拟机，负责执行编译指令、管理符号表和编译栈。"""

    _ENCODING: str = COMPILER_PARAMS["encoding"]

    def __init__(self, proj: project.Project) -> None:
        """
        初始化编译器虚拟机。
        :param proj: 项目对象，包含输出路径和根路径等信息。
        """
        self._project: project.Project = proj
        self._output_path = proj.output_path
        workspace = proj.root_path
        self._workspace: str = workspace
        self._exec_mode_stack: list[_ExecMode] = [_ExecMode.SQ]
        self._scope_count_stack: list[_ScopeCount] = [_ScopeCount.HOLD]
        self._src_info: SourceInfo = VIOLA_INIT
        self._symbol_table: symbol.SymbolTable = symbol.SymbolTable()
        self._var_state_table: symbol.VariableStateTable = symbol.VariableStateTable()
        self._stack: list[CompilingItem] = []
        self._current_class: Optional[symbol.ClassName] = None
        self._logger: Logger = Logger(f"Compiler VM[0]")
        # noinspection PyTypeChecker
        self._DEF_MAKER_DICT: dict[str, Callable[[list[str]], definition.Definition]] = {
            "CONST": lambda cmd: self.__make(
                definition.ConstDef(self._src_info, self._symbol_table, self._symbol_table.namespace)),
            "SQ": self.__make_def_sq,
            "CONSTRUCTOR": self.__make_def_constructor,
            "DESTRUCTOR": self.__make_def_destructor,
            "FN": self.__make_def_fn,
            "C_PART_SQ": lambda cmd: self.__make(
                definition.CPartSqDef(self._src_info, self._symbol_table, self._symbol_table.namespace,
                                      self._var_state_table.assigned_variables, cmd[0], " ".join(cmd[1:]).split("%"))),
            "CLASS": lambda cmd: self.__make_class(cmd),
            "CPART_IMPORT": lambda cmd: self.__make(definition.CPartImportDef(self._src_info, self._symbol_table, cmd[0])),
            "FROM_IMPORT": lambda cmd: self.__make(
                definition.FromImportDef(self._src_info, self._symbol_table, workspace, cmd[0], cmd[1:])),
            "IMPORT": lambda cmd: self.__make(project.ImportDef(self._src_info, self._symbol_table, workspace, cmd[0])),
            "ENUM": lambda cmd: self.__make(
                definition.EnumDef(self._src_info, self._symbol_table, self._symbol_table.namespace, cmd[0]))
        }
        # noinspection PyTypeChecker
        self._EXPR_MAKER_DICT: dict[str, Callable[[list[str]], expression.Expression]] = {
            "C": lambda cmd: self.__make(expression.CExpr(self._src_info, self._symbol_table)),
            "UNPACK": lambda cmd: self.__make(expression.UnpackExpr(self._src_info, self._symbol_table)),
            "VARIABLE_REF": lambda cmd: self.__make_variable_ref(cmd),
            "STRING_LITERAL": lambda cmd: self.__make(
                expression.StringLiteral(self._src_info, self._symbol_table, " ".join(cmd))),
            "BOOL_LITERAL": lambda cmd: self.__make(expression.BoolLiteral(self._src_info, self._symbol_table, cmd[0])),
            "INTEGER_LITERAL": lambda cmd: self.__make(
                expression.IntegerLiteral(self._src_info, self._symbol_table, cmd[0], cmd[1])),
            "FLOAT_LITERAL": lambda cmd: self.__make(
                expression.FloatLiteral(self._src_info, self._symbol_table, cmd[0])),
            "SLICE_REF": lambda cmd: self.__make(expression.SliceRef(self._src_info, self._symbol_table)),
            "ARRAY_REF": lambda cmd: self.__make(expression.ArrayRef(self._src_info, self._symbol_table)),
            "TUPLE_REF": lambda cmd: self.__make(expression.TupleRef(self._src_info, self._symbol_table)),
            "AUTO_TYPE_REF": lambda cmd: self.__make(expression.AutoTypeRef(self._src_info, self._symbol_table)),
            "FUNCTION_TYPE_REF": lambda cmd: self.__make(expression.FunctionTypeRef(self._src_info, self._symbol_table)),
            "TYPE_REF": lambda cmd: self.__make(
                expression.TypeRef.from_name(self._src_info, self._symbol_table, " ".join(cmd))),
            "CLASS_REF": lambda cmd: self.__make(
                expression.ClassRef.from_name(self._src_info, self._symbol_table, " ".join(cmd))),
            "ATTR_OP": lambda cmd: self.__make(expression.AttrOp(self._src_info, self._symbol_table)),
            "CALL_OP": lambda cmd: self.__make(expression.CallOp(self._src_info, self._symbol_table)),
            "ADD_OP": lambda cmd: self.__make(expression.AddOp(self._src_info, self._symbol_table)),
            "SUB_OP": lambda cmd: self.__make(expression.SubOp(self._src_info, self._symbol_table)),
            "MUL_OP": lambda cmd: self.__make(expression.MulOp(self._src_info, self._symbol_table)),
            "DIV_OP": lambda cmd: self.__make(expression.DivOp(self._src_info, self._symbol_table)),
            "MOD_OP": lambda cmd: self.__make(expression.ModOp(self._src_info, self._symbol_table)),
            "MATMUL_OP": lambda cmd: self.__make(expression.MatMulOp(self._src_info, self._symbol_table)),
            "POW_OP": lambda cmd: self.__make(expression.PowOp(self._src_info, self._symbol_table)),
            "LSHIFT_OP": lambda cmd: self.__make(expression.LeftShiftOp(self._src_info, self._symbol_table)),
            "RSHIFT_OP": lambda cmd: self.__make(expression.RightShiftOp(self._src_info, self._symbol_table)),
            "BIT_AND_OP": lambda cmd: self.__make(expression.BitAndOp(self._src_info, self._symbol_table)),
            "BIT_OR_OP": lambda cmd: self.__make(expression.BitOrOp(self._src_info, self._symbol_table)),
            "BIT_XOR_OP": lambda cmd: self.__make(expression.BitXorOp(self._src_info, self._symbol_table)),
            "BIT_NOT_OP": lambda cmd: self.__make(expression.BitNotOp(self._src_info, self._symbol_table)),
            "EQ_OP": lambda cmd: self.__make(expression.EqualOp(self._src_info, self._symbol_table)),
            "NEQ_OP": lambda cmd: self.__make(expression.NotEqualOp(self._src_info, self._symbol_table)),
            "LT_OP": lambda cmd: self.__make(expression.LessThanOp(self._src_info, self._symbol_table)),
            "LE_OP": lambda cmd: self.__make(expression.LessThanOrEqualOp(self._src_info, self._symbol_table)),
            "GT_OP": lambda cmd: self.__make(expression.GreaterThanOp(self._src_info, self._symbol_table)),
            "GE_OP": lambda cmd: self.__make(expression.GreaterThanOrEqualOp(self._src_info, self._symbol_table)),
            "NOT_OP": lambda cmd: self.__make(expression.LogicalNotOp(self._src_info, self._symbol_table)),
            "AND_OP": lambda cmd: self.__make(expression.LogicalAndOp(self._src_info, self._symbol_table)),
            "OR_OP": lambda cmd: self.__make(expression.LogicalOrOp(self._src_info, self._symbol_table)),
            "POSITIVE_OP": lambda cmd: self.__make(expression.PositiveOp(self._src_info, self._symbol_table)),
            "NEGATIVE_OP": lambda cmd: self.__make(expression.NegativeOp(self._src_info, self._symbol_table)),
            "ITEM_OP": lambda cmd: self.__make(expression.ItemOp(self._src_info, self._symbol_table)),
            "BRACKETS_OP": lambda cmd: self.__make(expression.BracketsOp(self._src_info, self._symbol_table)),
            "COND_OP": lambda cmd: self.__make(expression.ConditionalOp(self._src_info, self._symbol_table)),
            "UPDATE": lambda cmd: self.__make(expression.UpdateExpr(self._src_info, self._symbol_table)),
            "CAST_OP": lambda cmd: self.__make(
                statement.CastOp(self._src_info, self._symbol_table, self._var_state_table)),
            "CLOSURE": lambda cmd: self.__make(definition.Closure(self._src_info, self._symbol_table)),
            "GENERIC_CALL": lambda cmd: self.__make(definition.GenericCall(self._src_info, self._symbol_table)),
        }
        # noinspection PyTypeChecker
        self._STMT_MAKER_DICT: dict[str, Callable[[list[str]], statement.Statement]] = {
            "DECL": lambda cmd: self.__make(
                statement.DeclStmt(self._src_info, self._symbol_table, self._var_state_table, self._symbol_table.namespace)),
            "ASSIGN": lambda cmd: self.__make(
                statement.AssignStmt(self._src_info, self._symbol_table, self._var_state_table, self._current_class)
            ),
            "OP": lambda cmd: self.__make(statement.OpStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "RETURN": lambda cmd: self.__make(
                statement.ReturnStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "THROW": lambda cmd: self.__make(
                statement.ThrowStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "C": lambda cmd: self.__make(statement.CStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "IF": lambda cmd: self.__make(statement.IfStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "ELIF": lambda cmd: self.__make(
                statement.ElifStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "ELSE": lambda cmd: self.__make(
                statement.ElseStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "TRY": lambda cmd: self.__make(
                statement.TryStmt(self._src_info, self._symbol_table, self._var_state_table)
            ),
            "CATCH": lambda cmd: self.__make_catch_stmt(),
            "FINALLY": lambda cmd: self.__make(
                statement.FinallyStmt(self._src_info, self._symbol_table, self._var_state_table)),
            "TYPE_DEF": lambda cmd: self.__make(
                statement.TypeDefStmt(self._src_info, self._symbol_table, cmd[0], self._var_state_table)),
            "BLOCK": lambda cmd: self.__make_stmt_block()
        }
        self._CALLER_DICT: dict[str, Callable[[list[str]], None]] = {
            "ADD_ARG": lambda cmd: self.__call_add_arg(cmd),
            "ADD_DEF": lambda cmd: self.__call_add_def(),
            "ADD_ENUM": lambda cmd: self.__call_add_enum(cmd),
            "ADD_ITEM": lambda cmd: self.__call_add_item(cmd),
            "ADD_METHOD": lambda cmd: self.__call_add_method(),
            "ADD_PROP": lambda cmd: self.__call_add_property(cmd),
            "ADD_STATIC_PROP": lambda cmd: self.__call_add_static_prop(cmd),
            "ADD_STMT": lambda cmd: self.__call_add_stmt(),
            "ADD_TEXT": lambda cmd: self.__call_add_text(cmd),
            "ADD_TYPE": lambda cmd: self.__call_add_type(),
            "ADD_TYPE_ARG": lambda cmd: self.__call_add_type_arg(),
            "ADD_VALUE": lambda cmd: self.__call_add_value(),
            "ADD_VAR": lambda cmd: self.__call_add_var(cmd),
            "ADD_VAR_NAME": lambda cmd: self.__call_add_var_name(cmd[0]),
            "AS_ASYNC": lambda cmd: self.__call_as_async(),
            "FINISH": lambda cmd: self.__call_finish(),
            "FINISH_GENERIC": lambda cmd: self.__call_finish_generic(),
            "SET_ATTR": lambda cmd: self.__call_set_attr(cmd),
            "SET_ARG_TYPES": lambda cmd: self.__call_set_arg_types(),
            "SET_CALLER": lambda cmd: self.__call_set_caller(),
            "SET_COND_EXPR": lambda cmd: self.__call_set_cond_expr(),
            "SET_DEF": lambda cmd: self.__call_set_def(),
            "SET_DEFAULT_PARAM": lambda cmd: self.__call_set_default_param(cmd),
            "SET_END": lambda cmd: self.__call_set_end(),
            "SET_EXCEPT_DECL": lambda cmd: self.__call_set_except_decl(cmd),
            "SET_EXPR": lambda cmd: self.__call_set_expr(),
            "SET_EXPR_COND": lambda cmd: self.__call_set_expr_cond(),
            "SET_EXPR_ELSE": lambda cmd: self.__call_set_expr_else(),
            "SET_EXPR_LEFT": lambda cmd: self.__call_set_expr_left(),
            "SET_EXPR_RIGHT": lambda cmd: self.__call_set_expr_right(),
            "SET_EXPR_THEN": lambda cmd: self.__call_set_expr_then(),
            "SET_FUNC": lambda cmd: self.__call_set_func(),
            "SET_GENERIC_EXPR": lambda cmd: self.__call_set_generic_expr(),
            "SET_RETURN_TYPES": lambda cmd: self.__call_set_return_types(),
            "SET_SRC_EXPR": lambda cmd: self.__call_set_src_expr(),
            "SET_START": lambda cmd: self.__call_set_start(),
            "SET_STEP": lambda cmd: self.__call_set_step(),
            "SET_STMT": lambda cmd: self.__call_set_stmt(),
            "SET_TYPE": lambda cmd: self.__call_set_type(),
            "SET_VARS": lambda cmd: self.__call_set_vars(cmd),
            "SET_VAR_VALUE": lambda cmd: self.__call_set_var_value(),
        }

    def compile(self, src_path: str, thread_index: int = 0) -> TaskResult:
        """
        编译指定的源文件。
        :param src_path: 源文件的路径。
        :param thread_index: 线程索引，用于日志标识。
        :return: 包含编译结果的任务结果对象。
        """
        self._logger = Logger(f"Compiler VM[{thread_index}]")
        self._src_info = SourceInfo(src_path)
        src_path = os.path.abspath(src_path)
        src_relpath = os.path.relpath(src_path, self._workspace)
        cache_path = os.path.join(self._workspace, CACHE_DIR, src_relpath)
        output_path = os.path.join(self._output_path, src_relpath)
        if not os.path.exists(src_path):
            self._logger.error(f"Source file not found: {src_path}")
            return TaskResult(TaskResultState.FAILURE)
        self._logger.debug(f"Found compiling target: {src_path}")
        if CompilerVM._check_skip(src_path, output_path):
            self._logger.debug(f"Skipped: {src_path}")
            return TaskResult(TaskResultState.SUCCESS, [["violac", "add-make", output_path]])
        if not os.path.exists(cache_path + SYMBOL_TABLE_POSTFIX) or not os.path.exists(cache_path + COMMAND_POSTFIX):
            self._logger.debug(f"Required: {cache_path + SYMBOL_TABLE_POSTFIX}")
            self._logger.debug(f"Required: {cache_path + COMMAND_POSTFIX}")
            return TaskResult(TaskResultState.DELAYED, [["violac", "parse", src_path]])
        self._symbol_table = symbol.SymbolTable.read_from(cache_path + SYMBOL_TABLE_POSTFIX)
        self._var_state_table = symbol.VariableStateTable(src_path, self._workspace)
        self._stack.clear()
        self._stack.append(project.SourceFile(
            self._src_info, self._symbol_table, self._var_state_table, src_path, output_path,
            self._symbol_table.namespace
        ))
        with open(cache_path + COMMAND_POSTFIX, "r", encoding=CompilerVM._ENCODING) as f:
            commands = f.read()
        try:
            self.exec(commands)
            src_file = self.get()
        except CompilerException:
            self._logger.error(format_exc())
            return TaskResult(TaskResultState.FAILURE)
        except Exception as e:
            self._logger.error(format_exc())
            raise e
        self._project.add_source_file(src_file)
        self._logger.info(f"Successfully compiled: {src_path}")
        return TaskResult(TaskResultState.SUCCESS, [["violac", "add-make", output_path]])

    def exec(self, cmd: str) -> None:
        """逐行执行编译命令字符串。"""
        lines: list[str] = cmd.split("\n")
        for i, line in enumerate(lines):
            self._exec_line(line)

    def get(self) -> project.SourceFile:
        """获取栈底的源文件对象，完成写入并返回。"""
        # noinspection PyTypeChecker
        src_file: project.SourceFile = self._stack[0]
        src_file.finish()
        src_file.write()
        return src_file

    def _call(self, cmd: list[str]) -> None:
        """根据命令调用对应的处理器函数。"""
        self._CALLER_DICT[cmd[1]](cmd[2:])

    @staticmethod
    def _check_skip(src_path: str, dst_path: str) -> bool:
        """检查是否需要跳过编译（若目标头文件比源文件更新则跳过）。"""
        header_output_exists = os.path.exists(dst_path + ".h")
        if header_output_exists:
            return os.path.getmtime(dst_path + ".h") >= os.path.getmtime(src_path)
        return False

    def _exec_line(self, cmd: str) -> None:
        """解析并执行单行编译命令。"""
        cmd = cmd.strip()
        if not cmd:
            return
        cmd_parts: list[str] = cmd.split(" ")
        match cmd_parts[0]:
            case "CALL":
                self._call(cmd_parts)
            case "MAKE":
                self._make(cmd_parts)
            case "SET_INFO":
                self._set_info(cmd_parts)
            case _:
                raise InternalCompilerException(f"{cmd_parts[0]} is not a valid command", self._src_info)

    def _make(self, cmd: list[str]) -> None:
        """创建编译项（定义、表达式或语句）并压入栈中。"""
        match cmd[1]:
            case "DEF":
                result: CompilingItem = self._DEF_MAKER_DICT[cmd[2]](cmd[3:])
                self._stack.append(result)
            case "EXPR":
                result = self._EXPR_MAKER_DICT[cmd[2]](cmd[3:])
                self._stack.append(result)
            case "STMT":
                result = self._STMT_MAKER_DICT[cmd[2]](cmd[3:])
                self._stack.append(result)
            case _:
                raise InternalCompilerException(f"{cmd[1]} is not a valid command", self._src_info)
        self._stack[-1].bind_parent(self._stack[-2])

    def _set_info(self, cmd: list[str]) -> None:
        """设置当前源代码位置信息。"""
        loc: tuple[int, int, int, int] = int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4])
        src_text: str = " ".join(cmd[5:])
        self._src_info.set_loc(*loc)
        self._src_info.set_text(src_text)
        self._symbol_table.set_src_info(self._src_info)

    def __call_add_arg(self, cmd: list[str]) -> None:
        """为调用操作添加参数。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.CallOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_arg(self._stack[-1], cmd[0] if len(cmd) == 1 else None)
        self.__pop()

    def __call_add_def(self) -> None:
        """将定义添加到源文件中。"""
        self.__check_type(self._stack[-1], [definition.Definition])
        self.__check_type(self._stack[-2], [project.SourceFile])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_def(self._stack[-1])
        self.__pop()

    def __call_add_enum(self, cmd: list[str]) -> None:
        """为枚举定义添加枚举值。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [definition.EnumDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_enum(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_item(self, cmd: list[str]) -> None:
        """向更新表达式中添加元素。"""
        target_index: int = int(cmd[0])
        value_expr = self._stack[-1]
        self.__check_type(value_expr, [expression.Expression])
        if target_index < 0:
            raise InternalCompilerException("Invalid index", self._src_info)
        selected_expr = self._stack[-1 - target_index:-1]
        for expr in selected_expr:
            self.__check_type(expr, [expression.Expression])
        self.__check_type(self._stack[-2 - target_index], [expression.UpdateExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-2 - target_index].add_item(selected_expr, value_expr)
        self.__pop()
        for _ in selected_expr:
            self.__pop()

    def __call_add_method(self) -> None:
        """向类的定义中添加方法。"""
        self.__check_type(self._stack[-1], [definition.SqDef])
        self.__check_type(self._stack[-2], [definition.ClassDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_method(self._stack[-1])
        self.__pop()

    def __call_add_property(self, cmd: list[str]) -> None:
        """为更新表达式添加属性。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.UpdateExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_property(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_static_prop(self, cmd: list[str]) -> None:
        """为类的定义中添加静态属性。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [definition.ClassDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_static_prop(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_stmt(self) -> None:
        """向语句块或函数定义中添加语句。"""
        self.__check_type(self._stack[-1], [statement.Statement])
        self.__check_type(self._stack[-2], [definition.SqDef, statement.BlockStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_stmt(self._stack[-1])
        self.__pop()

    def __call_add_text(self, cmd: list[str]) -> None:
        """向 C 语句或表达式中添加文本。"""
        self.__check_type(self._stack[-1], [statement.CStmt, expression.CExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-1].add_text(" ".join(cmd))

    def __call_add_type(self) -> None:
        """向元组类型引用中添加类型。"""
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [expression.TupleTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_type(self._stack[-1])
        self.__pop()

    def __call_add_type_arg(self) -> None:
        """为泛型调用添加类型参数。"""
        self.__check_type(self._stack[-2], [definition.GenericCall])
        self.__check_type(self._stack[-1], [expression.TypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_type_arg(self._stack[-1])
        self.__pop()

    def __call_add_value(self) -> None:
        """向数组或元组引用中添加值。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ArrayRef, expression.TupleRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_value(self._stack[-1])
        self.__pop()

    def __call_add_var(self, cmd: list[str]) -> None:
        """为声明语句添加变量。"""
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.DeclStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_var(cmd[0], self._stack[-1], self.__scope_level == 0)
        self.__pop()

    def __call_add_var_name(self, cmd: str) -> None:
        """为赋值语句设置变量名列表。"""
        self.__check_type(self._stack[-1], [statement.AssignStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-1].add_var_name(cmd)

    def __call_as_async(self) -> None:
        """将栈顶语句转换为异步版本。"""
        self.__check_type(self._stack[-1], [statement.Statement])
        # noinspection PyUnresolvedReferences
        self._stack[-1] = self._stack[-1].as_async()

    def __call_finish(self) -> None:
        """完成栈顶编译项的构建。"""
        self.__check_type(self._stack[-1], [
            definition.SqDef, definition.ClassDef, definition.EnumDef, statement.DeclStmt, statement.AssignStmt,
            statement.TryStmt, statement.BlockStmt, statement.CStmt, expression.ArrayRef, expression.TupleRef,
            expression.TupleTypeRef, expression.UpdateExpr
        ])
        # noinspection PyUnresolvedReferences
        self._stack[-1].finish()
        # if isinstance(self._stack[-1], statement.BlockStmt):
        #     blk = self._stack[-1]
        #     self.__pop()
        #     if len(self._stack) >= 2 and isinstance(self._stack[-1], definition.SqDef):
        #         self._stack[-1].add_stmt(blk)

    def __call_finish_generic(self) -> None:
        """完成泛型调用，生成实例化后的表达式。"""
        self.__check_type(self._stack[-1], [definition.GenericCall])
        # noinspection PyUnresolvedReferences
        self._stack[-1].finish()
        # noinspection PyUnresolvedReferences
        instance = self._stack[-1].instance
        self.__pop()
        self.__make(instance)

    def __call_set_attr(self, cmd: list[str]) -> None:
        """设置属性表达式的属性名。"""
        self.__check_type(self._stack[-1], [expression.AttrOp])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_attr(cmd[0])

    def __call_set_arg_types(self) -> None:
        """为函数类型引用设置参数类型。"""
        self.__check_type(self._stack[-1], [expression.TupleTypeRef])
        self.__check_type(self._stack[-2], [expression.FunctionTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_arg_types(self._stack[-1])
        self.__pop()

    def __call_set_caller(self) -> None:
        """设置属性表达式的调用者。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.AttrOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_caller(self._stack[-1])
        self.__pop()

    def __call_set_cond_expr(self) -> None:
        """设置条件语句的条件表达式。"""
        self.__check_type(self._stack[-1], [statement.CondStmt])
        self.__check_type(self._stack[-2], [expression.Expression])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_cond_expr(self._stack[-2])
        self.__pop()

    def __call_set_def(self) -> None:
        """设置闭包中的函数定义。"""
        self.__check_type(self._stack[-1], [definition.SqDef])
        self.__check_type(self._stack[-2], [definition.Closure])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_def(self._stack[-1])
        self.__pop()

    def __call_set_default_param(self, cmd: list[str]) -> None:
        """为函数定义设置默认参数。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [definition.SqDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_default_param(cmd[0], self._stack[-1])
        self.__pop()

    def __call_set_end(self) -> None:
        """设置切片引用的结束位置。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_end(self._stack[-1])
        self.__pop()

    def __call_set_except_decl(self, cmd: list[str]) -> None:
        """设置 catch 语句的异常声明。"""
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.CatchStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_except_decl(symbol.LocalVariableName(self._src_info, cmd[0], self._stack[-1].return_type))
        self.__pop()

    def __call_set_expr(self) -> None:
        """设置运算符语句或转换操作的表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [
            statement.OpStmt, statement.ThrowStmt, statement.CastOp, expression.UnaryOperator, expression.UnpackExpr
        ])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr(self._stack[-1])
        self.__pop()

    def __call_set_expr_cond(self) -> None:
        """设置条件运算符的条件表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp, statement.CondStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_cond(self._stack[-1])
        self.__pop()

    def __call_set_expr_else(self) -> None:
        """设置条件运算符的 else 分支表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_else(self._stack[-1])
        self.__pop()

    def __call_set_expr_left(self) -> None:
        """设置双目运算符的左操作数。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.BinaryOperator, expression.ItemOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_left(self._stack[-1])
        self.__pop()

    def __call_set_expr_right(self) -> None:
        """设置双目运算符的右操作数。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.BinaryOperator])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_right(self._stack[-1])
        self.__pop()

    def __call_set_expr_then(self) -> None:
        """设置条件运算符的 then 分支表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_then(self._stack[-1])
        self.__pop()

    def __call_set_func(self) -> None:
        """设置调用操作的函数表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.CallOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_func(self._stack[-1])
        self.__pop()

    def __call_set_generic_expr(self) -> None:
        """设置泛型调用的泛型表达式。"""
        self.__check_type(self._stack[-1], [expression.VariableRef, expression.AttrOp, expression.ClassRef, expression.TypeRef])
        self.__check_type(self._stack[-2], [definition.GenericCall])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_generic_expr(self._stack[-1])
        self.__pop()

    def __call_set_return_types(self) -> None:
        """为函数类型引用设置返回值类型。"""
        self.__check_type(self._stack[-1], [expression.TupleTypeRef])
        self.__check_type(self._stack[-2], [expression.FunctionTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_return_types(self._stack[-1])
        self.__pop()

    def __call_set_src_expr(self) -> None:
        """设置对象更新的源表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.UpdateExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_src_expr(self._stack[-1])
        self.__pop()

    def __call_set_start(self) -> None:
        """设置切片引用的起始位置。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_start(self._stack[-1])
        self.__pop()

    def __call_set_step(self) -> None:
        """设置切片引用的步长。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_step(self._stack[-1])
        self.__pop()

    def __call_set_stmt(self) -> None:
        """为常量定义或条件语句设置语句。"""
        self.__check_type(self._stack[-2], [
            definition.ConstDef, statement.CondStmt, statement.CatchStmt, statement.FinallyStmt, statement.TryStmt
        ])
        self.__check_type(self._stack[-1], [statement.Statement])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_stmt(self._stack[-1])
        self.__pop()

    def __call_set_type(self) -> None:
        """为类型转换或类型定义语句设置类型。"""
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.CastOp, statement.TypeDefStmt, expression.ArrayTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_type(self._stack[-1])

    def __call_set_vars(self, cmd: list[str]) -> None:
        """为声明语句设置变量列表（类型和名称交替）。"""
        self.__check_type(self._stack[-1], [statement.DeclStmt])
        var_type_names: list[str] = cmd[::2]
        var_names: list[str] = cmd[1::2]
        is_global: bool = self.__scope_level == 0
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_vars_by_name(var_names, var_type_names, is_global)

    def __call_set_var_value(self) -> None:
        """为声明或赋值语句设置变量的值表达式。"""
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [statement.DeclStmt, statement.AssignStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_var_value(self._stack[-1])
        self.__pop()

    def __check_type(self, obj: CompilingItem, types: list[type]) -> None:
        """检查编译项是否为指定的类型之一，若不是则抛出异常。"""
        for t in types:
            if isinstance(obj, t):
                return
        raise InternalCompilerException(
            f"{obj.__class__.__name__} is not in expected types: {', '.join(t.__name__ for t in types)}",
            self._src_info
        )

    def __make(self, obj: CompilingItem) -> CompilingItem:
        """将一个编译项压入栈管理机制中，更新执行模式和作用域计数。"""
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        self._scope_count_stack.append(_ScopeCount.HOLD)
        return obj

    def __make_catch_stmt(self) -> statement.CatchStmt:
        """创建异常处理语句并添加新的作用域。"""
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        result = statement.CatchStmt(self._src_info, self._symbol_table, self._var_state_table)
        self._current_catch = result
        return result

    def __make_class(self, cmd: list[str]) -> definition.ClassDef:
        """创建类的定义并添加新的作用域。"""
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        result = definition.ClassDef(self._src_info, self._symbol_table, self._symbol_table.namespace, cmd[0], self._var_state_table)
        self._current_class = result.decl
        return result

    def __make_def_constructor(self, cmd: list[str]) -> definition.ConstructorDef:
        """创建构造函数的定义并添加新的作用域。"""
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        construct_def: definition.ConstructorDef = definition.ConstructorDef(
            self._src_info, self._symbol_table, self._var_state_table, self._symbol_table.namespace, cmd[0],
            cmd[1].split("%") if len(cmd) > 1 else []
        )
        return construct_def

    def __make_def_destructor(self, cmd: list[str]) -> definition.DestructorDef:
        """创建析构函数的定义并添加新的作用域。"""
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        destructor_def: definition.DestructorDef = definition.DestructorDef(
            self._src_info, self._symbol_table, self._var_state_table, self._symbol_table.namespace, cmd[0]
        )
        return destructor_def

    def __make_def_fn(self, cmd: list[str]) -> definition.FnDef:
        """创建函数（fn）的定义并添加新的作用域。"""
        self._exec_mode_stack.append(_ExecMode.FN)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        fn_def: definition.FnDef = definition.FnDef(
            self._src_info, self._symbol_table, self._var_state_table, self._symbol_table.namespace, cmd[0],
            cmd[1].split("%") if len(cmd) > 1 else []
        )
        return fn_def

    def __make_def_sq(self, cmd: list[str]) -> definition.SqDef:
        """创建函数（sq，语句函数）的定义并添加新的作用域。"""
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        sq_def: definition.SqDef = definition.SqDef(
            self._src_info, self._symbol_table, self._var_state_table, self._symbol_table.namespace, cmd[0],
            cmd[1].split("%") if len(cmd) > 1 else []
        )
        return sq_def

    def __make_stmt_block(self) -> statement.BlockStmt:
        """创建语句块（普通块或函数块）并添加新的作用域。"""
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        self._var_state_table.add_scope()
        if self._exec_mode_stack[-1] == _ExecMode.FN:
            return statement.FnBlockStmt(self._src_info, self._symbol_table, self._var_state_table)
        return statement.BlockStmt(self._src_info, self._symbol_table, self._var_state_table)

    def __make_variable_ref(self, cmd: list[str]) -> expression.Expression:
        """创建变量引用表达式，根据作用域级别决定是全局变量还是局部变量。"""
        var_type_name = " ".join(cmd[:-1])
        # noinspection PyTypeChecker
        # noinspection PyUnresolvedReferences
        if var_type_name != "auto":
            var_type = self._symbol_table[var_type_name, None]
        else:
            var_type = self._symbol_table[cmd[-1], None]
        var_name: str = cmd[-1]
        if (var_name, None) in self._symbol_table:
            var = self._symbol_table[var_name, None]
            # noinspection PyTypeChecker
            if isinstance(var, symbol.VariableName):
                expr = expression.VariableRef(self._src_info, self._symbol_table, var)
            elif isinstance(var, symbol.ClassName):
                expr = expression.ClassRef(self._src_info, self._symbol_table, var)
            else:
                raise InternalCompilerException(
                    f"{var_name} is not a variable name or a class name",
                    self._src_info
                )
            self.__make(expr)
            return expr
        if self.__scope_level == 0:
            var: symbol.VariableName = symbol.GlobalVariableName(self._src_info, self._symbol_table.namespace, var_name, var_type)
        else:
            var = symbol.LocalVariableName(self._src_info, var_name, var_type)
        expr: expression.VariableRef = expression.VariableRef(self._src_info, self._symbol_table, var)
        self.__make(expr)
        return expr

    def __pop(self) -> None:
        """从编译栈中弹出栈顶元素，恢复执行模式和作用域状态。"""
        self._stack.pop()
        self._exec_mode_stack.pop()
        scope = self._scope_count_stack.pop()
        if scope == _ScopeCount.INC:
            self._symbol_table.clear_temporaries()
            self._var_state_table.pop_scope()
        if len(self._scope_count_stack) == 1:
            self._current_class = None

    @property
    def __scope_level(self) -> int:
        """获取当前作用域级别。"""
        return sum(map(lambda x: x.value, self._scope_count_stack))
        
