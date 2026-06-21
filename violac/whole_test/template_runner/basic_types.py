"""Random filler for basic_types test template.

Usage:
    python basic_types.py <project_id>

Generates: template_projects/basic_types_<project_id>/basic_types.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "basic_types")
    output_dir = os.path.join(project_root, "template_projects", f"basic_types_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "basic_types.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Random seed based on project_id for reproducibility
    random.seed(int(project_id))

    # Bool
    content = content.replace("${BOOL_VAR}", f"flag_{project_id}")
    content = content.replace("${BOOL_VALUE}", random.choice(["true", "false"]))

    # Int types
    content = content.replace("${INT_VAR}", f"i_{project_id}")
    content = content.replace("${INT_VALUE}", str(random.randint(-100000, 100000)))
    content = content.replace("${INT8_VAR}", f"i8_{project_id}")
    content = content.replace("${INT8_VALUE}", str(random.randint(-128, 127)))
    content = content.replace("${INT16_VAR}", f"i16_{project_id}")
    content = content.replace("${INT16_VALUE}", str(random.randint(-32768, 32767)))
    content = content.replace("${INT32_VAR}", f"i32_{project_id}")
    content = content.replace("${INT32_VALUE}", str(random.randint(-2147483648, 2147483647)))
    content = content.replace("${INT64_VAR}", f"i64_{project_id}")
    content = content.replace("${INT64_VALUE}", str(random.randint(-9223372036854775808, 9223372036854775807)))

    # Unsigned int types
    content = content.replace("${UINT_VAR}", f"ui_{project_id}")
    content = content.replace("${UINT_VALUE}", str(random.randint(0, 200000)))
    content = content.replace("${UINT8_VAR}", f"ui8_{project_id}")
    content = content.replace("${UINT8_VALUE}", str(random.randint(0, 255)))
    content = content.replace("${UINT16_VAR}", f"ui16_{project_id}")
    content = content.replace("${UINT16_VALUE}", str(random.randint(0, 65535)))
    content = content.replace("${UINT32_VAR}", f"ui32_{project_id}")
    content = content.replace("${UINT32_VALUE}", str(random.randint(0, 4294967295)))
    content = content.replace("${UINT64_VAR}", f"ui64_{project_id}")
    content = content.replace("${UINT64_VALUE}", str(random.randint(0, 18446744073709551615)))

    # Size_t
    content = content.replace("${SIZE_VAR}", f"sz_{project_id}")
    content = content.replace("${SIZE_VALUE}", str(random.randint(0, 1000000)))

    # Float types
    content = content.replace("${FLOAT_VAR}", f"f_{project_id}")
    content = content.replace("${FLOAT_VALUE}", f"{random.uniform(-1000.0, 1000.0):.6f}f")
    content = content.replace("${FLOAT32_VAR}", f"f32_{project_id}")
    content = content.replace("${FLOAT32_VALUE}", f"{random.uniform(-1000.0, 1000.0):.6f}f")
    content = content.replace("${FLOAT64_VAR}", f"f64_{project_id}")
    content = content.replace("${FLOAT64_VALUE}", str(round(random.uniform(-10000.0, 10000.0), 10)))
    content = content.replace("${DOUBLE_VAR}", f"d_{project_id}")
    content = content.replace("${DOUBLE_VALUE}", str(round(random.uniform(-100000.0, 100000.0), 12)))

    content = content.replace("${PRINT_MESSAGE}", f"Basic types test #{project_id} completed")

    output_path = os.path.join(output_dir, "basic_types.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python basic_types.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
