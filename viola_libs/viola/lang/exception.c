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
