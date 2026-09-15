"""Random filler for enums test template.

Usage:
    python enums.py <project_id>

Generates: template_projects/enums_<project_id>/enums.vla
"""

import os
import random
import sys


ENUM_NAMES = ["Color", "Status", "Mode", "Level", "Flag", "Kind", "Signal", "Phase"]
ITEM_NAMES = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
              "Iota", "Kappa", "Lambda", "Sigma"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "enums")
    output_dir = os.path.join(project_root, "template_projects", f"enums_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "enums.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    enum_1, enum_2 = random.sample(ENUM_NAMES, 2)
    items = random.sample(ITEM_NAMES, 6)
    base = random.randint(1, 20)

    content = content.replace("${ENUM_1}", enum_1)
    content = content.replace("${ENUM_2}", enum_2)
    for i, item in enumerate(items):
        content = content.replace(f"${{ITEM_{i + 1}}}", item)
    content = content.replace("${BASE}", str(base))

    output_path = os.path.join(output_dir, "enums.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python enums.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
