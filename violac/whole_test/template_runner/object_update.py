"""Random filler for object_update test template.

Usage:
    python object_update.py <project_id>

Generates: template_projects/object_update_<project_id>/object_update.vla
"""

import os
import random
import sys


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "object_update")
    output_dir = os.path.join(project_root, "template_projects", f"object_update_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "object_update.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${CLASS_NAME}", f"Config_{pid}")

    content = content.replace("${PROP_TYPE_1}", "int")
    content = content.replace("${PROP_NAME_1}", "width")
    content = content.replace("${PROP_TYPE_2}", "int")
    content = content.replace("${PROP_NAME_2}", "height")
    content = content.replace("${PROP_TYPE_3}", "string")
    content = content.replace("${PROP_NAME_3}", "label")

    orig_w = random.randint(10, 100)
    orig_h = random.randint(10, 100)
    new_w = random.randint(100, 200)
    new_h = random.randint(100, 200)

    content = content.replace("${ORIG_OBJ}", f"orig_{pid}")
    content = content.replace("${VAL_1}", str(orig_w))
    content = content.replace("${VAL_2}", str(orig_h))
    content = content.replace("${VAL_3}", f'"original_{pid}"')

    content = content.replace("${UPDATED_OBJ_1}", f"upd1_{pid}")
    content = content.replace("${NEW_VAL_1}", str(new_w))
    content = content.replace("${UPDATED_OBJ_2}", f"upd2_{pid}")
    content = content.replace("${NEW_VAL_2}", str(new_h))
    content = content.replace("${UPDATED_OBJ_3}", f"upd3_{pid}")
    content = content.replace("${NEW_VAL_3}", f'"updated_{pid}"')

    # Array updates
    arr_size = random.randint(5, 10)
    arr_vals = ", ".join(str(random.randint(0, 50)) for _ in range(arr_size))
    idx1 = random.randint(0, arr_size - 1)
    idx2 = random.randint(0, arr_size - 1)
    if idx2 == idx1:
        idx2 = (idx2 + 1) % arr_size
    s_start = random.randint(0, arr_size - 3)
    s_end = s_start + random.randint(1, min(3, arr_size - s_start))
    slice_vals = ", ".join(str(random.randint(100, 200)) for _ in range(s_end - s_start))

    content = content.replace("${ORIG_ARR}", f"orig_arr_{pid}")
    content = content.replace("${ARR_VALS}", arr_vals)
    content = content.replace("${UPDATED_ARR_1}", f"upd_arr1_{pid}")
    content = content.replace("${ARR_IDX_1}", str(idx1))
    content = content.replace("${ARR_NEW_VAL_1}", str(random.randint(80, 99)))
    content = content.replace("${UPDATED_ARR_2}", f"upd_arr2_{pid}")
    content = content.replace("${ARR_IDX_2}", str(idx2))
    content = content.replace("${ARR_NEW_VAL_2}", str(random.randint(80, 99)))
    content = content.replace("${UPDATED_ARR_3}", f"upd_arr3_{pid}")
    content = content.replace("${SLICE_START}", str(s_start))
    content = content.replace("${SLICE_END}", str(s_end))
    content = content.replace("${SLICE_VALS}", slice_vals)

    content = content.replace("${PRINT_MESSAGE}", f"Object update test #{pid} completed")

    output_path = os.path.join(output_dir, "object_update.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python object_update.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
