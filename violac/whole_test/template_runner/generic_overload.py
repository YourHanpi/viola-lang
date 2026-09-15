"""Random filler for generic_overload test template.

Usage:
    python generic_overload.py <project_id>

Generates: template_projects/generic_overload_<project_id>/generic_overload.vla
"""

import os
import random
import sys


CLASS_NAMES = ["Holder", "Store", "Bucket", "Crate", "Tray", "Shelf", "Stack", "Pool"]
TYPE_PARAMS = ["T", "E", "V"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "generic_overload")
    output_dir = os.path.join(project_root, "template_projects", f"generic_overload_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "generic_overload.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    content = content.replace("${GENERIC_CLASS}", random.choice(CLASS_NAMES))
    content = content.replace("${TYPE_PARAM}", random.choice(TYPE_PARAMS))
    values = random.sample(range(1, 99), 4)
    for i, value in enumerate(values):
        content = content.replace(f"${{VALUE_{i + 1}}}", str(value))

    output_path = os.path.join(output_dir, "generic_overload.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generic_overload.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
