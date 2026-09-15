"""Random filler for refcount test template.

Usage:
    python refcount.py <project_id>

Generates: template_projects/refcount_<project_id>/refcount.vla
"""

import os
import random
import sys


CLASS_NAMES = ["Crate", "Bundle", "Parcel", "Payload", "Packet", "Container"]
HOLDER_NAMES = ["Shelf", "Bin", "Rack", "Locker", "Tray", "Drawer"]
LETTERS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "refcount")
    output_dir = os.path.join(project_root, "template_projects", f"refcount_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "refcount.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    cls_name = random.choice(CLASS_NAMES)
    holder_name = random.choice(HOLDER_NAMES)
    # 取值互不相同，使断言能区分是哪一个字符串被读到
    letters = random.sample(LETTERS, 6)

    content = content.replace("${CLASS_NAME}", cls_name)
    content = content.replace("${HOLDER_NAME}", holder_name)
    content = content.replace("${STRING_A}", letters[0])
    content = content.replace("${STRING_B}", letters[1])
    content = content.replace("${STRING_C}", letters[2])
    content = content.replace("${STRING_D}", letters[3])
    content = content.replace("${STRING_E}", letters[4])
    content = content.replace("${STRING_F}", letters[5])

    content = content.replace("${OBJ_A}", f"objA_{pid}")
    content = content.replace("${OBJ_B}", f"objB_{pid}")
    content = content.replace("${OBJ_C}", f"objC_{pid}")
    content = content.replace("${HOLDER_A}", f"holderA_{pid}")
    content = content.replace("${NAME_A}", f"nameA_{pid}")

    content = content.replace("${WEIGHT_A}", str(random.randint(1, 50)))
    content = content.replace("${WEIGHT_B}", str(random.randint(51, 99)))
    # 轮数保持较小：每轮都要编译期生成的代码执行一遍，过大只是拉长运行时间
    content = content.replace("${CHURN_ROUNDS}", str(random.randint(20, 60)))
    content = content.replace("${ARRAY_ROUNDS}", str(random.randint(20, 60)))
    content = content.replace("${CHAIN_DEPTH}", str(random.randint(5, 20)))

    output_path = os.path.join(output_dir, "refcount.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python refcount.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
