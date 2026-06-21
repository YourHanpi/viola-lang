"""Random filler for exceptions test template.

Usage:
    python exceptions.py <project_id>

Generates: template_projects/exceptions_<project_id>/exceptions.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "exceptions")
    output_dir = os.path.join(project_root, "template_projects", f"exceptions_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "exceptions.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${EXCEPTION_CLASS}", f"MathException_{pid}")
    content = content.replace("${EXC_PROP}", "message")

    content = content.replace("${DIVIDE_FUNC}", f"safeDivide_{pid}")
    content = content.replace("${DIV_BY_ZERO_MSG}", "Division by zero is not allowed")
    content = content.replace("${SAFE_FUNC}", f"square_{pid}")

    content = content.replace("${RESULT_VAR}", f"result_{pid}")

    # Safe division - b != 0
    content = content.replace("${NUM_A}", str(random.randint(10, 100)))
    content = content.replace("${NUM_B}", str(random.randint(2, 10)))
    # Division by zero
    content = content.replace("${NUM_C}", str(random.randint(1, 50)))

    content = content.replace("${CATCH_MSG_1}", "Caught exception in first try:")
    content = content.replace("${CATCH_MSG_2}", "Caught division by zero:")
    content = content.replace("${CATCH_MSG_3}", "This should not be caught")
    content = content.replace("${FINALLY_MSG}", "Finally block executed")

    content = content.replace("${NESTED_A}", str(random.randint(1, 10)))
    content = content.replace("${NESTED_B}", "0")
    content = content.replace("${INNER_CATCH_MSG}", "Inner catch - rethrowing")
    content = content.replace("${OUTER_CATCH_MSG}", "Outer catch - received rethrow")

    content = content.replace("${SAFE_VAL}", str(random.randint(1, 20)))
    content = content.replace("${PRINT_MESSAGE}", f"Exceptions test #{pid} completed")

    output_path = os.path.join(output_dir, "exceptions.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exceptions.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
