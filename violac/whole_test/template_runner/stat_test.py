"""viola.stat 0.1文件状态测试。

Usage:
    python stat_test.py <project_id>

Generates: template_projects/stat_test_<project_id>/main.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "stat_test", "stat_test.vla")
    output_dir = os.path.join(project_root, "template_projects", f"stat_test_{project_id}")
    os.makedirs(output_dir, exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("${PID}", project_id)
    with open(os.path.join(output_dir, "stat_test.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
