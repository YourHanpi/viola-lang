/* 本文件由build_tools/lib_tools/gen_async_wrappers.py生成，请勿手工修改。
 * 为原生（声明式）函数提供$async实现与相关的元组/数组结构体
 * （见开发疑问记录106）。 */
#include "runtime.h"

#ifndef _VIOLA_ARRAY_T_viola$lang$float64$$array
#define _VIOLA_ARRAY_T_viola$lang$float64$$array
typedef struct viola$lang$float64$$array {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$float64 data;
	viola$lang$uint64 size;
} viola$lang$float64$$array;
#endif

#ifndef _VIOLA_ARRAY_T_viola$lang$uint8$$array
#define _VIOLA_ARRAY_T_viola$lang$uint8$$array
typedef struct viola$lang$uint8$$array {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint8 data;
	viola$lang$uint64 size;
} viola$lang$uint8$$array;
#endif

#ifndef _VIOLA_ARRAY_T_viola$lang$string$$array
#define _VIOLA_ARRAY_T_viola$lang$string$$array
typedef struct viola$lang$string$$array {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$string ** data;
	viola$lang$uint64 size;
} viola$lang$string$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$float64  $0;

} viola$collections$Tuple$viola$lang$float64;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$viola$lang$float64
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$viola$lang$float64
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$float64  $0;
	viola$lang$float64  $1;

} viola$collections$Tuple$viola$lang$float64$viola$lang$float64;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$uint32  $0;

} viola$collections$Tuple$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint64
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint64
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$uint64  $0;

} viola$collections$Tuple$viola$lang$uint64;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$viola$lang$int32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$viola$lang$int32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$float64  $0;
	viola$lang$int32  $1;

} viola$collections$Tuple$viola$lang$float64$viola$lang$int32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int64$viola$lang$int64
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int64$viola$lang$int64
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int64  $0;
	viola$lang$int64  $1;

} viola$collections$Tuple$viola$lang$int64$viola$lang$int64;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int64
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int64
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int64  $0;

} viola$collections$Tuple$viola$lang$int64;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$uint32  $0;
	viola$lang$uint32  $1;

} viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$$array
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$$array
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$float64$$array *  $0;

} viola$collections$Tuple$viola$lang$float64$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$$array$viola$lang$float64$$array
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$float64$$array$viola$lang$float64$$array
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$float64$$array *  $0;
	viola$lang$float64$$array *  $1;

} viola$collections$Tuple$viola$lang$float64$$array$viola$lang$float64$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$bool
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$bool
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$bool  $0;

} viola$collections$Tuple$viola$lang$bool;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;

} viola$collections$Tuple$viola$lang$string;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$
#define _VIOLA_TUPLE_T_viola$collections$Tuple$
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;

} viola$collections$Tuple$;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$object
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$object
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$object *  $0;

} viola$collections$Tuple$viola$lang$object;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$string$viola$lang$string
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$string$viola$lang$string
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;
	viola$lang$string *  $1;
	viola$lang$string *  $2;

} viola$collections$Tuple$viola$lang$string$viola$lang$string$viola$lang$string;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$io$file *  $0;

} viola$collections$Tuple$viola$io$file;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint8$$array
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$uint8$$array
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$uint8$$array *  $0;

} viola$collections$Tuple$viola$lang$uint8$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file$viola$lang$string
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file$viola$lang$string
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$io$file *  $0;
	viola$lang$string *  $1;

} viola$collections$Tuple$viola$io$file$viola$lang$string;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file$viola$lang$uint8$$array
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$io$file$viola$lang$uint8$$array
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$io$file *  $0;
	viola$lang$uint8$$array *  $1;

} viola$collections$Tuple$viola$io$file$viola$lang$uint8$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;
	viola$lang$uint32  $1;

} viola$collections$Tuple$viola$lang$string$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;
	viola$lang$uint32  $1;
	viola$lang$uint32  $2;

} viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;

} viola$collections$Tuple$viola$lang$int32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$int32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$int32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;
	viola$lang$int32  $1;

} viola$collections$Tuple$viola$lang$int32$viola$lang$int32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;
	viola$lang$uint32  $1;

} viola$collections$Tuple$viola$lang$int32$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$uint32$viola$lang$uint32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$uint32$viola$lang$uint32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;
	viola$lang$uint32  $1;
	viola$lang$uint32  $2;

} viola$collections$Tuple$viola$lang$int32$viola$lang$uint32$viola$lang$uint32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$os$Stat
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$os$Stat
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$os$Stat *  $0;

} viola$collections$Tuple$viola$os$Stat;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$string
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$string
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;
	viola$lang$string *  $1;

} viola$collections$Tuple$viola$lang$string$viola$lang$string;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$$array
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$$array
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string$$array *  $0;

} viola$collections$Tuple$viola$lang$string$$array;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$int32$viola$lang$int32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$int32$viola$lang$int32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;
	viola$lang$int32  $1;
	viola$lang$int32  $2;

} viola$collections$Tuple$viola$lang$int32$viola$lang$int32$viola$lang$int32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$int32
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$string$viola$lang$int32
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$string *  $0;
	viola$lang$int32  $1;

} viola$collections$Tuple$viola$lang$string$viola$lang$int32;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$os$StatVFS
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$os$StatVFS
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$os$StatVFS *  $0;

} viola$collections$Tuple$viola$os$StatVFS;
#endif

#ifndef _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$string
#define _VIOLA_TUPLE_T_viola$collections$Tuple$viola$lang$int32$viola$lang$string
typedef struct {
	viola$lang$atomic_uint32 $refCount;
	viola$lang$ptr $parent;
	viola$lang$uint64 size;
	viola$lang$int32  $0;
	viola$lang$string *  $1;

} viola$collections$Tuple$viola$lang$int32$viola$lang$string;
#endif

/* 同步函数原型 */
void viola$math$sqrt(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$sin(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$cos(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$tan(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$asin(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$acos(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$atan(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$sinh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$cosh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$tanh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$exp(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$log(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$log10(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$log2(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$fabs(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$floor(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$ceil(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$round(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$trunc(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$pow(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$atan2(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$fmod(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$fmin(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$fmax(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$asinh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$acosh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$atanh(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$radians(viola$lang$float64 degrees, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$degrees(viola$lang$float64 radians, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$log1p(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$log$_1(viola$lang$float64 x, viola$lang$float64 base, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$erf(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$erfc(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$tgamma(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$lgamma(viola$lang$float64 x, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$factorial(viola$lang$uint32 n, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$math$frexp(viola$lang$float64 x, viola$lang$float64 * mantissa, viola$lang$int32 * exp, viola$threads$Listener *listener);
void viola$math$ldexp(viola$lang$float64 x, viola$lang$int32 exp, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$gcd(viola$lang$int64 a, viola$lang$int64 b, viola$lang$int64 * result, viola$threads$Listener *listener);
void viola$math$lcm(viola$lang$int64 a, viola$lang$int64 b, viola$lang$int64 * result, viola$threads$Listener *listener);
void viola$math$perm(viola$lang$uint32 n, viola$lang$uint32 k, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$math$comb(viola$lang$uint32 n, viola$lang$uint32 k, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$math$hypot(viola$lang$float64$$array * a, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$dist(viola$lang$float64$$array * a, viola$lang$float64$$array * b, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$modf(viola$lang$float64 x, viola$lang$float64 * fractional, viola$lang$float64 * integer, viola$threads$Listener *listener);
void viola$math$remainder(viola$lang$float64 x, viola$lang$float64 y, viola$lang$float64 * result, viola$threads$Listener *listener);
void viola$math$isfinite(viola$lang$float64 x, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$math$isinf(viola$lang$float64 x, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$math$isnan(viola$lang$float64 x, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISBLK(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISCHR(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISDIR(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISFIFO(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISLNK(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISREG(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$S_ISSOCK(viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$stat$filemode(viola$lang$uint32 mode, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$threads$addThread(viola$lang$uint32 num, viola$threads$Listener *listener);
void viola$threads$delThread(viola$lang$uint32 num, viola$threads$Listener *listener);
void viola$threads$getThreadsNum(viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$threads$setThreadsNum(viola$lang$uint32 num, viola$threads$Listener *listener);
void viola$lang$del(viola$lang$object * _this, viola$threads$Listener *listener);
void viola$io$print$print(viola$lang$string * text, viola$threads$Listener *listener);
void viola$io$print$perror(viola$lang$string * text, viola$threads$Listener *listener);
void viola$io$print$input(viola$lang$string ** result, viola$threads$Listener *listener);
void viola$io$file$open(viola$lang$string * path, viola$lang$string * mode, viola$lang$string * encoding, viola$io$file ** f, viola$threads$Listener *listener);
void viola$io$file$read(viola$io$file * f, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$io$file$readBytes(viola$io$file * f, viola$lang$uint8$$array ** result, viola$threads$Listener *listener);
void viola$io$file$write(viola$io$file * f, viola$lang$string * content, viola$threads$Listener *listener);
void viola$io$file$writeBytes(viola$io$file * f, viola$lang$uint8$$array * content, viola$threads$Listener *listener);
void viola$os$access(viola$lang$string * path, viola$lang$uint32 mode, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$chdir(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$chflags(viola$lang$string * path, viola$lang$uint32 flags, viola$threads$Listener *listener);
void viola$os$chmod(viola$lang$string * path, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$chown(viola$lang$string * path, viola$lang$uint32 uid, viola$lang$uint32 gid, viola$threads$Listener *listener);
void viola$os$chroot(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$close(viola$lang$int32 fd, viola$threads$Listener *listener);
void viola$os$closerange(viola$lang$int32 fd1, viola$lang$int32 fd2, viola$threads$Listener *listener);
void viola$os$dup(viola$lang$int32 fd, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$dup2(viola$lang$int32 fd1, viola$lang$int32 fd2, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$fchdir(viola$lang$int32 fd, viola$threads$Listener *listener);
void viola$os$fchmod(viola$lang$int32 fd, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$fchown(viola$lang$int32 fd, viola$lang$uint32 uid, viola$lang$uint32 gid, viola$threads$Listener *listener);
void viola$os$fdatasync(viola$lang$int32 fd, viola$threads$Listener *listener);
void viola$os$fdopen(viola$lang$int32 fd, viola$io$file ** result, viola$threads$Listener *listener);
void viola$os$fpathconf(viola$lang$int32 fd, viola$lang$int32 name, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$fstat(viola$lang$int32 fd, viola$os$Stat ** result, viola$threads$Listener *listener);
void viola$os$ftruncate(viola$lang$int32 fd, viola$lang$uint32 size, viola$threads$Listener *listener);
void viola$os$getcwd(viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$getcwdb(viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$getgid(viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$getuid(viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$isatty(viola$lang$int32 fd, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$lchflags(viola$lang$string * path, viola$lang$uint32 flags, viola$threads$Listener *listener);
void viola$os$lchmod(viola$lang$string * path, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$lchown(viola$lang$string * path, viola$lang$uint32 uid, viola$lang$uint32 gid, viola$threads$Listener *listener);
void viola$os$link(viola$lang$string * path, viola$lang$string * newPath, viola$threads$Listener *listener);
void viola$os$listdir(viola$lang$string * path, viola$lang$string$$array ** result, viola$threads$Listener *listener);
void viola$os$lseek(viola$lang$int32 fd, viola$lang$int32 offset, viola$lang$int32 whence, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$lstat(viola$lang$string * path, viola$os$Stat ** result, viola$threads$Listener *listener);
void viola$os$major(viola$lang$uint32 dev, viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$makedev(viola$lang$uint32 major, viola$lang$uint32 minor, viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$makedirs(viola$lang$string * path, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$minor(viola$lang$uint32 dev, viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$mkdir(viola$lang$string * path, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$mkfifo(viola$lang$string * path, viola$lang$uint32 mode, viola$threads$Listener *listener);
void viola$os$mknod(viola$lang$string * path, viola$lang$uint32 mode, viola$lang$uint32 dev, viola$threads$Listener *listener);
void viola$os$open(viola$lang$string * path, viola$lang$uint32 flags, viola$lang$uint32 mode, viola$lang$int32 * fd, viola$threads$Listener *listener);
void viola$os$openpty(viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$pathconf(viola$lang$string * path, viola$lang$int32 name, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$pipe(viola$lang$int32 * readFd, viola$lang$int32 * writeFd, viola$threads$Listener *listener);
void viola$os$popen(viola$lang$string * command, viola$lang$string * mode, viola$io$file ** result, viola$threads$Listener *listener);
void viola$os$read(viola$lang$int32 fd, viola$lang$uint32 nbyte, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$readlink(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$remove(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$removedirs(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$rename(viola$lang$string * oldPath, viola$lang$string * newPath, viola$threads$Listener *listener);
void viola$os$renames(viola$lang$string * oldPath, viola$lang$string * newPath, viola$threads$Listener *listener);
void viola$os$rmdir(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$stat(viola$lang$string * path, viola$os$Stat ** result, viola$threads$Listener *listener);
void viola$os$stat_float_times(viola$lang$bool useFloat, viola$threads$Listener *listener);
void viola$os$statvfs(viola$lang$string * path, viola$os$StatVFS ** result, viola$threads$Listener *listener);
void viola$os$tcgetpgrp(viola$lang$int32 fd, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$tcsetpgrp(viola$lang$int32 fd, viola$lang$int32 pgid, viola$threads$Listener *listener);
void viola$os$ttyname(viola$lang$int32 fd, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$unlink(viola$lang$string * path, viola$threads$Listener *listener);
void viola$os$utime(viola$lang$string * path, viola$lang$uint32 atime, viola$lang$uint32 mtime, viola$threads$Listener *listener);
void viola$os$write(viola$lang$int32 fd, viola$lang$string * data, viola$lang$uint32 * result, viola$threads$Listener *listener);
void viola$os$sleep(viola$lang$uint64 milliseconds, viola$threads$Listener *listener);
void viola$os$exit(viola$lang$int32 code, viola$threads$Listener *listener);
void viola$os$getEnv(viola$lang$string * name, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$time(viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$os$system(viola$lang$string * command, viola$lang$int32 * result, viola$threads$Listener *listener);
void viola$os$path$abspath(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$basename(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$commonpath(viola$lang$string$$array * paths, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$commonprefix(viola$lang$string$$array * paths, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$dirname(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$exists(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$getatime(viola$lang$string * path, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$os$path$getctime(viola$lang$string * path, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$os$path$getmtime(viola$lang$string * path, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$os$path$getsize(viola$lang$string * path, viola$lang$uint64 * result, viola$threads$Listener *listener);
void viola$os$path$isabs(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$isdir(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$isfile(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$islink(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$ismount(viola$lang$string * path, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$join(viola$lang$string$$array * paths, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$normpath(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$realpath(viola$lang$string * path, viola$lang$string ** result, viola$threads$Listener *listener);
void viola$os$path$samefile(viola$lang$string * path1, viola$lang$string * path2, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$sameopenfile(viola$lang$int32 fd1, viola$lang$int32 fd2, viola$lang$bool * result, viola$threads$Listener *listener);
void viola$os$path$split(viola$lang$string * path, viola$lang$string$$array ** result, viola$threads$Listener *listener);
void viola$os$path$splitext(viola$lang$string * path, viola$lang$string$$array ** result, viola$threads$Listener *listener);

void viola$math$sqrt$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$sqrt(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$sin$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$sin(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$cos$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$cos(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$tan$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$tan(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$asin$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$asin(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$acos$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$acos(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$atan$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$atan(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$sinh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$sinh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$cosh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$cosh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$tanh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$tanh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$exp$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$exp(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$log$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$log(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$log10$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$log10(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$log2$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$log2(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$fabs$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$fabs(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$floor$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$floor(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$ceil$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$ceil(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$round$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$round(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$trunc$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$trunc(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$pow$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$pow(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$atan2$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$atan2(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$fmod$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$fmod(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$fmin$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$fmin(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$fmax$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$fmax(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$asinh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$asinh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$acosh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$acosh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$atanh$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$atanh(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$radians$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 degrees;
		viola$lang$float64 result;
		degrees = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$radians(degrees, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$degrees$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 radians;
		viola$lang$float64 result;
		radians = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$degrees(radians, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$log1p$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$log1p(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$log$_1$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 base;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		base = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$log$_1(x, base, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$erf$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$erf(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$erfc$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$erfc(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$tgamma$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$tgamma(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$lgamma$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$lgamma(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$factorial$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 n;
		viola$lang$uint64 result;
		n = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$factorial(n, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$frexp$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 mantissa;
		viola$lang$int32 exp;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$frexp(x, &mantissa, &exp, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = mantissa;
		returns->$1 = exp;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$ldexp$async(viola$collections$Tuple$viola$lang$float64$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$int32 exp;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		exp = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$ldexp(x, exp, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$gcd$async(viola$collections$Tuple$viola$lang$int64$viola$lang$int64 * params, viola$collections$Tuple$viola$lang$int64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int64 a;
		viola$lang$int64 b;
		viola$lang$int64 result;
		a = params->$0;
		if ($$exc) goto $$_async_err;
		b = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$gcd(a, b, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$lcm$async(viola$collections$Tuple$viola$lang$int64$viola$lang$int64 * params, viola$collections$Tuple$viola$lang$int64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int64 a;
		viola$lang$int64 b;
		viola$lang$int64 result;
		a = params->$0;
		if ($$exc) goto $$_async_err;
		b = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$lcm(a, b, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$perm$async(viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 n;
		viola$lang$uint32 k;
		viola$lang$uint64 result;
		n = params->$0;
		if ($$exc) goto $$_async_err;
		k = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$perm(n, k, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$comb$async(viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 n;
		viola$lang$uint32 k;
		viola$lang$uint64 result;
		n = params->$0;
		if ($$exc) goto $$_async_err;
		k = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$comb(n, k, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$hypot$async(viola$collections$Tuple$viola$lang$float64$$array * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64$$array * a = NULL;
		viola$lang$float64 result;
		a = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$hypot(a, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$dist$async(viola$collections$Tuple$viola$lang$float64$$array$viola$lang$float64$$array * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64$$array * a = NULL;
		viola$lang$float64$$array * b = NULL;
		viola$lang$float64 result;
		a = params->$0;
		if ($$exc) goto $$_async_err;
		b = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$dist(a, b, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$modf$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 fractional;
		viola$lang$float64 integer;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$modf(x, &fractional, &integer, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = fractional;
		returns->$1 = integer;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$remainder$async(viola$collections$Tuple$viola$lang$float64$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$float64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$float64 y;
		viola$lang$float64 result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		y = params->$1;
		if ($$exc) goto $$_async_err;
		viola$math$remainder(x, y, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$isfinite$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$bool result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$isfinite(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$isinf$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$bool result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$isinf(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$math$isnan$async(viola$collections$Tuple$viola$lang$float64 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$float64 x;
		viola$lang$bool result;
		x = params->$0;
		if ($$exc) goto $$_async_err;
		viola$math$isnan(x, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISBLK$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISBLK(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISCHR$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISCHR(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISDIR$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISDIR(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISFIFO$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISFIFO(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISLNK$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISLNK(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISREG$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISREG(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$S_ISSOCK$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$bool result;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$S_ISSOCK(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$stat$filemode$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 mode;
		viola$lang$string * result = NULL;
		mode = params->$0;
		if ($$exc) goto $$_async_err;
		viola$stat$filemode(mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$threads$addThread$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$uint32 num;
		num = params->$0;
		if ($$exc) goto $$_async_err;
		viola$threads$addThread(num, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$threads$delThread$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$uint32 num;
		num = params->$0;
		if ($$exc) goto $$_async_err;
		viola$threads$delThread(num, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$threads$getThreadsNum$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$uint32 result;
		viola$threads$getThreadsNum(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$threads$setThreadsNum$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$uint32 num;
		num = params->$0;
		if ($$exc) goto $$_async_err;
		viola$threads$setThreadsNum(num, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$lang$del$async(viola$collections$Tuple$viola$lang$object * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$object * _this = NULL;
		_this = params->$0;
		if ($$exc) goto $$_async_err;
		viola$lang$del(_this, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$print$print$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * text = NULL;
		text = params->$0;
		if ($$exc) goto $$_async_err;
		viola$io$print$print(text, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$print$perror$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * text = NULL;
		text = params->$0;
		if ($$exc) goto $$_async_err;
		viola$io$print$perror(text, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$print$input$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$string * result = NULL;
		viola$io$print$input(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$file$open$async(viola$collections$Tuple$viola$lang$string$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$viola$io$file * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * mode = NULL;
		viola$lang$string * encoding = NULL;
		viola$io$file * f = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		encoding = params->$2;
		if ($$exc) goto $$_async_err;
		viola$io$file$open(path, mode, encoding, &f, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = f;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$file$read$async(viola$collections$Tuple$viola$io$file * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$io$file * f = NULL;
		viola$lang$string * result = NULL;
		f = params->$0;
		if ($$exc) goto $$_async_err;
		viola$io$file$read(f, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$file$readBytes$async(viola$collections$Tuple$viola$io$file * params, viola$collections$Tuple$viola$lang$uint8$$array * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$io$file * f = NULL;
		viola$lang$uint8$$array * result = NULL;
		f = params->$0;
		if ($$exc) goto $$_async_err;
		viola$io$file$readBytes(f, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$file$write$async(viola$collections$Tuple$viola$io$file$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$io$file * f = NULL;
		viola$lang$string * content = NULL;
		f = params->$0;
		if ($$exc) goto $$_async_err;
		content = params->$1;
		if ($$exc) goto $$_async_err;
		viola$io$file$write(f, content, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$io$file$writeBytes$async(viola$collections$Tuple$viola$io$file$viola$lang$uint8$$array * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$io$file * f = NULL;
		viola$lang$uint8$$array * content = NULL;
		f = params->$0;
		if ($$exc) goto $$_async_err;
		content = params->$1;
		if ($$exc) goto $$_async_err;
		viola$io$file$writeBytes(f, content, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$access$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$access(path, mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$chdir$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$chdir(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$chflags$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 flags;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		flags = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$chflags(path, flags, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$chmod$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$chmod(path, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$chown$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 uid;
		viola$lang$uint32 gid;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		uid = params->$1;
		if ($$exc) goto $$_async_err;
		gid = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$chown(path, uid, gid, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$chroot$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$chroot(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$close$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$close(fd, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$closerange$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd1;
		viola$lang$int32 fd2;
		fd1 = params->$0;
		if ($$exc) goto $$_async_err;
		fd2 = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$closerange(fd1, fd2, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$dup$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$int32 result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$dup(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$dup2$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd1;
		viola$lang$int32 fd2;
		viola$lang$int32 result;
		fd1 = params->$0;
		if ($$exc) goto $$_async_err;
		fd2 = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$dup2(fd1, fd2, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fchdir$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$fchdir(fd, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fchmod$async(viola$collections$Tuple$viola$lang$int32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		viola$lang$uint32 mode;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$fchmod(fd, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fchown$async(viola$collections$Tuple$viola$lang$int32$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		viola$lang$uint32 uid;
		viola$lang$uint32 gid;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		uid = params->$1;
		if ($$exc) goto $$_async_err;
		gid = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$fchown(fd, uid, gid, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fdatasync$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$fdatasync(fd, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fdopen$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$io$file * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$io$file * result = NULL;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$fdopen(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fpathconf$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$int32 name;
		viola$lang$int32 result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		name = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$fpathconf(fd, name, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$fstat$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$os$Stat * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$os$Stat * result = NULL;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$fstat(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$ftruncate$async(viola$collections$Tuple$viola$lang$int32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		viola$lang$uint32 size;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		size = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$ftruncate(fd, size, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$getcwd$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$string * result = NULL;
		viola$os$getcwd(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$getcwdb$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$string * result = NULL;
		viola$os$getcwdb(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$getgid$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$uint32 result;
		viola$os$getgid(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$getuid$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$uint32 result;
		viola$os$getuid(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$isatty$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$bool result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$isatty(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$lchflags$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 flags;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		flags = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$lchflags(path, flags, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$lchmod$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$lchmod(path, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$lchown$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 uid;
		viola$lang$uint32 gid;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		uid = params->$1;
		if ($$exc) goto $$_async_err;
		gid = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$lchown(path, uid, gid, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$link$async(viola$collections$Tuple$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$string * newPath = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		newPath = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$link(path, newPath, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$listdir$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string$$array * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string$$array * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$listdir(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$lseek$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$int32 offset;
		viola$lang$int32 whence;
		viola$lang$int32 result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		offset = params->$1;
		if ($$exc) goto $$_async_err;
		whence = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$lseek(fd, offset, whence, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$lstat$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$os$Stat * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$os$Stat * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$lstat(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$major$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 dev;
		viola$lang$uint32 result;
		dev = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$major(dev, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$makedev$async(viola$collections$Tuple$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 major;
		viola$lang$uint32 minor;
		viola$lang$uint32 result;
		major = params->$0;
		if ($$exc) goto $$_async_err;
		minor = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$makedev(major, minor, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$makedirs$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$makedirs(path, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$minor$async(viola$collections$Tuple$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$uint32 dev;
		viola$lang$uint32 result;
		dev = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$minor(dev, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$mkdir$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$mkdir(path, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$mkfifo$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$mkfifo(path, mode, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$mknod$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 mode;
		viola$lang$uint32 dev;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		dev = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$mknod(path, mode, dev, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$open$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint32 flags;
		viola$lang$uint32 mode;
		viola$lang$int32 fd;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		flags = params->$1;
		if ($$exc) goto $$_async_err;
		mode = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$open(path, flags, mode, &fd, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = fd;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$openpty$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$int32 result;
		viola$os$openpty(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$pathconf$async(viola$collections$Tuple$viola$lang$string$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$int32 name;
		viola$lang$int32 result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		name = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$pathconf(path, name, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$pipe$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$int32 readFd;
		viola$lang$int32 writeFd;
		viola$os$pipe(&readFd, &writeFd, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = readFd;
		returns->$1 = writeFd;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$popen$async(viola$collections$Tuple$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$viola$io$file * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * command = NULL;
		viola$lang$string * mode = NULL;
		viola$io$file * result = NULL;
		command = params->$0;
		if ($$exc) goto $$_async_err;
		mode = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$popen(command, mode, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$read$async(viola$collections$Tuple$viola$lang$int32$viola$lang$uint32 * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$uint32 nbyte;
		viola$lang$string * result = NULL;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		nbyte = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$read(fd, nbyte, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$readlink$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$readlink(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$remove$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$remove(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$removedirs$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$removedirs(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$rename$async(viola$collections$Tuple$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * oldPath = NULL;
		viola$lang$string * newPath = NULL;
		oldPath = params->$0;
		if ($$exc) goto $$_async_err;
		newPath = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$rename(oldPath, newPath, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$renames$async(viola$collections$Tuple$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * oldPath = NULL;
		viola$lang$string * newPath = NULL;
		oldPath = params->$0;
		if ($$exc) goto $$_async_err;
		newPath = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$renames(oldPath, newPath, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$rmdir$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$rmdir(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$stat$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$os$Stat * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$os$Stat * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$stat(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$stat_float_times$async(viola$collections$Tuple$viola$lang$bool * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$bool useFloat;
		useFloat = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$stat_float_times(useFloat, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$statvfs$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$os$StatVFS * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$os$StatVFS * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$statvfs(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$tcgetpgrp$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$int32 result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$tcgetpgrp(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$tcsetpgrp$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 fd;
		viola$lang$int32 pgid;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		pgid = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$tcsetpgrp(fd, pgid, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$ttyname$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$string * result = NULL;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$ttyname(fd, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$unlink$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$unlink(path, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$utime$async(viola$collections$Tuple$viola$lang$string$viola$lang$uint32$viola$lang$uint32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$string * path = NULL;
		viola$lang$uint32 atime;
		viola$lang$uint32 mtime;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		atime = params->$1;
		if ($$exc) goto $$_async_err;
		mtime = params->$2;
		if ($$exc) goto $$_async_err;
		viola$os$utime(path, atime, mtime, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$write$async(viola$collections$Tuple$viola$lang$int32$viola$lang$string * params, viola$collections$Tuple$viola$lang$uint32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd;
		viola$lang$string * data = NULL;
		viola$lang$uint32 result;
		fd = params->$0;
		if ($$exc) goto $$_async_err;
		data = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$write(fd, data, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$sleep$async(viola$collections$Tuple$viola$lang$uint64 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$uint64 milliseconds;
		milliseconds = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$sleep(milliseconds, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$exit$async(viola$collections$Tuple$viola$lang$int32 * params, viola$collections$Tuple$ * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)returns;
		viola$lang$int32 code;
		code = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$exit(code, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$getEnv$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * name = NULL;
		viola$lang$string * result = NULL;
		name = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$getEnv(name, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$time$async(viola$collections$Tuple$ * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		(void)params;
		viola$lang$uint64 result;
		viola$os$time(&result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$system$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$int32 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * command = NULL;
		viola$lang$int32 result;
		command = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$system(command, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$abspath$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$abspath(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$basename$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$basename(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$commonpath$async(viola$collections$Tuple$viola$lang$string$$array * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string$$array * paths = NULL;
		viola$lang$string * result = NULL;
		paths = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$commonpath(paths, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$commonprefix$async(viola$collections$Tuple$viola$lang$string$$array * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string$$array * paths = NULL;
		viola$lang$string * result = NULL;
		paths = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$commonprefix(paths, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$dirname$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$dirname(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$exists$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$exists(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$getatime$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint64 result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$getatime(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$getctime$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint64 result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$getctime(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$getmtime$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint64 result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$getmtime(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$getsize$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$uint64 * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$uint64 result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$getsize(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$isabs$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$isabs(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$isdir$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$isdir(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$isfile$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$isfile(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$islink$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$islink(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$ismount$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$bool result;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$ismount(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$join$async(viola$collections$Tuple$viola$lang$string$$array * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string$$array * paths = NULL;
		viola$lang$string * result = NULL;
		paths = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$join(paths, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$normpath$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$normpath(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$realpath$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$realpath(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$samefile$async(viola$collections$Tuple$viola$lang$string$viola$lang$string * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path1 = NULL;
		viola$lang$string * path2 = NULL;
		viola$lang$bool result;
		path1 = params->$0;
		if ($$exc) goto $$_async_err;
		path2 = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$path$samefile(path1, path2, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$sameopenfile$async(viola$collections$Tuple$viola$lang$int32$viola$lang$int32 * params, viola$collections$Tuple$viola$lang$bool * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$int32 fd1;
		viola$lang$int32 fd2;
		viola$lang$bool result;
		fd1 = params->$0;
		if ($$exc) goto $$_async_err;
		fd2 = params->$1;
		if ($$exc) goto $$_async_err;
		viola$os$path$sameopenfile(fd1, fd2, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$split$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string$$array * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string$$array * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$split(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}

void viola$os$path$splitext$async(viola$collections$Tuple$viola$lang$string * params, viola$collections$Tuple$viola$lang$string$$array * returns,
                          viola$threads$Listener *listener) {
	viola$lang$exception$Exception *$$exc = listener->exception;
	viola$threads$pushStackB(listener->currentThreadId);
	do {
		viola$lang$string * path = NULL;
		viola$lang$string$$array * result = NULL;
		path = params->$0;
		if ($$exc) goto $$_async_err;
		viola$os$path$splitext(path, &result, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		returns->$0 = result;
		if ($$exc) goto $$_async_err;
		goto $$_async_done;
	} while (0);
$$_async_err:
	if (viola$lang$convertibleTo($$exc->$$vtable, &viola$lang$exception$Exception$$vtable)) {
		viola$lang$exception$Exception *exc = $$exc;
		$$exc = NULL;
		listener->exception = NULL;
		viola$lang$string *$$_msg = NULL;
		viola$lang$exception$Exception$what$_0(exc, &$$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		viola$io$print$perror($$_msg, listener);
		if ($$exc == NULL) { $$exc = listener->exception; }
		listener->exception = exc;
		viola$lang$exception$Exception$__del__$_0(exc, listener);
		exc = NULL;
	}
$$_async_done:
$$_async_cleanup: ;
	if ($$exc) { goto $$_async_cleanup; }
	viola$threads$popStackB(listener->currentThreadId);
}
