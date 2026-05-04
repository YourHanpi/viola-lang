# -*- coding: utf-8 -*-
from backend.compiling_item import CompilingItem
import backend.definition as definition
import backend.expression as expression
import backend.project as project
import backend.statement as statement
import backend.symbol as symbol
import utils.compiler_params as compiler_params
from utils import SourceInfo, InternalCompilerException

from enum import Enum
import os
from typing import Callable, Optional


class _ExecMode(Enum):
    SQ = 0
    FN = 1


class _ScopeCount(Enum):
    HOLD = 0
    INC = 1


class CompilerVM:

    def __init__(self, src_path: str, workspace: str, compiler_option_path: str) -> None:
        compiler_params.COMPILER_PARAMS = compiler_params.CompilerParams(compiler_option_path)
        src_path = os.path.abspath(src_path)
        workspace = os.path.abspath(workspace)
        self._exec_mode_stack: list[_ExecMode] = [_ExecMode.SQ]
        self._scope_count_stack: list[_ScopeCount] = [_ScopeCount.HOLD]
        self._src_info: SourceInfo = SourceInfo(src_path)
        self._symbol_table: symbol.SymbolTable = symbol.SymbolTable.read_from(src_path + ".vlasymtab")
        expression.SYMBOL_TABLE = self._symbol_table
        self._var_state_table: symbol.VariableStateTable = symbol.VariableStateTable(src_path, workspace)
        statement.VariableStateTable = self._var_state_table
        self._stack: list[CompilingItem] = [project.SourceFile(self._src_info, src_path, self._symbol_table.namespace)]
        self._current_class: Optional[symbol.ClassName] = None
        # noinspection PyTypeChecker
        self._DEF_MAKER_DICT: dict[str, Callable[[list[str]], definition.Definition]] = {
            "CONST": lambda cmd: self.__make(definition.ConstDef(self._src_info, self._symbol_table.namespace)),
            "SQ": self.__make_def_sq,
            "CONSTRUCTOR": self.__make_def_constructor,
            "DESTRUCTOR": self.__make_def_destructor,
            "FN": self.__make_def_fn,
            "C_PART_SQ": lambda cmd: self.__make(definition.CPartSqDef(self._src_info, self._symbol_table.namespace,
                                                                       self._var_state_table.assigned_variables, cmd[0],
                                                                       " ".join(cmd[1:]).split("%"))),
            "CLASS": lambda cmd: self.__make_class(cmd),
            "FROM_IMPORT": lambda cmd: self.__make(definition.FromImportDef(self._src_info, workspace, cmd[0], cmd[1:])),
            "IMPORT": lambda cmd: self.__make(project.ImportDef(self._src_info, workspace, cmd[0])),
            "ENUM": lambda cmd: self.__make(definition.EnumDef(self._src_info, self._symbol_table.namespace, cmd[0]))
        }
        # noinspection PyTypeChecker
        self._EXPR_MAKER_DICT: dict[str, Callable[[list[str]], expression.Expression]] = {
            "C": lambda cmd: self.__make(expression.CExpr(self._src_info)),
            "UNPACK": lambda cmd: self.__make(expression.UnpackExpr(self._src_info)),
            "VARIABLE_REF": lambda cmd: self.__make_variable_ref(cmd),
            "STRING_LITERAL": lambda cmd: self.__make(expression.StringLiteral(self._src_info, " ".join(cmd))),
            "BOOL_LITERAL": lambda cmd: self.__make(expression.BoolLiteral(self._src_info, cmd[0])),
            "INTEGER_LITERAL": lambda cmd: self.__make(expression.IntegerLiteral(self._src_info, cmd[0], cmd[1])),
            "FLOAT_LITERAL": lambda cmd: self.__make(expression.FloatLiteral(self._src_info, cmd[0])),
            "SLICE_REF": lambda cmd: self.__make(expression.SliceRef(self._src_info)),
            "ARRAY_REF": lambda cmd: self.__make(expression.ArrayRef(self._src_info)),
            "TUPLE_REF": lambda cmd: self.__make(expression.TupleRef(self._src_info)),
            "AUTO_TYPE_REF": lambda cmd: self.__make(expression.AutoTypeRef(self._src_info)),
            "TYPE_REF": lambda cmd: self.__make(expression.TypeRef.from_name(self._src_info, " ".join(cmd))),
            "CLASS_REF": lambda cmd: self.__make(expression.ClassRef(self._src_info, " ".join(cmd))),
            "ATTR_OP": lambda cmd: self.__make(expression.AttrOp(self._src_info)),
            "CALL_OP": lambda cmd: self.__make(expression.CallOp(self._src_info)),
            "ADD_OP": lambda cmd: self.__make(expression.AddOp(self._src_info)),
            "SUB_OP": lambda cmd: self.__make(expression.SubOp(self._src_info)),
            "MUL_OP": lambda cmd: self.__make(expression.MulOp(self._src_info)),
            "DIV_OP": lambda cmd: self.__make(expression.DivOp(self._src_info)),
            "MOD_OP": lambda cmd: self.__make(expression.ModOp(self._src_info)),
            "MATMUL_OP": lambda cmd: self.__make(expression.MatMulOp(self._src_info)),
            "POW_OP": lambda cmd: self.__make(expression.PowOp(self._src_info)),
            "LSHIFT_OP": lambda cmd: self.__make(expression.LeftShiftOp(self._src_info)),
            "RSHIFT_OP": lambda cmd: self.__make(expression.RightShiftOp(self._src_info)),
            "BIT_AND_OP": lambda cmd: self.__make(expression.BitAndOp(self._src_info)),
            "BIT_OR_OP": lambda cmd: self.__make(expression.BitOrOp(self._src_info)),
            "BIT_XOR_OP": lambda cmd: self.__make(expression.BitXorOp(self._src_info)),
            "BIT_NOT_OP": lambda cmd: self.__make(expression.BitNotOp(self._src_info)),
            "EQ_OP": lambda cmd: self.__make(expression.EqualOp(self._src_info)),
            "NEQ_OP": lambda cmd: self.__make(expression.NotEqualOp(self._src_info)),
            "LT_OP": lambda cmd: self.__make(expression.LessThanOp(self._src_info)),
            "LE_OP": lambda cmd: self.__make(expression.LessThanOrEqualOp(self._src_info)),
            "GT_OP": lambda cmd: self.__make(expression.GreaterThanOp(self._src_info)),
            "GE_OP": lambda cmd: self.__make(expression.GreaterThanOrEqualOp(self._src_info)),
            "NOT_OP": lambda cmd: self.__make(expression.LogicalNotOp(self._src_info)),
            "AND_OP": lambda cmd: self.__make(expression.LogicalAndOp(self._src_info)),
            "OR_OP": lambda cmd: self.__make(expression.LogicalOrOp(self._src_info)),
            "POSITIVE_OP": lambda cmd: self.__make(expression.PositiveOp(self._src_info)),
            "NEGATIVE_OP": lambda cmd: self.__make(expression.NegativeOp(self._src_info)),
            "ITEM_OP": lambda cmd: self.__make(expression.ItemOp(self._src_info)),
            "BRACKETS_OP": lambda cmd: self.__make(expression.BracketsOp(self._src_info)),
            "COND_OP": lambda cmd: self.__make(expression.ConditionalOp(self._src_info)),
            "UPDATE": lambda cmd: self.__make(expression.UpdateExpr(self._src_info)),
            "CAST_OP": lambda cmd: self.__make(statement.CastOp(self._src_info)),
            "CLOSURE": lambda cmd: self.__make(definition.Closure(self._src_info)),
            "GENERIC_CALL": lambda cmd: self.__make(definition.GenericCall(self._src_info)),
        }
        # noinspection PyTypeChecker
        self._STMT_MAKER_DICT: dict[str, Callable[[list[str]], statement.Statement]] = {
            "DECL": lambda cmd: self.__make(statement.DeclStmt(self._src_info, self._symbol_table.namespace)),
            "ASSIGN": lambda cmd: self.__make(statement.AssignStmt(self._src_info)),
            "OP": lambda cmd: self.__make(statement.OpStmt(self._src_info)),
            "RETURN": lambda cmd: self.__make(statement.ReturnStmt(self._src_info)),
            "THROW": lambda cmd: self.__make(statement.ThrowStmt(self._src_info)),
            "C": lambda cmd: self.__make(statement.CStmt(self._src_info)),
            "IF": lambda cmd: self.__make(statement.IfStmt(self._src_info)),
            "ELIF": lambda cmd: self.__make(statement.ElifStmt(self._src_info)),
            "ELSE": lambda cmd: self.__make(statement.ElseStmt(self._src_info)),
            "TRY": lambda cmd: self.__make(statement.TryStmt(self._src_info)),
            "CATCH": lambda cmd: self.__make(statement.CatchStmt(self._src_info)),
            "FINALLY": lambda cmd: self.__make(statement.FinallyStmt(self._src_info)),
            "TYPE_DEF": lambda cmd: self.__make(statement.TypeDefStmt(self._src_info, cmd[0])),
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
            "ADD_TYPE_ARG": lambda cmd: self.__call_add_type_arg(cmd),
            "ADD_VALUE": lambda cmd: self.__call_add_value(),
            "ADD_VAR": lambda cmd: self.__call_add_var(cmd),
            "AS_ASYNC": lambda cmd: self.__call_as_async(),
            "FINISH": lambda cmd: self.__call_finish(),
            "SET_ATTR": lambda cmd: self.__call_set_attr(cmd),
            "SET_CALLER": lambda cmd: self.__call_set_caller(),
            "SET_COND_EXPR": lambda cmd: self.__call_set_cond_expr(),
            "SET_DEF": lambda cmd: self.__call_set_def(),
            "SET_END": lambda cmd: self.__call_set_end(),
            "SET_EXCEPT_DECL": lambda cmd: self.__call_set_except_decl(cmd),
            "SET_EXPR": lambda cmd: self.__call_set_expr(),
            "SET_EXPR_COND": lambda cmd: self.__call_set_expr_cond(),
            "SET_EXPR_ELSE": lambda cmd: self.__call_set_expr_else(),
            "SET_EXPR_LEFT": lambda cmd: self.__call_set_expr_left(),
            "SET_EXPR_RIGHT": lambda cmd: self.__call_set_expr_right(),
            "SET_EXPR_THEN": lambda cmd: self.__call_set_expr_then(),
            "SET_FUNC": lambda cmd: self.__call_set_func(),
            "SET_GENERIC_SYMBOL": lambda cmd: self.__call_set_generic_symbol(cmd),
            "SET_START": lambda cmd: self.__call_set_start(),
            "SET_STEP": lambda cmd: self.__call_set_step(),
            "SET_STMT": lambda cmd: self.__call_set_stmt(),
            "SET_TO_UNPACK": lambda cmd: self.__call_set_to_unpack(),
            "SET_TYPE": lambda cmd: self.__call_set_type(),
            "SET_VARS": lambda cmd: self.__call_set_vars(cmd),
            "SET_VAR_NAMES": lambda cmd: self.__call_add_var_name(cmd),
            "SET_VAR_VALUE": lambda cmd: self.__call_set_var_value(),
        }

    def exec(self, cmd: str) -> None:
        lines: list[str] = cmd.split("\n")
        for line in lines:
            self._exec_line(line)

    def get(self) -> project.SourceFile:
        # noinspection PyTypeChecker
        src_file: project.SourceFile = self._stack[0]
        src_file.finish()
        src_file.write()
        return src_file

    def _call(self, cmd: list[str]) -> None:
        self._CALLER_DICT[cmd[1]](cmd[2:])

    def _exec_line(self, cmd: str) -> None:
        cmd: list[str] = cmd.split(" ")
        match cmd[0]:
            case "CALL":
                self._call(cmd)
            case "MAKE":
                self._make(cmd)
            case "SET_INFO":
                self._set_info(cmd)
            case _:
                raise InternalCompilerException(f"{cmd[0]} is not a valid command", self._src_info)

    def _make(self, cmd: list[str]) -> None:
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
        loc: tuple[int, int, int, int] = int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4])
        src_text: str = " ".join(cmd[5:])
        self._src_info.set_loc(*loc)
        self._src_info.set_text(src_text)

    def __call_add_arg(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.CallOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_arg(self._stack[-1], cmd[0] if len(cmd) == 1 else None)
        self.__pop()

    def __call_add_def(self) -> None:
        self.__check_type(self._stack[-1], [definition.Definition])
        self.__check_type(self._stack[-2], [project.SourceFile])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_def(self._stack[-1])
        self.__pop()

    def __call_add_enum(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [definition.EnumDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_enum(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_item(self, cmd: list[str]) -> None:
        target_index: int = int(cmd[0])
        value_expr = self._stack[-1]
        self.__check_type(value_expr, [expression.Expression])
        if target_index < 0:
            raise InternalCompilerException("Invalid index", self._src_info)
        selected_expr = self._stack[-1 - target_index:-1]
        for expr in selected_expr:
            self.__check_type(expr, [expression.Expression])
        self.__check_type(selected_expr[-2 - target_index], [expression.UpdateExpr])
        # noinspection PyUnresolvedReferences
        selected_expr[-2 - target_index].add_item(selected_expr, value_expr)
        self.__pop()
        for _ in selected_expr:
            self.__pop()

    def __call_add_method(self) -> None:
        self.__check_type(self._stack[-1], [definition.SqDef])
        self.__check_type(self._stack[-2], [definition.ClassDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_method(self._stack[-1])
        self.__pop()

    def __call_add_property(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.UpdateExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_property(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_static_prop(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [definition.ClassDef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_static_prop(cmd[0], self._stack[-1])
        self.__pop()

    def __call_add_stmt(self) -> None:
        self.__check_type(self._stack[-1], [statement.Statement])
        self.__check_type(self._stack[-2], [definition.SqDef, statement.BlockStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_stmt(self._stack[-1])
        self.__pop()

    def __call_add_text(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [statement.CStmt, expression.CExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-1].add_text(" ".join(cmd))

    def __call_add_type(self) -> None:
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [expression.TupleTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_type(self._stack[-1])
        self.__pop()

    def __call_add_type_arg(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [definition.GenericCall])
        # noinspection PyTypeChecker
        t: symbol.TypeName = self._symbol_table[" ".join(cmd)]
        # noinspection PyUnresolvedReferences
        self._stack[-1].add_type_arg(t)

    def __call_add_value(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ArrayRef, expression.TupleRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_value(self._stack[-1])
        self.__pop()

    def __call_add_var(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.DeclStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].add_var(cmd[0], self._stack[-1], self.__scope_level == 0)
        self.__pop()

    def __call_add_var_name(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [statement.AssignStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_var_names(cmd)

    def __call_as_async(self) -> None:
        self.__check_type(self._stack[-1], [statement.Statement])
        # noinspection PyUnresolvedReferences
        self._stack[-1] = self._stack[-1].as_async()

    def __call_finish(self) -> None:
        self.__check_type(self._stack[-1], [
            definition.SqDef, definition.ClassDef, definition.GenericCall, definition.EnumDef, statement.DeclStmt,
            statement.AssignStmt, statement.TryStmt, statement.BlockStmt, expression.ArrayRef, expression.TupleRef,
            expression.TupleTypeRef, expression.UpdateExpr
        ])
        # noinspection PyUnresolvedReferences
        self._stack[-1].finish()

    def __call_set_attr(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.AttrOp])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_attr(cmd[0])

    def __call_set_caller(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.AttrOp])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_caller(self._stack[-2])
        self.__pop()

    def __call_set_cond_expr(self) -> None:
        self.__check_type(self._stack[-1], [statement.CondStmt])
        self.__check_type(self._stack[-2], [expression.Expression])
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_cond_expr(self._stack[-2])
        self.__pop()

    def __call_set_def(self) -> None:
        self.__check_type(self._stack[-1], [definition.SqDef])
        self.__check_type(self._stack[-2], [definition.Closure])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_def(self._stack[-1])
        self.__pop()

    def __call_set_end(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_end(self._stack[-1])
        self.__pop()

    def __call_set_except_decl(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.CatchStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_except_decl(symbol.TemporaryVariableName(self._src_info, cmd[0], self._stack[-1].return_type))
        self.__pop()

    def __call_set_expr(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [
            statement.OpStmt, statement.ThrowStmt, statement.CastOp, expression.UnaryOperator
        ])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr(self._stack[-1])
        self.__pop()

    def __call_set_expr_cond(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_cond(self._stack[-1])
        self.__pop()

    def __call_set_expr_else(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_else(self._stack[-1])
        self.__pop()

    def __call_set_expr_left(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.BinaryOperator, expression.ItemOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_left(self._stack[-1])
        self.__pop()

    def __call_set_expr_right(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.BinaryOperator])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_right(self._stack[-1])
        self.__pop()

    def __call_set_expr_then(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.ConditionalOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_expr_then(self._stack[-1])
        self.__pop()

    def __call_set_func(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.CallOp])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_func(self._stack[-1])
        self.__pop()

    def __call_set_generic_symbol(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [definition.GenericCall])
        # noinspection PyTypeChecker
        sym: symbol.ClassName | symbol.FunctionName | symbol.MethodName = self._symbol_table[cmd[0]]
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_generic_symbol(sym)

    def __call_set_start(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_start(self._stack[-1])
        self.__pop()

    def __call_set_step(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.SliceRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_step(self._stack[-1])
        self.__pop()

    def __call_set_stmt(self) -> None:
        self.__check_type(self._stack[-2], [
            definition.ConstDef, statement.CondStmt, statement.CatchStmt, statement.FinallyStmt
        ])
        self.__check_type(self._stack[-1], [statement.Statement])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_stmt(self._stack[-1])
        self.__pop()
        
    def __call_set_to_unpack(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [expression.UnpackExpr])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_to_unpack(self._stack[-1])
        self.__pop()

    def __call_set_type(self) -> None:
        self.__check_type(self._stack[-1], [expression.TypeRef])
        self.__check_type(self._stack[-2], [statement.CastOp, statement.TypeDefStmt, expression.ArrayTypeRef])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_type(self._stack[-1])

    def __call_set_vars(self, cmd: list[str]) -> None:
        self.__check_type(self._stack[-1], [statement.DeclStmt])
        var_type_names: list[str] = cmd[::2]
        var_names: list[str] = cmd[1::2]
        is_global: bool = self.__scope_level == 0
        # noinspection PyUnresolvedReferences
        self._stack[-1].set_vars_by_name(var_names, var_type_names, is_global)

    def __call_set_var_value(self) -> None:
        self.__check_type(self._stack[-1], [expression.Expression])
        self.__check_type(self._stack[-2], [statement.DeclStmt, statement.AssignStmt])
        # noinspection PyUnresolvedReferences
        self._stack[-2].set_var_value(self._stack[-1])
        self.__pop()

    def __check_type(self, obj: CompilingItem, types: list[type]) -> None:
        for t in types:
            if isinstance(obj, t):
                return
        raise InternalCompilerException(
            f"{obj.__class__.__name__} is not expected types: {', '.join(t.__name__ for t in types)}",
            self._src_info
        )

    def __make(self, obj: CompilingItem) -> CompilingItem:
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        self._scope_count_stack.append(_ScopeCount.HOLD)
        return obj

    def __make_class(self, cmd: list[str]) -> definition.ClassDef:
        result = definition.ClassDef(self._src_info, self._symbol_table.namespace, cmd[0], self._var_state_table.state)
        self._symbol_table.add_scope()
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._current_class = result.decl
        return result

    def __make_def_constructor(self, cmd: list[str]) -> definition.ConstructorDef:
        construct_def: definition.ConstructorDef = definition.ConstructorDef(
            self._src_info,
            self._symbol_table.namespace,
            self._var_state_table.assigned_variables,
            cmd[0], cmd[1:]
        )
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        return construct_def

    def __make_def_destructor(self, cmd: list[str]) -> definition.DestructorDef:
        destructor_def: definition.DestructorDef = definition.DestructorDef(self._src_info,
                                                                            self._symbol_table.namespace,
                                                                            self._var_state_table.assigned_variables,
                                                                            cmd[0])
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        return destructor_def

    def __make_def_fn(self, cmd: list[str]) -> definition.FnDef:
        fn_def: definition.FnDef = definition.FnDef(self._src_info, self._symbol_table.namespace,
                                                    self._var_state_table.assigned_variables, cmd[0], cmd[1:])
        self._exec_mode_stack.append(_ExecMode.FN)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        return fn_def

    def __make_def_sq(self, cmd: list[str]) -> definition.SqDef:
        sq_def: definition.SqDef = definition.SqDef(self._src_info, self._symbol_table.namespace,
                                                    self._var_state_table.assigned_variables, cmd[0], cmd[1:])
        self._exec_mode_stack.append(_ExecMode.SQ)
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        return sq_def

    def __make_stmt_block(self) -> statement.BlockStmt:
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        self._scope_count_stack.append(_ScopeCount.INC)
        self._symbol_table.add_scope()
        if self._exec_mode_stack[-1] == _ExecMode.FN:
            return statement.FnBlockStmt(self._src_info, self._var_state_table.state)
        else:
            return statement.BlockStmt(self._src_info, self._var_state_table.state)

    def __make_variable_ref(self, cmd: list[str]) -> expression.VariableRef:
        # noinspection PyTypeChecker
        # noinspection PyUnresolvedReferences
        var_type: symbol.TypeName = self._symbol_table[cmd[0]] if cmd[0] != "auto" else self._symbol_table[cmd[1]].type
        var_name: str = cmd[1]
        if self.__scope_level == 0:
            var: symbol.VariableName = symbol.GlobalVariableName(self._src_info, self._symbol_table.namespace, var_name, var_type)
        else:
            var = symbol.TemporaryVariableName(self._src_info, var_name, var_type)
        expr: expression.VariableRef = expression.VariableRef(self._src_info, var)
        self.__make(expr)
        return expr

    def __pop(self) -> None:
        self._stack.pop()
        self._exec_mode_stack.pop()
        scope = self._scope_count_stack.pop()
        if scope == _ScopeCount.INC:
            self._symbol_table.clear_temporaries()
        if len(self._scope_count_stack) == 1:
            self._current_class = None

    @property
    def __scope_level(self) -> int:
        return sum(map(lambda x: x.value, self._scope_count_stack))
        
