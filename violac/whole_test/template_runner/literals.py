"""Random filler for literals test template.

Usage:
    python literals.py <project_id>

Generates: template_projects/literals_<project_id>/literals.vla
"""

import os
import random
import sys


def _random_hex() -> str:
    val = random.randint(0, 0xFFFFFFFF)
    return f"0x{val:x}"


def _random_octal() -> str:
    val = random.randint(0, 0o77777777)
    return f"0o{val:o}"


def _random_binary() -> str:
    bits = random.randint(4, 16)
    val = random.randint(0, (1 << bits) - 1)
    return f"0b{val:b}"


def _random_sci_float() -> str:
    mantissa = random.uniform(1.0, 10.0)
    exponent = random.randint(-10, 10)
    return f"{mantissa:.6f}e{exponent:+d}"


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "literals")
    output_dir = os.path.join(project_root, "template_projects", f"literals_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "literals.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    # Decimal integers
    content = content.replace("${DEC_VAR_1}", f"dec_var1_{pid}")
    content = content.replace("${DEC_VALUE_1}", str(random.randint(-100000, 100000)))
    content = content.replace("${DEC_VAR_2}", f"dec_var2_{pid}")
    content = content.replace("${DEC_VALUE_2}", str(random.randint(-100000, 100000)))

    # Hexadecimal integers
    content = content.replace("${HEX_VAR_1}", f"hex_var1_{pid}")
    content = content.replace("${HEX_VALUE_1}", _random_hex())
    content = content.replace("${HEX_VAR_2}", f"hex_var2_{pid}")
    content = content.replace("${HEX_VALUE_2}", _random_hex())

    # Octal integers
    content = content.replace("${OCT_VAR_1}", f"oct_var1_{pid}")
    content = content.replace("${OCT_VALUE_1}", _random_octal())
    content = content.replace("${OCT_VAR_2}", f"oct_var2_{pid}")
    content = content.replace("${OCT_VALUE_2}", _random_octal())

    # Binary integers
    content = content.replace("${BIN_VAR_1}", f"bin_var1_{pid}")
    content = content.replace("${BIN_VALUE_1}", _random_binary())

    # Integer with suffixes
    content = content.replace("${SUFFIX_VAR_1}", f"suf_var1_{pid}")
    content = content.replace("${SUFFIX_VALUE_1}", f"{random.randint(0, 100000)}i")
    content = content.replace("${SUFFIX_VAR_2}", f"suf_var2_{pid}")
    content = content.replace("${SUFFIX_VALUE_2}", f"{random.randint(0, 100000)}u")

    # Float decimal
    content = content.replace("${FLOAT_DEC_VAR}", f"fdec_{pid}")
    content = content.replace("${FLOAT_DEC_VALUE}", f"{random.uniform(-100.0, 100.0):.4f}")

    # Float scientific
    content = content.replace("${FLOAT_SCI_VAR}", f"fsci_{pid}")
    content = content.replace("${FLOAT_SCI_VALUE}", _random_sci_float())

    # Float with suffixes
    content = content.replace("${FLOAT_SUF_VAR_1}", f"fsuf1_{pid}")
    content = content.replace("${FLOAT_SUF_VALUE_1}", f"{random.uniform(-100.0, 100.0):.4f}f")
    content = content.replace("${FLOAT_SUF_VAR_2}", f"fsuf2_{pid}")
    content = content.replace("${FLOAT_SUF_VALUE_2}", f"{random.uniform(-1000.0, 1000.0):.6f}l")

    # String literals
    content = content.replace("${STR_DQ_VAR}", f"sdq_{pid}")
    content = content.replace("${STR_DQ_VALUE}", f'"Test string with double quotes {pid}"')
    content = content.replace("${STR_SQ_VAR}", f"ssq_{pid}")
    content = content.replace("${STR_SQ_VALUE}", f"'Test string with single quotes {pid}'")
    content = content.replace("${STR_ESC_VAR}", f"sesc_{pid}")
    content = content.replace("${STR_ESC_VALUE}", f'"Line1\\nLine2\\tTabbed\\"quoted\\""')
    content = content.replace("${STR_RAW_VAR}", f"sraw_{pid}")
    content = content.replace("${STR_RAW_VALUE}", rf'r"C:\Users\test\path\file_{pid}"')

    # Bool variables
    content = content.replace("${BOOL_TRUE_VAR}", f"bt_{pid}")
    content = content.replace("${BOOL_FALSE_VAR}", f"bf_{pid}")

    content = content.replace("${PRINT_MESSAGE}", f"Literals test #{pid} completed")

    output_path = os.path.join(output_dir, "literals.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python literals.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
