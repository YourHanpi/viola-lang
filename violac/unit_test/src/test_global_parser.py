# -*- coding: utf-8 -*-
"""Unit tests for the GlobalParser class in violac.src.frontend.global_parser."""

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
from utils.compiler_params import COMPILER_PARAMS
from frontend.global_parser import GlobalParser
from frontend.utils import ParsingResult, ParserGenericTable


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


def _make_kw_token(keyword: str, col: int = 1) -> Token:
    """Helper to create a keyword token."""
    return _make_token(keyword, [keyword.upper()], start_col=col, end_col=col + len(keyword) - 1)


def _make_punct_token(text: str, ptype: str, col: int = 1) -> Token:
    """Helper to create a punctuation token."""
    return _make_token(text, [ptype], start_col=col, end_col=col)


def _make_eof_token() -> Token:
    """Helper to create an EOF token."""
    return _make_token("", ["_EOF"])


class TestGlobalParserInit(unittest.TestCase):
    """Tests for GlobalParser.__init__."""

    def test_init_sets_workspace(self):
        """Should set the workspace path."""
        parser = GlobalParser("./test/workspace")
        self.assertEqual(parser._workspace, os.path.abspath("./test/workspace"))

    def test_init_initializes_empty_tokens(self):
        """Should initialize with empty token list."""
        parser = GlobalParser("/test/workspace")
        self.assertEqual(parser._tokens, [])
        self.assertEqual(parser._tokens_num, 0)
        self.assertEqual(parser._current, 0)

    def test_init_initializes_empty_structures(self):
        """Should initialize imports, symbol types, tasks as empty."""
        parser = GlobalParser("/test/workspace")
        self.assertEqual(parser._imports, {})
        self.assertEqual(parser._symbol_types, {})
        self.assertEqual(parser._tasks, [])
        self.assertEqual(parser._expr_count, 0)
        self.assertEqual(parser._expr_tokens, [])

    def test_init_creates_generic_table(self):
        """Should create a ParserGenericTable."""
        parser = GlobalParser("/test/workspace")
        self.assertIsInstance(parser._parser_generic_table, ParserGenericTable)

    def test_init_sets_source_info_to_viola_init(self):
        """Source info should be VIOLA_INIT initially."""
        parser = GlobalParser("/test/workspace")
        self.assertEqual(parser._src_info.path, "<viola_init>")


class TestGlobalParserTokenNavigation(unittest.TestCase):
    """Tests for token navigation methods (_next, _back, _get_current, etc.)."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")
        # Set up tokens: ID(x), ID(y), SEMICOLON, _EOF
        self.tokens = [
            _make_id_token("x", 1),
            _make_id_token("y", 2),
            _make_punct_token(";", "SEMICOLON", 3),
        ]
        self.parser._load_tokens(self.tokens)

    def test_load_tokens_appends_eof(self):
        """_load_tokens should append an EOF token."""
        self.assertEqual(len(self.parser._tokens), 4)  # 3 + EOF
        self.assertIn("_EOF", self.parser._tokens[-1].type)

    def test_get_current_returns_first_token(self):
        """_get_current should return the first non-blank token after _move_to_first_token."""
        self.parser._move_to_first_token()
        token = self.parser._get_current()
        self.assertEqual(token.text, "x")
        self.assertIn("IDENTIFIER", token.type)

    def test_match_type_positive(self):
        """_match_type should return True when type matches."""
        self.parser._move_to_first_token()
        self.assertTrue(self.parser._match_type("IDENTIFIER"))

    def test_match_type_negative(self):
        """_match_type should return False when type doesn't match."""
        self.parser._move_to_first_token()
        self.assertFalse(self.parser._match_type("SEMICOLON"))

    def test_match_types_positive(self):
        """_match_types should return True when any type matches."""
        self.parser._move_to_first_token()
        self.assertTrue(self.parser._match_types(["IDENTIFIER", "SEMICOLON"]))

    def test_match_types_negative(self):
        """_match_types should return False when no type matches."""
        self.parser._move_to_first_token()
        self.assertFalse(self.parser._match_types(["SEMICOLON", "FN"]))

    def test_next_advances_current(self):
        """_next should advance past blanks."""
        self.parser._move_to_first_token()
        self.parser._next()
        token = self.parser._get_current()
        self.assertEqual(token.text, "y")

    def test_next_to_specific_position(self):
        """_next_to should advance to a specific position."""
        self.parser._move_to_first_token()
        self.parser._next_to(2)
        token = self.parser._get_current()
        self.assertEqual(token.text, ";")

    def test_back_goes_to_previous_token(self):
        """_back should go back one step."""
        self.parser._move_to_first_token()
        self.parser._next()  # now at 'y'
        self.parser._back()
        token = self.parser._get_current()
        self.assertEqual(token.text, "x")

    def test_back_to_specific_position(self):
        """_back_to should go back to a specific position."""
        self.parser._move_to_first_token()
        self.parser._next_to(2)  # now at ';'
        self.parser._back_to(0)
        token = self.parser._get_current()
        self.assertEqual(token.text, "x")

    def test_next_no_skip_does_not_skip_blanks(self):
        """_next_no_skip should advance without skipping blanks."""
        # Add a blank token to test skipping behavior
        blank_token = Token(" ", ["_BLANK"], VIOLA_INIT.copy())
        tokens_with_blank = [
            _make_id_token("x", 1),
            blank_token,
            _make_id_token("y", 3),
        ]
        self.parser._load_tokens(tokens_with_blank)
        self.parser._move_to_first_token()
        self.parser._next_no_skip()  # moves to blank
        token = self.parser._get_current()
        self.assertIn("_BLANK", token.type)

    def test_collect_until_finds_end_token(self):
        """_collect_until should collect tokens until the end type."""
        tokens = [
            _make_id_token("a", 1),
            _make_punct_token("+", "ADD", 2),
            _make_id_token("b", 3),
            _make_punct_token(";", "SEMICOLON", 4),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        collected = self.parser._collect_until(["SEMICOLON"])
        self.assertIsNotNone(collected)
        self.assertEqual(len(collected), 3)  # a, +, b

    def test_filter_blank_removes_blanks_and_comments(self):
        """_filter_blank should remove blank and comment tokens."""
        tokens = [
            Token(" ", ["_BLANK"], VIOLA_INIT.copy()),
            _make_id_token("x", 1),
            Token("// comment", ["_COMMENT"], VIOLA_INIT.copy()),
            _make_id_token("y", 2),
        ]
        filtered = GlobalParser._filter_blank(tokens)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].text, "x")
        self.assertEqual(filtered[1].text, "y")

    def test_buffer_match_types_matching(self):
        """_buffer_match_types should return True when types match."""
        tokens = [
            _make_id_token("x", 1),
            _make_punct_token("=", "ASSIGN", 2),
        ]
        self.assertTrue(GlobalParser._buffer_match_types(tokens, ["IDENTIFIER", "ASSIGN"]))

    def test_buffer_match_types_not_matching_wrong_length(self):
        """_buffer_match_types should return False when lengths differ."""
        tokens = [_make_id_token("x", 1)]
        self.assertFalse(GlobalParser._buffer_match_types(tokens, ["IDENTIFIER", "ASSIGN"]))

    def test_buffer_match_types_not_matching_wrong_type(self):
        """_buffer_match_types should return False when types don't match."""
        tokens = [
            _make_id_token("x", 1),
            _make_id_token("y", 2),
        ]
        self.assertFalse(GlobalParser._buffer_match_types(tokens, ["IDENTIFIER", "ASSIGN"]))


class TestGlobalParserChangeTokens(unittest.TestCase):
    """Tests for _change_tokens method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_change_tokens_replaces_range(self):
        """_change_tokens should replace a range with a single token and blanks."""
        tokens = [
            _make_id_token("a", 1),
            _make_id_token("b", 2),
            _make_id_token("c", 3),
            _make_id_token("d", 4),
        ]
        self.parser._load_tokens(tokens)
        new_token = _make_id_token("X", 1)
        self.parser._change_tokens(new_token, 1, 3)
        self.assertEqual(self.parser._tokens[0].text, "a")
        self.assertEqual(self.parser._tokens[1].text, "X")
        self.assertIn("_BLANK", self.parser._tokens[2].type)
        self.assertEqual(self.parser._tokens[3].text, "d")


class TestGlobalParserNameParsing(unittest.TestCase):
    """Tests for _parse_name method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_simple_name(self):
        """Should parse a single identifier."""
        tokens = [
            _make_id_token("foo", 1),
            _make_punct_token(";", "SEMICOLON", 4),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        name = self.parser._parse_name()
        self.assertEqual(name, "foo")

    def test_parse_dotted_name(self):
        """Should parse a dotted name like foo.bar.baz."""
        tokens = [
            _make_id_token("foo", 1),
            _make_punct_token(".", "DOT", 4),
            _make_id_token("bar", 5),
            _make_punct_token(".", "DOT", 8),
            _make_id_token("baz", 9),
            _make_punct_token(";", "SEMICOLON", 12),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        name = self.parser._parse_name()
        self.assertEqual(name, "foo.bar.baz")

    def test_parse_name_stops_at_non_identifier(self):
        """Should stop parsing when a non-identifier, non-dot token is found."""
        tokens = [
            _make_id_token("foo", 1),
            _make_punct_token(";", "SEMICOLON", 4),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        name = self.parser._parse_name()
        self.assertEqual(name, "foo")


class TestGlobalParserPrefixParsing(unittest.TestCase):
    """Tests for _parse_prefixes method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_prefixes_empty(self):
        """Should return empty list when no prefixes match."""
        tokens = [
            _make_id_token("fn", 1),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        prefixes = self.parser._parse_prefixes(["EXPORT", "STATIC"])
        self.assertEqual(prefixes, [])

    def test_parse_prefixes_method_exists(self):
        """_parse_prefixes is callable and returns a list."""
        tokens = [
            _make_kw_token("export", 1),
            _make_kw_token("fn", 8),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        prefixes = self.parser._parse_prefixes(["EXPORT", "STATIC"])
        self.assertIsInstance(prefixes, list)


class TestGlobalParserIdListParsing(unittest.TestCase):
    """Tests for _parse_id_list method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_id_list_single(self):
        """Should parse a single identifier."""
        tokens = [
            _make_id_token("x", 1),
            _make_punct_token(";", "SEMICOLON", 2),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_id_list()
        self.assertEqual(result, ["x"])

    def test_parse_id_list_multiple(self):
        """Should parse comma-separated identifiers."""
        tokens = [
            _make_id_token("x", 1),
            _make_punct_token(",", "COMMA", 2),
            _make_id_token("y", 4),
            _make_punct_token(",", "COMMA", 5),
            _make_id_token("z", 7),
            _make_punct_token(";", "SEMICOLON", 8),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_id_list()
        self.assertEqual(result, ["x", "y", "z"])


class TestGlobalParserAddParsingSlice(unittest.TestCase):
    """Tests for _add_parsing_slice method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_add_parsing_slice_increments_count(self):
        """Should increment expr_tokens and return RAW string."""
        tokens = [
            _make_id_token("x", 1),
            _make_punct_token("+", "ADD", 3),
            _make_id_token("y", 5),
        ]
        result = self.parser._add_parsing_slice(tokens)
        self.assertEqual(len(self.parser._expr_tokens), 1)
        self.assertTrue(result.startswith("RAW 0 "))

    def test_add_parsing_slice_second_call(self):
        """Second call should use index 1."""
        self.parser._add_parsing_slice([_make_id_token("a")])
        result = self.parser._add_parsing_slice([_make_id_token("b")])
        self.assertTrue(result.startswith("RAW 1 "))


class TestGlobalParserAddTask(unittest.TestCase):
    """Tests for _add_task method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_add_task_appends_command(self):
        """Should append to the tasks list."""
        self.parser._add_task(["violac", "lex", "/test/file.vla"])
        self.assertEqual(len(self.parser._tasks), 1)
        self.assertEqual(self.parser._tasks[0], ["violac", "lex", "/test/file.vla"])


class TestGlobalParserGetImportPrefix(unittest.TestCase):
    """Tests for _get_import_prefix method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_no_match_returns_original(self):
        """Should return original list when no import matches."""
        result = self.parser._get_import_prefix(["foo", "bar"])
        self.assertEqual(result, ["foo", "bar"])

    def test_match_replaces_prefix(self):
        """Should replace matching prefix with full import path."""
        self.parser._imports["foo"] = "pkg.foo"
        result = self.parser._get_import_prefix(["foo", "bar"])
        self.assertEqual(result, ["pkg.foo", "bar"])

    def test_longest_match_wins(self):
        """Should use the longest matching prefix."""
        self.parser._imports["foo"] = "pkg.foo"
        self.parser._imports["foo.bar"] = "pkg.foo.bar"
        result = self.parser._get_import_prefix(["foo", "bar", "baz"])
        self.assertEqual(result, ["pkg.foo.bar", "baz"])


class TestGlobalParserCondExpr(unittest.TestCase):
    """Tests for _parse_cond_expr method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_simple_cond_expr(self):
        """Should parse a simple parenthesized condition."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_id_token("x", 2),
            _make_punct_token(")", "R_BRACKET", 3),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_cond_expr()
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("RAW "))

    def test_parse_cond_expr_nested_brackets(self):
        """Should handle nested brackets in condition."""
        tokens = [
            _make_punct_token("(", "L_BRACKET", 1),
            _make_punct_token("(", "L_BRACKET", 2),
            _make_id_token("x", 3),
            _make_punct_token(")", "R_BRACKET", 4),
            _make_punct_token(")", "R_BRACKET", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_cond_expr()
        self.assertIsNotNone(result)


class TestGlobalParserTypeParsing(unittest.TestCase):
    """Tests for _parse_type method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_simple_type_name(self):
        """Should parse a simple type name like 'int'."""
        tokens = [
            _make_id_token("int", 1),
            _make_id_token("x", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_type()
        self.assertEqual(result, "int")

    def test_parse_generic_type(self):
        """Should parse a generic type like 'List::<T>'."""
        tokens = [
            _make_id_token("List", 1),
            _make_punct_token("::<", "GENERIC_START", 5),
            _make_id_token("int", 8),
            _make_punct_token(">", "GT", 11),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_type()
        self.assertIsNotNone(result)
        self.assertIn("List", result)

    def test_parse_array_type(self):
        """Should parse an array type like 'int[]'."""
        tokens = [
            _make_id_token("int", 1),
            _make_punct_token("[", "L_SQUARE_BRACKET", 4),
            _make_punct_token("]", "R_SQUARE_BRACKET", 5),
        ]
        self.parser._load_tokens(tokens)
        self.parser._move_to_first_token()
        result = self.parser._parse_type()
        self.assertIsNotNone(result)
        self.assertIn("int", result)


class TestGlobalParserParse(unittest.TestCase):
    """Tests for the main parse method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    def test_parse_method_exists_and_accepts_tokens(self):
        """parse() should be callable with a token list."""
        tokens = [
            _make_kw_token("import", 1),
            _make_id_token("std", 8),
            _make_punct_token(";", "SEMICOLON", 11),
        ]
        # parse() is complex and requires real filesystem for imports;
        # we verify it handles errors gracefully
        with patch.object(GlobalParser, "_find_import", return_value=None):
            with patch.object(GlobalParser, "_handle_error_from_import"):
                result = self.parser.parse(tokens)
                # Should return None when tasks are pending
                self.assertIsNone(result)


class TestGlobalParserFileOperations(unittest.TestCase):
    """Tests for file-related operations."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    @patch("os.path.exists")
    def test_check_file_lock_exists(self, mock_exists):
        """_check_file_lock should return os.path.exists result."""
        mock_exists.return_value = True
        self.assertTrue(GlobalParser._check_file_lock("/test/file"))

        mock_exists.return_value = False
        self.assertFalse(GlobalParser._check_file_lock("/test/file"))

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_set_file_lock_creates_lock_file(self, mock_file, mock_makedirs):
        """_set_file_lock should create a lock file."""
        GlobalParser._set_file_lock("/test/file")
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()

    @patch("os.remove")
    def test_remove_file_lock_removes_lock_file(self, mock_remove):
        """_remove_file_lock should remove the lock file."""
        GlobalParser._remove_file_lock("/test/file")
        mock_remove.assert_called_once()


class TestGlobalParserParseFromFile(unittest.TestCase):
    """Tests for parse_from_file method."""

    def setUp(self):
        self.parser = GlobalParser("/test/workspace")

    @patch("os.path.exists")
    @patch("frontend.global_parser.GlobalParser._set_file_lock")
    @patch("frontend.global_parser.GlobalParser._remove_file_lock")
    def test_parse_from_file_no_tokens_adds_task(self, mock_remove, mock_set, mock_exists):
        """When no token file exists, should add a lex task."""
        mock_exists.return_value = False
        result = self.parser.parse_from_file("/test/cache/file")
        self.assertIsNone(result)
        self.assertGreater(len(self.parser._tasks), 0)

    @patch("os.path.exists")
    @patch("frontend.global_parser.GlobalParser._set_file_lock")
    @patch("frontend.global_parser.GlobalParser._remove_file_lock")
    @patch("frontend.utils.TokenStreamIO.read")
    def test_parse_from_file_with_tokens(self, mock_read, mock_remove, mock_set, mock_exists):
        """When token file exists, should parse it."""
        mock_exists.return_value = True
        mock_read.return_value = []  # empty tokens

        result = self.parser.parse_from_file("./test/cache/file")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ParsingResult)


class TestGlobalParserParseToFile(unittest.TestCase):
    """Tests for parse_to_file method."""

    def setUp(self):
        self.parser = GlobalParser("./test/workspace")

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("frontend.global_parser.GlobalParser._set_file_lock")
    @patch("frontend.global_parser.GlobalParser._remove_file_lock")
    @patch("frontend.utils.TokenStreamIO.read")
    def test_parse_to_file_success(self, mock_read, mock_remove, mock_set, mock_makedirs, mock_exists):
        """Should return SUCCESS when parsing succeeds."""
        mock_exists.return_value = True
        mock_read.return_value = []

        result = self.parser.parse_to_file("./test/src/file.vla", thread_index=1)
        self.assertEqual(result.state, TaskResultState.SUCCESS)


if __name__ == "__main__":
    os.chdir("./violac/unit_test")
    unittest.main()
