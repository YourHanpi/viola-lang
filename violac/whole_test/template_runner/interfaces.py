"""Random filler for interfaces test template.

Usage:
    python interfaces.py <project_id>

Generates: template_projects/interfaces_<project_id>/interfaces.vla
"""

import os
import random
import sys


IFACE_NAMES = ["Shape2D", "Drawable", "Named", "Countable", "Comparable", "Printable"]
METHOD_NAMES = ["describe", "label", "size", "count", "extra", "tag", "kind", "value"]
CLASS_NAMES = ["Circle", "Square", "Node", "Leaf", "Sensor", "Widget", "Button", "Slider",
               "Cache", "Queue"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "interfaces")
    output_dir = os.path.join(project_root, "template_projects", f"interfaces_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "interfaces.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    iface_1, iface_2 = random.sample(IFACE_NAMES, 2)
    methods = random.sample(METHOD_NAMES, 3)
    cls_1, cls_2, cls_3, cls_4 = random.sample(CLASS_NAMES, 4)

    content = content.replace("${IFACE_1}", iface_1)
    content = content.replace("${IFACE_2}", iface_2)
    content = content.replace("${IFACE_METHOD_1}", methods[0])
    content = content.replace("${IFACE_METHOD_2}", methods[1])
    content = content.replace("${IFACE_METHOD_3}", methods[2])
    content = content.replace("${CLS_1}", cls_1)
    content = content.replace("${CLS_2}", cls_2)
    content = content.replace("${CLS_3}", cls_3)
    content = content.replace("${CLS_4}", cls_4)

    output_path = os.path.join(output_dir, "interfaces.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python interfaces.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
