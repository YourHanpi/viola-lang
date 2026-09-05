# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys


def generate_project(count: int) -> None:
    runner_dir = "./template_runner"
    if os.path.exists("./template_projects"):
        shutil.rmtree("./template_projects")
    os.mkdir("./template_projects")
    for name in os.listdir(runner_dir):
        for i in range(count):
            subprocess.run(["python", os.path.join(runner_dir, name), str(i)])


def main() -> None:
    if len(sys.argv) == 1:
        generate_project(8)
    elif len(sys.argv) == 2:
        generate_project(int(sys.argv[1]))
    else:
        print("Usage: python generate_test.py <count>")


if __name__ == "__main__":
    main()
