/* -*- coding: utf-8 -*-
 * Viola路径处理运行库。
 *
 * 命名空间：viola.os.path（C标识符前缀 viola$os$path$）。
 * Windows使用反斜杠语义（同时接受正斜杠），POSIX使用正斜杠语义，
 * 通过条件编译处理。路径算法直接作用于UTF-16单元，两种平台共用。
 * 涉及文件系统查询的函数（exists、isdir、getsize、realpath、
 * samefile等）由子线程发送请求、主线程串行执行（模型同viola/io/file.c）。
 */
#include "../lang/global_resource_manager.h"
#include "../lang/string.h"
#include "../threads.h"

#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <wchar.h>
#else
#include <unistd.h>
#include <limits.h>
#include <sched.h>
#endif

/* ================= 基本工具 ================= */

static viola$lang$uint16 pathSepChar(void) {
#ifdef _WIN32
    return (viola$lang$uint16)'\\';
#else
    return (viola$lang$uint16)'/';
#endif
}

/* 是否为路径分隔符（Windows上正斜杠与反斜杠均视为分隔符） */
static viola$lang$bool isSep(viola$lang$uint16 c) {
#ifdef _WIN32
    return c == (viola$lang$uint16)'/' || c == (viola$lang$uint16)'\\';
#else
    return c == (viola$lang$uint16)'/';
#endif
}

static viola$lang$bool isAlphaUnit(viola$lang$uint16 c) {
    return (c >= (viola$lang$uint16)'a' && c <= (viola$lang$uint16)'z') ||
           (c >= (viola$lang$uint16)'A' && c <= (viola$lang$uint16)'Z');
}

/* 前导分隔符个数 */
static viola$lang$uint64 leadingSepCount(const viola$lang$string *s) {
    viola$lang$uint64 i = 0;
    while (i < s->length && isSep(s->data[i])) {
        i++;
    }
    return i;
}

/* 驱动器前缀长度（仅Windows）："C:"记2，"C:/"、"C:\\"记3；POSIX返回0。 */
static viola$lang$uint64 driveLength(const viola$lang$string *s) {
#ifndef _WIN32
    (void)s;
    return 0;
#else
    if (s->length >= 2 && isAlphaUnit(s->data[0]) && s->data[1] == (viola$lang$uint16)':') {
        if (s->length >= 3 && isSep(s->data[2])) {
            return 3;
        }
        return 2;
    }
    return 0;
#endif
}

/* 由UTF-16单元构造新字符串（不带结尾NUL），新对象引用计数为1 */
static viola$lang$string *newStringFromUnits(const viola$lang$uint16 *data, viola$lang$uint64 length) {
    viola$lang$string *s = (viola$lang$string *)malloc(sizeof(viola$lang$string));
    s->$refCount = 1;
    s->$parent = NULL;
    s->length = length;
    if (length > 0) {
        s->data = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * length);
        memcpy(s->data, data, sizeof(viola$lang$uint16) * length);
    } else {
        s->data = NULL;
    }
    return s;
}

/* 连接两个字符串（结果为新对象），直接调用string.__add__实现 */
static viola$lang$string *concatStrings(viola$lang$string *a, viola$lang$string *b,
                                        viola$threads$Listener *listener) {
    viola$lang$string *result = NULL;
    viola$lang$string$__add__$_0(a, b, &result, listener);
    return result;
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

/* 宽字符串转Viola字符串 */
static viola$lang$string *fromWide(const wchar_t *w) {
    size_t len = wcslen(w);
    viola$lang$uint16 *units = (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * len);
    for (size_t i = 0; i < len; i++) {
        units[i] = (viola$lang$uint16)w[i];
    }
    viola$lang$string *s = newStringFromUnits(units, (viola$lang$uint64)len);
    free(units);
    return s;
}
#endif

/* 去除末尾分隔符后的长度（保留根路径："/"、"C:\\"、"C:"不受影响） */
static viola$lang$uint64 trimTrailingSepLength(const viola$lang$string *s) {
    viola$lang$uint64 end = s->length;
    viola$lang$uint64 drive = driveLength(s);
    while (end > drive && isSep(s->data[end - 1])) {
        end--;
    }
    if (end == 0 && s->length > 0 && isSep(s->data[0])) {
        /* 根路径"/"保持原样 */
        end = 1;
    }
    return end;
}

/* ================= 纯字符串路径操作 ================= */

void viola$os$path$isabs(viola$lang$string *path, viola$lang$bool *result,
                         viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    /* 驱动器前缀或前导分隔符均视为绝对路径（与ntpath一致） */
    *result = driveLength(path) >= 2 ||
              (path->length >= 1 && isSep(path->data[0]));
#else
    *result = path->length >= 1 && isSep(path->data[0]);
#endif
}

void viola$os$path$dirname(viola$lang$string *path, viola$lang$string **result,
                           viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$uint64 end = trimTrailingSepLength(path);
    viola$lang$uint64 drive = driveLength(path);
    if (end <= drive) {
        /* "C:"、"C:\\"或空路径：目录部分为路径自身 */
        *result = newStringFromUnits(path->data, end);
        return;
    }
    int64_t k = -1;
    for (int64_t i = (int64_t)end - 1; i >= 0; i--) {
        if (isSep(path->data[i])) {
            k = i;
            break;
        }
    }
    if (k < 0) {
        /* 无分隔符（如"foo"）：目录部分为空 */
        *result = newStringFromUnits(NULL, 0);
        return;
    }
    if (k == 0) {
        /* 根路径（如"/a"）：目录部分为单个分隔符 */
        viola$lang$uint16 sep = pathSepChar();
        *result = newStringFromUnits(&sep, 1);
        return;
    }
    if ((viola$lang$uint64)k < drive) {
        /* 分隔符位于驱动器前缀内（如"C:\\a"）：目录部分为驱动器前缀 */
        *result = newStringFromUnits(path->data, drive);
        return;
    }
    *result = newStringFromUnits(path->data, (viola$lang$uint64)k);
}

void viola$os$path$basename(viola$lang$string *path, viola$lang$string **result,
                            viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$uint64 end = trimTrailingSepLength(path);
    viola$lang$uint64 drive = driveLength(path);
    if (end <= drive) {
        /* "C:"、"C:\\"：无文件名部分；"foo"：整体为文件名 */
        if (end > drive) {
            *result = newStringFromUnits(path->data, end);
        } else {
            *result = newStringFromUnits(NULL, 0);
        }
        return;
    }
    int64_t k = -1;
    for (int64_t i = (int64_t)end - 1; i >= 0; i--) {
        if (isSep(path->data[i])) {
            k = i;
            break;
        }
    }
    if (k < 0) {
        *result = newStringFromUnits(path->data, end);
        return;
    }
    *result = newStringFromUnits(path->data + k + 1, end - (viola$lang$uint64)(k + 1));
}

void viola$os$path$split(viola$lang$string *path, viola$lang$string$$array **result,
                         viola$threads$Listener *listener) {
    viola$lang$string *head = NULL;
    viola$lang$string *tail = NULL;
    viola$os$path$dirname(path, &head, listener);
    viola$os$path$basename(path, &tail, listener);
    viola$lang$string$$array *arr = (viola$lang$string$$array *)malloc(
        sizeof(viola$lang$string$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->size = 2;
    arr->data = (viola$lang$string **)malloc(sizeof(viola$lang$string *) * 2);
    arr->data[0] = head;
    arr->data[1] = tail;
    *result = arr;
}

void viola$os$path$splitext(viola$lang$string *path, viola$lang$string$$array **result,
                            viola$threads$Listener *listener) {
    (void)listener;
    /* 在最后一个分隔符之后查找最后一个'.'；'.'位于开头时不拆分 */
    viola$lang$uint64 lastSep = 0;
    for (viola$lang$uint64 i = 0; i < path->length; i++) {
        if (isSep(path->data[i])) {
            lastSep = i + 1;
        }
    }
    viola$lang$uint64 lastDot = path->length;
    for (viola$lang$uint64 i = path->length; i > lastSep; i--) {
        if (path->data[i - 1] == (viola$lang$uint16)'.') {
            lastDot = i - 1;
            break;
        }
    }
    viola$lang$string$$array *arr = (viola$lang$string$$array *)malloc(
        sizeof(viola$lang$string$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->size = 2;
    arr->data = (viola$lang$string **)malloc(sizeof(viola$lang$string *) * 2);
    if (lastDot < path->length && lastDot > 0) {
        arr->data[0] = newStringFromUnits(path->data, lastDot);
        arr->data[1] = newStringFromUnits(path->data + lastDot, path->length - lastDot);
    } else {
        arr->data[0] = newStringFromUnits(path->data, path->length);
        arr->data[1] = newStringFromUnits(NULL, 0);
    }
    *result = arr;
}

void viola$os$path$join(viola$lang$string$$array *paths, viola$lang$string **result,
                        viola$threads$Listener *listener) {
    viola$lang$string *joined = newStringFromUnits(NULL, 0);
    for (viola$lang$uint64 i = 0; i < paths->size; i++) {
        viola$lang$string *p = paths->data[i];
        if (p == NULL || p->length == 0) {
            continue;
        }
        if (joined->length == 0) {
            viola$lang$string *old = joined;
            joined = newStringFromUnits(p->data, p->length);
            viola$lang$string$__del__$_0(old, listener);
            continue;
        }
        viola$lang$bool abs = false;
        viola$os$path$isabs(p, &abs, listener);
        if (abs) {
            /* 绝对路径重置结果 */
            viola$lang$string *old = joined;
            joined = newStringFromUnits(p->data, p->length);
            viola$lang$string$__del__$_0(old, listener);
            continue;
        }
        viola$lang$uint64 trimEnd = trimTrailingSepLength(joined);
        viola$lang$string *head = newStringFromUnits(joined->data, trimEnd);
        viola$lang$uint16 sep = pathSepChar();
        viola$lang$string *sepStr = newStringFromUnits(&sep, 1);
        viola$lang$string *withSep = concatStrings(head, sepStr, listener);
        viola$lang$string *newJoined = concatStrings(withSep, p, listener);
        viola$lang$string$__del__$_0(head, listener);
        viola$lang$string$__del__$_0(sepStr, listener);
        viola$lang$string$__del__$_0(withSep, listener);
        viola$lang$string$__del__$_0(joined, listener);
        joined = newJoined;
    }
    *result = joined;
}

/* normpath的通用实现（组件级解析".."与"."）。
   输入中分隔符已统一为平台分隔符；驱动器前缀或前导分隔符作为根前缀保留。 */
static viola$lang$string *normPathInternal(const viola$lang$string *path,
                                           viola$threads$Listener *listener) {
    viola$lang$uint64 drive = driveLength(path);
    viola$lang$uint64 start;
    viola$lang$uint64 prefixLen;
    viola$lang$bool rooted;
    if (drive > 0) {
        prefixLen = drive;
        start = drive;
        rooted = true;
    } else {
        viola$lang$uint64 leading = leadingSepCount(path);
        if (leading > 0) {
            /* UNC前缀（两个及以上分隔符）保留两个，其余保留一个 */
            prefixLen = leading >= 2 ? 2 : 1;
            start = leading;
            rooted = true;
        } else {
            prefixLen = 0;
            start = 0;
            rooted = false;
        }
    }
    /* 收集组件 */
    viola$lang$string **components = (viola$lang$string **)malloc(
        sizeof(viola$lang$string *) * (path->length + 1));
    viola$lang$uint64 compCount = 0;
    while (start < path->length) {
        viola$lang$uint64 compEnd = start;
        while (compEnd < path->length && !isSep(path->data[compEnd])) {
            compEnd++;
        }
        components[compCount++] = newStringFromUnits(path->data + start, compEnd - start);
        while (compEnd < path->length && isSep(path->data[compEnd])) {
            compEnd++;
        }
        start = compEnd;
    }
    /* 解析"."与".." */
    viola$lang$uint64 outCount = 0;
    for (viola$lang$uint64 i = 0; i < compCount; i++) {
        viola$lang$string *c = components[i];
        viola$lang$bool isDot = c->length == 1 && c->data[0] == (viola$lang$uint16)'.';
        viola$lang$bool isDotDot = c->length == 2 && c->data[0] == (viola$lang$uint16)'.' &&
                                   c->data[1] == (viola$lang$uint16)'.';
        if (isDot) {
            viola$lang$string$__del__$_0(c, listener);
            components[i] = NULL;
            continue;
        }
        if (isDotDot) {
            viola$lang$string$__del__$_0(c, listener);
            components[i] = NULL;
            if (outCount > 0) {
                viola$lang$string$__del__$_0(components[outCount - 1], listener);
                outCount--;
            } else if (!rooted) {
                /* 相对路径中开头的".."保留 */
                viola$lang$uint16 units[2] = {(viola$lang$uint16)'.', (viola$lang$uint16)'.'};
                components[outCount++] = newStringFromUnits(units, 2);
            }
            continue;
        }
        components[outCount++] = c;
    }
    /* 组装 */
    viola$lang$string *resultStr = newStringFromUnits(path->data, prefixLen);
    for (viola$lang$uint64 i = 0; i < outCount; i++) {
        if (resultStr->length > 0 && resultStr->data[resultStr->length - 1] != pathSepChar()) {
            viola$lang$uint16 sep = pathSepChar();
            viola$lang$string *sepStr = newStringFromUnits(&sep, 1);
            viola$lang$string *withSep = concatStrings(resultStr, sepStr, listener);
            viola$lang$string$__del__$_0(resultStr, listener);
            viola$lang$string$__del__$_0(sepStr, listener);
            resultStr = withSep;
        }
        viola$lang$string *newResult = concatStrings(resultStr, components[i], listener);
        viola$lang$string$__del__$_0(resultStr, listener);
        viola$lang$string$__del__$_0(components[i], listener);
        resultStr = newResult;
    }
    if (resultStr->length == 0) {
        viola$lang$uint16 dot = (viola$lang$uint16)'.';
        viola$lang$string *old = resultStr;
        resultStr = newStringFromUnits(&dot, 1);
        viola$lang$string$__del__$_0(old, listener);
    }
    free(components);
    return resultStr;
}

void viola$os$path$normpath(viola$lang$string *path, viola$lang$string **result,
                            viola$threads$Listener *listener) {
#ifdef _WIN32
    /* Windows：先把'/'统一为'\\'，再按组件解析 */
    viola$lang$uint16 *units = (viola$lang$uint16 *)malloc(
        sizeof(viola$lang$uint16) * (path->length + 1));
    for (viola$lang$uint64 i = 0; i < path->length; i++) {
        units[i] = (path->data[i] == (viola$lang$uint16)'/') ? (viola$lang$uint16)'\\'
                                                             : path->data[i];
    }
    viola$lang$string *normalized = newStringFromUnits(units, path->length);
    free(units);
    viola$lang$string *resolved = normPathInternal(normalized, listener);
    viola$lang$string$__del__$_0(normalized, listener);
    *result = resolved;
#else
    *result = normPathInternal(path, listener);
#endif
}

void viola$os$path$commonprefix(viola$lang$string$$array *paths, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    if (paths->size == 0) {
        *result = newStringFromUnits(NULL, 0);
        return;
    }
    viola$lang$string *first = paths->data[0];
    viola$lang$uint64 common = first->length;
    for (viola$lang$uint64 i = 1; i < paths->size; i++) {
        viola$lang$string *p = paths->data[i];
        viola$lang$uint64 j = 0;
        while (j < common && j < p->length && first->data[j] == p->data[j]) {
            j++;
        }
        common = j;
    }
    *result = newStringFromUnits(first->data, common);
}

/* 比较两个组件（Windows不区分大小写） */
static viola$lang$bool componentEquals(const viola$lang$string *a, const viola$lang$string *b) {
    if (a->length != b->length) {
        return false;
    }
    for (viola$lang$uint64 i = 0; i < a->length; i++) {
        viola$lang$uint16 ca = a->data[i];
        viola$lang$uint16 cb = b->data[i];
#ifdef _WIN32
        if (ca >= (viola$lang$uint16)'A' && ca <= (viola$lang$uint16)'Z') {
            ca = (viola$lang$uint16)(ca + ('a' - 'A'));
        }
        if (cb >= (viola$lang$uint16)'A' && cb <= (viola$lang$uint16)'Z') {
            cb = (viola$lang$uint16)(cb + ('a' - 'A'));
        }
#endif
        if (ca != cb) {
            return false;
        }
    }
    return true;
}

void viola$os$path$commonpath(viola$lang$string$$array *paths, viola$lang$string **result,
                              viola$threads$Listener *listener) {
    /* 组件级最长公共目录前缀：公共组件数至少为2（否则返回空串，与Python一致） */
    if (paths->size == 0) {
        *result = newStringFromUnits(NULL, 0);
        return;
    }
    viola$lang$string *first = paths->data[0];
    viola$lang$uint64 drive = driveLength(first);
    for (viola$lang$uint64 i = 1; i < paths->size; i++) {
        if (driveLength(paths->data[i]) != drive) {
            *result = newStringFromUnits(NULL, 0);
            return;
        }
        for (viola$lang$uint64 j = 0; j < drive; j++) {
            if (first->data[j] != paths->data[i]->data[j]) {
                /* 驱动器前缀不同（Windows） */
                *result = newStringFromUnits(NULL, 0);
                return;
            }
        }
    }
    /* 计算每个路径的组件数 */
    viola$lang$uint64 commonComponents = (viola$lang$uint64)-1;
    for (viola$lang$uint64 i = 0; i < paths->size; i++) {
        viola$lang$string *p = paths->data[i];
        viola$lang$uint64 count = 0;
        viola$lang$uint64 start = drive;
        while (start < p->length) {
            while (start < p->length && isSep(p->data[start])) {
                start++;
            }
            if (start >= p->length) {
                break;
            }
            viola$lang$uint64 end = start;
            while (end < p->length && !isSep(p->data[end])) {
                end++;
            }
            count++;
            start = end;
        }
        if (count < commonComponents) {
            commonComponents = count;
        }
        if (commonComponents == 0) {
            *result = newStringFromUnits(NULL, 0);
            return;
        }
    }
    /* 逐组件比较 */
    viola$lang$uint64 matched = 0;
    for (viola$lang$uint64 k = 0; k < commonComponents; k++) {
        viola$lang$string *ref = NULL;
        viola$lang$bool allMatch = true;
        for (viola$lang$uint64 i = 0; i < paths->size; i++) {
            viola$lang$string *p = paths->data[i];
            viola$lang$uint64 start = drive;
            viola$lang$uint64 idx = 0;
            while (start < p->length) {
                while (start < p->length && isSep(p->data[start])) {
                    start++;
                }
                if (start >= p->length) {
                    break;
                }
                viola$lang$uint64 end = start;
                while (end < p->length && !isSep(p->data[end])) {
                    end++;
                }
                if (idx == k) {
                    viola$lang$string *comp = newStringFromUnits(p->data + start, end - start);
                    if (ref == NULL) {
                        ref = comp;
                    } else {
                        viola$lang$bool eq = componentEquals(ref, comp);
                        viola$lang$string$__del__$_0(comp, listener);
                        if (!eq) {
                            allMatch = false;
                        }
                    }
                    break;
                }
                idx++;
                start = end;
            }
            if (!allMatch) {
                break;
            }
        }
        if (allMatch) {
            if (ref != NULL) {
                viola$lang$string$__del__$_0(ref, listener);
            }
            matched++;
        } else {
            if (ref != NULL) {
                viola$lang$string$__del__$_0(ref, listener);
            }
            break;
        }
    }
    if (matched < 2) {
        *result = newStringFromUnits(NULL, 0);
        return;
    }
    /* 组装公共前缀 */
    viola$lang$uint16 sep = pathSepChar();
    viola$lang$string *resultStr = newStringFromUnits(first->data, drive);
    viola$lang$string *p = paths->data[0];
    viola$lang$uint64 start = drive;
    for (viola$lang$uint64 k = 0; k < matched; k++) {
        while (start < p->length && isSep(p->data[start])) {
            start++;
        }
        viola$lang$uint64 end = start;
        while (end < p->length && !isSep(p->data[end])) {
            end++;
        }
        if (resultStr->length > 0) {
            viola$lang$string *sepStr = newStringFromUnits(&sep, 1);
            viola$lang$string *withSep = concatStrings(resultStr, sepStr, listener);
            viola$lang$string$__del__$_0(resultStr, listener);
            viola$lang$string$__del__$_0(sepStr, listener);
            resultStr = withSep;
        }
        viola$lang$string *comp = newStringFromUnits(p->data + start, end - start);
        viola$lang$string *newResult = concatStrings(resultStr, comp, listener);
        viola$lang$string$__del__$_0(resultStr, listener);
        viola$lang$string$__del__$_0(comp, listener);
        resultStr = newResult;
        start = end;
    }
    *result = resultStr;
}

void viola$os$path$abspath(viola$lang$string *path, viola$lang$string **result,
                           viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    wchar_t *wide = toWide(path);
    wchar_t buffer[MAX_PATH * 4];
    DWORD len = GetFullPathNameW(wide, MAX_PATH * 4, buffer, NULL);
    free(wide);
    if (len == 0 || len >= MAX_PATH * 4) {
        *result = newStringFromUnits(path->data, path->length);
        return;
    }
    *result = fromWide(buffer);
#else
    viola$lang$bool abs = false;
    viola$os$path$isabs(path, &abs, listener);
    if (abs) {
        *result = normPathInternal(path, listener);
        return;
    }
    char cwd[PATH_MAX];
    if (getcwd(cwd, sizeof(cwd)) == NULL) {
        *result = newStringFromUnits(path->data, path->length);
        return;
    }
    viola$lang$string *cwdStr = viola$lang$string$fromCharString(cwd);
    viola$lang$uint16 sep = pathSepChar();
    viola$lang$string *sepStr = newStringFromUnits(&sep, 1);
    viola$lang$string *withSep = concatStrings(cwdStr, sepStr, listener);
    viola$lang$string *joined = concatStrings(withSep, path, listener);
    viola$lang$string$__del__$_0(cwdStr, listener);
    viola$lang$string$__del__$_0(sepStr, listener);
    viola$lang$string$__del__$_0(withSep, listener);
    viola$lang$string *normalized = normPathInternal(joined, listener);
    viola$lang$string$__del__$_0(joined, listener);
    *result = normalized;
#endif
}

/* ================= 请求机制（文件系统查询） ================= */

/* 请求类型编码：与viola/io/file.c（1~6）和viola/os.c（101起）的
   请求类型不重叠（请求向量表按类型索引，重叠会互相覆盖处理器） */
enum {
    VIOLA_PATH_REQUEST_EXISTS = 201,
    VIOLA_PATH_REQUEST_GETATIME,
    VIOLA_PATH_REQUEST_GETCTIME,
    VIOLA_PATH_REQUEST_GETMTIME,
    VIOLA_PATH_REQUEST_GETSIZE,
    VIOLA_PATH_REQUEST_ISDIR,
    VIOLA_PATH_REQUEST_ISFILE,
    VIOLA_PATH_REQUEST_ISLINK,
    VIOLA_PATH_REQUEST_ISMOUNT,
    VIOLA_PATH_REQUEST_REALPATH,
    VIOLA_PATH_REQUEST_SAMEFILE,
    VIOLA_PATH_REQUEST_SAMEOPENFILE
};

typedef struct viola$os$path$PathRequest {
    viola$lang$global_resource_manager$Request base;
    viola$lang$string *path;
    viola$lang$string *path2;
    viola$lang$int32 fd1;
    viola$lang$int32 fd2;
    viola$lang$bool *resultBool;
    viola$lang$uint64 *resultU64;
    viola$lang$string **resultString;
    volatile uint8_t done;
} viola$os$path$PathRequest;

static void yieldCPU(void) {
#ifdef _WIN32
    Sleep(0);
#else
    sched_yield();
#endif
}

/* 子线程提交请求并等待主线程执行（主线程直接执行） */
static void submitOrRun(viola$os$path$PathRequest *request, viola$threads$Listener *listener) {
    /* 按当前线程判断是否为主线程：执行本任务的线程可能已改写
       listener->currentThreadId（见开发疑问记录113） */
    if (listener != NULL && viola$threads$isMainThread()) {
        viola$lang$global_resource_manager$handleRequest(&request->base);
        return;
    }
    request->done = 0;
    viola$lang$global_resource_manager$enqueueRequest(&request->base);
    while (!request->done) {
        yieldCPU();
    }
}

/* 获取路径的stat信息。返回0表示成功。 */
#ifdef _WIN32
static int pathStat(const viola$lang$string *path, struct _stat64 *st, viola$lang$bool followLink) {
    (void)followLink; /* Windows的_stat64不区分link（重解析点按目标解析） */
    wchar_t *wide = toWide(path);
    int rc = _wstat64(wide, st);
    free(wide);
    return rc;
}
#else
static int pathStat(const viola$lang$string *path, struct stat *st, viola$lang$bool followLink) {
    char *utf8 = viola$lang$string$toCharString(path);
    int rc = followLink ? stat(utf8, st) : lstat(utf8, st);
    free(utf8);
    return rc;
}
#endif

static void handleExists(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    wchar_t *wide = toWide(req->path);
    *req->resultBool = _waccess(wide, 0) == 0;
    free(wide);
#else
    char *utf8 = viola$lang$string$toCharString(req->path);
    *req->resultBool = access(utf8, F_OK) == 0;
    free(utf8);
#endif
    req->done = 1;
}

static void handleGetAtime(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_atime : 0;
#else
    struct stat st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_atime : 0;
#endif
    req->done = 1;
}

static void handleGetCtime(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_ctime : 0;
#else
    struct stat st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_ctime : 0;
#endif
    req->done = 1;
}

static void handleGetMtime(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_mtime : 0;
#else
    struct stat st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_mtime : 0;
#endif
    req->done = 1;
}

static void handleGetSize(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_size : 0;
#else
    struct stat st;
    *req->resultU64 = pathStat(req->path, &st, true) == 0 ? (viola$lang$uint64)st.st_size : 0;
#endif
    req->done = 1;
}

static void handleIsDir(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultBool = pathStat(req->path, &st, true) == 0 && (st.st_mode & _S_IFMT) == _S_IFDIR;
#else
    struct stat st;
    *req->resultBool = pathStat(req->path, &st, true) == 0 && S_ISDIR(st.st_mode);
#endif
    req->done = 1;
}

static void handleIsFile(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st;
    *req->resultBool = pathStat(req->path, &st, true) == 0 && (st.st_mode & _S_IFMT) == _S_IFREG;
#else
    struct stat st;
    *req->resultBool = pathStat(req->path, &st, true) == 0 && S_ISREG(st.st_mode);
#endif
    req->done = 1;
}

static void handleIsLink(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    /* Windows：检查重解析点属性（符号链接与junction均视为链接） */
    wchar_t *wide = toWide(req->path);
    DWORD attrs = GetFileAttributesW(wide);
    free(wide);
    *req->resultBool = attrs != INVALID_FILE_ATTRIBUTES &&
                       (attrs & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
#else
    struct stat st;
    *req->resultBool = pathStat(req->path, &st, false) == 0 && S_ISLNK(st.st_mode);
#endif
    req->done = 1;
}

static void handleIsMount(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    /* Windows：驱动器根（"C:"、"C:\\"、"C:/"）或UNC根（\\server\share） */
    viola$lang$string *p = req->path;
    if (p->length == 2 && isAlphaUnit(p->data[0]) && p->data[1] == (viola$lang$uint16)':') {
        *req->resultBool = true;
    } else if (p->length == 3 && isAlphaUnit(p->data[0]) && p->data[1] == (viola$lang$uint16)':' &&
               isSep(p->data[2])) {
        *req->resultBool = true;
    } else if (p->length >= 5 && isSep(p->data[0]) && isSep(p->data[1])) {
        /* UNC根：分隔符之后最多一个分隔符（即\\server\share或\\server\share\形式） */
        viola$lang$uint64 sepCount = 0;
        for (viola$lang$uint64 i = 2; i < p->length; i++) {
            if (isSep(p->data[i])) {
                sepCount++;
            }
        }
        *req->resultBool = sepCount <= 1;
    } else {
        *req->resultBool = false;
    }
#else
    /* POSIX：路径与父目录的st_dev不同 */
    struct stat stPath;
    if (pathStat(req->path, &stPath, true) != 0) {
        *req->resultBool = false;
    } else {
        viola$lang$string *parent = NULL;
        viola$os$path$dirname(req->path, &parent, NULL);
        viola$lang$bool diff = false;
        if (parent->length == 0) {
            diff = false;
        } else {
            struct stat stParent;
            if (pathStat(parent, &stParent, true) != 0) {
                diff = false;
            } else {
                diff = stPath.st_dev != stParent.st_dev;
            }
        }
        viola$lang$string$__del__$_0(parent, NULL);
        *req->resultBool = diff;
    }
#endif
    req->done = 1;
}

static void handleRealPath(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    wchar_t *wide = toWide(req->path);
    wchar_t buffer[MAX_PATH * 4];
    DWORD len = GetFullPathNameW(wide, MAX_PATH * 4, buffer, NULL);
    free(wide);
    *req->resultString = len > 0 && len < MAX_PATH * 4 ? fromWide(buffer)
                                                       : newStringFromUnits(req->path->data, req->path->length);
#else
    char *utf8 = viola$lang$string$toCharString(req->path);
    char resolved[PATH_MAX];
    if (realpath(utf8, resolved) != NULL) {
        *req->resultString = viola$lang$string$fromCharString(resolved);
    } else {
        /* 解析失败时回退到规范化路径 */
        viola$lang$string *normalized = normPathInternal(req->path, NULL);
        *req->resultString = normalized;
    }
    free(utf8);
#endif
    req->done = 1;
}

static void handleSameFile(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st1;
    struct _stat64 st2;
    *req->resultBool = pathStat(req->path, &st1, true) == 0 &&
                       pathStat(req->path2, &st2, true) == 0 &&
                       st1.st_dev == st2.st_dev && st1.st_ino == st2.st_ino;
#else
    struct stat st1;
    struct stat st2;
    *req->resultBool = pathStat(req->path, &st1, true) == 0 &&
                       pathStat(req->path2, &st2, true) == 0 &&
                       st1.st_dev == st2.st_dev && st1.st_ino == st2.st_ino;
#endif
    req->done = 1;
}

static void handleSameOpenFile(viola$lang$global_resource_manager$Request *base) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)base;
#ifdef _WIN32
    struct _stat64 st1;
    struct _stat64 st2;
    *req->resultBool = _fstat64(req->fd1, &st1) == 0 && _fstat64(req->fd2, &st2) == 0 &&
                       st1.st_dev == st2.st_dev && st1.st_ino == st2.st_ino;
#else
    struct stat st1;
    struct stat st2;
    *req->resultBool = fstat(req->fd1, &st1) == 0 && fstat(req->fd2, &st2) == 0 &&
                       st1.st_dev == st2.st_dev && st1.st_ino == st2.st_ino;
#endif
    req->done = 1;
}

/* 注册路径请求处理器（由全局资源管理器初始化时调用） */
void viola$os$path$registerPathHandlers(void) {
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_EXISTS, handleExists);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_GETATIME, handleGetAtime);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_GETCTIME, handleGetCtime);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_GETMTIME, handleGetMtime);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_GETSIZE, handleGetSize);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_ISDIR, handleIsDir);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_ISFILE, handleIsFile);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_ISLINK, handleIsLink);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_ISMOUNT, handleIsMount);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_REALPATH, handleRealPath);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_SAMEFILE, handleSameFile);
    viola$lang$global_resource_manager$registerHandler(VIOLA_PATH_REQUEST_SAMEOPENFILE, handleSameOpenFile);
}

/* ================= Viola接口 ================= */

/* 路径分隔符全局变量（path.vla中的`string pathsep;`声明；
   引用计数为1使清理代码不会释放该静态对象） */
static viola$lang$string s_pathSepString = {
    1, NULL,
#ifdef _WIN32
    1, (viola$lang$uint16 *)&(viola$lang$uint16[]){ ';' }
#else
    1, (viola$lang$uint16 *)&(viola$lang$uint16[]){ ':' }
#endif
};
viola$lang$string *viola$os$path$pathsep = &s_pathSepString;

void viola$os$path$exists(viola$lang$string *path, viola$lang$bool *result,
                          viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_EXISTS;
    req->path = path;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$getatime(viola$lang$string *path, viola$lang$uint64 *result,
                            viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_GETATIME;
    req->path = path;
    req->resultU64 = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$getctime(viola$lang$string *path, viola$lang$uint64 *result,
                            viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_GETCTIME;
    req->path = path;
    req->resultU64 = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$getmtime(viola$lang$string *path, viola$lang$uint64 *result,
                            viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_GETMTIME;
    req->path = path;
    req->resultU64 = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$getsize(viola$lang$string *path, viola$lang$uint64 *result,
                           viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_GETSIZE;
    req->path = path;
    req->resultU64 = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$isdir(viola$lang$string *path, viola$lang$bool *result,
                         viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_ISDIR;
    req->path = path;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$isfile(viola$lang$string *path, viola$lang$bool *result,
                          viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_ISFILE;
    req->path = path;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$islink(viola$lang$string *path, viola$lang$bool *result,
                          viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_ISLINK;
    req->path = path;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$ismount(viola$lang$string *path, viola$lang$bool *result,
                           viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_ISMOUNT;
    req->path = path;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$realpath(viola$lang$string *path, viola$lang$string **result,
                            viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_REALPATH;
    req->path = path;
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$samefile(viola$lang$string *path1, viola$lang$string *path2,
                            viola$lang$bool *result, viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_SAMEFILE;
    req->path = path1;
    req->path2 = path2;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}

void viola$os$path$sameopenfile(viola$lang$int32 fd1, viola$lang$int32 fd2,
                                viola$lang$bool *result, viola$threads$Listener *listener) {
    viola$os$path$PathRequest *req = (viola$os$path$PathRequest *)malloc(
        sizeof(viola$os$path$PathRequest));
    memset(req, 0, sizeof(viola$os$path$PathRequest));
    req->base.type = VIOLA_PATH_REQUEST_SAMEOPENFILE;
    req->fd1 = fd1;
    req->fd2 = fd2;
    req->resultBool = result;
    submitOrRun(req, listener);
    free(req);
}
