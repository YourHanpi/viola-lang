/* -*- coding: utf-8 -*-
 * Viola文件串行读写系统实现。
 *
 * 命名空间：viola.io（C标识符前缀 viola$io$）。
 * 模型：子线程发起请求（经全局资源管理器入队），主线程在waitListener的
 * 空闲期间执行请求并返回相关数据。主线程自身的文件操作直接执行。
 */
#include "../lang/global_resource_manager.h"
#include "../lang/string.h"
#include "../threads.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sched.h>
#endif

/* 数组类型（布局与编译器生成的数组结构体一致，使用相同guard避免冲突） */
#ifndef _VIOLA_ARRAY_T_viola$lang$uint8$$array
#define _VIOLA_ARRAY_T_viola$lang$uint8$$array
typedef struct viola$lang$uint8$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint8 *data;
    viola$lang$uint64 size;
} viola$lang$uint8$$array;
#endif

/* ================= 请求类型 ================= */
enum {
    VIOLA_FILE_REQUEST_OPEN = 1,
    VIOLA_FILE_REQUEST_CLOSE,
    VIOLA_FILE_REQUEST_READ,
    VIOLA_FILE_REQUEST_READ_BYTES,
    VIOLA_FILE_REQUEST_WRITE,
    VIOLA_FILE_REQUEST_WRITE_BYTES
};

/* 文件请求结构体（第一个成员是请求类型编码） */
typedef struct viola$io$FileRequest {
    viola$lang$global_resource_manager$Request base;
    viola$lang$string *path;
    viola$lang$string *mode;
    viola$lang$string *content;
    viola$lang$uint8 *bytes;
    viola$lang$uint64 bytesLength;
    viola$io$file *file;
    viola$lang$string **resultString;
    viola$lang$uint64 *resultLength;
    viola$io$file **resultFile;
    volatile uint8_t done;
} viola$io$FileRequest;

static void yieldCPU(void) {
#ifdef _WIN32
    Sleep(0);
#else
    sched_yield();
#endif
}

/* 子线程提交请求并等待主线程执行（主线程直接执行） */
static void submitOrRun(viola$io$FileRequest *request, viola$threads$Listener *listener) {
    if (listener != NULL && listener->currentThreadId == 0) {
        /* 主线程直接执行 */
        viola$lang$global_resource_manager$handleRequest(&request->base);
        return;
    }
    request->done = 0;
    viola$lang$global_resource_manager$enqueueRequest(&request->base);
    while (!request->done) {
        yieldCPU();
    }
}

/* ================= 请求处理器 ================= */

static void handleOpen(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    char *path = viola$lang$string$toCharString(req->path);
    char *mode = viola$lang$string$toCharString(req->mode);
    FILE *fp = fopen(path, mode);
    free(path);
    free(mode);
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

static void handleClose(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    if (req->file != NULL && req->file->fp != NULL) {
        if (req->file->isPopen) {
            pclose((FILE *)req->file->fp);
        } else {
            fclose((FILE *)req->file->fp);
        }
        req->file->fp = NULL;
    }
    req->done = 1;
}

static void handleRead(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    if (req->file == NULL || req->file->fp == NULL) {
        *req->resultString = viola$lang$string$fromCharString("");
        req->done = 1;
        return;
    }
    FILE *fp = (FILE *)req->file->fp;
    long saved = ftell(fp);
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, saved, SEEK_SET);
    if (size < 0) {
        size = 0;
    }
    char *buffer = (char *)malloc((size_t)size + 1);
    size_t readSize = fread(buffer, 1, (size_t)size, fp);
    buffer[readSize] = '\0';
    viola$lang$string *str = viola$lang$string$fromCharString(buffer);
    free(buffer);
    *req->resultString = str;
    req->done = 1;
}

static void handleReadBytes(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    if (req->file == NULL || req->file->fp == NULL) {
        req->bytes = NULL;
        *req->resultLength = 0;
        req->done = 1;
        return;
    }
    FILE *fp = (FILE *)req->file->fp;
    long saved = ftell(fp);
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, saved, SEEK_SET);
    if (size < 0) {
        size = 0;
    }
    viola$lang$uint8 *bytes = (viola$lang$uint8 *)malloc((size_t)size);
    size_t readSize = fread(bytes, 1, (size_t)size, fp);
    req->bytes = bytes;
    *req->resultLength = (viola$lang$uint64)readSize;
    req->done = 1;
}

static void handleWrite(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    if (req->file != NULL && req->file->fp != NULL && req->content != NULL) {
        char *text = viola$lang$string$toCharString(req->content);
        fwrite(text, 1, strlen(text), (FILE *)req->file->fp);
        fflush((FILE *)req->file->fp);
        free(text);
    }
    req->done = 1;
}

static void handleWriteBytes(viola$lang$global_resource_manager$Request *base) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)base;
    if (req->file != NULL && req->file->fp != NULL && req->bytes != NULL) {
        fwrite(req->bytes, 1, (size_t)req->bytesLength, (FILE *)req->file->fp);
        fflush((FILE *)req->file->fp);
    }
    req->done = 1;
}

/* 注册文件请求处理器（由资源管理器初始化时调用） */
void viola$io$registerFileHandlers(void) {
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_OPEN, handleOpen);
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_CLOSE, handleClose);
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_READ, handleRead);
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_READ_BYTES, handleReadBytes);
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_WRITE, handleWrite);
    viola$lang$global_resource_manager$registerHandler(VIOLA_FILE_REQUEST_WRITE_BYTES, handleWriteBytes);
}

/* ================= Viola接口 ================= */

/* file.__new__(path, mode, encoding) -> this（与open函数等效） */
void viola$io$file$__new__$_0(viola$lang$string *path, viola$lang$string *mode,
                              viola$lang$string *encoding, viola$io$file **this,
                              viola$threads$Listener *listener) {
    viola$io$open(path, mode, encoding, this, listener);
}

/* open()的默认参数全局变量（编译器生成的默认参数引用指向这里）：
 * mode = "r"，encoding = "utf-8"。引用计数为1使清理代码不会释放
 * 该静态对象（见开发疑问记录70）。 */
static viola$lang$string _viola_io_default_mode = {
    1, NULL, 1, (viola$lang$uint16 *)&(viola$lang$uint16[]){ 'r' }
};
static viola$lang$string _viola_io_default_encoding = {
    1, NULL, 5, (viola$lang$uint16 *)&(viola$lang$uint16[]){ 'u', 't', 'f', '-', '8' }
};
viola$lang$string *viola$io$open$$default$mode = &_viola_io_default_mode;
viola$lang$string *viola$io$open$$default$encoding = &_viola_io_default_encoding;

/* open(path, mode, encoding) -> file */
void viola$io$open(viola$lang$string *path, viola$lang$string *mode,
                   viola$lang$string *encoding, viola$io$file **f,
                   viola$threads$Listener *listener) {
    (void)encoding;
    viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
    memset(req, 0, sizeof(viola$io$FileRequest));
    req->base.type = VIOLA_FILE_REQUEST_OPEN;
    req->path = path;
    req->mode = mode;
    req->resultFile = f;
    submitOrRun(req, listener);
    free(req);
}

/* read(file) -> string */
void viola$io$read(viola$io$file *file, viola$lang$string **result,
                   viola$threads$Listener *listener) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
    memset(req, 0, sizeof(viola$io$FileRequest));
    req->base.type = VIOLA_FILE_REQUEST_READ;
    req->file = file;
    req->resultString = result;
    submitOrRun(req, listener);
    free(req);
}

/* readBytes(file) -> uint8[] */
void viola$io$readBytes(viola$io$file *file, viola$lang$uint8$$array **result,
                        viola$threads$Listener *listener) {
    viola$lang$uint64 resultLength = 0;
    viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
    memset(req, 0, sizeof(viola$io$FileRequest));
    req->base.type = VIOLA_FILE_REQUEST_READ_BYTES;
    req->file = file;
    req->resultLength = &resultLength;
    submitOrRun(req, listener);
    viola$lang$uint8$$array *arr = (viola$lang$uint8$$array *)malloc(sizeof(viola$lang$uint8$$array));
    arr->$refCount = 1;
    arr->$parent = NULL;
    arr->size = resultLength;
    arr->data = resultLength > 0 ? req->bytes : NULL;
    if (resultLength == 0) {
        free(req->bytes);
    }
    *result = arr;
    free(req);
}

/* write(file, content) -> () */
void viola$io$write(viola$io$file *file, viola$lang$string *content,
                    viola$threads$Listener *listener) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
    memset(req, 0, sizeof(viola$io$FileRequest));
    req->base.type = VIOLA_FILE_REQUEST_WRITE;
    req->file = file;
    req->content = content;
    submitOrRun(req, listener);
    free(req);
}

/* writeBytes(file, content: uint8[]) -> () */
void viola$io$writeBytes(viola$io$file *file, viola$lang$uint8$$array *content,
                         viola$threads$Listener *listener) {
    viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
    memset(req, 0, sizeof(viola$io$FileRequest));
    req->base.type = VIOLA_FILE_REQUEST_WRITE_BYTES;
    req->file = file;
    req->bytes = content != NULL ? content->data : NULL;
    req->bytesLength = content != NULL ? content->size : 0;
    submitOrRun(req, listener);
    free(req);
}

/* file.__del__() -> () */
void viola$io$file$__del__$_0(viola$io$file *_this, viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount == 0) {
        if (_this->$parent) {
            viola$lang$uint32 *parentRefCount = (viola$lang$uint32 *)_this->$parent;
            (*parentRefCount)--;
        } else {
            if (_this->fp != NULL) {
                viola$io$FileRequest *req = (viola$io$FileRequest *)malloc(sizeof(viola$io$FileRequest));
                memset(req, 0, sizeof(viola$io$FileRequest));
                req->base.type = VIOLA_FILE_REQUEST_CLOSE;
                req->file = _this;
                submitOrRun(req, listener);
                free(req);
            }
            free(_this);
        }
    }
}
