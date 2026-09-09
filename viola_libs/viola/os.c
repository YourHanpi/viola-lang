/* -*- coding: utf-8 -*-
 * Viola操作系统接口运行库：绑定Windows和POSIX的相关接口，使用条件编译。
 * 命名空间：viola.os（C标识符前缀 viola$os$）。
 *
 * 模型：涉及文件操作的函数由子线程发送请求（经全局资源管理器入队），
 * 主线程在waitListener的空闲期间执行请求并返回相关数据；主线程自身
 * 的操作直接执行（模型同viola/io/file.c）。
 * 纯计算类函数（getuid/getgid/major/makedev/minor等）直接执行。
 *
 * 0.1版Viola尚无异常机制：sq函数执行失败时静默忽略；
 * fn函数失败时返回约定值（-1、0或空字符串，见各函数注释）。
 */
#include "lang/global_resource_manager.h"
#include "lang/string.h"
#include "threads.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <direct.h>
#include <fcntl.h>
#include <wchar.h>
#include <sys/utime.h>
#else
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <utime.h>
#include <limits.h>
#include <sched.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/statvfs.h>
#ifdef __linux__
#include <sys/sysmacros.h>
#include <pty.h>
#endif
#endif

/* ================= 编译器生成的类结构体布局 ================= */
/* 与编译器为os.vla中的wrapper class Stat/StatVFS生成的结构体一致：
   布局为 $$vtable、属性（按声明顺序）、$refCount、$parent。
   本TU不包含生成的os.vla.h，因此自行声明相同布局。 */
typedef struct viola$os$Stat {
    viola$lang$ptr $$vtable;
    viola$lang$uint32 st_mode;
    viola$lang$uint64 st_ino;
    viola$lang$uint64 st_dev;
    viola$lang$uint64 st_nlink;
    viola$lang$uint32 st_uid;
    viola$lang$uint32 st_gid;
    viola$lang$uint64 st_size;
    viola$lang$uint64 st_atime;
    viola$lang$uint64 st_mtime;
    viola$lang$uint64 st_ctime;
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
} viola$os$Stat;

typedef struct viola$os$StatVFS {
    viola$lang$ptr $$vtable;
    viola$lang$uint64 f_bsize;
    viola$lang$uint64 f_frsize;
    viola$lang$uint64 f_blocks;
    viola$lang$uint64 f_bfree;
    viola$lang$uint64 f_bavail;
    viola$lang$uint64 f_files;
    viola$lang$uint64 f_ffree;
    viola$lang$uint64 f_favail;
    viola$lang$uint64 f_flag;
    viola$lang$uint64 f_namemax;
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
} viola$os$StatVFS;

/* ================= 全局变量（os.vla中的声明） ================= */

viola$lang$int32 viola$os$STDERR_FILENO = 2;
viola$lang$int32 viola$os$STDIN_FILENO = 0;
viola$lang$int32 viola$os$STDOUT_FILENO = 1;

/* open的flags常量：统一采用POSIX取值（Windows上由viola$os$open转换） */
viola$lang$uint32 viola$os$O_RDONLY = 0x0;
viola$lang$uint32 viola$os$O_WRONLY = 0x1;
viola$lang$uint32 viola$os$O_RDWR = 0x2;
viola$lang$uint32 viola$os$O_CREAT = 0x40;
viola$lang$uint32 viola$os$O_EXCL = 0x80;
viola$lang$uint32 viola$os$O_TRUNC = 0x200;
viola$lang$uint32 viola$os$O_APPEND = 0x400;
viola$lang$uint32 viola$os$O_BINARY = 0x0; /* POSIX上无二进制模式 */

/* 默认参数全局变量（编译器生成的默认参数引用指向这里） */
viola$lang$uint32 viola$os$makedirs$$default$mode = 0777;
viola$lang$uint32 viola$os$mkdir$$default$mode = 0777;
viola$lang$uint32 viola$os$mkfifo$$default$mode = 0666;
viola$lang$uint32 viola$os$mknod$$default$mode = 0666;
viola$lang$uint32 viola$os$mknod$$default$dev = 0;
viola$lang$uint32 viola$os$open$$default$mode = 0666;

/* ================= 基本工具 ================= */

static viola$lang$string *newStringFromBytes(const unsigned char *bytes, size_t length) {
    viola$lang$string *s = (viola$lang$string *)malloc(sizeof(viola$lang$string));
    s->$refCount = 1;
    s->$parent = NULL;
    s->length = (viola$lang$uint64)length;
    if (length > 0) {
        s->data = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * length);
        for (size_t i = 0; i < length; i++) {
            s->data[i] = (viola$lang$uint16)bytes[i];
        }
    } else {
        s->data = NULL;
    }
    return s;
}

static viola$os$Stat *newStat(void) {
    viola$os$Stat *s = (viola$os$Stat *)malloc(sizeof(viola$os$Stat));
    memset(s, 0, sizeof(viola$os$Stat));
    s->$$vtable = NULL;
    s->$refCount = 1;
    s->$parent = NULL;
    return s;
}

static viola$os$StatVFS *newStatVFS(void) {
    viola$os$StatVFS *s = (viola$os$StatVFS *)malloc(sizeof(viola$os$StatVFS));
    memset(s, 0, sizeof(viola$os$StatVFS));
    s->$$vtable = NULL;
    s->$refCount = 1;
    s->$parent = NULL;
    return s;
}

#ifdef _WIN32
/* Viola字符串（UTF-16）转宽字符串（调用方负责释放） */
static wchar_t *toWide(const viola$lang$string *s) {
    if (s == NULL) {
        return NULL;
    }
    wchar_t *w = (wchar_t *)malloc(sizeof(wchar_t) * (s->length + 1));
    for (viola$lang$uint64 i = 0; i < s->length; i++) {
        w[i] = (wchar_t)s->data[i];
    }
    w[s->length] = L'\0';
    return w;
}
#endif

static void yieldCPU(void) {
#ifdef _WIN32
    Sleep(0);
#else
    sched_yield();
#endif
}

/* ================= 请求机制 ================= */

/* 请求类型编码：与viola/io/file.c（1~6）和viola/os/path.c（201起）的
   请求类型不重叠（请求向量表按类型索引，重叠会互相覆盖处理器） */
enum {
    VIOLA_OS_REQUEST_ACCESS = 101,
    VIOLA_OS_REQUEST_CHDIR,
    VIOLA_OS_REQUEST_CHFLAGS,
    VIOLA_OS_REQUEST_CHMOD,
    VIOLA_OS_REQUEST_CHOWN,
    VIOLA_OS_REQUEST_CHROOT,
    VIOLA_OS_REQUEST_CLOSE,
    VIOLA_OS_REQUEST_CLOSERANGE,
    VIOLA_OS_REQUEST_DUP,
    VIOLA_OS_REQUEST_DUP2,
    VIOLA_OS_REQUEST_FCHDIR,
    VIOLA_OS_REQUEST_FCHMOD,
    VIOLA_OS_REQUEST_FCHOWN,
    VIOLA_OS_REQUEST_FDATASYNC,
    VIOLA_OS_REQUEST_FDOPEN,
    VIOLA_OS_REQUEST_FPATHCONF,
    VIOLA_OS_REQUEST_FSTAT,
    VIOLA_OS_REQUEST_FTRUNCATE,
    VIOLA_OS_REQUEST_GETCWD,
    VIOLA_OS_REQUEST_ISATTY,
    VIOLA_OS_REQUEST_LCHFLAGS,
    VIOLA_OS_REQUEST_LCHMOD,
    VIOLA_OS_REQUEST_LCHOWN,
    VIOLA_OS_REQUEST_LINK,
    VIOLA_OS_REQUEST_LISTDIR,
    VIOLA_OS_REQUEST_LSEEK,
    VIOLA_OS_REQUEST_LSTAT,
    VIOLA_OS_REQUEST_MAKEDIRS,
    VIOLA_OS_REQUEST_MKDIR,
    VIOLA_OS_REQUEST_MKFIFO,
    VIOLA_OS_REQUEST_MKNOD,
    VIOLA_OS_REQUEST_OPEN,
    VIOLA_OS_REQUEST_OPENPTY,
    VIOLA_OS_REQUEST_PATHCONF,
    VIOLA_OS_REQUEST_PIPE,
    VIOLA_OS_REQUEST_POPEN,
    VIOLA_OS_REQUEST_READ,
    VIOLA_OS_REQUEST_READLINK,
    VIOLA_OS_REQUEST_REMOVE,
    VIOLA_OS_REQUEST_REMOVEDIRS,
    VIOLA_OS_REQUEST_RENAME,
    VIOLA_OS_REQUEST_RENAMES,
    VIOLA_OS_REQUEST_RMDIR,
    VIOLA_OS_REQUEST_STAT,
    VIOLA_OS_REQUEST_STATVFS,
    VIOLA_OS_REQUEST_TCGETPGRP,
    VIOLA_OS_REQUEST_TCSETPGRP,
    VIOLA_OS_REQUEST_TTYNAME,
    VIOLA_OS_REQUEST_UNLINK,
    VIOLA_OS_REQUEST_UTIME,
    VIOLA_OS_REQUEST_WRITE
};

/* 请求结构体（第一个成员是请求类型编码） */
typedef struct viola$os$OsRequest {
    viola$lang$global_resource_manager$Request base;
    viola$lang$string *path;
    viola$lang$string *path2;
    viola$lang$string *data;
    viola$lang$uint32 mode;
    viola$lang$uint32 flags;
    viola$lang$uint32 uid;
    viola$lang$uint32 gid;
    viola$lang$uint32 nbyte;
    viola$lang$uint32 size;
    viola$lang$uint32 dev;
    viola$lang$uint32 atime;
    viola$lang$uint32 mtime;
    viola$lang$int32 fd;
    viola$lang$int32 fd2;
    viola$lang$int32 offset;
    viola$lang$int32 whence;
    viola$lang$int32 name;
    viola$lang$int32 pgid;
    viola$lang$bool *resultBool;
    viola$lang$int32 *resultInt;
    viola$lang$uint32 *resultU32;
    viola$lang$string **resultString;
    viola$lang$string$$array **resultStringArray;
    viola$os$Stat **resultStat;
    viola$os$StatVFS **resultStatVFS;
    viola$io$file **resultFile;
    volatile uint8_t done;
} viola$os$OsRequest;

/* 子线程提交请求并等待主线程执行（主线程直接执行） */
static void submitOrRun(viola$os$OsRequest *request, viola$threads$Listener *listener) {
    if (listener != NULL && listener->currentThreadId == 0) {
        viola$lang$global_resource_manager$handleRequest(&request->base);
        return;
    }
    request->done = 0;
    viola$lang$global_resource_manager$enqueueRequest(&request->base);
    while (!request->done) {
        yieldCPU();
    }
}

/* 分配并初始化一个请求 */
static viola$os$OsRequest *newRequest(viola$lang$global_resource_manager$RequestType type) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)malloc(sizeof(viola$os$OsRequest));
    memset(req, 0, sizeof(viola$os$OsRequest));
    req->base.type = type;
    return req;
}

/* ================= 请求处理器 ================= */

#ifdef _WIN32

static void handleAccess(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    int mode = 0;
    if (req->mode == 0) {
        mode = 0;
    } else if ((req->mode & 4) && (req->mode & 2)) {
        mode = 6;
    } else if (req->mode & 4) {
        mode = 4;
    } else if (req->mode & 2) {
        mode = 2;
    } else {
        mode = 0;
    }
    *req->resultBool = _waccess(wide, mode) == 0;
    free(wide);
    req->done = 1;
}

static void handleChdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    _wchdir(wide);
    free(wide);
    req->done = 1;
}

static void handleChmod(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    _wchmod(wide, (int)req->mode);
    free(wide);
    req->done = 1;
}

static void handleClose(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    _close(req->fd);
    req->done = 1;
}

static void handleCloseRange(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    for (viola$lang$int32 fd = req->fd; fd <= req->fd2; fd++) {
        _close(fd);
    }
    req->done = 1;
}

static void handleDup(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = _dup(req->fd);
    req->done = 1;
}

static void handleDup2(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = _dup2(req->fd, req->fd2);
    req->done = 1;
}

static void handleFdatasync(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    _commit(req->fd);
    req->done = 1;
}

static void handleFdopen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    FILE *fp = _fdopen(req->fd, "r");
    if (fp == NULL) {
        *req->resultFile = NULL;
    } else {
        viola$io$file *f = (viola$io$file *)malloc(sizeof(viola$io$file));
        f->$refCount = 1;
        f->$parent = NULL;
        f->$$vtable = NULL;
        f->fp = fp;
        f->isPopen = 0;
        *req->resultFile = f;
    }
    req->done = 1;
}

static void handleFstat(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$Stat *s = newStat();
    struct _stat64 st;
    if (_fstat64(req->fd, &st) == 0) {
        s->st_mode = (viola$lang$uint32)st.st_mode;
        s->st_ino = (viola$lang$uint64)st.st_ino;
        s->st_dev = (viola$lang$uint64)st.st_dev;
        s->st_nlink = (viola$lang$uint64)st.st_nlink;
        s->st_uid = (viola$lang$uint32)st.st_uid;
        s->st_gid = (viola$lang$uint32)st.st_gid;
        s->st_size = (viola$lang$uint64)st.st_size;
        s->st_atime = (viola$lang$uint64)st.st_atime;
        s->st_mtime = (viola$lang$uint64)st.st_mtime;
        s->st_ctime = (viola$lang$uint64)st.st_ctime;
    }
    *req->resultStat = s;
    req->done = 1;
}

static void handleFtruncate(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    _chsize(req->fd, (long)req->size);
    req->done = 1;
}

static void handleGetCwd(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t buffer[4096];
    if (_wgetcwd(buffer, 4096) != NULL) {
        size_t len = wcslen(buffer);
        viola$lang$uint16 *units = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * len);
        for (size_t i = 0; i < len; i++) {
            units[i] = (viola$lang$uint16)buffer[i];
        }
        viola$lang$string *s = (viola$lang$string *)malloc(sizeof(viola$lang$string));
        s->$refCount = 1;
        s->$parent = NULL;
        s->length = (viola$lang$uint64)len;
        if (len > 0) {
            s->data = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * len);
            memcpy(s->data, units, sizeof(viola$lang$uint16) * len);
        } else {
            s->data = NULL;
        }
        free(units);
        *req->resultString = s;
    } else {
        *req->resultString = viola$lang$string$fromCharString("");
    }
    req->done = 1;
}

static void handleIsatty(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultBool = _isatty(req->fd) != 0;
    req->done = 1;
}

static void handleLink(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *newPath = toWide(req->path2);
    wchar_t *oldPath = toWide(req->path);
    CreateHardLinkW(newPath, oldPath, NULL);
    free(newPath);
    free(oldPath);
    req->done = 1;
}

static void handleListDir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    /* 统计数量 */
    viola$lang$string$$array *arr = (viola$lang$string$$array *)malloc(
        sizeof(viola$lang$string$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->data = NULL;
    arr->size = 0;
    wchar_t *pattern = toWide(req->path);
    size_t plen = wcslen(pattern);
    pattern = (wchar_t *)realloc(pattern, sizeof(wchar_t) * (plen + 3));
    if (plen > 0 && pattern[plen - 1] != L'\\' && pattern[plen - 1] != L'/') {
        pattern[plen++] = L'\\';
    }
    pattern[plen++] = L'*';
    pattern[plen] = L'\0';
    WIN32_FIND_DATAW findData;
    HANDLE hFind = FindFirstFileW(pattern, &findData);
    if (hFind != INVALID_HANDLE_VALUE) {
        viola$lang$uint64 capacity = 0;
        viola$lang$uint64 count = 0;
        do {
            if (wcscmp(findData.cFileName, L".") == 0 || wcscmp(findData.cFileName, L"..") == 0) {
                continue;
            }
            if (count >= capacity) {
                capacity = capacity == 0 ? 8 : capacity * 2;
                arr->data = (viola$lang$string **)realloc(arr->data,
                                                          sizeof(viola$lang$string *) * capacity);
            }
            size_t nameLen = wcslen(findData.cFileName);
            viola$lang$string *name = (viola$lang$string *)malloc(sizeof(viola$lang$string));
            name->$refCount = 1;
            name->$parent = NULL;
            name->length = (viola$lang$uint64)nameLen;
            name->data = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * nameLen);
            for (size_t i = 0; i < nameLen; i++) {
                name->data[i] = (viola$lang$uint16)findData.cFileName[i];
            }
            arr->data[count++] = name;
        } while (FindNextFileW(hFind, &findData));
        FindClose(hFind);
        arr->size = count;
    }
    free(pattern);
    *req->resultStringArray = arr;
    req->done = 1;
}

static void handleLseek(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = (viola$lang$int32)_lseeki64(req->fd, req->offset, req->whence);
    req->done = 1;
}

static void handleMakedirs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *path = toWide(req->path);
    /* 自底向上递归创建目录 */
    size_t len = wcslen(path);
    wchar_t *tmp = (wchar_t *)malloc(sizeof(wchar_t) * (len + 1));
    memcpy(tmp, path, sizeof(wchar_t) * (len + 1));
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == L'\\' || tmp[i - 1] == L'/') {
            tmp[i - 1] = L'\0';
            _wmkdir(tmp);
        }
    }
    _wmkdir(tmp);
    free(tmp);
    free(path);
    req->done = 1;
}

static void handleMkdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    _wmkdir(wide);
    free(wide);
    req->done = 1;
}

static void handleOpen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    int flags = _O_BINARY;
    if ((req->flags & 0x2) != 0) {
        flags |= _O_RDWR;
    } else if ((req->flags & 0x1) != 0) {
        flags |= _O_WRONLY;
    } else {
        flags |= _O_RDONLY;
    }
    if ((req->flags & 0x40) != 0) {
        flags |= _O_CREAT;
    }
    if ((req->flags & 0x80) != 0) {
        flags |= _O_EXCL;
    }
    if ((req->flags & 0x200) != 0) {
        flags |= _O_TRUNC;
    }
    if ((req->flags & 0x400) != 0) {
        flags |= _O_APPEND;
    }
    int pmode = 0;
    if ((req->mode & 0x100) != 0) {
        pmode |= _S_IREAD;
    }
    if ((req->mode & 0x80) != 0) {
        pmode |= _S_IWRITE;
    }
    *req->resultInt = _wopen(wide, flags, pmode);
    free(wide);
    req->done = 1;
}

static void handlePipe(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    int fds[2];
    if (_pipe(fds, 256, _O_BINARY) == 0) {
        *req->resultInt = fds[0];
    } else {
        *req->resultInt = -1;
    }
    req->done = 1;
}

static void handlePopen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *command = toWide(req->path);
    wchar_t *mode = toWide(req->data);
    FILE *fp = _wpopen(command, mode);
    free(command);
    free(mode);
    if (fp == NULL) {
        *req->resultFile = NULL;
    } else {
        viola$io$file *f = (viola$io$file *)malloc(sizeof(viola$io$file));
        f->$refCount = 1;
        f->$parent = NULL;
        f->$$vtable = NULL;
        f->fp = fp;
        f->isPopen = 1;
        *req->resultFile = f;
    }
    req->done = 1;
}

static void handleRead(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    size_t nbyte = req->nbyte;
    unsigned char *buffer = (unsigned char *)malloc(nbyte > 0 ? nbyte : 1);
    int readSize = _read(req->fd, buffer, (unsigned int)nbyte);
    if (readSize < 0) {
        readSize = 0;
    }
    *req->resultString = newStringFromBytes(buffer, (size_t)readSize);
    free(buffer);
    req->done = 1;
}

static void handleRemove(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    _wremove(wide);
    free(wide);
    req->done = 1;
}

static void handleRemovedirs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *path = toWide(req->path);
    size_t len = wcslen(path);
    wchar_t *tmp = (wchar_t *)malloc(sizeof(wchar_t) * (len + 1));
    memcpy(tmp, path, sizeof(wchar_t) * (len + 1));
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == L'\\' || tmp[i - 1] == L'/') {
            tmp[i - 1] = L'\0';
            if (_wrmdir(tmp) != 0) {
                break;
            }
        }
    }
    free(tmp);
    free(path);
    req->done = 1;
}

static void handleRename(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *oldPath = toWide(req->path);
    wchar_t *newPath = toWide(req->path2);
    _wrename(oldPath, newPath);
    free(oldPath);
    free(newPath);
    req->done = 1;
}

static void handleRenames(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *oldPath = toWide(req->path);
    wchar_t *newPath = toWide(req->path2);
    /* 确保目标父目录存在（近似Python的os.renames） */
    size_t len = wcslen(newPath);
    wchar_t *tmp = (wchar_t *)malloc(sizeof(wchar_t) * (len + 1));
    memcpy(tmp, newPath, sizeof(wchar_t) * (len + 1));
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == L'\\' || tmp[i - 1] == L'/') {
            tmp[i - 1] = L'\0';
            _wmkdir(tmp);
        }
    }
    _wrename(oldPath, newPath);
    free(tmp);
    free(oldPath);
    free(newPath);
    req->done = 1;
}

static void handleRmdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    _wrmdir(wide);
    free(wide);
    req->done = 1;
}

static void handleStat(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$Stat *s = newStat();
    wchar_t *wide = toWide(req->path);
    struct _stat64 st;
    if (_wstat64(wide, &st) == 0) {
        s->st_mode = (viola$lang$uint32)st.st_mode;
        s->st_ino = (viola$lang$uint64)st.st_ino;
        s->st_dev = (viola$lang$uint64)st.st_dev;
        s->st_nlink = (viola$lang$uint64)st.st_nlink;
        s->st_uid = (viola$lang$uint32)st.st_uid;
        s->st_gid = (viola$lang$uint32)st.st_gid;
        s->st_size = (viola$lang$uint64)st.st_size;
        s->st_atime = (viola$lang$uint64)st.st_atime;
        s->st_mtime = (viola$lang$uint64)st.st_mtime;
        s->st_ctime = (viola$lang$uint64)st.st_ctime;
    }
    free(wide);
    *req->resultStat = s;
    req->done = 1;
}

static void handleStatVfs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$StatVFS *s = newStatVFS();
    wchar_t *wide = toWide(req->path);
    ULARGE_INTEGER freeBytesAvail;
    ULARGE_INTEGER totalBytes;
    ULARGE_INTEGER totalFreeBytes;
    if (GetDiskFreeSpaceExW(wide, &freeBytesAvail, &totalBytes, &totalFreeBytes)) {
        s->f_bsize = 1;
        s->f_frsize = 1;
        s->f_blocks = (viola$lang$uint64)totalBytes.QuadPart;
        s->f_bfree = (viola$lang$uint64)totalFreeBytes.QuadPart;
        s->f_bavail = (viola$lang$uint64)freeBytesAvail.QuadPart;
        s->f_namemax = 260;
    }
    free(wide);
    *req->resultStatVFS = s;
    req->done = 1;
}

static void handleTtyname(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    (void)req;
    *req->resultString = viola$lang$string$fromCharString("");
    req->done = 1;
}

static void handleUtime(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    wchar_t *wide = toWide(req->path);
    struct _utimbuf times;
    times.actime = (time_t)req->atime;
    times.modtime = (time_t)req->mtime;
    _wutime(wide, &times);
    free(wide);
    req->done = 1;
}

static void handleWrite(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *text = viola$lang$string$toCharString(req->data);
    size_t len = strlen(text);
    int written = _write(req->fd, text, (unsigned int)len);
    *req->resultU32 = written > 0 ? (viola$lang$uint32)written : 0;
    free(text);
    req->done = 1;
}

/* Windows上不支持的操作：静默忽略或返回约定值 */
static void handleNoop(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    req->done = 1;
}

static void handleUnsupported(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    if (req->resultInt != NULL) {
        *req->resultInt = -1;
    }
    if (req->resultBool != NULL) {
        *req->resultBool = false;
    }
    if (req->resultString != NULL) {
        *req->resultString = viola$lang$string$fromCharString("");
    }
    if (req->resultStat != NULL) {
        *req->resultStat = newStat();
    }
    if (req->resultStatVFS != NULL) {
        *req->resultStatVFS = newStatVFS();
    }
    req->done = 1;
}

#else /* POSIX */

static void handleAccess(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    *req->resultBool = access(utf8, (int)req->mode) == 0;
    free(utf8);
    req->done = 1;
}

static void handleChdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    chdir(utf8);
    free(utf8);
    req->done = 1;
}

static void handleChflags(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    chflags(utf8, (unsigned int)req->flags);
    free(utf8);
    req->done = 1;
}

static void handleChmod(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    chmod(utf8, (mode_t)req->mode);
    free(utf8);
    req->done = 1;
}

static void handleChown(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    chown(utf8, (uid_t)req->uid, (gid_t)req->gid);
    free(utf8);
    req->done = 1;
}

static void handleChroot(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    chroot(utf8);
    free(utf8);
    req->done = 1;
}

static void handleClose(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    close(req->fd);
    req->done = 1;
}

static void handleCloseRange(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    for (viola$lang$int32 fd = req->fd; fd <= req->fd2; fd++) {
        close(fd);
    }
    req->done = 1;
}

static void handleDup(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = dup(req->fd);
    req->done = 1;
}

static void handleDup2(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = dup2(req->fd, req->fd2);
    req->done = 1;
}

static void handleFchdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    fchdir(req->fd);
    req->done = 1;
}

static void handleFchmod(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    fchmod(req->fd, (mode_t)req->mode);
    req->done = 1;
}

static void handleFchown(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    fchown(req->fd, (uid_t)req->uid, (gid_t)req->gid);
    req->done = 1;
}

static void handleFdatasync(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
#ifdef __linux__
    fdatasync(req->fd);
#else
    fsync(req->fd);
#endif
    req->done = 1;
}

static void handleFdopen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    FILE *fp = fdopen(req->fd, "r");
    if (fp == NULL) {
        *req->resultFile = NULL;
    } else {
        viola$io$file *f = (viola$io$file *)malloc(sizeof(viola$io$file));
        f->$refCount = 1;
        f->$parent = NULL;
        f->$$vtable = NULL;
        f->fp = fp;
        f->isPopen = 0;
        *req->resultFile = f;
    }
    req->done = 1;
}

static void handleFpathconf(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    errno = 0;
    long result = fpathconf(req->fd, req->name);
    *req->resultInt = (errno == 0) ? (viola$lang$int32)result : -1;
    req->done = 1;
}

static void handleFstat(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$Stat *s = newStat();
    struct stat st;
    if (fstat(req->fd, &st) == 0) {
        s->st_mode = (viola$lang$uint32)st.st_mode;
        s->st_ino = (viola$lang$uint64)st.st_ino;
        s->st_dev = (viola$lang$uint64)st.st_dev;
        s->st_nlink = (viola$lang$uint64)st.st_nlink;
        s->st_uid = (viola$lang$uint32)st.st_uid;
        s->st_gid = (viola$lang$uint32)st.st_gid;
        s->st_size = (viola$lang$uint64)st.st_size;
        s->st_atime = (viola$lang$uint64)st.st_atime;
        s->st_mtime = (viola$lang$uint64)st.st_mtime;
        s->st_ctime = (viola$lang$uint64)st.st_ctime;
    }
    *req->resultStat = s;
    req->done = 1;
}

static void handleFtruncate(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    ftruncate(req->fd, (off_t)req->size);
    req->done = 1;
}

static void handleGetCwd(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char buffer[PATH_MAX];
    if (getcwd(buffer, sizeof(buffer)) != NULL) {
        *req->resultString = viola$lang$string$fromCharString(buffer);
    } else {
        *req->resultString = viola$lang$string$fromCharString("");
    }
    req->done = 1;
}

static void handleIsatty(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultBool = isatty(req->fd) != 0;
    req->done = 1;
}

static void handleLchflags(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    lchflags(utf8, (unsigned int)req->flags);
    free(utf8);
    req->done = 1;
}

static void handleLchmod(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
#ifdef __linux__
    fchmodat(AT_FDCWD, utf8, (mode_t)req->mode, AT_SYMLINK_NOFOLLOW);
#else
    lchmod(utf8, (mode_t)req->mode);
#endif
    free(utf8);
    req->done = 1;
}

static void handleLchown(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    lchown(utf8, (uid_t)req->uid, (gid_t)req->gid);
    free(utf8);
    req->done = 1;
}

static void handleLink(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *oldPath = viola$lang$string$toCharString(req->path);
    char *newPath = viola$lang$string$toCharString(req->path2);
    link(oldPath, newPath);
    free(oldPath);
    free(newPath);
    req->done = 1;
}

static void handleListDir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$lang$string$$array *arr = (viola$lang$string$$array *)malloc(
        sizeof(viola$lang$string$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->data = NULL;
    arr->size = 0;
    char *utf8 = viola$lang$string$toCharString(req->path);
    DIR *dir = opendir(utf8);
    free(utf8);
    if (dir != NULL) {
        viola$lang$uint64 capacity = 0;
        viola$lang$uint64 count = 0;
        struct dirent *entry;
        while ((entry = readdir(dir)) != NULL) {
            if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            if (count >= capacity) {
                capacity = capacity == 0 ? 8 : capacity * 2;
                arr->data = (viola$lang$string **)realloc(arr->data,
                                                          sizeof(viola$lang$string *) * capacity);
            }
            arr->data[count++] = viola$lang$string$fromCharString(entry->d_name);
        }
        closedir(dir);
        arr->size = count;
    }
    *req->resultStringArray = arr;
    req->done = 1;
}

static void handleLseek(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = (viola$lang$int32)lseek(req->fd, (off_t)req->offset, req->whence);
    req->done = 1;
}

static void handleLstat(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$Stat *s = newStat();
    char *utf8 = viola$lang$string$toCharString(req->path);
    struct stat st;
    if (lstat(utf8, &st) == 0) {
        s->st_mode = (viola$lang$uint32)st.st_mode;
        s->st_ino = (viola$lang$uint64)st.st_ino;
        s->st_dev = (viola$lang$uint64)st.st_dev;
        s->st_nlink = (viola$lang$uint64)st.st_nlink;
        s->st_uid = (viola$lang$uint32)st.st_uid;
        s->st_gid = (viola$lang$uint32)st.st_gid;
        s->st_size = (viola$lang$uint64)st.st_size;
        s->st_atime = (viola$lang$uint64)st.st_atime;
        s->st_mtime = (viola$lang$uint64)st.st_mtime;
        s->st_ctime = (viola$lang$uint64)st.st_ctime;
    }
    free(utf8);
    *req->resultStat = s;
    req->done = 1;
}

static void handleMakedirs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *path = viola$lang$string$toCharString(req->path);
    size_t len = strlen(path);
    char *tmp = (char *)malloc(len + 1);
    memcpy(tmp, path, len + 1);
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == '/') {
            tmp[i - 1] = '\0';
            mkdir(tmp, (mode_t)req->mode);
        }
    }
    mkdir(tmp, (mode_t)req->mode);
    free(tmp);
    free(path);
    req->done = 1;
}

static void handleMkdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    mkdir(utf8, (mode_t)req->mode);
    free(utf8);
    req->done = 1;
}

static void handleMkfifo(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    mkfifo(utf8, (mode_t)req->mode);
    free(utf8);
    req->done = 1;
}

static void handleMknod(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    mknod(utf8, (mode_t)req->mode, (dev_t)req->dev);
    free(utf8);
    req->done = 1;
}

static void handleOpen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    *req->resultInt = open(utf8, (int)req->flags, (mode_t)req->mode);
    free(utf8);
    req->done = 1;
}

static void handleOpenpty(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    *req->resultInt = -1;
#ifdef __linux__
    int master;
    int slave;
    if (openpty(&master, &slave, NULL, NULL, NULL) == 0) {
        close(slave);
        *req->resultInt = master;
    }
#endif
    req->done = 1;
}

static void handlePathconf(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    errno = 0;
    long result = pathconf(utf8, req->name);
    *req->resultInt = (errno == 0) ? (viola$lang$int32)result : -1;
    free(utf8);
    req->done = 1;
}

static void handlePipe(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    int fds[2];
    if (pipe(fds) == 0) {
        *req->resultInt = fds[0];
    } else {
        *req->resultInt = -1;
    }
    req->done = 1;
}

static void handlePopen(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *command = viola$lang$string$toCharString(req->path);
    char *mode = viola$lang$string$toCharString(req->data);
    FILE *fp = popen(command, mode);
    free(command);
    free(mode);
    if (fp == NULL) {
        *req->resultFile = NULL;
    } else {
        viola$io$file *f = (viola$io$file *)malloc(sizeof(viola$io$file));
        f->$refCount = 1;
        f->$parent = NULL;
        f->$$vtable = NULL;
        f->fp = fp;
        f->isPopen = 1;
        *req->resultFile = f;
    }
    req->done = 1;
}

static void handleRead(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    size_t nbyte = req->nbyte;
    unsigned char *buffer = (unsigned char *)malloc(nbyte > 0 ? nbyte : 1);
    ssize_t readSize = read(req->fd, buffer, nbyte);
    if (readSize < 0) {
        readSize = 0;
    }
    *req->resultString = newStringFromBytes(buffer, (size_t)readSize);
    free(buffer);
    req->done = 1;
}

static void handleReadlink(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    char buffer[PATH_MAX];
    ssize_t len = readlink(utf8, buffer, sizeof(buffer) - 1);
    free(utf8);
    if (len < 0) {
        *req->resultString = viola$lang$string$fromCharString("");
    } else {
        buffer[len] = '\0';
        *req->resultString = viola$lang$string$fromCharString(buffer);
    }
    req->done = 1;
}

static void handleRemove(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    remove(utf8);
    free(utf8);
    req->done = 1;
}

static void handleRemovedirs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *path = viola$lang$string$toCharString(req->path);
    size_t len = strlen(path);
    char *tmp = (char *)malloc(len + 1);
    memcpy(tmp, path, len + 1);
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == '/') {
            tmp[i - 1] = '\0';
            if (rmdir(tmp) != 0) {
                break;
            }
        }
    }
    free(tmp);
    free(path);
    req->done = 1;
}

static void handleRename(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *oldPath = viola$lang$string$toCharString(req->path);
    char *newPath = viola$lang$string$toCharString(req->path2);
    rename(oldPath, newPath);
    free(oldPath);
    free(newPath);
    req->done = 1;
}

static void handleRenames(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *oldPath = viola$lang$string$toCharString(req->path);
    char *newPath = viola$lang$string$toCharString(req->path2);
    /* 确保目标父目录存在（近似Python的os.renames） */
    size_t len = strlen(newPath);
    char *tmp = (char *)malloc(len + 1);
    memcpy(tmp, newPath, len + 1);
    for (size_t i = len; i > 0; i--) {
        if (tmp[i - 1] == '/') {
            tmp[i - 1] = '\0';
            mkdir(tmp, 0777);
        }
    }
    rename(oldPath, newPath);
    free(tmp);
    free(oldPath);
    free(newPath);
    req->done = 1;
}

static void handleRmdir(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    rmdir(utf8);
    free(utf8);
    req->done = 1;
}

static void handleStat(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$Stat *s = newStat();
    char *utf8 = viola$lang$string$toCharString(req->path);
    struct stat st;
    if (stat(utf8, &st) == 0) {
        s->st_mode = (viola$lang$uint32)st.st_mode;
        s->st_ino = (viola$lang$uint64)st.st_ino;
        s->st_dev = (viola$lang$uint64)st.st_dev;
        s->st_nlink = (viola$lang$uint64)st.st_nlink;
        s->st_uid = (viola$lang$uint32)st.st_uid;
        s->st_gid = (viola$lang$uint32)st.st_gid;
        s->st_size = (viola$lang$uint64)st.st_size;
        s->st_atime = (viola$lang$uint64)st.st_atime;
        s->st_mtime = (viola$lang$uint64)st.st_mtime;
        s->st_ctime = (viola$lang$uint64)st.st_ctime;
    }
    free(utf8);
    *req->resultStat = s;
    req->done = 1;
}

static void handleStatVfs(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    viola$os$StatVFS *s = newStatVFS();
    char *utf8 = viola$lang$string$toCharString(req->path);
    struct statvfs st;
    if (statvfs(utf8, &st) == 0) {
        s->f_bsize = (viola$lang$uint64)st.f_bsize;
        s->f_frsize = (viola$lang$uint64)st.f_frsize;
        s->f_blocks = (viola$lang$uint64)st.f_blocks;
        s->f_bfree = (viola$lang$uint64)st.f_bfree;
        s->f_bavail = (viola$lang$uint64)st.f_bavail;
        s->f_files = (viola$lang$uint64)st.f_files;
        s->f_ffree = (viola$lang$uint64)st.f_ffree;
        s->f_favail = (viola$lang$uint64)st.f_favail;
        s->f_flag = (viola$lang$uint64)st.f_flag;
        s->f_namemax = (viola$lang$uint64)st.f_namemax;
    }
    free(utf8);
    *req->resultStatVFS = s;
    req->done = 1;
}

static void handleTcgetpgrp(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    errno = 0;
    pid_t pgid = tcgetpgrp(req->fd);
    *req->resultInt = (errno == 0) ? (viola$lang$int32)pgid : -1;
    req->done = 1;
}

static void handleTcsetpgrp(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    tcsetpgrp(req->fd, (pid_t)req->pgid);
    req->done = 1;
}

static void handleTtyname(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *name = ttyname(req->fd);
    *req->resultString = viola$lang$string$fromCharString(name != NULL ? name : "");
    req->done = 1;
}

static void handleUtime(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *utf8 = viola$lang$string$toCharString(req->path);
    struct utimbuf times;
    times.actime = (time_t)req->atime;
    times.modtime = (time_t)req->mtime;
    utime(utf8, &times);
    free(utf8);
    req->done = 1;
}

static void handleWrite(viola$lang$global_resource_manager$Request *base) {
    viola$os$OsRequest *req = (viola$os$OsRequest *)base;
    char *text = viola$lang$string$toCharString(req->data);
    size_t len = strlen(text);
    ssize_t written = write(req->fd, text, len);
    *req->resultU32 = written > 0 ? (viola$lang$uint32)written : 0;
    free(text);
    req->done = 1;
}

#endif

/* 注册操作系统请求处理器（由全局资源管理器初始化时调用） */
void viola$os$registerOsHandlers(void) {
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_ACCESS, handleAccess);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHDIR, handleChdir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHMOD, handleChmod);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CLOSE, handleClose);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CLOSERANGE, handleCloseRange);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_DUP, handleDup);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_DUP2, handleDup2);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FDATASYNC, handleFdatasync);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FDOPEN, handleFdopen);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FSTAT, handleFstat);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FTRUNCATE, handleFtruncate);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_GETCWD, handleGetCwd);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_ISATTY, handleIsatty);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LINK, handleLink);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LISTDIR, handleListDir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LSEEK, handleLseek);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MAKEDIRS, handleMakedirs);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MKDIR, handleMkdir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_OPEN, handleOpen);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_PIPE, handlePipe);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_POPEN, handlePopen);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_READ, handleRead);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_REMOVE, handleRemove);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_REMOVEDIRS, handleRemovedirs);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_RENAME, handleRename);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_RENAMES, handleRenames);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_RMDIR, handleRmdir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_STAT, handleStat);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_STATVFS, handleStatVfs);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_TTYNAME, handleTtyname);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_UTIME, handleUtime);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_WRITE, handleWrite);
#ifdef _WIN32
    /* Windows上不支持的操作 */
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHFLAGS, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHOWN, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHROOT, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHDIR, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHMOD, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHOWN, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FPATHCONF, handleUnsupported);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHFLAGS, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHMOD, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHOWN, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LSTAT, handleStat);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MKFIFO, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MKNOD, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_OPENPTY, handleUnsupported);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_PATHCONF, handleUnsupported);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_READLINK, handleUnsupported);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_TCGETPGRP, handleUnsupported);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_TCSETPGRP, handleNoop);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_UNLINK, handleRemove);
#else
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHFLAGS, handleChflags);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHOWN, handleChown);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_CHROOT, handleChroot);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHDIR, handleFchdir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHMOD, handleFchmod);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FCHOWN, handleFchown);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_FPATHCONF, handleFpathconf);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHFLAGS, handleLchflags);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHMOD, handleLchmod);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LCHOWN, handleLchown);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_LSTAT, handleLstat);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MKFIFO, handleMkfifo);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_MKNOD, handleMknod);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_OPENPTY, handleOpenpty);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_PATHCONF, handlePathconf);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_READLINK, handleReadlink);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_TCGETPGRP, handleTcgetpgrp);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_TCSETPGRP, handleTcsetpgrp);
    viola$lang$global_resource_manager$registerHandler(VIOLA_OS_REQUEST_UNLINK, handleRemove);
#endif
}

/* ================= 类析构 ================= */

void viola$os$Stat$__del__$_0$_0(viola$os$Stat *_this, viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount == 0) {
        if (_this->$parent) {
            ((viola$lang$uint32 *)_this->$parent)[0]--;
        } else {
            free(_this);
        }
    }
}

void viola$os$StatVFS$__del__$_0$_0(viola$os$StatVFS *_this, viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount == 0) {
        if (_this->$parent) {
            ((viola$lang$uint32 *)_this->$parent)[0]--;
        } else {
            free(_this);
        }
    }
}

/* ================= Viola接口 ================= */

void viola$os$access(viola$lang$string *path, viola$lang$uint32 mode, viola$lang$bool *result,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_ACCESS);
    req->path = path;
    req->mode = mode;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$chdir(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CHDIR);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$chflags(viola$lang$string *path, viola$lang$uint32 flags,
                      viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CHFLAGS);
    req->path = path;
    req->flags = flags;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$chmod(viola$lang$string *path, viola$lang$uint32 mode,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CHMOD);
    req->path = path;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$chown(viola$lang$string *path, viola$lang$uint32 uid, viola$lang$uint32 gid,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CHOWN);
    req->path = path;
    req->uid = uid;
    req->gid = gid;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$chroot(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CHROOT);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$close(viola$lang$int32 fd, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CLOSE);
    req->fd = fd;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$closerange(viola$lang$int32 fd1, viola$lang$int32 fd2,
                         viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_CLOSERANGE);
    req->fd = fd1;
    req->fd2 = fd2;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$dup(viola$lang$int32 fd, viola$lang$int32 *result,
                  viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_DUP);
    req->fd = fd;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$dup2(viola$lang$int32 fd1, viola$lang$int32 fd2, viola$lang$int32 *result,
                   viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_DUP2);
    req->fd = fd1;
    req->fd2 = fd2;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fchdir(viola$lang$int32 fd, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FCHDIR);
    req->fd = fd;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fchmod(viola$lang$int32 fd, viola$lang$uint32 mode,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FCHMOD);
    req->fd = fd;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fchown(viola$lang$int32 fd, viola$lang$uint32 uid, viola$lang$uint32 gid,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FCHOWN);
    req->fd = fd;
    req->uid = uid;
    req->gid = gid;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fdatasync(viola$lang$int32 fd, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FDATASYNC);
    req->fd = fd;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fdopen(viola$lang$int32 fd, viola$io$file **result,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FDOPEN);
    req->fd = fd;
    req->resultFile = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fpathconf(viola$lang$int32 fd, viola$lang$int32 name, viola$lang$int32 *result,
                        viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FPATHCONF);
    req->fd = fd;
    req->name = name;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$fstat(viola$lang$int32 fd, viola$os$Stat **result,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FSTAT);
    req->fd = fd;
    req->resultStat = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$ftruncate(viola$lang$int32 fd, viola$lang$uint32 size,
                        viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_FTRUNCATE);
    req->fd = fd;
    req->size = size;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$getcwd(viola$lang$string **result, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_GETCWD);
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$getcwdb(viola$lang$string **result, viola$threads$Listener *listener) {
    /* Viola中字符串为UTF-16，字节形式与getcwd一致 */
    viola$os$getcwd(result, listener);
}

void viola$os$getgid(viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = 0;
#else
    *result = (viola$lang$uint32)getgid();
#endif
}

void viola$os$getuid(viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = 0;
#else
    *result = (viola$lang$uint32)getuid();
#endif
}

void viola$os$isatty(viola$lang$int32 fd, viola$lang$bool *result,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_ISATTY);
    req->fd = fd;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$lchflags(viola$lang$string *path, viola$lang$uint32 flags,
                       viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LCHFLAGS);
    req->path = path;
    req->flags = flags;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$lchmod(viola$lang$string *path, viola$lang$uint32 mode,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LCHMOD);
    req->path = path;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$lchown(viola$lang$string *path, viola$lang$uint32 uid, viola$lang$uint32 gid,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LCHOWN);
    req->path = path;
    req->uid = uid;
    req->gid = gid;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$link(viola$lang$string *path, viola$lang$string *newPath,
                   viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LINK);
    req->path = path;
    req->path2 = newPath;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$listdir(viola$lang$string *path, viola$lang$string$$array **result,
                      viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LISTDIR);
    req->path = path;
    req->resultStringArray = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$lseek(viola$lang$int32 fd, viola$lang$int32 offset, viola$lang$int32 whence,
                    viola$lang$int32 *result, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LSEEK);
    req->fd = fd;
    req->offset = offset;
    req->whence = whence;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$lstat(viola$lang$string *path, viola$os$Stat **result,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_LSTAT);
    req->path = path;
    req->resultStat = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$major(viola$lang$uint32 dev, viola$lang$uint32 *result,
                    viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = (dev >> 8) & 0xFF;
#else
    *result = (viola$lang$uint32)major((dev_t)dev);
#endif
}

void viola$os$makedev(viola$lang$uint32 major, viola$lang$uint32 minor,
                      viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = ((major & 0xFF) << 8) | (minor & 0xFF);
#else
    *result = (viola$lang$uint32)makedev((unsigned int)major, (unsigned int)minor);
#endif
}

void viola$os$makedirs(viola$lang$string *path, viola$lang$uint32 mode,
                       viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_MAKEDIRS);
    req->path = path;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$minor(viola$lang$uint32 dev, viola$lang$uint32 *result,
                    viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = dev & 0xFF;
#else
    *result = (viola$lang$uint32)minor((dev_t)dev);
#endif
}

void viola$os$mkdir(viola$lang$string *path, viola$lang$uint32 mode,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_MKDIR);
    req->path = path;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$mkfifo(viola$lang$string *path, viola$lang$uint32 mode,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_MKFIFO);
    req->path = path;
    req->mode = mode;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$mknod(viola$lang$string *path, viola$lang$uint32 mode, viola$lang$uint32 dev,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_MKNOD);
    req->path = path;
    req->mode = mode;
    req->dev = dev;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$open(viola$lang$string *path, viola$lang$uint32 flags, viola$lang$uint32 mode,
                   viola$lang$int32 *fd, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_OPEN);
    req->path = path;
    req->flags = flags;
    req->mode = mode;
    req->resultInt = fd;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$openpty(viola$lang$int32 *result, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_OPENPTY);
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$pathconf(viola$lang$string *path, viola$lang$int32 name, viola$lang$int32 *result,
                       viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_PATHCONF);
    req->path = path;
    req->name = name;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$pipe(viola$lang$int32 *result, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_PIPE);
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$popen(viola$lang$string *command, viola$lang$string *mode,
                    viola$io$file **result, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_POPEN);
    req->path = command;
    req->data = mode;
    req->resultFile = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$read(viola$lang$int32 fd, viola$lang$uint32 nbyte, viola$lang$string **result,
                   viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_READ);
    req->fd = fd;
    req->nbyte = nbyte;
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$readlink(viola$lang$string *path, viola$lang$string **result,
                       viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_READLINK);
    req->path = path;
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$remove(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_REMOVE);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$removedirs(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_REMOVEDIRS);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$rename(viola$lang$string *oldPath, viola$lang$string *newPath,
                     viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_RENAME);
    req->path = oldPath;
    req->path2 = newPath;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$renames(viola$lang$string *oldPath, viola$lang$string *newPath,
                      viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_RENAMES);
    req->path = oldPath;
    req->path2 = newPath;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$rmdir(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_RMDIR);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$stat(viola$lang$string *path, viola$os$Stat **result,
                   viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_STAT);
    req->path = path;
    req->resultStat = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$stat_float_times(viola$lang$bool useFloat, viola$threads$Listener *listener) {
    (void)useFloat;
    (void)listener;
    /* Python兼容保留接口：无操作 */
}

void viola$os$statvfs(viola$lang$string *path, viola$os$StatVFS **result,
                      viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_STATVFS);
    req->path = path;
    req->resultStatVFS = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$tcgetpgrp(viola$lang$int32 fd, viola$lang$int32 *result,
                        viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_TCGETPGRP);
    req->fd = fd;
    req->resultInt = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$tcsetpgrp(viola$lang$int32 fd, viola$lang$int32 pgid,
                        viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_TCSETPGRP);
    req->fd = fd;
    req->pgid = pgid;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$ttyname(viola$lang$int32 fd, viola$lang$string **result,
                      viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_TTYNAME);
    req->fd = fd;
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$unlink(viola$lang$string *path, viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_UNLINK);
    req->path = path;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$utime(viola$lang$string *path, viola$lang$uint32 atime, viola$lang$uint32 mtime,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_UTIME);
    req->path = path;
    req->atime = atime;
    req->mtime = mtime;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$write(viola$lang$int32 fd, viola$lang$string *data, viola$lang$uint32 *result,
                    viola$threads$Listener *listener) {
    viola$os$OsRequest *req = newRequest(VIOLA_OS_REQUEST_WRITE);
    req->fd = fd;
    req->data = data;
    req->resultU32 = result;
    submitOrRun(req, listener);
    free(req);
}

/* ================= 进程与其他 ================= */

void viola$os$sleep(viola$lang$uint64 milliseconds, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    Sleep((DWORD)milliseconds);
#else
    usleep((useconds_t)(milliseconds * 1000));
#endif
}

void viola$os$exit(viola$lang$int32 code, viola$threads$Listener *listener) {
    (void)listener;
    exit(code);
}

void viola$os$getEnv(viola$lang$string *name, viola$lang$string **result,
                     viola$threads$Listener *listener) {
    (void)listener;
    char *nameText = viola$lang$string$toCharString(name);
    const char *value = getenv(nameText);
    free(nameText);
    *result = viola$lang$string$fromCharString(value != NULL ? value : "");
}

void viola$os$time(viola$lang$uint64 *result, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    *result = (viola$lang$uint64)GetTickCount64();
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    *result = (viola$lang$uint64)tv.tv_sec * 1000 + (viola$lang$uint64)tv.tv_usec / 1000;
#endif
}

void viola$os$system(viola$lang$string *command, viola$lang$int32 *result,
                     viola$threads$Listener *listener) {
    (void)listener;
    char *cmdText = viola$lang$string$toCharString(command);
    *result = system(cmdText);
    free(cmdText);
}
