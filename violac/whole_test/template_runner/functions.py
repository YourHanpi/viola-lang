"""Random filler for functions test template.

Usage:
    python functions.py <project_id>

Generates: template_projects/functions_<project_id>/functions.vla
"""

import os
import random
import sys


NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
GREET_PREFIXES = ["Hello, ", "Hi, ", "Greetings, ", "Welcome, "]
GREET_SUFFIXES = ["!", "!!", " :)", "."]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "functions")
    output_dir = os.path.join(project_root, "template_projects", f"functions_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "functions.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${GREET_PREFIX}", random.choice(GREET_PREFIXES))
    content = content.replace("${GREET_SUFFIX}", random.choice(GREET_SUFFIXES))
    content = content.replace("${DEFAULT_EXP}", str(round(random.uniform(0.5, 3.0), 4)))
    content = content.replace("${NAME}", random.choice(NAMES))
    content = content.replace("${VAL_A}", str(random.randint(1, 100)))
    content = content.replace("${VAL_B}", str(random.randint(1, 100)))
    content = content.replace("${VAL_C}", str(random.randint(10, 100)))
    content = content.replace("${VAL_D}", str(random.randint(2, 10)))
    content = content.replace("${BASE_VAL}", str(round(random.uniform(1.0, 10.0), 4)))
    content = content.replace("${APPLY_VAL}", str(random.randint(1, 50)))
    content = content.replace("${PRINT_MESSAGE}", f"Functions test #{pid} completed")

    output_path = os.path.join(output_dir, "functions.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python functions.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
