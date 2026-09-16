/* -*- coding: utf-8 -*-
 * Viola异常运行库实现。
 * 命名空间：viola.lang.exception（C标识符前缀 viola$lang$exception$）。
 */
#include "string.h"

/* 异常基类的析构函数（前置声明：下面的TypeInfo需要取其地址） */
void viola$lang$exception$Exception$__del__$_0(viola$lang$exception$Exception *_this,
                                               viola$threads$Listener *listener);

/* 释放一个局部持有的字符串（定义见下）：what()在拼接多个异常消息时使用 */
static void releaseString(viola$lang$string *str);

/* 异常基类的TypeInfo（子类的$parent链指向此处）。
   $del为虚析构入口（见开发疑问记录170(a)）；$name为类名（见开发疑问记录175(b)）；
   异常类不实现接口，故$interfaces为NULL（见开发疑问记录170(c)） */
viola$dynamic$TypeInfo viola$lang$exception$Exception$$vtable = {
    NULL, NULL, (void *)&viola$lang$exception$Exception$__del__$_0, "exception.Exception", NULL};

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
    exc->$suppressed = NULL;
    exc->$suppressedNext = NULL;
    /* 成员持有message：计一次数（调用方随后释放自己的实参槽位）。
       与析构中的递减成对（见开发疑问记录190）。 */
    exc->message = message;
    if (exc->message != NULL) {
        viola$lang$refcount_inc(&exc->message->$refCount);
    }
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
    if (this->message != NULL) {
        viola$lang$refcount_inc(&this->message->$refCount);
    }
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
    /* 返回值槽位成为新的持有者：该槽位释放时会递减，故此处先计一次数，
       否则调用方释放返回值时会把异常仍在使用中的message释放掉
       （见开发疑问记录190）。 */
    *result = _this->message;
    viola$lang$refcount_inc(&(*result)->$refCount);
    if (_this->$suppressed != NULL) {
        /* 同时存在多个异常（被抑制的异常链，见开发疑问记录196）：
           把它们的消息一并追加，使报告处一次给出全部报错。 */
        viola$lang$exception$Exception *item = _this->$suppressed;
        viola$lang$string *separator = viola$lang$string$fromCharString("\n\tcaused by: ");
        while (item != NULL) {
            if (item->message != NULL) {
                viola$lang$string *joined = NULL;
                viola$lang$string$__add__$_0(*result, separator, &joined, listener);
                releaseString(*result);
                *result = joined;
                viola$lang$string$__add__$_0(*result, item->message, &joined, listener);
                releaseString(*result);
                *result = joined;
            }
            item = item->$suppressedNext;
        }
        releaseString(separator);
    }
}

/* 抑制一个异常：在primary已在传播时，把与其同时出现的extra挂到primary上
   （按出现顺序追加到链表尾部），随primary一同报告与释放（见开发疑问记录196）。
   extra的所有权转入链表中，调用方不再持有。 */
void viola$lang$exception$suppress(viola$lang$exception$Exception *primary,
                                   viola$lang$exception$Exception *extra) {
    viola$lang$exception$Exception *tail = NULL;
    if (primary == NULL || extra == NULL || primary == extra) {
        return;
    }
    tail = primary;
    while (tail->$suppressedNext != NULL) {
        if (tail->$suppressedNext == extra) {
            /* 已在链上，不重复挂接 */
            return;
        }
        tail = tail->$suppressedNext;
    }
    tail->$suppressedNext = extra;
    extra->$suppressedNext = NULL;
    primary->$suppressed = primary->$suppressedNext;
    /* 链表持有extra：计一次数，其释放由primary的析构负责 */
    viola$lang$refcount_inc(&extra->$refCount);
}

/* 释放一个局部持有的字符串：递减计数，归零则析构（见开发疑问记录190）。
   与编译器生成的释放代码同一语义，供本文件中手工管理的局部槽位使用。 */
static void releaseString(viola$lang$string *str) {
    if (str != NULL && viola$lang$refcount_dec(&str->$refCount) == 0) {
        viola$lang$string$__del__$_0(str, NULL);
    }
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
    /* 构造已retain该message：局部槽位不再持有，释放之，否则只增不减而泄漏
       （见开发疑问记录190） */
    releaseString(message);
    message = NULL;
    listener->exception = exc;
}

/* 数组切片范围非法（start > end）：构造异常并上报到listener。
   生成的__setitem__$_1（切片赋值）在start > end时调用本函数后立即返回；
   该情形原先使长度计算的新长度按uint64下溢（size - (end - start)），
   随后的malloc通常失败并解引用空指针（见开发疑问记录129）。 */
void viola$lang$exception$sliceError(viola$lang$uint64 start, viola$lang$uint64 end,
                                     viola$threads$Listener *listener) {
    char buffer[128];
    viola$lang$string *message = NULL;
    viola$lang$exception$Exception *exc = NULL;
    if (listener == NULL) {
        /* 无监听器可上报（正常路径不会发生）：调用方仍会立即返回，
           不进行非法范围的计算与分配 */
        return;
    }
    snprintf(buffer, sizeof(buffer), "array slice range is invalid: start %llu > end %llu",
             (unsigned long long)start, (unsigned long long)end);
    message = viola$lang$string$fromCharString(buffer);
    viola$lang$exception$Exception$__new__$_0(message, &exc, listener);
    /* 构造已retain该message：局部槽位不再持有，释放之，否则只增不减而泄漏
       （见开发疑问记录190） */
    releaseString(message);
    message = NULL;
    listener->exception = exc;
}

/* 数组切片步长为0：构造异常并上报到listener。
   生成的__getitem__$_1（切片访问）在step == 0时调用本函数后返回空结果；
   该情形原先使元素个数计算 (end - start + step - 1) / step 除以0
   （整数除零，x86上触发SIGFPE），且步长为0时遍历循环永不结束
   （见开发疑问记录135）。 */
void viola$lang$exception$sliceStepError(viola$lang$uint64 step,
                                         viola$threads$Listener *listener) {
    char buffer[128];
    viola$lang$string *message = NULL;
    viola$lang$exception$Exception *exc = NULL;
    if (listener == NULL) {
        /* 无监听器可上报（正常路径不会发生）：调用方仍会立即返回空结果，
           不进行除以0的计算与遍历 */
        return;
    }
    snprintf(buffer, sizeof(buffer), "array slice step must not be 0: step %llu",
             (unsigned long long)step);
    message = viola$lang$string$fromCharString(buffer);
    viola$lang$exception$Exception$__new__$_0(message, &exc, listener);
    /* 构造已retain该message：局部槽位不再持有，释放之，否则只增不减而泄漏
       （见开发疑问记录190） */
    releaseString(message);
    message = NULL;
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
            /* message成员失去一个持有者：与构造中的retain成对
               （见开发疑问记录190）。直接调用string析构而不递减会使计数永不
               归零，message（含其data缓冲区）随异常一起泄漏。 */
            if (_this->message != NULL
                && viola$lang$refcount_dec(&_this->message->$refCount) == 0) {
                viola$lang$string$__del__$_0(_this->message, NULL);
            }
            /* 被抑制的异常链随本异常一同释放（见开发疑问记录196）：
               链上的每个异常由suppress计过一次数，此处递减并递归释放 */
            {
                viola$lang$exception$Exception *item = _this->$suppressedNext;
                _this->$suppressed = NULL;
                _this->$suppressedNext = NULL;
                while (item != NULL) {
                    viola$lang$exception$Exception *next = item->$suppressedNext;
                    item->$suppressedNext = NULL;
                    if (viola$lang$refcount_dec(&item->$refCount) == 0) {
                        viola$lang$exception$Exception$__del__$_0(item, NULL);
                    }
                    item = next;
                }
            }
            free(_this);
        }
    }
}
