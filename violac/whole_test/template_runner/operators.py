"""Random filler for operators test template.

Usage:
    python operators.py <project_id>

Generates: template_projects/operators_<project_id>/operators.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "operators")
    output_dir = os.path.join(project_root, "template_projects", f"operators_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "operators.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    # Operands - ensure b != 0 for division
    a = random.randint(1, 100)
    b = random.choice([x for x in range(1, 50) if a % x == random.choice([0, 0, 0, random.randint(0, a)])]) or random.randint(2, 20)

    content = content.replace("${OP_A}", str(a))
    content = content.replace("${OP_B}", str(b))
    content = content.replace("${SHIFT_AMOUNT}", str(random.randint(0, 4)))
    content = content.replace("${POW_EXP}", str(random.randint(0, 3)))
    content = content.replace("${PRINT_MESSAGE}", f"Operators test #{pid} completed")

    output_path = os.path.join(output_dir, "operators.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python operators.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
