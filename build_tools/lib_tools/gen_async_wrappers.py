# -*- coding: utf-8 -*-
"""为原生（声明式）函数批量生成$async实现与相关元组结构体。

背景（开发疑问记录106）：编译器只为有函数体的定义生成异步包装
（定义处生成`<C名>$async`），声明式（以";"结尾）的原生函数没有异步包装。
本脚本按编译器的异步调用约定为这些函数生成$async实现，供运行库链接。

涉及wrapper类（viola.io.file、viola.os.Stat/StatVFS）的原生函数同样支持：
这些类的结构体定义由运行库头文件runtime.h提供，本文件直接包含该头文件即可
（见开发疑问记录113）。用法见下方“用法”，生成的 native_async.c 覆盖
viola.math / viola.stat / viola.threads / viola.lang / viola.io / viola.os /
viola.os.path。

native_async.c 由本脚本整体重写，因此每次修改运行库声明文件（.vla）后都应
重新生成（生成前会自动校验wrapper类的结构体与runtime.h一致，见开发疑问记录118）。
生成 native_async.c 所用的命令（在viola_libs目录下执行）：

    python ../build_tools/lib_tools/gen_async_wrappers.py \
        viola/math.vla viola/stat.vla viola/threads.vla viola/lang.vla \
        viola/io.vla viola/os.vla viola/os/path.vla \
        --root . -o viola/native_async.c

异步包装的C签名（与编译器生成的完全一致）：
    void <C名>$async(<参数元组> * params, <返回元组> * returns,
                     viola$threads$Listener *listener);

用法：
    python gen_async_wrappers.py <file.vla> [<file.vla> ...] \
        --root <viola_libs目录> -o <输出.c>

    - <file.vla>：含原生函数声明的Viola声明文件（如viola/math.vla）
    - --root：命名空间根目录（.vla路径相对该目录即为命名空间，缺省为当前目录）
    - -o：输出C文件（缺省输出到标准输出）

生成内容：
    1. 各函数参数元组/返回元组的typedef（带与编译器一致的include guard，
       与编译器生成的同名结构体互不冲突）；
    2. 各函数的$async实现（解包参数 → 调用同步函数 → 写回返回值；
       捕获异常时经what()上报并交回调用线程）。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional

# Viola类型名 -> C类型名（覆盖运行库声明文件中所用的类型）
# 值类型（基本数据类型）的C形式即为类型名本身
TYPE_MAP: dict[str, str] = {
    "bool": "viola$lang$bool",
    "int": "viola$lang$int",
    "int8": "viola$lang$int8",
    "int16": "viola$lang$int16",
    "int32": "viola$lang$int32",
    "int64": "viola$lang$int64",
    "uint": "viola$lang$uint",
    "uint8": "viola$lang$uint8",
    "uint16": "viola$lang$uint16",
    "uint32": "viola$lang$uint32",
    "uint64": "viola$lang$uint64",
    "size_t": "viola$lang$uint64",
    "float": "viola$lang$float",
    "float32": "viola$lang$float32",
    "float64": "viola$lang$float64",
    "double": "viola$lang$double",
    "float128": "viola$lang$float128",
    "byte": "viola$lang$uint8",
}
# 对象类型（C层为结构体指针）：形参用一级指针、输出形参用二级指针
OBJECT_TYPE_MAP: dict[str, str] = {
    "string": "viola$lang$string",
    "ptr": "viola$lang$ptr",
    "object": "viola$lang$object",
    "file": "viola$io$file",
    # 运行库中的包装类（wrapper class）：C名称为<命名空间>$<类名>
    "Stat": "viola$os$Stat",
    "StatVFS": "viola$os$StatVFS",
}
# 指针类型（用于决定局部变量是否初始化为NULL）
POINTER_SUFFIX: str = " *"
TUPLE_PREFIX: str = "viola$collections$Tuple"
LISTENER_T: str = "viola$threads$Listener"
EXCEPTION_T: str = "viola$lang$exception$Exception"
PERROR_NAME: str = "viola$io$print$perror"
WHAT_NAME: str = "viola$lang$exception$Exception$what$_0"
EXCEPTION_DEL_NAME: str = "viola$lang$exception$Exception$__del__$_0"

DECL_PATTERN = re.compile(
    r"^\s*(?:sq|fn)\s+([A-Za-z_][A-Za-z0-9_]*)\s*"
    r"\((.*?)\)\s*->\s*\((.*?)\)\s*(?:cname\s+\"([^\"]+)\")?\s*;\s*$")
# 形如 "string text = \"\"" 的参数/返回值：去掉默认值部分
DEFAULT_VALUE_PATTERN = re.compile(r"\s*=.*$")


class FuncDecl:
    """一条原生函数声明。args/rets的元素为(名称, CType)。"""

    def __init__(self, name: str, args: list[tuple[str, "CType"]],
                 rets: list[tuple[str, "CType"]], c_name: str, src: str) -> None:
        self.name: str = name
        self.args: list[tuple[str, CType]] = args
        self.rets: list[tuple[str, CType]] = rets
        self.c_name: str = c_name
        self.src: str = src

    @property
    def async_name(self) -> str:
        return f"{self.c_name}$async"


def c_safe_type_name(c_type: str) -> str:
    """与编译器FunctionTypeName._c_safe_type_name一致的C名安全化。"""
    return re.sub(r"[^A-Za-z0-9_$]", "$", c_type)


def tuple_c_name(types: list[str]) -> str:
    """获取类型元组的C名称（与编译器生成的元组结构体名一致）。"""
    return TUPLE_PREFIX + "$" + "$".join(c_safe_type_name(t) for t in types) \
        if types else TUPLE_PREFIX + "$"


class CType:
    """一个Viola类型对应的C形式。

    name为C类型名（用于元组/数组结构体命名），calling为形参写法，
    assigning为输出形参（返回值）写法，element为数组元素类型（非数组为None）。
    """

    def __init__(self, name: str, calling: str, assigning: str,
                 element: Optional["CType"] = None) -> None:
        self.name: str = name
        self.calling: str = calling
        self.assigning: str = assigning
        self.element: Optional[CType] = element

    @property
    def is_pointer(self) -> bool:
        return self.calling.endswith("*")


def parse_type(text: str, where: str) -> CType:
    """将Viola类型名转换为C类型。"""
    text = text.strip()
    if text.endswith("[]"):
        # 数组类型：C名为<元素C名>$$array，形参为指针，输出形参为二级指针
        element: CType = parse_type(text[:-2], where)
        array_name: str = element.name + "$$array"
        return CType(array_name, array_name + " *", array_name + " **", element)
    if text in TYPE_MAP:
        name: str = TYPE_MAP[text]
        return CType(name, name, name + " *")
    if text in OBJECT_TYPE_MAP:
        name = OBJECT_TYPE_MAP[text]
        return CType(name, name + " *", name + " **")
    raise ValueError(f"{where}: 未知类型 {text!r}（请在TYPE_MAP/OBJECT_TYPE_MAP中补充）")


# 元素为对象（结构体指针）的类型：数组的data字段为二级指针
OBJECT_TYPES: set[str] = {"viola$lang$string", "viola$io$file", "viola$lang$object"}


def gen_array_def(array_type: CType) -> str:
    """生成数组结构体的typedef（带与编译器一致的include guard）。"""
    assert array_type.element is not None
    element: CType = array_type.element
    data_type: str = element.calling + ("*" if element.name in OBJECT_TYPES else "")
    guard = "_VIOLA_ARRAY_T_" + c_safe_type_name(array_type.name)
    return "\n".join([
        f"#ifndef {guard}",
        f"#define {guard}",
        f"typedef struct {array_type.name} {{",
        "\tviola$lang$uint32 $refCount;",
        "\tviola$lang$ptr $parent;",
        f"\t{data_type} data;",
        "\tviola$lang$uint64 size;",
        f"}} {array_type.name};",
        "#endif",
    ])


def parse_decl_line(line: str, namespace: str, overload_counts: dict[str, int]) -> Optional[FuncDecl]:
    """解析一行原生函数声明，非声明行返回None。"""
    match = DECL_PATTERN.match(line)
    if match is None:
        return None
    name, args_text, rets_text, explicit_c_name = match.groups()
    args: list[tuple[str, CType]] = []
    for item in filter(lambda x: x.strip() != "", args_text.split(",")):
        parts = DEFAULT_VALUE_PATTERN.sub("", item.strip()).rsplit(" ", 1)
        if len(parts) != 2:
            raise ValueError(f"{line.strip()}: 参数写法无法识别：{item!r}")
        args.append((parts[1].strip(), parse_type(parts[0], name)))
    rets: list[tuple[str, CType]] = []
    for item in filter(lambda x: x.strip() != "", rets_text.split(",")):
        parts = item.strip().rsplit(" ", 1)
        if len(parts) != 2:
            raise ValueError(f"{line.strip()}: 返回值写法无法识别：{item!r}")
        rets.append((parts[1].strip(), parse_type(parts[0], name)))
    if explicit_c_name is not None:
        c_name = explicit_c_name
    else:
        # 与编译器一致：原生函数的第2个及以后的重载追加$_N序号
        times = overload_counts.get(name, 0)
        overload_counts[name] = times + 1
        c_name = f"{namespace}${name}" + (f"$_{times}" if times > 0 else "")
    return FuncDecl(name, args, rets, c_name, line.strip())


def namespace_of(path: str, root: str) -> str:
    """由.vla路径相对根目录得到命名空间（与编译器的规则一致）。"""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
    rel = os.path.splitext(rel)[0]
    parts = re.split(r"[\\/]", rel)
    return "$".join(parts)


def collect_decls(paths: list[str], root: str) -> list[FuncDecl]:
    """收集所有声明文件中的原生函数声明。"""
    result: list[FuncDecl] = []
    for path in paths:
        namespace = namespace_of(path, root)
        overload_counts: dict[str, int] = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                decl = parse_decl_line(line, namespace, overload_counts)
                if decl is not None:
                    result.append(decl)
    return result


# wrapper类结构体的固定前缀字段（与编译器生成的类结构体布局一致）：
# $refCount/$parent来自object类（见symbol.py中Object.add_property），
# $$vtable由编译器为每个类自动添加
WRAPPER_STRUCT_PREFIX: list[tuple[str, str]] = [
    ("$refCount", "viola$lang$uint32"),
    ("$parent", "viola$lang$ptr"),
    ("$$vtable", "viola$lang$ptr"),
]
# 允许出现在声明字段之后的运行库内部字段（wrapper类的C实现自用，
# 不在.vla中声明）。运行时新增此类字段需同步更新此表。
RUNTIME_INTERNAL_FIELDS: dict[str, list[str]] = {
    "viola$io$file": ["fp", "isPopen"],
}
# 布局不由.vla声明决定的wrapper类：其C结构体由编译器内置类型或运行库
# 自行定义（.vla声明仅列出方法），无法据声明推导字段，故跳过校验。
LAYOUT_NOT_FROM_VLA: dict[str, str] = {
    "viola$lang$string": "编译器内置类型StringTypeName，布局由编译器与运行库维护",
}

WRAPPER_CLASS_PATTERN = re.compile(r"^\s*wrapper\s+class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
CLASS_END_PATTERN = re.compile(r"^\s*\}\s*$")
# 属性声明：可选修饰符 + 类型 + 名称 + ";"
WRAPPER_PROPERTY_PATTERN = re.compile(
    r"^\s*((?:public|private|protected|static)\s+)*([^(){};]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;\s*$")
STRUCT_PATTERN = re.compile(r"typedef\s+struct\s+([A-Za-z0-9_$]+)\s*\{([^}]*)\}\s*([A-Za-z0-9_$]+)\s*;")


def parse_wrapper_classes(paths: list[str], root: str) -> dict[str, list[tuple[str, str]]]:
    """解析.vla文件中的wrapper类声明。

    返回：C结构体名 -> [(字段名, C类型), ...]（不含固定前缀字段）。
    字段顺序与编译器的结构体布局一致（即声明顺序，static属性不进入结构体）。
    """
    result: dict[str, list[tuple[str, str]]] = {}
    for path in paths:
        namespace = namespace_of(path, root)
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        i = 0
        while i < len(lines):
            match = WRAPPER_CLASS_PATTERN.match(lines[i])
            if match is None:
                i += 1
                continue
            cls_name = match.group(1)
            c_name = f"{namespace}${cls_name}"
            fields: list[tuple[str, str]] = []
            i += 1
            while i < len(lines) and CLASS_END_PATTERN.match(lines[i]) is None:
                body = lines[i].strip()
                if body != "" and not body.startswith("//") and "(" not in body:
                    prop = WRAPPER_PROPERTY_PATTERN.match(lines[i])
                    if prop is not None:
                        modifiers = prop.group(1) or ""
                        if "static" not in modifiers:
                            c_type = parse_type(prop.group(2), f"{path}:{cls_name}")
                            fields.append((prop.group(3), c_type.calling))
                i += 1
            if c_name in result:
                raise ValueError(f"{path}: wrapper类 {cls_name} 重复声明（C名 {c_name}）")
            result[c_name] = fields
    return result


def parse_runtime_structs(path: str) -> dict[str, list[tuple[str, str]]]:
    """解析runtime.h中的结构体定义。

    返回：结构体名 -> [(字段名, C类型), ...]（按定义顺序）。
    """
    with open(path, encoding="utf-8") as f:
        # 先去掉注释，避免结构体外的说明文字干扰匹配
        text = re.sub(r"/\*.*?\*/", "", f.read(), flags=re.S)
    result: dict[str, list[tuple[str, str]]] = {}
    for match in STRUCT_PATTERN.finditer(text):
        struct_name, body, alias = match.group(1), match.group(2), match.group(3)
        if struct_name != alias:
            # typedef struct X {...} Y;形式（如匿名结构体）不作为wrapper类定义
            continue
        fields: list[tuple[str, str]] = []
        for field_text in body.split(";"):
            field_text = " ".join(field_text.split())
            if field_text == "":
                continue
            # 字段形如"<类型> <名称>"，声明符可能带*（如"viola$lang$uint16 *data"）
            field_match = re.match(r"^(.+?)\s*(\**)\s*([A-Za-z_$][A-Za-z0-9_$]*)$", field_text)
            if field_match is None:
                raise ValueError(f"{path}: 无法解析结构体 {struct_name} 的字段：{field_text!r}")
            field_type: str = (field_match.group(1).strip() + " " + field_match.group(2)).strip()
            fields.append((field_match.group(3), field_type))
        result[struct_name] = fields
    return result


def check_wrapper_structs(paths: list[str], root: str, runtime_header: str) -> list[str]:
    """校验.vla中的wrapper类声明与runtime.h中的结构体定义是否一致。

    两份定义必须字段顺序与类型完全一致（编译器与运行库按相同偏移读写，
    不一致时不会报错而是静默读写错误字段，见开发疑问记录113/118）。
    返回不一致的说明列表，为空表示一致。
    """
    if not os.path.exists(runtime_header):
        return [f"运行库头文件不存在：{runtime_header}"]
    declared = parse_wrapper_classes(paths, root)
    structs = parse_runtime_structs(runtime_header)
    problems: list[str] = []
    for c_name, fields in sorted(declared.items()):
        if c_name in LAYOUT_NOT_FROM_VLA:
            # 布局不由.vla声明决定（见LAYOUT_NOT_FROM_VLA的说明）
            continue
        expected: list[tuple[str, str]] = WRAPPER_STRUCT_PREFIX + fields
        actual: Optional[list[tuple[str, str]]] = structs.get(c_name)
        if actual is None:
            problems.append(f"{c_name}: {runtime_header} 中缺少该wrapper类的结构体定义")
            continue
        if len(actual) < len(expected):
            problems.append(
                f"{c_name}: {runtime_header} 中的字段过少（需至少{len(expected)}个，实际{len(actual)}个）")
            continue
        for index, (want, got) in enumerate(zip(expected, actual)):
            if want != got:
                problems.append(
                    f"{c_name}: 第{index}个字段不一致：.vla声明为 {want[0]} ({want[1]})，"
                    f"runtime.h为 {got[0]} ({got[1]})")
        extras: list[str] = [name for name, _ in actual[len(expected):]]
        allowed: list[str] = RUNTIME_INTERNAL_FIELDS.get(c_name, [])
        if extras != allowed:
            problems.append(
                f"{c_name}: 声明字段之后的运行库内部字段不一致：runtime.h为{extras}，"
                f"预期为{allowed}（若为新增的运行时内部字段，请在RUNTIME_INTERNAL_FIELDS中登记）")
    return problems


def gen_tuple_def(types: list[CType]) -> str:
    """生成元组结构体的typedef（带与编译器一致的include guard）。"""
    name = tuple_c_name([t.name for t in types])
    guard = "_VIOLA_TUPLE_T_" + c_safe_type_name(name)
    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "typedef struct {",
        "\tviola$lang$uint32 $refCount;",
        "\tviola$lang$ptr $parent;",
        "\tviola$lang$uint64 size;",
    ]
    lines += [f"\t{t.calling}  ${i};" for i, t in enumerate(types)]
    lines += ["", f"}} {name};", "#endif"]
    return "\n".join(lines)


def gen_async_wrapper(decl: FuncDecl) -> str:
    """生成一个原生函数的$async实现（与编译器生成的包装体等价）。"""
    args_tuple: str = tuple_c_name([t.name for _, t in decl.args]) + " *"
    rets_tuple: str = tuple_c_name([t.name for _, t in decl.rets]) + " *"
    lines: list[str] = [
        f"void {decl.async_name}({args_tuple} params, {rets_tuple} returns,",
        f"                          {LISTENER_T} *listener) {{",
        f"\t{EXCEPTION_T} *$$exc = listener->exception;",
        # 异步任务开始执行：压入B栈（与编译器生成的包装体一致）
        "\tviola$threads$pushStackB(listener->currentThreadId);",
        "\tdo {",
    ]
    indent = "\t\t"
    # 无参数/无返回值的函数不使用对应的元组，显式标记以避免-Wunused-parameter
    if len(decl.args) == 0:
        lines.append(f"{indent}(void)params;")
    if len(decl.rets) == 0:
        lines.append(f"{indent}(void)returns;")
    for arg_name, arg_type in decl.args:
        init = " = NULL" if arg_type.is_pointer else ""
        lines.append(f"{indent}{arg_type.calling} {arg_name}{init};")
    for ret_name, ret_type in decl.rets:
        init = " = NULL" if ret_type.is_pointer else ""
        lines.append(f"{indent}{ret_type.calling} {ret_name}{init};")
    for i, (arg_name, _) in enumerate(decl.args):
        lines.append(f"{indent}{arg_name} = params->${i};")
        lines.append(f"{indent}if ($$exc) goto $$_async_err;")
    call_args: list[str] = [name for name, _ in decl.args]
    call_args += [f"&{name}" for name, _ in decl.rets]
    call_args.append("listener")
    lines.append(f"{indent}{decl.c_name}({', '.join(call_args)});")
    # 同步调用可能通过listener上报异常
    lines.append(f"{indent}if ($$exc == NULL) {{ $$exc = listener->exception; }}")
    for i, (ret_name, _) in enumerate(decl.rets):
        lines.append(f"{indent}returns->${i} = {ret_name};")
    lines.append(f"{indent}if ($$exc) goto $$_async_err;")
    lines.append(f"{indent}goto $$_async_done;")
    lines.append("\t} while (0);")
    lines.extend([
        "$$_async_err:",
        f"\tif ({EXCEPTION_T_REPORT_COND}) {{",
        f"\t\t{EXCEPTION_T} *exc = $$exc;",
        "\t\t$$exc = NULL;",
        "\t\tlistener->exception = NULL;",
        "\t\tviola$lang$string *$$_msg = NULL;",
        f"\t\t{WHAT_NAME}(exc, &$$_msg, listener);",
        "\t\tif ($$exc == NULL) { $$exc = listener->exception; }",
        f"\t\t{PERROR_NAME}($$_msg, listener);",
        "\t\tif ($$exc == NULL) { $$exc = listener->exception; }",
        "\t\tlistener->exception = exc;",
        f"\t\t{EXCEPTION_DEL_NAME}(exc, listener);",
        "\t\texc = NULL;",
        "\t}",
        "$$_async_done:",
        "$$_async_cleanup: ;",
        "\tif ($$exc) { goto $$_async_cleanup; }",
        "\tviola$threads$popStackB(listener->currentThreadId);",
        "}",
    ])
    return "\n".join(lines)


EXCEPTION_T_REPORT_COND: str = (
    f"viola$lang$convertibleTo($$exc->$$vtable, &{EXCEPTION_T}$$vtable)")


def main() -> int:
    parser = argparse.ArgumentParser(description="为原生函数生成$async实现")
    parser.add_argument("files", nargs="+", help="Viola声明文件（.vla）")
    parser.add_argument("--root", default=".", help="命名空间根目录")
    parser.add_argument("-o", "--output", default="", help="输出C文件")
    parser.add_argument("--list", action="store_true", help="仅列出解析到的声明")
    parser.add_argument("--runtime-header", default="",
                        help="运行库头文件路径（缺省为<root>/viola/runtime.h），"
                             "用于校验wrapper类结构体定义是否一致")
    parser.add_argument("--skip-struct-check", action="store_true",
                        help="跳过wrapper类结构体的一致性校验")
    args = parser.parse_args()

    if args.list:
        decls: list[FuncDecl] = collect_decls(args.files, args.root)
        for decl in decls:
            print(f"{decl.async_name}")
        return 0

    # wrapper类的结构体定义在runtime.h中，与.vla声明是两份必须保持一致的
    # 定义（见开发疑问记录113/118）：不一致时按不同偏移读写且不会报错，
    # 因此生成前先校验
    if not args.skip_struct_check:
        runtime_header: str = args.runtime_header or os.path.join(
            args.root, "viola", "runtime.h")
        problems: list[str] = check_wrapper_structs(args.files, args.root, runtime_header)
        if len(problems) > 0:
            print("wrapper类结构体定义不一致（.vla声明 与 runtime.h）：", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            print("请同步修改两侧定义（或确认后以--skip-struct-check跳过校验）。",
                  file=sys.stderr)
            return 1

    decls = collect_decls(args.files, args.root)

    # 先收集所有需要的元组/数组结构体定义（按C名去重，保持确定顺序：
    # 每次解析生成的CType是新对象，按对象身份去重会输出重复的typedef）
    tuples: list[list[CType]] = []
    tuple_names: set[str] = set()
    arrays: list[CType] = []
    array_names: set[str] = set()
    for decl in decls:
        for types in ([t for _, t in decl.args], [t for _, t in decl.rets]):
            tuple_name: str = tuple_c_name([t.name for t in types])
            if tuple_name not in tuple_names:
                tuple_names.add(tuple_name)
                tuples.append(types)
            for c_type in types:
                if c_type.element is not None and c_type.name not in array_names:
                    array_names.add(c_type.name)
                    arrays.append(c_type)

    blocks: list[str] = [
        "/* 本文件由build_tools/lib_tools/gen_async_wrappers.py生成，请勿手工修改。",
        " * 为原生（声明式）函数提供$async实现与相关的元组/数组结构体",
        " * （见开发疑问记录106）。 */",
        '#include "runtime.h"',
        "",
    ]
    for array_type in arrays:
        blocks.append(gen_array_def(array_type))
        blocks.append("")
    for types in tuples:
        blocks.append(gen_tuple_def(types))
        blocks.append("")
    # 同步函数的原型声明（原生函数的实现位于运行库的其他.c文件，
    # 此处显式声明以便本文件独立编译）
    blocks.append("/* 同步函数原型 */")
    for decl in decls:
        params: list[str] = [f"{t.calling} {n}" for n, t in decl.args]
        params += [f"{t.assigning} {n}" for n, t in decl.rets]
        params.append(f"{LISTENER_T} *listener")
        blocks.append(f"void {decl.c_name}({', '.join(params)});")
    blocks.append("")
    for decl in decls:
        blocks.append(gen_async_wrapper(decl))
        blocks.append("")

    text = "\n".join(blocks)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"已生成 {args.output}（{len(decls)}个$async实现）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
