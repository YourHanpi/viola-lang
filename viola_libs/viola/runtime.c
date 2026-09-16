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

/* 目标是否为obj_vtable（沿$parent链）实现的接口（见开发疑问记录170(c)）。
   接口条目中的接口自身也可以继承接口，故沿接口的$parent链查找。 */
static int viola$lang$implementsInterface(viola$dynamic$TypeInfo *obj_vtable,
                                          viola$dynamic$TypeInfo *target_vtable) {
    while (obj_vtable != NULL) {
        const viola$dynamic$InterfaceEntry *entry = obj_vtable->$interfaces;
        while (entry != NULL && entry->$interface != NULL) {
            if (entry->$interface == target_vtable ||
                    viola$lang$convertibleTo(entry->$interface, target_vtable)) {
                return 1;
            }
            entry++;
        }
        obj_vtable = obj_vtable->$parent;
    }
    return 0;
}

int viola$lang$convertibleTo(void *obj_vtable, void *target_vtable) {
    viola$dynamic$TypeInfo *vtable;
    if (obj_vtable == NULL || target_vtable == NULL) {
        return 0;
    }
    vtable = (viola$dynamic$TypeInfo *)obj_vtable;
    while (vtable != NULL) {
        if (vtable == (viola$dynamic$TypeInfo *)target_vtable) {
            return 1;
        }
        vtable = vtable->$parent;
    }
    return viola$lang$implementsInterface((viola$dynamic$TypeInfo *)obj_vtable,
                                          (viola$dynamic$TypeInfo *)target_vtable);
}

viola$dynamic$VFuncSlot *viola$lang$interfaceVfunc(void *vtable, void *interface_vtable) {
    viola$dynamic$TypeInfo *type_info = (viola$dynamic$TypeInfo *)vtable;
    viola$dynamic$TypeInfo *target = (viola$dynamic$TypeInfo *)interface_vtable;
    while (type_info != NULL) {
        const viola$dynamic$InterfaceEntry *entry = type_info->$interfaces;
        while (entry != NULL && entry->$interface != NULL) {
            if (entry->$interface == target ||
                    viola$lang$convertibleTo(entry->$interface, target)) {
                return entry->vfunc;
            }
            entry++;
        }
        type_info = type_info->$parent;
    }
    return NULL;
}

/* 取对象的类名（供未定义toString的类的默认转换使用，见开发疑问记录175(b)）。
   编译器生成的类实例的第2个指针成员是$$vtable（布局：$refCount、$parent、$$vtable）；
   未参与虚分派（$$vtable为NULL）或无名字时返回"object"。 */
const char *viola$lang$objectTypeName(viola$lang$ptr object) {
    viola$dynamic$TypeInfo *type_info;
    if (object == NULL) {
        return "object";
    }
    type_info = ((viola$dynamic$TypeInfo **)object)[2];
    if (type_info == NULL || type_info->$name == NULL) {
        return "object";
    }
    return type_info->$name;
}

/* ================= 元组析构转发 ================= */
/* 所有元组结构体共享相同的前缀（$refCount、$parent、size、$del），故可在此
   统一转发到该元组具体类型的析构函数（$del，由编译器在分配处写入；元素类型为
   对象时需逐个释放成员，故析构按元素类型单态化，见开发疑问记录192）。
   编译器生成的释放代码只引用本固定名字，不引用具体类型的析构函数名。 */
void viola$collections$Tuple$__del__(void *_this, viola$threads$Listener *listener) {
    viola$collections$Tuple *tuple = (viola$collections$Tuple *)_this;
    if (tuple == NULL || tuple->$del == NULL) {
        return;
    }
    tuple->$del(_this, listener);
}

/* ================= object析构 ================= */
void viola$lang$object$__del__$_0(viola$lang$object *_this, viola$threads$Listener *listener) {
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
