# -*- coding: utf-8 -*-
TOKEN_POSTFIX: str = ".vlatoken"
SYMBOL_TABLE_POSTFIX: str = ".vlasymtab"
PARSING_LOCK_POSTFIX: str = ".parsing.lock"
SYMBOL_TYPE_POSTFIX: str = ".vlasymt"
COMMAND_POSTFIX: str = ".vlacmd"
GLOBAL_COMMAND_POSTFIX: str = ".vlacmd0"
EXPR_TOKENS_POSTFIX: str = ".vlaexpr"
IMPORTS_POSTFIX: str = ".vlaimports"
CACHE_DIR: str = "__viola_cache__"
MAKE_CONFIG_POSTFIX: str = ".vlamk.toml"
LOG_DIR: str = "__log__"

import hashlib
import os
import threading
import time


def write_text_atomic(path: str, text: str) -> None:
    """
    原子写出文本文件：先写同目录下的临时文件，再改名到目标路径。

    并发读取缓存文件时（见开发疑问记录128），若直接以"w"打开目标文件，
    文件在写入期间会先被截断，读者可能读到写了一半的内容。改为"写临时
    文件+改名"后，目标文件在任何时刻都是一个完整版本。

    编码与换行符沿用原直接写出的行为（不显式指定），以保证缓存文件
    的字节内容与改动前一致。
    :param path: 目标文件路径。
    :param text: 要写入的文本。
    """
    temp_path: str = f"{path}.tmp${os.getpid()}${threading.get_ident()}"
    try:
        with open(temp_path, "w") as file:
            file.write(text)
        for _ in range(50):
            try:
                os.replace(temp_path, path)
                return
            except OSError:
                # 目标文件可能正被读者/其他进程打开（Windows下改名会被拒绝），
                # 稍后重试
                time.sleep(0.02)
        # 长时间无法改名（如目标被其他进程独占）：退化为直接写出，
        # 与改动前行为一致，避免此处直接失败
        with open(path, "w") as file:
            file.write(text)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def get_cache_path(workspace: str, src_path: str) -> str:
    """
    计算源文件对应的缓存路径（不含后缀）。

    工作区内的文件按相对工作区的路径镜像到工作区缓存目录下。
    工作区之外的文件（如VIOLA_HOME中的运行库模块）若直接使用相对路径，
    其中的".."段会把缓存写到源文件旁边（例如violac/viola_libs/），
    --clear-cache无法覆盖，残留缓存会导致模块被错误跳过、
    或生成与修改后的.vla声明不符的代码（见开发疑问记录94）。
    此类文件改为在缓存目录的__external__子目录下按绝对路径编码命名。
    :param workspace: 工作区根目录。
    :param src_path: 源文件路径。
    :return: 缓存路径（不含后缀）。
    """
    abs_src: str = os.path.abspath(src_path)
    rel: str = os.path.relpath(abs_src, os.path.abspath(workspace))
    if rel != ".." and not rel.startswith(".." + os.sep):
        return os.path.join(workspace, CACHE_DIR, rel)
    # 以绝对路径的哈希+文件名命名，避免路径过长（Windows的路径长度限制）
    # 以及不同库目录下的同名模块互相覆盖
    digest: str = hashlib.sha1(abs_src.encode("utf-8")).hexdigest()[:16]
    return os.path.join(workspace, CACHE_DIR, "__external__", digest + "$" + os.path.basename(abs_src))


def set_file_lock(path: str) -> bool:
    """
    设置文件解析锁（防止并发处理同一缓存文件）。
    使用排他创建保证原子性：若锁文件已存在则说明其他线程正在处理该文件。
    :param path: 文件路径（不含锁后缀）。
    :return: 锁文件已存在（其他线程正在处理）时返回False，否则返回True。
    """
    lock_path: str = path + PARSING_LOCK_POSTFIX
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    try:
        with open(lock_path, "x") as file:
            file.write("")
    except (FileExistsError, PermissionError):
        # 锁文件已存在，或正被其他线程创建/删除，视为已有其他线程在处理
        return False
    return True


def remove_file_lock(path: str) -> None:
    """
    移除文件解析锁。容忍锁文件已被删除或暂时被占用的情况。
    :param path: 文件路径（不含锁后缀）。
    """
    lock_path: str = path + PARSING_LOCK_POSTFIX
    for _ in range(10):
        try:
            os.remove(lock_path)
            return
        except FileNotFoundError:
            return
        except OSError:
            # 锁文件正被其他线程短暂占用，稍后重试
            time.sleep(0.05)
