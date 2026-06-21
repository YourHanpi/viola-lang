"""Random filler for variables test template.

Usage:
    python variables.py <project_id>

Generates: template_projects/variables_<project_id>/variables.vla
"""

import os
import random
import sys


STR_VALUES = [
    "Hello, Viola!",
    "Testing variables",
    "Variable assignment works",
    "This is a test string",
    "abcdefghijklmnop",
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "variables")
    output_dir = os.path.join(project_root, "template_projects", f"variables_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "variables.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    content = content.replace("${VAR_DECL_1}", f"decl_var_{project_id}")
    content = content.replace("${VAR_VALUE_1}", str(random.randint(-1000, 1000)))
    content = content.replace("${VAR_DEF_1}", f"def_var_{project_id}")
    content = content.replace("${VAR_VALUE_2}", str(random.randint(-1000, 1000)))
    content = content.replace("${STR_VAR}", f"str_var_{project_id}")
    content = content.replace("${STR_VALUE}", random.choice(STR_VALUES))
    content = content.replace("${FLOAT_VAR}", f"float_var_{project_id}")
    content = content.replace("${FLOAT_VALUE}", f"{random.uniform(-100.0, 100.0):.4f}")
    content = content.replace("${BOOL_VAR}", f"bool_var_{project_id}")
    content = content.replace("${BOOL_VALUE}", random.choice(["true", "false"]))
    content = content.replace("${PRINT_MESSAGE}", f"Variables test #{project_id} passed")

    output_path = os.path.join(output_dir, "variables.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python variables.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
