# -*- coding: utf-8 -*-
import os


def _remove_binary_files(directory: str) -> None:
    for p in os.listdir(directory):
        path = os.path.join(directory, p)
        if os.path.isfile(path) and os.path.splitext(path)[1] in {".pyc", ".o", ".pyd", ".so", ".exe", ".dll", ".dylib", ".lib", ".a", ".bin"}:
            os.remove(path)
        elif os.path.isdir(path):
            print(f"[REMOVE]{path}")
            _remove_binary_files(path)


def main() -> None:
    os.chdir(os.path.dirname(str(os.path.dirname(str(os.path.dirname(__file__))))))
    _remove_binary_files(os.path.join("violac", "whole_test", "test_compiled"))


if __name__ == "__main__":
    main()
