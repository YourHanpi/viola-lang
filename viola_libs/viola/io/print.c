/* -*- coding: utf-8 -*-
 * Viola标准输入输出实现。
 * 命名空间：viola.io（C标识符前缀 viola$io$）。
 */
#include "../lang/string.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 向指定流输出UTF-8编码的字符串 */
static void writeStringToStream(FILE *stream, viola$lang$string *content) {
    if (content == NULL) {
        return;
    }
    char *text = viola$lang$string$toCharString(content);
    fwrite(text, 1, strlen(text), stream);
    free(text);
    fflush(stream);
}

/* print(string content) -> () */
void viola$io$print(viola$lang$string *content, viola$threads$Listener *listener) {
    (void)listener;
    writeStringToStream(stdout, content);
}

/* perror(string content) -> () */
void viola$io$perror(viola$lang$string *content, viola$threads$Listener *listener) {
    (void)listener;
    writeStringToStream(stderr, content);
}

/* input() -> string：从标准输入读取一行（去除末尾换行） */
void viola$io$input(viola$lang$string **result, viola$threads$Listener *listener) {
    (void)listener;
    size_t cap = 256;
    size_t len = 0;
    char *buffer = (char *)malloc(cap);
    if (buffer == NULL) {
        *result = viola$lang$string$fromCharString("");
        return;
    }
    while (fgets(buffer + len, (int)(cap - len), stdin) != NULL) {
        len += strlen(buffer + len);
        if (len > 0 && (buffer[len - 1] == '\n' || buffer[len - 1] == '\r')) {
            break;
        }
        if (len + 1 >= cap) {
            cap *= 2;
            buffer = (char *)realloc(buffer, cap);
        }
    }
    /* 去除末尾换行符 */
    while (len > 0 && (buffer[len - 1] == '\n' || buffer[len - 1] == '\r')) {
        buffer[--len] = '\0';
    }
    *result = viola$lang$string$fromCharString(buffer);
    free(buffer);
}
