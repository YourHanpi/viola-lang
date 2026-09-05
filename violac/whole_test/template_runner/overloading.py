"""Random filler for overloading test template.

Usage:
    python overloading.py <project_id>

Generates: template_projects/overloading_<project_id>/overloading.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "overloading")
    output_dir = os.path.join(project_root, "template_projects", f"overloading_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "overloading.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${INT_PREFIX}", f"[INT:{pid}]")
    content = content.replace("${FLOAT_PREFIX}", f"[FLOAT:{pid}]")
    content = content.replace("${STR_PREFIX}", f"[STR:{pid}]")
    content = content.replace("${SEPARATOR}", "")

    content = content.replace("${INT_VAR}", f"int_val_{pid}")
    content = content.replace("${INT_VAL}", str(random.randint(-100, 100)))
    content = content.replace("${FLOAT_VAR}", f"float_val_{pid}")
    content = content.replace("${FLOAT_VAL}", str(round(random.uniform(-100.0, 100.0), 4)))
    content = content.replace("${STR_VAR}", f"str_val_{pid}")
    content = content.replace("${STR_VAL}", f"Test string {pid}")

    content = content.replace("${V1_X}", str(round(random.uniform(-10.0, 10.0), 2)))
    content = content.replace("${V1_Y}", str(round(random.uniform(-10.0, 10.0), 2)))
    content = content.replace("${V2_X}", str(round(random.uniform(-10.0, 10.0), 2)))
    content = content.replace("${V2_Y}", str(round(random.uniform(-10.0, 10.0), 2)))
    content = content.replace("${SCALAR_VAL}", str(round(random.uniform(0.5, 5.0), 2)))
    content = content.replace("${PRINT_MESSAGE}", f"Overloading test #{pid} completed")

    output_path = os.path.join(output_dir, "overloading.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python overloading.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
