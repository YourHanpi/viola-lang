"""Viola 0.1关键字与内置功能测试（export/final/impl/interface/访问修饰符/return/static/unsafe/wrapper/_/Pointer/void）。

Usage:
    python keywords.py <project_id>

Generates: template_projects/keywords_<project_id>/keywords.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "keywords", "keywords.vla")
    output_dir = os.path.join(project_root, "template_projects", f"keywords_{project_id}")
    os.makedirs(output_dir, exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("${PID}", project_id)
    with open(os.path.join(output_dir, "keywords.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
