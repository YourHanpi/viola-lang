# -*- coding: utf-8 -*-
from .global_parser import GlobalParser, set_loc_command
from .utils import ParsingResult, ParserGenericTable
from utils import Token

from enum import Enum
from typing import Optional, Callable, Sequence, Mapping, Any


__PARSER_UTILS_WITH_ARGS_TYPE = Callable[["Parser", Sequence[Any], Mapping[Any, Any]], Optional[Any]]
__PARSER_UTILS_WITHOUT_ARGS_TYPE = Callable[["Parser"], Optional[Any]]
__PARSER_UTILS_TYPE = __PARSER_UTILS_WITH_ARGS_TYPE | __PARSER_UTILS_WITHOUT_ARGS_TYPE


_OPERATOR_TYPES: set[str] = {
    "ADD", "SUB", "MUL", "MATMUL", "DIV", "MOD", "POW", "LSHIFT", "RSHIFT", "AND", "BIT_AND", "OR", "BIT_OR",
    "BIT_XOR", "NOT", "INVERT", "EQ", "NE", "LT", "GT", "LE", "GE"
}
_EXPR_SPLITTERS: set[str] = {"COMMA", "L_BRACKET", "L_SQUARE_BRACKET", "L_CURLY_BRACKET", "QUESTION", "COLON"}

_BLANK_TOKEN: Token = Token("", ["_BLANK"])


class _ExprState(Enum):
    """
    表达式状态类，用来表示当前的表达式状态。其中：
    - EXPR_ENDING表示刚刚结束了一个表达式，后续可以添加二元运算符等中缀符号。
    - EXPR_STARTING表示期望一个新的表达式，此时添加的中缀符号应当视为非法，或者视为一元运算符。
    - INDEXABLE_ENDING是EXPR_ENDING的一种子状态，这一状态表示前一表达式（可能）可以取索引。
    - CALLABLE_ENDING是INDEXABLE_ENDING的一种子状态。这一状态表示前一表达式（可能）可以被调用。
    - CAST_STARTING是EXPR_STARTING的一种子状态。结束此状态时，应当连接如下文本到IR：["SET_EXPR"]
    - UPDATE_STARTING表示对象更新表达式的花括号的开始，此时应当只接受左花括号和对象更新表达式，直至匹配的右花括号结束。
    """
    EXPR_ENDING = ("EXPR_ENDING", None)
    EXPR_STARTING = ("EXPR_STARTING", None)
    INDEXABLE_ENDING = ("INDEXABLE_ENDING", EXPR_ENDING)
    CALLABLE_ENDING = ("CALLABLE_ENDING", INDEXABLE_ENDING)
    CAST_STARTING = ("CAST_STARTING", EXPR_STARTING)
    UPDATE_STARTING = ("UPDATE_STARTING", None)
    # 后续按需添加状态


def _is_substate(state: _ExprState, substate: _ExprState) -> bool:
    """
    检查substate是否为state的子状态。
    """
    target_name: str = substate.value[0]
    while state is not None:
        if target_name == state.value[0]:
            return True
        # noinspection PyTypeChecker
        state = state.value[1]
    return False


class ExprParser(GlobalParser):

    def __init__(self, workspace: str) -> None:
        super().__init__(workspace)

    @staticmethod
    def _lex_unary_op(tokens: list[Token]) -> list[Token]:
        check_unary_op: bool = True
        for t in tokens:
            if check_unary_op:
                if "ADD" in t.type:
                    t.add_types(["POS"])
                elif "SUB" in t.type:
                    t.add_types(["NEG"])
                elif "MUL" in t.type:
                    t.add_types(["UNPACK"])
            check_unary_op = len((_OPERATOR_TYPES | _EXPR_SPLITTERS) & set(t.type)) > 0
        return tokens

    @set_loc_command
    def _parse_arg_list(self) -> Optional[list[str]]:
        kwarg_name: str = ""
        start_pos: int = self._current
        bracket_count: int = 0
        command: list[str] = []
        while self._current < self._tokens_num:
            if self._match_type("L_BRACKET"):
                bracket_count += 1
            if self._match_type("R_BRACKET"):
                bracket_count -= 1
                if bracket_count == -1:
                    end_pos: int = self._current
                    self._back_to(start_pos)
                    expr_result = self._parse_expr(end_pos)
                    if expr_result is None:
                        return None
                    command += expr_result
                    self._next()
                    return command
            if self._match_type("IDENTIFIER") and bracket_count == 0:
                name: str = self._get_current().text
                self._next()
                if self._match_type("ASSIGN"):
                    if kwarg_name != "":
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    kwarg_name = name
            if self._match_type("COMMA") and bracket_count == 0:
                end_pos: int = self._current
                self._back_to(start_pos)
                start_pos = end_pos
                if kwarg_name != "":
                    self._next(2)
                expr_result = self._parse_expr(end_pos)
                if expr_result is None:
                    return None
                command += expr_result
                command.append("CALL ADD_ARG" if kwarg_name == "" else f"CALL ADD_ARG {kwarg_name}")
                kwarg_name = ""
        self._raise("Unexpected EOF")
        return None

    @set_loc_command
    def _parse_attr_expr(self) -> Optional[tuple[list[str], _ExprState]]:
        id_list: list[str] = []
        is_prefix: bool = True
        expect_dot: bool = False
        command: list[str] = []
        while self._current < self._tokens_num:
            token = self._get_current()
            if self._match_type("IDENTIFIER"):
                if expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                if is_prefix:
                    id_list.append(token.text)
                else:
                    command = ["MAKE EXPR ATTR_OP"] + command + ["CALL SET_CALLER", "CALL SET_ATTR " + token.text]
                expect_dot = True
            elif self._match_type("L_BRACKET"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expr_result = self._parse_bracket_expr(_ExprState.CALLABLE_ENDING)
                if expr_result is None:
                    return None
                command = ["MAKE EXPR CALL_OP"] + command + expr_result[0]
                if is_prefix:
                    is_prefix = False
                    command += self.__handle_id_prefix(id_list)
                command += ["CALL SET_FUNC"]
            elif self._match_type("L_SQUARE_BRACKET"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expr_result = self._parse_square_bracket_expr(_ExprState.CALLABLE_ENDING)
                if expr_result is None:
                    return None
                command = ["MAKE EXPR ITEM_OP"] + command + expr_result[0]
                if is_prefix:
                    is_prefix = False
                    command += self.__handle_id_prefix(id_list)
                command += ["CALL SET_EXPR_LEFT"]
            elif self._match_type("DOT"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expect_dot = False
            else:
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                if is_prefix:
                    command += self.__handle_id_prefix(id_list)
                return command, _ExprState.CALLABLE_ENDING
        self._raise("Unexpected EOF")
        return None

    @set_loc_command
    def _parse_bool(self) -> Optional[tuple[list[str], _ExprState]]:
        result = [f"MAKE EXPR BOOL_LITERAL {self._get_current().text}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @set_loc_command
    def _parse_bracket_expr(self, current_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        command: list[str] = []
        start_pos: int = self._current
        is_tuple: bool = False
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        if self._match_type("R_BRACKET"):
            self._next()
            if _is_substate(_ExprState.CALLABLE_ENDING, current_state):
                return [], _ExprState.CALLABLE_ENDING
            return ["MAKE EXPR TUPLE_REF", "CALL FINISH"], _ExprState.CALLABLE_ENDING
        if _is_substate(_ExprState.CALLABLE_ENDING, current_state):
            arg_list_result = self._parse_arg_list()
            if arg_list_result is None:
                return None
            return arg_list_result, _ExprState.CALLABLE_ENDING
        if self._match_type("AS"):
            self._next()
            type_name = self._parse_type()
            if type_name is None:
                return None
            if not self._match_type("R_BRACKET"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
            return ["MAKE EXPR CAST_OP", f"MAKE EXPR TYPE_REF {type_name}", "CALL SET_TYPE"], _ExprState.CAST_STARTING
        while self._current < self._tokens_num and bracket_count >= 0:
            self._next()
            if self._match_type("L_BRACKET"):
                bracket_count += 1
            elif self._match_type("R_BRACKET"):
                bracket_count -= 1
            elif self._match_type("L_SQUARE_BRACKET"):
                square_bracket_count += 1
            elif self._match_type("R_SQUARE_BRACKET"):
                square_bracket_count -= 1
            elif self._match_type("L_CURLY_BRACKET"):
                curly_bracket_count += 1
            elif self._match_type("R_CURLY_BRACKET"):
                curly_bracket_count -= 1
            elif self._match_type("COMMA") and bracket_count == 0 and square_bracket_count == 0 and curly_bracket_count == 0:
                end_pos: int = self._current
                self._back_to(start_pos)
                self._next()
                start_pos = end_pos
                expr_result = self._parse_expr(end_pos)
                if expr_result is None:
                    return None
                command += expr_result + ["CALL ADD_VALUE"]
                self._next()
                is_tuple = True
            if square_bracket_count < 0 or curly_bracket_count < 0:
                self._raise("Unbalanced brackets")
                return None
        if self._current >= self._tokens_num:
            self._raise("Unexpected EOF")
            return None
        if square_bracket_count != 0 or curly_bracket_count != 0:
            self._raise("Unbalanced brackets")
            return None
        end_pos: int = self._current
        self._back_to(start_pos)
        self._next()
        if self._current < end_pos:
            expr_result = self._parse_expr(end_pos)
            if expr_result is None:
                return None
            command += expr_result
            if is_tuple:
                command.append("CALL ADD_VALUE")
            else:
                command.append("CALL SET_EXPR")
        if is_tuple:
            return ["MAKE EXPR TUPLE_REF"] + command + ["CALL FINISH"], _ExprState.EXPR_ENDING
        return ["MAKE EXPR BRACKETS_OP"] + command, _ExprState.EXPR_ENDING

    @set_loc_command
    def _parse_closure_expr(self) -> Optional[tuple[list[str], _ExprState]]:
        closure_result = self._parse_func([], self._get_current().type[0], True, True)
        if closure_result is None:
            return None
        commands = closure_result[0]
        return ["MAKE EXPR CLOSURE"] + commands + ["CALL SET_DEF"], _ExprState.CALLABLE_ENDING

    @set_loc_command
    def _parse_curly_bracket_expr(self, current_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        is_update: bool = _is_substate(_ExprState.UPDATE_STARTING, current_state)
        if is_update:
            update_result = self._parse_update()
            if update_result is None:
                return None
            return update_result, _ExprState.CALLABLE_ENDING
        # TODO: 增加字典和集合的解析（推迟一个小版本）
        self._raise("The dict expression and the set expression will be added in the future.")
        return None

    @set_loc_command
    def _parse_expr(self, end_pos: int) -> Optional[list[str]]:
        # TODO: 添加表达式解析
        ...

    @set_loc_command
    def _parse_expr_ends_with(self, end_token_types: list[str]) -> Optional[list[str]]:
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        start_pos: int = self._current
        while not self._match_types(end_token_types) or bracket_count > 0 or square_bracket_count > 0 or curly_bracket_count > 0:
            self._next()
            if self._current >= self._tokens_num:
                self._raise("Unexpected end of expression")
                return None
            if self._match_type("L_BRACKET"):
                bracket_count += 1
            elif self._match_type("R_BRACKET"):
                bracket_count -= 1
            elif self._match_type("L_SQUARE_BRACKET"):
                square_bracket_count += 1
            elif self._match_type("R_SQUARE_BRACKET"):
                square_bracket_count -= 1
            elif self._match_type("L_CURLY_BRACKET"):
                curly_bracket_count += 1
            elif self._match_type("R_CURLY_BRACKET"):
                curly_bracket_count -= 1
        end_pos: int = self._current
        self._back_to(start_pos)
        return self._parse_expr(end_pos)

    @set_loc_command
    def _parse_expr_splits_with(self, splitters: list[str], end_token_types: list[str], expr_end_command: list[str]) -> Optional[tuple[list[str], int]]:
        command: list[str] = []
        expr_count: int = 0
        while self._current < self._tokens_num:
            sub_command = self._parse_expr_ends_with(splitters + end_token_types)
            expr_count += 1
            if sub_command is None:
                return None
            self._next()
            if len(sub_command) > 0:
                command += sub_command + expr_end_command
            else:
                return command, expr_count
            if self._match_types(end_token_types):
                return command, expr_count
        self._raise("Unexpected end of expression")
        return None

    @set_loc_command
    def _parse_float(self) -> Optional[tuple[list[str], _ExprState]]:
        result = [f"MAKE EXPR FLOAT_LITERAL {self._get_current().text}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @set_loc_command
    def _parse_int(self) -> Optional[tuple[list[str], _ExprState]]:
        result = [f"MAKE EXPR INTEGER_LITERAL {self._get_current().text} {self._get_current().type[0]}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @set_loc_command
    def _parse_operand(self) -> Optional[tuple[list[str], _ExprState]]:
        if self._match_type("L_BRACKET"):
            result = self._parse_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_type("L_SQUARE_BRACKET"):
            result = self._parse_square_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_type("L_CURLY_BRACKET"):
            result = self._parse_curly_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_type("IDENTIFIER"):
            result = self._parse_attr_expr()
        elif self._match_types(["INT32", "UINT32", "INT_N", "UINT_N"]):
            result = self._parse_int()
        elif self._match_types(["FLOAT", "DOUBLE"]):
            result = self._parse_float()
        elif self._match_types(["STRING", "LONG_STRING"]):
            result = self._parse_string()
        elif self._match_types(["TRUE", "FALSE"]):
            result = self._parse_bool()
        elif self._match_types(["SQ", "FN"]):
            result = self._parse_closure_expr()
        else:
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        if result is None:
            return None
        return result

    @set_loc_command
    def _parse_square_bracket_expr(self, expr_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        if not self._match_type("L_SQUARE_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        is_index: bool = _is_substate(_ExprState.INDEXABLE_ENDING, expr_state)
        if self._match_type("R_SQUARE_BRACKET"):
            self._next()
            if is_index:
                return [], _ExprState.CALLABLE_ENDING
            return ["MAKE EXPR ARRAY_REF", "CALL FINISH"], _ExprState.CALLABLE_ENDING
        command: list[str] = ["MAKE EXPR ARRAY_REF"] if not is_index else []
        if is_index:
            result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], ["CALL ADD_ARG"])
        else:
            result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], ["CALL ADD_VALUE"])
        if result is None:
            return None
        command += result[0]
        return command, _ExprState.CALLABLE_ENDING

    @set_loc_command
    def _parse_string(self) -> Optional[tuple[list[str], _ExprState]]:
        string_buffer: list[str] = []
        while self._match_types(["STRING", "LONG_STRING"]):
            if self._match_type("LONG_STRING"):
                skip_length: int = 3
            else:
                skip_length: int = 1
            string_buffer.append(self._get_current().text[skip_length:-skip_length].replace("\n", "\\n"))
            self._next()
        return ["MAKE EXPR STRING_LITERAL " + "".join(string_buffer)], _ExprState.INDEXABLE_ENDING

    @set_loc_command
    def _parse_unary_op(self) -> Optional[tuple[list[str], _ExprState]]:
        command: list[str] = []
        steps: int = 0
        while self._match_types(["POS", "NEG", "NOT", "INVERSE", "UNPACK"]):
            if self._match_type("POS"):
                command.append("MAKE EXPR POSITIVE_OP")
            elif self._match_type("NEG"):
                command.append("MAKE EXPR NEGATIVE_OP")
            elif self._match_type("NOT"):
                command.append("MAKE EXPR NOT_OP")
            elif self._match_type("INVERSE"):
                command.append("MAKE EXPR BIT_NOT_OP")
            elif self._match_type("UNPACK"):
                command.append("MAKE EXPR UNPACK")
            self._next()
            steps += 1
        operand = self._parse_operand()
        if operand is None:
            return None
        command += operand[0]
        command += ["CALL SET_EXPR"] * steps
        return command, operand[1]

    @set_loc_command
    def _parse_update(self) -> Optional[list[str]]:
        command: list[str] = []
        while self._current < self._tokens_num:
            if self._match_type("COMMA"):
                self._next()
            elif self._match_type("L_SQUARE_BRACKET"):
                result = self._parse_update_item()
                if result is None:
                    return None
                command += result
            elif self._match_type("DOT"):
                result = self._parse_update_prop()
                if result is None:
                    return None
                command += result
            elif self._match_type("R_CURLY_BRACKET"):
                command.append("CALL FINISH")
                return command
        self._raise("Unexpected end of expression")
        return None

    @set_loc_command
    def _parse_update_item(self) -> Optional[list[str]]:
        command: list[str] = []
        self._next()
        result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], [])
        if result is None:
            return None
        command += result[0]
        expr_count = result[1]
        if not self._match_type("ASSIGN"):
            self._raise(f"Expected \"=\", but got unexpected token: {self._get_current().text}")
        self._next()
        value = self._parse_expr_ends_with(["COMMA", "R_CURLY_BRACKET"])
        if value is None:
            return None
        command += value + [f"CALL ADD_ITEM {expr_count}"]
        self._next()
        return command

    @set_loc_command
    def _parse_update_prop(self) -> Optional[list[str]]:
        command: list[str] = []
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Expected identifier, but got unexpected token: {self._get_current().text}")
            return None
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise(f"Expected '=', but got unexpected token: {self._get_current().text}")
            return None
        value = self._parse_expr_ends_with(["COMMA", "R_CURLY_BRACKET"])
        if value is None:
            return None
        command += value
        self._next()
        return command

    def __handle_id_prefix(self, id_list: list[str]) -> list[str]:
        id_list = self.__get_import_prefix(id_list)
        command: list[str] = ["MAKE EXPR ATTR_OP"] * (len(id_list) - 1)
        command += ["MAKE EXPR VARIABLE_REF auto " + id_list[0]]
        for id_item in id_list[1:]:
            command += ["CALL SET_CALLER", "CALL SET_ATTR " + id_item]
        return command
