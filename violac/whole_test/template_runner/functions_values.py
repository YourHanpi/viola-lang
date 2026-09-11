"""Viola 0.1函数值（Function结构体）与闭包按参数名传参测试。

Usage:
    python functions_values.py <project_id>

Generates: template_projects/functions_values_<project_id>/main.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "functions_values", "functions_values.vla")
    output_dir = os.path.join(project_root, "template_projects", f"functions_values_{project_id}")
    os.makedirs(output_dir, exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("${PID}", project_id)
    with open(os.path.join(output_dir, "functions_values.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
