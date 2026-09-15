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

/* 字符串相等比较（供编译器生成的按参数名传参代码使用） */
int viola$lang$string$equals(const viola$lang$string *a, const viola$lang$string *b);

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

/* ================= 0.1新增方法 ================= */
void viola$lang$string$count$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener);
void viola$lang$string$find$_0(viola$lang$string *_this, viola$lang$string *sub,
                               viola$lang$uint32 *result, viola$threads$Listener *listener);
void viola$lang$string$rfind$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener);
void viola$lang$string$index$_0(viola$lang$string *_this, viola$lang$string *sub,
                                viola$lang$uint32 *result, viola$threads$Listener *listener);
void viola$lang$string$rindex$_0(viola$lang$string *_this, viola$lang$string *sub,
                                 viola$lang$uint32 *result, viola$threads$Listener *listener);
void viola$lang$string$float$_0(viola$lang$string *_this, viola$lang$float64 *result,
                                viola$threads$Listener *listener);
void viola$lang$string$int$_0(viola$lang$string *_this, viola$lang$int64 *result,
                              viola$threads$Listener *listener);
void viola$lang$string$int$_1(viola$lang$string *_this, viola$lang$uint8 base,
                              viola$lang$int64 *result, viola$threads$Listener *listener);
void viola$lang$string$fromInt$_0(viola$lang$int64 value, viola$lang$string **result,
                                  viola$threads$Listener *listener);
void viola$lang$string$fromInt$_1(viola$lang$int64 value, viola$lang$uint8 base,
                                  viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$fromFloat$_0(viola$lang$float64 value, viola$lang$string **result,
                                    viola$threads$Listener *listener);
void viola$lang$string$isalnum$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$isalpha$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$isdecimal$_0(viola$lang$string *_this, viola$lang$bool *result,
                                    viola$threads$Listener *listener);
void viola$lang$string$isdigit$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$isidentifier$_0(viola$lang$string *_this, viola$lang$bool *result,
                                       viola$threads$Listener *listener);
void viola$lang$string$islower$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$isnumeric$_0(viola$lang$string *_this, viola$lang$bool *result,
                                    viola$threads$Listener *listener);
void viola$lang$string$isprintable$_0(viola$lang$string *_this, viola$lang$bool *result,
                                      viola$threads$Listener *listener);
void viola$lang$string$isspace$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$isupper$_0(viola$lang$string *_this, viola$lang$bool *result,
                                  viola$threads$Listener *listener);
void viola$lang$string$ljust$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string *fillChar, viola$lang$string **result,
                                viola$threads$Listener *listener);
void viola$lang$string$lstrip$_0(viola$lang$string *_this, viola$lang$string **result,
                                 viola$threads$Listener *listener);
void viola$lang$string$lstrip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                 viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$rjust$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string *fillChar, viola$lang$string **result,
                                viola$threads$Listener *listener);
void viola$lang$string$rstrip$_0(viola$lang$string *_this, viola$lang$string **result,
                                 viola$threads$Listener *listener);
void viola$lang$string$rstrip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                 viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$strip$_0(viola$lang$string *_this, viola$lang$string **result,
                                viola$threads$Listener *listener);
void viola$lang$string$strip$_1(viola$lang$string *_this, viola$lang$string *toRemove,
                                viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$swapcase$_0(viola$lang$string *_this, viola$lang$string **result,
                                   viola$threads$Listener *listener);
void viola$lang$string$zfill$_0(viola$lang$string *_this, viola$lang$uint32 length,
                                viola$lang$string **result, viola$threads$Listener *listener);
void viola$lang$string$replace$_1(viola$lang$string *_this, viola$lang$string *old,
                                  viola$lang$string *new, viola$lang$uint32 count,
                                  viola$lang$string **result, viola$threads$Listener *listener);

/* 值到字符串的转换（x.toString()按x的静态类型解析到这些静态函数，
   见开发疑问记录166）。参数为值本身，结果为新建的字符串。 */
void viola$lang$string$_int32ToString$_0(viola$lang$int32 value, viola$lang$string **result,
                                         viola$threads$Listener *listener);
void viola$lang$string$_int64ToString$_0(viola$lang$int64 value, viola$lang$string **result,
                                         viola$threads$Listener *listener);
void viola$lang$string$_uint32ToString$_0(viola$lang$uint32 value, viola$lang$string **result,
                                          viola$threads$Listener *listener);
void viola$lang$string$_uint64ToString$_0(viola$lang$uint64 value, viola$lang$string **result,
                                          viola$threads$Listener *listener);
void viola$lang$string$_float64ToString$_0(viola$lang$float64 value, viola$lang$string **result,
                                           viola$threads$Listener *listener);
void viola$lang$string$_boolToString$_0(viola$lang$bool value, viola$lang$string **result,
                                        viola$threads$Listener *listener);
void viola$lang$string$_stringToString$_0(viola$lang$string *value, viola$lang$string **result,
                                          viola$threads$Listener *listener);

#endif /* VIOLA_LANG_STRING_H */
