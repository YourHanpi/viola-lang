# -*- coding: utf-8 -*-
"""Diagnose gcc link errors for one template project (temporary tool)."""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "template_projects")
OUTPUT_ROOT = os.path.join(BASE_DIR, "test_compiled")
COMPILER = os.path.join(BASE_DIR, "..", "src", "main.py")
VIOLA_LIBS = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "viola_libs"))

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
]
GCC_FLAGS = ["-std=gnu99", "-Wall", "-Wextra", "-O2", "-fcommon"]

project = sys.argv[1] if len(sys.argv) > 1 else "hello_world_0"
project_dir = os.path.join(PROJECTS_DIR, project)
output_dir = os.path.join(OUTPUT_ROOT, project)
entries = sorted(os.listdir(project_dir))
main_file = os.path.join(project_dir, "main.vla") if "main.vla" in entries else \
    os.path.join(project_dir, next(e for e in entries if not e.startswith("__")))
env = dict(os.environ)
env["VIOLA_HOME"] = VIOLA_LIBS + (";" if os.name == "nt" else ":") + env.get("VIOLA_HOME", "")

# 清除工程与运行库的缓存（编译器修改后mtime无法反映变更）
for cache_root in [project_dir, VIOLA_LIBS]:
    for root, _, files in os.walk(cache_root):
        for f in files:
            if f.endswith((".vlatoken", ".vlacmd", ".vlacmd0", ".vlaexpr", ".vlasymtab", ".vlasymt")):
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass

r = subprocess.run(
    [sys.executable, COMPILER, "compile", project_dir,
     f"-i={main_file}", f"-o={output_dir}",
     "-j=4", "--clear-cache", "--clear-output", "--clear-log"],
    capture_output=True, text=True, timeout=120, env=env
)
print("compile rc =", r.returncode)
if r.returncode != 0:
    print(r.stdout[-2000:])
    print(r.stderr[-2000:])
    sys.exit(1)

sources = []
for root, _, files in os.walk(output_dir):
    for f in files:
        if f.endswith(".c"):
            sources.append(os.path.join(root, f))
sources.extend(os.path.join(VIOLA_LIBS, s) for s in RUNTIME_SOURCES)
exe = os.path.join(output_dir, "main.exe" if os.name == "nt" else "main")
r = subprocess.run(
    ["gcc", *GCC_FLAGS, f"-I{os.path.join(VIOLA_LIBS, 'viola')}",
     f"-include{os.path.join(VIOLA_LIBS, 'viola', 'runtime.h')}",
     "-o", exe, *sources, "-lpthread"],
    capture_output=True, text=True, timeout=120
)
print("gcc rc =", r.returncode)
if r.returncode != 0:
    print(r.stderr[-3000:])
    sys.exit(1)
rr = subprocess.run([exe], capture_output=True, text=True, timeout=60)
print("run rc =", rr.returncode)
print(rr.stdout[-800:])
print(rr.stderr[-800:])
