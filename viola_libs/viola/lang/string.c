/* -*- coding: utf-8 -*-
 * Viola字符串运行库实现。
 *
 * 字符串内部使用UTF-16编码的uint16数组（与编译器的字符串字面量生成一致），
 * 对外（如文件读写、控制台）在UTF-8与UTF-16之间转换。
 */
#include "string.h"

#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <errno.h>

/* ================= UTF-8 <-> UTF-16 ================= */

/* 单个UTF-8序列解码为码点。返回消耗的字节数（0表示非法）。 */
static int utf8Decode(const unsigned char *s, size_t len, uint32_t *codepoint) {
    if (len == 0) {
        return 0;
    }
    unsigned char c = s[0];
    if (c < 0x80) {
        *codepoint = c;
        return 1;
    }
    int n;
    uint32_t cp;
    if ((c & 0xE0) == 0xC0) {
        n = 2;
        cp = c & 0x1F;
    } else if ((c & 0xF0) == 0xE0) {
        n = 3;
        cp = c & 0x0F;
    } else if ((c & 0xF8) == 0xF0) {
        n = 4;
        cp = c & 0x07;
    } else {
        return 0;
    }
    if ((size_t)n > len) {
        return 0;
    }
    for (int i = 1; i < n; i++) {
        if ((s[i] & 0xC0) != 0x80) {
            return 0;
        }
        cp = (cp << 6) | (s[i] & 0x3F);
    }
    *codepoint = cp;
    return n;
}

static size_t utf8Encode(uint32_t cp, char *out) {
    if (cp < 0x80) {
        out[0] = (char)cp;
        return 1;
    }
    if (cp < 0x800) {
        out[0] = (char)(0xC0 | (cp >> 6));
        out[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp < 0x10000) {
        out[0] = (char)(0xE0 | (cp >> 12));
        out[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        out[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    out[0] = (char)(0xF0 | (cp >> 18));
    out[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    out[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
    out[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}

/* ================= 对象构造与析构 ================= */

static viola$lang$string *newString(const uint16_t *data, uint64_t length) {
    viola$lang$string *str = (viola$lang$string *)malloc(sizeof(viola$lang$string));
    str->$refCount = 1;
    str->$parent = NULL;
    str->length = length;
    if (length > 0) {
        str->data = (uint16_t *)malloc(sizeof(uint16_t) * length);
        memcpy(str->data, data, sizeof(uint16_t) * length);
    } else {
        str->data = NULL;
    }
    return str;
}

viola$lang$string *viola$lang$string$fromCharString(const char *str) {
    size_t len = strlen(str);
    size_t utf16Len = 0;
    size_t pos = 0;
    while (pos < len) {
        uint32_t cp;
        int n = utf8Decode((const unsigned char *)str + pos, len - pos, &cp);
        if (n <= 0) {
            pos++;
            utf16Len++;
            continue;
        }
        pos += (size_t)n;
        utf16Len += (cp >= 0x10000) ? 2 : 1;
    }
    uint16_t *buf = utf16Len > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * utf16Len) : NULL;
    pos = 0;
    size_t i = 0;
    while (pos < len) {
        uint32_t cp;
        int n = utf8Decode((const unsigned char *)str + pos, len - pos, &cp);
        if (n <= 0) {
            buf[i++] = (uint16_t)(unsigned char)str[pos];
            pos++;
            continue;
        }
        pos += (size_t)n;
        if (cp >= 0x10000) {
            cp -= 0x10000;
            buf[i++] = (uint16_t)(0xD800 | (cp >> 10));
            buf[i++] = (uint16_t)(0xDC00 | (cp & 0x3FF));
        } else {
            buf[i++] = (uint16_t)cp;
        }
    }
    viola$lang$string *result = newString(buf, utf16Len);
    free(buf);
    return result;
}

char *viola$lang$string$toCharString(const viola$lang$string *str) {
    size_t cap = (str->length + 1) * 4;
    char *out = (char *)malloc(cap);
    size_t pos = 0;
    for (uint64_t i = 0; i < str->length; i++) {
        uint32_t cp = str->data[i];
        if (cp >= 0xD800 && cp <= 0xDBFF && i + 1 < str->length &&
            str->data[i + 1] >= 0xDC00 && str->data[i + 1] <= 0xDFFF) {
            cp = 0x10000 + ((cp - 0xD800) << 10) + (str->data[i + 1] - 0xDC00);
            i++;
        }
        char buf[4];
        size_t n = utf8Encode(cp, buf);
        if (pos + n + 1 > cap) {
            cap *= 2;
            out = (char *)realloc(out, cap);
        }
        memcpy(out + pos, buf, n);
        pos += n;
    }
    out[pos] = '\0';
    return out;
}

viola$lang$string *viola$lang$string$$array$decode(const char *str, const char *encoding) {
    /* 输入按UTF-8处理（encoding参数保留以兼容接口） */
    (void)encoding;
    return viola$lang$string$fromCharString(str);
}

void viola$lang$string$__new__$_0(viola$lang$ptr data, viola$lang$string **this,
                                  viola$threads$Listener *listener) {
    /* data为已有的uint16数组指针，长度未知时视为空（主要供内部使用） */
    (void)data;
    (void)listener;
    *this = (viola$lang$string *)malloc(sizeof(viola$lang$string));
    (*this)->$refCount = 1;
    (*this)->$parent = NULL;
    (*this)->length = 0;
    (*this)->data = NULL;
}

void viola$lang$string$__del__$_0(viola$lang$string *_this, viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount == 0) {
        if (_this->$parent) {
            viola$lang$uint32 *parentRefCount = (viola$lang$uint32 *)_this->$parent;
            (*parentRefCount)--;
        } else {
            free(_this->data);
            free(_this);
        }
    }
}

/* ================= 基本操作 ================= */

void viola$lang$string$length$_0(viola$lang$string *_this, viola$lang$uint64 *result,
                                 viola$threads$Listener *listener) {
    (void)listener;
    *result = _this->length;
}

void viola$lang$string$__add__$_0(viola$lang$string *_this, viola$lang$string *s,
                                  viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t len = _this->length + s->length;
    uint16_t *buf = len > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * len) : NULL;
    if (_this->length > 0) {
        memcpy(buf, _this->data, sizeof(uint16_t) * _this->length);
    }
    if (s->length > 0) {
        memcpy(buf + _this->length, s->data, sizeof(uint16_t) * s->length);
    }
    *result = newString(buf, len);
    free(buf);
}

void viola$lang$string$concat$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$string **result, viola$threads$Listener *listener) {
    viola$lang$string$__add__$_0(_this, s, result, listener);
}

void viola$lang$string$__mul__$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                  viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t len = _this->length * times;
    uint16_t *buf = len > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * len) : NULL;
    for (uint64_t t = 0; t < times; t++) {
        if (_this->length > 0) {
            memcpy(buf + t * _this->length, _this->data, sizeof(uint16_t) * _this->length);
        }
    }
    *result = newString(buf, len);
    free(buf);
}

void viola$lang$string$repeat$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                 viola$lang$string **result, viola$threads$Listener *listener) {
    viola$lang$string$__mul__$_0(_this, times, result, listener);
}

void viola$lang$string$__rmul__$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                   viola$lang$string **result, viola$threads$Listener *listener) {
    viola$lang$string$__mul__$_0(_this, times, result, listener);
}

/* ================= 比较 ================= */

static int stringEquals(const viola$lang$string *a, const viola$lang$string *b) {
    if (a->length != b->length) {
        return 0;
    }
    for (uint64_t i = 0; i < a->length; i++) {
        if (a->data[i] != b->data[i]) {
            return 0;
        }
    }
    return 1;
}

/* 对外相等比较（供编译器生成的按参数名传参代码使用） */
int viola$lang$string$equals(const viola$lang$string *a, const viola$lang$string *b) {
    return stringEquals(a, b);
}

void viola$lang$string$__eq__$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$bool *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = stringEquals(_this, s);
}

void viola$lang$string$__ne__$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$bool *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = !stringEquals(_this, s);
}

/* ================= 前缀/后缀 ================= */

static int stringStartsWith(const viola$lang$string *a, const viola$lang$string *prefix) {
    if (prefix->length > a->length) {
        return 0;
    }
    for (uint64_t i = 0; i < prefix->length; i++) {
        if (a->data[i] != prefix->data[i]) {
            return 0;
        }
    }
    return 1;
}

static int stringEndsWith(const viola$lang$string *a, const viola$lang$string *suffix) {
    if (suffix->length > a->length) {
        return 0;
    }
    uint64_t offset = a->length - suffix->length;
    for (uint64_t i = 0; i < suffix->length; i++) {
        if (a->data[offset + i] != suffix->data[i]) {
            return 0;
        }
    }
    return 1;
}

void viola$lang$string$startswith$_0(viola$lang$string *_this, viola$lang$string *s,
                                     viola$lang$bool *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = stringStartsWith(_this, s);
}

void viola$lang$string$startsWith$_0(viola$lang$string *_this, viola$lang$string *s,
                                     viola$lang$bool *result, viola$threads$Listener *listener) {
    viola$lang$string$startswith$_0(_this, s, result, listener);
}

void viola$lang$string$endswith$_0(viola$lang$string *_this, viola$lang$string *s,
                                   viola$lang$bool *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = stringEndsWith(_this, s);
}

void viola$lang$string$endsWith$_0(viola$lang$string *_this, viola$lang$string *s,
                                   viola$lang$bool *result, viola$threads$Listener *listener) {
    viola$lang$string$endswith$_0(_this, s, result, listener);
}

void viola$lang$string$isascii$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    for (uint64_t i = 0; i < _this->length; i++) {
        if (_this->data[i] > 0x7F) {
            *result = false;
            return;
        }
    }
    *result = true;
}

/* ================= 索引与切片 ================= */

void viola$lang$string$__getitem__$_0(viola$lang$string *_this, viola$lang$int64 index,
                                      viola$lang$string **ch, viola$threads$Listener *listener) {
    (void)listener;
    if (index < 0) {
        index += (viola$lang$int64)_this->length;
    }
    uint16_t buf[1];
    if (index < 0 || (uint64_t)index >= _this->length) {
        *ch = newString(NULL, 0);
        return;
    }
    buf[0] = _this->data[index];
    *ch = newString(buf, 1);
}

void viola$lang$string$__getitem__$_1(viola$lang$string *_this, viola$lang$slice *s,
                                      viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t start = s->start;
    uint64_t end = s->end > _this->length ? _this->length : s->end;
    uint64_t step = s->step;
    uint64_t count = start < end ? (end - start + step - 1) / step : 0;
    uint16_t *buf = count > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * count) : NULL;
    uint64_t j = 0;
    for (uint64_t i = start; i < end; i += step) {
        buf[j++] = _this->data[i];
    }
    *result = newString(buf, count);
    free(buf);
}

void viola$lang$string$slice$_0(viola$lang$string *_this, viola$lang$int64 start,
                                viola$lang$int64 end, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    if (start < 0) {
        start += (viola$lang$int64)_this->length;
    }
    if (end < 0) {
        end += (viola$lang$int64)_this->length;
    }
    if (start < 0) {
        start = 0;
    }
    if (end > (viola$lang$int64)_this->length) {
        end = (viola$lang$int64)_this->length;
    }
    if (end <= start) {
        *result = newString(NULL, 0);
        return;
    }
    *result = newString(_this->data + start, (uint64_t)(end - start));
}

/* ================= 大小写 ================= */

static uint16_t toLowerChar(uint16_t c) {
    if (c >= 'A' && c <= 'Z') {
        return (uint16_t)(c + 32);
    }
    return c;
}

static uint16_t toUpperChar(uint16_t c) {
    if (c >= 'a' && c <= 'z') {
        return (uint16_t)(c - 32);
    }
    return c;
}

void viola$lang$string$lower$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    uint16_t *buf = _this->length > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * _this->length) : NULL;
    for (uint64_t i = 0; i < _this->length; i++) {
        buf[i] = toLowerChar(_this->data[i]);
    }
    *result = newString(buf, _this->length);
    free(buf);
}

void viola$lang$string$upper$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    uint16_t *buf = _this->length > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * _this->length) : NULL;
    for (uint64_t i = 0; i < _this->length; i++) {
        buf[i] = toUpperChar(_this->data[i]);
    }
    *result = newString(buf, _this->length);
    free(buf);
}

/* ================= 查找与替换 ================= */

static int64_t stringFind(const viola$lang$string *a, const viola$lang$string *needle,
                          uint64_t from) {
    if (needle->length == 0) {
        return (int64_t)from;
    }
    if (needle->length > a->length) {
        return -1;
    }
    for (uint64_t i = from; i + needle->length <= a->length; i++) {
        int match = 1;
        for (uint64_t j = 0; j < needle->length; j++) {
            if (a->data[i + j] != needle->data[j]) {
                match = 0;
                break;
            }
        }
        if (match) {
            return (int64_t)i;
        }
    }
    return -1;
}

void viola$lang$string$replace$_0(viola$lang$string *_this, viola$lang$string *old,
                                  viola$lang$string *new, viola$lang$string **result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    if (old->length == 0 || old->length > _this->length) {
        *result = newString(_this->data, _this->length);
        return;
    }
    /* 计算替换次数并构建结果 */
    uint64_t count = 0;
    int64_t pos = 0;
    while ((pos = stringFind(_this, old, (uint64_t)pos)) >= 0) {
        count++;
        pos += (int64_t)old->length;
    }
    uint64_t outLen = _this->length + count * (new->length - old->length);
    uint16_t *buf = outLen > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * outLen) : NULL;
    uint64_t src = 0;
    uint64_t dst = 0;
    while (src < _this->length) {
        if (src + old->length <= _this->length &&
            stringFind(_this, old, src) == (int64_t)src) {
            if (new->length > 0) {
                memcpy(buf + dst, new->data, sizeof(uint16_t) * new->length);
                dst += new->length;
            }
            src += old->length;
        } else {
            buf[dst++] = _this->data[src++];
        }
    }
    *result = newString(buf, dst);
    free(buf);
}

/* ================= 分割与连接 ================= */

static viola$lang$string$$array *newStringArray(void) {
    viola$lang$string$$array *arr = (viola$lang$string$$array *)malloc(sizeof(viola$lang$string$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->data = NULL;
    arr->size = 0;
    return arr;
}

void viola$lang$string$split$_0(viola$lang$string *_this, viola$lang$string *s,
                                viola$lang$string$$array **results,
                                viola$threads$Listener *listener) {
    viola$lang$string$split$_1(_this, s, UINT64_MAX, results, listener);
}

void viola$lang$string$split$_1(viola$lang$string *_this, viola$lang$string *s,
                                viola$lang$uint64 maxsplit, viola$lang$string$$array **results,
                                viola$threads$Listener *listener) {
    (void)listener;
    /* -1（UINT64_MAX）表示不限制分割次数 */
    if (maxsplit == UINT64_MAX) {
        maxsplit = _this->length;
    }
    viola$lang$string$$array *arr = newStringArray();
    uint64_t cap = 8;
    arr->data = (viola$lang$string **)malloc(sizeof(viola$lang$string *) * cap);
    uint64_t start = 0;
    uint64_t splits = 0;
    for (uint64_t i = 0; i <= _this->length; i++) {
        int isSep = 0;
        if (s->length > 0 && i + s->length <= _this->length) {
            isSep = 1;
            for (uint64_t j = 0; j < s->length; j++) {
                if (_this->data[i + j] != s->data[j]) {
                    isSep = 0;
                    break;
                }
            }
        } else if (s->length == 0 && i < _this->length) {
            isSep = 1; /* 空分隔符：按字符分割 */
        }
        if (isSep && splits < maxsplit) {
            if (arr->size >= cap) {
                cap *= 2;
                arr->data = (viola$lang$string **)realloc(arr->data,
                                                            sizeof(viola$lang$string *) * cap);
            }
            arr->data[arr->size++] = newString(_this->data + start, i - start);
            start = i + s->length;
            splits++;
            i += s->length > 0 ? s->length - 1 : 0;
        }
    }
    if (arr->size >= cap) {
        cap++;
        arr->data = (viola$lang$string **)realloc(arr->data, sizeof(viola$lang$string *) * cap);
    }
    arr->data[arr->size++] = newString(_this->data + start, _this->length - start);
    *results = arr;
}

void viola$lang$string$rsplit$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$string$$array **results,
                                 viola$threads$Listener *listener) {
    viola$lang$string$rsplit$_1(_this, s, UINT64_MAX, results, listener);
}

void viola$lang$string$rsplit$_1(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$uint64 maxsplit, viola$lang$string$$array **results,
                                 viola$threads$Listener *listener) {
    /* 简化实现：从右向左收集分隔位置后再构建 */
    (void)listener;
    if (maxsplit == UINT64_MAX) {
        maxsplit = _this->length;
    }
    if (s->length == 0) {
        viola$lang$string$split$_1(_this, s, maxsplit, results, listener);
        return;
    }
    /* 找到所有分隔位置 */
    uint64_t *sepPos = (uint64_t *)malloc(sizeof(uint64_t) * (_this->length + 1));
    uint64_t sepCount = 0;
    for (uint64_t i = 0; i + s->length <= _this->length; i++) {
        int isSep = 1;
        for (uint64_t j = 0; j < s->length; j++) {
            if (_this->data[i + j] != s->data[j]) {
                isSep = 0;
                break;
            }
        }
        if (isSep) {
            sepPos[sepCount++] = i;
            i += s->length - 1;
        }
    }
    viola$lang$string$$array *arr = newStringArray();
    uint64_t cap = 8;
    arr->data = (viola$lang$string **)malloc(sizeof(viola$lang$string *) * cap);
    /* 取最后maxsplit个分隔（含首尾边界） */
    uint64_t take = sepCount < maxsplit ? sepCount : maxsplit;
    uint64_t start = 0;
    for (uint64_t k = 0; k < take; k++) {
        uint64_t idx = sepCount - take + k;
        if (arr->size >= cap) {
            cap *= 2;
            arr->data = (viola$lang$string **)realloc(arr->data,
                                                        sizeof(viola$lang$string *) * cap);
        }
        arr->data[arr->size++] = newString(_this->data + start, sepPos[idx] - start);
        start = sepPos[idx] + s->length;
    }
    if (arr->size >= cap) {
        cap++;
        arr->data = (viola$lang$string **)realloc(arr->data, sizeof(viola$lang$string *) * cap);
    }
    arr->data[arr->size++] = newString(_this->data + start, _this->length - start);
    free(sepPos);
    *results = arr;
}

void viola$lang$string$join$_0(viola$lang$string *_this, viola$lang$string$$array *s,
                               viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t totalLen = 0;
    for (uint64_t i = 0; i < s->size; i++) {
        totalLen += s->data[i]->length;
        if (i + 1 < s->size) {
            totalLen += _this->length;
        }
    }
    uint16_t *buf = totalLen > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * totalLen) : NULL;
    uint64_t pos = 0;
    for (uint64_t i = 0; i < s->size; i++) {
        if (s->data[i]->length > 0) {
            memcpy(buf + pos, s->data[i]->data, sizeof(uint16_t) * s->data[i]->length);
            pos += s->data[i]->length;
        }
        if (i + 1 < s->size && _this->length > 0) {
            memcpy(buf + pos, _this->data, sizeof(uint16_t) * _this->length);
            pos += _this->length;
        }
    }
    *result = newString(buf, totalLen);
    free(buf);
}

void viola$lang$string$unicode$_0(viola$lang$string *_this, viola$lang$uint16$$array **result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$uint16$$array *arr = (viola$lang$uint16$$array *)malloc(sizeof(viola$lang$uint16$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->size = _this->length;
    arr->data = _this->length > 0 ? (viola$lang$uint16 *)malloc(sizeof(viola$lang$uint16) * _this->length) : NULL;
    if (_this->length > 0) {
        memcpy(arr->data, _this->data, sizeof(viola$lang$uint16) * _this->length);
    }
    *result = arr;
}

/* ================= 0.1新增：查找与统计 ================= */

/* 从from位置起查找子串（from可超出长度）。返回索引，未找到返回-1。 */
static int64_t stringFindFrom(const viola$lang$string *a, const viola$lang$string *needle,
                              uint64_t from) {
    if (needle->length == 0) {
        return from <= a->length ? (int64_t)from : -1;
    }
    if (needle->length > a->length) {
        return -1;
    }
    for (uint64_t i = from; i + needle->length <= a->length; i++) {
        int match = 1;
        for (uint64_t j = 0; j < needle->length; j++) {
            if (a->data[i + j] != needle->data[j]) {
                match = 0;
                break;
            }
        }
        if (match) {
            return (int64_t)i;
        }
    }
    return -1;
}

static uint32_t findResult(int64_t pos) {
    /* 未找到时返回UINT32_MAX（对应Python的-1，uint32无法表示负数） */
    return pos < 0 ? UINT32_MAX : (uint32_t)pos;
}

/* count(sub) -> uint32：统计sub非重叠出现的次数 */
void viola$lang$string$count$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
    uint32_t count = 0;
    if (sub->length == 0) {
        /* 空子串：长度为length+1 */
        *result = (viola$lang$uint32)_this->length + 1;
        return;
    }
    uint64_t pos = 0;
    while (pos + sub->length <= _this->length) {
        if (stringFindFrom(_this, sub, pos) == (int64_t)pos) {
            count++;
            pos += sub->length;
        } else {
            pos++;
        }
    }
    *result = count;
}

/* find(sub) -> uint32：返回sub首次出现的索引，未找到返回UINT32_MAX */
void viola$lang$string$find$_0(viola$lang$string *_this, viola$lang$string *sub,
                               viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = findResult(stringFindFrom(_this, sub, 0));
}

/* rfind(sub) -> uint32：返回sub最后一次出现的索引，未找到返回UINT32_MAX */
void viola$lang$string$rfind$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener) {
    (void)listener;
    int64_t found = -1;
    uint64_t pos = 0;
    while (pos + sub->length <= _this->length || (sub->length == 0 && pos <= _this->length)) {
        int64_t hit = stringFindFrom(_this, sub, pos);
        if (hit < 0) {
            break;
        }
        found = hit;
        pos = (uint64_t)hit + (sub->length > 0 ? sub->length : 1);
    }
    if (sub->length == 0) {
        *result = (viola$lang$uint32)_this->length;
        return;
    }
    *result = findResult(found);
}

/* index(sub) -> uint32：与find一致（0.1未实现异常，未找到返回UINT32_MAX） */
void viola$lang$string$index$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener) {
    viola$lang$string$find$_0(_this, sub, result, listener);
}

/* rindex(sub) -> uint32：与rfind一致 */
void viola$lang$string$rindex$_0(viola$lang$string *_this, viola$lang$string *sub,
                                 viola$lang$uint32 *result, viola$threads$Listener *listener) {
    viola$lang$string$rfind$_0(_this, sub, result, listener);
}

/* ================= 0.1新增：数值转换 ================= */

/* float() -> float64：解析为浮点数（支持inf/nan与科学计数法） */
void viola$lang$string$float$_0(viola$lang$string *_this, viola$lang$float64 *result,
                                viola$threads$Listener *listener) {
    (void)listener;
    char *text = viola$lang$string$toCharString(_this);
    char *end = NULL;
    errno = 0;
    double value = strtod(text, &end);
    if (end == text) {
        value = 0.0;
    }
    free(text);
    *result = value;
}

/* int(base = 10) -> int64：解析为整数（支持2~16进制） */
void viola$lang$string$int$_0(viola$lang$string *_this, viola$lang$int64 *result,
                              viola$threads$Listener *listener) {
    char *text = viola$lang$string$toCharString(_this);
    char *end = NULL;
    errno = 0;
    long long value = strtoll(text, &end, 10);
    if (end == text) {
        value = 0;
    }
    free(text);
    *result = value;
}

void viola$lang$string$int$_1(viola$lang$string *_this, viola$lang$uint8 base,
                              viola$lang$int64 *result, viola$threads$Listener *listener) {
    (void)listener;
    if (base < 2 || base > 16) {
        *result = 0;
        return;
    }
    char *text = viola$lang$string$toCharString(_this);
    char *end = NULL;
    errno = 0;
    long long value = strtoll(text, &end, (int)base);
    if (end == text) {
        value = 0;
    }
    free(text);
    *result = value;
}

/* 整数按base（2~16）转换为字符串（含负号），写入UTF-16缓冲区 */
static viola$lang$string *intToString(int64_t value, uint8_t base) {
    char buf[72];
    char *p = buf + sizeof(buf) - 1;
    *p = '\0';
    uint64_t u = value < 0 ? (uint64_t)(-(value + 1)) + 1 : (uint64_t)value;
    static const char digits[] = "0123456789abcdef";
    if (u == 0) {
        *--p = '0';
    }
    while (u > 0) {
        *--p = digits[u % base];
        u /= base;
    }
    if (value < 0) {
        *--p = '-';
    }
    return viola$lang$string$fromCharString(p);
}

/* fromInt(value, base = 10) -> string：整数转换为字符串（支持2~16进制） */
void viola$lang$string$fromInt$_0(viola$lang$int64 value, viola$lang$string **result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    *result = intToString(value, 10);
}

void viola$lang$string$fromInt$_1(viola$lang$int64 value, viola$lang$uint8 base,
                                  viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    if (base < 2 || base > 16) {
        *result = intToString(value, 10);
        return;
    }
    *result = intToString(value, base);
}

/* fromFloat(value) -> string：浮点数转换为字符串（类似%.15g，去除多余尾零） */
void viola$lang$string$fromFloat$_0(viola$lang$float64 value, viola$lang$string **result,
                                    viola$threads$Listener *listener) {
    (void)listener;
    char buf[64];
    if (value != value) {
        *result = viola$lang$string$fromCharString("nan");
        return;
    }
    if (value > DBL_MAX || value < -DBL_MAX) {
        *result = viola$lang$string$fromCharString(value > 0 ? "inf" : "-inf");
        return;
    }
    snprintf(buf, sizeof(buf), "%.15g", value);
    /* 去除指数表示外的多余尾零：保留至少一位小数 */
    if (strchr(buf, 'e') == NULL && strchr(buf, '.') != NULL) {
        size_t len = strlen(buf);
        while (len > 1 && buf[len - 1] == '0') {
            len--;
        }
        if (len > 0 && buf[len - 1] == '.') {
            len--;
        }
        buf[len] = '\0';
    }
    *result = viola$lang$string$fromCharString(buf);
}

/* ================= 0.1新增：字符类别判断 ================= */

static int isAsciiAlpha(uint16_t c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static int isAsciiDigit(uint16_t c) {
    return c >= '0' && c <= '9';
}

static int isUnicodeDigit(uint16_t c) {
    if (isAsciiDigit(c)) {
        return 1;
    }
    /* 常见Unicode十进制数字区段 */
    if (c >= 0x0660 && c <= 0x0669) {
        return 1; /* 阿拉伯-印度数字 */
    }
    if (c >= 0x06F0 && c <= 0x06F9) {
        return 1; /* 扩展阿拉伯-印度数字 */
    }
    if (c >= 0x0966 && c <= 0x096F) {
        return 1; /* 天城文数字 */
    }
    if (c >= 0xFF10 && c <= 0xFF19) {
        return 1; /* 全角数字 */
    }
    return 0;
}

static int stringAll(const viola$lang$string *s, int (*pred)(uint16_t), int emptyValue) {
    if (s->length == 0) {
        return emptyValue;
    }
    for (uint64_t i = 0; i < s->length; i++) {
        if (!pred(s->data[i])) {
            return 0;
        }
    }
    return 1;
}

void viola$lang$string$isalnum$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (!isAsciiAlpha(c) && !isUnicodeDigit(c)) {
            *result = 0;
            break;
        }
    }
    if (_this->length == 0) {
        *result = 0;
    }
}

void viola$lang$string$isalpha$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        if (!isAsciiAlpha(_this->data[i])) {
            *result = 0;
            break;
        }
    }
    if (_this->length == 0) {
        *result = 0;
    }
}

void viola$lang$string$isdecimal$_0(viola$lang$string *_this, viola$lang$bool *result,
                                    viola$threads$Listener *listener) {
    (void)listener;
    *result = stringAll(_this, isUnicodeDigit, 0);
}

void viola$lang$string$isdigit$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    *result = stringAll(_this, isUnicodeDigit, 0);
}

void viola$lang$string$isidentifier$_0(viola$lang$string *_this, viola$lang$bool *result,
                                       viola$threads$Listener *listener) {
    (void)listener;
    *result = 0;
    if (_this->length == 0) {
        return;
    }
    uint16_t first = _this->data[0];
    if (!isAsciiAlpha(first) && first != '_') {
        return;
    }
    *result = 1;
    for (uint64_t i = 1; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (!isAsciiAlpha(c) && !isAsciiDigit(c) && c != '_') {
            *result = 0;
            break;
        }
    }
}

void viola$lang$string$islower$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    int hasCased = 0;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (c >= 'A' && c <= 'Z') {
            *result = 0;
            break;
        }
        if (c >= 'a' && c <= 'z') {
            hasCased = 1;
        }
    }
    if (!hasCased) {
        *result = 0;
    }
}

void viola$lang$string$isupper$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    int hasCased = 0;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (c >= 'a' && c <= 'z') {
            *result = 0;
            break;
        }
        if (c >= 'A' && c <= 'Z') {
            hasCased = 1;
        }
    }
    if (!hasCased) {
        *result = 0;
    }
}

void viola$lang$string$isnumeric$_0(viola$lang$string *_this, viola$lang$bool *result,
                                    viola$threads$Listener *listener) {
    (void)listener;
    *result = stringAll(_this, isUnicodeDigit, 0);
}

void viola$lang$string$isprintable$_0(viola$lang$string *_this, viola$lang$bool *result,
                                      viola$threads$Listener *listener) {
    (void)listener;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (c < 0x20 || c == 0x7F) {
            *result = 0;
            break;
        }
    }
}

void viola$lang$string$isspace$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener) {
    (void)listener;
    *result = 1;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (c != ' ' && c != '\t' && c != '\n' && c != '\r' && c != '\v' && c != '\f') {
            *result = 0;
            break;
        }
    }
    if (_this->length == 0) {
        *result = 0;
    }
}

/* ================= 0.1新增：填充与修剪 ================= */

static uint16_t fillCharOf(const viola$lang$string *fill) {
    if (fill != NULL && fill->length > 0) {
        return fill->data[0];
    }
    return ' ';
}

/* 左对齐：用fill字符在右侧填充到length长度（"ab".ljust(4,"*") == "ab**"） */
void viola$lang$string$ljust$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string *fillChar, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    uint16_t fill = fillCharOf(fillChar);
    uint64_t total = (uint64_t)length > _this->length ? length : _this->length;
    uint16_t *buf = total > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * total) : NULL;
    if (_this->length > 0) {
        memcpy(buf, _this->data, sizeof(uint16_t) * _this->length);
    }
    for (uint64_t i = _this->length; i < total; i++) {
        buf[i] = fill;
    }
    *result = newString(buf, total);
    free(buf);
}

/* 右对齐：用fill字符在左侧填充到length长度（"ab".rjust(4,"*") == "**ab"） */
void viola$lang$string$rjust$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string *fillChar, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    (void)listener;
    uint16_t fill = fillCharOf(fillChar);
    uint64_t total = (uint64_t)length > _this->length ? length : _this->length;
    uint16_t *buf = total > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * total) : NULL;
    for (uint64_t i = 0; i + _this->length < total; i++) {
        buf[i] = fill;
    }
    if (_this->length > 0) {
        memcpy(buf + total - _this->length, _this->data, sizeof(uint16_t) * _this->length);
    }
    *result = newString(buf, total);
    free(buf);
}

/* 字符是否在修剪集合中 */
static int inStripSet(uint16_t c, const viola$lang$string *set) {
    for (uint64_t i = 0; i < set->length; i++) {
        if (set->data[i] == c) {
            return 1;
        }
    }
    return 0;
}

void viola$lang$string$lstrip$_0(viola$lang$string *_this, viola$lang$string **result,
                                 viola$threads$Listener *listener) {
    viola$lang$string *def = viola$lang$string$fromCharString(" \t\n\r");
    viola$lang$string$lstrip$_1(_this, def, result, listener);
    free(def);
}

/* 去除左侧的修剪集合字符 */
void viola$lang$string$lstrip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                 viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t start = 0;
    while (start < _this->length && inStripSet(_this->data[start], toRemove)) {
        start++;
    }
    *result = newString(_this->data + start, _this->length - start);
}

void viola$lang$string$rstrip$_0(viola$lang$string *_this, viola$lang$string **result,
                                 viola$threads$Listener *listener) {
    viola$lang$string *def = viola$lang$string$fromCharString(" \t\n\r");
    viola$lang$string$rstrip$_1(_this, def, result, listener);
    free(def);
}

/* 去除右侧的修剪集合字符 */
void viola$lang$string$rstrip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                 viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t end = _this->length;
    while (end > 0 && inStripSet(_this->data[end - 1], toRemove)) {
        end--;
    }
    *result = newString(_this->data, end);
}

void viola$lang$string$strip$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener) {
    viola$lang$string *def = viola$lang$string$fromCharString(" \t\n\r");
    viola$lang$string$strip$_1(_this, def, result, listener);
    free(def);
}

/* 去除两侧的修剪集合字符 */
void viola$lang$string$strip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t start = 0;
    uint64_t end = _this->length;
    while (start < end && inStripSet(_this->data[start], toRemove)) {
        start++;
    }
    while (end > start && inStripSet(_this->data[end - 1], toRemove)) {
        end--;
    }
    *result = newString(_this->data + start, end - start);
}

/* 大小写互换 */
void viola$lang$string$swapcase$_0(viola$lang$string *_this, viola$lang$string **result,
                                   viola$threads$Listener *listener) {
    (void)listener;
    uint16_t *buf = _this->length > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * _this->length) : NULL;
    for (uint64_t i = 0; i < _this->length; i++) {
        uint16_t c = _this->data[i];
        if (c >= 'a' && c <= 'z') {
            buf[i] = (uint16_t)(c - 32);
        } else if (c >= 'A' && c <= 'Z') {
            buf[i] = (uint16_t)(c + 32);
        } else {
            buf[i] = c;
        }
    }
    *result = newString(buf, _this->length);
    free(buf);
}

/* 左侧补零到length长度（符号保持在最前） */
void viola$lang$string$zfill$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    uint64_t total = (uint64_t)length > _this->length ? length : _this->length;
    uint64_t signLen = 0;
    if (_this->length > 0 && (_this->data[0] == '+' || _this->data[0] == '-')) {
        signLen = 1;
    }
    uint16_t *buf = total > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * total) : NULL;
    /* 需要补的零的个数：有符号时符号位也占用一个位置（补零数加一） */
    uint64_t zeroCount = total - _this->length + signLen;
    for (uint64_t i = 0; i < zeroCount; i++) {
        buf[i] = '0';
    }
    if (signLen > 0 && total > 0) {
        buf[0] = _this->data[0];
        if (_this->length > 0) {
            memcpy(buf + total - _this->length + 1, _this->data + 1,
                   sizeof(uint16_t) * (_this->length - 1));
        }
    } else if (_this->length > 0) {
        memcpy(buf + total - _this->length, _this->data, sizeof(uint16_t) * _this->length);
    }
    *result = newString(buf, total);
    free(buf);
}

/* replace(oldSub, newSub, count)：count为0时替换全部 */
void viola$lang$string$replace$_1(viola$lang$string *_this, viola$lang$string *old,
                                  viola$lang$string *new, viola$lang$uint32 count,
                                  viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    if (old->length == 0 || old->length > _this->length) {
        *result = newString(_this->data, _this->length);
        return;
    }
    /* 收集所有匹配位置 */
    uint64_t total = 0;
    uint64_t *posList = (uint64_t *)malloc(sizeof(uint64_t) * (_this->length + 1));
    uint64_t pos = 0;
    while (pos + old->length <= _this->length) {
        if (stringFindFrom(_this, old, pos) == (int64_t)pos) {
            posList[total++] = pos;
            pos += old->length;
        } else {
            pos++;
        }
    }
    uint64_t replaceCount = count == 0 ? total : (total < count ? total : count);
    uint64_t outLen = _this->length + replaceCount * (new->length - old->length);
    uint16_t *buf = outLen > 0 ? (uint16_t *)malloc(sizeof(uint16_t) * outLen) : NULL;
    uint64_t src = 0;
    uint64_t dst = 0;
    for (uint64_t i = 0; i < replaceCount; i++) {
        uint64_t matchPos = posList[i];
        if (matchPos > src) {
            memcpy(buf + dst, _this->data + src, sizeof(uint16_t) * (matchPos - src));
            dst += matchPos - src;
        }
        if (new->length > 0) {
            memcpy(buf + dst, new->data, sizeof(uint16_t) * new->length);
            dst += new->length;
        }
        src = matchPos + old->length;
    }
    if (src < _this->length) {
        memcpy(buf + dst, _this->data + src, sizeof(uint16_t) * (_this->length - src));
        dst += _this->length - src;
    }
    free(posList);
    *result = newString(buf, dst);
    free(buf);
}
