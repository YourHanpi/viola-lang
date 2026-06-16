# -*- coding: utf-8 -*-
from .utils import ParserGenericTable, ParsingResult, TokenStreamIO
from utils import CompilerException, SourceInfo, VIOLA_INIT, Token, COMPILER_PARAMS
from utils.file_marks import TOKEN_POSTFIX, PARSING_LOCK_POSTFIX, SYMBOL_TYPE_POSTFIX, CACHE_DIR
from utils.logger import Logger
from utils.task import TaskResult, TaskResultState

import os
import time
from typing import Optional, Callable, Sequence, Mapping, Any

__PARSER_UTILS_WITH_ARGS_TYPE = Callable[["GlobalParser", Sequence[Any], Mapping[Any, Any]], Optional[tuple[list[str], list[str]]]]
__PARSER_UTILS_WITHOUT_ARGS_TYPE = Callable[["GlobalParser"], Optional[tuple[list[str], list[str]]]]
__PARSER_UTILS_TYPE = __PARSER_UTILS_WITH_ARGS_TYPE | __PARSER_UTILS_WITHOUT_ARGS_TYPE


def _set_loc_command(parse_func: __PARSER_UTILS_TYPE) -> __PARSER_UTILS_TYPE:
    def wrapper(self: "GlobalParser", *args, **kwargs) -> Optional[tuple[list[str], list[str]]]:
        start_line, start_col, _, _ = self._src_info.location_tuple
        start_token_count: int = self._current
        result = parse_func(self, *args, **kwargs)
        end_token_count: int = self._current
        codes: str = "".join([token.text for token in self._tokens[start_token_count:end_token_count]])
        self._src_info.set_text(codes)
        if result is not None:
            command, symbol = result
            _, _, end_line, end_col = self._src_info.location_tuple
            return [f"SET_INFO {start_line} {start_col} {end_line} {end_col}"] + command, symbol
        return None

    return wrapper


_OPERATOR_TYPES: set[str] = {
    "ADD", "SUB", "MUL", "MATMUL", "DIV", "MOD", "POW", "LSHIFT", "RSHIFT", "AND", "BIT_AND", "OR", "BIT_OR",
    "BIT_XOR", "NOT", "INVERT", "EQ", "NE", "LT", "GT", "LE", "GE"
}
_EXPR_SPLITTERS: set[str] = {"COMMA", "L_BRACKET", "L_SQUARE_BRACKET", "L_CURLY_BRACKET", "QUESTION", "COLON"}

_BLANK_TOKEN: Token = Token("", ["_BLANK"])


class GlobalParser:
    _ENCODING: str = COMPILER_PARAMS["encoding"]

    def __init__(self, workspace: str) -> None:
        self._workspace: str = workspace
        self._tokens: list[Token] = []
        self._tokens_num: int = 0
        self._current: int = 0
        self._messages: list[str] = []
        self._exceptions: list[CompilerException] = []
        self._start_line: int = 1
        self._start_col: int = 1
        self._end_line: int = 1
        self._end_col: int = 1
        self._src_info: SourceInfo = VIOLA_INIT
        self._imports: dict[str, str] = {}
        self._parser_generic_table: ParserGenericTable = ParserGenericTable()
        self._symbol_types: dict[str, tuple[str, int]] = {}
        self._logger: Logger = Logger(f"Parser[0]")
        self._tasks: list[list[str]] = []
        self._static_libs_to_link: list[str] = []
        self._dynamic_libs_to_link: list[str] = []
        self._expr_count: int = 0
        self._expr_tokens: list[list[Token]] = []

    def parse(self, tokens: list[Token]) -> Optional[ParsingResult]:
        self._tasks.clear()
        self._load_tokens(tokens)
        self._move_to_first_token()
        command: list[str] = []
        symbol: list[str] = []
        is_error: bool = False
        while self._match_type("IMPORT") or self._match_type("FROM"):
            last_task_count: int = len(self._tasks)
            result = self._parse_import_line()
            if result is None and len(self._tasks) - last_task_count == 0:
                is_error = True
                self._handle_error_from_import()
            elif result is not None:
                command += result[0]
                symbol += result[1]
        if len(self._tasks) > 0:
            return None
        while not self._match_type("_EOF"):
            result = self._parse_def()
            if result is None:
                is_error = True
                self._handle_error()
            else:
                command += result[0]
                symbol += result[1]
        if is_error:
            return None
        return ParsingResult(command, symbol, self._expr_tokens, True)
    
    def parse_from_file(self, file_path: str) -> Optional[ParsingResult]:
        self._set_file_lock(file_path)
        self._logger.info(f"Start parsing {file_path}")
        if not os.path.exists(file_path + TOKEN_POSTFIX):
            self._add_task(["violac", "lex", file_path])
            return None
        tokens: list[Token] = TokenStreamIO.read(file_path + TOKEN_POSTFIX)
        result = self.parse(tokens)
        self._dump_symbol_type_list(file_path)
        self._remove_file_lock(file_path)
        if result is None:
            if len(self._tasks) == 0:
                self._logger.error(f"Failed to parse {file_path}")
            else:
                self._logger.debug("Required some other modules")
        else:
            self._logger.info(f"Successfully parsed {file_path}")
        return result

    def parse_to_file(self, file_path: str, thread_index: int = 0) -> TaskResult:
        self._logger: Logger = Logger(f"Parser[{thread_index}]")
        file_relpath = os.path.relpath(os.path.abspath(file_path), self._workspace)
        cache_file_path = os.path.abspath(os.path.join(CACHE_DIR, file_relpath))
        result = self.parse_from_file(cache_file_path)
        if result is not None:
            result.write(cache_file_path)
            return TaskResult(TaskResultState.SUCCESS, [["violac", "parse-expr", file_path]])
        elif len(self._tasks) > 0:
            return TaskResult(TaskResultState.DELAYED, self._tasks)
        return TaskResult(TaskResultState.FAILURE)

    def _add_parsing_slice(self, expr_tokens: list[Token]) -> str:
        self._expr_tokens.append(expr_tokens)
        return f"RAW {len(self._expr_tokens) - 1}"

    def _add_task(self, task_command: list[str]) -> None:
        self._tasks.append(task_command)

    def _back(self, steps: int = 1) -> None:
        for _ in range(steps):
            self._current -= 1
            self.__back_loc()
            while self._current >= 0 and self._get_current().type[0] in ["_COMMENT", "_BLANK"]:
                self._current -= 1
                self.__back_loc()

    def _back_to(self, pos: int) -> None:
        while self._current > pos:
            self._current -= 1
            self.__back_loc()

    @staticmethod
    def _buffer_match_types(tokens: list[Token], types: list[str]) -> bool:
        for i, token in enumerate(tokens):
            if token.type != types:
                return False
        return True

    def _change_tokens(self, token: Token, start_pos: int, end_pos: int) -> None:
        self._tokens[start_pos] = token
        self._tokens[start_pos + 1:end_pos] = [_BLANK_TOKEN] * (end_pos - start_pos - 1)
        
    @staticmethod
    def _check_file_lock(path: str) -> bool:
        return os.path.exists(path + PARSING_LOCK_POSTFIX)

    def _collect_until(self, end_token_type: str) -> Optional[list[Token]]:
        tokens: list[Token] = []
        while self._current < self._tokens_num:
            token = self._get_current()
            if token.type == end_token_type:
                return tokens
            tokens.append(token)
            self._next_no_skip()
        self._raise("Unexpected EOF")
        return None

    def _dump_symbol_type_list(self, file_path: str) -> None:
        lines: list[str] = []
        for name, (t, type_args) in self._symbol_types.items():
            if "." in name:
                continue
            lines.append(f"{name}%{t}%{type_args}")
        with open(file_path + SYMBOL_TYPE_POSTFIX, "w") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _filter_blank(tokens: list[Token]) -> list[Token]:
        return [token for token in tokens if "_BLANK" not in token.type and "_COMMENT" not in token.type]
    
    def _find_import(self, namespace: str) -> Optional[tuple[str, str, str, str]]:
        """
        根据命名空间寻找需要导入的模块位置。

        Args:
            namespace: 导入的命名空间。

        Returns:
            依次为目标的符号表路径、符号类型表路径、语法分析锁路径和源代码路径。
        """
        root_paths: list[str] = [self._workspace] + os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":")
        for root_path in root_paths:
            # TODO: 增加对Viola元数据（viola.metadata）的格式与解析
            # header_path = os.path.join(root_path, namespace.replace(".", os.sep) + ".vlah")
            # if os.path.exists(header_path):
            #     return header_path
            path = os.path.join(root_path, namespace.replace(".", os.sep) + ".vla")
            cache_path = os.path.join(root_path, CACHE_DIR, namespace.replace(".", os.sep) + ".vla")
            if os.path.exists(path):
                return cache_path + SYMBOL_TYPE_POSTFIX, cache_path + SYMBOL_TYPE_POSTFIX, cache_path + PARSING_LOCK_POSTFIX, path
        self._raise(f"Cannot find module {namespace}")
        return None

    def _get_current(self) -> Token:
        return self._tokens[self._current]

    def _handle_error(self) -> None:
        while self._current < self._tokens_num:
            if self._match_types(["FN", "SQ", "CLASS", "ENUM"]):
                break

    def _handle_error_from_import(self) -> None:
        while self._current < self._tokens_num:
            if self._match_types(["FN", "SQ", "CLASS", "ENUM", "IMPORT", "FROM"]):
                break

    def _load_symbol(self, namespace: str, to_load: Optional[list[str]] = None) -> Optional[list[str]]:
        file_path = self._find_import(namespace)
        if file_path is None:
            return None
        symbol_table_path, _, parsing_lock_path, token_path = file_path
        if not os.path.exists(symbol_table_path):
            if os.path.exists(parsing_lock_path):
                while os.path.exists(parsing_lock_path):
                    time.sleep(0.1)
            else:
                self._add_task(["violac", "parse", token_path])
                return None
        with open(symbol_table_path, "r", encoding=GlobalParser._ENCODING) as file:
            texts: str = file.read().split("---", 1)[1]
        text_list = texts.split("\n")
        if to_load is None:
            return text_list
        current_line: int = 0
        total_lines: int = len(text_list)
        to_load_locations: list[int] = []
        while current_line < total_lines:
            head: str = text_list[current_line].strip()
            current_line += 1
            line: str = text_list[current_line].strip()
            if head in ["BASE", "FUNC", "METHOD"] and line.split(" ", 1)[0] in to_load:
                to_load_locations.append(current_line - 1)
            elif head in ["CLASS", "ENUM"] and line.split("%", 1)[0] in to_load:
                to_load_locations.append(current_line - 1)
            elif head == "VAR" and line.split("%")[1] in to_load:
                to_load_locations.append(current_line - 1)
            else:
                self._logger.warning(f"Unknown symbol table head: {head}")
            while current_line < total_lines and text_list[current_line].strip() != "---":
                current_line += 1
        symbols: list[str] = []
        for loc in to_load_locations:
            while text_list[loc].strip() != "---":
                symbols.append(text_list[loc])
                loc += 1
            symbols.append("---")
        return symbols
                
    def _load_symbol_type_list(self, namespace: str, alias: str, to_load: Optional[list[str]] = None) -> None:
        file_path = self._find_import(namespace)
        if file_path is None:
            return
        _, symbol_types_path, parsing_lock_path, token_path = file_path
        if not os.path.exists(symbol_types_path):
            if os.path.exists(parsing_lock_path):
                while os.path.exists(parsing_lock_path):
                    time.sleep(0.1)
            else:
                self._add_task(["violac", "parse", token_path])
                return
        with open(symbol_types_path, "r") as file:
            texts: list[str] = file.readlines()
        for text in texts:
            text = text.strip()
            kv_list: list[str] = text.split("%")
            type_args_count: int = int(kv_list[2])
            if to_load is None or kv_list[0] in to_load:
                original_name: str = kv_list[0]
                if to_load is None:
                    original_name = namespace + "." + original_name
                    kv_list[0] = alias + "." + kv_list[0]
                self._symbol_types[kv_list[0]] = kv_list[1], type_args_count
                self._imports[kv_list[0]] = original_name
                if type_args_count > 0:
                    self._parser_generic_table.add(kv_list[0], type_args_count)

    def _load_tokens(self, tokens: list[Token]) -> None:
        self._tokens = tokens + [Token("", ["_EOF"])]
        self._tokens_num = len(tokens)
        self._current = 0
        self._exceptions.clear()

    def _match_import(self, end_pos: int) -> Optional[list[Token]]:
        expect_dot: bool = False
        str_buffer: list[str] = []
        tokens: list[Token] = []
        while self._current < end_pos:
            token = self._get_current()
            if "DOT" in token.type:
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expect_dot = False
            elif "IDENTIFIER" in token.type:
                if expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                str_buffer.append(token.text)
                expect_dot = True
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            tokens.append(token)
        for i in range(len(str_buffer) - 1, -1, -1):
            prefix_string = ".".join(str_buffer[:i + 1])
            if prefix_string in self._imports:
                return [Token(
                    self._imports[prefix_string] + "." + tokens[i].text, ["IDENTIFIER", "OPERAND"],
                    tokens[0].start_col
                )] + tokens[2 * i + 1:]
        return tokens

    def _match_type(self, token_type: str) -> bool:
        return token_type in self._get_current().type

    def _match_types(self, types: list[str]) -> bool:
        return len(set(types) & set(self._get_current().type)) > 0

    def _move_to_first_token(self) -> None:
        while self._current < self._tokens_num and self._get_current().type[0] in ["_COMMENT", "_BLANK"]:
            self._current += 1
            self.__next_loc()

    def _next(self, steps: int = 1) -> str:
        output: list[str] = []
        for _ in range(steps):
            self._current += 1
            output.append(self._get_current().text)
            self.__next_loc()
            while self._current < self._tokens_num and self._get_current().type[0] in ["_COMMENT", "_BLANK"]:
                self._current += 1
                self.__next_loc()
                output.append(self._get_current().text)
        return "".join(output)

    def _next_no_skip(self, steps: int = 1) -> str:
        output: list[str] = []
        for _ in range(steps):
            self._current += 1
            output.append(self._get_current().text)
            self.__next_loc()
        return "".join(output)

    def _next_to(self, pos: int) -> None:
        while self._current < pos:
            self._current += 1
            self.__next_loc()

    @_set_loc_command
    def _parse_assign_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        names_result = self._parse_id_list()
        if names_result is None:
            return None
        name_commands: list[str] = [f"CALL ADD_VAR_NAME {name}" for name in names_result]
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        expr_results = self._collect_until("SEMICOLON")
        if expr_results is None:
            return None
        expr_commands = self._add_parsing_slice(expr_results)
        self._expr_count += 1
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return ["MAKE STMT ASSIGN", expr_commands, "CALL SET_VAR_VALUE"] + name_commands + ["CALL FINISH"], []

    @_set_loc_command
    def _parse_block_stmt(self, new_scope: bool) -> Optional[tuple[list[str], list[str]]]:
        command: list[str] = ["MAKE STMT BLOCK"]
        symbol: list[str] = []
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        if new_scope:
            command += ["MAKE STMT C", "CALL ADD_TEXT do {", "CALL ADD_STMT"]
        while True:
            self._next()
            if self._match_type("R_CURLY_BRACKET"):
                break
            self._back()
            stmt_result = self._parse_stmt()
            if stmt_result is None:
                return None
            command += stmt_result[0] + ["CALL ADD_STMT"]
            symbol += stmt_result[1]
        if new_scope:
            command += ["MAKE STMT C", "CALL ADD_TEXT } while(0);", "CALL ADD_STMT"]
        command.append("CALL FINISH")
        return command, symbol

    @_set_loc_command
    def _parse_c_part_sq(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 1:
            self._raise(f"Unexpected prefix for C part sq: {' '.join(prefixes)}")
            return None
        self._next()
        decl_result = self._parse_func_decl("SQ", [], True)
        if decl_result is not None:
            command, symbol = decl_result
        else:
            return None
        body_result = self._parse_c_part_stmt()
        if body_result is not None:
            body_result, _ = body_result
            command += body_result
        else:
            return None
        command.append("CALL FINISH")
        return command, symbol

    @_set_loc_command
    def _parse_c_part_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        self._next()
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        codes: list[str] = []
        while True:
            if self._current >= self._tokens_num:
                self._raise("Unexpected EOF")
                return None
            if self._match_type("ESCAPED_CURLY_BRACKET"):
                codes.append(self._next()[1:])
            else:
                codes.append(self._next())
            if self._match_type("R_CURLY_BRACKET"):
                break
        codes = "".join(codes).split("\n")
        return [f"CALL ADD_TEXT {code}" for code in codes], []

    @_set_loc_command
    def _parse_catch_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("CATCH"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        type_result: Optional[str] = "viola$lang$exception$Exception"
        exc_name: str = "_"
        if not self._match_type("L_CURLY_BRACKET"):
            type_result = self._parse_type()
            if type_result is None:
                return None
            self._next()
            if self._match_type("IDENTIFIER"):
                exc_name = self._get_current().text
            self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        return ["MAKE STMT CATCH", f"MAKE EXPR TYPE_REF {type_result}", f"CALL SET_EXCEPT_DECL {exc_name}"] + block_result[0] + ["CALL SET_STMT"], []

    @_set_loc_command
    def _parse_class(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if "static" in prefixes:
            self._raise("Unexpected prefix for class: static")
            return None
        commands: list[str] = []
        symbol: list[str] = ["CLASS"]
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        class_name = self._get_current().text
        commands.append(f"MAKE DEF CLASS {class_name}")
        self._next()
        generic_args: list[str] = []
        if self._match_type("LT"):
            self._next()
            expect_comma: bool = False
            while not self._match_type("GT"):
                if self._match_type("IDENTIFIER"):
                    if expect_comma:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    generic_args.append(self._get_current().text)
                    expect_comma = True
                elif self._match_type("COMMA"):
                    if not expect_comma:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    expect_comma = False
                elif self._current >= self._tokens_num:
                    self._raise("Unexpected EOF")
                    return None
                else:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
            self._parser_generic_table.add(class_name, len(generic_args))
            self._next()
        self._symbol_types[class_name] = "CLASS", len(generic_args)
        parent_name: str = "object"
        if self._match_type("EXTENDS"):
            self._next()
            parent_name: Optional[str] = self._parse_type()
            if parent_name is None:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
        if self._match_type("L_CURLY_BRACKET"):
            symbol.append(f"{class_name}%" + " ".join([parent_name] + prefixes))
            symbol.append(" ".join(generic_args))
        else:
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        body_result = self._parse_class_body(class_name)
        if body_result is None:
            return None
        commands += body_result[0]
        symbol += body_result[1]
        self._next()
        return commands, symbol

    @_set_loc_command
    def _parse_class_body(self, class_name: str) -> Optional[tuple[list[str], list[str]]]:
        prop_command: list[str] = []
        prop_symbol: list[str] = []
        func_command: list[str] = []
        func_symbol: list[str] = []
        while self._current < self._tokens_num:
            self._next()
            prefixes = self._parse_prefixes(["ABSTRACT", "CPART", "STATIC", "PUBLIC", "PROTECTED", "PRIVATE"])
            if prefixes is None:
                return None
            if self._match_type("SQ") or self._match_type("FN"):
                self._back()
                result: Optional[tuple[list[str], list[str]]] = self._parse_method(class_name, prefixes)
                if not result:
                    return None
                func_command += result[0]
                func_symbol += result[1]
            elif self._match_type("IDENTIFIER"):
                self._back()
                result = self._parse_property(prefixes)
                if not result:
                    return None
                prop_command += result[0]
                prop_symbol += result[1]
            elif self._match_type("R_CURLY_BRACKET"):
                return prop_command + func_command, [*prop_symbol, "---", *func_symbol]
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            func_command += result[0]
            func_symbol += result[1]
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_closure_stmt(self, token_buffer: list[Token]) -> Optional[tuple[list[str], list[str]]]:
        if len(token_buffer) == 1:
            self._next()
            if not self._match_type("IDENTIFIER"):
                self._raise("Unexpected token: " + self._get_current().text)
            func_name: str = self._get_current().text
            self._back()
            closure_result = self._parse_func([], self._get_current().type[0], True)
            if closure_result is None:
                return None
            commands = closure_result[0]
            return ["MAKE STMT DECL", "MAKE EXPR CLOSURE"] + commands + [
                "CALL SET_DEF", "CALL SET_EXPR", "MAKE EXPR AUTO_TYPE_REF", f"CALL ADD_VAR {func_name}",
                "CALL FINISH"
            ], []
        self._back(len(token_buffer) - 1)
        if not self._match_type("AUTO"):
            self._raise("Please use auto type here.")
            return None
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        func_name = self._get_current().text
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        closure_result = self._parse_func([], self._get_current().text, True, True)
        if closure_result is None:
            return None
        commands = closure_result[0]
        return ["MAKE STMT DECL", "MAKE EXPR CLOSURE"] + commands + [
            "CALL SET_DEF", "CALL SET_EXPR", "MAKE EXPR AUTO_TYPE_REF", f"CALL ADD_VAR {func_name}",
            "CALL FINISH"
        ], []

    def _parse_cond_expr(self) -> Optional[str]:
        tokens: list[Token] = []
        if not self._match_type("L_BRACKET"):
            self._raise("Expected \"(\". Unexpected token: " + self._get_current().text)
            return None
        bracket_count: int = 1
        self._next_no_skip()
        while self._current < self._tokens_num:
            tokens.append(self._get_current())
            if self._match_type("L_BRACKET"):
                bracket_count += 1
            elif self._match_type("R_BRACKET"):
                bracket_count -= 1
            if bracket_count == 0:
                self._next()
                result = self._add_parsing_slice(tokens)
                self._expr_count += 1
                return result
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_cond_stmt(self, keyword: str) -> Optional[tuple[list[str], list[str]]]:
        if keyword not in ["IF", "ELIF", "ELSE"]:
            self._raise(f"Expected \"IF\", \"ELIF\", or \"ELSE\". Unexpected keyword: {keyword}")
            return None
        command: list[str] = ["MAKE STMT " + keyword]
        if not self._match_type(keyword):
            self._raise("Expected \"IF\", \"ELIF\", or \"ELSE\". Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if keyword != "ELSE":
            expr_result = self._parse_cond_expr()
            if expr_result is None:
                return None
            command += [expr_result, "CALL SET_EXPR_COND"]
            self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        command += block_result[0] + ["CALL SET_STMT"]
        if not self._match_type("R_CURLY_BRACKET"):
            self._raise("Expected \"}\". Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return command, []

    @_set_loc_command
    def _parse_const_def(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 0:
            self._raise(f"Unexpected prefix: {' '.join(prefixes)}")
        command: list[str] = ["MAKE DEF CONST"]
        stmt_result = self._parse_stmt()
        if stmt_result is None:
            return None
        command += stmt_result[0] + ["CALL SET_STMT"]
        symbol = stmt_result[1]
        command += ["CALL FINISH", "CALL ADD_DEF"]
        return command, symbol

    @_set_loc_command
    def _parse_decl_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        name_results = self._parse_type_name_list(["ASSIGN", "SEMICOLON"])
        if name_results is None:
            return None
        name_command, symbol = name_results
        if self._match_type("SEMICOLON"):
            return ["MAKE STMT DECL"] + name_command + ["CALL FINISH"], symbol
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        expr_results = self._collect_until("SEMICOLON")
        if expr_results is None:
            return None
        expr_commands = self._add_parsing_slice(expr_results)
        self._expr_count += 1
        return ["MAKE STMT DECL", expr_commands, "CALL SET_VAR_VALUE"] + name_command + ["CALL FINISH"], symbol

    @_set_loc_command
    def _parse_decl_assign_op_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """
        pure_decl_stmt = type_name_list SEMICOLON; -- 纯声明语句
        decl_stmt = type_name_list ASSIGN expr SEMICOLON; -- 声明语句
        assign_stmt = name_list ASSIGN expr SEMICOLON; -- 赋值语句
        op_stmt = expr SEMICOLON; -- 操作语句
        """
        token_buffer: list[Token] = [self._get_current()]
        while not self._match_type("SEMICOLON") and not self._match_type("FN") and not self._match_type("SQ"):
            token_buffer.append(self._get_current())
            self._next()
        if len(token_buffer) == 1:
            return [], []
        is_closure: bool = self._get_current().type in ["FN", "SQ"]
        if is_closure:
            return self._parse_closure_stmt(token_buffer)
        if len(token_buffer) == 0:
            return [], []
        if GlobalParser._buffer_match_types(token_buffer, ["IDENTIFIER", "SEMICOLON"]):
            return ["MAKE STMT OP", f"MAKE EXPR VARIABLE_REF auto {token_buffer[0].text}", "CALL SET_EXPR"], []
        self._back(len(token_buffer))
        if GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "IDENTIFIER"]) or \
                GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "LT"]):
            return self._parse_decl_stmt()
        if GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "ASSIGN"]) or \
                GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "COMMA"]) or \
                GlobalParser._buffer_match_types(token_buffer[:2], ["THIS", "DOT"]):
            return self._parse_assign_stmt()
        segments_num = self.__get_segments_num(token_buffer)
        if segments_num is None:
            return None
        if segments_num > 1:
            return self._parse_decl_stmt()
        return self._parse_op_stmt()

    @_set_loc_command
    def _parse_def(self) -> Optional[tuple[list[str], list[str]]]:
        prefixes = self._parse_prefixes(["ABSTRACT", "CPART", "EXPORT", "STATIC"])
        if prefixes is None:
            return None
        if self._match_type("SQ"):
            if "cpart" in prefixes:
                command, symbol = self._parse_c_part_sq(prefixes)
            else:
                command, symbol = self._parse_sq(prefixes)
        elif self._match_type("FN"):
            command, symbol = self._parse_fn(prefixes)
        elif self._match_type("CLASS"):
            command, symbol = self._parse_class(prefixes)
        elif self._match_type("ENUM"):
            command, symbol = self._parse_enum(prefixes)
        else:
            command, symbol = self._parse_const_def(prefixes)
        command += ["CALL ADD_DEF"]
        symbol.append("---")
        self._next()
        return command, symbol

    def _parse_elif_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        return self._parse_cond_stmt("ELIF")

    def _parse_else_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        return self._parse_cond_stmt("ELSE")

    @_set_loc_command
    def _parse_enum(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 0:
            self._raise(f"Unexpected prefix: {' '.join(prefixes)}")
        token: Token = self._get_current()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Unexpected token: {token}")
        enum_name: str = token.text
        command: list[str] = [f"MAKE DEF ENUM {token.text}"]
        symbol: list[str] = ["ENUM"]
        based_type: str = "uint32"
        self._next()
        if self._match_type("EXTENDS"):
            self._next()
            name: Optional[str] = self._parse_name()
            if name is None:
                return None
            based_type = name
            self._next()
        if self._match_type("L_CURLY_BRACKET"):
            symbol += [f"{enum_name} {based_type}", "---"]
        else:
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        body_result = self._parse_enum_body()
        if body_result is None:
            return None
        body_result, _ = body_result
        command += body_result
        self._next()
        return command, symbol

    @_set_loc_command
    def _parse_enum_body(self) -> Optional[tuple[list[str], list[str]]]:
        command: list[str] = []
        expect_semicolon: bool = False
        while True:
            self._next()
            if self._current >= self._tokens_num:
                self._raise("Unexpected EOF")
                return None
            if self._match_type("R_CURLY_BRACKET") and not expect_semicolon:
                break
            elif self._match_type("IDENTIFIER") and not expect_semicolon:
                self._back()
                result = self._parse_enum_item()
                if result is None:
                    return None
                command += result
                expect_semicolon = True
            elif self._match_type("SEMICOLON") and expect_semicolon:
                expect_semicolon = False
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        return command, []

    @_set_loc_command
    def _parse_enum_item(self) -> Optional[tuple[list[str], list[str]]]:
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        name: str = self._get_current().text
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        value = self._collect_until("SEMICOLON")
        if value is None:
            return None
        result = self._add_parsing_slice(value)
        self._expr_count += 1
        command: list[str] = [result] + [f"CALL ADD_ENUM {name}"]
        self._next()
        return command, []

    def _parse_expr(self) -> Optional[list[str]]:
        result_tokens = self._collect_until("SEMICOLON")
        if result_tokens is None:
            return None
        result = self._add_parsing_slice(result_tokens)
        self._expr_count += 1
        return [result]

    @_set_loc_command
    def _parse_finally_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("FINALLY"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        self._next()
        return ["MAKE STMT FINALLY"] + block_result[0] + ["CALL SET_STMT"], []

    def _parse_fn(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if "cpart" in prefixes:
            self._raise("Unexpected prefix: cpart")
            return None
        return self._parse_func(prefixes, "FN")

    @_set_loc_command
    def _parse_from_import(self) -> Optional[tuple[list[str], list[str]]]:
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        self._next()
        if not self._match_type("IMPORT"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        expect_comma: bool = False
        import_symbols: list[str] = []
        while True:
            if self._current >= self._tokens_num:
                self._raise("Unexpected EOF")
                return None
            if self._match_type("COMMA") and expect_comma:
                expect_comma = False
                self._next()
            elif self._match_type("COMMA") and not expect_comma:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            elif self._match_type("IDENTIFIER"):
                import_symbols.append(self._get_current().text)
                expect_comma = True
                self._next()
            elif self._match_type("SEMICOLON"):
                break
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        self._load_symbol_type_list(module_path, module_path, import_symbols)
        if len(self._tasks) > 0:
            return None
        command: list[str] = [f"MAKE FROM_IMPORT {module_path} " + " ".join(import_symbols)]
        symbol = self._load_symbol(module_path, import_symbols)
        if symbol is None:
            return None
        return command, symbol

    @_set_loc_command
    def _parse_func(self, prefixes: list[str], func_type: str, is_closure: bool = False, without_name: bool = False) -> \
            Optional[tuple[list[str], list[str]]]:
        decl_result = self._parse_func_decl(func_type, prefixes, is_closure, without_name)
        if decl_result is not None:
            command, symbol = decl_result
        else:
            return None
        self._next()
        body_result = self._parse_block_stmt(False)
        if body_result is not None:
            command += body_result
        else:
            return None
        command += ["CALL FINISH"]
        symbol.append("---")
        return command, symbol

    @_set_loc_command
    def _parse_func_decl(self, func_type: str, prefixes: list[str], is_closure: bool = False,
                         without_name: bool = False) -> Optional[tuple[list[str], list[str]]]:
        if func_type not in ["FN", "SQ"]:
            self._raise(f"Unexpected func type: {func_type}")
            return None
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Unexpected token: {self._get_current().text}")
            return None
        func_name: str = self._get_current().text if not is_closure else "!ANONYMOUS"
        command: list[str] = [" ".join([f"MAKE DEF {func_type} {func_name}"] + prefixes)]
        symbol: list[str] = ["FUNCTION", " ".join([func_name] + prefixes)]
        if not without_name:
            self._next()
        if not is_closure:
            generic_names: list[str] = []
            if self._match_type("LT"):
                expect_comma: bool = False
                while True:
                    if self._current >= self._tokens_num:
                        self._raise("Unexpected EOF")
                        return None
                    if self._match_type("GT"):
                        break
                    if self._match_type("IDENTIFIER") and not expect_comma:
                        generic_names.append(self._get_current().text)
                        self._next()
                        expect_comma = True
                    elif self._match_type("COMMA") and expect_comma:
                        expect_comma = False
                        self._next()
                    else:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                symbol.append(" ".join(generic_names))
                self._parser_generic_table.add(func_name, len(generic_names))
                self._next()
            self._symbol_types[func_name] = "FUNCTION", len(generic_names)
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        args_result = self._parse_type_name_list(["R_BRACKET"])
        if args_result is None:
            return None
        symbol += args_result[1]
        self._next()
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("ARROW"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        rets_result = self._parse_type_name_list(["R_BRACKET"])
        if rets_result is None:
            return None
        symbol += rets_result[1]
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return command, symbol

    def _parse_id_list(self) -> Optional[list[str]]:
        id_list: list[str] = []
        expect_comma: bool = False
        while self._current < self._tokens_num:
            if self._match_type("IDENTIFIER"):
                if expect_comma:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                id_list.append(self._get_current().text)
                expect_comma = True
                self._next()
            elif self._match_type("COMMA"):
                if not expect_comma:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                self._next()
                expect_comma = False
            else:
                return id_list
        self._raise("Unexpected EOF")
        return None

    def _parse_if_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        return self._parse_cond_stmt("IF")

    @_set_loc_command
    def _parse_import(self) -> Optional[tuple[list[str], list[str]]]:
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        alias: str = module_path
        if self._match_type("AS"):
            alias = self._get_current().text
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._load_symbol_type_list(module_path, alias)
        if len(self._tasks) > 0:
            return None
        symbol = self._load_symbol(module_path)
        if symbol is None:
            return None
        return ["CALL IMPORT " + module_path], symbol

    @_set_loc_command
    def _parse_import_line(self) -> Optional[tuple[list[str], list[str]]]:
        if self._match_type("IMPORT"):
            result: Optional[tuple[list[str], list[str]]] = self._parse_import()
        elif self._match_type("FROM"):
            result = self._parse_from_import()
        else:
            self._raise(f"Unexpected token: {self._get_current().text}")
            return None
        if result is None:
            return None
        return result

    @_set_loc_command
    def _parse_method(self, class_name: str, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        self._next()
        if sum(modifier in prefixes for modifier in ["PUBLIC", "PROTECTED", "PRIVATE"]) > 1:
            self._raise("Unexpected modifiers: " + " ".join(prefixes))
            return None
        if self._match_type("SQ"):
            result = self._parse_sq(prefixes)
            if result is None:
                return None
            command, symbol = result
            symbol[0] = "METHOD"
            symbol[1] = class_name + " " + symbol[1]
            return command, symbol
        if self._match_type("FN"):
            result = self._parse_fn(prefixes)
            if result is None:
                return None
            command, symbol = result
            symbol[0] = "METHOD"
            symbol[1] = class_name + " " + symbol[1]
            return command, symbol
        self._raise("Unexpected token: " + self._get_current().text)
        return None

    def _parse_name(self) -> Optional[str]:
        names: list[str] = []
        expect_dot: bool = False
        while True:
            if self._match_type("IDENTIFIER"):
                names.append(self._get_current().text)
                expect_dot = True
                self._next()
            elif self._match_type("DOT"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                expect_dot = False
                self._next()
            else:
                break
        return ".".join(names)

    @_set_loc_command
    def _parse_op_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        expr_result = self._collect_until("SEMICOLON")
        if expr_result is None:
            return None
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        parsing_slice = self._add_parsing_slice(expr_result)
        self._expr_count += 1
        return ["MAKE STMT OP", parsing_slice, "CALL SET_EXPR"], []

    def _parse_prefixes(self, matches: list[str]) -> Optional[list[str]]:
        prefixes: list[str] = []
        while (token := self._get_current()).type in matches:
            if token in prefixes:
                self._raise(f"Unexpected prefix: {token.text}")
                return None
            prefixes.append(token.text)
            self._next()
        self._back()
        return prefixes

    @_set_loc_command
    def _parse_property(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if sum(modifier in prefixes for modifier in ["PUBLIC", "PROTECTED", "PRIVATE"]) > 1:
            self._raise("Unexpected modifiers: " + " ".join(prefixes))
            return None
        if "cpart" in prefixes:
            self._raise("Unexpected prefix: cpart")
            return None
        if "abstract" in prefixes:
            self._raise("Unexpected prefix: abstract")
            return None
        is_static: bool = "static" in prefixes
        start_line: int = self._start_line
        start_col: int = self._start_col
        type_name = self._parse_type()
        if type_name is None:
            return None
        symbol = type_name + "%"
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        prop_name = self._get_current().text
        symbol += prop_name
        self._next()
        command: list[str] = []
        if is_static:
            if not self._match_type("ASSIGN"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
            expr_tokens = self._collect_until("SEMICOLON")
            if expr_tokens is None:
                return None
            command = [self._add_parsing_slice(expr_tokens), "CALL ADD_STATIC_PROP"]
            self._expr_count += 1
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        end_line: int = self._end_line
        end_col: int = self._end_col
        symbol = f"{start_line}:{start_col}:{end_line}:{end_col} " + " ".join([symbol] + prefixes)
        return command, [symbol]

    @_set_loc_command
    def _parse_return_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("RETURN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        return ["MAKE STMT RETURN"], []

    @_set_loc_command
    def _parse_sq(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        return self._parse_func(prefixes, "SQ")

    @_set_loc_command
    def _parse_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if self._match_type("ASYNC"):
            self._next()
            result = self._parse_stmt_no_async()
            if result is None:
                return None
            command, symbol = result
            command += ["CALL AS_ASYNC"]
            return command, symbol
        return self._parse_stmt_no_async()

    @_set_loc_command
    def _parse_stmt_no_async(self) -> Optional[tuple[list[str], list[str]]]:
        if self._match_type("RETURN"):
            return self._parse_return_stmt()
        if self._match_type("THROW"):
            return self._parse_throw_stmt()
        if self._match_type("CPART"):
            return self._parse_c_part_stmt()
        if self._match_type("IF"):
            return self._parse_if_stmt()
        if self._match_type("ELIF"):
            return self._parse_elif_stmt()
        if self._match_type("ELSE"):
            return self._parse_else_stmt()
        if self._match_type("TRY"):
            return self._parse_try_stmt()
        if self._match_type("CATCH"):
            return self._parse_catch_stmt()
        if self._match_type("FINALLY"):
            return self._parse_finally_stmt()
        if self._match_type("USING"):
            return self._parse_typedef_stmt()
        if self._match_type("L_CURLY_BRACKET"):
            return self._parse_block_stmt(True)
        return self._parse_decl_assign_op_stmt()

    @_set_loc_command
    def _parse_throw_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("THROW"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        to_throw_expr_result = self._parse_expr()
        if to_throw_expr_result is None:
            return None
        self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return ["MAKE STMT THROW", *to_throw_expr_result, "CALL SET_EXPR"], []

    @_set_loc_command
    def _parse_try_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("TRY"):
            self._raise("Expected try. Unexpected token: " + self._get_current().text)
            return None
        self._next()
        block_result = self._parse_block_stmt(True)
        if block_result is None:
            return None
        if not self._match_type("R_CURLY_BRACKET"):
            self._raise("Expected }")
            return None
        self._next()
        return ["MAKE STMT TRY"] + block_result[0] + ["CALL SET_STMT"], []

    def _parse_type(self) -> Optional[str]:
        l_bracket_count: int = 0
        l_angle_bracket_count: int = 0
        is_tuple: bool = False
        result: list[str] = []
        while self._current < self._tokens_num:
            token = self._get_current()
            result.append(token.text)
            if "L_BRACKET" in token.type:
                l_bracket_count += 1
                is_tuple = True
            elif "R_BRACKET" in token.type:
                l_bracket_count -= 1
            elif "GENERIC_START" in token.type:
                l_angle_bracket_count += 1
            elif "GT" in token.type:
                l_angle_bracket_count -= 1
            elif "R_SHIFT" in token.type:
                l_angle_bracket_count -= 2
            if l_bracket_count == 0 and l_angle_bracket_count == 0:
                self._next()
                if self._match_type("ARROW"):
                    if not is_tuple:
                        self._raise("Unexpected token: " + token.text)
                        return None
                    result.append(self._get_current().text)
                    self._next()
                    if not self._match_type("L_BRACKET"):
                        self._raise("Unexpected token: " + token.text)
                        return None
                    result.append(self._get_current().text)
                    self._next()
                    dst_type = self._parse_type()
                    if dst_type is None:
                        return None
                    if not self._match_type("R_BRACKET"):
                        self._raise("Unexpected token: " + token.text)
                        return None
                    self._next()
                    result.append(dst_type)
                return "".join(result)
            if l_bracket_count < 0 or l_angle_bracket_count < 0:
                self._raise(f"Unexpected token {token.text}")
                return None
            self._next()
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_typedef_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        if not self._match_type("USING"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        src_type = self._parse_type()
        if src_type is None:
            return None
        dst_type = self._get_current().text
        return [f"MAKE STMT TYPEDEF {dst_type}", f"MAKE EXPR TYPE_REF {src_type}", "CALL SET_TYPE"], []

    @_set_loc_command
    def _parse_type_name_list(self, end_symbols: list[str]) -> Optional[tuple[list[str], list[str]]]:
        expect_comma: bool = False
        command: list[str] = []
        symbol: list[str] = []
        while True:
            if self._match_types(end_symbols):
                break
            if expect_comma and not self._match_type("COMMA"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            if expect_comma and self._match_type("COMMA"):
                self._next()
                expect_comma = False
            else:
                type_decl = self._parse_type()
                if type_decl is None:
                    return None
                if not self._match_type("IDENTIFIER"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                symbol.append(type_decl + "%" + self._get_current().text)
                command.append(f"MAKE EXPR TYPE_REF {type_decl}")
                command.append(f"CALL ADD_VAR {self._get_current()}")
                expect_comma = True
                self._next()
        return command, symbol

    def _raise(self, message: str) -> None:
        self._logger.error(str(CompilerException(message, self._src_info)))
        
    @staticmethod
    def _remove_file_lock(path: str) -> None:
        os.remove(path + PARSING_LOCK_POSTFIX)
        
    @staticmethod
    def _set_file_lock(path: str) -> None:
        with open(path + PARSING_LOCK_POSTFIX, "w") as file:
            file.write("")

    def __back_loc(self) -> None:
        token: Token = self._get_current()
        self._end_line = self._start_line
        self._end_col = self._start_col
        token_lines: list[str] = token.text.split("\n")
        self._start_line -= len(token_lines) - 1
        self._start_col = token.start_col
        self._src_info.set_loc(self._start_line, self._start_col, self._end_line, self._end_col)

    def __get_import_prefix(self, id_list: list[str]) -> list[str]:
        for i in range(len(id_list), 0, -1):
            prefix: str = ".".join(id_list[:i])
            if prefix in self._imports:
                return [self._imports[prefix]] + id_list[i:]
        return id_list

    def __get_segments_num(self, token_buffer: list[Token]) -> Optional[int]:
        bracket_level: int = 0
        segments_num: int = 0
        local_token_buffer: list[Token] = []
        for token in token_buffer:
            if bracket_level == 0:
                if "ARROW" in token.type:
                    if "R_BRACKET" in local_token_buffer[-1].type:
                        local_token_buffer.append(token)
                    else:
                        local_token_buffer.clear()
                elif "L_BRACKET" in token.type:
                    if "ARROW" in local_token_buffer[-1].type:
                        local_token_buffer.append(token)
                    else:
                        local_token_buffer.clear()
                elif "DOT" not in token.type:
                    segments_num += 1
                elif "ASSIGN" in token.type:
                    return segments_num + 1
            if "L_BRACKET" in token.type:
                bracket_level += 1
            elif "R_BRACKET" in token.type:
                bracket_level -= 1
                if bracket_level == 0 and len(local_token_buffer) == 0:
                    local_token_buffer.append(token)
            if bracket_level < 0:
                self._raise("Unexpected token: " + token.text)
                return None
        return segments_num

    def __next_loc(self, token: Optional[Token] = None) -> None:
        token: Token = self._get_current() if token is None else token
        self._start_line = self._end_line
        self._start_col = self._end_col
        token_lines: list[str] = token.text.split("\n")
        self._end_line += len(token_lines) - 1
        self._end_col = len(token_lines[-1]) + 1
        self._src_info.set_loc(self._start_line, self._start_col, self._end_line, self._end_col)
