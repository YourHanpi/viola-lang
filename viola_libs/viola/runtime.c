/* -*- coding: utf-8 -*-
 * Viola运行时库基础实现：动态类型转换与元组共享析构。
 */
#include "runtime.h"

/* ================= 动态类型转换 ================= */

int viola$lang$convertibleTo(void *obj_vtable, void *target_vtable) {
    if (obj_vtable == NULL || target_vtable == NULL) {
        return 0;
    }
    viola$dynamic$TypeInfo *vtable = (viola$dynamic$TypeInfo *)obj_vtable;
    while (vtable != NULL) {
        if (vtable == (viola$dynamic$TypeInfo *)target_vtable) {
            return 1;
        }
        vtable = vtable->$parent;
    }
    return 0;
}

/* ================= 元组共享析构 ================= */
/* 所有元组结构体共享相同的前缀（$refCount、$parent、size），因此可用统一析构。 */
void viola$collections$Tuple$__del__(void *_this, viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$uint32 *refCount = (viola$lang$uint32 *)_this;
    void **parent = (void **)((char *)_this + sizeof(viola$lang$uint32));
    if (*refCount == 0) {
        if (*parent) {
            viola$lang$uint32 *parentRefCount = (viola$lang$uint32 *)*parent;
            (*parentRefCount)--;
        } else {
            free(_this);
        }
    }
}

/* ================= 切片析构 ================= */
void viola$lang$slice$__del__$_0(viola$lang$slice *_this, viola$threads$Listener *listener) {
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
