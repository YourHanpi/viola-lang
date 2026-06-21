# -*- coding: utf-8 -*-
import os
import psutil
import subprocess
import sys
import time
import traceback


def main() -> None:
    root: str = os.path.join(os.path.dirname(str(__file__)), "src")
    tests: list[str] = os.listdir(root)
    memory_max_bytes: int = 1024 * 1024 * 1024 * 1
    if os.name == "nt":
        subprocess.run(["chcp", "65001"], text=True, shell=True)
    for test in tests:
        try:
            process = subprocess.Popen(
                [sys.executable, os.path.join(root, test)]
            )
            ps_process = psutil.Process(process.pid)
            while process.poll() is None:
                if psutil.pid_exists(process.pid) and ps_process.memory_info().rss > memory_max_bytes:
                    process.kill()
                    print(f"{test} exceeded memory limit", file=sys.stderr)
                    time.sleep(1)
                    break
        except subprocess.TimeoutExpired:
            print(f"{test} timed out", file=sys.stderr)
        except psutil.NoSuchProcess:
            pass
        except Exception:
            print(f"{test} failed: \n{traceback.format_exc()}", file=sys.stderr)


if __name__ == "__main__":
    main()
