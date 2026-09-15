"""Random filler for class_tostring test template.

Usage:
    python class_tostring.py <project_id>

Generates: template_projects/class_tostring_<project_id>/class_tostring.vla
"""

import os
import random
import sys


CLASS_NAMES = ["Point", "Node", "Item", "Record", "Cell", "Box", "Entry", "Shape",
               "Token", "Frame", "Slot", "Chunk"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "class_tostring")
    output_dir = os.path.join(project_root, "template_projects", f"class_tostring_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "class_tostring.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    plain, custom, sub, plain_sub = random.sample(CLASS_NAMES, 4)
    content = content.replace("${PLAIN_CLASS}", plain)
    content = content.replace("${CUSTOM_CLASS}", custom)
    content = content.replace("${SUB_CLASS}", sub)
    content = content.replace("${PLAIN_SUB_CLASS}", plain_sub)
    content = content.replace("${PROP_TYPE}", "int32")
    content = content.replace("${PROP_NAME}", "value")
    content = content.replace("${VALUE_1}", str(random.randint(1, 99)))

    output_path = os.path.join(output_dir, "class_tostring.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python class_tostring.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
