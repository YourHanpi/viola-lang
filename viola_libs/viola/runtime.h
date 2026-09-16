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
/* Viola源代码中的int是int32的别名，编译器生成的C代码一律使用
   viola$lang$int32（见开发疑问记录151）；本类型保留供手写C代码使用。 */
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
/* 虚方法槽位：同步实现与异步包装各一个函数指针。
   槽位下标由基类的方法声明顺序决定，子类重写的方法占用同一槽位，
   因此以基类类型引用派生类对象时按对象的实际类型分派
   （见开发疑问记录161）。 */
typedef struct viola$dynamic$VFuncSlot {
    void *$sync;   /* 同步实现（方法C名称） */
    void *$async;  /* 异步包装（方法C名称 + "$async"） */
} viola$dynamic$VFuncSlot;

/* 接口条目：某个类（的TypeInfo）对某接口提供的槽位数组。
   接口不在类的继承链上（一个类可实现多个接口），故接口的实现单独列在此表中，
   槽位下标由接口自身的方法顺序决定，因而同一个接口在各类中的下标一致
   （见开发疑问记录170(c)）。 */
typedef struct viola$dynamic$InterfaceEntry {
    struct viola$dynamic$TypeInfo *$interface;  /* 接口的类型信息 */
    viola$dynamic$VFuncSlot *vfunc;             /* 该类对应该接口的槽位数组 */
} viola$dynamic$InterfaceEntry;

typedef struct viola$dynamic$TypeInfo {
    struct viola$dynamic$TypeInfo *$parent;
    viola$dynamic$VFuncSlot *vfunc;  /* 虚方法槽位数组；无虚方法时为NULL */
    /* 虚析构入口：签名与析构函数一致（void (*)(<类> *, viola$threads$Listener *)）。
       编译器生成的析构函数在开头比较对象的$$vtable与自身的TypeInfo：不同则经此
       转交对象的实际类型的析构函数，从而实现虚析构（见开发疑问记录170(a)）。 */
    void *$del;
    /* 类的名称（UTF-8的C字符串，由编译器在__global__中写入）。未定义toString的类
       由默认转换返回该名称（见开发疑问记录175(b)）。 */
    const char *$name;
    /* 本类型实现的接口条目数组，以$interface为NULL的条目结尾；
       未实现任何接口时为NULL（见开发疑问记录170(c)）。 */
    const viola$dynamic$InterfaceEntry *$interfaces;
} viola$dynamic$TypeInfo;

/* 判断对象类型是否为目标的子类型（沿$parent链与接口表查找） */
int viola$lang$convertibleTo(void *obj_vtable, void *target_vtable);
/* 取某类型对某接口提供的槽位数组（无则返回NULL）。
   供接口类型的接收者上的方法调用按接口的槽位下标分派（见开发疑问记录170(c)）。 */
viola$dynamic$VFuncSlot *viola$lang$interfaceVfunc(void *vtable, void *interface_vtable);
/* 取对象的类名（未参与虚分派或无名字时返回"object"），供默认的toString使用 */
const char *viola$lang$objectTypeName(viola$lang$ptr object);

/* ================= 数组越界检查 ================= */
/* 数组下标访问（__getitem__/__setitem__）的越界检查由本符号控制：
   默认开启，越界时上报viola.lang.exception的IndexError（可被catch捕获）；
   以-DVIOLA_ARRAY_BOUNDS_CHECK=0编译可关闭该检查（关闭后越界访问为
   未定义行为，仅用于对性能敏感且已确认下标安全的场景）。
   见开发疑问记录124。 */
#ifndef VIOLA_ARRAY_BOUNDS_CHECK
#define VIOLA_ARRAY_BOUNDS_CHECK 1
#endif

/* ================= 原子引用计数 ================= */
/* 对象的引用计数$refCount以系统提供的原子设施进行增减：多线程（viola.thread）
   可并发持有同一对象，非原子的计数会发生丢失更新，进而导致提前释放或重复释放
   （见versions_dev_plan_zh.md"漏洞修复"）。
   各编译环境下所用的系统原子设施：
     - C11及以上的C：_Atomic（<stdatomic.h>）与atomic_fetch_*_explicit；
     - C++11及以上：std::atomic（<atomic>）；
     - 其它（C99等）：GCC/Clang的__atomic内建函数、MSVC的_Interlocked内建函数。
   无论采用哪一种，viola$lang$atomic_uint32的大小与对齐都与viola$lang$uint32相同，
   故各结构体的布局（以及编译器侧的结构体布局校验）不受影响。 */
#if defined(__cplusplus) && (__cplusplus >= 201103L)
#include <atomic>
typedef std::atomic<viola$lang$uint32> viola$lang$atomic_uint32;
#define VIOLA_REFCOUNT_ADD_FETCH(p, value) ((p)->fetch_add((value), std::memory_order_seq_cst) + (value))
#define VIOLA_REFCOUNT_SUB_FETCH(p, value) ((p)->fetch_sub((value), std::memory_order_seq_cst) - (value))
#define VIOLA_REFCOUNT_LOAD(p) ((p)->load(std::memory_order_seq_cst))
#define VIOLA_REFCOUNT_STORE(p, value) ((p)->store((value), std::memory_order_seq_cst))
#elif (defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)) \
    || (defined(__GNUC__) && (__GNUC__ >= 5))
/* GCC/Clang在C99等更早的标准模式下也提供_Atomic与<stdatomic.h>扩展 */
#include <stdatomic.h>
typedef _Atomic viola$lang$uint32 viola$lang$atomic_uint32;
/* atomic_fetch_*返回的是操作前的值，而refcount_inc/dec约定"返回操作后的值"
   （dec返回0即本次递减丢弃了最后一个引用），故在此补齐差值。
   其余分支（C++的fetch_add、MSVC的_InterlockedExchangeAdd、退化分支的复合赋值）
   本来就返回操作后的值，四个分支的语义由此一致。 */
#define VIOLA_REFCOUNT_ADD_FETCH(p, value) (atomic_fetch_add_explicit((p), (value), memory_order_seq_cst) + (value))
#define VIOLA_REFCOUNT_SUB_FETCH(p, value) (atomic_fetch_sub_explicit((p), (value), memory_order_seq_cst) - (value))
#define VIOLA_REFCOUNT_LOAD(p) atomic_load_explicit((p), memory_order_seq_cst)
#define VIOLA_REFCOUNT_STORE(p, value) atomic_store_explicit((p), (value), memory_order_seq_cst)
#elif defined(_MSC_VER)
#include <intrin.h>
typedef volatile viola$lang$uint32 viola$lang$atomic_uint32;
#define VIOLA_REFCOUNT_ADD_FETCH(p, value) ((viola$lang$uint32)(_InterlockedExchangeAdd((volatile long *)(p), \
    (long)(value)) + (long)(value)))
#define VIOLA_REFCOUNT_SUB_FETCH(p, value) ((viola$lang$uint32)(_InterlockedExchangeAdd((volatile long *)(p), \
    -(long)(value)) - (long)(value)))
#define VIOLA_REFCOUNT_LOAD(p) (*(p))
#define VIOLA_REFCOUNT_STORE(p, value) (*(p) = (value))
#else
typedef viola$lang$uint32 viola$lang$atomic_uint32;
#define VIOLA_REFCOUNT_ADD_FETCH(p, value) (*(p) += (value))
#define VIOLA_REFCOUNT_SUB_FETCH(p, value) (*(p) -= (value))
#define VIOLA_REFCOUNT_LOAD(p) (*(p))
#define VIOLA_REFCOUNT_STORE(p, value) (*(p) = (value))
#endif

/* 增减引用计数（返回操作后的值） */
static inline viola$lang$uint32 viola$lang$refcount_inc(viola$lang$atomic_uint32 *ref_count) {
    return VIOLA_REFCOUNT_ADD_FETCH(ref_count, 1);
}

/* 递减引用计数，返回递减后的值：返回0表示此次递减丢弃了最后一个引用，
   调用方应随即释放对象。整个"递减并判断是否归零"是一次原子操作，
   避免两个线程各自递减后都读到0而重复释放（见versions_dev_plan_zh.md"漏洞修复"）。 */
static inline viola$lang$uint32 viola$lang$refcount_dec(viola$lang$atomic_uint32 *ref_count) {
    return VIOLA_REFCOUNT_SUB_FETCH(ref_count, 1);
}

/* 读取引用计数 */
static inline viola$lang$uint32 viola$lang$refcount_get(const viola$lang$atomic_uint32 *ref_count) {
    return VIOLA_REFCOUNT_LOAD(ref_count);
}

/* 写入引用计数（仅在对象尚未被其他线程共享时使用，如分配点） */
static inline void viola$lang$refcount_set(viola$lang$atomic_uint32 *ref_count, viola$lang$uint32 value) {
    VIOLA_REFCOUNT_STORE(ref_count, value);
}

/* 容器（数组）元素的持有与释放：元素存入容器时计一次数，容器析构时递减。
   编译器按元素类型选用下面的一对宏——对象元素用VIOLA_ELEM_RETAIN，
   基本类型元素（无$refCount）用VIOLA_ELEM_RETAIN_NOOP（求值后丢弃）。
   计数按"$refCount位于对象首字段（偏移0）"直接取址，而不写成(e)->$refCount：
   数组方法的实现生成在__main__.c中，彼时元素类型通常只有前向声明，按成员名
   访问会报"invalid use of incomplete typedef"（见开发疑问记录190）。
   该布局由runtime.h"对象基类"保证，runtime.c的元组析构也是同样做法。 */
#define VIOLA_ELEM_RETAIN(e) do { \
    if ((e)) { viola$lang$refcount_inc((viola$lang$atomic_uint32 *)(void *)(e)); } \
} while (0)
#define VIOLA_ELEM_RETAIN_NOOP(e) ((void)(e))

/* ================= 对象基类 ================= */
/* 所有类实例以$refCount、$parent开头（用户类的结构体由编译器生成，
   并继承object的字段布局；此处提供object类型供元组等组合类型引用） */
typedef struct viola$lang$object {
    viola$lang$atomic_uint32 $refCount;
    viola$lang$ptr $parent;
} viola$lang$object;

/* ================= 字符串 ================= */
typedef struct viola$lang$string {
    viola$lang$atomic_uint32 $refCount;
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
    viola$lang$atomic_uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint64 start;
    viola$lang$uint64 end;
    viola$lang$uint64 step;
} viola$lang$slice;

/* ================= 异常 ================= */
typedef struct viola$lang$exception$Exception viola$lang$exception$Exception;
struct viola$lang$exception$Exception {
    viola$lang$atomic_uint32 $refCount;
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
    viola$lang$atomic_uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$string **data;
    viola$lang$uint64 size;
} viola$lang$string$$array;
#endif

/* 函数值结构体（原Closure，0.1起更名为Function并扩展）。
   所有函数（无论静态还是动态）作为值使用时均封装为本结构体；
   调用静态函数时仍然直接传递函数指针。 */
typedef struct viola$threads$Listener viola$threads$Listener;
typedef struct viola$lang$function$Function {
    viola$lang$atomic_uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$function$AsyncPtr *asyncPtr;
    viola$lang$function$SyncPtr *syncPtr;
    /* 捕获的环境（元组类型）。以$开头，避免被用户代码意外修改 */
    void *$capture;
    viola$lang$string$$array *argNames;
    /* 捕获环境的释放入口：由编译器为每个闭包生成（释放$capture中的对象成员
       并free捕获结构体自身，见开发疑问记录195）；静态函数封装为Function值时
       $capture为NULL、本指针也为NULL。形参写成void *，以免依赖Listener类型
       在本头文件中的声明顺序 */
    void (*$captureDel)(void *, void *);
} viola$lang$function$Function;

/* 函数值（Function结构体）的析构：释放捕获环境、形参名数组与结构体自身。
   编译器生成的释放代码在引用计数归零后调用本函数（见开发疑问记录195：
   此前函数值从不释放，捕获结构体与其捕获的对象成员都随之泄漏）。 */
void viola$lang$function$__del__(viola$lang$function$Function *_this, viola$threads$Listener *listener);

/* ================= 元组 ================= */
/* 具体的元组结构体由编译器按元素类型生成（成员为$0、$1等，析构函数按元素类型
   单态化，见开发疑问记录192）；此处定义所有元组共有的前缀，顺序为
   $refCount、$parent、size、$del。
   $del指向该元组具体类型的析构函数（元素类型为对象时需逐个释放成员，故析构
   必须按类型单态化），由编译器在元组的分配处写入。释放元组的代码一律调用
   固定名字的viola$collections$Tuple$__del__转发：这样释放代码的文本不含元素
   类型名，可以在泛型函数体（彼时类型仍是占位符，如Tuple$U）中提前渲染而不会
   引用到不存在的符号（泛型体的释放代码在语句加入块时渲染、实例化后复用）。 */
typedef struct viola$collections$Tuple {
    viola$lang$atomic_uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$uint64 size;
    void (*$del)(void *_this, viola$threads$Listener *listener);
} viola$collections$Tuple;
void viola$collections$Tuple$__del__(void *_this, viola$threads$Listener *listener);

/* object类型的析构。编译器为object注册了__del__（见symbol.py的Object.add_method），
   静态类型为object的值被释放时会调用它（如object[]的元素、object类型的变量）。
   object没有$$vtable（不参与虚分派），故只递减计数并在归零时回收结构体；
   实际类型为派生类的对象在此按静态类型（object）释放，派生类成员不会随之释放
   （与"按变量的静态类型调用析构"的既有约定一致，见开发疑问记录190）。 */
void viola$lang$object$__del__$_0(viola$lang$object *_this, viola$threads$Listener *listener);

/* ================= 文件 ================= */
/* wrapper类的结构体定义由编译器按.vla中的wrapper class声明生成；此处给出
   正式定义，供运行库与生成代码共用（见开发疑问记录113）。编译器生成的同名
   定义带相同的include guard，二者不会冲突（本文件先行包含时以本定义为准）。
   修改viola.io/viola.os的wrapper类声明时，必须同步修改此处，否则两侧按
   不同的字段偏移读写。 */
#ifndef _VIOLA_CLASS_T_viola$io$file
#define _VIOLA_CLASS_T_viola$io$file
typedef struct viola$io$file {
    viola$lang$atomic_uint32 $refCount;
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
    viola$lang$atomic_uint32 $refCount;
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
    viola$lang$atomic_uint32 $refCount;
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
    viola$lang$atomic_uint32 $refCount;
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
/* 数组切片步长为0：构造异常并写入listener->exception，供生成的切片访问
   （__getitem__$_1）上报——步长为0时元素个数计算会除以0，取值为0与变量时
   均可达（见开发疑问记录135） */
void viola$lang$exception$sliceStepError(viola$lang$uint64 step,
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
