/* -*- coding: utf-8 -*-
 * Viola运行时库基础实现：动态类型转换与元组共享析构。
 */
#include "runtime.h"

/* ================= 内置释放函数 ================= */

/* viola.lang.del的内置实现。
   仅有意义的用法是del(super);（wrapper类__del__中释放普通成员），
   该形式由编译器直接生成当前类的$__del__super$_0调用；
   其余形式的del调用到达本函数时为原生空操作。 */
void viola$lang$del(viola$lang$object *_this, viola$threads$Listener *listener) {
    (void)_this;
    (void)listener;
}

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
