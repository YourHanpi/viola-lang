/* -*- coding: utf-8 -*-
 * Viola运行时库总头文件。
 *
 * 所有编译器生成的C代码都通过编译命令行的 -include 选项包含本文件，
 * 因此本文件提供所有生成代码依赖的类型定义、宏和函数声明。
 */
#ifndef VIOLA_RUNTIME_H
#define VIOLA_RUNTIME_H

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <signal.h>
#include <math.h>

/* ================= 基本数据类型 ================= */
typedef bool viola$lang$bool;
typedef int32_t viola$lang$int;
typedef int8_t viola$lang$int8;
typedef int16_t viola$lang$int16;
typedef int32_t viola$lang$int32;
typedef int64_t viola$lang$int64;
typedef uint32_t viola$lang$uint;
typedef uint8_t viola$lang$uint8;
typedef uint16_t viola$lang$uint16;
typedef uint32_t viola$lang$uint32;
typedef uint64_t viola$lang$uint64;
typedef float viola$lang$float;
typedef float viola$lang$float32;
typedef double viola$lang$float64;
typedef long double viola$lang$float128;
typedef double viola$lang$double;
typedef long double viola$lang$long_double;
typedef void *viola$lang$ptr;

/* 切片默认结束位置的最大值 */
#define I_SIZE_MAX ((viola$lang$uint64)-1)
/* 调试标记中的源文件路径（由编译器生成时未提供，暂以NULL代替） */
#define $$_PATH NULL

/* ================= 动态类型信息（虚函数表） ================= */
typedef struct viola$dynamic$TypeInfo {
    struct viola$dynamic$TypeInfo *$parent;
    void *vfunc;
} viola$dynamic$TypeInfo;

/* 判断对象类型是否为目标的子类型（沿$parent链查找） */
int viola$lang$convertibleTo(void *obj_vtable, void *target_vtable);

/* ================= 数组越界检查 ================= */
/* 数组下标访问（__getitem__/__setitem__）的越界检查由本符号控制：
   默认开启，越界时上报viola.lang.exception的IndexError（可被catch捕获）；
   以-DVIOLA_ARRAY_BOUNDS_CHECK=0编译可关闭该检查（关闭后越界访问为
   未定义行为，仅用于对性能敏感且已确认下标安全的场景）。
   见开发疑问记录124。 */
#ifndef VIOLA_ARRAY_BOUNDS_CHECK
#define VIOLA_ARRAY_BOUNDS_CHECK 1
#endif

/* ================= 对象基类 ================= */
/* 所有类实例以$refCount、$parent开头（用户类的结构体由编译器生成，
   并继承object的字段布局；此处提供object类型供元组等组合类型引用） */
typedef struct viola$lang$object {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
} viola$lang$object;

/* ================= 字符串 ================= */
typedef struct viola$lang$string {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint64 length;
    viola$lang$uint16 *data;
} viola$lang$string;

/* 从C字符串（UTF-8）创建Viola字符串 */
viola$lang$string *viola$lang$string$fromCharString(const char *str);
/* 将Viola字符串（UTF-16）转换为UTF-8的C字符串（调用方负责释放） */
char *viola$lang$string$toCharString(const viola$lang$string *str);
/* 数组解码接口（由__main__.c调用，返回argv元素对应的字符串） */
viola$lang$string *viola$lang$string$$array$decode(const char *str, const char *encoding);

/* ================= 切片 ================= */
typedef struct viola$lang$slice {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint64 start;
    viola$lang$uint64 end;
    viola$lang$uint64 step;
} viola$lang$slice;

/* ================= 异常 ================= */
typedef struct viola$lang$exception$Exception viola$lang$exception$Exception;
struct viola$lang$exception$Exception {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$ptr $$vtable;
    viola$lang$string *message;
};
extern viola$dynamic$TypeInfo viola$lang$exception$Exception$$vtable;

/* ================= 函数（Function） ================= */
/* 同步/异步函数指针的不透明类型（具体调用时按函数签名转换）。
   注：计划文档中的viola$lang$function$S$ / viola$lang$function$A$名称
   与按签名生成的函数指针typedef族（S$<args>$$R$<rets>）冲突，
   故采用AsyncPtr / SyncPtr命名（见开发疑问记录）。 */
typedef void (*viola$lang$function$SyncPtr)(void);
typedef void (*viola$lang$function$AsyncPtr)(void);

/* 字符串数组类型（viola$lang$string$$array，供Function.argNames使用；
   带include guard，与string.h中的定义互斥） */
#ifndef _VIOLA_ARRAY_T_viola$lang$string$$array
#define _VIOLA_ARRAY_T_viola$lang$string$$array
typedef struct viola$lang$string$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$string **data;
    viola$lang$uint64 size;
} viola$lang$string$$array;
#endif

/* 函数值结构体（原Closure，0.1起更名为Function并扩展）。
   所有函数（无论静态还是动态）作为值使用时均封装为本结构体；
   调用静态函数时仍然直接传递函数指针。 */
typedef struct viola$lang$function$Function {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$function$AsyncPtr *asyncPtr;
    viola$lang$function$SyncPtr *syncPtr;
    /* 捕获的环境（元组类型）。以$开头，避免被用户代码意外修改 */
    void *$capture;
    viola$lang$string$$array *argNames;
} viola$lang$function$Function;

/* ================= 元组（共享析构） ================= */
/* 具体的元组结构体由编译器按元素类型生成（成员为$0、$1等）；
   此处定义无元素的通用元组结构体前缀。 */
typedef struct viola$collections$Tuple {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint64 size;
} viola$collections$Tuple;
typedef struct viola$threads$Listener viola$threads$Listener;
void viola$collections$Tuple$__del__(void *_this, viola$threads$Listener *listener);

/* ================= 文件 ================= */
/* wrapper类的结构体定义由编译器按.vla中的wrapper class声明生成；此处给出
   正式定义，供运行库与生成代码共用（见开发疑问记录113）。编译器生成的同名
   定义带相同的include guard，二者不会冲突（本文件先行包含时以本定义为准）。
   修改viola.io/viola.os的wrapper类声明时，必须同步修改此处，否则两侧按
   不同的字段偏移读写。 */
#ifndef _VIOLA_CLASS_T_viola$io$file
#define _VIOLA_CLASS_T_viola$io$file
typedef struct viola$io$file {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$ptr $$vtable;
    void *fp;
    /* 是否为popen创建的文件（关闭时使用pclose而非fclose） */
    viola$lang$int32 isPopen;
} viola$io$file;
#endif

/* viola.os的wrapper类（字段与viola/os.vla中的声明一致） */
#ifndef _VIOLA_CLASS_T_viola$os$Stat
#define _VIOLA_CLASS_T_viola$os$Stat
typedef struct viola$os$Stat {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$ptr $$vtable;
    viola$lang$uint32 st_mode;
    viola$lang$uint64 st_ino;
    viola$lang$uint64 st_dev;
    viola$lang$uint64 st_nlink;
    viola$lang$uint32 st_uid;
    viola$lang$uint32 st_gid;
    viola$lang$uint64 st_size;
    viola$lang$uint64 st_atime;
    viola$lang$uint64 st_mtime;
    viola$lang$uint64 st_ctime;
} viola$os$Stat;
#endif
#ifndef _VIOLA_CLASS_T_viola$os$StatVFS
#define _VIOLA_CLASS_T_viola$os$StatVFS
typedef struct viola$os$StatVFS {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$ptr $$vtable;
    viola$lang$uint64 f_bsize;
    viola$lang$uint64 f_frsize;
    viola$lang$uint64 f_blocks;
    viola$lang$uint64 f_bfree;
    viola$lang$uint64 f_bavail;
    viola$lang$uint64 f_files;
    viola$lang$uint64 f_ffree;
    viola$lang$uint64 f_favail;
    viola$lang$uint64 f_flag;
    viola$lang$uint64 f_namemax;
} viola$os$StatVFS;
#endif

/* 本头文件内的数组类型（布局与编译器生成的数组结构体一致）。
   使用与编译器相同的include guard，避免与模块头文件中的typedef冲突 */
#ifndef _VIOLA_ARRAY_T_viola$lang$uint8$$array
#define _VIOLA_ARRAY_T_viola$lang$uint8$$array
typedef struct viola$lang$uint8$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint8 *data;
    viola$lang$uint64 size;
} viola$lang$uint8$$array;
#endif

/* ================= viola.io：标准输入输出与文件 ================= */
/* open()的默认参数全局变量（定义于viola/io/file.c） */
extern viola$lang$string *viola$io$file$open$$default$mode;
extern viola$lang$string *viola$io$file$open$$default$encoding;
/* print()/perror()的默认参数（content = ""，定义于viola/io/print.c） */
extern viola$lang$string *viola$io$print$print$$default$text;
extern viola$lang$string *viola$io$print$perror$$default$text;
void viola$io$print$print(viola$lang$string *content, viola$threads$Listener *listener);
void viola$io$print$perror(viola$lang$string *content, viola$threads$Listener *listener);
void viola$io$print$input(viola$lang$string **result, viola$threads$Listener *listener);
void viola$io$file$open(viola$lang$string *path, viola$lang$string *mode,
                   viola$lang$string *encoding, viola$io$file **f,
                   viola$threads$Listener *listener);
void viola$io$file$read(viola$io$file *file, viola$lang$string **result,
                   viola$threads$Listener *listener);
void viola$io$file$readBytes(viola$io$file *file, viola$lang$uint8$$array **result,
                        viola$threads$Listener *listener);
void viola$io$file$write(viola$io$file *file, viola$lang$string *content,
                    viola$threads$Listener *listener);
void viola$io$file$writeBytes(viola$io$file *file, viola$lang$uint8$$array *content,
                         viola$threads$Listener *listener);
void viola$io$file$__del__$_0(viola$io$file *_this, viola$threads$Listener *listener);
void viola$io$file$__new__$_0(viola$lang$string *path, viola$lang$string *mode,
                              viola$lang$string *encoding, viola$io$file **this,
                              viola$threads$Listener *listener);
/* 注册文件请求处理器（由全局资源管理器初始化时调用，实现于viola/io/file.c） */
void viola$io$registerFileHandlers(void);

/* ================= viola.os ================= */
/* 注册操作系统请求处理器（由全局资源管理器初始化时调用，实现于viola/os.c） */
void viola$os$registerOsHandlers(void);
/* 注册路径查询请求处理器（由全局资源管理器初始化时调用，实现于viola/os/path.c） */
void viola$os$path$registerPathHandlers(void);

/* ================= viola.lang ================= */
/* viola.lang.del内置实现（仅del(super)有意义，由编译器特殊处理；其余为空操作） */
void viola$lang$del(viola$lang$object *_this, viola$threads$Listener *listener);

/* ================= viola.lang.exception ================= */
void viola$lang$exception$Exception$__new__$_0(viola$lang$string *message,
                                               viola$lang$exception$Exception **this,
                                               viola$threads$Listener *listener);
/* 父类构造初始化（super = Exception(...)）：在子类已分配的对象上设置message，
   不重新分配对象、不覆盖子类vtable（见开发疑问记录107） */
void viola$lang$exception$Exception$__new__super$_0(viola$lang$string *message,
                                                    viola$lang$exception$Exception *this,
                                                    viola$threads$Listener *listener);
void viola$lang$exception$Exception$what$_0(viola$lang$exception$Exception *_this,
                                            viola$lang$string **result,
                                            viola$threads$Listener *listener);
void viola$lang$exception$Exception$__del__$_0(viola$lang$exception$Exception *_this,
                                               viola$threads$Listener *listener);
/* 数组下标越界：构造IndexError异常并写入listener->exception，供生成的数组
   方法在越界时上报（见开发疑问记录124与VIOLA_ARRAY_BOUNDS_CHECK） */
void viola$lang$exception$indexError(viola$lang$uint64 index, viola$lang$uint64 size,
                                     viola$threads$Listener *listener);
/* 数组切片范围非法（start > end）：构造异常并写入listener->exception，供生成的
   切片赋值（__setitem__$_1）在范围非法时上报（见开发疑问记录129） */
void viola$lang$exception$sliceError(viola$lang$uint64 start, viola$lang$uint64 end,
                                     viola$threads$Listener *listener);

/* ================= viola.lang.slice ================= */
void viola$lang$slice$__del__$_0(viola$lang$slice *_this, viola$threads$Listener *listener);

/* ================= viola.math ================= */
#define VIOLA_MATH_UNARY(name) \
    void viola$math$##name(viola$lang$float64 x, viola$lang$float64 *result, \
                           viola$threads$Listener *listener);
#define VIOLA_MATH_BINARY(name) \
    void viola$math$##name(viola$lang$float64 x, viola$lang$float64 y, \
                           viola$lang$float64 *result, viola$threads$Listener *listener);
VIOLA_MATH_UNARY(sqrt)
VIOLA_MATH_UNARY(sin)
VIOLA_MATH_UNARY(cos)
VIOLA_MATH_UNARY(tan)
VIOLA_MATH_UNARY(asin)
VIOLA_MATH_UNARY(acos)
VIOLA_MATH_UNARY(atan)
VIOLA_MATH_UNARY(sinh)
VIOLA_MATH_UNARY(cosh)
VIOLA_MATH_UNARY(tanh)
VIOLA_MATH_UNARY(exp)
VIOLA_MATH_UNARY(log)
VIOLA_MATH_UNARY(log10)
VIOLA_MATH_UNARY(log2)
VIOLA_MATH_UNARY(fabs)
VIOLA_MATH_UNARY(floor)
VIOLA_MATH_UNARY(ceil)
VIOLA_MATH_UNARY(round)
VIOLA_MATH_UNARY(trunc)
VIOLA_MATH_BINARY(pow)
VIOLA_MATH_BINARY(atan2)
VIOLA_MATH_BINARY(fmod)
VIOLA_MATH_BINARY(fmin)
VIOLA_MATH_BINARY(fmax)
#undef VIOLA_MATH_UNARY
#undef VIOLA_MATH_BINARY

/* ================= viola.os ================= */
void viola$os$sleep(viola$lang$uint64 milliseconds, viola$threads$Listener *listener);
void viola$os$exit(viola$lang$int32 code, viola$threads$Listener *listener);
void viola$os$getEnv(viola$lang$string *name, viola$lang$string **result,
                     viola$threads$Listener *listener);
void viola$os$time(viola$lang$uint64 *result, viola$threads$Listener *listener);
void viola$os$system(viola$lang$string *command, viola$lang$int32 *result,
                     viola$threads$Listener *listener);

/* ================= 线程调度 ================= */
#include "threads.h"

/* ================= 全局资源管理器 ================= */
#include "lang/global_resource_manager.h"

/* ================= 字符串 ================= */
#include "lang/string.h"

#endif /* VIOLA_RUNTIME_H */
