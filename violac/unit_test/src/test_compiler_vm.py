# -*- coding: utf-8 -*-
"""Unit tests for the CompilerVM class in violac.src.backend.compiler_vm."""

import sys
import os
import unittest
from unittest.mock import patch, mock_open, MagicMock, PropertyMock, call

# Add source path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "violac", "src")))

# Mock the global logger controller to prevent file-handler errors
import utils.logger as logger_module
_mock_controller = MagicMock()
_mock_controller.log_level = 100  # Higher than all levels, suppresses output
logger_module.LOGGER_CONTROLLER = _mock_controller

from backend.compiler_vm import CompilerVM, _ExecMode, _ScopeCount
from backend.compiling_item import CompilingItem
from backend import definition as definition
from backend import expression as expression
from backend import project as project
from backend import statement as statement
from backend import symbol as symbol
from utils.source_info import SourceInfo, VIOLA_INIT
from utils.compiler_params import COMPILER_PARAMS
from utils.task import TaskResult, TaskResultState
from utils.compiler_exceptions import InternalCompilerException


class TestCompilerVMInit(unittest.TestCase):
    """Tests for CompilerVM.__init__."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"

    def test_init_sets_project(self):
        """Should store the project reference."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._project, self.mock_project)

    def test_init_sets_output_path(self):
        """Should set output_path from project."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._output_path, "/test/output")

    def test_init_sets_workspace(self):
        """Should set workspace from project root_path."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._workspace, "/test/workspace")

    def test_init_starts_in_sq_mode(self):
        """Should start in statement (SQ) execution mode."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._exec_mode_stack, [_ExecMode.SQ])

    def test_init_starts_with_hold_scope(self):
        """Should start with HOLD scope count."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._scope_count_stack, [_ScopeCount.HOLD])

    def test_init_sets_default_source_info(self):
        """Source info should be VIOLA_INIT initially."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._src_info.path, "<viola_init>")

    def test_init_creates_symbol_table(self):
        """Should create a SymbolTable."""
        vm = CompilerVM(self.mock_project)
        self.assertIsNotNone(vm._symbol_table)
        self.assertIsInstance(vm._symbol_table, symbol.SymbolTable)

    def test_init_creates_var_state_table(self):
        """Should create a VariableStateTable."""
        vm = CompilerVM(self.mock_project)
        self.assertIsNotNone(vm._var_state_table)
        self.assertIsInstance(vm._var_state_table, symbol.VariableStateTable)

    def test_init_has_empty_stack(self):
        """Should start with an empty compilation stack."""
        vm = CompilerVM(self.mock_project)
        self.assertEqual(vm._stack, [])

    def test_init_current_class_is_none(self):
        """Should start with no current class."""
        vm = CompilerVM(self.mock_project)
        self.assertIsNone(vm._current_class)

    def test_init_has_all_maker_dicts(self):
        """Should initialize DEF, EXPR, and STMT maker dicts."""
        vm = CompilerVM(self.mock_project)
        self.assertIsInstance(vm._DEF_MAKER_DICT, dict)
        self.assertIsInstance(vm._EXPR_MAKER_DICT, dict)
        self.assertIsInstance(vm._STMT_MAKER_DICT, dict)
        self.assertIsInstance(vm._CALLER_DICT, dict)

    def test_init_def_maker_has_expected_keys(self):
        """DEF maker dict should contain expected definition types."""
        vm = CompilerVM(self.mock_project)
        expected_keys = ["CONST", "SQ", "CONSTRUCTOR", "DESTRUCTOR", "FN",
                         "C_PART_SQ", "CLASS", "FROM_IMPORT", "IMPORT", "ENUM"]
        for key in expected_keys:
            self.assertIn(key, vm._DEF_MAKER_DICT, f"Missing DEF maker: {key}")

    def test_init_expr_maker_has_expected_keys(self):
        """EXPR maker dict should contain expected expression types."""
        vm = CompilerVM(self.mock_project)
        expected_keys = [
            "C", "UNPACK", "VARIABLE_REF", "STRING_LITERAL", "BOOL_LITERAL",
            "INTEGER_LITERAL", "FLOAT_LITERAL", "SLICE_REF", "ARRAY_REF",
            "TUPLE_REF", "AUTO_TYPE_REF", "FUNCTION_TYPE_REF", "TYPE_REF",
            "CLASS_REF", "ATTR_OP", "CALL_OP",
        ]
        for key in expected_keys:
            self.assertIn(key, vm._EXPR_MAKER_DICT, f"Missing EXPR maker: {key}")

    def test_init_expr_maker_has_operators(self):
        """EXPR maker dict should contain operator expression types."""
        vm = CompilerVM(self.mock_project)
        operator_keys = [
            "ADD_OP", "SUB_OP", "MUL_OP", "DIV_OP", "MOD_OP", "MATMUL_OP",
            "POW_OP", "LSHIFT_OP", "RSHIFT_OP", "BIT_AND_OP", "BIT_OR_OP",
            "BIT_XOR_OP", "BIT_NOT_OP", "EQ_OP", "NEQ_OP", "LT_OP", "LE_OP",
            "GT_OP", "GE_OP", "NOT_OP", "AND_OP", "OR_OP",
            "POSITIVE_OP", "NEGATIVE_OP", "ITEM_OP", "BRACKETS_OP", "COND_OP",
            "UPDATE", "CAST_OP", "CLOSURE", "GENERIC_CALL",
        ]
        for key in operator_keys:
            self.assertIn(key, vm._EXPR_MAKER_DICT, f"Missing EXPR maker: {key}")

    def test_init_stmt_maker_has_expected_keys(self):
        """STMT maker dict should contain expected statement types."""
        vm = CompilerVM(self.mock_project)
        expected_keys = [
            "DECL", "ASSIGN", "OP", "RETURN", "THROW", "C",
            "IF", "ELIF", "ELSE", "TRY", "CATCH", "FINALLY",
            "TYPE_DEF", "BLOCK",
        ]
        for key in expected_keys:
            self.assertIn(key, vm._STMT_MAKER_DICT, f"Missing STMT maker: {key}")

    def test_init_caller_dict_has_expected_keys(self):
        """CALLER dict should contain expected caller commands."""
        vm = CompilerVM(self.mock_project)
        expected_keys = [
            "ADD_ARG", "ADD_DEF", "ADD_ENUM", "ADD_ITEM", "ADD_METHOD",
            "ADD_PROP", "ADD_STATIC_PROP", "ADD_STMT", "ADD_TEXT",
            "ADD_TYPE", "ADD_TYPE_ARG", "ADD_VALUE", "ADD_VAR",
            "ADD_VAR_NAME", "AS_ASYNC", "FINISH", "FINISH_GENERIC",
            "SET_ATTR", "SET_ARG_TYPES", "SET_CALLER", "SET_COND_EXPR",
            "SET_DEF", "SET_END", "SET_EXCEPT_DECL", "SET_EXPR",
            "SET_EXPR_COND", "SET_EXPR_ELSE", "SET_EXPR_LEFT",
            "SET_EXPR_RIGHT", "SET_EXPR_THEN", "SET_FUNC",
            "SET_GENERIC_EXPR", "SET_RETURN_TYPES", "SET_SRC_EXPR",
            "SET_START", "SET_STEP", "SET_STMT", "SET_TYPE",
            "SET_VARS", "SET_VAR_VALUE",
        ]
        for key in expected_keys:
            self.assertIn(key, vm._CALLER_DICT, f"Missing CALLER: {key}")


class TestExecModeAndScopeCount(unittest.TestCase):
    """Tests for _ExecMode and _ScopeCount enums."""

    def test_exec_mode_values(self):
        """Should have correct enum values."""
        self.assertEqual(_ExecMode.SQ.value, 0)
        self.assertEqual(_ExecMode.FN.value, 1)

    def test_scope_count_values(self):
        """Should have correct enum values."""
        self.assertEqual(_ScopeCount.HOLD.value, 0)
        self.assertEqual(_ScopeCount.INC.value, 1)


class TestCompilerVMCheckSkip(unittest.TestCase):
    """Tests for CompilerVM._check_skip static method."""

    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_check_skip_when_header_newer(self, mock_getmtime, mock_exists):
        """Should return True when header is newer than source."""
        mock_exists.return_value = True
        mock_getmtime.side_effect = [200, 100]  # header(200) >= source(100)

        result = CompilerVM._check_skip("/test/src.vla", "/test/output/src")
        self.assertTrue(result)

    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_check_skip_when_source_newer(self, mock_getmtime, mock_exists):
        """Should return False when source is newer than header."""
        mock_exists.return_value = True
        mock_getmtime.side_effect = [100, 200]  # header(100) < source(200)

        result = CompilerVM._check_skip("/test/src.vla", "/test/output/src")
        self.assertFalse(result)

    @patch("os.path.exists")
    def test_check_skip_no_header(self, mock_exists):
        """Should return False when header doesn't exist."""
        mock_exists.return_value = False

        result = CompilerVM._check_skip("/test/src.vla", "/test/output/src")
        self.assertFalse(result)


class TestCompilerVMExecLine(unittest.TestCase):
    """Tests for CompilerVM._exec_line method."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    def test_exec_line_empty(self):
        """Empty or whitespace-only lines should be ignored."""
        self.vm._exec_line("")
        self.vm._exec_line("   ")
        # Should not raise any exception

    def test_exec_line_set_info(self):
        """SET_INFO should update source info."""
        self.vm._exec_line("SET_INFO 1 1 1 5 hello")
        self.assertEqual(self.vm._src_info.location_tuple, (1, 1, 1, 5))
        self.assertEqual(self.vm._src_info.src_text, "hello")

    def test_exec_line_unknown_command_raises(self):
        """Unknown command should raise InternalCompilerException."""
        with self.assertRaises(InternalCompilerException):
            self.vm._exec_line("UNKNOWN_CMD arg1 arg2")

    def test_exec_line_make_def_const(self):
        """MAKE DEF CONST should push to stack and bind parent."""
        # Set up stack with a parent item
        mock_parent = MagicMock(spec=CompilingItem)
        self.vm._stack.append(mock_parent)
        # Push a SourceFile-like item for the CONST to bind to
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.append(mock_src_file)

        # We need the stack to have items first
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)
        # Push a dummy that serves as parent
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE DEF CONST")
        self.assertGreater(len(self.vm._stack), 2)

    def test_exec_line_make_expr_int_literal(self):
        """MAKE EXPR INTEGER_LITERAL should push an expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR INTEGER_LITERAL 42 INT32")
        self.assertGreater(len(self.vm._stack), 1)

    def test_exec_line_make_expr_string_literal(self):
        """MAKE EXPR STRING_LITERAL should push an expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR STRING_LITERAL hello world")
        self.assertGreater(len(self.vm._stack), 1)

    def test_exec_line_make_expr_bool_literal(self):
        """MAKE EXPR BOOL_LITERAL should push an expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR BOOL_LITERAL true")
        self.assertGreater(len(self.vm._stack), 1)

    def test_exec_line_make_stmt_return(self):
        """MAKE STMT RETURN should push a statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT RETURN")
        self.assertGreater(len(self.vm._stack), 1)

    def test_exec_line_make_invalid_category(self):
        """Invalid MAKE category should raise InternalCompilerException."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)
        # Need two items on stack for bind_parent
        self.vm._stack.append(mock_src_file)

        with self.assertRaises(InternalCompilerException):
            self.vm._exec_line("MAKE INVALID something")

    def test_exec_line_call(self):
        """CALL command should dispatch to caller dict."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        # CALL ADD_DEF requires a Definition on top and SourceFile below
        mock_def = MagicMock(spec=definition.Definition)
        self.vm._stack.append(mock_src_file)
        self.vm._stack.append(mock_def)

        self.vm._exec_line("CALL ADD_DEF")
        # Should succeed without error
        self.assertLess(len(self.vm._stack), 3)  # definition was popped


class TestCompilerVMMake(unittest.TestCase):
    """Tests for CompilerVM._make method (using mocked symbol table)."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)
        # Mock the symbol table to accept lookups without error
        self.vm._symbol_table = MagicMock()
        self.vm._symbol_table.namespace = "test"
        self.vm._var_state_table = MagicMock()

    def test_make_stmt_return(self):
        """MAKE STMT RETURN should push a statement onto the stack."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        initial_stack_len = len(self.vm._stack)
        self.vm._exec_line("MAKE STMT RETURN")
        self.assertGreater(len(self.vm._stack), initial_stack_len)

    def test_make_stmt_decl(self):
        """MAKE STMT DECL should create a declaration statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT DECL")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_stmt_assign(self):
        """MAKE STMT ASSIGN should create an assignment statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT ASSIGN")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_stmt_if(self):
        """MAKE STMT IF should create an if statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT IF")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_stmt_block(self):
        """MAKE STMT BLOCK should create a block statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT BLOCK")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_stmt_try(self):
        """MAKE STMT TRY should create a try statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT TRY")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_stmt_catch(self):
        """MAKE STMT CATCH should create a catch statement."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT CATCH")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_expr_add_op(self):
        """MAKE EXPR ADD_OP should push an AddOp expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR ADD_OP")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_expr_eq_op(self):
        """MAKE EXPR EQ_OP should push an EqualOp expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR EQ_OP")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_expr_not_op(self):
        """MAKE EXPR NOT_OP should push a LogicalNotOp expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR NOT_OP")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_expr_bool_literal(self):
        """MAKE EXPR BOOL_LITERAL should push a BoolLiteral expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR BOOL_LITERAL true")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_expr_string_literal(self):
        """MAKE EXPR STRING_LITERAL should push a StringLiteral expression."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE EXPR STRING_LITERAL hello")
        self.assertGreater(len(self.vm._stack), 1)

    def test_make_binds_parent(self):
        """After MAKE, the new item should bind to its parent in the stack."""
        mock_parent = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock(spec=project.SourceFile))  # bottom
        self.vm._stack.append(mock_parent)  # parent

        self.vm._exec_line("MAKE STMT RETURN")
        self.assertGreater(len(self.vm._stack), 2)


class TestCompilerVMSetInfo(unittest.TestCase):
    """Tests for CompilerVM._set_info method."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    def test_set_info_updates_location(self):
        """Should update source info location."""
        self.vm._set_info(["SET_INFO", "1", "1", "1", "5", "hello", "world"])
        self.assertEqual(self.vm._src_info.location_tuple, (1, 1, 1, 5))

    def test_set_info_updates_text(self):
        """Should update source text."""
        self.vm._set_info(["SET_INFO", "2", "1", "2", "5", "foo", "bar"])
        self.assertEqual(self.vm._src_info.src_text, "foo bar")


class TestCompilerVMCallerDict(unittest.TestCase):
    """Tests for various CALL commands in the caller dict."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    def test_call_add_def(self):
        """CALL ADD_DEF should add a definition to source file."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        mock_def = MagicMock(spec=definition.Definition)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)
        self.vm._stack.append(mock_def)

        self.vm._exec_line("CALL ADD_DEF")
        mock_src_file.add_def.assert_called_once_with(mock_def)
        self.assertEqual(len(self.vm._stack), 1)  # definition popped

    def test_call_add_stmt(self):
        """CALL ADD_STMT should add a statement to a block or function."""
        mock_sq_def = MagicMock(spec=definition.SqDef)
        mock_ret_stmt = MagicMock(spec=statement.ReturnStmt)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())  # bottom
        self.vm._stack.append(mock_sq_def)
        self.vm._stack.append(mock_ret_stmt)

        self.vm._exec_line("CALL ADD_STMT")
        mock_sq_def.add_stmt.assert_called_once_with(mock_ret_stmt)
        self.assertEqual(len(self.vm._stack), 2)  # statement popped

    def test_call_set_expr(self):
        """CALL SET_EXPR should set expression on an operator or cast."""
        mock_op_stmt = MagicMock(spec=statement.OpStmt)
        mock_expr = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())  # bottom
        self.vm._stack.append(mock_op_stmt)
        self.vm._stack.append(mock_expr)

        self.vm._exec_line("CALL SET_EXPR")
        mock_op_stmt.set_expr.assert_called_once_with(mock_expr)
        self.assertEqual(len(self.vm._stack), 2)  # expression popped

    def test_call_set_expr_left(self):
        """CALL SET_EXPR_LEFT should set left operand on binary operator."""
        mock_bin_op = MagicMock(spec=expression.AddOp)
        mock_left = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_bin_op)
        self.vm._stack.append(mock_left)

        self.vm._exec_line("CALL SET_EXPR_LEFT")
        mock_bin_op.set_expr_left.assert_called_once_with(mock_left)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_expr_right(self):
        """CALL SET_EXPR_RIGHT should set right operand on binary operator."""
        mock_bin_op = MagicMock(spec=expression.AddOp)
        mock_right = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_bin_op)
        self.vm._stack.append(mock_right)

        self.vm._exec_line("CALL SET_EXPR_RIGHT")
        mock_bin_op.set_expr_right.assert_called_once_with(mock_right)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_func(self):
        """CALL SET_FUNC should set function on a call operation."""
        mock_call_op = MagicMock(spec=expression.CallOp)
        mock_func = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_call_op)
        self.vm._stack.append(mock_func)

        self.vm._exec_line("CALL SET_FUNC")
        mock_call_op.set_func.assert_called_once_with(mock_func)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_caller(self):
        """CALL SET_CALLER should set caller on an attribute operation."""
        mock_attr_op = MagicMock(spec=expression.AttrOp)
        mock_caller = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_attr_op)
        self.vm._stack.append(mock_caller)

        self.vm._exec_line("CALL SET_CALLER")
        mock_attr_op.set_caller.assert_called_once_with(mock_caller)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_attr(self):
        """CALL SET_ATTR should set attribute name on AttrOp."""
        mock_attr_op = MagicMock(spec=expression.AttrOp)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_attr_op)

        self.vm._exec_line("CALL SET_ATTR myProperty")
        mock_attr_op.set_attr.assert_called_once_with("myProperty")

    def test_call_add_text(self):
        """CALL ADD_TEXT should add text to C statement or expression."""
        mock_c_stmt = MagicMock(spec=statement.CStmt)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_c_stmt)

        self.vm._exec_line("CALL ADD_TEXT do {")
        mock_c_stmt.add_text.assert_called_once_with("do {")

    def test_call_finish(self):
        """CALL FINISH should call finish() on the top item."""
        mock_sq_def = MagicMock(spec=definition.SqDef)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_sq_def)

        self.vm._exec_line("CALL FINISH")
        mock_sq_def.finish.assert_called_once()

    def test_call_add_value(self):
        """CALL ADD_VALUE should add a value to array or tuple ref."""
        mock_array_ref = MagicMock(spec=expression.ArrayRef)
        mock_value = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_array_ref)
        self.vm._stack.append(mock_value)

        self.vm._exec_line("CALL ADD_VALUE")
        mock_array_ref.add_value.assert_called_once_with(mock_value)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_add_type(self):
        """CALL ADD_TYPE should add a type to tuple type ref."""
        mock_tuple_type = MagicMock(spec=expression.TupleTypeRef)
        mock_type = MagicMock(spec=expression.TypeRef)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_tuple_type)
        self.vm._stack.append(mock_type)

        self.vm._exec_line("CALL ADD_TYPE")
        mock_tuple_type.add_type.assert_called_once_with(mock_type)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_start(self):
        """CALL SET_START should set start on slice ref."""
        mock_slice = MagicMock(spec=expression.SliceRef)
        mock_start = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_slice)
        self.vm._stack.append(mock_start)

        self.vm._exec_line("CALL SET_START")
        mock_slice.set_start.assert_called_once_with(mock_start)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_end(self):
        """CALL SET_END should set end on slice ref."""
        mock_slice = MagicMock(spec=expression.SliceRef)
        mock_end = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_slice)
        self.vm._stack.append(mock_end)

        self.vm._exec_line("CALL SET_END")
        mock_slice.set_end.assert_called_once_with(mock_end)
        self.assertEqual(len(self.vm._stack), 2)

    def test_call_set_step(self):
        """CALL SET_STEP should set step on slice ref."""
        mock_slice = MagicMock(spec=expression.SliceRef)
        mock_step = MagicMock(spec=expression.Expression)
        self.vm._stack.clear()
        self.vm._stack.append(MagicMock())
        self.vm._stack.append(mock_slice)
        self.vm._stack.append(mock_step)

        self.vm._exec_line("CALL SET_STEP")
        mock_slice.set_step.assert_called_once_with(mock_step)
        self.assertEqual(len(self.vm._stack), 2)


class TestCompilerVMExec(unittest.TestCase):
    """Tests for CompilerVM.exec method."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    def test_exec_empty_commands(self):
        """Executing empty commands should do nothing."""
        self.vm.exec("")
        self.assertEqual(len(self.vm._stack), 0)

    def test_exec_set_info_only(self):
        """Executing only SET_INFO should update source info."""
        self.vm.exec("SET_INFO 1 1 1 5 test")
        self.assertEqual(self.vm._src_info.location_tuple, (1, 1, 1, 5))


class TestCompilerVMCompile(unittest.TestCase):
    """Tests for CompilerVM.compile method."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    @patch("os.path.exists")
    def test_compile_source_not_found(self, mock_exists):
        """Should return FAILURE when source file doesn't exist."""
        mock_exists.return_value = False
        result = self.vm.compile("/test/src/missing.vla")
        self.assertEqual(result.state, TaskResultState.FAILURE)

    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_compile_skip_when_up_to_date(self, mock_getmtime, mock_exists):
        """Should skip and return SUCCESS when output is up to date."""
        mock_exists.side_effect = lambda p: ".vla" in p or p.endswith(".h")
        mock_getmtime.side_effect = [200, 100]  # header newer than source

        result = self.vm.compile("/test/src/file.vla")
        self.assertEqual(result.state, TaskResultState.SUCCESS)

    @patch("os.path.exists")
    def test_compile_requires_parsing_cache(self, mock_exists):
        """Should return DELAYED when parsing cache is missing."""
        def exists_side_effect(path):
            if path.endswith(".vla"):
                return True
            if path.endswith(".h"):
                return False
            return False  # no cache files

        mock_exists.side_effect = exists_side_effect

        result = self.vm.compile("/test/src/file.vla")
        self.assertEqual(result.state, TaskResultState.DELAYED)


class TestCompilerVMScopeManagement(unittest.TestCase):
    """Tests for scope management in CompilerVM."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)
        # Mock symbol table to avoid type resolution
        self.vm._symbol_table = MagicMock()
        self.vm._symbol_table.namespace = "test"
        self.vm._var_state_table = MagicMock()

    def test_make_stmt_block_increments_scope(self):
        """Making a BLOCK statement should increment scope level."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        initial_scope = self.vm._CompilerVM__scope_level
        self.vm._exec_line("MAKE STMT BLOCK")
        self.assertGreater(self.vm._CompilerVM__scope_level, initial_scope)

    def test_scope_level_starts_at_zero(self):
        """Initial scope level should be 0."""
        # HOLD has value 0, so scope level starts at 0
        self.assertEqual(self.vm._CompilerVM__scope_level, 0)

    def test_multiple_blocks_increment_scope(self):
        """Nested blocks should increment scope further."""
        mock_src_file = MagicMock(spec=project.SourceFile)
        self.vm._stack.clear()
        self.vm._stack.append(mock_src_file)

        self.vm._exec_line("MAKE STMT BLOCK")
        scope_after_first = self.vm._CompilerVM__scope_level

        # Push a parent for second block
        self.vm._stack.append(MagicMock(spec=project.SourceFile))
        self.vm._exec_line("MAKE STMT BLOCK")
        scope_after_second = self.vm._CompilerVM__scope_level

        self.assertGreater(scope_after_second, scope_after_first)


class TestCompilerVMCheckType(unittest.TestCase):
    """Tests for CompilerVM.__check_type method."""

    def setUp(self):
        self.mock_project = MagicMock(spec=project.Project)
        self.mock_project.output_path = "/test/output"
        self.mock_project.root_path = "/test/workspace"
        self.vm = CompilerVM(self.mock_project)

    def test_check_type_passes_when_match(self):
        """Should not raise when type matches."""
        mock_expr = MagicMock(spec=expression.Expression)
        self.vm._CompilerVM__check_type(mock_expr, [expression.Expression])
        # No exception raised

    def test_check_type_raises_when_no_match(self):
        """Should raise InternalCompilerException when no type matches."""
        mock_expr = MagicMock(spec=expression.Expression)
        with self.assertRaises(InternalCompilerException):
            self.vm._CompilerVM__check_type(mock_expr, [statement.Statement])

    def test_check_type_with_multiple_options(self):
        """Should pass when item matches any of multiple allowed types."""
        mock_stmt = MagicMock(spec=statement.ReturnStmt)
        self.vm._CompilerVM__check_type(
            mock_stmt,
            [statement.ReturnStmt, statement.ThrowStmt, statement.OpStmt]
        )
        # No exception raised


class TestCompilerVMEncoding(unittest.TestCase):
    """Tests for CompilerVM encoding setting."""

    def test_encoding_is_from_compiler_params(self):
        """Should use encoding from COMPILER_PARAMS."""
        self.assertEqual(CompilerVM._ENCODING, COMPILER_PARAMS["encoding"])


if __name__ == "__main__":
    unittest.main()
