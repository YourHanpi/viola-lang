# -*- coding: utf-8 -*-
"""编译器单元测试运行器。

逐个运行src目录下的测试脚本，并在其常驻内存集超过上限时终止该进程
（部分测试会构造大规模符号表，失控时以内存上限兜底，避免拖垮整机）。

进程内存的读取原先借助第三方库psutil；为将来能够自举，本项目不使用第三方库
（见README_zh.md与versions_dev_plan_zh.md"漏洞修复"），故改为使用
标准库自行实现：Windows下调用process status API，其他平台读取/proc。
"""
import os
import subprocess
import sys
import time
import traceback

MEMORY_MAX_BYTES: int = 1024 * 1024 * 1024 * 1


def get_process_rss(pid: int) -> "int | None":
    """获取进程的常驻内存集（字节）。

    进程已结束或无法查询时返回None（等价于原先psutil.NoSuchProcess的语义）。
    """
    if os.name == "nt":
        return _get_process_rss_windows(pid)
    return _get_process_rss_posix(pid)


# ================= Windows：process status API =================
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _ProcessMemoryCounters(ctypes.Structure):
        """PROCESS_MEMORY_COUNTERS（见Windows SDK的psapi.h）。"""
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    _PROCESS_QUERY_LIMITED_INFORMATION: int = 0x1000
    _PROCESS_QUERY_INFORMATION: int = 0x0400
    _PROCESS_VM_READ: int = 0x0010
    _STILL_ACTIVE: int = 259

    def _load_get_process_memory_info():
        """获取GetProcessMemoryInfo（优先kernel32的K32版本，回退psapi）。"""
        for dll_name, func_name in (("kernel32", "K32GetProcessMemoryInfo"),
                                    ("psapi", "GetProcessMemoryInfo")):
            try:
                dll = ctypes.WinDLL(dll_name)
            except OSError:
                continue
            func = getattr(dll, func_name, None)
            if func is None:
                continue
            func.argtypes = [wintypes.HANDLE,
                             ctypes.POINTER(_ProcessMemoryCounters),
                             wintypes.DWORD]
            func.restype = wintypes.BOOL
            return func
        return None

    _get_process_memory_info = _load_get_process_memory_info()

    def _is_process_alive(handle) -> bool:
        """判断进程是否仍在运行（对应原先的psutil.pid_exists）。"""
        exit_code = wintypes.DWORD()
        if not ctypes.WinDLL("kernel32").GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == _STILL_ACTIVE

    def _get_process_rss_windows(pid: int) -> "int | None":
        if _get_process_memory_info is None:
            return None
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION | _PROCESS_QUERY_INFORMATION | _PROCESS_VM_READ,
            False, pid)
        if not handle:
            # 进程已结束（或权限不足）：等价于原先的psutil.NoSuchProcess
            return None
        try:
            if not _is_process_alive(handle):
                return None
            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
            if not _get_process_memory_info(handle, ctypes.byref(counters), counters.cb):
                return None
            return int(counters.WorkingSetSize)
        finally:
            kernel32.CloseHandle(handle)


# ================= POSIX：/proc =================
def _get_process_rss_posix(pid: int) -> "int | None":
    """读取/proc/<pid>/statm的第二项（常驻页数）并换算为字节。"""
    try:
        with open(f"/proc/{pid}/statm", "r", encoding="ascii") as f:
            fields: list[str] = f.read().split()
    except OSError:
        return None
    if len(fields) < 2:
        return None
    try:
        resident_pages: int = int(fields[1])
    except ValueError:
        return None
    return resident_pages * os.sysconf("SC_PAGE_SIZE")


def main() -> None:
    root: str = os.path.join(os.path.dirname(str(__file__)), "src")
    tests: list[str] = os.listdir(root)
    if os.name == "nt":
        subprocess.run(["chcp", "65001"], text=True, shell=True)
    for test in tests:
        process: "subprocess.Popen | None" = None
        try:
            process = subprocess.Popen(
                [sys.executable, os.path.join(root, test)]
            )
            while process.poll() is None:
                rss: "int | None" = get_process_rss(process.pid)
                if rss is None:
                    # 进程已结束：交给下一轮poll判断退出码
                    time.sleep(0.05)
                    continue
                if rss > MEMORY_MAX_BYTES:
                    process.kill()
                    print(f"{test} exceeded memory limit", file=sys.stderr)
                    time.sleep(1)
                    break
                time.sleep(0.05)
        except subprocess.TimeoutExpired:
            print(f"{test} timed out", file=sys.stderr)
        except Exception:
            print(f"{test} failed: \n{traceback.format_exc()}", file=sys.stderr)


if __name__ == "__main__":
    main()
