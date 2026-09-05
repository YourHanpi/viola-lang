"""Random filler for recursion test template.

Usage:
    python recursion.py <project_id>

Generates: template_projects/recursion_<project_id>/recursion.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "recursion")
    output_dir = os.path.join(project_root, "template_projects", f"recursion_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "recursion.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${FACT_N}", str(random.randint(1, 10)))
    content = content.replace("${FIB_N}", str(random.randint(1, 15)))
    content = content.replace("${SUM_START}", str(random.randint(1, 20)))
    content = content.replace("${SUM_END}", str(random.randint(30, 50)))
    content = content.replace("${PRINT_MESSAGE}", f"Recursion test #{pid} completed")

    output_path = os.path.join(output_dir, "recursion.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python recursion.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
