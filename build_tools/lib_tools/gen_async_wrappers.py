# -*- coding: utf-8 -*-
"""为原生（声明式）函数批量生成$async实现与相关元组结构体。

背景（开发疑问记录106）：编译器只为有函数体的定义生成异步包装
（定义处生成`<C名>$async`），声明式（以";"结尾）的原生函数没有异步包装。
本脚本按编译器的异步调用约定为这些函数生成$async实现，供运行库链接。

涉及wrapper类（viola.io.file、viola.os.Stat/StatVFS）的原生函数同样支持：
这些类的结构体定义由运行库头文件runtime.h提供，本文件直接包含该头文件即可
（见开发疑问记录113）。用法见下方“用法”，生成的 native_async.c 覆盖
viola.math / viola.stat / viola.threads / viola.lang / viola.io / viola.os。

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
    args = parser.parse_args()

    decls: list[FuncDecl] = collect_decls(args.files, args.root)
    if args.list:
        for decl in decls:
            print(f"{decl.async_name}")
        return 0

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
