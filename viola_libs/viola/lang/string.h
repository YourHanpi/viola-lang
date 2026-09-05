/* -*- coding: utf-8 -*-
 * Viola字符串运行库声明。
 * 命名空间：viola.lang.string（C标识符前缀 viola$lang$string$）。
 */
#ifndef VIOLA_LANG_STRING_H
#define VIOLA_LANG_STRING_H

#include "../runtime.h"

/* 数组类型（布局与编译器生成的数组结构体一致，使用相同guard避免冲突） */
#ifndef _VIOLA_ARRAY_T_viola$lang$string$$array
#define _VIOLA_ARRAY_T_viola$lang$string$$array
typedef struct viola$lang$string$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$string **data;
    viola$lang$uint64 size;
} viola$lang$string$$array;
#endif

#ifndef _VIOLA_ARRAY_T_viola$lang$uint16$$array
#define _VIOLA_ARRAY_T_viola$lang$uint16$$array
typedef struct viola$lang$uint16$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint16 *data;
    viola$lang$uint64 size;
} viola$lang$uint16$$array;
#endif

/* 字符串方法（实现于string.c） */
void viola$lang$string$__new__$_0(viola$lang$ptr data, viola$lang$string **this,
                                  viola$threads$Listener *listener);
void viola$lang$string$__del__$_0(viola$lang$string *_this, viola$threads$Listener *listener);
void viola$lang$string$__add__$_0(viola$lang$string *_this, viola$lang$string *s,
                                  viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$__eq__$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$__getitem__$_0(viola$lang$string *_this, viola$lang$int64 index,
                                      viola$lang$string **ch, viola$threads$Listener *listener);
void viola$lang$string$__getitem__$_1(viola$lang$string *_this, viola$lang$slice *s,
                                      viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$__mul__$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                  viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$__ne__$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$__rmul__$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                   viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$concat$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$endswith$_0(viola$lang$string *_this, viola$lang$string *s,
                                   viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$endsWith$_0(viola$lang$string *_this, viola$lang$string *s,
                                   viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$isascii$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$join$_0(viola$lang$string *_this, viola$lang$string$$array *s,
                               viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$length$_0(viola$lang$string *_this, viola$lang$uint64 *result,
                                 viola$threads$Listener *listener);
void viola$lang$string$lower$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener);
void viola$lang$string$replace$_0(viola$lang$string *_this, viola$lang$string *old,
                                  viola$lang$string *new, viola$lang$string **result,
                                  viola$threads$Listener *listener);
void viola$lang$string$repeat$_0(viola$lang$string *_this, viola$lang$uint64 times,
                                 viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$rsplit$_0(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$string$$array **results,
                                 viola$threads$Listener *listener);
void viola$lang$string$rsplit$_1(viola$lang$string *_this, viola$lang$string *s,
                                 viola$lang$uint64 maxsplit, viola$lang$string$$array **results,
                                 viola$threads$Listener *listener);
void viola$lang$string$slice$_0(viola$lang$string *_this, viola$lang$int64 start,
                                viola$lang$int64 end, viola$lang$string **result,
                                viola$threads$Listener *listener);
void viola$lang$string$split$_0(viola$lang$string *_this, viola$lang$string *s,
                                viola$lang$string$$array **results,
                                viola$threads$Listener *listener);
void viola$lang$string$split$_1(viola$lang$string *_this, viola$lang$string *s,
                                viola$lang$uint64 maxsplit, viola$lang$string$$array **results,
                                viola$threads$Listener *listener);
void viola$lang$string$startswith$_0(viola$lang$string *_this, viola$lang$string *s,
                                     viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$startsWith$_0(viola$lang$string *_this, viola$lang$string *s,
                                     viola$lang$bool *result, viola$threads$Listener *listener);
void viola$lang$string$unicode$_0(viola$lang$string *_this, viola$lang$uint16$$array **result,
                                  viola$threads$Listener *listener);
void viola$lang$string$upper$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener);

#endif /* VIOLA_LANG_STRING_H */
