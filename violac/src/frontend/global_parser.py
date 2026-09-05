# -*- coding: utf-8 -*-
from .utils import ParserGenericTable, ParsingResult, TokenStreamIO
from utils import CompilerException, SourceInfo, VIOLA_INIT, Token, COMPILER_PARAMS
from utils.file_marks import TOKEN_POSTFIX, PARSING_LOCK_POSTFIX, SYMBOL_TABLE_POSTFIX, SYMBOL_TYPE_POSTFIX, CACHE_DIR, set_file_lock, remove_file_lock
from utils.logger import Logger
from utils.task import TaskResult, TaskResultState

import os
import time
from typing import Optional, Callable, Sequence, Mapping, Any

__PARSER_UTILS_WITH_ARGS_TYPE = Callable[["GlobalParser", Sequence[Any], Mapping[Any, Any]], Optional[tuple[list[str], list[str]]]]
__PARSER_UTILS_WITHOUT_ARGS_TYPE = Callable[["GlobalParser"], Optional[tuple[list[str], list[str]]]]
__PARSER_UTILS_TYPE = __PARSER_UTILS_WITH_ARGS_TYPE | __PARSER_UTILS_WITHOUT_ARGS_TYPE


def _set_loc_command(parse_func: __PARSER_UTILS_TYPE) -> __PARSER_UTILS_TYPE:
    """
    装饰器：自动为解析函数注入位置信息和源代码文本，并生成SET_INFO命令。
    :param parse_func: 被装饰的解析函数。
    :return: 装饰后的包装函数。
    """
    def wrapper(self: "GlobalParser", *args, **kwargs) -> Optional[tuple[list[str], list[str]]]:
        start_line, start_col, _, _ = self._src_info.location_tuple
        result = parse_func(self, *args, **kwargs)
        if result is not None:
            command, symbol = result
            _, _, end_line, end_col = self._src_info.location_tuple
            return [f"SET_INFO {start_line} {start_col} {end_line} {end_col}"] + command, symbol
        self._logger.debug(f"Exit function {parse_func.__name__}")
        return None

    return wrapper


_OPERATOR_TYPES: set[str] = {
    "ADD", "SUB", "MUL", "MATMUL", "DIV", "MOD", "POW", "LSHIFT", "RSHIFT", "AND", "BIT_AND", "OR", "BIT_OR",
    "BIT_XOR", "NOT", "INVERT", "EQ", "NE", "LT", "GT", "LE", "GE"
}
_EXPR_SPLITTERS: set[str] = {"COMMA", "L_BRACKET", "L_SQUARE_BRACKET", "L_CURLY_BRACKET", "QUESTION", "COLON"}

_BLANK_TOKEN: Token = Token("", ["_BLANK"])


class GlobalParser:
    """
    全局解析器基类，负责Viola语言源文件的语法分析。
    包含预处理、导入解析、定义解析及语句解析等功能。
    """
    _ENCODING: str = COMPILER_PARAMS["encoding"]

    def __init__(self, workspace: str) -> None:
        """
        初始化全局解析器。
        :param workspace: 工作区路径。
        """
        self._workspace: str = os.path.abspath(workspace)
        self._tokens: list[Token] = []
        self._tokens_num: int = 0
        self._current: int = 0
        self._messages: list[str] = []
        self._exceptions: list[CompilerException] = []
        self._src_info: SourceInfo = VIOLA_INIT.copy()
        self._imports: dict[str, str] = {}
        self._parser_generic_table: ParserGenericTable = ParserGenericTable()
        self._symbol_types: dict[str, tuple[str, list[str]]] = {}
        self._logger: Logger = Logger(f"Parser[0]")
        self._tasks: list[list[str]] = []
        self._static_libs_to_link: list[str] = []
        self._dynamic_libs_to_link: list[str] = []
        self._expr_count: int = 0
        self._expr_tokens: list[list[Token]] = []

    def parse(self, tokens: list[Token]) -> Optional[ParsingResult]:
        """
        解析记号流，返回解析结果。
        :param tokens: 记号列表。
        :return: 解析结果对象，失败返回None。
        """
        self._tasks.clear()
        self._expr_tokens.clear()
        self._symbol_types.clear()
        self._imports = {}
        self._load_tokens(tokens)
        self._move_to_first_token()
        command: list[str] = []
        symbol: list[str] = []
        is_error: bool = False
        while self._match_types(["_BLANK", "_COMMENT"]):
            self._next()
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
            self._tasks.insert(0, ["violac", "parse", self._src_info.path])
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
        return ParsingResult(command, symbol, self._expr_tokens, True, self._imports)
    
    def parse_from_file(self, file_path: str, src_path: str = "") -> Optional[ParsingResult]:
        """
        从文件中读取记号流并进行解析。
        注意：调用方需自行管理文件解析锁（见parse_to_file）。
        :param file_path: 缓存文件路径。
        :param src_path: 源文件路径，如果为空则使用缓存文件路径。
        :return: 解析结果对象，失败或需要其他任务时返回None。
        """
        file_path = os.path.abspath(file_path)
        self._tasks.clear()
        src_path = src_path if src_path else file_path
        if not os.path.exists(file_path + TOKEN_POSTFIX):
            self._add_task(["violac", "lex", src_path])
            return None
        if os.path.exists(file_path + SYMBOL_TABLE_POSTFIX) and \
                os.path.getmtime(src_path) < os.path.getmtime(file_path + SYMBOL_TABLE_POSTFIX):
            # 已解析过且源文件未更新，直接复用已有结果
            return ParsingResult.read(file_path)
        tokens: list[Token] = TokenStreamIO.read(file_path + TOKEN_POSTFIX)
        result = self.parse(tokens)
        self._dump_symbol_type_list(file_path)
        return result

    def parse_to_file(self, file_path: str, thread_index: int = 0) -> TaskResult:
        """
        解析文件并将结果写入缓存。
        :param file_path: 源文件路径。
        :param thread_index: 线程索引。
        :return: 任务结果。
        """
        self._logger: Logger = Logger(f"Parser[{thread_index}]")
        file_abs_path = os.path.abspath(file_path)
        file_relpath = os.path.relpath(file_abs_path, self._workspace)
        cache_file_path = os.path.join(self._workspace, CACHE_DIR, file_relpath)
        self._src_info: SourceInfo = SourceInfo(file_abs_path)
        self._logger.info(f"Start parsing {file_path}")
        if not self._set_file_lock(cache_file_path):
            # 该文件正在被其他线程解析，重新入队等待
            self._logger.debug("File is being parsed by another thread")
            return TaskResult(TaskResultState.DELAYED, [["violac", "parse", file_path]])
        try:
            result = self.parse_from_file(cache_file_path, file_abs_path)
            if result is None:
                if len(self._tasks) == 0:
                    self._logger.error(f"Failed to parse {file_path}")
                else:
                    self._logger.debug("Required some other modules")
            else:
                self._logger.info(f"Successfully parsed {file_path}")
            if result is not None:
                result.write(cache_file_path, file_abs_path, self._workspace)
                return TaskResult(TaskResultState.SUCCESS, [["violac", "parse-expr", file_path]])
            elif len(self._tasks) > 0:
                return TaskResult(TaskResultState.DELAYED, self._tasks)
            return TaskResult(TaskResultState.FAILURE)
        finally:
            self._remove_file_lock(cache_file_path)

    def _add_parsing_slice(self, expr_tokens: list[Token]) -> str:
        """
        添加表达式切片到表达式列表，并返回其RAW引用。
        :param expr_tokens: 表达式的记号列表。
        :return: RAW命令字符串。
        """
        self._expr_tokens.append(expr_tokens)
        return f"RAW {len(self._expr_tokens) - 1} {self._src_info.location} {''.join([token.text for token in expr_tokens]).replace('\n', ' ').replace('\t', ' ')}"

    def _add_task(self, task_command: list[str]) -> None:
        """
        添加一个待执行的任务。
        :param task_command: 任务命令列表。
        """
        self._tasks.append(task_command)

    def _back(self, steps: int = 1) -> None:
        """
        向后移动指定步数（跳过空白和注释）。
        :param steps: 移动步数。
        """
        for _ in range(steps):
            self._current -= 1
            self.__back_loc()
            while self._current >= 0 and self._get_current().type[0] in ["_COMMENT", "_BLANK"]:
                self._current -= 1
                self.__back_loc()

    def _back_to(self, pos: int) -> None:
        """
        向后移动到指定位置。
        :param pos: 目标位置。
        """
        while self._current > pos:
            self._current -= 1
            self.__back_loc()

    @staticmethod
    def _buffer_match_types(tokens: list[Token], types: list[str]) -> bool:
        """
        判断缓冲区中的记号类型是否与指定类型列表匹配。
        :param tokens: 记号缓冲区。
        :param types: 期望的类型列表。
        :return: 是否匹配。
        """
        if len(tokens) != len(types):
            return False
        for i, token in enumerate(tokens):
            if types[i] not in token.type:
                return False
        return True

    def _change_tokens(self, token: Token, start_pos: int, end_pos: int) -> None:
        """
        替换指定范围内的记号为新的记号（其余设为空白）。
        :param token: 新记号。
        :param start_pos: 起始位置。
        :param end_pos: 结束位置。
        """
        self._tokens[start_pos] = token
        self._tokens[start_pos + 1:end_pos] = [_BLANK_TOKEN] * (end_pos - start_pos - 1)
        
    @staticmethod
    def _check_file_lock(path: str) -> bool:
        """
        检查文件解析锁是否存在。
        :param path: 文件路径。
        :return: 是否存在锁文件。
        """
        return os.path.exists(path + PARSING_LOCK_POSTFIX)

    def _collect_until(self, end_token_type: list[str]) -> Optional[list[Token]]:
        """
        收集记号直到遇到指定类型的结束记号（跳过空白和注释）。
        :param end_token_type: 结束记号类型。
        :return: 收集的记号列表。
        """
        tokens: list[Token] = []
        while self._current < self._tokens_num:
            token = self._get_current()
            if token.type[0] in end_token_type:
                return tokens
            tokens.append(token)
            self._next_no_skip()
        self._raise("Unexpected EOF")
        return None

    def _dump_symbol_type_list(self, file_path: str) -> None:
        """
        将符号类型表写入文件。
        :param file_path: 文件路径（不含后缀）。
        """
        lines: list[str] = []
        for name, (t, type_args) in self._symbol_types.items():
            if "." in name:
                continue
            lines.append(f"{name}%{t}%{type_args}")
        with open(file_path + SYMBOL_TYPE_POSTFIX, "w") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _filter_blank(tokens: list[Token]) -> list[Token]:
        """
        过滤掉空白和注释记号。
        :param tokens: 原始记号列表。
        :return: 过滤后的记号列表。
        """
        return [token for token in tokens if "_BLANK" not in token.type and "_COMMENT" not in token.type]
    
    def _find_import(self, namespace: str) -> Optional[tuple[str, str, str, str]]:
        """
        根据命名空间寻找需要导入的模块位置。

        Args:
            namespace: 导入的命名空间。

        Returns:
            依次为目标的符号表路径、符号类型表路径、语法分析锁路径和源代码路径。
        """
        root_paths: list[str] = [self._workspace]
        if "VIOLA_HOME" in os.environ:
            root_paths += os.environ["VIOLA_HOME"].split(";" if os.name == "nt" else ":")
        for root_path in root_paths:
            # TODO: 增加对Viola元数据（viola.metadata）的格式与解析
            # header_path = os.path.join(root_path, namespace.replace(".", os.sep) + ".vlah")
            # if os.path.exists(header_path):
            #     return header_path
            path = os.path.join(root_path, namespace.replace(".", os.sep) + ".vla")
            if os.path.exists(path):
                # 缓存路径与lexer/parser的写入位置一致：
                # 工作区缓存目录 + 相对工作区的路径（库文件会解析到工作区之外）
                cache_path = os.path.join(self._workspace, CACHE_DIR, os.path.relpath(path, self._workspace))
                return cache_path + SYMBOL_TABLE_POSTFIX, cache_path + SYMBOL_TYPE_POSTFIX, \
                    cache_path + PARSING_LOCK_POSTFIX, path
        self._raise(f"Cannot find module {namespace}")
        return None

    def _get_current(self) -> Token:
        """
        获取当前位置的记号。
        :return: 当前记号对象。
        """
        return self._tokens[self._current]

    def _handle_error(self) -> None:
        """
        跳过错误记号直到下一个顶层定义（FN/SQ/CLASS/ENUM）。
        """
        while self._current < self._tokens_num:
            if self._match_types(["FN", "SQ", "CLASS", "ENUM"]):
                break
            self._next()

    def _handle_error_from_import(self) -> None:
        """
        跳过导入语句中的错误，直到下一个有效关键字。
        """
        while self._current < self._tokens_num:
            if self._match_types(["FN", "SQ", "CLASS", "ENUM", "IMPORT", "FROM"]):
                break
            self._next()

    def _load_symbol(self, namespace: str, to_load: Optional[list[str]] = None) -> Optional[list[str]]:
        """
        加载指定命名空间的符号表。
        :param namespace: 命名空间。
        :param to_load: 需要加载的符号列表，为None则加载全部。
        :return: 符号列表。
        """
        file_path = self._find_import(namespace)
        if file_path is None:
            return None
        symbol_table_path, _, parsing_lock_path, token_path = file_path
        if os.path.exists(parsing_lock_path):
            # 目标模块正被其他线程处理，等待其完成后再读取符号表
            while os.path.exists(parsing_lock_path):
                time.sleep(0.1)
        if not os.path.exists(symbol_table_path):
            self._add_task(["violac", "parse", token_path])
            return None
        with open(symbol_table_path, "r") as file:
            text_list: list[str] = file.read().split("\n")
        # 符号表文件头部固定为三行：源路径、缓存目录、分隔符
        if len(text_list) > 2 and text_list[2].strip() == "---":
            text_list = text_list[3:]
        if to_load is None:
            return self._qualify_symbol_entries(text_list, namespace)
        load_all: bool = "*" in to_load
        current_line: int = 0
        total_lines: int = len(text_list)
        to_load_locations: list[int] = []
        while current_line < total_lines:
            head: str = text_list[current_line].strip()
            current_line += 1
            # 跳过空行与条目尾部的分隔符（函数条目尾部可能连续出现多个）
            if head in ["", "---"]:
                continue
            if current_line >= total_lines:
                break
            line: str = text_list[current_line].strip()
            matched: bool = load_all
            if head in ["BASE", "FUNC", "FUNCTION", "METHOD"]:
                matched = matched or line.split(" ", 1)[0] in to_load
            elif head in ["CLASS", "ENUM"]:
                matched = matched or line.split("%", 1)[0] in to_load
            elif head == "VAR":
                line_parts: list[str] = line.split("%")
                matched = matched or (len(line_parts) > 1 and line_parts[1] in to_load)
            else:
                self._logger.warning(f"Unknown symbol table head: {head}")
            if matched:
                to_load_locations.append(current_line - 1)
            while current_line < total_lines and text_list[current_line].strip() != "---":
                current_line += 1
        # 收集模块自身定义的符号名（用于条目中的类型限定）
        module_names: set[str] = set()
        _, symbol_types_path, _, _ = file_path
        if os.path.exists(symbol_types_path):
            with open(symbol_types_path, "r") as symbol_file:
                for text in symbol_file.readlines():
                    text = text.strip()
                    if "%" in text:
                        module_names.add(text.split("%", 1)[0].split(".")[-1])
        symbols: list[str] = []
        for loc in to_load_locations:
            head: str = text_list[loc].strip()
            entry: list[str] = []
            cursor: int = loc + 1
            while text_list[cursor].strip() != "---":
                entry.append(text_list[cursor])
                cursor += 1
            # from...import的符号同样需要模块命名空间限定，
            # 否则后端会以导入方模块的命名空间注册符号
            qualified: list[str] = GlobalParser._qualify_symbol_entry(head, entry, namespace, module_names)
            symbols.extend([head] + qualified + ["---"])
        return symbols

    @staticmethod
    def _qualify_type_name(type_name: str, namespace: str, module_names: set[str]) -> str:
        """
        若类型名属于导入模块，则加上模块命名空间限定。
        :param type_name: 类型名。
        :param namespace: 模块命名空间。
        :param module_names: 模块自身定义的符号名集合。
        :return: 限定后的类型名。
        """
        if type_name in module_names:
            return namespace + "." + type_name
        return type_name

    @staticmethod
    def _qualify_symbol_entry(head: str, entry: list[str], namespace: str, module_names: set[str]) -> list[str]:
        """
        对导入模块的单个符号条目做模块命名空间限定，供 `import X;` 使用。
        :param head: 条目头（FUNCTION/METHOD/VAR/CLASS等）。
        :param entry: 条目内容（不含条目头与尾部分隔符）。
        :param namespace: 模块命名空间。
        :param module_names: 模块自身定义的符号名集合。
        :return: 限定后的条目内容。
        """
        if not entry:
            return []
        result: list[str] = entry.copy()
        if head in ["FUNC", "FUNCTION", "METHOD"]:
            # 名称行：函数名或"类名 方法名"（后接修饰符）
            name_parts: list[str] = result[0].split(" ")
            name_parts[0] = namespace + "." + name_parts[0]
            result[0] = " ".join(name_parts)
            # 参数行与返回行中的类型名（%分隔的偶数位）
            for i in range(1, len(result)):
                if "%" not in result[i]:
                    continue
                segments: list[str] = result[i].split("%")
                for j in range(0, len(segments), 2):
                    segments[j] = GlobalParser._qualify_type_name(segments[j], namespace, module_names)
                result[i] = "%".join(segments)
        elif head == "VAR":
            for i in range(len(result)):
                parts: list[str] = result[i].split("%")
                if len(parts) > 1:
                    parts[0] = GlobalParser._qualify_type_name(parts[0], namespace, module_names)
                    parts[1] = namespace + "." + parts[1]
                    result[i] = "%".join(parts)
        elif head == "CLASS":
            # 名称行：类名%父类名（后接修饰符）
            name_line: list[str] = result[0].split(" ")
            cls_parent: list[str] = name_line[0].split("%")
            cls_parent[0] = namespace + "." + cls_parent[0]
            if len(cls_parent) > 1 and cls_parent[1] in module_names:
                cls_parent[1] = namespace + "." + cls_parent[1]
            name_line[0] = "%".join(cls_parent)
            result[0] = " ".join(name_line)
            # 属性行：<位置> 类型%名称 [修饰符]（泛型行不含位置标记，跳过）
            for i in range(1, len(result)):
                line: str = result[i].strip()
                if line == "END CLASS":
                    break
                parts = line.split(" ")
                if len(parts) > 1 and ":" in parts[0] and "%" in parts[1]:
                    type_parts: list[str] = parts[1].split("%")
                    type_parts[0] = GlobalParser._qualify_type_name(type_parts[0], namespace, module_names)
                    parts[1] = "%".join(type_parts)
                    result[i] = " ".join(parts)
        return result

    def _qualify_symbol_entries(self, text_list: list[str], namespace: str) -> list[str]:
        """
        为导入模块的符号表条目添加模块命名空间限定，供 `import X;` 使用。
        :param text_list: 模块符号表条目（已去除文件头）。
        :param namespace: 模块命名空间。
        :return: 限定后的符号条目列表。
        """
        file_path = self._find_import(namespace)
        if file_path is None:
            return []
        _, symbol_types_path, _, _ = file_path
        module_names: set[str] = set()
        if os.path.exists(symbol_types_path):
            with open(symbol_types_path, "r") as file:
                for text in file.readlines():
                    kv_list: list[str] = text.strip().split("%")
                    if len(kv_list) > 0 and kv_list[0]:
                        module_names.add(kv_list[0])
        symbols: list[str] = []
        current_line: int = 0
        total_lines: int = len(text_list)
        while current_line < total_lines:
            head: str = text_list[current_line].strip()
            current_line += 1
            if head in ["", "---"]:
                continue
            if current_line >= total_lines:
                break
            entry: list[str] = []
            while current_line < total_lines and text_list[current_line].strip() != "---":
                entry.append(text_list[current_line])
                current_line += 1
            symbols.append(head)
            symbols += self._qualify_symbol_entry(head, entry, namespace, module_names)
            symbols.append("---")
        return symbols
                
    def _load_symbol_type_list(self, namespace: str, alias: str, to_load: Optional[list[str]] = None) -> None:
        """
        加载指定命名空间的符号类型列表。
        :param namespace: 命名空间。
        :param alias: 别名。
        :param to_load: 需要加载的符号列表。
        """
        file_path = self._find_import(namespace)
        if file_path is None:
            return
        _, symbol_types_path, parsing_lock_path, token_path = file_path
        if os.path.exists(parsing_lock_path):
            # 目标模块正被其他线程处理，等待其完成后再读取符号类型表
            while os.path.exists(parsing_lock_path):
                time.sleep(0.1)
        if not os.path.exists(symbol_types_path):
            self._add_task(["violac", "parse", token_path])
            return
        with open(symbol_types_path, "r") as file:
            texts: list[str] = file.readlines()
        for text in texts:
            text = text.strip()
            kv_list: list[str] = text.split("%")
            type_args: list[str] = kv_list[2:]
            if to_load is None or "*" in to_load or kv_list[0] in to_load:
                original_name: str = kv_list[0]
                if to_load is None:
                    original_name = namespace + "." + original_name
                    kv_list[0] = alias + "." + kv_list[0]
                else:
                    # from...import：导入名保持原名，但原始符号名需要模块限定
                    original_name = namespace + "." + original_name
                self._symbol_types[kv_list[0]] = kv_list[1], type_args
                self._imports[kv_list[0]] = original_name
                if len(type_args) > 0:
                    self._parser_generic_table.add(kv_list[0], type_args)

    def _load_tokens(self, tokens: list[Token]) -> None:
        """
        加载记号流到解析器（追加EOF标记）。
        :param tokens: 记号列表。
        """
        self._tokens = tokens + [Token("", ["_EOF"], tokens[-1].src_info if len(tokens) > 0 else self._src_info)]
        self._tokens_num = len(tokens)
        self._current = 0
        self._exceptions.clear()

    def _match_import(self, end_pos: int) -> Optional[list[Token]]:
        """
        匹配导入路径并解析为完整记号的序列。
        :param end_pos: 结束位置。
        :return: 解析后的记号列表。
        """
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
                    SourceInfo.concat([tokens[0].src_info, tokens[i].src_info])
                )] + tokens[2 * i + 1:]
        return tokens

    def _match_type(self, token_type: str) -> bool:
        """
        判断当前记号是否包含指定类型。
        :param token_type: 记号类型。
        :return: 是否匹配。
        """
        return token_type in self._get_current().type

    def _match_types(self, types: list[str]) -> bool:
        """
        判断当前记号是否包含指定类型列表中的任一类型。
        :param types: 类型列表。
        :return: 是否匹配。
        """
        return len(set(types) & set(self._get_current().type)) > 0

    def _move_to_first_token(self) -> None:
        """
        移动到第一个有效的非空白、非注释记号。
        """
        while self._current < self._tokens_num and self._get_current().type[0] in ["_COMMENT", "_BLANK"]:
            self._current += 1
            self.__next_loc()

    def _next(self, steps: int = 1) -> str:
        """
        向前移动指定步数（跳过空白和注释），返回经过的文本。
        :param steps: 移动步数。
        :return: 经过的文本内容。
        """
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
        """
        向前移动指定步数（不跳过空白和注释）。
        :param steps: 移动步数。
        :return: 经过的文本内容。
        """
        output: list[str] = []
        for _ in range(steps):
            self._current += 1
            output.append(self._get_current().text)
            self.__next_loc()
        return "".join(output)

    def _next_to(self, pos: int) -> None:
        """
        向前移动到指定位置。
        :param pos: 目标位置。
        """
        while self._current < pos:
            self._current += 1
            self.__next_loc()

    @_set_loc_command
    def _parse_assign_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析赋值语句（变量 = 表达式）。"""
        if not self._match_types(["IDENTIFIER", "THIS"]):
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
        expr_results = self._collect_until(["SEMICOLON"])
        if expr_results is None:
            return None
        expr_commands = self._add_parsing_slice(expr_results)
        # self._expr_count += 1
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return ["MAKE STMT ASSIGN", expr_commands, "CALL SET_VAR_VALUE"] + name_commands + ["CALL FINISH"], []

    @_set_loc_command
    def _parse_block_stmt(self, new_scope: bool) -> Optional[tuple[list[str], list[str]]]:
        """解析块语句（花括号内的语句序列）。"""
        command: list[str] = ["MAKE STMT BLOCK"]
        symbol: list[str] = []
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if new_scope:
            command += ["MAKE STMT C", "CALL ADD_TEXT do {", "CALL ADD_STMT"]
        while not self._match_type("R_CURLY_BRACKET"):
            stmt_result = self._parse_stmt()
            if stmt_result is None:
                return None
            command += stmt_result[0] + ["CALL ADD_STMT"]
            symbol += stmt_result[1]
        if new_scope:
            command += ["MAKE STMT C", "CALL ADD_TEXT } while(0);", "CALL ADD_STMT"]
        command.append("CALL FINISH")
        self._next()
        return command, symbol

    @_set_loc_command
    def _parse_c_part_sq(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析C语言函数（cpart sq）。"""
        if len(prefixes) > 1:
            self._raise(f"Unexpected prefix for C part sq: {' '.join(prefixes)}")
            return None
        decl_result = self._parse_func_decl("SQ", [], False)
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
        """解析C代码片段语句（cpart { ... }）。"""
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        codes: list[str] = []
        while True:
            if self._current >= self._tokens_num:
                self._raise("Unexpected EOF")
                return None
            if self._match_type("ESCAPED_CURLY_BRACKET"):
                codes.append(self._next_no_skip()[1:])
            elif self._match_type("R_CURLY_BRACKET"):
                break
            else:
                codes.append(self._next_no_skip())
        self._next()
        codes = "".join(codes).rstrip("}").split("\n")
        result = ["MAKE STMT C"]
        for code in codes:
            if code.strip():
                result.append(f"CALL ADD_TEXT {code}")
        result.append("CALL ADD_STMT")
        return result, []

    @_set_loc_command
    def _parse_catch_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析catch语句（异常捕获）。"""
        if not self._match_type("CATCH"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        type_result: Optional[str] = "viola$lang$exception$Exception"
        exc_name: str = "_"
        if not self._match_type("L_CURLY_BRACKET"):
            self._next()
            type_result = self._parse_type()
            if type_result is None:
                return None
            if self._match_type("IDENTIFIER"):
                exc_name = self._get_current().text
            self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        return ["MAKE STMT CATCH", f"MAKE EXPR TYPE_REF {type_result}", f"CALL SET_EXCEPT_DECL {exc_name}"] + block_result[0] + ["CALL SET_STMT"], []

    @_set_loc_command
    def _parse_class(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析类定义（class ClassName { ... }）。"""
        if "static" in prefixes:
            self._raise("Unexpected prefix for class: static")
            return None
        commands: list[str] = []
        symbol: list[str] = ["CLASS"]
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        class_name = self._get_current().text
        commands.append(f"MAKE DEF CLASS {class_name}")
        self._next()
        generic_args: list[str] = []
        if self._match_type("GENERIC_START"):
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
                self._next()
            self._parser_generic_table.add(class_name, generic_args)
            self._next()
        self._symbol_types[class_name] = "CLASS", generic_args
        parent_names: list[str] = []
        if self._match_type("EXTENDS") or self._match_type("IMPL"):
            # extends与impl均解析为父类型列表（接口允许多继承）
            self._next()
            while True:
                parent_name: Optional[str] = self._parse_type()
                if parent_name is None:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                parent_names.append(parent_name)
                if self._match_type("COMMA"):
                    self._next()
                    continue
                break
        parent_name: str = "object" if len(parent_names) == 0 else ",".join(parent_names)
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
        return commands, symbol

    @_set_loc_command
    def _parse_class_body(self, class_name: str) -> Optional[tuple[list[str], list[str]]]:
        """解析类体（成员方法和属性）。"""
        prop_command: list[str] = []
        prop_symbol: list[str] = []
        func_command: list[str] = []
        func_symbol: list[str] = []
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        while self._current < self._tokens_num:
            prefixes = self._parse_prefixes(["ABSTRACT", "CPART", "STATIC", "PUBLIC", "PROTECTED", "PRIVATE", "FINAL", "EXPORT", "UNSAFE"])
            if prefixes is None:
                return None
            if self._match_type("SQ") or self._match_type("FN"):
                result: Optional[tuple[list[str], list[str]]] = self._parse_method(class_name, prefixes)
                if not result:
                    return None
                func_command += result[0]
                func_symbol += result[1]
            elif self._match_type("R_CURLY_BRACKET"):
                self._next()
                return prop_command + func_command, [*prop_symbol, "END CLASS", "---", *func_symbol]
            else:
                result = self._parse_property(prefixes)
                if not result:
                    return None
                prop_command += result[0]
                prop_symbol += result[1]
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_closure_stmt(self, token_buffer: list[Token]) -> Optional[tuple[list[str], list[str]]]:
        """解析闭包声明语句。"""
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
        """
        解析条件表达式（括号括起的条件）。
        :return: RAW命令字符串。
        """
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
                result = self._add_parsing_slice(tokens[1:-1])
                self._next()
                # self._expr_count += 1
                return result
            self._next()
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_cond_stmt(self, keyword: str) -> Optional[tuple[list[str], list[str]]]:
        """解析条件语句（if/elif/else）。"""
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
        if not self._match_type("L_CURLY_BRACKET"):
            self._raise("Expected \"{\". Unexpected token: " + self._get_current().text)
            return None
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        command += block_result[0] + ["CALL SET_STMT"]
        return command, []

    @_set_loc_command
    def _parse_const_def(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析常量定义。"""
        if len(prefixes) > 0:
            self._raise(f"Unexpected prefix: {' '.join(prefixes)}")
        command: list[str] = ["MAKE DEF CONST"]
        stmt_result = self._parse_stmt()
        if stmt_result is None:
            return None
        command += stmt_result[0] + ["CALL SET_STMT"]
        symbol = ["VAR"] + stmt_result[1]
        command += ["CALL FINISH"]
        return command, symbol

    @_set_loc_command
    def _parse_constructor_call_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析构造函数调用语句。"""
        cls_name = self._parse_type()
        if cls_name is None:
            return None
        if not self._match_type("IDENTIFIER"):
            self._raise("Expected identifier. Unexpected token: " + self._get_current().text)
            return None
        var_name = self._get_current().text
        self._next()
        expr_tokens = self._collect_until(["SEMICOLON"])
        if expr_tokens is None:
            return None
        expr_tokens = [Token(cls_name, ["IDENTIFIER"], self._src_info.copy())] + expr_tokens
        raw_command = self._add_parsing_slice(expr_tokens)
        command: list[str] = [
            "MAKE STMT DECL", f"MAKE EXPR TYPE_REF {cls_name}", f"CALL ADD_VAR {var_name}",
            raw_command, "CALL SET_VAR_VALUE", "CALL FINISH"
        ]
        # self._expr_count += 1
        symbol = [f"{cls_name}%{var_name}"]
        return command, symbol

    @_set_loc_command
    def _parse_decl_stmt(self, pure_decl_expected: Optional[bool] = None) -> Optional[tuple[list[str], list[str]]]:
        """解析变量声明语句（类型 名称 = 表达式;）。"""
        start_pos: int = self._current
        name_results = self._parse_type_name_list(["ASSIGN", "SEMICOLON"])
        if name_results is None:
            return None
        name_command, symbol = name_results
        if self._match_type("L_BRACKET"):
            if pure_decl_expected is not None and not pure_decl_expected:
                self._raise("Pure declaration expected. Unexpected token: " + self._get_current().text)
                return None
            if len(name_command) > 3:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._back_to(start_pos)
            return self._parse_constructor_call_stmt()
        if self._match_type("SEMICOLON"):
            if pure_decl_expected is not None and not pure_decl_expected:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            return ["MAKE STMT DECL"] + name_command + ["CALL FINISH"], symbol
        if not self._match_type("ASSIGN"):
            if pure_decl_expected is not None and pure_decl_expected:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        expr_results = self._collect_until(["SEMICOLON"])
        if expr_results is None:
            return None
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        expr_commands = self._add_parsing_slice(expr_results)
        # self._expr_count += 1
        return ["MAKE STMT DECL", expr_commands, "CALL SET_VAR_VALUE"] + name_command + ["CALL FINISH"], symbol

    @_set_loc_command
    def _parse_decl_assign_op_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """
        解析语句（声明/赋值/操作语句的统合入口）。

        pure_decl_stmt = type_name_list SEMICOLON; -- 纯声明语句
        decl_stmt = type_name_list ASSIGN expr SEMICOLON; -- 声明语句
        assign_stmt = name_list ASSIGN expr SEMICOLON; -- 赋值语句
        op_stmt = expr SEMICOLON; -- 操作语句
        """
        start_pos: int = self._current
        token_buffer: list[Token] = []
        while not self._match_type("SEMICOLON") and not self._match_type("FN") and not self._match_type("SQ"):
            token_buffer.append(self._get_current())
            self._next()
        if len(token_buffer) == 0:
            self._next()
            return ["MAKE STMT OP"], []
        is_closure: bool = self._get_current().type in ["FN", "SQ"]
        if is_closure:
            return self._parse_closure_stmt(token_buffer)
        self._back_to(start_pos)
        if GlobalParser._buffer_match_types(token_buffer, ["IDENTIFIER"]):
            return ["MAKE STMT OP", f"MAKE EXPR VARIABLE_REF auto {token_buffer[0].text}", "CALL SET_EXPR"], []
        if GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "IDENTIFIER"]):
            return self._parse_decl_stmt()
        if GlobalParser._buffer_match_types(token_buffer[:2], ["IDENTIFIER", "GENERIC_START"]):
            if self.__is_generic_call(token_buffer):
                # 泛型函数调用语句（如 forEachEach::<T>(...)）
                return self._parse_op_stmt()
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
        """解析顶层定义（声明式函数、过程式函数、类、枚举、常量）。"""
        prefixes = self._parse_prefixes(["ABSTRACT", "CPART", "EXPORT", "STATIC", "FINAL", "UNSAFE", "WRAPPER"])
        if prefixes is None:
            return None
        if self._match_type("SQ"):
            if "cpart" in prefixes:
                result = self._parse_c_part_sq(prefixes)
            else:
                result = self._parse_sq(prefixes)
        elif self._match_type("FN"):
            result = self._parse_fn(prefixes)
        elif self._match_type("CLASS"):
            result = self._parse_class(prefixes)
        elif self._match_type("INTERFACE"):
            # interface关键字标记接口类
            result = self._parse_class(prefixes + ["interface"])
        elif self._match_type("ENUM"):
            result = self._parse_enum(prefixes)
        else:
            result = self._parse_const_def(prefixes)
        if result is None:
            return None
        command, symbol = result
        command += ["CALL ADD_DEF"]
        symbol.append("---")
        return command, symbol

    def _parse_elif_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析elif语句。"""
        return self._parse_cond_stmt("ELIF")

    def _parse_else_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析else语句。"""
        return self._parse_cond_stmt("ELSE")

    @_set_loc_command
    def _parse_enum(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析枚举定义。"""
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
        """解析枚举体（枚举项列表）。"""
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
                command += result[0]
                expect_semicolon = True
            elif self._match_type("SEMICOLON") and expect_semicolon:
                expect_semicolon = False
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        return command, []

    @_set_loc_command
    def _parse_enum_item(self) -> Optional[tuple[list[str], list[str]]]:
        """解析枚举项（名称 = 值）。"""
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
        value = self._collect_until(["SEMICOLON"])
        if value is None:
            return None
        result = self._add_parsing_slice(value)
        # self._expr_count += 1
        command: list[str] = [result] + [f"CALL ADD_ENUM {name}"]
        self._next()
        return command, []

    def _parse_expr(self) -> Optional[list[str]]:
        """
        解析表达式并返回RAW引用。
        :return: RAW命令列表。
        """
        result_tokens = self._collect_until(["SEMICOLON"])
        if result_tokens is None:
            return None
        result = self._add_parsing_slice(result_tokens)
        # self._expr_count += 1
        return [result]

    @_set_loc_command
    def _parse_finally_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析finally语句。"""
        if not self._match_type("FINALLY"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        return ["MAKE STMT FINALLY"] + block_result[0] + ["CALL SET_STMT"], []

    def _parse_fn(self, prefixes: list[str], cls_name: str = "") -> Optional[tuple[list[str], list[str]]]:
        """
        解析声明式函数定义。
        :param prefixes: 前缀修饰符列表。
        :return: 命令和符号列表。
        """
        if "cpart" in prefixes:
            self._raise("Unexpected prefix: cpart")
            return None
        return self._parse_func(prefixes, "FN", cls_name=cls_name)

    @_set_loc_command
    def _parse_from_import(self) -> Optional[tuple[list[str], list[str]]]:
        """解析from...import语句。"""
        self._next()
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        if not self._match_type("IMPORT"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        expect_comma: bool = False
        import_symbols: list[str] = []
        is_wildcard: bool = False
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
            elif self._match_type("MUL"):
                is_wildcard = True
                self._next()
            elif self._match_type("SEMICOLON"):
                break
            else:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
        if is_wildcard:
            import_symbols = ["*"]
        self._load_symbol_type_list(module_path, module_path, import_symbols)
        if len(self._tasks) > 0:
            return None
        command: list[str] = [f"MAKE DEF FROM_IMPORT {module_path} " + " ".join(import_symbols), "CALL ADD_DEF"]
        symbol = self._load_symbol(module_path, import_symbols)
        if symbol is None:
            return None
        self._next()
        return command, symbol

    @_set_loc_command
    def _parse_func(self, prefixes: list[str], func_type: str, is_closure: bool = False, without_name: bool = False,
                    cls_name: str = "") -> Optional[tuple[list[str], list[str]]]:
        """
        解析函数定义（函数体包括声明和块语句）。
        :param prefixes: 前缀修饰符列表。
        :param func_type: 函数类型（FN/SQ）。
        :param is_closure: 是否为闭包。
        :param without_name: 是否匿名。
        :return: 命令和符号列表。
        """
        decl_result = self._parse_func_decl(func_type, prefixes, is_closure, without_name, cls_name)
        if decl_result is not None:
            command, symbol = decl_result
        else:
            return None
        if self._match_type("SEMICOLON"):
            # 仅声明不定义（原生函数/方法原型，实现由运行库提供；
            # 接口内的无体方法仍按抽象方法处理，见_read_method_decl）
            self._next()
            symbol[1] += " native"
            command.append("CALL FINISH")
            symbol.append("---")
            return command, symbol
        body_result = self._parse_block_stmt(False)
        if body_result is not None:
            command += body_result[0]
        else:
            return None
        command += ["CALL ADD_STMT", "CALL FINISH"]
        symbol.append("---")
        return command, symbol

    @_set_loc_command
    def _parse_func_decl(self, func_type: str, prefixes: list[str], is_closure: bool = False,
                         without_name: bool = False, cls_name: str = "") -> Optional[tuple[list[str], list[str]]]:
        """
        解析函数声明（函数名称、泛型参数、参数列表和返回类型）。
        :param func_type: 函数类型。
        :param prefixes: 前缀修饰符列表。
        :param is_closure: 是否为闭包。
        :param without_name: 是否匿名。
        :return: 命令和符号列表。
        """
        if func_type not in ["FN", "SQ"]:
            self._raise(f"Unexpected func type: {func_type}")
            return None
        self._next()
        if not self._match_type("IDENTIFIER"):
            self._raise(f"Unexpected token: {self._get_current().text}")
            return None
        func_name: str = self._get_current().text if not is_closure else "!ANONYMOUS"
        is_method = cls_name != ""
        if func_type == "SQ" and func_name == "__new__" and is_method:
            func_type = "CONSTRUCTOR"
        elif func_type == "SQ" and func_name == "__del__" and is_method:
            func_type = "DESTRUCTOR"
        if func_type in ["CONSTRUCTOR", "DESTRUCTOR"]:
            command: list[str] = [f"MAKE DEF {func_type} {cls_name} "]
        else:
            command: list[str] = [f"MAKE DEF {func_type} {func_name} " if not is_method else f"MAKE DEF {func_type} {cls_name}.{func_name} "]
        symbol: list[str] = ["FUNCTION", " ".join([func_name] + prefixes)]
        if not without_name:
            self._next()
        if not is_closure:
            generic_names: list[str] = []
            if self._match_type("GENERIC_START"):
                expect_comma: bool = False
                self._next()
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
                self._parser_generic_table.add(func_name, generic_names)
                self._next()
            else:
                symbol.append("")
            self._symbol_types[func_name] = "FUNCTION", generic_names
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        args_result = self._parse_type_name_list_with_default(["R_BRACKET"])
        if args_result is None:
            return None
        command[0] += "%".join([t.split("%")[0] for t in args_result[1]]) if len(args_result[1]) > 0 else ""
        command += args_result[0]
        symbol += ["%".join(args_result[1])]
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
        self._next()
        rets_result = self._parse_type_name_list(["R_BRACKET"])
        if rets_result is None:
            return None
        rets = rets_result[1]
        if func_name == "__new__":
            if len(rets) != 1 or rets[0] != "THIS":
                self._raise("__new__ must return this")
                return None
            rets = [f"{cls_name}%_this"]
        symbol += ["%".join(rets), " ".join(args_result[2])]
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return command, symbol

    def _parse_id_list(self) -> Optional[list[str]]:
        """
        解析标识符列表（逗号分隔）。
        :return: 标识符列表。
        """
        id_list: list[str] = []
        expect_comma: bool = False
        while self._current < self._tokens_num:
            if self._match_type("THIS"):
                if expect_comma:
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                id_list.append("this.")
                self._next()
                if not self._match_type("DOT"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                self._next()
                if not self._match_type("IDENTIFIER") and not self._match_type("SUPER"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                id_list[-1] += self._get_current().text
                expect_comma = True
                self._next()
            elif self._match_type("IDENTIFIER"):
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
        """解析if语句。"""
        return self._parse_cond_stmt("IF")

    @_set_loc_command
    def _parse_import(self) -> Optional[tuple[list[str], list[str]]]:
        """解析import语句。"""
        self._next()
        if self._match_type("CPART"):
            self._next()
            name_buffer: list[str] = []
            while self._current < self._tokens_num and not self._match_type("SEMICOLON"):
                name_buffer.append(self._get_current().text)
                self._next_no_skip()
            if self._current >= self._tokens_num:
                self._raise("Unexpected EOF")
                return None
            self._next()
            return [f"MAKE DEF CPART_IMPORT {''.join(name_buffer)}", "CALL ADD_DEF"], []
        module_path: Optional[str] = self._parse_name()
        if module_path is None:
            return None
        alias: str = module_path
        if self._match_type("AS"):
            self._next()
            if not self._match_type("IDENTIFIER"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            alias = self._get_current().text
            self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._load_symbol_type_list(module_path, alias)
        if len(self._tasks) > 0:
            return None
        symbol = self._load_symbol(module_path)
        if symbol is None:
            return None
        self._next()
        return ["MAKE DEF IMPORT " + module_path, "CALL ADD_DEF"], symbol

    @_set_loc_command
    def _parse_import_line(self) -> Optional[tuple[list[str], list[str]]]:
        """解析导入行（import或from...import）。"""
        if self._match_type("IMPORT"):
            result: Optional[tuple[list[str], list[str]]] = self._parse_import()
        elif self._match_type("FROM"):
            result = self._parse_from_import()
        else:
            self._raise(f"Unexpected token: {self._get_current().text}")
            return None
        return result

    @_set_loc_command
    def _parse_method(self, class_name: str, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析类方法定义。"""
        if sum(modifier in prefixes for modifier in ["PUBLIC", "PROTECTED", "PRIVATE"]) > 1:
            self._raise("Unexpected modifiers: " + " ".join(prefixes))
            return None
        if self._match_type("SQ"):
            result = self._parse_sq(prefixes, class_name)
            if result is None:
                return None
            command, symbol = result
            symbol[0] = "METHOD"
            symbol[1] = class_name + " " + symbol[1]
            command.append("CALL ADD_METHOD")
            return command, symbol
        if self._match_type("FN"):
            result = self._parse_fn(prefixes, class_name)
            if result is None:
                return None
            command, symbol = result
            symbol[0] = "METHOD"
            symbol[1] = class_name + " " + symbol[1]
            command.append("CALL ADD_METHOD")
            return command, symbol
        self._raise("Unexpected token: " + self._get_current().text)
        return None

    def _parse_name(self) -> Optional[str]:
        """
        解析点分隔的名称（命名空间路径）。
        :return: 完整的点分隔名称字符串。
        """
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
        """解析操作语句（表达式语句）。"""
        expr_result = self._collect_until(["SEMICOLON"])
        if expr_result is None:
            return None
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        parsing_slice = self._add_parsing_slice(expr_result)
        # self._expr_count += 1
        return ["MAKE STMT OP", parsing_slice, "CALL SET_EXPR"], []

    def _parse_prefixes(self, matches: list[str]) -> Optional[list[str]]:
        """
        解析修饰符前缀列表。
        :param matches: 允许的修饰符列表。
        :return: 解析到的修饰符列表。
        """
        prefixes: list[str] = []
        while self._match_types(matches):
            token = self._get_current()
            if token in prefixes:
                self._raise(f"Unexpected prefix: {token.text}")
                return None
            prefixes.append(token.text)
            self._next()
        return prefixes

    @_set_loc_command
    def _parse_property(self, prefixes: list[str]) -> Optional[tuple[list[str], list[str]]]:
        """解析类属性定义。"""
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
        start_line, start_col, _, _ = self._src_info.location_tuple
        type_decl: Optional[str] = self._parse_type()
        if type_decl is None:
            return None
        if not self._match_type("IDENTIFIER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        prop_name: str = self._get_current().text
        self._next()
        commands: list[str] = []
        if self._match_type("ASSIGN"):
            # 带初始值（静态属性必须有初始值，动态属性不允许）
            if not is_static:
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
            expr_results = self._collect_until(["SEMICOLON"])
            if expr_results is None:
                return None
            if not self._match_type("SEMICOLON"):
                self._raise("Unexpected token: " + self._get_current().text)
                return None
            self._next()
            commands = [self._add_parsing_slice(expr_results), f"CALL ADD_STATIC_PROP {prop_name}"]
        elif self._match_type("SEMICOLON"):
            self._next()
        else:
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        _, _, end_line, end_col = self._src_info.location_tuple
        symbol = f"{start_line}:{start_col}:{end_line}:{end_col} {type_decl}%{prop_name} {' '.join(prefixes)}"
        return commands, [symbol]

    @_set_loc_command
    def _parse_del_super_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析del(super);语句（wrapper类的__del__中释放普通成员）。"""
        self._next()
        if not self._match_type("L_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("SUPER"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("R_BRACKET"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return ["MAKE STMT DEL_SUPER"], []

    @_set_loc_command
    def _parse_return_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析return语句。"""
        if not self._match_type("RETURN"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        return ["MAKE STMT RETURN"], []

    @_set_loc_command
    def _parse_sq(self, prefixes: list[str], cls_name: str = "") -> Optional[tuple[list[str], list[str]]]:
        """解析序列（sq）函数定义。"""
        return self._parse_func(prefixes, "SQ", cls_name=cls_name)

    @_set_loc_command
    def _parse_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析语句（支持async修饰）。"""
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
        """解析非async语句（分派到各类具体语句解析器）。"""
        if self._match_type("RETURN"):
            return self._parse_return_stmt()
        if self._match_type("DEL"):
            return self._parse_del_super_stmt()
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
        """解析throw语句。"""
        if not self._match_type("THROW"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        to_throw_expr_result = self._parse_expr()
        if to_throw_expr_result is None:
            return None
        if not self._match_type("SEMICOLON"):
            self._raise("Unexpected token: " + self._get_current().text)
            return None
        self._next()
        return ["MAKE STMT THROW", *to_throw_expr_result, "CALL SET_EXPR"], []

    @_set_loc_command
    def _parse_try_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析try语句。"""
        if not self._match_type("TRY"):
            self._raise("Expected try. Unexpected token: " + self._get_current().text)
            return None
        self._next()
        block_result = self._parse_block_stmt(False)
        if block_result is None:
            return None
        return ["MAKE STMT TRY"] + block_result[0] + ["CALL SET_STMT"], []

    def _parse_type(self) -> Optional[str]:
        """
        解析类型表达式（返回类型名称字符串）。
        :return: 类型名称字符串。
        """
        l_bracket_count: int = 0
        l_angle_bracket_count: int = 0
        l_square_bracket_count: int = 0
        is_tuple: bool = False
        is_array: bool = False
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
            elif "L_SQUARE_BRACKET" in token.type:
                l_square_bracket_count += 1
            elif "R_SQUARE_BRACKET" in token.type:
                l_square_bracket_count -= 1
            if l_bracket_count == 0 and l_angle_bracket_count == 0 and l_square_bracket_count == 0:
                self._next()
                if self._match_type("L_SQUARE_BRACKET"):
                    result.append(self._get_current().text)
                    l_square_bracket_count += 1
                    is_array = True
                    self._next()
                    continue
                if not is_array and not is_tuple and self._match_type("GENERIC_START"):
                    result.append(self._get_current().text)
                    l_angle_bracket_count += 1
                    self._next()
                    continue
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
                    if self._match_type("R_BRACKET"):
                        # 空返回类型 ()
                        result.append(self._get_current().text)
                        self._next()
                        return "".join(result)
                    dst_type = self._parse_type()
                    if dst_type is None:
                        return None
                    if not self._match_type("R_BRACKET"):
                        self._raise("Unexpected token: " + token.text)
                        return None
                    result.append(dst_type)
                    result.append(self._get_current().text)
                    self._next()
                    return "".join(result)
                return "".join(result)
            if l_bracket_count < 0 or l_angle_bracket_count < 0 or l_square_bracket_count < 0:
                self._raise(f"Unexpected token {token.text}")
                return None
            self._next()
        self._raise("Unexpected EOF")
        return None

    @_set_loc_command
    def _parse_typedef_stmt(self) -> Optional[tuple[list[str], list[str]]]:
        """解析类型别名定义语句（using）。"""
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
        """解析类型-名称列表（类型声明中的参数列表）。"""
        expect_comma: bool = False
        command: list[str] = []
        symbol: list[str] = []
        while True:
            if self._match_types(end_symbols):
                break
            # 左括号表示构造函数调用形式的声明（TypeName var(...)），
            # 仅在已解析完至少一个类型-变量对后生效
            if expect_comma and self._match_type("L_BRACKET"):
                break
            if expect_comma and not self._match_type("COMMA"):
                self._raise("Expected comma. Unexpected token: " + self._get_current().text)
                return None
            if expect_comma and self._match_type("COMMA"):
                self._next()
                expect_comma = False
            else:
                if self._match_type("THIS"):
                    if len(symbol) > 0:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    self._next()
                    symbol.append("THIS")
                    continue
                type_decl = self._parse_type()
                if type_decl is None:
                    return None
                if type_decl == "void":
                    # void类型等效于()：不产生参数或返回值
                    expect_comma = True
                    continue
                if not self._match_type("IDENTIFIER"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                symbol.append(type_decl + "%" + self._get_current().text)
                command.append(f"MAKE EXPR TYPE_REF {type_decl}")
                command.append(f"CALL ADD_VAR {self._get_current().text}")
                expect_comma = True
                self._next()
        return command, symbol

    def _parse_type_name_list_with_default(self, end_symbols: list[str]) -> Optional[tuple[list[str], list[str], list[str]]]:
        """解析类型-名称列表（类型声明中的参数列表），但是带有默认参数。"""
        expect_comma: bool = False
        command: list[str] = []
        args_symbol: list[str] = []
        defaults: list[str] = []
        while True:
            if self._match_types(end_symbols):
                break
            if expect_comma and not self._match_type("COMMA"):
                self._raise("Expected comma. Unexpected token: " + self._get_current().text)
                return None
            if expect_comma and self._match_type("COMMA"):
                self._next()
                expect_comma = False
            else:
                if self._match_type("THIS"):
                    if len(args_symbol) > 0:
                        self._raise("Unexpected token: " + self._get_current().text)
                        return None
                    self._next()
                    args_symbol.append("THIS")
                    continue
                type_decl = self._parse_type()
                if type_decl is None:
                    return None
                if not self._match_type("IDENTIFIER"):
                    self._raise("Unexpected token: " + self._get_current().text)
                    return None
                arg_name = self._get_current().text
                args_symbol.append(type_decl + "%" + arg_name)
                expect_comma = True
                self._next()
                if self._match_type("ASSIGN"):
                    self._next()
                    expr_tokens = self._collect_until(["COMMA", "R_BRACKET"])
                    if expr_tokens is None:
                        return None
                    command.append(self._add_parsing_slice(expr_tokens))
                    command.append(f"CALL SET_DEFAULT_PARAM {arg_name}")
                    defaults.append(arg_name)
        return command, args_symbol, defaults

    def _raise(self, message: str) -> None:
        """
        记录解析错误日志。
        :param message: 错误消息。
        """
        self._logger.error(str(CompilerException(message, self._src_info)))
        
    @staticmethod
    def _remove_file_lock(path: str) -> None:
        """
        移除文件解析锁。
        :param path: 文件路径。
        """
        remove_file_lock(path)
    
    @staticmethod
    def _set_file_lock(path: str) -> bool:
        """
        设置文件解析锁（防止并发解析）。
        :param path: 文件路径。
        :return: 锁文件已存在（其他线程正在解析）时返回False，否则返回True。
        """
        return set_file_lock(path)

    def __back_loc(self) -> None:
        """
        向后更新源代码位置信息。
        """
        token: Token = self._get_current()
        self._src_info.set_loc(*token.src_info.location_tuple)

    def _get_import_prefix(self, id_list: list[str]) -> list[str]:
        """
        获取标识符中匹配导入路径的前缀部分。
        :param id_list: 标识符分段列表。
        :return: 替换后的标识符列表。
        """
        if len(id_list) == 1:
            # 单一标识符也可能来自from...import（如compute_0(...)）
            if id_list[0] in self._imports:
                return [self._imports[id_list[0]]]
            return id_list
        for i in range(len(id_list), 0, -1):
            prefix: str = ".".join(id_list[:i])
            if prefix in self._imports:
                return [self._imports[prefix]] + id_list[i:]
        return id_list

    def __get_segments_num(self, token_buffer: list[Token]) -> Optional[int]:
        """
        计算记号缓冲区中的类型-名称段数量。
        :param token_buffer: 记号缓冲区。
        :return: 段数量。
        """
        bracket_level: int = 0
        segments_num: int = 0
        local_token_buffer: list[Token] = []
        last_was_dot: bool = False
        for token in token_buffer:
            if bracket_level == 0:
                if "ARROW" in token.type:
                    if local_token_buffer and "R_BRACKET" in local_token_buffer[-1].type:
                        local_token_buffer.append(token)
                    else:
                        local_token_buffer.clear()
                elif "L_BRACKET" in token.type:
                    if local_token_buffer and "ARROW" in local_token_buffer[-1].type:
                        local_token_buffer.append(token)
                    else:
                        local_token_buffer.clear()
                elif "DOT" not in token.type:
                    # DOT 连接的限定名链（如 collections.print_msg_0）作为一个整体只计一段
                    if not last_was_dot:
                        segments_num += 1
                last_was_dot = "DOT" in token.type
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

    @staticmethod
    def __is_generic_call(token_buffer: list[Token]) -> bool:
        """
        判断记号缓冲区是否为泛型函数调用语句（IDENTIFIER ::<...>(...)。
        :param token_buffer: 记号缓冲区。
        :return: 是否为泛型调用。
        """
        angle_depth: int = 0
        for i in range(1, len(token_buffer)):
            if "GENERIC_START" in token_buffer[i].type:
                angle_depth += 1
            elif "GT" in token_buffer[i].type:
                angle_depth -= 1
            elif "R_SHIFT" in token_buffer[i].type:
                angle_depth -= 2
            if angle_depth < 0:
                return False
            if angle_depth == 0:
                # 泛型参数列表结束：之后紧跟 ( 则为调用，否则为类型声明
                if i + 1 >= len(token_buffer):
                    return False
                return "L_BRACKET" in token_buffer[i + 1].type
        return False

    def __next_loc(self, token: Optional[Token] = None) -> None:
        """
        向前更新源代码位置信息。
        :param token: 可选的记号对象，为None则使用当前记号。
        """
        token: Token = self._get_current() if token is None else token
        self._src_info.set_loc(*token.src_info.location_tuple)
        self._src_info.set_text(token.src_info.src_text)
