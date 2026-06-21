"""Random filler for hello_world test template.

Usage:
    python hello_world.py <project_id>

Generates: template_projects/hello_world_<project_id>/hello_world.vla
"""

import os
import random
import sys


GREETINGS = ["Hello", "Hi", "Greetings", "Salutations", "Howdy", "Hey", "Welcome", "Bonjour"]
TARGETS = ["World", "Viola", "Universe", "Everyone", "Friend", "Developer", "Earth", "Galaxy"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "hello_world")
    output_dir = os.path.join(project_root, "template_projects", f"hello_world_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "hello_world.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    greeting = random.choice(GREETINGS)
    target = random.choice(TARGETS)

    content = content.replace("${GREETING}", greeting)
    content = content.replace("${TARGET}", target)

    output_path = os.path.join(output_dir, "hello_world.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hello_world.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
