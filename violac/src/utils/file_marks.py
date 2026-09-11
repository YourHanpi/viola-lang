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
import time


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
