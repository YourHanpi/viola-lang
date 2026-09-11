/* -*- coding: utf-8 -*-
 * Viola文件状态运行库：文件类型与权限位的常量及判断函数。
 *
 * 命名空间：viola.stat（C标识符前缀 viola$stat$）。
 * 绑定Windows和POSIX的相关接口，使用条件编译：
 * Windows（MinGW）上权限位映射到_S_IREAD/_S_IWRITE/_S_IEXEC，
 * 组/其他权限位与用户权限位取相同值；S_IFBLK/S_IFLNK/S_IFSOCK
 * 采用POSIX取值但Windows上不会出现相应文件类型。
 * 本模块所有函数均为纯计算，不涉及文件系统访问，无需经过请求机制。
 */
#include "runtime.h"

#include <stdint.h>

#ifdef _WIN32
#include <sys/stat.h>
#else
#include <sys/stat.h>
#endif

/* ================= 常量（Viola全局变量声明，见stat.vla） ================= */

#ifdef _WIN32
/* MinGW的sys/stat.h仅提供_S_*常量；映射为POSIX风格的名称。
   组/其他权限位在Windows上不存在，与用户权限位取相同值。 */
viola$lang$uint32 viola$stat$S_IFDIR = _S_IFDIR;
viola$lang$uint32 viola$stat$S_IFREG = _S_IFREG;
viola$lang$uint32 viola$stat$S_IRUSR = _S_IREAD;
viola$lang$uint32 viola$stat$S_IWUSR = _S_IWRITE;
viola$lang$uint32 viola$stat$S_IXUSR = _S_IEXEC;
viola$lang$uint32 viola$stat$S_IRGRP = _S_IREAD;
viola$lang$uint32 viola$stat$S_IWGRP = _S_IWRITE;
viola$lang$uint32 viola$stat$S_IXGRP = _S_IEXEC;
viola$lang$uint32 viola$stat$S_IROTH = _S_IREAD;
viola$lang$uint32 viola$stat$S_IWOTH = _S_IWRITE;
viola$lang$uint32 viola$stat$S_IXOTH = _S_IEXEC;
#else
viola$lang$uint32 viola$stat$S_IFDIR = S_IFDIR;
viola$lang$uint32 viola$stat$S_IFREG = S_IFREG;
viola$lang$uint32 viola$stat$S_IRUSR = S_IRUSR;
viola$lang$uint32 viola$stat$S_IWUSR = S_IWUSR;
viola$lang$uint32 viola$stat$S_IXUSR = S_IXUSR;
viola$lang$uint32 viola$stat$S_IRGRP = S_IRGRP;
viola$lang$uint32 viola$stat$S_IWGRP = S_IWGRP;
viola$lang$uint32 viola$stat$S_IXGRP = S_IXGRP;
viola$lang$uint32 viola$stat$S_IROTH = S_IROTH;
viola$lang$uint32 viola$stat$S_IWOTH = S_IWOTH;
viola$lang$uint32 viola$stat$S_IXOTH = S_IXOTH;
#endif

/* 文件类型掩码与其余类型位（与Python的stat模块一致；判断函数内部使用） */
#ifdef _WIN32
#define VIOLA_STAT_S_IFMT _S_IFMT
#else
#define VIOLA_STAT_S_IFMT S_IFMT
#endif
#define VIOLA_STAT_S_IFBLK 0x6000
#define VIOLA_STAT_S_IFCHR 0x2000
#define VIOLA_STAT_S_IFIFO 0x1000
#define VIOLA_STAT_S_IFLNK 0xA000
#define VIOLA_STAT_S_IFSOCK 0xC000

/* 文件类型位与掩码（stat.vla中的Viola全局变量声明） */
viola$lang$uint32 viola$stat$S_IFMT = VIOLA_STAT_S_IFMT;
viola$lang$uint32 viola$stat$S_IFBLK = VIOLA_STAT_S_IFBLK;
viola$lang$uint32 viola$stat$S_IFCHR = VIOLA_STAT_S_IFCHR;
viola$lang$uint32 viola$stat$S_IFIFO = VIOLA_STAT_S_IFIFO;
viola$lang$uint32 viola$stat$S_IFLNK = VIOLA_STAT_S_IFLNK;
viola$lang$uint32 viola$stat$S_IFSOCK = VIOLA_STAT_S_IFSOCK;

/* ================= 文件类型判断 ================= */

static viola$lang$bool violaStatIsType(viola$lang$uint32 mode, viola$lang$uint32 typeBits) {
    return (mode & VIOLA_STAT_S_IFMT) == typeBits;
}

void viola$stat$S_ISBLK(viola$lang$uint32 mode, viola$lang$bool *result,
                        viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, VIOLA_STAT_S_IFBLK);
}

void viola$stat$S_ISCHR(viola$lang$uint32 mode, viola$lang$bool *result,
                        viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, VIOLA_STAT_S_IFCHR);
}

void viola$stat$S_ISDIR(viola$lang$uint32 mode, viola$lang$bool *result,
                        viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, viola$stat$S_IFDIR);
}

void viola$stat$S_ISFIFO(viola$lang$uint32 mode, viola$lang$bool *result,
                         viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, VIOLA_STAT_S_IFIFO);
}

void viola$stat$S_ISLNK(viola$lang$uint32 mode, viola$lang$bool *result,
                        viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, VIOLA_STAT_S_IFLNK);
}

void viola$stat$S_ISREG(viola$lang$uint32 mode, viola$lang$bool *result,
                        viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, viola$stat$S_IFREG);
}

void viola$stat$S_ISSOCK(viola$lang$uint32 mode, viola$lang$bool *result,
                         viola$threads$Listener *listener) {
    (void)listener;
    *result = violaStatIsType(mode, VIOLA_STAT_S_IFSOCK);
}

/* ================= filemode ================= */

/* 特殊权限位（仅POSIX有意义；Windows上filemode按0处理） */
#define VIOLA_STAT_S_ISUID 0x800
#define VIOLA_STAT_S_ISGID 0x400
#define VIOLA_STAT_S_ISVTX 0x200

void viola$stat$filemode(viola$lang$uint32 mode, viola$lang$string **result,
                         viola$threads$Listener *listener) {
    (void)listener;
    /* 与Python的stat.filemode一致：类型字符 + 9个权限位（含s/S/t/T特判） */
    char out[11];
    if (violaStatIsType(mode, viola$stat$S_IFDIR)) {
        out[0] = 'd';
    } else if (violaStatIsType(mode, VIOLA_STAT_S_IFCHR)) {
        out[0] = 'c';
    } else if (violaStatIsType(mode, VIOLA_STAT_S_IFBLK)) {
        out[0] = 'b';
    } else if (violaStatIsType(mode, viola$stat$S_IFREG)) {
        out[0] = '-';
    } else if (violaStatIsType(mode, VIOLA_STAT_S_IFIFO)) {
        out[0] = 'p';
    } else if (violaStatIsType(mode, VIOLA_STAT_S_IFLNK)) {
        out[0] = 'l';
    } else if (violaStatIsType(mode, VIOLA_STAT_S_IFSOCK)) {
        out[0] = 's';
    } else {
        out[0] = '?';
    }
    out[1] = (mode & viola$stat$S_IRUSR) ? 'r' : '-';
    out[2] = (mode & viola$stat$S_IWUSR) ? 'w' : '-';
    out[3] = (mode & VIOLA_STAT_S_ISUID) ? ((mode & viola$stat$S_IXUSR) ? 's' : 'S')
                                        : ((mode & viola$stat$S_IXUSR) ? 'x' : '-');
    out[4] = (mode & viola$stat$S_IRGRP) ? 'r' : '-';
    out[5] = (mode & viola$stat$S_IWGRP) ? 'w' : '-';
    out[6] = (mode & VIOLA_STAT_S_ISGID) ? ((mode & viola$stat$S_IXGRP) ? 's' : 'S')
                                        : ((mode & viola$stat$S_IXGRP) ? 'x' : '-');
    out[7] = (mode & viola$stat$S_IROTH) ? 'r' : '-';
    out[8] = (mode & viola$stat$S_IWOTH) ? 'w' : '-';
    out[9] = (mode & VIOLA_STAT_S_ISVTX) ? ((mode & viola$stat$S_IXOTH) ? 't' : 'T')
                                        : ((mode & viola$stat$S_IXOTH) ? 'x' : '-');
    out[10] = '\0';
    *result = viola$lang$string$fromCharString(out);
}
