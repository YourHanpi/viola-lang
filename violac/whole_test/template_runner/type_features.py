"""Random filler for type_features test template.

Usage:
    python type_features.py <project_id>

Generates: template_projects/type_features_<project_id>/type_features.vla
"""

import os
import random
import sys


CLASS_NAMES = ["Box", "Holder", "Wrapper", "Cell", "Vessel", "Crate", "Tin", "Case"]
PROP_NAMES = ["value", "count", "total", "amount", "size", "level"]


def _format_float(value: float) -> tuple[str, str]:
    """返回浮点字面量文本与其toString结果文本（%.15g，去除多余尾零）。"""
    literal = repr(value)
    if "." not in literal and "e" not in literal:
        literal += ".0"
    # 与runtime的fromFloat一致：最多15位有效数字且去掉多余的尾零
    text = "%.15g" % value
    if "e" not in text and "." in text:
        text = text.rstrip("0").rstrip(".")
    return literal, text


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "type_features")
    output_dir = os.path.join(project_root, "template_projects", f"type_features_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "type_features.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    cls_name = random.choice(CLASS_NAMES)
    prop_name = random.choice(PROP_NAMES)
    value_1 = random.randint(1, 100)
    value_2 = random.randint(101, 200)
    value_3 = random.randint(201, 300)
    float_value = round(random.uniform(0.5, 50.0), 3)
    float_literal, float_text = _format_float(float_value)

    content = content.replace("${CLASS_NAME}", cls_name)
    content = content.replace("${PROP_TYPE}", "int")
    content = content.replace("${PROP_NAME}", prop_name)
    content = content.replace("${VALUE_1}", str(value_1))
    content = content.replace("${VALUE_2}", str(value_2))
    content = content.replace("${VALUE_3}", str(value_3))
    content = content.replace("${FLOAT_VALUE}", float_literal)
    content = content.replace("${FLOAT_TEXT}", float_text)
    content = content.replace("${NEXT_VALUE}", str(value_1 + 1))
    for i in range(1, 5):
        content = content.replace(f"${{ALIAS_{i}}}", f"Alias{i}_{pid}")

    output_path = os.path.join(output_dir, "type_features.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python type_features.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
