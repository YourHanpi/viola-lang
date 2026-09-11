# -*- coding: utf-8 -*-
"""Viola整体测试（完整流程）：viola -> C -> gcc编译链接 -> 运行。

用法：
    python run_full_test.py [skips]

对 template_projects 中的每个工程执行：
    1. violac compile（生成C代码）；
    2. gcc 将生成的C代码与运行库（viola_libs）编译链接为可执行文件；
    3. 运行可执行文件，检查退出码。
"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "template_projects")
OUTPUT_ROOT = os.path.join(BASE_DIR, "test_compiled")
COMPILER = os.path.join(BASE_DIR, "..", "src", "main.py")
VIOLA_LIBS = os.path.join(BASE_DIR, "..", "..", "viola_libs")

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
             # 历史规避项：此前观察到异常处理代码与gcc的-O2内联交互异常；
             # 其根因为子类结构体字段布局与父类不一致（未定义行为，已修复，
             # 见开发疑问记录），在无-fno-inline的-O2下异常测试亦通过，
             # 是否移除该规避项待确认
             "-fno-inline"]


def get_c_sources(output_dir: str) -> list[str]:
    sources: list[str] = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.endswith(".c"):
                sources.append(os.path.join(root, f))
    return sources


def test_one(project: str) -> bool:
    if os.path.isabs(project):
        project_dir = project
        project = os.path.basename(project)
    else:
        project_dir = os.path.join(PROJECTS_DIR, project)
    output_dir = os.path.join(OUTPUT_ROOT, project)
    entries = sorted(os.listdir(project_dir))
    main_file = os.path.join(project_dir, "main.vla") if "main.vla" in entries else \
        os.path.join(project_dir, next(e for e in entries if not e.startswith("__")))
    env = dict(os.environ)
    env["VIOLA_HOME"] = VIOLA_LIBS + (";" if os.name == "nt" else ":") + env.get("VIOLA_HOME", "")
    # 清除运行库目录旁的缓存文件（viola_libs模块的缓存在工作区之外，
    # --clear-cache无法覆盖，残留缓存会导致模块被错误跳过）
    for lib_root in VIOLA_LIBS.split(";" if os.name == "nt" else ":"):
        for root, _, files in os.walk(lib_root):
            for f in files:
                if f.endswith((".vlatoken", ".vlacmd", ".vlacmd0", ".vlaexpr", ".vlasymtab", ".vlasymt")):
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
    # 清除工程目录内的缓存（编译器修改后源文件mtime不变，缓存可能过期，
    # 导致解析命令与符号表与编译器版本不一致）
    for cache_root in [PROJECTS_DIR, os.path.join(BASE_DIR, "runtime_test_project")]:
        for root, _, files in os.walk(cache_root):
            for f in files:
                if f.endswith((".vlatoken", ".vlacmd", ".vlacmd0", ".vlaexpr", ".vlasymtab", ".vlasymt")):
                    try:
                        os.remove(os.path.join(root, f))
                    except OSError:
                        pass
    # 编译器也可能把工作区外模块的缓存写到与源文件相邻的位置
    # （路径中的..段会把缓存解析到violac/viola_libs等目录），一并清除
    for extra in [os.path.join(COMPILER, "..", "..", "viola_libs")]:
        extra = os.path.abspath(extra)
        if os.path.isdir(extra):
            for root, _, files in os.walk(extra):
                for f in files:
                    if f.endswith((".vlatoken", ".vlacmd", ".vlacmd0", ".vlaexpr", ".vlasymtab", ".vlasymt")):
                        try:
                            os.remove(os.path.join(root, f))
                        except OSError:
                            pass
    # 1. viola -> C
    r = subprocess.run(
        [sys.executable, COMPILER, "compile", project_dir, f"-i={main_file}", f"-o={output_dir}",
         "-j=4", "--clear-cache", "--clear-output", "--clear-log"],
        # 泛型实例化较多的工程（如runtime_test_project）编译耗时较长
        capture_output=True, text=True, timeout=900, env=env
    )
    if r.returncode != 0 or "Critical error" in r.stderr:
        print(f"FAIL(compile) {project}")
        return False
    # 2. gcc 编译链接
    sources = get_c_sources(output_dir)
    sources.extend(os.path.join(VIOLA_LIBS, s) for s in RUNTIME_SOURCES)
    exe = os.path.join(output_dir, "main.exe" if os.name == "nt" else "main")
    r = subprocess.run(
        ["gcc", *GCC_FLAGS, f"-I{os.path.join(VIOLA_LIBS, 'viola')}",
         # 嵌套模块（如viola/os.vla.h）以"viola/io.vla.h"形式包含其他模块头文件，
         # 需将输出目录加入头文件搜索路径
         f"-I{output_dir}",
         f"-include{os.path.join(VIOLA_LIBS, 'viola', 'runtime.h')}",
         "-o", exe, *sources, "-lpthread"],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        print(f"FAIL(gcc) {project}")
        for line in r.stderr.split("\n"):
            if "error" in line:
                print("   ", line.strip()[:150])
                break
        return False
    # 3. 运行
    try:
        r = subprocess.run([exe], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"FAIL(timeout) {project}")
        return False
    if r.returncode != 0:
        print(f"FAIL(run rc={r.returncode}) {project}")
        print("   ", (r.stderr or r.stdout).strip()[:200])
        return False
    print(f"PASS {project}")
    return True


def main() -> None:
    skips = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    projects = sorted(os.listdir(PROJECTS_DIR))
    passed = 0
    failed: list[str] = []
    for i, project in enumerate(projects):
        if i < skips:
            continue
        if test_one(project):
            passed += 1
        else:
            failed.append(project)
    # 0.1运行库综合测试（viola_libs的.vla模块 + main.vla）
    if test_one(os.path.join(BASE_DIR, "runtime_test_project")):
        passed += 1
    else:
        failed.append("runtime_test_project")
    print(f"\nTOTAL: {len(projects) - skips + 1} PASS: {passed} FAIL: {failed}")


if __name__ == "__main__":
    main()
