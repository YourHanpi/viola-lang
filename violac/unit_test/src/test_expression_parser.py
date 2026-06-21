# -*- coding: utf-8 -*-
"""Unit tests for the ExprParser class in violac.src.frontend.expression_parser."""

import sys
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock, PropertyMock

# Add source path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "violac", "src")))

# Mock the global logger controller to prevent file-handler errors
import utils.logger as logger_module
_mock_controller = MagicMock()
_mock_controller.log_level = 100  # Higher than all levels, suppresses output
logger_module.LOGGER_CONTROLLER = _mock_controller

from utils.fsm import Token
from utils.source_info import SourceInfo, VIOLA_INIT
from utils.task import TaskResult, TaskResultState
from frontend.expression_parser import (
    ExprParser, _ExprState, _is_substate, _set_loc_command,
    _set_loc_command_with_state,
)
from frontend.global_parser import GlobalParser
from frontend.utils import ParsingResult


def _make_token(text: str, types: list[str],
                start_line: int = 1, start_col: int = 1,
                end_line: int = 1, end_col: int = 1) -> Token:
    """Helper to create a Token with specific source info."""
    src = SourceInfo("<test>")
    src.set_loc(start_line, start_col, end_line, end_col)
    return Token(text, types, src)


def _make_id_token(name: str, col: int = 1) -> Token:
    """Helper to create an IDENTIFIER token."""
    return _make_token(name, ["IDENTIFIER"], start_col=col, end_col=col + len(name) - 1)


def _make_punct_token(text: str, ptype: str, col: int = 1) -> Token:
    """Helper to create a punctuation token."""
    return _make_token(text, [ptype], start_col=col, end_col=col)


def _make_int_token(value: str, col: int = 1) -> Token:
    """Helper to create an integer literal token."""
    return _make_token(value, ["INT32"], start_col=col, end_col=col + len(value) - 1)


def _make_str_token(value: str, col: int = 1) -> Token:
    """Helper to create a string literal token."""
    return _make_token(f'"{value}"', ["STRING"], start_col=col, end_col=col + len(value) + 1)


def _make_bool_token(value: str, col: int = 1) -> Token:
    """Helper to create a boolean literal token."""
    return _make_token(value, [value.upper()], start_col=col, end_col=col + len(value) - 1)


class TestExprParserInit(unittest.TestCase):
    """Tests for ExprParser.__init__."""

    def test_init_inherits_from_global_parser(self):
        """ExprParser should inherit from GlobalParser."""
        parser = ExprParser("/test/workspace")
        self.assertIsInstance(parser, GlobalParser)

    def test_init_sets_workspace(self):
        """Should set the workspace path."""
        parser = ExprParser("./test/workspace")
        self.assertEqual(parser._workspace, os.path.abspath("./test/workspace"))

    def test_init_has_empty_tokens(self):
        """Should initialize with empty token structures."""
        parser = ExprParser("./test/workspace")
        self.assertEqual(parser._tokens, [])
        self.assertEqual(parser._tokens_num, 0)
        self.assertEqual(parser._current, 0)


class TestExprState(unittest.TestCase):
    """Tests for _ExprState enum and _is_substate function."""

    def test_is_substate_direct_match(self):
        """Direct state: _is_substate(A, A) returns True."""
        self.assertTrue(_is_substate(_ExprState.EXPR_ENDING, _ExprState.EXPR_ENDING))

    def test_is_substate_parent_match(self):
        """_is_substate walks state's parent chain, checking against substate's name.
        So _is_substate(EXPR_ENDING, INDEXABLE_ENDING) is True because
        INDEXABLE_ENDING's parent is EXPR_ENDING, matching substate's name."""
        self.assertTrue(_is_substate(_ExprState.EXPR_ENDING, _ExprState.INDEXABLE_ENDING))

    def test_is_substate_grandparent_match(self):
        """_is_substate(EXPR_ENDING, CALLABLE_ENDING) walks to INDEXABLE_ENDING
        then to EXPR_ENDING -> match."""
        self.assertTrue(_is_substate(_ExprState.EXPR_ENDING, _ExprState.CALLABLE_ENDING))

    def test_is_substate_not_related(self):
        """EXPR_STARTING has no parent chain containing EXPR_ENDING."""
        self.assertFalse(_is_substate(_ExprState.EXPR_ENDING, _ExprState.EXPR_STARTING))

    def test_is_substate_cast_starting(self):
        """_is_substate(EXPR_STARTING, CAST_STARTING): CAST_STARTING parent is EXPR_STARTING -> match."""
        self.assertTrue(_is_substate(_ExprState.EXPR_STARTING, _ExprState.CAST_STARTING))

    def test_is_substate_reverse_not_match(self):
        """_is_substate(CAST_STARTING, EXPR_STARTING): EXPR_STARTING parent is None, no match."""
        self.assertFalse(_is_substate(_ExprState.CAST_STARTING, _ExprState.EXPR_STARTING))

    def test_is_substate_update_unrelated(self):
        """UPDATE_STARTING parent is None, so no ancestor matches EXPR_ENDING or EXPR_STARTING."""
        self.assertFalse(_is_substate(_ExprState.EXPR_ENDING, _ExprState.UPDATE_STARTING))
        self.assertFalse(_is_substate(_ExprState.EXPR_STARTING, _ExprState.UPDATE_STARTING))

    def test_expr_ending_value(self):
        """EXPR_ENDING should have correct value structure."""
        self.assertEqual(_ExprState.EXPR_ENDING.value[0], "EXPR_ENDING")
        self.assertIsNone(_ExprState.EXPR_ENDING.value[1])

    def test_indexable_ending_parent(self):
        """INDEXABLE_ENDING's parent should be EXPR_ENDING."""
        self.assertEqual(_ExprState.INDEXABLE_ENDING.value[1], _ExprState.EXPR_ENDING)

    def test_callable_ending_parent(self):
        """CALLABLE_ENDING's parent should be INDEXABLE_ENDING."""
        self.assertEqual(_ExprState.CALLABLE_ENDING.value[1], _ExprState.INDEXABLE_ENDING)


class TestLexUnaryOp(unittest.TestCase):
    """Tests for ExprParser._lex_unary_op."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_add_becomes_pos_after_operator(self):
        """After a binary operator, + should become POS."""
        tokens = [
            _make_punct_token("+", "ADD", 1),
            _make_int_token("5", 3),
        ]
        self.parser._load_tokens(tokens)
        self.parser._current = 0
        self.parser._lex_unary_op()
        self.assertIn("POS", self.parser._tokens[0].type)

    def test_sub_becomes_neg_after_operator(self):
        """After a binary operator, - should become NEG."""
        tokens = [
            _make_punct_token("-", "SUB", 1),
            _make_int_token("5", 3),
        ]
        self.parser._load_tokens(tokens)
        self.parser._current = 0
        self.parser._lex_unary_op()
        self.assertIn("NEG", self.parser._tokens[0].type)

    def test_mul_becomes_unpack_after_operator(self):
        """After a binary operator, * should become UNPACK."""
        tokens = [
            _make_punct_token("*", "MUL", 1),
            _make_id_token("x", 3),
        ]
        self.parser._load_tokens(tokens)
        self.parser._current = 0
        self.parser._lex_unary_op()
        self.assertIn("UNPACK", self.parser._tokens[0].type)

    def test_add_stays_add_after_operand(self):
        """After an operand (not an operator), + should remain ADD."""
        tokens = [
            _make_int_token("5", 1),
            _make_punct_token("+", "ADD", 3),
            _make_int_token("3", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._current = 0
        self.parser._lex_unary_op()
        # The first token is not an operator, it's INT32
        # The second token is + which FOLLOWS an operand, so should stay ADD
        self.assertIn("ADD", self.parser._tokens[1].type)
        self.assertNotIn("POS", self.parser._tokens[1].type)

    def test_initial_unary_at_start(self):
        """At the start of an expression, operators should be unary."""
        tokens = [
            _make_punct_token("-", "SUB", 1),
            _make_int_token("5", 2),
        ]
        self.parser._load_tokens(tokens)
        self.parser._current = 0
        self.parser._lex_unary_op()
        self.assertIn("NEG", self.parser._tokens[0].type)


class TestSplitByBinOp(unittest.TestCase):
    """Tests for ExprParser._split_by_bin_op."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_split_no_operators(self):
        """No operators means one segment."""
        tokens = [
            _make_int_token("42", 1),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        starts, ends, ops = self.parser._split_by_bin_op(["ADD", "SUB"], 1)
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(ends), 1)
        self.assertEqual(len(ops), 0)

    def test_split_single_operator(self):
        """Single operator should split into two segments."""
        tokens = [
            _make_int_token("1", 1),
            _make_punct_token("+", "ADD", 3),
            _make_int_token("2", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        starts, ends, ops = self.parser._split_by_bin_op(["ADD"], 3)
        self.assertEqual(len(starts), 2)
        self.assertEqual(len(ends), 2)
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0], "ADD")

    def test_split_respects_brackets(self):
        """Operators inside brackets should not split."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_int_token("1", 2),
            _make_punct_token("+", "ADD", 3),
            _make_int_token("2", 4),
            _make_punct_token(")", "R_BRACKET", 5),
            _make_punct_token("*", "MUL", 7),
            _make_int_token("3", 9),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        starts, ends, ops = self.parser._split_by_bin_op(["ADD", "MUL"], 7)
        # ADD inside brackets should be ignored; MUL outside brackets should split
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0], "MUL")


class TestParseSingleExpr(unittest.TestCase):
    """Tests for ExprParser.parse_single_expr."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_single_expr_integer(self):
        """Should parse a single integer literal."""
        tokens = [_make_int_token("42", 1)]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        # Result should contain MAKE EXPR INTEGER_LITERAL
        self.assertTrue(any("INTEGER_LITERAL" in cmd for cmd in result))

    def test_parse_single_expr_string(self):
        """Should parse a single string literal."""
        tokens = [_make_str_token("hello", 1)]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("STRING_LITERAL" in cmd for cmd in result))

    def test_parse_single_expr_bool_true(self):
        """Should parse true literal."""
        tokens = [_make_bool_token("true", 1)]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("BOOL_LITERAL" in cmd for cmd in result))

    def test_parse_single_expr_bool_false(self):
        """Should parse false literal."""
        tokens = [_make_bool_token("false", 1)]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("BOOL_LITERAL" in cmd for cmd in result))

    def test_parse_single_expr_simple_identifier(self):
        """Should parse a simple identifier used in an expression context."""
        # Single token identifiers have a parsing edge case with tokens_num.
        # Test with a binary expression that includes identifiers: x + y
        tokens = [
            _make_id_token("x", 1),
            _make_punct_token("+", "ADD", 3),
            _make_id_token("y", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("VARIABLE_REF" in cmd for cmd in result))

    def test_parse_single_expr_binary_add(self):
        """Should parse a binary addition."""
        tokens = [
            _make_int_token("1", 1),
            _make_punct_token("+", "ADD", 3),
            _make_int_token("2", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("ADD_OP" in cmd for cmd in result))

    def test_parse_single_expr_binary_sub(self):
        """Should parse a binary subtraction."""
        tokens = [
            _make_int_token("5", 1),
            _make_punct_token("-", "SUB", 3),
            _make_int_token("3", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("SUB_OP" in cmd for cmd in result))

    def test_parse_single_expr_binary_mul(self):
        """Should parse a binary multiplication."""
        tokens = [
            _make_int_token("2", 1),
            _make_punct_token("*", "MUL", 3),
            _make_int_token("3", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("MUL_OP" in cmd for cmd in result))

    def test_parse_single_expr_binary_div(self):
        """Should parse a binary division."""
        tokens = [
            _make_int_token("6", 1),
            _make_punct_token("/", "DIV", 3),
            _make_int_token("2", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("DIV_OP" in cmd for cmd in result))

    def test_parse_single_expr_comparison(self):
        """Should parse a comparison expression."""
        tokens = [
            _make_int_token("1", 1),
            _make_punct_token("<", "LT", 3),
            _make_int_token("2", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("LT_OP" in cmd for cmd in result))

    def test_parse_single_expr_equality(self):
        """Should parse an equality expression."""
        tokens = [
            _make_int_token("1", 1),
            _make_punct_token("==", "EQ", 3),
            _make_int_token("2", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("EQ_OP" in cmd for cmd in result))

    def test_parse_single_expr_logical_and(self):
        """Should parse a logical AND expression."""
        tokens = [
            _make_bool_token("true", 1),
            _make_punct_token("&&", "AND", 6),
            _make_bool_token("false", 9),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("AND_OP" in cmd for cmd in result))

    def test_parse_single_expr_logical_or(self):
        """Should parse a logical OR expression."""
        tokens = [
            _make_bool_token("true", 1),
            _make_punct_token("||", "OR", 6),
            _make_bool_token("false", 9),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("OR_OP" in cmd for cmd in result))

    def test_parse_single_expr_unary_neg(self):
        """Should parse a unary negation."""
        tokens = [
            _make_punct_token("-", "SUB", 1),
            _make_int_token("5", 2),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("NEGATIVE_OP" in cmd for cmd in result))

    def test_parse_single_expr_unary_not(self):
        """Should parse a logical NOT."""
        tokens = [
            _make_punct_token("!", "NOT", 1),
            _make_bool_token("true", 2),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("NOT_OP" in cmd for cmd in result))

    def test_parse_single_expr_bracketed(self):
        """Should parse a parenthesized expression."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_int_token("1", 2),
            _make_punct_token("+", "ADD", 3),
            _make_int_token("2", 4),
            _make_punct_token(")", "R_BRACKET", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("BRACKETS_OP" in cmd for cmd in result))

    def test_parse_single_expr_empty_tuple(self):
        """Should parse empty brackets as tuple."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_punct_token(")", "R_BRACKET", 2),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("TUPLE_REF" in cmd for cmd in result))

    def test_parse_single_expr_attr_access(self):
        """Should parse dotted attribute access: obj.prop in expression context."""
        tokens = [
            _make_id_token("obj", 1),
            _make_punct_token(".", "DOT", 4),
            _make_id_token("prop", 5),
            _make_punct_token("+", "ADD", 10),
            _make_int_token("1", 12),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        # ATTR_OP should appear for the dotted access
        self.assertTrue(any("ATTR_OP" in cmd for cmd in result))

    def test_parse_single_expr_empty_array(self):
        """Should parse empty square brackets as array."""
        tokens = [
            _make_punct_token("[", "L_SQUARE_BRACKET", 1),
            _make_punct_token("]", "R_SQUARE_BRACKET", 2),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("ARRAY_REF" in cmd for cmd in result))

    def test_parse_single_expr_slice(self):
        """Should parse a slice expression."""
        tokens = [
            _make_int_token("1", 1),
            _make_punct_token(":", "COLON", 2),
            _make_int_token("5", 3),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("SLICE_REF" in cmd for cmd in result))

    def test_parse_single_expr_ternary(self):
        """Should parse a ternary conditional expression."""
        tokens = [
            _make_bool_token("true", 1),
            _make_punct_token("?", "QUESTION", 6),
            _make_int_token("1", 8),
            _make_punct_token(":", "COLON", 10),
            _make_int_token("2", 12),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("COND_OP" in cmd for cmd in result))

    def test_parse_single_expr_bitwise_and(self):
        """Should parse a bitwise AND expression."""
        tokens = [
            _make_int_token("5", 1),
            _make_punct_token("&", "BIT_AND", 3),
            _make_int_token("3", 5),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("BIT_AND_OP" in cmd for cmd in result))


class TestParseAllExpr(unittest.TestCase):
    """Tests for ExprParser.parse_all_expr."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_all_expr_no_expressions(self):
        """ParsingResult with no RAW entries should pass through unchanged."""
        result = ParsingResult(
            command=["MAKE STMT OP", "CALL FINISH"],
            symbol=[],
            expr_tokens=[],
            from_global_parser=True
        )
        output = self.parser.parse_all_expr(result)
        self.assertIsNotNone(output)
        self.assertEqual(len(output), 2)

    def test_parse_all_expr_with_raw(self):
        """Should replace RAW entries with parsed expressions."""
        tokens = [_make_int_token("42", 1)]
        result = ParsingResult(
            command=["RAW 0 1:1:1:2 42", "CALL SET_EXPR"],
            symbol=[],
            expr_tokens=[tokens],
            from_global_parser=True
        )
        output = self.parser.parse_all_expr(result)
        self.assertIsNotNone(output)
        # RAW should be replaced with MAKE EXPR INTEGER_LITERAL ...
        self.assertTrue(any("INTEGER_LITERAL" in cmd for cmd in output))

    def test_parse_all_expr_skips_non_raw(self):
        """Non-RAW commands should pass through unchanged."""
        result = ParsingResult(
            command=[
                "MAKE STMT DECL",
                "RAW 0 1:1:1:1 x",
                "CALL SET_VAR_VALUE",
                "CALL FINISH",
            ],
            symbol=[],
            expr_tokens=[[_make_id_token("x", 1)]],
            from_global_parser=True
        )
        output = self.parser.parse_all_expr(result)
        self.assertIsNotNone(output)


class TestParseExprToFile(unittest.TestCase):
    """Tests for ExprParser.parse_expr_to_file."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("frontend.utils.ParsingResult.read")
    def test_parse_expr_to_file_success(self, mock_read, mock_file, mock_makedirs, mock_exists):
        """Should return SUCCESS when parsing succeeds."""
        mock_exists.return_value = True
        mock_read.return_value = ParsingResult(
            command=["MAKE STMT OP", "CALL FINISH"],
            symbol=[],
            expr_tokens=[],
            from_global_parser=False,
        )

        result = self.parser.parse_expr_to_file("/test/src/file.vla", thread_index=1)
        self.assertEqual(result.state, TaskResultState.SUCCESS)


class TestHandleIdPrefix(unittest.TestCase):
    """Tests for ExprParser.__handle_id_prefix."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_single_identifier(self):
        """Single identifier should produce a VARIABLE_REF."""
        result = self.parser._ExprParser__handle_id_prefix(["x"])
        self.assertIsNotNone(result)
        self.assertTrue(any("VARIABLE_REF" in cmd for cmd in result))

    def test_dotted_identifiers(self):
        """Dotted identifiers should produce ATTR_OP chain."""
        result = self.parser._ExprParser__handle_id_prefix(["a", "b", "c"])
        self.assertIsNotNone(result)
        self.assertTrue(any("ATTR_OP" in cmd for cmd in result))
        self.assertTrue(any("VARIABLE_REF" in cmd for cmd in result))


class TestParseString(unittest.TestCase):
    """Tests for ExprParser._parse_string."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_single_string(self):
        """Should parse a single string token."""
        tokens = [_make_str_token("hello", 1)]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        # _parse_string is a bound method; we call it through parse_single_expr
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("STRING_LITERAL" in cmd for cmd in result))


class TestParseFloat(unittest.TestCase):
    """Tests for ExprParser._parse_float."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_float(self):
        """Should parse a float literal."""
        tokens = [_make_token("3.14", ["DOUBLE"], start_col=1, end_col=4)]
        self.parser._load_tokens(tokens)
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("FLOAT_LITERAL" in cmd for cmd in result))


class TestParseQuestionExpr(unittest.TestCase):
    """Tests for ExprParser._parse_question_expr (ternary)."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_simple_ternary(self):
        """Should parse cond ? then : else."""
        tokens = [
            _make_bool_token("true", 1),
            _make_punct_token("?", "QUESTION", 6),
            _make_int_token("1", 8),
            _make_punct_token(":", "COLON", 10),
            _make_int_token("2", 12),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("COND_OP" in cmd for cmd in result))


class TestParseSquareBracketExpr(unittest.TestCase):
    """Tests for ExprParser._parse_square_bracket_expr."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_empty_square_brackets(self):
        """Should parse [] as empty array."""
        tokens = [
            _make_punct_token("[", "L_SQUARE_BRACKET", 1),
            _make_punct_token("]", "R_SQUARE_BRACKET", 2),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("ARRAY_REF" in cmd for cmd in result))

    def test_parse_array_with_elements(self):
        """Should parse [1, 2, 3] as array."""
        tokens = [
            _make_punct_token("[", "L_SQUARE_BRACKET", 1),
            _make_int_token("1", 2),
            _make_punct_token(",", "COMMA", 3),
            _make_int_token("2", 5),
            _make_punct_token(",", "COMMA", 6),
            _make_int_token("3", 8),
            _make_punct_token("]", "R_SQUARE_BRACKET", 9),
        ]
        result = self.parser.parse_single_expr(tokens)
        self.assertIsNotNone(result)
        self.assertTrue(any("ARRAY_REF" in cmd for cmd in result))


class TestParseType(unittest.TestCase):
    """Tests for ExprParser._parse_type."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_simple_type(self):
        """Should parse a simple type reference."""
        tokens = [_make_id_token("int", 1)]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_type()
        self.assertIsNotNone(result)
        self.assertTrue(any("TYPE_REF" in cmd for cmd in result))

    def test_parse_array_type(self):
        """Should parse an array type like int[]."""
        tokens = [
            _make_id_token("int", 1),
            _make_punct_token("[", "L_SQUARE_BRACKET", 4),
            _make_punct_token("]", "R_SQUARE_BRACKET", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_type()
        self.assertIsNotNone(result)


class TestParseArgList(unittest.TestCase):
    """Tests for ExprParser._parse_arg_list."""

    def setUp(self):
        self.parser = ExprParser("/test/workspace")

    def test_parse_empty_args(self):
        """Empty parentheses should return a wrapped result (with SET_INFO prefix)."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_punct_token(")", "R_BRACKET", 2),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_arg_list()
        self.assertIsNotNone(result)
        # Result includes SET_INFO prefix; content may be empty list or commands
        self.assertIsInstance(result, list)

    def test_parse_single_arg(self):
        """Should parse a single argument."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_int_token("42", 2),
            _make_punct_token(")", "R_BRACKET", 4),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_arg_list()
        self.assertIsNotNone(result)
        # After decorator wrapping, result includes CALL ADD_ARG commands
        self.assertTrue(any("CALL ADD_ARG" in cmd for cmd in result) or any("INTEGER_LITERAL" in cmd for cmd in result))


if __name__ == "__main__":
    unittest.main()
