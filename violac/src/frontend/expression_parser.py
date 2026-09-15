# -*- coding: utf-8 -*-
from .global_parser import GlobalParser
from .utils import ParsingResult
from utils import Token, SourceInfo
from utils.file_marks import COMMAND_POSTFIX, GLOBAL_COMMAND_POSTFIX, CACHE_DIR, get_cache_path
from utils.logger import Logger
from utils.task import TaskResult, TaskResultState

from enum import Enum
import os
from typing import Optional, Callable, Sequence, Mapping, Any, Union


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

    def __eq__(self, other: Union["_ExprState", tuple[str, Optional["_ExprState"]]]) -> bool:
        if isinstance(other, _ExprState):
            return self.value[0] == other.value[0]
        elif isinstance(other, tuple):
            return self.value[0] == other[0]
        else:
            return False


def _is_substate(substate: _ExprState | tuple[str, _ExprState], state: _ExprState | tuple[str, _ExprState]) -> bool:
    """
    检查substate是否为state的子状态。
    """
    target_name: str = substate.value[0] if isinstance(substate, _ExprState) else substate[0]
    while state is not None:
        state_tuple = state.value if isinstance(state, _ExprState) else state
        if target_name == state_tuple[0]:
            return True
        # noinspection PyTypeChecker
        state = state_tuple[1]
    return False


__PARSER_UTILS_WITH_ARGS_TYPE = Callable[["ExprParser", Sequence[Any], Mapping[Any, Any]], Optional[list[str]]]
__PARSER_UTILS_WITHOUT_ARGS_TYPE = Callable[["ExprParser"], Optional[list[str]]]
__PARSER_UTILS_TYPE = __PARSER_UTILS_WITH_ARGS_TYPE | __PARSER_UTILS_WITHOUT_ARGS_TYPE

__PARSER_UTILS_WITH_STATE_WITH_ARGS_TYPE = Callable[["ExprParser", Sequence[Any], Mapping[Any, Any]], Optional[tuple[list[str], _ExprState]]]
__PARSER_UTILS_WITH_STATE_WITHOUT_ARGS_TYPE = Callable[["ExprParser"], Optional[tuple[list[str], _ExprState]]]
__PARSER_UTILS_WITH_STATE_TYPE = __PARSER_UTILS_WITH_STATE_WITH_ARGS_TYPE | __PARSER_UTILS_WITH_STATE_WITHOUT_ARGS_TYPE


_OPERATOR_TYPES: set[str] = {
    "ADD", "SUB", "MUL", "MATMUL", "DIV", "MOD", "POW", "LSHIFT", "RSHIFT", "AND", "BIT_AND", "OR", "BIT_OR",
    "BIT_XOR", "EQ", "NE", "LT", "GT", "LE", "GE"
}
_EXPR_SPLITTERS: set[str] = {"COMMA", "L_BRACKET", "L_SQUARE_BRACKET", "L_CURLY_BRACKET", "QUESTION", "COLON"}

_BLANK_TOKEN: Token = Token("", ["_BLANK"])


def _set_loc_command(parse_func: __PARSER_UTILS_TYPE) -> __PARSER_UTILS_TYPE:
    """
    装饰器：自动为解析函数注入位置信息和源代码文本，并生成SET_INFO命令。
    :param parse_func: 被装饰的解析函数。
    :return: 装饰后的包装函数。
    """
    def wrapper(self: "ExprParser", *args, **kwargs) -> Optional[list[str]]:
        # self._logger.debug(f"Enter function {parse_func.__name__}")
        start_line, start_col, _, _ = self._src_info.location_tuple
        start_token_count: int = self._current
        result = parse_func(self, *args, **kwargs)
        end_token_count: int = self._current
        codes: str = "".join([token.text for token in self._tokens[start_token_count:end_token_count]])
        self._src_info.set_text(codes)
        if result is not None:
            command = result
            _, _, end_line, end_col = self._src_info.location_tuple
            return [f"SET_INFO {start_line} {start_col} {end_line} {end_col}"] + command
        self._logger.debug(f"Exit function {parse_func.__name__}")
        return None

    return wrapper


def _set_loc_command_with_state(parse_func: __PARSER_UTILS_WITH_STATE_TYPE) -> __PARSER_UTILS_WITH_STATE_TYPE:
    """
    装饰器：自动为解析函数注入位置信息和源代码文本，并生成SET_INFO命令（带表达式状态）。
    :param parse_func: 被装饰的解析函数。
    :return: 装饰后的包装函数。
    """
    def wrapper(self: "ExprParser", *args, **kwargs) -> Optional[tuple[list[str], _ExprState]]:
        # self._logger.debug(f"Enter function {parse_func.__name__}")
        start_line, start_col, _, _ = self._src_info.location_tuple
        start_token_count: int = self._current
        result = parse_func(self, *args, **kwargs)
        end_token_count: int = self._current
        codes: str = "".join([token.text for token in self._tokens[start_token_count:end_token_count]])
        self._src_info.set_text(codes)
        if result is not None:
            command, state = result
            _, _, end_line, end_col = self._src_info.location_tuple
            return [f"SET_INFO {start_line} {start_col} {end_line} {end_col}"] + command, state
        self._logger.debug(f"Exit function {parse_func.__name__}")
        return None

    return wrapper


class ExprParser(GlobalParser):
    """
    表达式解析器，负责解析Viola语言中的各种表达式。
    """

    def __init__(self, workspace: str) -> None:
        """
        初始化表达式解析器。
        :param workspace: 工作区路径。
        """
        super().__init__(workspace)

    def parse_all_expr(self, parsing_result: ParsingResult) -> Optional[list[str]]:
        """
        解析解析结果中的所有表达式。
        :param parsing_result: 解析结果对象。
        :return: 完整命令列表，失败返回None。
        """
        command = parsing_result.command
        current_command_count: int = 0
        expr_count: int = 0
        command_count: int = len(command)
        while current_command_count < command_count:
            if command[current_command_count].startswith("RAW "):
                raw_data = command[current_command_count].split(" ")
                location_str = raw_data[2].split(":")
                self._src_info.set_loc(int(location_str[0]), int(location_str[1]), int(location_str[2]), int(location_str[3]))
                self._src_info.set_text(" ".join(raw_data[3:]))
                expr_token = parsing_result.expr_tokens[expr_count]
                result = self.parse_single_expr(expr_token)
                if result is None:
                    return None
                command = command[:current_command_count] + result + command[current_command_count + 1:]
                current_command_count += len(result)
                command_count = len(command)
                expr_count += 1
            else:
                current_command_count += 1
        return command

    def parse_expr_to_file(self, file_path: str, thread_index: int = 0) -> TaskResult:
        """
        解析表达式并将结果写入文件。
        :param file_path: 源文件路径。
        :param thread_index: 线程索引。
        :return: 任务结果。
        """
        self._logger = Logger(f"Expression Parser[{thread_index}]")
        self._logger.info(f"Start parsing expressions from {file_path}")
        self._src_info = SourceInfo(file_path)
        file_abs_path = os.path.abspath(file_path)
        cache_path = get_cache_path(self._workspace, file_abs_path)
        cache_file_path = cache_path + COMMAND_POSTFIX
        global_command_path = cache_path + GLOBAL_COMMAND_POSTFIX
        if not self._set_file_lock(cache_path):
            # 该文件正在被其他线程解析，重新入队等待
            return TaskResult(TaskResultState.DELAYED, [["violac", "parse-expr", file_path]])
        self._held_locks.add(cache_path)
        try:
            if os.path.exists(cache_file_path) and os.path.exists(global_command_path) and \
                    os.path.getmtime(cache_file_path) >= os.path.getmtime(global_command_path):
                # 已解析过表达式且全局命令未更新，直接复用已有结果
                self._logger.info(f"Passed: {file_path}")
                return TaskResult(TaskResultState.SUCCESS, [["violac", "run-vm", file_path]])
            parsing_result: ParsingResult = ParsingResult.read(cache_path)
            self._imports = parsing_result.imports if parsing_result.imports is not None else {}
            command = self.parse_all_expr(parsing_result)
            if command is None:
                self._logger.error(f"Failed to parse {file_path}")
                return TaskResult(TaskResultState.FAILURE)
            os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)
            with open(cache_file_path, "w", encoding=self._ENCODING) as f:
                f.write("\n".join(command).replace("\n\n", "\n"))
            self._logger.info(f"Successfully parsed expressions from {file_path}")
            return TaskResult(TaskResultState.SUCCESS, [["violac", "run-vm", file_path]])
        finally:
            self._held_locks.discard(cache_path)
            self._remove_file_lock(cache_path)

    def parse_single_expr(self, expr_tokens: list[Token]) -> Optional[list[str]]:
        """
        解析单个表达式。
        :param expr_tokens: 表达式的记号列表。
        :return: 表达式对应的命令列表，失败返回None。
        """
        self._load_tokens(expr_tokens)
        self._lex_unary_op()
        self._current = 0
        if len(expr_tokens) == 0:
            self._raise("Empty expression")
            return None
        return self._parse_expr(len(expr_tokens))

    def _lex_unary_op(self) -> None:
        """
        预处理一元运算符，将加减乘等标记转换为一元运算符标记。
        """
        check_unary_op: bool = True
        while self._current < self._tokens_num:
            t: Token = self._get_current()
            if check_unary_op:
                if "ADD" in t.type:
                    t.set_types(["POS"])
                elif "SUB" in t.type:
                    t.set_types(["NEG"])
                elif "MUL" in t.type:
                    t.set_types(["UNPACK"])
            check_unary_op = len((_OPERATOR_TYPES | _EXPR_SPLITTERS) & set(t.type)) > 0
            self._next()

    @_set_loc_command_with_state
    def _parse_add_sub(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析加减法表达式。"""
        return self._parse_bin_math_op(
            {"ADD": "MAKE EXPR ADD_OP", "SUB": "MAKE EXPR SUB_OP"},
            end_pos, self._parse_mul_div_mod
        )

    @_set_loc_command_with_state
    def _parse_and(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析逻辑与表达式。"""
        return self._parse_bin_math_op(
            {"AND": "MAKE EXPR AND_OP"},
            end_pos, self._parse_bit_xor
        )

    @_set_loc_command
    def _parse_arg_list(self) -> Optional[list[str]]:
        """解析函数调用参数列表。"""
        command: list[str] = []
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if self._match_type("R_BRACKET"):
            self._next()
            return []
        while self._current < self._tokens_num:
            if self._match_type("R_BRACKET"):
                self._next()
                break
            start_pos: int = self._current
            expr_start_pos: int = start_pos
            kwarg_name: str = ""
            # kwarg 检测：仅当实参以 IDENTIFIER ASSIGN 开头
            if self._match_type("IDENTIFIER"):
                name: str = self._get_current().text
                self._next()
                if self._match_type("ASSIGN"):
                    kwarg_name = name
                    self._next()
                    expr_start_pos = self._current
                else:
                    self._back_to(start_pos)
            # 扫描到实参列表结束的 R_BRACKET 或顶层 COMMA
            bracket_count: int = 0
            square_bracket_count: int = 0
            curly_bracket_count: int = 0
            while self._current < self._tokens_num:
                if self._match_type("L_BRACKET"):
                    bracket_count += 1
                elif self._match_type("R_BRACKET"):
                    if bracket_count == 0:
                        break
                    bracket_count -= 1
                elif self._match_type("L_SQUARE_BRACKET"):
                    square_bracket_count += 1
                elif self._match_type("R_SQUARE_BRACKET"):
                    square_bracket_count -= 1
                elif self._match_type("L_CURLY_BRACKET"):
                    curly_bracket_count += 1
                elif self._match_type("R_CURLY_BRACKET"):
                    curly_bracket_count -= 1
                elif self._match_type("COMMA") and bracket_count == 0 and square_bracket_count == 0 and \
                        curly_bracket_count == 0:
                    break
                self._next()
            end_pos: int = self._current
            self._back_to(expr_start_pos)
            expr_result = self._parse_expr(end_pos)
            if expr_result is None:
                return None
            command += expr_result
            command.append("CALL ADD_ARG" if kwarg_name == "" else f"CALL ADD_ARG {kwarg_name}")
            self._next_to(end_pos)
            if self._match_type("COMMA"):
                self._next()
            elif self._match_type("R_BRACKET"):
                self._next()
                break
        return command

    @_set_loc_command_with_state
    def _parse_attr_expr(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析属性访问表达式（包括链式调用和索引）。"""
        id_list: list[str] = []
        is_prefix: bool = True
        expect_dot: bool = False
        command: list[str] = []
        while self._current < self._tokens_num:
            token = self._get_current()
            if self._match_types(["IDENTIFIER", "THIS"]):
                if expect_dot:
                    self._raise("Expected dot. Unexpected token: " + self._get_current().text)
                    return None
                if is_prefix:
                    if self._match_type("THIS") and len(id_list) > 0:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    id_list.append(token.text if not self._match_type("THIS") else "_this")
                else:
                    command = ["MAKE EXPR ATTR_OP"] + command + ["CALL SET_CALLER", "CALL SET_ATTR " + token.text]
                expect_dot = True
                self._next()
            elif self._match_type("L_BRACKET"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expr_result = self._parse_arg_list()
                if expr_result is None:
                    return None
                if is_prefix:
                    is_prefix = False
                    command += self.__handle_id_prefix(id_list)
                command = ["MAKE EXPR CALL_OP"] + expr_result + command + ["CALL SET_FUNC"]
            elif self._match_type("L_SQUARE_BRACKET"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expr_result = self._parse_square_bracket_expr(_ExprState.INDEXABLE_ENDING)
                if expr_result is None:
                    return None
                if is_prefix:
                    is_prefix = False
                    command += self.__handle_id_prefix(id_list)
                command = ["MAKE EXPR ITEM_OP"] + expr_result[0] + command + ["CALL SET_EXPR_LEFT"]
            elif self._match_type("GENERIC_START"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                if is_prefix:
                    is_prefix = False
                    command += self.__handle_id_prefix(id_list)
                expr_result = self._parse_generic_expr()
                if expr_result is None:
                    return None
                command = ["MAKE EXPR GENERIC_CALL"] + command + ["CALL SET_GENERIC_EXPR"] + expr_result + ["CALL FINISH_GENERIC"]
            elif self._match_type("DOT"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expect_dot = False
                self._next()
            else:
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                if is_prefix:
                    command += self.__handle_id_prefix(id_list)
                return command, _ExprState.CALLABLE_ENDING
        if is_prefix:
            command += self.__handle_id_prefix(id_list)
        return command, _ExprState.CALLABLE_ENDING

    def _parse_bin_math_op(
            self, op_maker_commands: dict[str, str], end_pos: int,
            inner_parser: Callable[[int], Optional[tuple[list[str], _ExprState]]],
            associativity_left: bool = True
    ) -> Optional[tuple[list[str], _ExprState]]:
        """解析二元数学运算表达式，支持左右结合性。"""
        if associativity_left:
            commands = self._parse_bin_op_left_associativity(op_maker_commands, end_pos, inner_parser)
        else:
            commands = self._parse_bin_op_right_associativity(op_maker_commands, end_pos, inner_parser)
        return commands

    @_set_loc_command_with_state
    def _parse_bin_op_left_associativity(
            self, op_maker_commands: dict[str, str], end_pos: int,
            inner_parser: Callable[[int], Optional[tuple[list[str], _ExprState]]]
    ) -> Optional[tuple[list[str], _ExprState]]:
        """解析左结合二元运算符表达式。"""
        token_start, token_end, op_list = self._split_by_bin_op(list(op_maker_commands.keys()), end_pos)
        if len(op_list) == 0:
            return inner_parser(end_pos)
        commands = list(map(lambda op: op_maker_commands[op], op_list[::-1]))
        state: _ExprState = _ExprState.CALLABLE_ENDING
        for i, start in enumerate(token_start):
            self._next_to(start)
            sub_commands = inner_parser(token_end[i])
            if sub_commands is None:
                return None
            commands += sub_commands[0]
            state = sub_commands[1]
            if i > 0:
                commands += ["CALL SET_EXPR_RIGHT"]
            if i < len(token_start) - 1:
                commands += ["CALL SET_EXPR_LEFT"]
        return commands, state

    @_set_loc_command_with_state
    def _parse_bin_op_right_associativity(
            self, op_maker_commands: dict[str, str], end_pos: int,
            inner_parser: Callable[[int], Optional[tuple[list[str], _ExprState]]]
    ) -> Optional[tuple[list[str], _ExprState]]:
        """解析右结合二元运算符表达式。"""
        token_start, token_end, op_list = self._split_by_bin_op(list(op_maker_commands.keys()), end_pos)
        if len(op_list) == 0:
            return inner_parser(end_pos)
        commands = list(map(lambda op: op_maker_commands[op], op_list))
        state: _ExprState = _ExprState.CALLABLE_ENDING
        for i, start in enumerate(token_start):
            self._next_to(start)
            sub_result = inner_parser(token_end[i])
            if sub_result is None:
                return None
            commands += sub_result[0]
            state = sub_result[1]
            # 首个操作数进入最内层（最后创建的）运算符，其余依次归入外层运算符
            commands.append("CALL SET_EXPR_LEFT" if i == 0 else "CALL SET_EXPR_RIGHT")
        return commands, state

    @_set_loc_command_with_state
    def _parse_bit_and(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析按位与表达式。"""
        return self._parse_bin_math_op(
            {"BIT_AND": "MAKE EXPR BIT_AND_OP"},
            end_pos,
            self._parse_equal_expr
        )

    @_set_loc_command_with_state
    def _parse_bit_or(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析按位或表达式。"""
        return self._parse_bin_math_op(
            {"BIT_OR": "MAKE EXPR BIT_OR_OP"},
            end_pos,
            self._parse_bit_and
        )

    @_set_loc_command_with_state
    def _parse_bit_xor(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析按位异或表达式。"""
        return self._parse_bin_math_op(
            {"BIT_XOR": "MAKE EXPR BIT_XOR_OP"},
            end_pos,
            self._parse_bit_or
        )

    @_set_loc_command_with_state
    def _parse_bool(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析布尔字面量（true/false）。"""
        result = [f"MAKE EXPR BOOL_LITERAL {self._get_current().text}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @_set_loc_command_with_state
    def _parse_bracket_expr(self, current_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        """解析圆括号表达式（分组、调用、元组、类型转换）。"""
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        command: list[str] = []
        start_pos: int = self._current
        is_tuple: bool = False
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        self._next()
        if self._match_type("R_BRACKET"):
            self._next()
            if _is_substate(_ExprState.CALLABLE_ENDING, current_state):
                return [], _ExprState.CALLABLE_ENDING
            return ["MAKE EXPR TUPLE_REF", "CALL FINISH"], _ExprState.CALLABLE_ENDING
        self._back()
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
            operand_result = self._parse_operand()
            if operand_result is None:
                return None
            return (["MAKE EXPR CAST_OP"] + type_name + ["CALL SET_TYPE"] + operand_result[0] + ["CALL SET_EXPR"],
                    _ExprState.CALLABLE_ENDING)
        while self._current < self._tokens_num and bracket_count >= 0:
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
            elif self._match_type("COMMA") and bracket_count == 1 and square_bracket_count == 0 and curly_bracket_count == 0:
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
                continue
            if square_bracket_count < 0 or curly_bracket_count < 0:
                self._raise("Unbalanced brackets")
                return None
            self._next()
            if bracket_count <= 0:
                break
        if bracket_count > 0 or square_bracket_count != 0 or curly_bracket_count != 0:
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
        else:
            self._next()
        # 子表达式的解析停在本层的右括号上（_parse_expr以end_pos为界，
        # 不在界内消费括号），此处消费它，否则括号表达式之后的后缀
        # （如(a + 1).toString()）无法解析（见开发疑问记录166）
        if self._match_type("R_BRACKET"):
            self._next()
        if is_tuple:
            return ["MAKE EXPR TUPLE_REF"] + command + ["CALL FINISH"], _ExprState.EXPR_ENDING
        # 括号表达式之后允许继续调用与取索引（如(f)(x)、(arr)[0]）：
        # CALLABLE_ENDING是INDEXABLE_ENDING的子状态、后者又是EXPR_ENDING的子状态，
        # 故原先以EXPR_ENDING收尾的用法（二元运算符等）不受影响
        # （见开发疑问记录175(a)）
        return ["MAKE EXPR BRACKETS_OP"] + command, _ExprState.CALLABLE_ENDING

    @_set_loc_command_with_state
    def _parse_closure_expr(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析闭包表达式（匿名函数）。"""
        closure_result = self._parse_func([], self._get_current().type[0], True, True)
        if closure_result is None:
            return None
        commands = closure_result[0]
        return ["MAKE EXPR CLOSURE"] + commands + ["CALL SET_DEF"], _ExprState.CALLABLE_ENDING

    @_set_loc_command_with_state
    def _parse_compare_expr(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析比较表达式（> < >= <=）。"""
        return self._parse_bin_math_op({
            "GT": "MAKE EXPR GT_OP",
            "LT": "MAKE EXPR LT_OP",
            "GE": "MAKE EXPR GE_OP",
            "LE": "MAKE EXPR LE_OP"
        }, end_pos, self._parse_shift)

    @_set_loc_command_with_state
    def _parse_curly_bracket_expr(self, current_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        """解析花括号表达式（对象更新）。"""
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

    @_set_loc_command
    def _parse_expr(self, end_pos: int) -> Optional[list[str]]:
        """解析表达式（顶层入口，分发到切片解析）。"""
        result = self._parse_update_arrow(end_pos)
        return result

    @_set_loc_command_with_state
    def _parse_equal_expr(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析相等性比较表达式（== !=）。"""
        return self._parse_bin_math_op({
            "EQ": "MAKE EXPR EQ_OP",
            "NE": "MAKE EXPR NE_OP"
        }, end_pos, self._parse_compare_expr)

    @_set_loc_command
    def _parse_expr_ends_with(
            self, end_token_types: list[str], parser: Callable[[int], Optional[list[str]]],
            end_pos: Optional[int] = None
    ) -> Optional[list[str]]:
        """解析以指定类型记号结尾的表达式。"""
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        question_mark_count: int = 0
        start_pos: int = self._current
        while self._current < self._tokens_num and (
            not self._match_types(end_token_types) or bracket_count > 0 or square_bracket_count > 0 or
            curly_bracket_count > 0 or question_mark_count > 0
        ):
            self._next()
            if end_pos is not None and self._current >= end_pos:
                break
            if self._match_type("L_BRACKET"):
                bracket_count += 1
            elif self._match_type("R_BRACKET"):
                bracket_count -= 1
                if "R_BRACKET" in end_token_types and bracket_count <= 1:
                    break
            elif self._match_type("L_SQUARE_BRACKET"):
                square_bracket_count += 1
            elif self._match_type("R_SQUARE_BRACKET"):
                square_bracket_count -= 1
                if "R_SQUARE_BRACKET" in end_token_types and square_bracket_count <= 1:
                    break
            elif self._match_type("L_CURLY_BRACKET"):
                curly_bracket_count += 1
            elif self._match_type("R_CURLY_BRACKET"):
                curly_bracket_count -= 1
                if "R_CURLY_BRACKET" in end_token_types and curly_bracket_count <= 1:
                    break
            if bracket_count == 0 and square_bracket_count == 0 and curly_bracket_count == 0:
                if self._match_type("QUESTION_MARK"):
                    question_mark_count += 1
                elif self._match_type("COLON"):
                    question_mark_count -= 1
        end_pos: int = self._current
        self._back_to(start_pos)
        return parser(end_pos)

    @_set_loc_command_with_state
    def _parse_expr_splits_with(self, splitters: list[str], end_token_types: list[str], expr_end_command: list[str],
                                parser: Callable[[int], Optional[list[str]]]) -> Optional[tuple[list[str], int]]:
        """解析以分隔符分割的表达式列表。"""
        command: list[str] = []
        expr_count: int = 0
        while self._current < self._tokens_num:
            sub_command = self._parse_expr_ends_with(splitters + end_token_types, parser)
            expr_count += 1
            if sub_command is None:
                return None
            if len(sub_command) > 0:
                command += sub_command + expr_end_command
            else:
                return command, expr_count
            if self._match_types(end_token_types):
                self._next()
                return command, expr_count
            self._next()
        # self._raise("Unexpected end of expression")
        return command, expr_count

    @_set_loc_command_with_state
    def _parse_float(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析浮点数字面量。"""
        result = [f"MAKE EXPR FLOAT_LITERAL {self._get_current().text}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @_set_loc_command
    def _parse_generic_expr(self) -> Optional[list[str]]:
        """解析泛型参数表达式（::<T>）。"""
        if not self._match_type("GENERIC_START"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        result = self._parse_type_list(["CALL ADD_TYPE_ARG"])
        if result is None:
            return None
        if result[1] < 0:
            self._raise("Unbalanced angle brackets")
            return None
        return result[0]

    @_set_loc_command_with_state
    def _parse_int(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析整数字面量。"""
        result = [f"MAKE EXPR INTEGER_LITERAL {self._get_current().text} {self._get_current().type[0]}"]
        self._next()
        return result, _ExprState.EXPR_ENDING

    @_set_loc_command_with_state
    def _parse_mul_div_mod(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析乘除模表达式（* / % @）。"""
        return self._parse_bin_math_op(
            {"MUL": "MAKE EXPR MUL_OP", "DIV": "MAKE EXPR DIV_OP", "MOD": "MAKE EXPR MOD_OP", "MATMUL": "MAKE EXPR MATMUL_OP"},
            end_pos, self._parse_pow
        )

    @_set_loc_command_with_state
    def _parse_operand(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析操作数（字面量、标识符、括号表达式等）。"""
        if self._match_type("_EOF"):
            self._raise("Unexpected end of expression")
            return None
        is_identifier_chain: bool = False
        if self._match_type("L_BRACKET"):
            result = self._parse_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_type("L_SQUARE_BRACKET"):
            result = self._parse_square_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_type("L_CURLY_BRACKET"):
            result = self._parse_curly_bracket_expr(_ExprState.EXPR_STARTING)
        elif self._match_types(["IDENTIFIER", "THIS"]):
            result = self._parse_attr_expr()
            is_identifier_chain = True
        elif self._match_types(["INT32", "UINT32", "INT_N", "UINT_N", "SIZE_T"]):
            result = self._parse_int()
        elif self._match_types(["FLOAT", "DOUBLE"]):
            result = self._parse_float()
        elif self._match_types(["STRING", "LONG_STRING", "RAW_STRING"]):
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
        if not is_identifier_chain:
            # 非标识符链的操作数（如字符串字面量）同样支持
            # 属性访问/调用/索引等后缀操作（如"abc".count("a")）
            result = self.__parse_postfix_chain(result)
        return result

    def __parse_postfix_chain(self, operand: tuple[list[str], _ExprState]) -> tuple[list[str], _ExprState]:
        """解析操作数的后缀链（.属性、调用、索引）。"""
        result: tuple[list[str], _ExprState] = operand
        while True:
            if self._match_type("DOT"):
                self._next()
                if not self._match_type("IDENTIFIER"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return result
                attr: str = self._get_current().text
                self._next()
                result = (["MAKE EXPR ATTR_OP"] + result[0] +
                          ["CALL SET_CALLER", "CALL SET_ATTR " + attr], _ExprState.CALLABLE_ENDING)
            elif self._match_type("L_BRACKET") and \
                    _is_substate(_ExprState.CALLABLE_ENDING, result[1]):
                arg_list_result = self._parse_arg_list()
                if arg_list_result is None:
                    return result
                result = (["MAKE EXPR CALL_OP"] + arg_list_result + result[0] + ["CALL SET_FUNC"],
                          _ExprState.CALLABLE_ENDING)
            elif self._match_type("L_SQUARE_BRACKET") and \
                    _is_substate(_ExprState.INDEXABLE_ENDING, result[1]):
                index_result = self._parse_square_bracket_expr(result[1])
                if index_result is None:
                    return result
                result = (["MAKE EXPR ITEM_OP"] + index_result[0] + result[0] + ["CALL SET_EXPR_LEFT"],
                          _ExprState.CALLABLE_ENDING)
            else:
                return result

    @_set_loc_command_with_state
    def _parse_or(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析逻辑或表达式。"""
        return self._parse_bin_math_op({"OR": "MAKE EXPR OR_OP"}, end_pos, self._parse_and)

    def _parse_or_no_state(self, end_pos: int) -> Optional[list[str]]:
        """解析逻辑或表达式（无状态版本，用于条件表达式内部）。"""
        result = self._parse_or(end_pos)
        if result is None:
            return None
        return result[0]

    @_set_loc_command_with_state
    def _parse_pow(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析幂运算表达式（**，右结合）。"""
        return self._parse_bin_math_op({"POW": "MAKE EXPR POW_OP"}, end_pos, self._parse_unary_op, False)

    @_set_loc_command_with_state
    def _parse_question_expr(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析条件表达式（三元运算符 ? :）。"""
        cond_commands = self._parse_expr_ends_with(["QUESTION"], self._parse_or_no_state, end_pos)
        if cond_commands is None:
            return None
        if not self._match_type("QUESTION"):
            return cond_commands, _ExprState.EXPR_ENDING
        self._next()
        then_commands = self._parse_expr_ends_with(["COLON"], self._parse_question_expr_no_state)
        if then_commands is None:
            return None
        self._next()
        else_commands = self._parse_expr_ends_with([], self._parse_question_expr_no_state, end_pos)
        if else_commands is None:
            return None
        return ["MAKE EXPR COND_OP"] + cond_commands + ["CALL SET_EXPR_COND"] + then_commands + ["CALL SET_EXPR_THEN"] + \
            else_commands + ["CALL SET_EXPR_ELSE"], _ExprState.EXPR_ENDING

    def _parse_question_expr_no_state(self, end_pos: int) -> Optional[list[str]]:
        """解析条件表达式（无状态版本，用于嵌套调用）。"""
        result = self._parse_question_expr(end_pos)
        if result is None:
            return None
        return result[0]

    @_set_loc_command_with_state
    def _parse_shift(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析移位表达式（<< >>）。"""
        return self._parse_bin_math_op(
            {"LSHIFT": "MAKE EXPR LSHIFT_OP", "RSHIFT": "MAKE EXPR RSHIFT_OP"},
            end_pos, self._parse_add_sub
        )

    @_set_loc_command_with_state
    def _parse_slice(self, end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析切片表达式或顶层表达式（包含三元运算符）。"""
        question_count: int = 0
        slice_count: int = 0
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        start_token_begin: Optional[int] = self._current if not self._match_type("COLON") else None
        stop_token_begin: Optional[int] = None
        step_token_begin: Optional[int] = None
        steps: int = 0
        while self._current < end_pos:
            if self._match_type("QUESTION") and bracket_count == 0 and square_bracket_count == 0 and curly_bracket_count == 0:
                question_count += 1
            elif self._match_type("COLON") and bracket_count == 0 and square_bracket_count == 0 and curly_bracket_count == 0:
                if question_count > 0:
                    question_count -= 1
                else:
                    slice_count += 1
                    if slice_count == 1:
                        stop_token_begin = self._current
                    elif slice_count == 2:
                        step_token_begin = self._current
                    elif slice_count > 2:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
            elif self._match_type("L_BRACKET"):
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
            self._next()
            steps += 1
        is_slice = slice_count > 0
        command: list[str] = ["MAKE EXPR SLICE_REF"] if is_slice else []
        self._back(steps)
        if start_token_begin is not None:
            if stop_token_begin is not None:
                start_expr_end_pos: int = stop_token_begin - 1
            elif step_token_begin is not None:
                start_expr_end_pos: int = step_token_begin - 2
            else:
                start_expr_end_pos: int = end_pos
            start_result = self._parse_question_expr(start_expr_end_pos)
            if start_result is None:
                return None
            command += start_result[0]
            if not is_slice:
                return command, start_result[1]
            else:
                command.append("CALL SET_START")
        self._next()
        if stop_token_begin is not None:
            if step_token_begin is not None:
                stop_expr_end_pos: int = step_token_begin - 1
            else:
                stop_expr_end_pos: int = end_pos
            if self._current >= end_pos:
                return command, _ExprState.CALLABLE_ENDING
            stop_result = self._parse_question_expr(stop_expr_end_pos)
            if stop_result is None:
                return None
            command += stop_result[0] + ["CALL SET_END"]
            if slice_count < 2:
                return command, _ExprState.CALLABLE_ENDING
        self._next()
        step_result = self._parse_question_expr(end_pos)
        if step_result is None:
            return None
        command += step_result[0] + ["CALL SET_STEP"]
        return command, _ExprState.CALLABLE_ENDING

    @_set_loc_command_with_state
    def _parse_square_bracket_expr(self, expr_state: _ExprState) -> Optional[tuple[list[str], _ExprState]]:
        """解析方括号表达式（数组、索引）。"""
        if not self._match_type("L_SQUARE_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        is_index: bool = _is_substate(_ExprState.INDEXABLE_ENDING, expr_state)
        if self._match_type("R_SQUARE_BRACKET"):
            self._next()
            if is_index:
                return [], _ExprState.CALLABLE_ENDING
            return ["MAKE EXPR ARRAY_REF", "CALL FINISH"], _ExprState.CALLABLE_ENDING
        command: list[str] = ["MAKE EXPR ARRAY_REF"] if not is_index else []
        if is_index:
            result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], ["CALL ADD_ARG"], self._parse_expr)
        else:
            result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], ["CALL ADD_VALUE"], self._parse_expr)
        if result is None:
            return None
        command += result[0]
        if not is_index:
            command.append("CALL FINISH")
        return command, _ExprState.CALLABLE_ENDING

    @_set_loc_command_with_state
    def _parse_string(self) -> Optional[tuple[list[str], _ExprState]]:
        """解析字符串字面量（支持连续字符串拼接）。"""
        string_buffer: list[str] = []
        while self._match_types(["STRING", "LONG_STRING", "RAW_STRING"]):
            if self._match_type("LONG_STRING"):
                skip_length: int = 3
            elif self._match_type("RAW_STRING"):
                # r 前缀原始字符串：转义反斜杠，使后端转义替换后仍为原始内容
                skip_length: int = 2
                raw_content: str = self._get_current().text[skip_length:-1]
                string_buffer.append(raw_content.replace("\\", "\\\\").replace("\n", "\\n"))
                self._next()
                continue
            else:
                skip_length: int = 1
            # 空格转义为\s：命令按空白分割且执行时会strip，否则首尾空格会丢失
            string_buffer.append(self._get_current().text[skip_length:-skip_length]
                                 .replace("\n", "\\n").replace(" ", "\\s"))
            self._next()
        return ["MAKE EXPR STRING_LITERAL " + "".join(string_buffer)], _ExprState.INDEXABLE_ENDING

    @_set_loc_command
    def _parse_type(self) -> Optional[list[str]]:
        """解析类型表达式（类型引用、泛型、函数类型等）。"""
        result: list[str] = []
        if self._match_type("IDENTIFIER"):
            result.append(f"MAKE EXPR TYPE_REF {self._get_current().text}")
            self._next()
            if self._match_type("GENERIC_START"):
                result = ["MAKE EXPR GENERIC_CALL"] + result + ["CALL SET_GENERIC_EXPR"]
                inner_result = self._parse_type_list(["CALL ADD_TYPE_ARG"])
                if inner_result is None:
                    return None
                result += inner_result[0] + ["CALL FINISH_GENERIC"]
                if inner_result[1] < 0:
                    return result
        elif self._match_type("L_BRACKET"):
            result.append("MAKE EXPR TUPLE_TYPE_REF")
            self._next()
            inner_result = self._parse_type_list(["CALL ADD_TYPE"])
            if inner_result is None:
                return None
            result += inner_result[0]
            if inner_result[1] < 0:
                return result
            result.append("CALL FINISH")
            if self._match_type("ARROW"):
                result = ["MAKE EXPR FUNCTION_TYPE_REF"] + result + ["CALL SET_ARG_TYPES"]
                self._next()
                if not self._match_type("L_BRACKET"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                result.append("MAKE EXPR TUPLE_TYPE_REF")
                self._next()
                inner_result = self._parse_type_list(["CALL ADD_TYPE"])
                if inner_result is None:
                    return None
                result += inner_result[0]
                result += ["CALL FINISH", "CALL SET_RETURN_TYPE", "CALL FINISH"]
                if inner_result[1] < 0:
                    return result
        else:
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        while self._match_type("L_SQUARE_BRACKET"):
            result = ["MAKE EXPR ARRAY_TYPE_REF"] + result + ["CALL SET_TYPE"]
            self._next()
            if not self._match_type("R_SQUARE_BRACKET"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
        return result

    @_set_loc_command_with_state
    def _parse_type_list(self, type_ending_commands: list[str]) -> Optional[tuple[list[str], int]]:
        """解析类型列表（逗号分隔的类型序列）。"""
        result: list[str] = []
        expect_comma: bool = False
        while self._current < self._tokens_num:
            if not expect_comma:
                inner_result = self._parse_type()
                if inner_result is None:
                    return None
                result += inner_result + type_ending_commands
                expect_comma = True
            elif self._match_type("R_BRACKET"):
                self._next()
                return result, 0
            elif self._match_type("COMMA") and expect_comma:
                self._next()
                expect_comma = False
            elif self._match_type("GT"):
                self._next()
                return result, 0
            elif self._match_type("RSHIFT"):
                # >>一次闭合两层泛型参数（如Box::<Box::<int>>）
                self._next()
                return result, -1
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        self._raise("Unexpected end of expression")
        return None

    @_set_loc_command_with_state
    def _parse_unary_op(self, _end_pos: int) -> Optional[tuple[list[str], _ExprState]]:
        """解析一元运算符表达式（正、负、非、取反、解包）。"""
        if self._current >= self._tokens_num:
            self._raise("Unexpected end of expression")
            return None
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

    @_set_loc_command
    def _parse_update(self) -> Optional[list[str]]:
        """解析对象更新表达式（花括号内的属性和索引更新）。"""
        command: list[str] = []
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        while self._current < self._tokens_num:
            if self._match_type("COMMA"):
                self._next()
            elif self._match_type("L_SQUARE_BRACKET"):
                self._next()
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
                self._next()
                return command
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        self._raise("Unexpected end of expression")
        return None

    @_set_loc_command
    def _parse_update_arrow(self, end_pos: int) -> Optional[list[str]]:
        start_pos = self._current
        bracket_count = 0
        square_bracket_count = 0
        curly_bracket_count = 0
        while self._current < end_pos:
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
            elif self._match_type("UPDATE") and bracket_count == 0 and square_bracket_count == 0 and curly_bracket_count == 0:
                arrow_loc = self._current
                self._back_to(start_pos)
                source_result = self._parse_expr(arrow_loc)
                if source_result is None:
                    return None
                self._next()
                modifier_result = self._parse_curly_bracket_expr(_ExprState.UPDATE_STARTING)
                if modifier_result is None:
                    return None
                return ["MAKE EXPR UPDATE"] + source_result + ["CALL SET_SRC_EXPR"] + modifier_result[0]
            self._next()
        self._back_to(start_pos)
        result = self._parse_slice(end_pos)
        if result is None:
            return None
        return result[0]

    @_set_loc_command
    def _parse_update_item(self) -> Optional[list[str]]:
        """解析对象更新中的索引项。[expr] = value。"""
        command: list[str] = []
        # self._logger.debug(self._get_current().text)
        result = self._parse_expr_splits_with(["COMMA"], ["R_SQUARE_BRACKET"], [], self._parse_expr)
        if result is None:
            return None
        command += result[0]
        expr_count = result[1]
        if not self._match_type("ASSIGN"):
            self._raise(f"Expected \"=\", but got unexpected token: {self._get_current().text}")
        self._next()
        value = self._parse_expr_ends_with(["COMMA", "R_CURLY_BRACKET"], self._parse_expr)
        if value is None:
            return None
        command += value + [f"CALL ADD_ITEM {expr_count}"]
        return command

    @_set_loc_command
    def _parse_update_prop(self) -> Optional[list[str]]:
        """解析对象更新中的属性项。.prop = value。"""
        command: list[str] = []
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Expected identifier, but got unexpected token: {self._get_current().text}")
            return None
        prop_name: str = self._get_current().text
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise(f"Expected '=', but got unexpected token: {self._get_current().text}")
            return None
        self._next()
        value = self._parse_expr_ends_with(["COMMA", "R_CURLY_BRACKET"], self._parse_expr)
        if value is None:
            return None
        command += value
        command.append(f"CALL ADD_PROP {prop_name}")
        return command

    def _split_by_bin_op(self, op_types: list[str], end_pos: int) -> tuple[list[int], list[int], list[str]]:
        """
        根据二元运算符分割表达式，返回操作数起始位置和运算符列表。
        :param op_types: 运算符类型列表。
        :param end_pos: 结束位置。
        :return: 起始位置列表和运算符类型列表。
        """
        tokens_start_pos: list[int] = [self._current]
        tokens_end_pos: list[int] = []
        operators: list[str] = []
        bracket_count: int = 0
        square_bracket_count: int = 0
        curly_bracket_count: int = 0
        angle_bracket_count: int = 0
        start_pos: int = self._current
        while self._current < end_pos:
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
            elif self._match_type("GENERIC_START"):
                # 泛型参数列表中的>是闭合尖括号，不是比较运算符
                angle_bracket_count += 1
            elif self._match_type("GT") and angle_bracket_count > 0:
                # 仅在泛型参数列表内部，>才作为闭合尖括号处理；
                # 否则（如a > b）交由下面的运算符分支处理
                angle_bracket_count -= 1
            elif self._match_type("RSHIFT") and angle_bracket_count >= 2:
                # >>闭合两层泛型参数（如Array::<Array::<T>>）；
                # 不在泛型列表中时作为右移运算符处理
                angle_bracket_count -= 2
            elif self._match_types(op_types) and bracket_count == 0 and square_bracket_count == 0 and \
                    curly_bracket_count == 0 and angle_bracket_count == 0:
                tokens_end_pos.append(self._current)
                operators.append(self._get_current().type[0])
                self._next()
                tokens_start_pos.append(self._current)
                # 不移到操作数的第二个记号：末尾的_next会跳过操作数的首个记号，
                # 使其后的括号不再被计数（如a + (b + 1).y中的(，见开发疑问记录166）
                continue
            self._next()
        self._back_to(start_pos)
        tokens_end_pos.append(end_pos)
        return tokens_start_pos, tokens_end_pos, operators

    def __handle_id_prefix(self, id_list: list[str]) -> list[str]:
        """
        处理标识符前缀，将其转换为属性访问命令序列。
        :param id_list: 标识符列表。
        :return: 属性访问命令列表。
        """
        id_list = self._get_import_prefix(id_list)
        command: list[str] = ["MAKE EXPR ATTR_OP"] * (len(id_list) - 1)
        command += ["MAKE EXPR VARIABLE_REF auto " + id_list[0]]
        for id_item in id_list[1:]:
            command += ["CALL SET_CALLER", "CALL SET_ATTR " + id_item]
        return command
