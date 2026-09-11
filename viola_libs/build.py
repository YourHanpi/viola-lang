# -*- coding: utf-8 -*-
"""Viola运行时库构建脚本。

用法：
    python build.py <项目目录> [-i 入口文件] [-o 输出目录] [--run] [--clean]

流程：
    1. 使用violac将项目（.vla）编译为C代码；
    2. 使用gcc将生成的C代码与本运行库的C源文件一起编译、链接为可执行文件；
    3. 可选执行生成的可执行文件。
"""
import os
import shutil
import subprocess
import sys

# 本脚本所在目录（viola_libs）
VIOLA_LIBS_DIR = os.path.dirname(os.path.abspath(__file__))
# violac编译器入口
VIOLAC_DIR = os.path.join(os.path.dirname(VIOLA_LIBS_DIR), "violac")
VIOLAC_MAIN = os.path.join(VIOLAC_DIR, "src", "main.py")
# 运行库C源文件
RUNTIME_SOURCES = [
    os.path.join("viola", "runtime.c"),
    os.path.join("viola", "threads.c"),
    os.path.join("viola", "lang", "global_resource_manager.c"),
    os.path.join("viola", "lang", "string.c"),
    os.path.join("viola", "lang", "exception.c"),
    os.path.join("viola", "io", "print.c"),
    os.path.join("viola", "io", "file.c"),
    os.path.join("viola", "math.c"),
    os.path.join("viola", "os.c"),
    os.path.join("viola", "os", "path.c"),
    os.path.join("viola", "stat.c"),
]
GCC_FLAGS = ["-std=gnu99", "-Wall", "-Wextra", "-O2",
             # 规避历史问题（见run_full_test.py中的说明）；
             # 该问题的根因（子类结构体字段布局错位导致的未定义行为）已修复，
             # 在无-fno-inline的-O2下异常测试亦通过，是否移除待确认
             "-fno-inline"]


def get_c_sources(output_dir: str) -> list[str]:
    """收集输出目录中所有生成的.c文件（__main__.c与各模块的.c）。"""
    sources: list[str] = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.endswith(".c"):
                sources.append(os.path.join(root, f))
    return sources


def main() -> None:
    args: list[str] = sys.argv[1:]
    if len(args) < 1:
        print(__doc__)
        return
    project_dir: str = os.path.abspath(args[0])
    entry: str = ""
    output_dir: str = os.path.join(project_dir, "viola-compiled")
    do_run: bool = "--run" in args
    clean: bool = "--clean" in args
    for i, arg in enumerate(args):
        if arg.startswith("-i="):
            entry = arg[3:]
        elif arg.startswith("-o="):
            output_dir = os.path.abspath(arg[3:])
    if entry == "":
        # 默认入口：项目目录中的main.vla
        entry = os.path.join(project_dir, "main.vla")
    if clean and os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    # 设置库搜索路径，使 import viola.xxx 可用
    env = dict(os.environ)
    env["VIOLA_HOME"] = VIOLA_LIBS_DIR + (";" if os.name == "nt" else ":") + env.get("VIOLA_HOME", "")
    # 1. viola -> C
    compile_cmd = [
        sys.executable, VIOLAC_MAIN, "compile", project_dir,
        f"-i={entry}", f"-o={output_dir}", "-j=4",
        "--clear-cache", "--clear-output", "--clear-log"
    ]
    print(" ".join(compile_cmd))
    result = subprocess.run(compile_cmd, env=env, text=True)
    if result.returncode != 0:
        print("violac编译失败", file=sys.stderr)
        sys.exit(1)
    # 2. gcc 编译链接
    sources: list[str] = get_c_sources(output_dir)
    sources.extend(os.path.join(VIOLA_LIBS_DIR, s) for s in RUNTIME_SOURCES)
    executable = os.path.join(output_dir, "main")
    if os.name == "nt":
        executable += ".exe"
    gcc_cmd = ["gcc", *GCC_FLAGS,
               f"-I{os.path.join(VIOLA_LIBS_DIR, 'viola')}",
               # 嵌套模块（如viola/os.vla.h）以"viola/io.vla.h"形式包含其他
               # 模块头文件，需将输出目录加入头文件搜索路径
               f"-I{output_dir}",
               f"-include{os.path.join(VIOLA_LIBS_DIR, 'viola', 'runtime.h')}",
               "-o", executable, *sources, "-lpthread"]
    print("gcc", " ".join(GCC_FLAGS), "-o", executable, "<N个源文件>")
    result = subprocess.run(gcc_cmd, text=True)
    if result.returncode != 0:
        print("gcc编译失败", file=sys.stderr)
        sys.exit(1)
    print(f"构建成功: {executable}")
    # 3. 可选运行
    if do_run:
        print("=== 运行输出 ===")
        result = subprocess.run([executable])
        print("=== 退出码:", result.returncode, "===")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
