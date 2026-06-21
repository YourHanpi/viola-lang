"""Random filler for strings test template.

Usage:
    python strings.py <project_id>

Generates: template_projects/strings_<project_id>/strings.vla
"""

import os
import random
import sys


STR_POOL = [
    "Hello",
    "World",
    "Viola",
    "Programming",
    "Language",
    "Compiler",
    "Testing",
    "Template",
    "abcdef",
    "GHIJKL",
    "12345",
    "!@#$%",
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "strings")
    output_dir = os.path.join(project_root, "template_projects", f"strings_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "strings.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    s1 = random.choice(STR_POOL)
    s2 = random.choice([s for s in STR_POOL if s != s1] or STR_POOL)

    content = content.replace("${STR_VAR_1}", f"str1_{pid}")
    content = content.replace("${STR_VALUE_1}", s1)
    content = content.replace("${STR_VAR_2}", f"str2_{pid}")
    content = content.replace("${STR_VALUE_2}", s2)

    repeat_count = random.randint(2, 5)
    content = content.replace("${CONCAT_PLUS}", f"concat_plus_{pid}")
    content = content.replace("${REPEAT_STAR}", f"repeat_star_{pid}")
    content = content.replace("${REPEAT_COUNT}", str(repeat_count))
    content = content.replace("${CONCAT_METHOD}", f"concat_method_{pid}")
    content = content.replace("${REPEAT_METHOD}", f"repeat_method_{pid}")

    s1_len = len(s1)
    slice_start = random.randint(0, max(0, s1_len - 2))
    slice_end = min(slice_start + random.randint(1, 3), s1_len)
    slice_from = random.randint(0, max(0, s1_len - 1))
    slice_to = random.randint(1, s1_len)

    content = content.replace("${SLICE_1}", f"ss1_{pid}")
    content = content.replace("${STR_SLICE_START}", str(slice_start))
    content = content.replace("${STR_SLICE_END}", str(slice_end))
    content = content.replace("${SLICE_2}", f"ss2_{pid}")
    content = content.replace("${STR_SLICE_FROM}", str(slice_from))
    content = content.replace("${SLICE_3}", f"ss3_{pid}")
    content = content.replace("${STR_SLICE_TO}", str(slice_to))

    content = content.replace("${SPLIT_VAR}", f"split_{pid}")
    content = content.replace("${SPLIT_DELIM}", "l" if "l" in s1 else s1[0] if s1 else " ")
    content = content.replace("${REPLACE_VAR}", f"replace_{pid}")
    content = content.replace("${REPLACE_OLD}", s1[:min(3, s1_len)] if s1_len >= 1 else "a")
    content = content.replace("${REPLACE_NEW}", "XYZ")
    content = content.replace("${LEN_VAR}", f"len_{pid}")
    content = content.replace("${STARTS_VAR}", f"starts_{pid}")
    content = content.replace("${STARTS_WITH}", s1[:min(2, s1_len)] if s1_len >= 1 else "H")
    content = content.replace("${ENDS_VAR}", f"ends_{pid}")
    content = content.replace("${ENDS_WITH}", s1[-min(2, s1_len):] if s1_len >= 1 else "o")

    content = content.replace("${PRINT_MESSAGE}", f"Strings test #{pid} completed")

    output_path = os.path.join(output_dir, "strings.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python strings.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
