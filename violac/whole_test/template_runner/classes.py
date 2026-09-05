"""Random filler for classes test template.

Usage:
    python classes.py <project_id>

Generates: template_projects/classes_<project_id>/classes.vla
"""

import os
import random
import sys


CLASS_NAMES = ["Calculator", "Counter", "Storage", "Processor", "Accumulator", "Registry"]
PROP_NAMES = ["value", "count", "total", "amount", "score", "level"]
DEFAULT_INTS = [0, 1, -1, 10, 100, 42]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "classes")
    output_dir = os.path.join(project_root, "template_projects", f"classes_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "classes.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    cls_name = random.choice(CLASS_NAMES)
    prop1 = random.choice(PROP_NAMES)
    prop2 = random.choice([p for p in PROP_NAMES if p != prop1] or PROP_NAMES)
    prop3 = random.choice([p for p in PROP_NAMES if p not in (prop1, prop2)] or PROP_NAMES)

    content = content.replace("${CLASS_NAME}", cls_name)

    # Properties: int, int, string
    content = content.replace("${PROP_TYPE_1}", "int")
    content = content.replace("${PROP_NAME_1}", prop1)
    content = content.replace("${PROP_TYPE_2}", "int")
    content = content.replace("${PROP_NAME_2}", prop2)
    content = content.replace("${PROP_TYPE_3}", "string")
    content = content.replace("${PROP_NAME_3}", prop3)
    content = content.replace("${PROP_NAME_CAP_1}", prop1.capitalize())

    content = content.replace("${DEFAULT_VAL_1}", str(random.choice(DEFAULT_INTS)))
    content = content.replace("${DEFAULT_VAL_2}", str(random.choice(DEFAULT_INTS)))
    content = content.replace("${DEFAULT_VAL_3}", f'"default_{pid}"')

    content = content.replace("${OBJ_VAR_1}", f"obj1_{pid}")
    content = content.replace("${OBJ_VAR_2}", f"obj2_{pid}")
    content = content.replace("${OBJ_VAR_3}", f"obj3_{pid}")
    content = content.replace("${OBJ_VAR_4}", f"obj4_{pid}")

    content = content.replace("${INIT_VAL_1}", str(random.randint(1, 100)))
    content = content.replace("${INIT_VAL_2}", str(random.randint(1, 100)))
    content = content.replace("${INIT_VAL_3}", f'"init_{pid}"')

    content = content.replace("${RESULT_VAR_1}", f"res1_{pid}")
    content = content.replace("${RESULT_VAR_2}", f"res2_{pid}")

    content = content.replace("${POINT_X}", str(random.randint(0, 100)))
    content = content.replace("${POINT_Y}", str(random.randint(0, 100)))
    content = content.replace("${PRINT_MESSAGE}", f"Classes test #{pid} completed")

    output_path = os.path.join(output_dir, "classes.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python classes.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
