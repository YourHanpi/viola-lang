/* -*- coding: utf-8 -*-
 * Viola操作系统接口运行库：绑定Windows和POSIX的相关接口，使用条件编译。
 * 命名空间：viola.os（C标识符前缀 viola$os$）。
 */
#include "lang/string.h"

#include <stdlib.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#include <sys/time.h>
#endif

/* sleep(milliseconds) -> () */
void viola$os$sleep(viola$lang$uint64 milliseconds, viola$threads$Listener *listener) {
    (void)listener;
#ifdef _WIN32
    Sleep((DWORD)milliseconds);
#else
    usleep((useconds_t)(milliseconds * 1000));
#endif
}

/* exit(code) -> () */
void viola$os$exit(viola$lang$int32 code, viola$threads$Listener *listener) {
    (void)listener;
    exit(code);
}

/* getEnv(name) -> string */
void viola$os$getEnv(viola$lang$string *name, viola$lang$string **result,
                     viola$threads$Listener *listener) {
    (void)listener;
    char *nameText = viola$lang$string$toCharString(name);
    const char *value = getenv(nameText);
    free(nameText);
    *result = viola$lang$string$fromCharString(value != NULL ? value : "");
}

/* time() -> uint64：当前Unix时间戳（毫秒） */
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

/* system(command) -> int32 */
void viola$os$system(viola$lang$string *command, viola$lang$int32 *result,
                     viola$threads$Listener *listener) {
    (void)listener;
    char *cmdText = viola$lang$string$toCharString(command);
    *result = system(cmdText);
    free(cmdText);
}
