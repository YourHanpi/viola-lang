"""Random filler for concurrency test template.

Usage:
    python concurrency.py <project_id>

Generates: template_projects/concurrency_<project_id>/concurrency.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "concurrency")
    output_dir = os.path.join(project_root, "template_projects", f"concurrency_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "concurrency.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${SLOW_FUNC}", f"heavyCompute_{pid}")
    content = content.replace("${MULTIPLIER}", str(random.randint(2, 10)))
    content = content.replace("${FAST_FUNC}", f"quickAdd_{pid}")

    content = content.replace("${SYNC_A}", str(random.randint(1, 50)))
    content = content.replace("${SYNC_B}", str(random.randint(1, 50)))
    content = content.replace("${SYNC_C}", str(random.randint(1, 50)))
    content = content.replace("${SYNC_D}", str(random.randint(1, 50)))

    content = content.replace("${ASYNC_VAL_1}", str(random.randint(1, 20)))
    content = content.replace("${ASYNC_VAL_2}", str(random.randint(1, 20)))
    content = content.replace("${ASYNC_VAL_3}", str(random.randint(1, 20)))

    content = content.replace("${PRINT_MESSAGE}", f"Concurrency test #{pid} completed")

    output_path = os.path.join(output_dir, "concurrency.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python concurrency.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
