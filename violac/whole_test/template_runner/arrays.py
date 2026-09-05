"""Random filler for arrays test template.

Usage:
    python arrays.py <project_id>

Generates: template_projects/arrays_<project_id>/arrays.vla
"""

import os
import random
import sys


def _random_array_values(size: int, min_val: int, max_val: int) -> str:
    return ", ".join(str(random.randint(min_val, max_val)) for _ in range(size))


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "arrays")
    output_dir = os.path.join(project_root, "template_projects", f"arrays_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "arrays.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    arr1_size = random.randint(5, 12)
    arr1_vals = _random_array_values(arr1_size, 0, 100)
    arr2_size = random.randint(3, 6)
    arr2_vals = _random_array_values(arr2_size, 100, 200)

    content = content.replace("${ARR_NAME_1}", f"arr1_{pid}")
    content = content.replace("${ARR_VALUES_1}", arr1_vals)
    content = content.replace("${ELEM_VAR_1}", f"elem1_{pid}")
    content = content.replace("${INDEX_1}", str(random.randint(0, max(0, arr1_size - 1))))
    content = content.replace("${ELEM_VAR_2}", f"elem2_{pid}")
    content = content.replace("${INDEX_2}", str(random.randint(0, max(0, arr1_size - 1))))

    slice_start = random.randint(0, max(0, arr1_size - 3))
    slice_end = random.randint(slice_start + 1, arr1_size)
    slice_from = random.randint(0, max(0, arr1_size - 2))

    content = content.replace("${SLICE_NAME_1}", f"slice1_{pid}")
    content = content.replace("${SLICE_START}", str(slice_start))
    content = content.replace("${SLICE_END}", str(slice_end))
    content = content.replace("${SLICE_NAME_2}", f"slice2_{pid}")
    content = content.replace("${SLICE_FROM}", str(slice_from))
    content = content.replace("${SLICE_NAME_3}", f"slice3_{pid}")
    content = content.replace("${SLICE_TO}", str(random.randint(1, arr1_size)))

    content = content.replace("${ARR_NAME_2}", f"arr2_{pid}")
    content = content.replace("${ARR_VALUES_2}", arr2_vals)
    content = content.replace("${CONCAT_NAME}", f"concat_{pid}")
    content = content.replace("${APPEND_NAME}", f"append_{pid}")
    content = content.replace("${APPEND_VAL}", str(random.randint(200, 300)))
    content = content.replace("${INSERT_NAME}", f"insert_{pid}")
    content = content.replace("${INSERT_IDX}", str(random.randint(0, max(0, arr1_size - 1))))
    content = content.replace("${INSERT_VAL}", str(random.randint(-100, 0)))
    content = content.replace("${LEN_VAR_1}", f"len1_{pid}")

    content = content.replace("${UPDATE_NAME_1}", f"upd1_{pid}")
    content = content.replace("${UPDATE_IDX_1}", str(random.randint(0, max(0, arr1_size - 1))))
    content = content.replace("${UPDATE_VAL_1}", str(random.randint(500, 600)))
    content = content.replace("${UPDATE_NAME_2}", f"upd2_{pid}")
    content = content.replace("${UPDATE_START}", str(slice_start))
    content = content.replace("${UPDATE_END}", str(slice_end))
    update_vals = _random_array_values(slice_end - slice_start, 700, 800)
    content = content.replace("${UPDATE_VALS}", update_vals)

    content = content.replace("${PRINT_MESSAGE}", f"Arrays test #{pid} completed")

    output_path = os.path.join(output_dir, "arrays.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python arrays.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
