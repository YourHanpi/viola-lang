"""Random filler for branches test template.

Usage:
    python branches.py <project_id>

Generates: template_projects/branches_<project_id>/branches.vla
"""

import os
import random
import sys


RESULT_MESSAGES = [
    "Condition A met",
    "Condition B met",
    "Default path taken",
    "Branch 1 executed",
    "Branch 2 executed",
    "Branch 3 executed",
    "Fallback branch",
    "Both conditions satisfied",
    "Only first condition satisfied",
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "branches")
    output_dir = os.path.join(project_root, "template_projects", f"branches_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "branches.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${TEST_VAR_1}", f"test_var1_{pid}")
    content = content.replace("${TEST_VALUE_1}", str(random.randint(0, 100)))
    content = content.replace("${TEST_VAR_2}", f"test_var2_{pid}")
    content = content.replace("${TEST_VALUE_2}", str(random.randint(0, 100)))
    content = content.replace("${THRESHOLD_1}", str(random.randint(20, 80)))
    content = content.replace("${THRESHOLD_2}", str(random.randint(20, 80)))

    content = content.replace("${COMPARE_VAR}", f"cmp_var_{pid}")
    branch_vals = random.sample(range(1, 100), 3)
    content = content.replace("${COMPARE_VALUE}", str(random.choice(branch_vals)))
    content = content.replace("${BRANCH_VAL_1}", str(branch_vals[0]))
    content = content.replace("${BRANCH_VAL_2}", str(branch_vals[1]))
    content = content.replace("${BRANCH_VAL_3}", str(branch_vals[2]))

    content = content.replace("${NESTED_THRESHOLD}", str(random.randint(10, 90)))

    msgs = random.sample(RESULT_MESSAGES, 9)
    for i, msg in enumerate(msgs):
        content = content.replace(f"${{RESULT_MSG_{i+1}}}", msg)

    output_path = os.path.join(output_dir, "branches.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python branches.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
