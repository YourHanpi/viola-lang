"""Viola 0.1尾递归优化测试（先求值新参数再赋值跳转，求值顺序保持不变）。

Usage:
    python tail_recursion.py <project_id>

Generates: template_projects/tail_recursion_<project_id>/main.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "tail_recursion", "tail_recursion.vla")
    output_dir = os.path.join(project_root, "template_projects", f"tail_recursion_{project_id}")
    os.makedirs(output_dir, exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("${PID}", project_id)
    with open(os.path.join(output_dir, "tail_recursion.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
