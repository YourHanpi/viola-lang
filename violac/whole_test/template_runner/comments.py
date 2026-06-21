"""Random filler for comments test template.

Usage:
    python comments.py <project_id>

Generates: template_projects/comments_<project_id>/comments.vla
"""

import os
import random
import sys


SINGLE_LINE_COMMENTS = [
    "This is a single-line comment for testing purposes",
    "TODO: Implement additional features",
    "FIXME: Review this section",
    "NOTE: This is an important note",
    "HACK: Temporary workaround",
    "DEBUG: Debug output follows",
    "INFO: Configuration options below",
    "WARNING: Sensitive code ahead",
]

MULTI_LINE_PHRASES = [
    ["Multi-line comment block", "This is the second line", "This is the third line"],
    ["Copyright notice", "All rights reserved", "Do not distribute without permission"],
    ["Algorithm description:", "Step 1: Initialize variables", "Step 2: Process data", "Step 3: Output results"],
    ["Configuration block", "Setting A: enabled", "Setting B: disabled"],
]

OUTPUT_MESSAGES = [
    "Comments test completed successfully",
    "All comment styles verified",
    "Comment syntax validation passed",
    "No issues found with comments",
]


def generate(project_id: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    template_dir = os.path.join(project_root, "template", "comments")
    output_dir = os.path.join(project_root, "template_projects", f"comments_{project_id}")

    os.makedirs(output_dir, exist_ok=True)

    template_path = os.path.join(template_dir, "comments.vla")
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Generate single-line comments
    for i in range(1, 3):
        content = content.replace(f"${{SINGLE_LINE_COMMENT_{i}}}", random.choice(SINGLE_LINE_COMMENTS))

    # Generate multi-line comments
    ml_phrases = random.choice(MULTI_LINE_PHRASES)
    for i, phrase in enumerate(ml_phrases[:4]):
        content = content.replace(f"${{MULTI_LINE_COMMENT_LINE{i+1}}}", phrase)

    # Fill remaining multi-line slots if any
    for i in range(len(ml_phrases) + 1, 5):
        content = content.replace(f"${{MULTI_LINE_COMMENT_LINE{i}}}", "")

    content = content.replace("${OUTPUT_MESSAGE}", random.choice(OUTPUT_MESSAGES))

    output_path = os.path.join(output_dir, "comments.vla")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python comments.py <project_id>")
        sys.exit(1)
    generate(sys.argv[1])
