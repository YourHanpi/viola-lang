"""Random filler for the regression test template (见开发疑问记录196).

Usage:
    python regression.py <project_id>

Generates: template_projects/regression_<project_id>/regression.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_path = os.path.join(project_root, "template", "regression", "regression.vla")
    output_dir = os.path.join(project_root, "template_projects", f"regression_{project_id}")
    os.makedirs(output_dir, exist_ok=True)

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    # PID作为标识符后缀与字符串内容的一部分，直接用其原文
    content = content.replace("${PID}", str(project_id))
    content = content.replace("${W}", str(random.randint(1, 99)))
    content = content.replace("${H}", str(random.randint(100, 999)))

    with open(os.path.join(output_dir, "regression.vla"), "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else "0")
