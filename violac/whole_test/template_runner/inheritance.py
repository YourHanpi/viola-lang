"""Random filler for inheritance test template.

Usage:
    python inheritance.py <project_id>

Generates: template_projects/inheritance_<project_id>/inheritance.vla
"""

import os
import random
import sys


ABSTRACT_NAMES = ["Shape", "Animal", "Vehicle", "Figure", "Entity"]
SUBCLASS_PREFIXES = ["Circle", "Rectangle", "Square", "Triangle", "Ellipse",
                     "Cat", "Dog", "Bird", "Fish", "Snake",
                     "Car", "Truck", "Bike", "Boat", "Plane"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "inheritance")
    output_dir = os.path.join(project_root, "template_projects", f"inheritance_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "inheritance.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    abstract = random.choice(ABSTRACT_NAMES)
    sub1 = random.choice(SUBCLASS_PREFIXES[:5]) + abstract
    sub2 = random.choice(SUBCLASS_PREFIXES[5:10]) + abstract
    intermediate = "Abstract" + abstract
    sub3 = random.choice(SUBCLASS_PREFIXES[10:]) + abstract

    content = content.replace("${ABSTRACT_CLASS}", abstract)
    content = content.replace("${PROP_A_TYPE}", "double")
    content = content.replace("${PROP_A_NAME}", "size")
    content = content.replace("${PROP_A_NAME_CAP}", "Size")

    content = content.replace("${SUBCLASS_1}", sub1)
    content = content.replace("${PROP_B_TYPE}", "double")
    content = content.replace("${PROP_B_NAME}", "ratio")
    content = content.replace("${SUBCLASS_1_DESC}", f"{sub1} instance")

    content = content.replace("${SUBCLASS_2}", sub2)
    content = content.replace("${PROP_C_TYPE}", "double")
    content = content.replace("${PROP_C_NAME}", "factor")
    content = content.replace("${AREA_FACTOR}", str(round(random.uniform(0.1, 2.0), 2)))
    content = content.replace("${SUBCLASS_2_DESC}", f"{sub2} instance")

    content = content.replace("${INTERMEDIATE_CLASS}", intermediate)
    content = content.replace("${PROP_D_TYPE}", "double")
    content = content.replace("${PROP_D_NAME}", "offset")
    content = content.replace("${SUBCLASS_3}", sub3)
    content = content.replace("${SUBCLASS_3_DESC}", f"{sub3} instance")

    content = content.replace("${INIT_VAL_A}", str(round(random.uniform(1.0, 10.0), 2)))
    content = content.replace("${INIT_VAL_B}", str(round(random.uniform(0.5, 5.0), 2)))
    content = content.replace("${INIT_VAL_C}", str(round(random.uniform(0.1, 3.0), 2)))
    content = content.replace("${INIT_VAL_D}", str(round(random.uniform(1.0, 20.0), 2)))

    content = content.replace("${PRINT_MESSAGE}", f"Inheritance test #{pid} completed")

    output_path = os.path.join(output_dir, "inheritance.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inheritance.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
