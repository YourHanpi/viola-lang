"""viola.lang.global_resource_manager 0.1请求处理器注册测试。

Usage:
    python grm_test.py <project_id>

Generates: template_projects/grm_test_<project_id>/main.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "grm_test", "grm_test.vla")
    output_dir = os.path.join(project_root, "template_projects", f"grm_test_{project_id}")
    os.makedirs(output_dir, exist_ok=True)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("${PID}", project_id)
    with open(os.path.join(output_dir, "grm_test.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
