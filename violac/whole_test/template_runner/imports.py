"""Random filler for imports test template.

Usage:
    python imports.py <project_id>

Generates: template_projects/imports_<project_id>/ with main.vla, module_a.vla, module_b.vla
"""

import os
import random
import sys


MODULE_NAMES = ["math_utils", "string_ops", "data_tools", "io_helpers", "core_lib",
                "algorithms", "collections", "parsers", "validators", "formatters"]
FUNC_PREFIXES = ["print", "calculate", "process", "format", "validate", "transform", "compute", "analyze"]
WILDCARD_FUNCS = ["getVersion", "getConfig", "initialize", "setup", "configure", "bootstrap"]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "imports")
    output_dir = os.path.join(project_root, "template_projects", f"imports_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    random.seed(int(project_id))
    pid = project_id

    # Pick module names
    mod1, mod2, mod3, mod4 = random.sample(MODULE_NAMES, 4)

    # ====== Generate main.vla ======
    main_path = os.path.join(template_dir, "main.vla")
    with open(main_path, "r", encoding="utf-8") as f:
        main_content = f.read()

    main_content = main_content.replace("${MODULE_1}", mod1)
    main_content = main_content.replace("${MODULE_2}", mod2)
    main_content = main_content.replace("${MODULE_3}", mod3)
    main_content = main_content.replace("${MODULE_4}", mod4)

    main_content = main_content.replace("${MODULE_1_ALIAS}", mod1)
    main_content = main_content.replace("${MODULE_1_FUNC}", f"print_msg_{pid}")
    main_content = main_content.replace("${MODULE_1_ARG}", f'"Hello from {pid}"')

    main_content = main_content.replace("${MODULE_2_ALIAS}", mod2)
    main_content = main_content.replace("${MODULE_2_FUNC}", f"calc_{pid}")
    main_content = main_content.replace("${MODULE_2_ARG_1}", str(random.randint(1, 10)))
    main_content = main_content.replace("${MODULE_2_ARG_2}", str(random.randint(1, 10)))

    imported_func1 = random.choice(FUNC_PREFIXES) + f"_{pid}"
    imported_func2 = random.choice(FUNC_PREFIXES) + f"2_{pid}"
    main_content = main_content.replace("${IMPORTED_SYMBOL_1}", imported_func1)
    main_content = main_content.replace("${IMPORTED_SYMBOL_2}", imported_func2)
    main_content = main_content.replace("${IMPORTED_FUNC_1}", imported_func1)
    main_content = main_content.replace("${IMPORTED_ARG_1}", str(random.randint(1, 100)))
    main_content = main_content.replace("${IMPORTED_FUNC_2}", imported_func2)
    main_content = main_content.replace("${IMPORTED_ARG_2}", str(random.randint(1, 100)))

    wildcard_func = random.choice(WILDCARD_FUNCS) + f"_{pid}"
    main_content = main_content.replace("${WILDCARD_FUNC}", wildcard_func)
    main_content = main_content.replace("${WILDCARD_ARG}", str(random.randint(1, 50)))

    main_content = main_content.replace("${RESULT_VAR_1}", f"res1_{pid}")
    main_content = main_content.replace("${RESULT_VAR_2}", f"res2_{pid}")
    main_content = main_content.replace("${RESULT_VAR_3}", f"res3_{pid}")
    main_content = main_content.replace("${PRINT_MESSAGE}", f"Imports test #{pid} completed")

    with open(os.path.join(output_dir, "main.vla"), "w", encoding="utf-8") as f:
        f.write(main_content)

    # ====== Generate module_a.vla ======
    mod_a_path = os.path.join(template_dir, "module_a.vla")
    with open(mod_a_path, "r", encoding="utf-8") as f:
        mod_a_content = f.read()

    mod_a_content = mod_a_content.replace("${MODULE_DESC_A}", f"Module A for test #{pid}")
    mod_a_content = mod_a_content.replace("${MODULE_FUNC_A}", f"print_msg_{pid}")
    mod_a_content = mod_a_content.replace("${MODULE_PREFIX_A}", f"[MOD_A:{pid}]")
    mod_a_content = mod_a_content.replace("${MODULE_SUFFIX_A}", "")
    mod_a_content = mod_a_content.replace("${MODULE_FUNC_B}", f"calc_{pid}")
    mod_a_content = mod_a_content.replace("${MODULE_CONST_A}", str(random.randint(1, 100)))

    with open(os.path.join(output_dir, f"{mod1}.vla"), "w", encoding="utf-8") as f:
        f.write(mod_a_content)

    # ====== Generate module_b.vla ======
    mod_b_path = os.path.join(template_dir, "module_b.vla")
    with open(mod_b_path, "r", encoding="utf-8") as f:
        mod_b_content = f.read()

    mod_b_content = mod_b_content.replace("${MODULE_DESC_B}", f"Module B for test #{pid}")
    mod_b_content = mod_b_content.replace("${WILDCARD_FUNC_A}", imported_func1)
    mod_b_content = mod_b_content.replace("${WILDCARD_PREFIX}", f"[WILD_{pid}]")
    mod_b_content = mod_b_content.replace("${WILDCARD_FUNC_B}", wildcard_func)
    mod_b_content = mod_b_content.replace("${WILDCARD_OFFSET}", str(random.randint(0, 50)))
    mod_b_content = mod_b_content.replace("${MODULE_EXPORT_VAR}", f"EXPORT_VAL_{pid}")
    mod_b_content = mod_b_content.replace("${MODULE_EXPORT_VAL}", str(random.randint(100, 999)))

    with open(os.path.join(output_dir, f"{mod4}.vla"), "w", encoding="utf-8") as f:
        f.write(mod_b_content)

    # ====== Also create modules for mod2 and mod3 ======
    # mod3（from...import 模块）需导出imported_func1与imported_func2。
    # 注意：main中以int实参调用（imported_func1接收int，imported_func2为
    # int -> int），需直接生成与main调用一致的签名。
    mod3_content = (
        "from viola.io import *;\n"
        "// Module C - Module C for test #{}\n"
        "\n"
        "sq {}(int x) -> () {{\n"
        "    print(\"[MOD_C:{}]\");\n"
        "}}\n"
        "\n"
        "fn {}(int x) -> (int result) {{\n"
        "    result = x * x + {};\n"
        "}}\n"
    ).format(pid, imported_func1, pid, imported_func2, random.randint(1, 50))
    with open(os.path.join(output_dir, f"{mod3}.vla"), "w", encoding="utf-8") as f:
        f.write(mod3_content)

    # mod2 is a copy of module_a
    with open(os.path.join(output_dir, f"{mod2}.vla"), "w", encoding="utf-8") as f:
        f.write(mod_a_content)

    print(f"Generated: {output_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python imports.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
