"""Random filler for C compatibility test template.

Usage:
    python c_compat.py <project_id>

Generates: template_projects/c_compat_<project_id>/c_compat.vla
"""

import os
import random
import sys


C_HEADERS = [
    ("stdio.h", "math.h"),
    ("stdlib.h", "string.h"),
    ("stdint.h", "stdbool.h"),
    ("time.h", "assert.h"),
]

C_OPS = ["+", "-", "*", "/", "&", "|", "^"]
C_STRUCTS = [
    ("Point", "x", "y"),
    ("Rect", "width", "height"),
    ("Vector", "dx", "dy"),
    ("Complex", "real", "imag"),
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "c_compat")
    output_dir = os.path.join(project_root, "template_projects", f"c_compat_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "c_compat.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    headers = random.choice(C_HEADERS)
    content = content.replace("${C_HEADER_1}", headers[0])
    content = content.replace("${C_HEADER_2}", headers[1])

    content = content.replace("${CPART_FUNC_NAME}", f"cpart_op_{pid}")
    content = content.replace("${CPART_OP}", random.choice(C_OPS))

    struct = random.choice(C_STRUCTS)
    content = content.replace("${WRAPPER_CLASS}", f"{struct[0]}Wrapper_{pid}")
    content = content.replace("${C_STRUCT_TYPE}", struct[0])
    content = content.replace("${C_STRUCT_VAR}", f"_s")
    content = content.replace("${C_FIELD_1}", struct[1])
    content = content.replace("${C_FIELD_2}", struct[2])
    content = content.replace("${C_FIELD_CAP_1}", struct[1].capitalize())
    content = content.replace("${C_FIELD_CAP_2}", struct[2].capitalize())
    content = content.replace("${INIT_PARAM_1}", struct[1])
    content = content.replace("${INIT_PARAM_2}", struct[2])

    content = content.replace("${CPART_MATH_FUNC}", f"cpart_math_{pid}")
    content = content.replace("${CPART_MATH_EXPR}", f"sqrt(x) + {random.uniform(0.1, 3.0):.4f}")

    content = content.replace("${CPART_RESULT}", f"cresult_{pid}")
    content = content.replace("${CPART_ARG_A}", str(random.randint(1, 50)))
    content = content.replace("${CPART_ARG_B}", str(random.randint(1, 50)))

    content = content.replace("${WRAPPER_OBJ}", f"wrap_{pid}")
    content = content.replace("${WRAPPER_ARG_1}", str(random.randint(0, 100)))
    content = content.replace("${WRAPPER_ARG_2}", str(random.randint(0, 100)))
    content = content.replace("${FIELD_VAL_1}", f"field1_{pid}")
    content = content.replace("${FIELD_VAL_2}", f"field2_{pid}")

    content = content.replace("${MATH_RESULT}", f"math_res_{pid}")
    content = content.replace("${MATH_ARG}", str(round(random.uniform(1.0, 100.0), 4)))

    content = content.replace("${PRINT_MESSAGE}", f"C compatibility test #{pid} completed")

    output_path = os.path.join(output_dir, "c_compat.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python c_compat.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
