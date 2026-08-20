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

import os
import time


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
