/* -*- coding: utf-8 -*-
 * Viola数学运行库：包含math.h并生成相关绑定函数。
 * 命名空间：viola.math（C标识符前缀 viola$math$）。
 */
#include "runtime.h"

#ifndef _WIN32
/* glibc的gamma函数在math.h中可能未声明 */
double tgamma(double);
double lgamma(double);
#endif

#define MATH_UNARY_FUNC(func_name, c_func)                                                    \
    void viola$math$##func_name(viola$lang$float64 x, viola$lang$float64 *result,             \
                                viola$threads$Listener *listener) {                           \
        (void)listener;                                                                       \
        *result = c_func(x);                                                                  \
    }

#define MATH_BINARY_FUNC(func_name, c_func)                                                   \
    void viola$math$##func_name(viola$lang$float64 x, viola$lang$float64 y,                   \
                                viola$lang$float64 *result, viola$threads$Listener *listener) { \
        (void)listener;                                                                       \
        *result = c_func(x, y);                                                               \
    }

MATH_UNARY_FUNC(sqrt, sqrt)
MATH_UNARY_FUNC(sin, sin)
MATH_UNARY_FUNC(cos, cos)
MATH_UNARY_FUNC(tan, tan)
MATH_UNARY_FUNC(asin, asin)
MATH_UNARY_FUNC(acos, acos)
MATH_UNARY_FUNC(atan, atan)
MATH_UNARY_FUNC(sinh, sinh)
MATH_UNARY_FUNC(cosh, cosh)
MATH_UNARY_FUNC(tanh, tanh)
MATH_UNARY_FUNC(exp, exp)
MATH_UNARY_FUNC(log, log)
MATH_UNARY_FUNC(log10, log10)
MATH_UNARY_FUNC(log2, log2)
MATH_UNARY_FUNC(fabs, fabs)
MATH_UNARY_FUNC(floor, floor)
MATH_UNARY_FUNC(ceil, ceil)
MATH_UNARY_FUNC(round, round)
MATH_UNARY_FUNC(trunc, trunc)
MATH_BINARY_FUNC(pow, pow)
MATH_BINARY_FUNC(atan2, atan2)
MATH_BINARY_FUNC(fmod, fmod)
MATH_BINARY_FUNC(fmin, fmin)
MATH_BINARY_FUNC(fmax, fmax)

/* ================= 常量 ================= */
/* math.vla中声明的原生全局变量在此提供存储（头文件中为extern声明）。
   注意：这些全局变量必须在本文件中给出定义，否则使用它们的
   程序会在链接时报告 undefined reference。 */
viola$lang$float64 viola$math$pi = 3.14159265358979323846;
viola$lang$float64 viola$math$e = 2.71828182845904523536;
viola$lang$float64 viola$math$tau = 6.28318530717958647692;
viola$lang$float64 viola$math$nan = (viola$lang$float64)NAN;
viola$lang$float64 viola$math$inf = (viola$lang$float64)INFINITY;

/* ================= 0.1新增：反双曲函数 ================= */
MATH_UNARY_FUNC(asinh, asinh)
MATH_UNARY_FUNC(acosh, acosh)
MATH_UNARY_FUNC(atanh, atanh)

/* ================= 0.1新增：弧度与角度转换 ================= */
#define VIOLA_MATH_PI 3.14159265358979323846

static double viola_math_radians_impl(double x) {
    return x * VIOLA_MATH_PI / 180.0;
}

static double viola_math_degrees_impl(double x) {
    return x * 180.0 / VIOLA_MATH_PI;
}

MATH_UNARY_FUNC(radians, viola_math_radians_impl)
MATH_UNARY_FUNC(degrees, viola_math_degrees_impl)

/* ================= 0.1新增：对数 ================= */
MATH_UNARY_FUNC(log1p, log1p)
/* log(x, base)重载（Viola声明中的第二个重载） */
void viola$math$log$_1(viola$lang$float64 x, viola$lang$float64 base,
                       viola$lang$float64 *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = log(x) / log(base);
}

/* ================= 0.1新增：误差函数与伽马函数 ================= */
MATH_UNARY_FUNC(erf, erf)
MATH_UNARY_FUNC(erfc, erfc)
MATH_UNARY_FUNC(tgamma, tgamma)
MATH_UNARY_FUNC(lgamma, lgamma)

/* 阶乘（整数参数，uint64结果） */
void viola$math$factorial(viola$lang$uint32 n, viola$lang$uint64 *result,
                          viola$threads$Listener *listener) {
    (void)listener;
    viola$lang$uint64 r = 1;
    for (viola$lang$uint32 i = 2; i <= n; i++) {
        r *= i;
    }
    *result = r;
}

/* ================= 0.1新增：指数与尾数 ================= */
/* frexp(x) -> (mantissa, exp)：分离为尾数与指数 */
void viola$math$frexp(viola$lang$float64 x, viola$lang$float64 *mantissa,
                      viola$lang$int32 *exp, viola$threads$Listener *listener) {
    (void)listener;
    int e = 0;
    *mantissa = frexp(x, &e);
    *exp = e;
}

/* ldexp(x, exp)：由尾数与指数组合浮点数 */
void viola$math$ldexp(viola$lang$float64 x, viola$lang$int32 exp,
                      viola$lang$float64 *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = ldexp(x, (int)exp);
}

/* ================= 0.1新增：整数函数 ================= */

static int64_t gcdImpl(int64_t a, int64_t b) {
    if (a < 0) {
        a = -a;
    }
    if (b < 0) {
        b = -b;
    }
    while (b != 0) {
        int64_t t = a % b;
        a = b;
        b = t;
    }
    return a;
}

/* gcd(a, b)：最大公约数 */
void viola$math$gcd(viola$lang$int64 a, viola$lang$int64 b, viola$lang$int64 *result,
                    viola$threads$Listener *listener) {
    (void)listener;
    *result = gcdImpl(a, b);
}

/* lcm(a, b)：最小公倍数 */
void viola$math$lcm(viola$lang$int64 a, viola$lang$int64 b, viola$lang$int64 *result,
                    viola$threads$Listener *listener) {
    (void)listener;
    int64_t g = gcdImpl(a, b);
    if (g == 0) {
        *result = 0;
        return;
    }
    if (a < 0) {
        a = -a;
    }
    if (b < 0) {
        b = -b;
    }
    *result = (a / g) * b;
}

static uint64_t permImpl(uint64_t n, uint64_t k) {
    uint64_t r = 1;
    for (uint64_t i = 0; i < k; i++) {
        r *= n - i;
    }
    return r;
}

/* perm(n, k)：排列数（n!/(n-k)!，k>n时为0） */
void viola$math$perm(viola$lang$uint32 n, viola$lang$uint32 k, viola$lang$uint64 *result,
                     viola$threads$Listener *listener) {
    (void)listener;
    if (k > n) {
        *result = 0;
        return;
    }
    *result = permImpl(n, k);
}

/* comb(n, k)：组合数（C(n,k)，k>n时为0） */
void viola$math$comb(viola$lang$uint32 n, viola$lang$uint32 k, viola$lang$uint64 *result,
                     viola$threads$Listener *listener) {
    (void)listener;
    if (k > n) {
        *result = 0;
        return;
    }
    if (k > n - k) {
        k = n - k;
    }
    uint64_t r = 1;
    for (uint64_t i = 1; i <= k; i++) {
        r = r * (n - k + i) / i;
    }
    *result = r;
}

/* ================= 0.1新增：数组范数 ================= */

#ifndef _VIOLA_ARRAY_T_viola$lang$float64$$array
#define _VIOLA_ARRAY_T_viola$lang$float64$$array
typedef struct viola$lang$float64$$array {
    viola$lang$uint32 $refCount;
    viola$lang$ptr $parent;
    viola$lang$float64 *data;
    viola$lang$uint64 size;
} viola$lang$float64$$array;
#endif

/* hypot(a)：欧几里得范数 */
void viola$math$hypot(viola$lang$float64$$array *a, viola$lang$float64 *result,
                      viola$threads$Listener *listener) {
    (void)listener;
    double sum = 0.0;
    if (a != NULL) {
        for (uint64_t i = 0; i < a->size; i++) {
            sum += a->data[i] * a->data[i];
        }
    }
    *result = sqrt(sum);
}

/* dist(a, b)：欧几里得距离（要求a与b长度相同） */
void viola$math$dist(viola$lang$float64$$array *a, viola$lang$float64$$array *b,
                     viola$lang$float64 *result, viola$threads$Listener *listener) {
    (void)listener;
    double sum = 0.0;
    uint64_t n = 0;
    if (a != NULL) {
        n = a->size;
    }
    if (b != NULL && b->size < n) {
        n = b->size;
    }
    for (uint64_t i = 0; i < n; i++) {
        double d = a->data[i] - b->data[i];
        sum += d * d;
    }
    *result = sqrt(sum);
}

/* ================= 0.1新增：小数部分 ================= */

/* modf(x) -> (fractional, integer)：分离整数部分与小数部分 */
void viola$math$modf(viola$lang$float64 x, viola$lang$float64 *fractional,
                     viola$lang$float64 *integer, viola$threads$Listener *listener) {
    (void)listener;
    double ip = 0.0;
    *fractional = modf(x, &ip);
    *integer = ip;
}

/* remainder(x, y)：IEEE 754风格的小数余数 */
MATH_BINARY_FUNC(remainder, remainder)

/* ================= 0.1新增：无效值判断 ================= */

/* isfinite(x)：判断x是否为有限值 */
void viola$math$isfinite(viola$lang$float64 x, viola$lang$bool *result,
                         viola$threads$Listener *listener) {
    (void)listener;
    *result = isfinite(x);
}

/* isinf(x)：判断x是否为正负无穷 */
void viola$math$isinf(viola$lang$float64 x, viola$lang$bool *result,
                      viola$threads$Listener *listener) {
    (void)listener;
    *result = isinf(x);
}

/* isnan(x)：判断x是否为NaN */
void viola$math$isnan(viola$lang$float64 x, viola$lang$bool *result,
                      viola$threads$Listener *listener) {
    (void)listener;
    *result = isnan(x);
}