/* -*- coding: utf-8 -*-
 * Viola数学运行库：包含math.h并生成相关绑定函数。
 * 命名空间：viola.math（C标识符前缀 viola$math$）。
 */
#include "runtime.h"

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

/* 常量 */
void viola$math$pi(viola$lang$float64 *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = 3.14159265358979323846;
}

void viola$math$e(viola$lang$float64 *result, viola$threads$Listener *listener) {
    (void)listener;
    *result = 2.71828182845904523536;
}
