"""Random filler for polymorphism test template.

Usage:
    python polymorphism.py <project_id>

Generates: template_projects/polymorphism_<project_id>/polymorphism.vla
"""

import os
import random
import sys


BASE_NAMES = ["Shape", "Node", "Animal", "Vehicle", "Account", "Device", "Widget", "Logger"]
SUB_NAMES = ["Circle", "Square", "Leaf", "Branch", "Dog", "Cat", "Car", "Bike",
             "Savings", "Checking", "Sensor", "Motor", "Button", "Slider"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "polymorphism")
    output_dir = os.path.join(project_root, "template_projects", f"polymorphism_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "polymorphism.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))

    base = random.choice(BASE_NAMES)
    sub_1, sub_2 = random.sample(SUB_NAMES, 2)

    content = content.replace("${BASE_CLASS}", base)
    content = content.replace("${SUB_CLASS_1}", sub_1)
    content = content.replace("${SUB_CLASS_2}", sub_2)

    output_path = os.path.join(output_dir, "polymorphism.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python polymorphism.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
