"""Random filler for generics test template.

Usage:
    python generics.py <project_id>

Generates: template_projects/generics_<project_id>/generics.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "generics")
    output_dir = os.path.join(project_root, "template_projects", f"generics_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "generics.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${GENERIC_CLASS}", f"Container_{pid}")
    content = content.replace("${TYPE_PARAM}", "T")
    content = content.replace("${PROP_NAME_1}", "data")
    content = content.replace("${PROP_NAME_2}", "id")
    content = content.replace("${TYPE_PARAM_2}", "U")

    content = content.replace("${TYPE_PARAM_A}", "K")
    content = content.replace("${TYPE_PARAM_B}", "V")

    content = content.replace("${INT_INST}", f"int_cont_{pid}")
    content = content.replace("${INT_VAL}", str(random.randint(1, 1000)))
    content = content.replace("${COUNT_VAL}", str(random.randint(1, 100)))
    content = content.replace("${STR_INST}", f"str_cont_{pid}")
    content = content.replace("${STR_VAL}", f"generic_test_{pid}")

    content = content.replace("${PAIR_INT_VAL}", str(random.randint(1, 100)))
    content = content.replace("${PAIR_STR_VAL}", f"pair_value_{pid}")

    content = content.replace("${PRINT_MESSAGE}", f"Generics test #{pid} completed")

    output_path = os.path.join(output_dir, "generics.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generics.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
