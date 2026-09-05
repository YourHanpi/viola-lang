"""Random filler for I/O test template.

Usage:
    python io.py <project_id>

Generates: template_projects/io_<project_id>/io.vla
"""

import os
import random
import sys


FILE_CONTENTS = [
    ["First line of test data", "Second line with more info", "Third line for completeness"],
    ["Hello from Viola I/O test", "This file was written by the test", "End of file marker"],
    ["Line 1: Alpha", "Line 2: Beta", "Line 3: Gamma"],
    ["Configuration data", "Key=Value pairs", "End of configuration"],
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "io")
    output_dir = os.path.join(project_root, "template_projects", f"io_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "io.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    random.seed(int(project_id))
    pid = project_id

    content = content.replace("${PRINT_MSG_1}", f"Starting I/O test #{pid}")
    content = content.replace("${PRINT_MSG_2}", "Output to stdout works")
    content = content.replace("${PERROR_MSG}", f"Stderr test message #{pid}")

    content = content.replace("${OUTPUT_FILE}", f"test_output_{pid}.txt")
    content = content.replace("${WRITE_MODE}", "w")
    content = content.replace("${ENCODING}", "utf-8")

    lines = random.choice(FILE_CONTENTS)
    content = content.replace("${FILE_CONTENT_LINE1}", lines[0])
    content = content.replace("${FILE_CONTENT_LINE2}", lines[1])
    content = content.replace("${FILE_CONTENT_LINE3}", lines[2])

    content = content.replace("${READ_MODE}", "r")
    content = content.replace("${READ_MSG}", f"Content of test_output_{pid}.txt:")

    bin_vals = ", ".join(str(random.randint(0, 255)) for _ in range(random.randint(4, 8)))
    content = content.replace("${BIN_DATA}", f"bin_data_{pid}")
    content = content.replace("${BIN_VALUES}", bin_vals)
    content = content.replace("${BIN_FILE}", f"test_binary_{pid}.bin")
    content = content.replace("${BIN_MODE}", "wb")
    content = content.replace("${BIN_READ_MODE}", "rb")

    content = content.replace("${PRINT_MESSAGE}", f"I/O test #{pid} completed")

    output_path = os.path.join(output_dir, "io.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python io.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
