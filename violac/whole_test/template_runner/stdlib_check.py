"""Standard library spot-check template runner.

Usage:
    python stdlib_check.py <project_id>

Generates: template_projects/stdlib_check_<project_id>/stdlib_check.vla
"""

import os
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "stdlib_check", "stdlib_check.vla")
    output_dir = os.path.join(project_root, "template_projects", f"stdlib_check_{project_id}")
    os.makedirs(output_dir, exist_ok=True)

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    with open(os.path.join(output_dir, "stdlib_check.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
