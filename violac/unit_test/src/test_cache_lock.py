# -*- coding: utf-8 -*-
"""Unit tests for cache file concurrency (see 开发疑问记录128).

写侧以"w"打开缓存文件时会先截断，读侧若不加锁直接读取，
就可能读到写了一半的内容（模块导入映射因此不完整，后端报
"Type xxx not found"）。这里验证两处保证：
    - 缓存文件原子写出（utils.file_marks.write_text_atomic）；
    - GlobalParser._cache_read_lock 与写侧互斥。
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock

# Add source path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "violac", "src")))

from utils.file_marks import set_file_lock, remove_file_lock, write_text_atomic
from frontend.global_parser import GlobalParser

_SYMBOL_TYPE_POSTFIX: str = ".vlasymt"

# 两段合法内容：读到其中任意一段的完整文本即为"读到了完整版本"
_CONTENTS: list[str] = [
    "".join(f"symbolA{i}%uint32%[]\n" for i in range(200)),
    "".join(f"symbolB{i}%string%[]\n" for i in range(200)),
]


class TestWriteTextAtomic(unittest.TestCase):
    """Tests for write_text_atomic."""

    def test_writes_content(self):
        """写出后的文件内容应与传入文本一致。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "target.vlasymt")
            write_text_atomic(path, "hello\nworld\n")
            with open(path, "r") as f:
                self.assertEqual(f.read(), "hello\nworld\n")

    def test_no_temp_file_left_behind(self):
        """写出后不应残留临时文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "target.vlasymt")
            write_text_atomic(path, "content")
            self.assertEqual(sorted(os.listdir(tmp)), ["target.vlasymt"])

    def test_reader_never_sees_partial_content(self):
        """并发写出时，未加锁的读者也只应读到某个完整版本。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "target.vlasymt")
            write_text_atomic(path, _CONTENTS[0])
            stop = threading.Event()
            partial: list[str] = []

            def writer() -> None:
                i = 0
                while not stop.is_set():
                    write_text_atomic(path, _CONTENTS[i % 2])
                    i += 1

            def reader() -> None:
                while not stop.is_set():
                    try:
                        with open(path, "r") as f:
                            text = f.read()
                    except OSError:
                        # Windows下改名与打开可能瞬时互斥（共享冲突），跳过本次
                        continue
                    if text not in _CONTENTS:
                        partial.append(text)

            threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
            for t in threads:
                t.start()
            time.sleep(1.0)
            stop.set()
            for t in threads:
                t.join()
            self.assertEqual(partial, [], "原子写出下读者读到了不完整的内容")


class TestCacheReadLock(unittest.TestCase):
    """Tests for GlobalParser._cache_read_lock."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._workspace = self._tmp.name
        self._parser = GlobalParser(self._workspace)
        # 单元测试环境中日志文件未打开，替换为mock以免输出与异常干扰
        self._parser._logger = MagicMock()
        self._cache_path = os.path.join(self._workspace, "module")

    def tearDown(self):
        self._tmp.cleanup()

    def test_read_lock_excludes_locked_writer(self):
        """写侧在同一把锁内以截断方式写出时，读者不应读到部分内容。"""
        target = self._cache_path + _SYMBOL_TYPE_POSTFIX
        write_text_atomic(target, _CONTENTS[0])
        stop = threading.Event()
        partial: list[str] = []
        reads: list[int] = [0]

        def writer() -> None:
            i = 0
            while not stop.is_set():
                # 与真实写侧一致：持锁 + 截断写出（分两段写入以放大写入窗口）
                if not set_file_lock(self._cache_path):
                    time.sleep(0.001)
                    continue
                try:
                    with open(target, "w") as f:
                        f.write(_CONTENTS[i % 2][: len(_CONTENTS[0]) // 2])
                        f.flush()
                        time.sleep(0.002)
                        f.write(_CONTENTS[i % 2][len(_CONTENTS[0]) // 2:])
                    i += 1
                finally:
                    remove_file_lock(self._cache_path)

        def reader() -> None:
            while not stop.is_set():
                with self._parser._cache_read_lock(self._cache_path, timeout=5.0):
                    try:
                        with open(target, "r") as f:
                            text = f.read()
                    except OSError:
                        continue
                reads[0] += 1
                if text not in _CONTENTS:
                    partial.append(text)

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        time.sleep(1.0)
        stop.set()
        for t in threads:
            t.join()
        self.assertGreater(reads[0], 0, "读者一次都没有读取成功")
        self.assertEqual(partial, [], "持锁读取仍读到了不完整的内容")

    def test_read_lock_does_not_deadlock_on_reentrancy(self):
        """本实例已持有该锁时，重复获取不应死等（超时返回）。"""
        self._parser._held_locks.add(self._cache_path)
        self.assertTrue(set_file_lock(self._cache_path))
        try:
            start = time.time()
            with self._parser._cache_read_lock(self._cache_path, timeout=1.0):
                pass
            self.assertLess(time.time() - start, 1.0, "重入时不应急需等待")
        finally:
            remove_file_lock(self._cache_path)

    def test_read_lock_timeout_when_held_by_other(self):
        """锁被其他持有者占用时，超时后应退化为直接读取而不是永久等待。"""
        self.assertTrue(set_file_lock(self._cache_path))
        try:
            start = time.time()
            with self._parser._cache_read_lock(self._cache_path, timeout=0.2) as acquired:
                self.assertFalse(acquired)
            self.assertGreaterEqual(time.time() - start, 0.2)
        finally:
            remove_file_lock(self._cache_path)

    def test_read_lock_releases_after_use(self):
        """正常读取后应释放锁，使其他持有者可以获取。"""
        with self._parser._cache_read_lock(self._cache_path, timeout=1.0) as acquired:
            self.assertTrue(acquired)
            self.assertTrue(os.path.exists(self._cache_path + ".parsing.lock"))
        self.assertFalse(os.path.exists(self._cache_path + ".parsing.lock"))


if __name__ == "__main__":
    unittest.main()
