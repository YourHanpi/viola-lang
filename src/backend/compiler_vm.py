# -*- coding: utf-8 -*-
from backend.compiling_item import CompilingItem
import backend.definition as definition
import backend.expression as expression
import backend.statement as statement
import backend.symbol as symbol
from utils import SourceInfo, InternalCompilerException

from enum import Enum
from typing import Callable, Optional


class _ExecMode(Enum):
    SQ = 0
    FN = 1


class CompilerVM:

    def __init__(self, src_path: str, workspace: str) -> None:
        self._stack: list[CompilingItem] = []
        self._exec_mode_stack: list[_ExecMode] = []
        self._stack_size: int = 0
        self._src_info: SourceInfo = SourceInfo(src_path)
        self._symbol_table: symbol.SymbolTable = symbol.SymbolTable(src_path, workspace)
        self._symbol_table.read(src_path + ".vlasymtab")
        expression.SYMBOL_TABLE = self._symbol_table
        self._var_state_table: symbol.VariableStateTable = symbol.VariableStateTable(src_path, workspace)
        statement.VariableStateTable = self._var_state_table
        self._type_register: Optional[symbol.TypeName] = None
        self._DEF_MAKER_DICT: dict[str, Callable[[list[str]], definition.Definition]] = {
            "CONST": lambda cmd: self.__make(definition.ConstDef(self._src_info, self._symbol_table.namespace)),
            "SQ": self.__make_def_sq,
            "CONSTRUCTOR": self.__make_def_constructor,
            "DESTRUCTOR": self.__make_def_destructor,
            "FN": self.__make_def_fn,
            "C_PART_SQ": lambda cmd: self.__make(definition.CPartSqDef(self._src_info, self._symbol_table.namespace, self._var_state_table.assigned_variables, cmd[0], cmd[1:])),
            "CLASS": lambda cmd: self.__make(definition.ClassDef(self._src_info, self._symbol_table.namespace, cmd[0], self._var_state_table.state)),
            "IMPORT": lambda cmd: self.__make(definition.ImportDef(self._src_info, workspace, cmd[0], cmd[1])),
            "ENUM": lambda cmd: self.__make(definition.EnumDef(self._src_info, self._symbol_table.namespace, cmd[0]))
        }
        # noinspection PyTypeChecker
        self._EXPR_MAKER_DICT: dict[str, Callable[[list[str]], expression.Expression]] = {
            "UNPACK": lambda cmd: self.__make(expression.UnpackExpr(self._src_info)),
            "VARIABLE_REF": lambda cmd: self.__make(expression.VariableRef(self._src_info, cmd[0])),
            "STRING_LITERAL": lambda cmd: self.__make(expression.StringLiteral(self._src_info, ", ".join(cmd))),
            "BOOL_LITERAL": lambda cmd: self.__make(expression.BoolLiteral(self._src_info, cmd[0])),
            "INTEGER_LITERAL": lambda cmd: self.__make(expression.IntegerLiteral(self._src_info, cmd[0])),
            "FLOAT_LITERAL": lambda cmd: self.__make(expression.FloatLiteral(self._src_info, cmd[0])),
            "ARRAY_REF": lambda cmd: self.__make(expression.ArrayRef(self._src_info, self._type_register)),
            "TUPLE_REF": lambda cmd: self.__make(expression.TupleRef(self._src_info)),
            "CLASS_REF": lambda cmd: self.__make(expression.ClassRef(self._src_info, cmd[0])),
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
            "COND_OP": lambda cmd: self.__make(expression.ConditionalOp(self._src_info, self._type_register)),
            "UPDATE": lambda cmd: self.__make(expression.UpdateExpr(self._src_info)),
            "CAST_OP": lambda cmd: self.__make(statement.CastOp(self._src_info)),
            "CLOSURE": lambda cmd: self.__make(definition.Closure(self._src_info))
        }
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
            "BLOCK": lambda cmd: self.__make_stmt_block()
        }

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
        self._stack_size += 1

    def _pop(self) -> None:
        self._stack.pop()
        self._exec_mode_stack.pop()
        self._stack_size -= 1

    def _set_info(self, cmd: list[str]) -> None:
        loc: tuple[int, int, int, int] = int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4])
        src_text: str = ", ".join(cmd[5:])
        self._src_info.set_loc(*loc)
        self._src_info.set_text(src_text)
        
    def __make(self, obj: CompilingItem) -> CompilingItem:
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        return obj

    def __make_def_constructor(self, cmd: list[str]) -> definition.ConstructorDef:
        construct_def: definition.ConstructorDef = definition.ConstructorDef(self._src_info, self._symbol_table.namespace, self._var_state_table.assigned_variables, cmd[0], cmd[1:])
        self._exec_mode_stack.append(_ExecMode.SQ)
        return construct_def

    def __make_def_destructor(self, cmd: list[str]) -> definition.DestructorDef:
        destructor_def: definition.DestructorDef = definition.DestructorDef(self._src_info, self._symbol_table.namespace, self._var_state_table.assigned_variables, cmd[0])
        self._exec_mode_stack.append(_ExecMode.SQ)
        return destructor_def
        
    def __make_def_fn(self, cmd: list[str]) -> definition.FnDef:
        fn_def: definition.FnDef = definition.FnDef(self._src_info, self._symbol_table.namespace, self._var_state_table.assigned_variables, cmd[0], cmd[1:])
        self._exec_mode_stack.append(_ExecMode.FN)
        return fn_def
        
    def __make_def_sq(self, cmd: list[str]) -> definition.SqDef:
        sq_def: definition.SqDef = definition.SqDef(self._src_info, self._symbol_table.namespace, self._var_state_table.assigned_variables, cmd[0], cmd[1:])
        self._exec_mode_stack.append(_ExecMode.SQ)
        return sq_def

    def __make_stmt_block(self) -> statement.BlockStmt:
        self._exec_mode_stack.append(self._exec_mode_stack[-1])
        if self._exec_mode_stack[-1] == _ExecMode.FN:
            return statement.FnBlockStmt(self._src_info, self._var_state_table.state)
        else:
            return statement.BlockStmt(self._src_info, self._var_state_table.state)
