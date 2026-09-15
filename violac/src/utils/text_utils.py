# -*- coding: utf-8 -*-
"""文本处理的轻量工具（不依赖re模块）。

为将来能够自举，编译器不使用第三方库，也不使用C语言没有原生实现的
标准库功能（包括正则表达式，见README_zh.md与versions_dev_plan_zh.md
"漏洞修复"），故原先使用re模块的少量文本处理改为此处的手写实现。
"""


def sanitize_c_identifier(text: str, keep: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                             "abcdefghijklmnopqrstuvwxyz0123456789_$",
                          replacement: str = "$") -> str:
    """把text中不属于keep的字符逐个替换为replacement，返回新字符串。

    等价于原先的re.sub(r"[^A-Za-z0-9_$]", "$", text)：逐个字符判断，
    非ASCII字符一律视为需要替换（Python的str.isalnum对非ASCII字符也返回True，
    故不能直接使用isalnum）。
    """
    return "".join(c if c in keep else replacement for c in text)


def strip_trailing_overload_suffix(name: str) -> str:
    """去掉名称末尾连续的重载序号（形如"$_0"、"$_12"），返回裸名称。

    等价于原先的re.sub(r"(\\$_\\d+)+$", "", name)：末尾可能连续出现多个序号
    （声明时的前置序号与set_cls追加的序号），故需反复剥离直至不再变化。
    """
    end: int = len(name)
    while True:
        stripped: int = _strip_one_overload_suffix(name, end)
        if stripped == end:
            return name[:end]
        end = stripped


def _strip_one_overload_suffix(name: str, end: int) -> int:
    """若name[:end]以"$_<数字>"结尾，返回剥离该序号后的新末尾位置，否则返回end。"""
    digit_end: int = end
    while digit_end > 0 and name[digit_end - 1].isdigit() and name[digit_end - 1].isascii():
        digit_end -= 1
    if digit_end == end:
        return end
    # 数字之前应当是"$_"
    if digit_end < 2 or name[digit_end - 1] != "_" or name[digit_end - 2] != "$":
        return end
    return digit_end - 2


def find_placeholder(text: str, prefix: str = "@", suffix: str = "@") -> str:
    """查找文本中形如"@名称@"的占位符（名称由ASCII字母与下划线组成）。

    等价于原先的re.findall(r"@[a-zA-Z_]+@", text)的首个匹配，未找到时返回空串。
    用于检查模板替换后是否仍有未展开的占位符。
    """
    index: int = 0
    while True:
        start: int = text.find(prefix, index)
        if start < 0:
            return ""
        pos: int = start + len(prefix)
        name_end: int = pos
        while name_end < len(text) and _is_ascii_alpha_or_underscore(text[name_end]):
            name_end += 1
        if name_end > pos and text.startswith(suffix, name_end):
            return text[start:name_end + len(suffix)]
        index = start + 1


def _is_ascii_alpha_or_underscore(c: str) -> bool:
    """判断字符是否为ASCII字母或下划线（等价于正则的[a-zA-Z_]）。"""
    return c == "_" or ("a" <= c <= "z") or ("A" <= c <= "Z")


def renumber_marks(text: str, prefix: str = "$$_MARK_") -> str:
    """将文本中的调试标记占位名（$$_MARK_<数字>_<数字>）按出现顺序重编号。

    等价于原先的re.sub(r"\\$\\$_MARK_\\d+_\\d+", ...)：占位名由符号表序号与
    符号表内编号构成，并行编译下同一符号在不同线程中的编号可能不同；按各自
    出现的顺序统一重编号，可使同一编译单元内的标记编号与线程交错无关
    （见开发疑问记录117、123）。同一占位名只分配一个编号。
    """
    mapping: dict[str, str] = {}
    result: list[str] = []
    index: int = 0
    while True:
        start: int = text.find(prefix, index)
        if start < 0:
            result.append(text[index:])
            return "".join(result)
        end: int = _match_mark_placeholder(text, start, prefix)
        if end < 0:
            # 不是占位名：原样输出该前缀，继续向后查找
            result.append(text[index:start + len(prefix)])
            index = start + len(prefix)
            continue
        name: str = text[start:end]
        if name not in mapping:
            mapping[name] = f"$$_MARK_{len(mapping)}"
        result.append(text[index:start])
        result.append(mapping[name])
        index = end


def _match_mark_placeholder(text: str, start: int, prefix: str) -> int:
    """若text[start:]是"<prefix><数字>_<数字>"，返回其结束位置，否则返回-1。"""
    pos: int = start + len(prefix)
    pos = _skip_ascii_digits(text, pos)
    if pos == start + len(prefix) or not text.startswith("_", pos):
        return -1
    second_start: int = pos + 1
    pos = _skip_ascii_digits(text, second_start)
    if pos == second_start:
        return -1
    return pos


def _skip_ascii_digits(text: str, pos: int) -> int:
    """从pos起跳过连续的ASCII数字，返回第一个非数字字符的位置。"""
    while pos < len(text) and "0" <= text[pos] <= "9":
        pos += 1
    return pos
