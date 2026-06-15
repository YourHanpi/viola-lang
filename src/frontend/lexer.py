# -*- coding: utf-8 -*-
from .utils import TokenStreamIO
from utils import SourceInfo, CompilerException, COMPILER_PARAMS, VIOLA_INIT
from utils.file_marks import TOKEN_POSTFIX, CACHE_DIR
from utils.fsm import Token, StateNode, FSM
from utils.logger import Logger
from utils.task import TaskResult, TaskResultState

import os
from typing import Optional


class Lexer(FSM):
    
    def __init__(self, workspace: str, thread_index: int = 0) -> None:
        super().__init__()
        self._workspace: str = workspace
        self._src_info: SourceInfo = VIOLA_INIT
        self._start_line: int = 1
        self._start_col: int = 1
        self._end_line: int = 1
        self._end_col: int = 1
        self._exceptions: list[CompilerException] = []
        self._logger = Logger(f"Lexer[{thread_index}]")

    @property
    def exceptions(self) -> list[CompilerException]:
        return self._exceptions

    def lex(self, path: str) -> Optional[list[Token]]:
        self._src_info = SourceInfo(path)
        with open(path, "r", encoding=COMPILER_PARAMS["encoding"]) as f:
            text: str = f.read()
        self.reset()
        self._exceptions.clear()
        tokens: list[Token] = []
        char_buf: list[str] = []
        current_loc: int = 0
        text_length: int = len(text)
        error_occurred: bool = False
        while current_loc < text_length:
            char: str = text[current_loc]
            token: Token = Lexer._get_char_token(char)
            if char == "\n":
                self._end_line += 1
                self._end_col = 1
            else:
                self._end_col += 1
            next_state = self.transfer(token)
            if next_state is None:
                if self._current.output is None:
                    self._src_info.set_loc(self._start_line, self._start_col, self._end_line, self._end_col)
                    self._src_info.set_text("".join(char_buf))
                    self._logger.error(str(CompilerException(f"Unexpected character {char}", self._src_info.copy())))
                    error_occurred = True
                    while current_loc < text_length and char not in " \n\t":
                        current_loc += 1
                        char = text[current_loc]
                    tokens.append(Token("", ["_ERROR"], self._start_col))
                else:
                    tokens.append(Token("".join(char_buf), [self._current.output], self._start_col))
                self._start_line = self._end_line
                self._start_col = self._end_col
                char_buf.clear()
                self.reset()
                self.transfer(token)
            char_buf.append(char)
            current_loc += 1
        if error_occurred:
            return None
        return tokens

    def lex_with_writer(self, file_path: str) -> TaskResult:
        file_path = os.path.abspath(file_path)
        result = self.lex(file_path)
        if result is None:
            self._logger.error(f"Failed to lex: {file_path}")
            return TaskResult(TaskResultState.FAILURE)
        file_relpath = os.path.relpath(file_path, self._workspace)
        file_path = os.path.abspath(os.path.join(CACHE_DIR, file_relpath))
        if not os.path.exists(file_path + TOKEN_POSTFIX):
            TokenStreamIO.write(file_path + TOKEN_POSTFIX, result)
        return TaskResult(TaskResultState.SUCCESS)

    @staticmethod
    def _get_char_token(char: str) -> Token:
        type_list: list[str] = [char]
        if char in "01":
            type_list.append("BIN_DIGIT")
        if char in "01234567":
            type_list.append("OCT_DIGIT")
        if char.isdigit():
            if char != "0":
                type_list.append("DIGIT_NO_ZERO")
            type_list.append("DIGIT")
        if char.isalpha():
            type_list.append(f"CHAR_{char.upper()}")
            type_list.append("LETTER")
        if char in "0123456789abcdefABCDEF":
            type_list.append("HEX_DIGIT")
        if char != "\n":
            type_list.append("CHAR")
        return Token(char, type_list)
        
    def _set_states_list(self) -> StateNode:
        start: StateNode = StateNode()
        start = Lexer.__string_states_list(start, True)
        start = Lexer.__string_states_list(start, False)
        start = Lexer.__number_states_list(start)
        start = Lexer.__identifier_states_list(start)
        start = Lexer.__blank_states_list(start)
        start = Lexer.__bin_math_op_states_list(start)
        start = Lexer.__compare_states_list(start)
        start = Lexer.__brackets_states_list(start)
        start = Lexer.__punctuation_states_list(start)
        start = Lexer.__comment_states_list(start)
        return start

    @staticmethod
    def __bin_math_op_states_list(first: StateNode) -> StateNode:
        add_op: StateNode = StateNode()
        sub_op: StateNode = StateNode()
        ret_ptr: StateNode = StateNode()
        mul_op: StateNode = StateNode()
        div_op: StateNode = Lexer.__comment_states_list(StateNode())
        mod_op: StateNode = StateNode()
        pow_op: StateNode = StateNode()
        matmul_op: StateNode = StateNode()
        first.add_transfer("+", add_op)
        first.add_transfer("-", sub_op)
        first.add_transfer("*", mul_op)
        first.add_transfer("/", div_op)
        first.add_transfer("%", mod_op)
        first.add_transfer("@", matmul_op)
        add_op.set_output("ADD")
        sub_op.set_output("SUB")
        sub_op.add_transfer(">", ret_ptr)
        ret_ptr.set_output("ARROW")
        mul_op.set_output("MUL")
        mul_op.add_transfer("*", pow_op)
        div_op.set_output("DIV")
        mod_op.set_output("MOD")
        pow_op.set_output("POW")
        matmul_op.set_output("MATMUL")
        return first

    @staticmethod
    def __blank_states_list(first: StateNode) -> StateNode:
        first.add_transfer(" ", first)
        first.add_transfer("\n", first)
        first.add_transfer("\t", first)
        first.set_output("_BLANK")
        return first

    @staticmethod
    def __brackets_states_list(first: StateNode) -> StateNode:
        l_bracket: StateNode = StateNode()
        r_bracket: StateNode = StateNode()
        l_square_bracket: StateNode = StateNode()
        r_square_bracket: StateNode = StateNode()
        l_curly_bracket: StateNode = StateNode()
        r_curly_bracket: StateNode = StateNode()
        escape: StateNode = StateNode()
        escaped_curly_bracket: StateNode = StateNode()
        first.add_transfer("(", l_bracket)
        first.add_transfer(")", r_bracket)
        first.add_transfer("[", l_square_bracket)
        first.add_transfer("]", r_square_bracket)
        first.add_transfer("{", l_curly_bracket)
        first.add_transfer("}", r_curly_bracket)
        first.add_transfer("\\", escape)
        escape.add_transfer("{", escaped_curly_bracket)
        escape.add_transfer("}", escaped_curly_bracket)
        escaped_curly_bracket.set_output("ESCAPED_CURLY_BRACKET")
        l_bracket.set_output("L_BRACKET")
        r_bracket.set_output("R_BRACKET")
        l_square_bracket.set_output("L_SQUARE_BRACKET")
        r_square_bracket.set_output("R_SQUARE_BRACKET")
        l_curly_bracket.set_output("L_CURLY_BRACKET")
        r_curly_bracket.set_output("R_CURLY_BRACKET")
        return first

    @staticmethod
    def __comment_states_list(div_op: StateNode) -> StateNode:
        line_comment2: StateNode = StateNode()
        multi_lines_comment2: StateNode = StateNode()
        multi_lines_comment3: StateNode = StateNode()
        multi_lines_comment4: StateNode = StateNode()
        div_op.add_transfer("/", line_comment2)
        div_op.add_transfer("*", multi_lines_comment2)
        line_comment2.add_transfer("CHAR", line_comment2)
        line_comment2.set_output("_COMMENT")
        multi_lines_comment2.add_transfer("CHAR", multi_lines_comment2)
        multi_lines_comment2.add_transfer("\n", multi_lines_comment2)
        multi_lines_comment2.add_transfer("*", multi_lines_comment3)
        multi_lines_comment3.add_transfer("/", multi_lines_comment4)
        multi_lines_comment3.add_transfer("*", multi_lines_comment3)
        multi_lines_comment3.add_transfer("CHAR", multi_lines_comment2)
        multi_lines_comment3.set_output("_COMMENT")
        multi_lines_comment4.add_transfer("CHAR", multi_lines_comment4)
        multi_lines_comment4.set_output("_COMMENT")
        return div_op

    @staticmethod
    def __compare_states_list(first: StateNode) -> StateNode:
        assign: StateNode = StateNode()
        update: StateNode = StateNode()
        eq: StateNode = StateNode()
        ne: StateNode = StateNode()
        lt: StateNode = StateNode()
        lshift: StateNode = StateNode()
        gt: StateNode = StateNode()
        rshift: StateNode = StateNode()
        le: StateNode = StateNode()
        ge: StateNode = StateNode()
        not_state: StateNode = StateNode()
        invert: StateNode = StateNode()
        first.add_transfer("=", assign)
        first.add_transfer("<", lt)
        first.add_transfer(">", gt)
        first.add_transfer("!", not_state)
        first.add_transfer("~", invert)
        assign.add_transfer("=", eq)
        assign.add_transfer(">", update)
        assign.set_output("ASSIGN")
        update.set_output("UPDATE")
        eq.set_output("EQ")
        not_state.add_transfer("=", ne)
        not_state.set_output("NOT")
        lt.add_transfer("=", le)
        lt.add_transfer("<", lshift)
        lt.set_output("LT")
        lshift.set_output("LSHIFT")
        gt.add_transfer("=", ge)
        gt.add_transfer(">", rshift)
        gt.set_output("GT")
        rshift.set_output("RSHIFT")
        le.set_output("LE")
        ge.set_output("GE")
        invert.set_output("INVERT")
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
        keywords: list[str] = [
            "abstract",
            "as",
            "async",
            "catch",
            "class",
            "cpart",
            "elif",
            "else",
            "enum",
            "export",
            "extends",
            "false",
            "finally",
            "fn",
            "from",
            "if",
            "import",
            "public",
            "private",
            "protected",
            "return",
            "sq",
            "static",
            "this",
            "throw",
            "true",
            "try",
            "using"
        ]
        states: list[list[StateNode]] = []
        buffered_word: str = ""
        buffered_word_length: int = 0
        buffered_state: StateNode = StateNode()
        for i, k in enumerate(keywords):
            j: int = 0
            c: str = k[0]
            kw_length: int = len(k)
            states.append([])
            while j < buffered_word_length and j < kw_length and c == buffered_word[j]:
                buffered_state = states[i - 1][j]
                j += 1
                c = k[j]
            if j == 0:
                first.add_transfer(c, buffered_state)
            while j < kw_length:
                new_node: StateNode = StateNode()
                buffered_state.add_transfer(c, new_node)
                buffered_state.add_transfer("LETTER", identifier_state)
                buffered_state.add_transfer("DIGIT", identifier_state)
                if j == kw_length - 1:
                    new_node.set_output(k.upper())
                else:
                    new_node.set_output("IDENTIFIER")
                states[i].append(new_node)
                buffered_state = new_node
                j += 1
                c = k[j]
        return first

    @staticmethod
    def __logical_states_list(first: StateNode) -> StateNode:
        bit_and: StateNode = StateNode()
        logical_and: StateNode = StateNode()
        bit_or: StateNode = StateNode()
        logical_or: StateNode = StateNode()
        bit_xor: StateNode = StateNode()
        first.add_transfer("&", bit_and)
        first.add_transfer("|", bit_or)
        first.add_transfer("^", bit_xor)
        bit_and.add_transfer("&", logical_and)
        bit_or.add_transfer("|", logical_or)
        bit_and.set_output("BIT_AND")
        logical_and.set_output("AND")
        bit_or.set_output("BIT_OR")
        logical_or.set_output("OR")
        bit_xor.set_output("BIT_XOR")
        return first

    @staticmethod
    def __number_states_list(first: StateNode) -> StateNode:
        int_state: StateNode = StateNode()
        zero_state: StateNode = StateNode()
        double_float_state: StateNode = StateNode()
        exponential_state1: StateNode = StateNode()
        exponential_state2: StateNode = StateNode()
        hex_state: StateNode = StateNode()
        oct_state: StateNode = StateNode()
        bin_state: StateNode = StateNode()
        float_state: StateNode = StateNode()
        unsigned_state: StateNode = StateNode()
        signed_state: StateNode = StateNode()
        unsigned_n_state: StateNode = StateNode()
        signed_n_state: StateNode = StateNode()
        first.add_transfer("DIGIT_NO_ZERO", int_state)
        first.add_transfer("0", zero_state)
        int_state.add_transfer("DIGIT", int_state)
        int_state.add_transfer("DOT", double_float_state)
        int_state.add_transfer("CHAR_E", exponential_state1)
        int_state.add_transfer("CHAR_U", unsigned_state)
        int_state.add_transfer("CHAR_I", signed_state)
        int_state.set_output("INT32")
        zero_state.add_transfer("DOT", double_float_state)
        zero_state.add_transfer("CHAR_X", hex_state)
        zero_state.add_transfer("DIGIT", oct_state)
        zero_state.add_transfer("CHAR_B", bin_state)
        zero_state.set_output("INT32")
        double_float_state.add_transfer("DIGIT", double_float_state)
        double_float_state.add_transfer("CHAR_E", exponential_state1)
        double_float_state.add_transfer("CHAR_F", float_state)
        double_float_state.set_output("DOUBLE")
        exponential_state1.add_transfer("DIGIT", exponential_state2)
        exponential_state2.add_transfer("SIGN", exponential_state2)
        exponential_state2.add_transfer("DIGIT", exponential_state2)
        exponential_state2.add_transfer("CHAR_F", float_state)
        exponential_state2.set_output("DOUBLE")
        hex_state.add_transfer("HEX_DIGIT", hex_state)
        hex_state.add_transfer("CHAR_U", unsigned_state)
        hex_state.add_transfer("CHAR_I", signed_state)
        hex_state.set_output("INT32")
        oct_state.add_transfer("OCT_DIGIT", oct_state)
        oct_state.add_transfer("CHAR_U", unsigned_state)
        oct_state.add_transfer("CHAR_I", signed_state)
        oct_state.set_output("INT32")
        bin_state.add_transfer("BIN_DIGIT", bin_state)
        bin_state.add_transfer("CHAR_U", unsigned_state)
        bin_state.add_transfer("CHAR_I", signed_state)
        bin_state.set_output("INT32")
        float_state.set_output("FLOAT")
        unsigned_state.add_transfer("DIGIT", unsigned_n_state)
        unsigned_n_state.set_output("UINT32")
        signed_state.add_transfer("DIGIT", signed_n_state)
        signed_n_state.set_output("INT32")
        unsigned_n_state.set_output("UINT_N")
        signed_n_state.set_output("INT_N")
        return first

    @staticmethod
    def __punctuation_states_list(first: StateNode) -> StateNode:
        comma: StateNode = StateNode()
        semicolon: StateNode = StateNode()
        generic_start1: StateNode = StateNode()
        generic_start2: StateNode = StateNode()
        colon: StateNode = StateNode()
        question: StateNode = StateNode()
        first.add_transfer(",", comma)
        first.add_transfer(";", semicolon)
        first.add_transfer(":", colon)
        first.add_transfer("?", question)
        comma.set_output("COMMA")
        semicolon.set_output("SEMICOLON")
        colon.add_transfer(":", generic_start1)
        generic_start1.add_transfer("<", generic_start2)
        colon.set_output("COLON")
        question.set_output("QUESTION")
        generic_start2.set_output("GENERIC_START")
        return first
        
    @staticmethod
    def __string_states_list(first_state: StateNode, double_quote: bool) -> StateNode:
        quote: str = "\"" if double_quote else "\'"
        first: StateNode = StateNode()
        second: StateNode = StateNode()
        third: StateNode = StateNode()
        forth: StateNode = StateNode()
        fifth: StateNode = StateNode()
        sixth: StateNode = StateNode()
        escape1: StateNode = StateNode()
        escape2: StateNode = StateNode()
        first_state.add_transfer(quote, first)
        first.add_transfer(quote, second)
        first.add_transfer("CHAR", first)
        first.add_transfer("\\", escape1)
        escape1.add_transfer("CHAR", first)
        second.add_transfer(quote, third)
        second.set_output("STRING")
        third.add_transfer(quote, forth)
        third.add_transfer("CHAR", third)
        third.add_transfer("\n", third)
        third.add_transfer("\\", escape2)
        escape2.add_transfer("CHAR", third)
        forth.add_transfer(quote, fifth)
        forth.add_transfer("CHAR", third)
        fifth.add_transfer(quote, sixth)
        fifth.add_transfer("CHAR", third)
        sixth.set_output("LONG_STRING")
        return first
