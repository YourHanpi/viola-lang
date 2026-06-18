# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys


def __test_one_project(compiler_path: str, project_dir: str) -> None:
    if not os.path.exists(os.path.join(project_dir, "__log__")):
        os.mkdir(os.path.join(project_dir, "__log__"))
    if not os.path.exists(os.path.join(project_dir, "__viola_cache__")):
        os.mkdir(os.path.join(project_dir, "__viola_cache__"))
    main_file = os.path.join(project_dir, "main.vla") if len(os.listdir(project_dir)) > 3 else \
        os.path.join(project_dir, os.listdir(project_dir)[0])
    output_dir = os.path.join(os.path.dirname(__file__), "test_compiled", os.path.basename(project_dir))
    print(f"Testing: {project_dir}")
    if os.name == "nt":
        subprocess.run(
            [compiler_path, "compile", f"\"{project_dir}\"", f"-i=\"{main_file}\"", f"-o=\"{output_dir}\"", "-j",
             "--clear-cache", "--clear-output"],
            text=True,
            shell=True,
            timeout=30
        )
    else:
        subprocess.run(
            [compiler_path, "compile", f"\"{project_dir}\"", f"-i=\"{main_file}\"", f"-o=\"{output_dir}\"", "-j",
             "--clear-cache", "--clear-output"],
            text=True,
            shell=True,
            timeout=30
        )


def test_projects(compiler_path: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(base_dir, "template_projects")
    if os.name == "nt":
        subprocess.run(["chcp", "65001"], text=True, shell=True)
    for project in os.listdir(project_dir):
        __test_one_project(compiler_path, os.path.join(project_dir, project))


def main() -> None:
    if len(sys.argv) == 2:
        compiler: str = sys.argv[1]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        compiler = f"{base_dir}/../../shortcuts/violac"
    if compiler.startswith("\"") and compiler.endswith("\"") or compiler.startswith("'") and compiler.endswith("'"):
        compiler = compiler[1:-1]
    test_projects(compiler)


if __name__ == "__main__":
    main()
