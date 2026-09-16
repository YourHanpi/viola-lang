"""Random filler for module_alias test template.

Usage:
    python module_alias.py <project_id>

Generates: template_projects/module_alias_<project_id>/ with module_alias.vla and <module>.vla
"""

import os
import random
import sys


MODULE_NAMES = ["math_utils", "string_ops", "data_tools", "core_lib", "algorithms",
                "collections", "parsers", "validators"]
FUNC_NAMES = ["computeSum", "addValues", "totalOf", "sumUp", "accumulate"]
CLASS_NAMES = ["Counter", "Accumulator", "Tally", "Ledger", "Register"]
MAKE_NAMES = ["makeDefault", "defaultValue", "initialValue", "seedValue"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "module_alias")
    output_dir = os.path.join(project_root, "template_projects", f"module_alias_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    random.seed(int(project_id))
    pid = project_id

    module_name = random.choice(MODULE_NAMES)
    func_name = random.choice(FUNC_NAMES)
    cls_name = random.choice(CLASS_NAMES)
    make_name = random.choice(MAKE_NAMES)
    value_1 = random.randint(1, 50)
    value_2 = random.randint(51, 100)
    make_value = random.randint(1, 999)

    replacements = {
        "${MODULE_1}": module_name,
        "${FUNC_1}": func_name,
        "${CLASS_1}": cls_name,
        "${MAKE_FUNC}": make_name,
        "${SCALE_FUNC}": f"double_{make_name}",
        "${GENERIC_FUNC}": f"countExtra_{make_name}",
        "${MODULE_ALIAS}": f"lib_alias_{pid}",
        "${FUNC_ALIAS}": f"aliased_{func_name}_{pid}",
        "${CLASS_ALIAS}": f"Aliased{cls_name}{pid}",
        "${ALIAS_TYPE}": f"LibInt_{pid}",
        "${VALUE_1}": str(value_1),
        "${VALUE_2}": str(value_2),
        "${SUM}": str(value_1 + value_2),
        "${MAKE_VALUE}": str(make_value),
        "${SCALED_VALUE}": str(value_2 * 2),
    }

    for template_file, output_name in [("main.vla", "main.vla"),
                                       ("module.vla", f"{module_name}.vla")]:
        with open(os.path.join(template_dir, template_file), "r", encoding="utf-8") as f:
            content = f.read()
        for key, value in replacements.items():
            content = content.replace(key, value)
        output_path = os.path.join(output_dir, output_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python module_alias.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
