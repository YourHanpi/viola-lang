# -*- coding: utf-8 -*-
from utils.fsm import Token
from utils import CompilerException, SourceInfo, VIOLA_INIT

from typing import Optional, Literal


_STATEMENT_LOOK_AHEAD: list[tuple[str, list[str]]] = [
    ("ASSIGN", ["IDENTIFIER", "ASSIGN"])
]


class Parser:

    def __init__(self) -> None:
        self._tokens: list[Token] = []
        self._tokens_num: int = 0
        self._current: int = -1
        self._exceptions: list[CompilerException] = []
        self._start_line: int = 1
        self._start_col: int = 1
        self._end_line: int = 1
        self._end_col: int = 1
        self._src_info: SourceInfo = VIOLA_INIT

    def _back(self) -> None:
        self._current -= 1
        self.__back_loc()
        while self._current >= 0 and self._tokens[self._current].type in ["_COMMENT", "_BLANK"]:
            self._current -= 1
            self.__back_loc()

    def _match_look_ahead(self, states: list[tuple[str, list[str]]]) -> Optional[str]:
        states = sorted(states, key=lambda x: len(x[1]), reverse=True)
        match_list_max_length: int = len(states[0][1])
        ahead_tokens: list[list[str]] = []
        ahead_tokens_num: int = 0
        current: int = self._current + 1
        while ahead_tokens_num < match_list_max_length and current < self._tokens_num:
            if self._tokens[current].type not in ["_COMMENT", "_BLANK"]:
                ahead_tokens.append(self._tokens[current].type)
        for k, v in states:
            if len(ahead_tokens) >= len(v):
                if all(expected_token in token_types for expected_token, token_types in zip(v, ahead_tokens[:len(v)])):
                    return k
        return None

    def _match_type(self, token_type: str) -> bool:
        return token_type in self._tokens[self._current]

    def _next(self) -> str:
        self._current += 1
        output: list[str] = [self._tokens[self._current].text]
        self.__next_loc()
        while self._current < self._tokens_num and self._tokens[self._current].type in ["_COMMENT", "_BLANK"]:
            self._current += 1
            self.__next_loc()
            output.append(self._tokens[self._current].text)
        return "".join(output)

    def _parse_class(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if "static" in prefixes:
            self._raise("Unexpected prefix for class: static")
            return None
        self._next()
        commands: list[str] = []
        symbol: list[str] = ["CLASS"]
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        class_name = self._tokens[self._current].text
        commands.append(f"MAKE DEF CLASS {class_name}")
        self._next()
        parent_name: str = "object"
        if self._match_type("EXTENDS"):
            self._next()
            parent_name: Optional[str] = self._parse_name()
            if parent_name is None:
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
            self._next()
        if self._match_type("L_CURLY_BRACKET"):
            symbol.append(f"{class_name} " + " ".join([parent_name] + prefixes))
        else:
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        body_result = self._parse_class_body(class_name)
        if body_result is None:
            return None
        commands += body_result[0]
        symbol += body_result[1]
        return commands, symbol

    def _parse_block_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        command: list[str] = ["MAKE STMT BLOCK"]
        symbol: list[str] = []
        self._next()
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        while True:
            self._next()
            if self._match_type("R_CURLY_BRACKET"):
                break
            self._back()
            stmt_result = self._parse_stmt()
            if stmt_result is None:
                return None
            command += stmt_result[0]
            symbol += stmt_result[1]
        command.append("FINISH")
        return command, symbol

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
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
            func_command += result[0]
            func_symbol += result[1]
        self._raise("Unexpected EOF")
        return None

    def _parse_const_def(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 0:
            self._raise(f"Unexpected prefix: {' '.join(prefixes)}")
        command: list[str] = ["MAKE DEF CONST"]
        stmt_result = self._parse_stmt()
        if stmt_result is None:
            return None
        command += stmt_result[0]
        symbol = stmt_result[1]
        command += ["FINISH", "CALL ADD_DEF"]
        return command, symbol

    def _parse_c_part_sq(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 1:
            self._raise(f"Unexpected prefix for cpart sq: {' '.join(prefixes)}")
            return None
        self._next()
        decl_result = self._parse_func_decl("SQ", [])
        if decl_result is not None:
            command, symbol = decl_result
        else:
            return None
        body_result = self._parse_c_part_stmt()
        if body_result is not None:
            command += body_result
        else:
            return None
        command.append("CALL FINISH")
        return command, symbol

    def _parse_c_part_stmt(self) -> Optional[list[str]]:
        self._next()
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
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
        return [f"CALL ADD_TEXT {code}" for code in codes]

    def _parse_def(self) -> Optional[tuple[list[str], list[str]]]:
        self._next()
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
        return command, symbol

    def _parse_enum(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if len(prefixes) > 0:
            self._raise(f"Unexpected prefix: {' '.join(prefixes)}")
        self._next()
        token: Token = self._tokens[self._current]
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
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        body_result: Optional[list[str]] = self._parse_enum_body()
        if body_result is None:
            return None
        command += body_result
        return command, symbol

    def _parse_enum_body(self) -> Optional[list[str]]:
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
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
        return command

    def _parse_enum_item(self) -> Optional[list[str]]:
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        name: str = self._tokens[self._current].text
        self._next()
        if not self._match_type("ASSIGN"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        self._next()
        value: Optional[list[str]] = self._parse_expr()
        if value is None:
            return None
        command: list[str] = value + [f"CALL ADD_ENUM {name}"]
        return command

    def _parse_fn(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        if "cpart" in prefixes:
            self._raise("Unexpected prefix: cpart")
            return None
        return self._parse_func(prefixes, "FN")

    def _parse_from_import(self) -> Optional[tuple[list[str], list[str]]]:
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        self._next()
        if not self._match_type("IMPORT"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
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
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
            elif self._match_type("IDENTIFIER"):
                import_symbols.append(self._tokens[self._current].text)
                expect_comma = True
                self._next()
            elif self._match_type("SEMICOLON"):
                break
            else:
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
        command: list[str] = [f"MAKE FROM_IMPORT {module_path} " + " ".join(import_symbols)]
        symbol: list[str] = ["FROM_IMPORT", module_path, " ".join(import_symbols), "---"]
        return command, symbol

    def _parse_func(self, prefixes: list[str], func_type: Literal["SQ"] | Literal["FN"]) -> Optional[tuple[list[str], list[str]]]:
        self._next()
        decl_result = self._parse_func_decl(func_type, prefixes)
        if decl_result is not None:
            command, symbol = decl_result
        else:
            return None
        body_result = self._parse_block_stmt()
        if body_result is not None:
            command += body_result
        else:
            return None
        command += ["CALL FINISH"]
        symbol.append("---")
        return command, symbol

    def _parse_func_decl(self, func_type: Literal["SQ"] | Literal["FN"], prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Unexpected token: {self._tokens[self._current].text}")
            return None
        func_name: str = self._tokens[self._current].text
        command: list[str] = [" ".join([f"MAKE DEF {func_type} {func_name}"] + prefixes)]
        symbol: list[str] = ["FUNCTION", " ".join([func_name] + prefixes)]
        self._next()
        if self._match_type("LT"):
            expect_comma: bool = False
            generic_names: list[str] = []
            while True:
                if self._current >= self._tokens_num:
                    self._raise("Unexpected EOF")
                    return None
                if self._match_type("GT"):
                    break
                if self._match_type("IDENTIFIER") and not expect_comma:
                    generic_names.append(self._tokens[self._current].text)
                    self._next()
                    expect_comma = True
                elif self._match_type("COMMA") and expect_comma:
                    expect_comma = False
                    self._next()
                else:
                    self._raise("Unexpected token: " + self._tokens[self._current].text)
                    return None
            symbol.append(" ".join(generic_names))
            self._next()
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        args_result = self._parse_type_name_list("R_BRACKET")
        if args_result is None:
            return None
        command += args_result[0]
        symbol += args_result[1]
        self._next()
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        self._next()
        if not self._match_type("ARROW"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        self._next()
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        rets_result = self._parse_type_name_list("R_BRACKET")
        if rets_result is None:
            return None
        command += rets_result[0]
        symbol += rets_result[1]
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        self._next()
        return command, symbol

    def _parse_import(self) -> Optional[tuple[list[str], list[str]]]:
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._tokens[self._current].text)
            return None
        return ["CALL IMPORT " + module_path], ["IMPORT", module_path, "---"]

    def _parse_import_line(self) -> Optional[tuple[list[str], list[str]]]:
        if self._match_type("IMPORT"):
            result: Optional[tuple[list[str], list[str]]] = self._parse_import()
        elif self._match_type("FROM"):
            result = self._parse_from_import()
        else:
            self._raise(f"Unexpected token: {self._tokens[self._current].text}")
            return None
        if result is None:
            return None
        return result

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
        self._raise("Unexpected token: " + self._tokens[self._current].text)
        return None

    def _parse_name(self) -> Optional[str]:
        names: list[str] = []
        expect_dot: bool = False
        while True:
            if self._match_type("IDENTIFIER"):
                names.append(self._tokens[self._current].text)
                expect_dot = True
                self._next()
            elif self._match_type("DOT"):
                if not expect_dot:
                    self._raise("Unexpected token: " + self._tokens[self._current].text)
                    return None
                expect_dot = False
                self._next()
            else:
                break
        return ".".join(names)

    def _parse_prefixes(self, matches: list[str]) -> Optional[list[str]]:
        prefixes: list[str] = []
        self._next()
        while (token := self._tokens[self._current]).type in matches:
            if token in prefixes:
                self._raise(f"Unexpected prefix: {token.text}")
                return None
            prefixes.append(token.text)
            self._next()
        self._back()
        return prefixes

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
        start_line: int = self._start_line
        start_col: int = self._start_col
        result = self._parse_decl_stmt()
        end_line: int = self._end_line
        end_col: int = self._end_col
        if result is None:
            return None
        _, symbol = result
        symbol[0] = f"{start_line}:{start_col}:{end_line}:{end_col} " + " ".join([symbol[0]] + prefixes)
        return [], symbol

    def _parse_sq(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        return self._parse_func(prefixes, "SQ")

    def _parse_type(self) -> Optional[str]:
        l_bracket_count: int = 0
        l_angle_bracket_count: int = 0
        result: list[str] = []
        for token in self._tokens:
            result.append(token.text)
            if token.type == "L_BRACKET":
                l_bracket_count += 1
            elif token.type == "R_BRACKET":
                l_bracket_count -= 1
            elif token.type == "LT":
                l_angle_bracket_count += 1
            elif token.type == "GT":
                l_angle_bracket_count -= 1
            if l_bracket_count == 0 and l_angle_bracket_count == 0:
                return "".join(result)
            if l_bracket_count < 0 or l_angle_bracket_count < 0:
                self._raise(f"Unexpected token {token.text}")
                return None
        self._raise("Unexpected EOF")
        return None

    def _parse_type_name_list(self, end_symbol: str) -> Optional[tuple[list[str], list[str]]]:
        expect_comma: bool = False
        symbol: list[str] = []
        self._next()
        while True:
            if self._match_type(end_symbol):
                break
            if expect_comma and not self._match_type("COMMA"):
                self._raise("Unexpected token: " + self._tokens[self._current].text)
                return None
            if expect_comma and self._match_type("COMMA"):
                self._next()
                expect_comma = False
            else:
                type_decl = self._parse_type()
                if type_decl is None:
                    return None
                symbol.append(type_decl)
                if not self._match_type("IDENTIFIER"):
                    self._raise("Unexpected token: " + self._tokens[self._current].text)
                    return None
                symbol.append(self._tokens[self._current].text)
                expect_comma = True
                self._next()
        return [], [" ".join(symbol)]

    def _raise(self, message: str) -> None:
        self._src_info.set_loc(self._start_line, self._start_col, self._end_line, self._end_col)
        self._exceptions.append(CompilerException(message, self._src_info))

    def __back_loc(self) -> None:
        token: Token = self._tokens[self._current]
        self._end_line = self._start_line
        self._end_col = self._start_col
        token_lines: list[str] = token.text.split("\n")
        self._start_line -= len(token_lines) - 1
        self._start_col = token.start_col

    def __next_loc(self) -> None:
        token: Token = self._tokens[self._current]
        self._start_line = self._end_line
        self._start_col = self._end_col
        token_lines: list[str] = token.text.split("\n")
        self._end_line += len(token_lines) - 1
        self._end_col = len(token_lines[-1]) + 1
