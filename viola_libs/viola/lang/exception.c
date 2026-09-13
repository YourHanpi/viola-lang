/* -*- coding: utf-8 -*-
 * Viola异常运行库实现。
 * 命名空间：viola.lang.exception（C标识符前缀 viola$lang$exception$）。
 */
#include "string.h"

/* 异常基类的TypeInfo（子类的$parent链指向此处） */
viola$dynamic$TypeInfo viola$lang$exception$Exception$$vtable = {NULL, NULL};

/* 构造异常：__new__(string message) -> Exception */
void viola$lang$exception$Exception$__new__$_0(viola$lang$string *message,
                                               viola$lang$exception$Exception **this,
                                               viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$exception$Exception *exc =
        (viola$lang$exception$Exception *)malloc(sizeof(viola$lang$exception$Exception));
    exc->$refCount = 1;
    exc->$parent = NULL;
    exc->$$vtable = &viola$lang$exception$Exception$$vtable;
    exc->message = message;
    *this = exc;
}

/* 父类构造初始化：在子类已分配的对象上设置message。
   子类以`super = Exception(message);`调用：对象与其vtable均由子类构造函数
   负责分配与设置，此处只初始化基类成员（见开发疑问记录107）。 */
void viola$lang$exception$Exception$__new__super$_0(viola$lang$string *message,
                                                    viola$lang$exception$Exception *this,
                                                    viola$threads$Listener *listener) {
    (void)listener;
    if (this == NULL) {
        return;
    }
    this->message = message;
}

/* 获取异常消息：what() -> string。
   message未被设置（子类__new__未调用基类构造）时返回空串，
   避免把未初始化/空指针交给打印路径（见开发疑问记录84）。 */
void viola$lang$exception$Exception$what$_0(viola$lang$exception$Exception *_this,
                                            viola$lang$string **result,
                                            viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL || _this->message == NULL) {
        *result = viola$lang$string$fromCharString("");
        return;
    }
    *result = _this->message;
}

/* 数组下标越界：构造IndexError并上报到listener。
   生成的数组方法在越界时调用本函数后立即返回，调用方在同步调用之后
   读取listener->exception，异常由此传播到Viola层的try/catch
   （见开发疑问记录124与VIOLA_ARRAY_BOUNDS_CHECK）。 */
void viola$lang$exception$indexError(viola$lang$uint64 index, viola$lang$uint64 size,
                                     viola$threads$Listener *listener) {
    char buffer[128];
    viola$lang$string *message = NULL;
    viola$lang$exception$Exception *exc = NULL;
    if (listener == NULL) {
        /* 无监听器可上报（正常路径不会发生）：调用方仍会立即返回，
           不进行越界访问 */
        return;
    }
    snprintf(buffer, sizeof(buffer), "array index out of range: %llu (size: %llu)",
             (unsigned long long)index, (unsigned long long)size);
    message = viola$lang$string$fromCharString(buffer);
    viola$lang$exception$Exception$__new__$_0(message, &exc, listener);
    listener->exception = exc;
}

/* 析构异常 */
void viola$lang$exception$Exception$__del__$_0(viola$lang$exception$Exception *_this,
                                               viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount == 0) {
        if (_this->$parent) {
            viola$lang$uint32 *parentRefCount = (viola$lang$uint32 *)_this->$parent;
            (*parentRefCount)--;
        } else {
            if (_this->message != NULL) {
                viola$lang$string$__del__$_0(_this->message, NULL);
            }
            free(_this);
        }
    }
}
