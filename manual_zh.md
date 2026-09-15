# Viola编译器

**在GitHub上访问[项目](https://github.com/YourHanpi/viola-lang)**

## 简介

Viola是一种静态类型的、编译式的、通用的、大小写敏感的、数据不可变的编程语言，它可以兼容C语言。

Viola支持面向对象的程序设计，包括封装、继承、多态和抽象等等。

## 注释

注释的写法如下：

```viola
// 这是单行注释

/*
这是多行注释
*/
```

## 基本数据类型

- `bool` - 布尔类型（相当于C `bool`）
- `int` - 整型（相当于C `int32_t`）；与`int32`是同一个类型，两个名字完全等价
    - `int8` - 8位整型（相当于C `int8_t`）
    - `int16` - 16位整型（相当于C `int16_t`）
    - `int32` - 32位整型（相当于C `int32_t`）；与`int`是同一个类型
    - `int64` - 64位整型（相当于C `int64_t`）
    - `uint` - 无符号整型（相当于C `unsigned int`）
    - `uint8` - 8位无符号整型（相当于C `uint8_t`）
    - `uint16` - 16位无符号整型（相当于C `uint16_t`）
    - `uint32` - 32位无符号整型（相当于C `uint32_t`）
    - `uint64` - 64位无符号整型（相当于C `uint64_t`）
- `float` - 浮点型（相当于C `float`）
    - `float32` - 32位浮点型（相当于C `float32_t`）
    - `float64` - 64位浮点型（相当于C `float64_t`）
    - `double` - 双精度浮点型（相当于C `double`）
    - `float128` - 四精度浮点型（相当于C `long double`）
- `void` - 空类型，等效于`()`类型（可用于函数返回值和参数位置）
- `Pointer::<T>` - 指针类型（`unsafe`），C语言层表示为`void *`，由用户手动管理内存，
  用于与C语言交互

## 集合数据类型

**注意：所有集合类型与类类型在实现上均为object类。**

- `T[]` - 元素类型为T的数组类型
- `dict::<K, V>` - 键为K类型，值为V类型的字典类型（**TODO: 字典功能尚未实装**）
- `(T1, T2, ...)` - 元素类型为T1, T2, ...的元组类型
- `(T1, T2, ...) -> (R1, R2, ...)` - 函数类型，参数类型为`T1, T2, ...`，返回类型为`(R1, R2, ...)`
- `string` - 字符串类型

## 变量的使用方式

**变量必须先声明，后赋值，或者声明的同时赋值。每个变量只允许赋值一次。**

变量的声明语法如下：

```viola
Typename varname;
```

例如：

```viola
int a;
float b;
string c;
dict::<int, string> d;
```

变量的定义语法如下：

```viola
Typename varname = value;
```

例如：

```viola
int a = 10;
float b = 3.14;
string c = "Hello, World!";
dict::<int, string> d = {1: "one", 2: "two", 3: "three"};
```

变量的赋值语法如下：

```viola
varname = value;
```

例如：

```viola
x = 20;
y = getValue();
```

**注意：每个变量只能赋值一次。**

## 变量的作用域

- 不在任何代码块内声明的变量，在当前文件内有效。如果需要在其他文件中使用，则需要在该文件内使用`import`进行导入。这种变量称为
  **全局变量**。
- 在函数的参数定义中声明的变量，在当前函数有效。这种变量称为**形式参数**，或简称为**形参**。
- 在代码块内部声明的变量，只在代码块内部有效。这种变量称为**局部变量**。
- 任何超出作用域的变量都会被自动回收。

## 字面量

字面量指的是可以直接使用的值，如具体的数字、字符串、布尔值等。字面量可以分为四类：整数字面量、浮点数字面量、字符串字面量、布尔字面量。例如：

```viola
114514  // 整数字面量
114.514  // 浮点数字面量
"114514" // 字符串字面量
true  // 布尔字面量
```

### 整数字面量

整数字面量的写法是这样的：

- 最简单的写法是直接写十进制数字，这一类写法可以用正则表达式`^[+-]?\d+$`匹配。例如：

```viola
114514
-1919810
```

- 如果数字是16进制，则需要以`0x`开头，这一类写法可以用正则表达式`^0x[0-9a-fA-F]+$`匹配。例如：

```viola
0xdeadbeef
0xDEADBEEF
```

- 如果数字是8进制，则需要以`0o`或`0`开头，这一类写法可以用正则表达式`^0o?[0-7]+$`匹配。例如：

```viola
0o12345670
012345670
```

- 如果数字是2进制，则需要以`0b`开头，这一类写法可以用正则表达式`^0b[01]+$`匹配。例如：

```viola
0b11001100
```

- 如果需要限定数据类型，则需要加上数据类型后缀。后缀的写法可以用正则表达式`^[ui](8|16|32|64)?$`匹配。例如：

```viola
114514i // 默认长度的整型
114514u // 默认长度的无符号整型
114514i64 // 64位整型
-1919810u64 // 64位无符号整型
0xdeadbeefu32 // 32位无符号整型
```

### 浮点数字面量

浮点数字面量的写法是这样的：

- 最简单的写法是直接写小数，这一类写法可以用正则表达式`^[+-]?\d+\.\d*$`匹配。例如：

```viola
3.14
-0.618
```

- 如果数字是科学计数法，可以写成用正则表达式`^[+-]?\d+(\.\d*)?e[+-]?\d+$`匹配的格式，默认为64位浮点型。例如：

```viola
114.514e3
-0.618e-2
1919810e+16
```

- 如果需要限定数据类型，则需要加上数据类型后缀。后缀的写法可以用正则表达式`^[FfLl]$`匹配。例如：

```viola
114.514f // 32位浮点型
1919.810l // 128位浮点型
```

**TODO: 128位浮点型的支持**

### 字符串字面量

字符串字面量的写法是这样的：

- 最简单的写法是直接写字符串，只需用单引号或双引号括起来即可。例如：

```viola
"Hello, world!"
'Hello, world!'
```

- 字符串可以包含转义字符。例如：

```viola
"Hello, world!\n"
```

**TODO: 实现r前缀字符串。**

- 如果不希望转义任何字符，则需要加上`r`前缀。例如：

```viola
r"Hello, world!\n" // 相当于"Hello, world!\\n"的值
```

### 布尔字面量

布尔字面量只有两种写法：`true`和`false`。前者表示真，后者表示假。

## 运算符

**注意：由于任何已经初始化的数据都不可变，Viola不提供自增、自减、加且赋值等导致已初始化数据改变的运算符。**

### 通用的运算符

二元算术运算符：

| 运算符  | 描述                   | 调用方式         | 调用的魔术方法                                                                                                                           |
|:-----|:---------------------|:-------------|:----------------------------------------------------------------------------------------------------------------------------------|
| `+`  | 把两个操作数相加             | `x = a + b`  | `fn __add__(T1 other) -> (T2 result)`<br>`fn __radd__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__add__`方法未定义时，调用`b`的此方法          |
| `-`  | 将前一操作数减去后一操作数        | `x = a - b`  | `fn __sub__(T1 other) -> (T2 result)`<br>`fn __rsub__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__sub__`方法未定义时，调用`b`的此方法          |
| `*`  | 把两个操作数相乘             | `x = a * b`  | `fn __mul__(T1 other) -> (T2 result)`<br>`fn __rmul__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__mul__`方法未定义时，调用`b`的此方法          |
| `/`  | 将前一操作数除以后一操作数        | `x = a / b`  | `fn __div__(T1 other) -> (T2 result)`<br>`fn __rdiv__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__div__`方法未定义时，调用`b`的此方法          |
| `%`  | 取前一操作数除以后一操作数的余数     | `x = a % b`  | `fn __mod__(T1 other) -> (T2 result)`<br>`fn __rmod__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__mod__`方法未定义时，调用`b`的此方法          |
| `**` | 取前一操作数的幂，指数为后一操作数    | `x = a ** b` | `fn __pow__(T1 other) -> (T2 result)`<br>`fn __rpow__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__pow__`方法未定义时，调用`b`的此方法          |
| `@`  | 进行矩阵乘法，将前一操作数右乘后一操作数 | `x = a @ b`  | `fn __matmul__(T1 other) -> (T2 result)`<br>`fn __rmatmul__(T1 other) -> (T2 result)`\*<br>\*当`a`所在类的`__matmul__`方法未定义时，调用`b`的此方法 |

一元算术运算符：

| 运算符 | 描述   | 调用方式     | 调用的魔术方法                |
|:----|:-----|:---------|:-----------------------|
| `+` | 取正数  | `x = +a` | `fn __pos__() -> T`    |
| `-` | 取负数  | `x = -a` | `fn __neg__() -> T`    |
| `~` | 按位取反 | `x = ~a` | `fn __invert__() -> T` |

关系运算符：

| 运算符  | 描述                 | 调用方式         | 调用的魔术方法                              |
|:-----|:-------------------|:-------------|:-------------------------------------|
| `==` | 判断两个操作数是否相等        | `x = a == b` | `fn __eq__(T1 other) -> (T2 result)` |
| `!=` | 判断两个操作数是否不相等       | `x = a != b` | `fn __ne__(T1 other) -> (T2 result)` |
| `>`  | 判断前一操作数是否大于后一操作数   | `x = a > b`  | `fn __gt__(T1 other) -> (T2 result)` |
| `<`  | 判断前一操作数是否小于后一操作数   | `x = a < b`  | `fn __lt__(T1 other) -> (T2 result)` |
| `>=` | 判断前一操作数是否大于等于后一操作数 | `x = a >= b` | `fn __ge__(T1 other) -> (T2 result)` |
| `<=` | 判断前一操作数是否小于等于后一操作数 | `x = a <= b` | `fn __le__(T1 other) -> (T2 result)` |

逻辑运算符：

| 运算符    | 描述  | 调用方式           | 调用的魔术方法 |
|:-------|:----|:---------------|:--------|
| `&&`   | 逻辑与 | `x = a && b`   | 无       |
| `\|\|` | 逻辑或 | `x = a \|\| b` | 无       |
| `!`    | 逻辑非 | `x = !a`       | 无       |

位运算符：

| 运算符  | 描述   | 调用方式         | 调用的魔术方法                                                                                                                                        |
|:-----|:-----|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------------------|
| `&`  | 按位与  | `x = a & b`  | `fn __and__(T1 other) -> (T2 result)`<br>`fn __rand__(T1 other) -> (T2 result) `\*<br>\*当`a`所在类的`__and__`方法未定义时，调用`b`的`__rand__`方法             |
| `\|` | 按位或  | `x = a \| b` | `fn __or__(T1 other) -> (T2 result)`<br>`fn __ror__(T1 other) -> (T2 result) `\*<br>\*当`a`所在类的`__or__`方法未定义时，调用`b`的`__ror__`方法                 |
| `^`  | 按位异或 | `x = a ^ b`  | `fn __xor__(T1 other) -> (T2 result)`<br>`fn __rxor__(T1 other) -> (T2 result) `\*<br>\*当`a`所在类的`__xor__`方法未定义时，调用`b`的`__rxor__`方法             |
| `~`  | 按位取反 | `x = ~a`     | `fn __not__() -> (T2 result)`                                                                                                                  |
| `<<` | 左移   | `x = a << b` | `fn __lshift__(T1 other) -> (T2 result)`<br>`fn __rlshift__(T1 other) -> (T2 result) `\*<br>\*当`a`所在类的`__lshift__`方法未定义时，调用`b`的`__rlshift__`方法 |
| `>>` | 右移   | `x = a >> b` | `fn __rshift__(T1 other) -> (T2 result)`<br>`fn __rrshift__(T1 other) -> (T2 result) `\*<br>\*当`a`所在类的`__rshift__`方法未定义时，调用`b`的`__rrshift__`方法 |

其他运算符：

| 运算符       | 描述   | 调用方式              | 调用的魔术方法                                   |
|:----------|:-----|:------------------|:------------------------------------------|
| `.`       | 属性访问 | `x = obj.prop`    | 无                                         |
| `(as T)`  | 类型转换 | `x = (as T)value` | 无                                         |
| `[index]` | 索引访问 | `x = obj[index]`  | `fn __getitem__(T1 index) -> (T2 result)` |

### 对象更新操作符

对象更新操作符的写法是这样的：

```viola
obj1 = obj0 => {
    .prop1 = val1,
    .prop2 = val2
    // 花括号内可以继续增加，也可以为空，或者只有一条赋值语句
};
```

这段代码的含义是：令obj1的prop1等于val1，obj1的prop2等于val2，其余值与obj0相同。类似还有：

```viola
arr1 = arr0 => {
    [index1] = val1,
    [index2] = val2
    // ...
};
```

这段代码的含义是：令arr1的索引为index1的元素为val1，arr1的索引为index2的元素为val2，其余值与arr0相同。
**只有定义了`__setitem__`方法时，才能使用这种对象更新操作符。**

此外，还可以有如下写法：

```viola
arr2 = arr1 => {
    [start1:end1] = newArr1,
    [start2:end2] = newArr2,
    // ...
};
```

这段代码的含义是：令arr2的索引为start1到end1的元素依次为newArr1，arr2的索引为start2到end2的元素依次为newArr2，其余值与arr1相同。
**只有定义了`__setitem__`方法，且`__setitem__`方法接受切片作为索引时，才能使用这种对象更新操作符。**

### 运算符优先级

运算符优先级排序如下：

| 优先级 | 类别    | 运算符               | 结合性  |
|:----|:------|:------------------|:-----|
| 1   | 后缀    | `()` `[]` `.`     | 从左到右 |
| 2   | 一元运算符 | `+` `-` `!` `~`   | 从右到左 |
| 3   | 幂     | `**`              | 从右到左 |
| 4   | 乘除和取模 | `*` `/` `%` `@`   | 从左到右 |
| 5   | 加减    | `+` `-`           | 从左到右 |
| 6   | 移位    | `<<` `>>`         | 从左到右 |
| 7   | 比较    | `>` `>=` `<` `<=` | 从左到右 |
| 8   | 相等    | `==` `!=`         | 从左到右 |
| 9   | 按位与   | `&`               | 从左到右 |
| 10  | 按位异或  | `^`               | 从左到右 |
| 11  | 按位或   | `\|`              | 从左到右 |
| 12  | 逻辑与   | `&&`              | 从左到右 |
| 13  | 逻辑或   | `\|\|`            | 从左到右 |
| 14  | 条件    | `? :`             | 从右到左 |
| 15  | 对象更新  | `=> {}`           | 从右到左 |

## 循环

**注意：由于数据不可变性，Viola不提供循环语句。如有需要，请使用递归，或使用运行库
`viola.util.control_flow` 提供的循环函数。**

使用方式（先导入：`import viola.util.control_flow as control_flow;`）：

```viola
// 按顺序遍历数组并应用mapper（保证顺序）
fn forEach::<T, U>(T[] iterable, (T) -> (U) mapper) -> (U[] result);
sq forEach::<T>(T[] iterable, (T) -> () mapper) -> ();

// 循环执行updater，直到predicate为假（while语义）
fn while::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);
// 先执行一次updater再判断predicate（do-while语义）
fn doWhile::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);
```

例：

```viola
import viola.util.control_flow as control_flow;

fn increment(int x) -> (int r) {
    r = x + 1;
}

fn lessThanFive(int x) -> (bool c) {
    c = x < 5;
}

sq main() -> () {
    // 结果为5
    int result = control_flow.while::<int>(1, increment, lessThanFive);
    print("done");
}
```

`viola.util.functools` 提供函数式编程原语（`import viola.util.functools as functools;`）：

```viola
fn map::<T, U>(T[] iterable, (T) -> (U) mapper, bool useAsync) -> (U[] result);
fn filter::<T>(T[] iterable, (T) -> (bool) predicate, bool useAsync) -> (T[] result);
fn reduce::<T>(T[] iterable, (T[]) -> (T) reducer, uint32 reduceSize, bool useAsync) -> (T result);
fn expand::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);
fn expandWithCut::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);
```

## 分支

Viola提供了以下两类分支语句：

- `if`语句的格式如下：

```viola
if (condition0) {
    // 当条件condition0满足时执行
}
elif (condition1) { // 可选，可以有多个elif语句，必须跟随在if语句或elif语句之后
    // 当前述条件都不满足，且条件condition1满足时执行
}
else { // 可选，必须跟随在if语句或elif语句之后
    // 当前述条件都不满足时执行
}
```

- `match`语句的格式如下（**TODO: 添加match语句的实现**）：

```viola
match value {
    case pattern0 {
        // 当value与pattern0匹配时执行，执行后退出匹配
    }
    case pattern1 {
        // 当value与pattern1匹配时执行，执行后退出匹配
    }
    case _ { // 可选
        // 当value与上述pattern都不匹配时执行
    }
}
```

## 并发

- `async`修饰的语句会在自动保证线程安全的情况下异步执行。例如：

```viola
async int a = 1 + 2; // 异步执行
async int b = getValue();
int c = 3 + 4; // 同步执行
int d = a + b + c; // 在a、b计算完成后才会计算d
```

运行库中声明的原生函数（`viola.math`、`viola.stat`、`viola.threads`、
`viola.lang`、`viola.io`、`viola.os`）同样可以异步调用，例如
`async string text = read(f);`、`async Stat st = viola.os.stat(".");`。

## 函数

函数是一组语句的集合，可以有返回值。每个Viola程序都至少有一个函数，即`main`函数。

### 函数的声明与定义

Viola中的函数声明的一般形式如下：

```viola
关键字 函数名(参数列表) -> (返回值类型列表);
```

其中：

- 关键字可以为`fn`或`sq`，前者表示按需执行（不需要按顺序输入语句，求出所有返回值后自动退出，要求必须有返回值），后者表示顺序执行。
- 函数名遵循标识符命名规则。
- 参数列表为若干对参数类型与形参名称，每对之间用逗号分隔。
- 返回值类型列表为若干类型标识符，用逗号分隔。

例如：

```viola
fn max(int a, int b) -> (int);
sq write(string path, string content) -> ();
```

**TODO: 添加lambda表达式的实现（如下）**

```viola
(T1 arg1, T2 arg2, ...) -> (expr1, expr2, ...)

// 等价于：

fn (T1 arg1, T2 arg2, ...) -> (T1 result1, T2 result2, ...) {
    result1 = expr1;
    result2 = expr2;
    // ...
}
```

Viola中的函数定义的一般形式如下：

```viola
关键字 函数名(参数列表) -> (返回值列表) {函数体}
```

其中返回值列表为若干对返回值类型与变量名，每对之间用逗号分隔。返回值不需要在函数体中再次声明。

例如：

```viola
fn max(int a, int b) -> (int result) {
    result = a > b ? a : b;
}
```

### return语句

`sq`函数可以使用`return`语句强制返回。**`return`后应当直接跟随分号**，因为返回变量在函数声明处（`-> (返回值列表)`）就已经确定。例：

```viola
sq countTo(uint32 n) -> () {
    if (n == 0) {
        return;
    }
    countTo(n - 1);
}
```

如果编译器发现`return`处有返回值尚未被赋值，会报出编译时错误。返回值为`void`（即`()`）时也可以使用`return`。**注意：`fn`函数按需执行，求出所有返回值后自动退出，不允许使用`return`。**

Viola支持匿名函数，格式如下：

```viola
关键字(参数列表) -> (返回值列表) {函数体}
```

### 函数调用

Viola中的函数调用的一般形式如下：

```viola
函数名(参数列表); // 如不需要接收返回值
返回值列表 = 函数名(参数列表); // 如需要接收返回值
```

例如：

```viola
write("test.txt", "Hello, World!");
int a = max(1, 2);
```

**接收多个返回值时，返回值目标的个数必须与被调函数的返回值个数相同，且按位置一一对应。**
函数返回几个值，就要写几个目标变量（多返回值目标之间用逗号分隔）：

```viola
fn two() -> (int x, int y) { x = 1; y = 2; }

int a, int b = two(); // 正确：2个目标对应2个返回值
```

不支持"最后一个目标接收其余返回值"的写法（即尾部解包）：目标的个数不得少于
返回值个数，多于返回值个数同样会报错：

```viola
fn three() -> (int x, int y, int z) { x = 1; y = 2; z = 3; }

int a, int[] rest = three(); // 错误：不接受由rest接收其余返回值的写法
int a, int b = three();      // 错误：目标个数（2）少于返回值个数（3）
```

先声明后赋值的形式同样要求个数一致：

```viola
int a;
int b;
a, b = two();
```

**计划中（0.1版本尚未实现）**：尾部解包需要显式标记目标为由剩余返回值构成的
元组类型，形如`*Type`（`*`标记该目标接收其余返回值，括号给出其元组类型）：

```viola
double x, *(double, double) yz = getTriple(); // 计划形式：yz接收后两个返回值
```

该形式尚未实现，当前会被报为"目标个数少于返回值个数"的编译错误，错误信息中会
给出上述计划形式的写法。目前如需接收全部返回值，请给出与返回值个数相同的目标。

调用时，参数列表也可以乱序传值，例如：

```viola
write(content="Hello, World!", path="test.txt"); // 乱序传值的部分必须位于参数列表的最后
```

Viola中的函数参数，如果是基本数据类型则按值传递，否则按引用传递。函数参数的默认值可以指定，格式如下：

```viola
<关键字> <函数名>(<参数列表>, <参数名与参数默认值的列表>) -> (<返回值列表>) {<函数体>}
// “参数名与参数默认值的列表”的写法是：T var1 = defaultValue1, T var2 = defaultValue2, ...
// “参数名与参数默认值的列表”必须位于整个参数列表的最后
```

例如：

```viola
double log(double x, double base = 2.71828) -> (double result) {...}
```

**TODO: 为以下功能添加标准库支持**

## 数组

数组是一种数据结构，用于存储多个相同类型的数据。

### 数组的声明与定义

在Viola中，数组的声明与定义方式如下：

```viola
T[] var; // T为元素的类型
T[] var = [val1, val2, ...]; // 初始化数组
```

例如：

```viola
uint[] fibonacci = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55];
```

### 数组的访问与操作

数组中的元素的访问方式如下（**注意：索引从0开始**）：

```viola
T item = var[index];
```

也可以用以下方式截取一段数组：

```viola
T[] slice0 = var[startIndex:endIndex]; // 截取从第startIndex项（含）到第endIndex项（不含）的所有元素
T[] slice1 = var[startIndex:]; // 截取从第startIndex项（含）到末尾的所有元素
T[] slice2 = var[:endIndex]; // 截取从开头到第endIndex项（不含）的所有元素
T[] slice3 = var[:]; // 截取整个数组
T[] slice4 = var.slice(startIndex, endIndex); // 相当于slice0
```

数组支持对象更新操作符，例如：

```viola
int[] arange = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
int[] newArray0 = arange => {
    [1] = 10;
    [2] = 40;
};
int[] newArray1 = arange => {
    [0:4] = [5, 10, 20, 30];
};
```

数组也支持一些方法，例如：

```viola
int[] arange0 = [0, 1, 2, 3];
int[] arange1 = [4, 5, 6, 7];
int[] arange2 = arange0.concat(arange1); // arange2 = [0, 1, 2, 3, 4, 5, 6, 7]
int[] array0 = arange0.append(9); // array0 = [0, 1, 2, 3, 9]
int[] array1 = arange0.insert(1, 10); // array1 = [0, 10, 1, 2, 3]
size_t array0Length = arange0.length(); // array0Length = 5
```

此外，还有一些较为通用的内置函数适用于数组，例如：

```viola
int[] array2 = filter(arange2, fn(int x) -> (bool f) {f = x > 2}, async=false); // array2 = [3, 4, 5, 6, 7]
int[] array3 = map(arange0, fn(int x) -> (int f) {f = x * 2}, async=true); // array3 = [0, 2, 4, 6]
```

### 元素类型不同的数组

数组的元素类型不同时（如`int32[]`与`int64[]`），把前者赋给后者、或作为实参传给
元素类型不同的形参，都会按目标元素类型**逐个元素转换并复制出一个新数组**：

```viola
int32[] source = [1, 2, 3];
int64[] widened = source; // widened = [1, 2, 3]，元素类型为int64
int64 total = sumOfInt64(source); // 实参同样按形参的元素类型转换
```

由于数据不可变，复制出的新数组与源数组互不影响；类元素数组按同样的方式转换
（元素为子类对象、目标元素为父类时转换为父类，不需要复制元素对象本身）。

## 字符串

字符串是两端带引号（单引号或双引号均可）的一段文本。

### 字符串的声明与定义

在Viola中，字符串的声明与定义方式如下：

```viola
string var; // 声明一个字符串变量
string var0 = "Hello, World! "; // 定义一个字符串变量
```

### 字符串的访问与操作

可以用以下方式拼接两个字符串：

```viola
string var1 = var0 + "Welcome to Viola! "; // var1 = "Hello, World! Welcome to Viola! "
string var2 = var0 * 2; // var2 = "Hello, World! Hello, World! "
string var3 = var0.concat("Welcome to Viola! "); // 相当于var1
string var4 = var0.repeat(2); // 相当于var2
```

也可以用以下方式截取字符串：

```viola
string var5 = var0[startIndex:endIndex]; // 截取从第startIndex项（含）到第endIndex项（不含）的所有字符
string var6 = var0[startIndex:]; // 截取从第startIndex项（含）到末尾的所有字符
string var7 = var0[:endIndex]; // 截取从开头到第endIndex项（不含）的所有字符
string var8 = var0[:]; // 截取整个字符串
string var9 = var0.slice(startIndex, endIndex); // 相当于var5
```

类似数组，字符串也支持一些方法：

```viola
string[] var10 = var0.split(" "); // var10 = ["Hello,", "World!", ""]
string var11 = var0.replace("World", "Viola"); // var11 = "Hello, Viola! "
size_t var12 = var0.length(); // var12 = 14
bool var13 = var0.startsWith("Hello"); // var13 = true
bool var14 = var0.endsWith("Hello"); // var14 = false
```

### 字符串的常用方法（0.1新增）

`string`类（命名空间`viola.lang`）还提供以下方法（未找到子串时
`find`/`rfind`/`index`/`rindex`返回`UINT32_MAX`；这些string方法本身不抛出异常）：

```viola
uint32 var15 = var0.count("o");      // 统计子串非重叠出现的次数
uint32 var16 = var0.find("World");   // 子串首次出现的索引
uint32 var17 = var0.rfind("o");      // 子串最后一次出现的索引
uint32 var18 = var0.index("World");  // 与find一致
uint32 var19 = var0.rindex("o");     // 与rfind一致
double var20 = "3.14".float();       // 解析为浮点数（支持inf/nan与科学计数法）
int64 var21 = "42".int();            // 解析为十进制整数
int64 var22 = "ff".int(16);          // 按base（2~16）解析为整数
string var23 = string.fromInt(-42);  // 整数转换为字符串（静态方法）
string var24 = string.fromInt(255, 16); // 按base（2~16）转换（静态方法）
string var25 = string.fromFloat(3.14);  // 浮点数转换为字符串（静态方法）
bool var26 = "abc123".isalnum();     // 是否全部为字母或数字
bool var27 = "abc".isalpha();        // 是否全部为字母
bool var28 = "123".isdecimal();      // 是否全部为十进制数字
bool var29 = "123".isdigit();        // 是否全部为数字
bool var30 = "abc_1".isidentifier(); // 是否为合法标识符
bool var31 = "abc".islower();        // 是否全部为小写
bool var32 = "123".isnumeric();      // 是否全部为数字（含Unicode数字）
bool var33 = "abc".isprintable();    // 是否全部为可打印字符
bool var34 = " \t".isspace();        // 是否全部为空白字符
bool var35 = "ABC".isupper();        // 是否全部为大写
string var36 = "ab".ljust(4, "*");   // 左侧用fillChar填充到指定长度（"ab**"）
string var37 = " ab ".lstrip();      // 去除左侧空白（默认" \t\n\r"）
string var38 = "xyab".lstrip("xy");  // 去除左侧toRemove集合中的字符
string var39 = "ab".rjust(4, "*");   // 右侧用fillChar填充到指定长度（"**ab"）
string var40 = " ab ".rstrip();      // 去除右侧空白
string var41 = " ab ".strip();       // 去除两侧空白
string var42 = "AbC".swapcase();     // 大小写互换（"aBc"）
string var43 = "42".zfill(5);        // 左侧补零（"00042"，符号保持在最前）
string var44 = var0.replace("l", "L", 1); // 替换子串（count为0时替换全部）
```

字符串与数字互转的方法`int`/`float`/`fromInt`/`fromFloat`位于`viola.lang`
命名空间（使用前需`import viola.lang;`或`from viola.lang import *;`）。

### 值到字符串的转换（toString）

基本数据类型（整型、浮点型、布尔与字符串）的值可以调用`toString`方法转换为
字符串：

```viola
string a = (1 + 2).toString();   // "3"
string b = 3.5.toString();       // "3.5"
string c = true.toString();      // "true"
string d = "text".toString();    // "text"（字符串返回自身）
```

转换由`string`类上的静态转换函数实现（`_int32ToString`/`_float64ToString`等），
编译器按接收者的类型自动选择，无需显式指定。浮点数的转换结果与`string.fromFloat`
一致（最多15位有效数字、去除多余的尾零），布尔的转换结果为`true`/`false`
（与字面量一致）。整型之间的差异按C的隐式转换处理（如`int8`按`int32`转换）。

自定义类不参与上述转换：如需要，请为该类定义自己的方法或运算符。

## 输入与输出

Viola提供了一些用于输入与输出的函数。这些函数位于`viola.io`命名空间，
使用前需要导入：

```viola
import viola.io as io;
// 或
import viola.io.print;
import viola.io.perror;
import viola.io.input;
```

### 标准输入输出

要向标准输出流进行输出，可以使用`print`函数，函数声明如下：

```viola
sq print(string content = "") -> ();
```

未来将会加入更多的`print`函数的调用方式。如果希望访问标准输出流，请使用`sys.stdout`。

类似地，要向标准错误流进行输出，可以使用`perror`函数，函数声明如下：

```viola
sq perror(string content = "") -> ();
```

如果希望访问标准错误流，请使用`sys.stderr`。

此外，如果要从标准输入流进行输入，可以使用`input`函数，函数声明如下：

```viola
sq input() -> (string);
```

如果希望访问标准输入流，请使用`sys.stdin`。

### 对文件的输入与输出

首先我们需要打开文件，并获取文件句柄，函数声明如下：

```viola
fn open(string path, string mode = "r", string encoding = "utf-8") -> (file);
// 文件句柄离开作用域时，会自动调用file.__del__()函数
```

关于读写文件的函数，声明如下：

```viola
fn read(file f) -> (string);
fn readBytes(file f) -> (uint8[]);
sq write(file f, string content) -> ();
sq writeBytes(file f, uint8[] content) -> ();
```

**当有多个线程访问同一个文件时，如果文件正在被写入，那么后续访问的线程将会被阻塞，直到写入操作完成。**

## 数学函数（viola.math）

`viola.math`提供数学常量与函数（使用前需`from viola.math import *;`或`import viola.math as math;`）。

常量：`pi`、`e`、`tau`（2π）、`inf`（正无穷）、`nan`（非数值）。

math.h基本函数：`sqrt`、`sin`、`cos`、`tan`、`asin`、`acos`、`atan`、
`sinh`、`cosh`、`tanh`、`asinh`、`acosh`、`atanh`、`exp`、`log`、
`log10`、`log2`、`log1p`、`fabs`、`floor`、`ceil`、`round`、`trunc`、
`pow`、`atan2`、`fmod`、`fmin`、`fmax`。

0.1新增函数：

```viola
fn radians(double x) -> (double result);        // 角度制转弧度制
fn degrees(double x) -> (double result);        // 弧度制转角度制
fn dist(double[] a, double[] b) -> (double result);   // 欧几里得距离（a与b长度需相同）
fn hypot(double[] a) -> (double result);        // 欧几里得范数
fn log(double x, double base) -> (double result);     // 任意底对数（重载）
fn erf(double x) -> (double result);            // 误差函数
fn erfc(double x) -> (double result);           // 补误差函数
fn tgamma(double x) -> (double result);         // 伽马函数
fn lgamma(double x) -> (double result);         // 伽马函数的自然对数
fn factorial(double x) -> (double result);      // 阶乘
fn frexp(double x) -> (double mantissa, int32 exp);    // 指数与尾数分离
fn ldexp(double x, int32 exp) -> (double result);      // 指数与尾数组合
fn gcd(int64 a, int64 b) -> (int64 result);     // 最大公约数
fn lcm(int64 a, int64 b) -> (int64 result);     // 最小公倍数
fn perm(int64 n, int64 k) -> (int64 result);    // 排列数
fn comb(int64 n, int64 k) -> (int64 result);    // 组合数
fn modf(double x) -> (double fractional, double integer); // 整数部分与小数部分分离
fn remainder(double x, double y) -> (double result);      // IEEE 754风格的小数余数
fn isnan(double x) -> (bool result);            // 是否为nan
fn isinf(double x) -> (bool result);            // 是否为无穷
fn isfinite(double x) -> (bool result);         // 是否为有限值
```

## 操作系统接口（viola.os）

`viola.os`绑定Windows和POSIX的相关接口（使用条件编译，使用前需
`import viola.os;`）。其中涉及到文件操作的函数由子线程发送请求、
由主线程串行执行。**注意：这些系统接口本身不抛出异常，执行失败时
`sq`函数静默忽略、`fn`函数返回约定值（-1、0或空字符串）；
用户代码可用`try`/`catch`捕获自行抛出的异常（见“异常处理”一节）。**

常量与类型：

```viola
int32 STDIN_FILENO;   // 0
int32 STDOUT_FILENO;  // 1
int32 STDERR_FILENO;  // 2
// open的flags常量（POSIX取值，Windows在运行库内转换）：
uint32 O_RDONLY; uint32 O_WRONLY; uint32 O_RDWR;
uint32 O_CREAT; uint32 O_EXCL; uint32 O_TRUNC; uint32 O_APPEND; uint32 O_BINARY;
// 文件状态（字段与Python的stat_result一致）：
class Stat { uint32 st_mode; uint64 st_ino; uint64 st_dev; uint64 st_nlink;
             uint32 st_uid; uint32 st_gid; uint64 st_size;
             uint64 st_atime; uint64 st_mtime; uint64 st_ctime; }
// 文件系统信息（字段与Python的statvfs_result一致）：
class StatVFS { uint64 f_bsize; uint64 f_frsize; uint64 f_blocks; uint64 f_bfree;
                uint64 f_bavail; uint64 f_files; uint64 f_ffree; uint64 f_favail;
                uint64 f_flag; uint64 f_namemax; }
```

常用函数（完整清单见`viola_libs/viola/os.vla`）：

```viola
fn access(string path, uint32 mode) -> (bool result);      // 判断路径是否可按mode访问
sq chdir(string path) -> ();                               // 改变当前工作目录
sq chmod(string path, uint32 mode) -> ();                  // 改变文件权限
sq close(int32 fd) -> ();                                  // 关闭文件描述符
fn dup(int32 fd) -> (int32 result);                        // 复制文件描述符
fn dup2(int32 fd1, int32 fd2) -> (int32 result);           // 复制到指定编号
fn fstat(int32 fd) -> (Stat result);                       // 文件描述符状态
fn getcwd() -> (string result);                            // 当前工作目录
fn getuid() -> (uint32 result);                            // 用户ID（Windows上恒为0）
fn isatty(int32 fd) -> (bool result);                      // 是否为终端
fn listdir(string path) -> (string[] result);              // 列出目录内容
fn lstat(string path) -> (Stat result);                    // 路径状态（不跟随符号链接）
sq lseek(int32 fd, int32 offset, int32 whence) -> (int32 result); // 移动读写位置
sq makedirs(string path, uint32 mode = 0o777) -> ();       // 递归创建目录
sq mkdir(string path, uint32 mode = 0o777) -> ();          // 创建目录
sq open(string path, uint32 flags, uint32 mode = 0o666) -> (int32 fd); // 打开文件
sq pipe() -> (int32 result);                               // 创建管道（返回读端fd）
sq popen(string command, string mode) -> (file result);    // 执行命令（返回viola.io.file）
sq read(int32 fd, uint32 nbyte) -> (string result);        // 读取（最多nbyte字节）
sq remove(string path) -> ();                              // 删除文件
sq rename(string oldPath, string newPath) -> ();           // 重命名
sq rmdir(string path) -> ();                               // 删除空目录
fn stat(string path) -> (Stat result);                     // 路径状态
fn statvfs(string path) -> (StatVFS result);               // 文件系统信息
sq unlink(string path) -> ();                              // 删除文件（同remove）
sq utime(string path, uint32 atime, uint32 mtime) -> ();   // 设置访问与修改时间
sq write(int32 fd, string data) -> (uint32 result);        // 写入（返回写入字节数）
```

其余函数（如`sleep`、`exit`、`getEnv`、`time`、`system`等）保持不变。

## 路径处理（viola.os.path）

`viola.os.path`提供路径处理功能（Windows使用反斜杠语义，POSIX使用
正斜杠语义；使用前需`import viola.os.path;`）：

```viola
string pathsep;                                       // 路径分隔符（Windows为";"，POSIX为":"）
fn abspath(string path) -> (string result);           // 绝对路径表示
fn basename(string path) -> (string result);          // 最后一个组件
fn commonpath(string[] paths) -> (string result);     // 最长公共目录前缀
fn commonprefix(string[] paths) -> (string result);   // 最长公共字符前缀
fn dirname(string path) -> (string result);           // 目录部分
fn exists(string path) -> (bool result);              // 是否存在
fn getatime(string path) -> (uint64 result);          // 最后访问时间（秒）
fn getctime(string path) -> (uint64 result);          // 创建时间（秒）
fn getmtime(string path) -> (uint64 result);          // 最后修改时间（秒）
fn getsize(string path) -> (uint64 result);           // 文件大小（字节）
fn isabs(string path) -> (bool result);               // 是否为绝对路径
fn isdir(string path) -> (bool result);               // 是否为目录
fn isfile(string path) -> (bool result);              // 是否为普通文件
fn islink(string path) -> (bool result);              // 是否为符号链接（Windows上恒为false）
fn ismount(string path) -> (bool result);             // 是否为挂载点
fn join(string[] paths) -> (string result);           // 用分隔符连接
fn normpath(string path) -> (string result);          // 规范化（折叠".."、"."与重复分隔符）
fn realpath(string path) -> (string result);          // 规范绝对路径（解析符号链接）
fn samefile(string path1, string path2) -> (bool result);     // 是否指向同一文件
fn sameopenfile(int32 fd1, int32 fd2) -> (bool result);       // 文件描述符是否指向同一文件
fn split(string path) -> (string[] result);           // 拆分为(head, tail)
fn splitext(string path) -> (string[] result);        // 拆分为(root, ext)
```

## 文件状态（viola.stat）

`viola.stat`提供文件类型与权限位的常量及判断函数（使用前需
`import viola.stat;`）。Windows上组/其他权限位与用户权限位取相同值，
`S_ISBLK`/`S_ISLNK`/`S_ISSOCK`在Windows上恒为false。

```viola
uint32 S_IFDIR; uint32 S_IFREG;   // 文件类型位
uint32 S_IRUSR; uint32 S_IWUSR; uint32 S_IXUSR;   // 用户权限位
uint32 S_IRGRP; uint32 S_IWGRP; uint32 S_IXGRP;   // 组权限位
uint32 S_IROTH; uint32 S_IWOTH; uint32 S_IXOTH;   // 其他权限位
fn S_ISBLK(uint32 mode) -> (bool result);   // 块设备
fn S_ISCHR(uint32 mode) -> (bool result);   // 字符设备
fn S_ISDIR(uint32 mode) -> (bool result);   // 目录
fn S_ISFIFO(uint32 mode) -> (bool result);  // 命名管道
fn S_ISLNK(uint32 mode) -> (bool result);   // 符号链接
fn S_ISREG(uint32 mode) -> (bool result);   // 普通文件
fn S_ISSOCK(uint32 mode) -> (bool result);  // 套接字
fn filemode(uint32 mode) -> (string result); // 转换为"-rwxr-xr-x"形式
```

## 线程调度（viola.threads）

`viola.threads`提供线程调度系统（使用前需`from viola.threads import *;`）：

```viola
sq addThread(uint32 number) -> ();       // 添加线程
sq delThread(uint32 number) -> ();       // 删除线程（等待当前任务完成后移除）
fn getThreadsNum() -> (uint32 number);   // 获取线程数量
sq setThreadsNum(uint32 number) -> ();   // 设置线程数量
```

## 函数值（viola.lang.function）

0.1起，所有函数（无论静态还是动态）作为值使用时都被封装为
`viola.lang.function.Function`结构体（原`Closure`类，是`object`的子类），
但**调用静态函数时仍然直接传递函数指针**。`Function`类包含以下成员：

- `Pointer::<viola.lang.function.AsyncPtr> asyncPtr`：异步函数指针。
- `Pointer::<viola.lang.function.SyncPtr> syncPtr`：同步函数指针。
- `Pointer::<Tuple> $capture`：捕获的环境（元组类型）。
- `string[] argNames`：参数名称（不包括捕获的环境参数）。

调用函数值（闭包）时支持**按参数名传参**（`name = value`形式），
未按位置传入的参数按`argNames`在运行时匹配。

## 数组类（viola.util.array）

`viola.util.array`定义泛型数组类`Array::<T>`（`import viola.util.array;`），
提供`__getitem__`（索引与切片）、`length`、`concat`、`append`、
`insert`、`__setitem__`等方法，用于需要对象化数组的场景。

## 全局资源管理器（viola.lang.global_resource_manager）

`viola.lang.global_resource_manager`提供基于请求的全局资源管理器：
子线程通过请求队列发起请求，主线程在空闲期间串行执行请求并返回数据
（文件读写等资源操作即基于此机制）。0.1新增以下接口：

```viola
// 以Viola函数注册请求处理器
sq register_request_handler(uint32 request_id, (_Request) -> () handler) -> ();
```

## 类与对象

在Viola中，每个类都是一个数据类型，包含若干**属性**（存储的数据）和**方法**（类中定义或声明的函数）。

### 类的声明与定义

类的声明与定义方式如下：

```viola
class 类名(父类列表) {
    属性列表
    构造函数
    其他方法
}
```

其中，父类列表及其两边的括号可以省略。例如：

```viola
class Image {
    uint channels; // 属性，默认为public，但也支持public和private，也可以显式写出protected
    uint height;
    uint width;
    uint8[] pixels;
    
    public sq __new__(uint channels, uint height, uint width, uint8[] pixels) -> (this) { // 构造函数，声明必须为public sq __new__(...) -> (this)
        this.channels = channels;
        this.height = height;
        this.width = width;
        this.pixels = pixels;
    }
    
    static public sq load(string path) -> (Image img) {...} // 静态方法，指不使用类实例的方法
    
    static public fn black(uint channels, uint height, uint width) -> (Image img) {
        pixels = zeros::<uint8>(height * width * channels);
        img = Image(channels, height, width, pixels);
    }
    
    public sq save(string path, string format = "png") -> () {...}
    
    public fn resize(uint height, uint width) -> (Image img) {...}
    
    public fn crop(uint x, uint y, uint width, uint height) -> (Image img) {...}
    
    public fn fill(uint8[] color) -> (Image img) {
        img = this => {
            .pixels = color.repeat(this.height * this.width);
        };
    }
    
    public fn drawLine(uint x1, uint y1, uint x2, uint y2, uint8[] color) -> (Image img) {...}
}
```

**包含动态属性的类必须添加构造方法，并且构造方法必须为所有动态属性赋值。**

### 对象的声明、定义与访问

之后，我们可以创建对象，并访问对象属性和方法：

```viola
Image img0; // 声明一个对象变量
Image img1 = Image.black(3, 100, 100); // 注意：这里调用的是静态方法
img2 = img1.drawLine(0, 0, 100, 100, [255, 255, 255]); // 这里既可以调用静态方法，也可以调用实例方法
Image img3(3, 100, 100, zeros::<uint8>(30000)); // 相当于Image img3 = Image(3, 100, 100, zeros::<uint8>(30000));
```

类似基本数据类型，我们也可以直接将类类型的数据传入函数。例如：

```viola
sq toBytes(Image img) -> (uint8[] result) {...}
```

### 访问修饰符

对于访问修饰符`public`、`protected`和`private`，Viola 0.1起按**模块**解释（其中“+”表示可以访问，“-”表示不可以访问）：

| 访问者 | public | protected | private |
|-----|--------|-----------|---------|
| 自身（类成员为类自身，模块成员为模块自身） | + | + | + |
| 同一模块内的其他成员 | + | + | - |
| 其他模块 | + | - | - |

- `public`：公共访问修饰符，表示该成员可以被任何其他模块访问。
- `protected`：受保护访问修饰符，表示该成员只能被同一模块中的其他成员访问。
- `private`：私有访问修饰符，表示该成员只能被自身访问。
- 无访问修饰符的**默认情况为`public`**（0.1起；早期版本曾为`protected`）。

如果试图访问不应被访问的成员，编译器会报出编译时错误。

## 类继承

Viola支持类继承。**在子类的构造方法中，必须调用父类的构造方法。** 定义子类的格式如下：

```viola
class 子类名 extends 父类名 {...}
```

例如：

```viola
class Bear extends Mammal {...}
```

Viola不支持多重继承。

## 接口（interface）

`interface`关键字声明接口。接口不能被实例化，只允许包含方法和静态属性，其中的方法都是抽象方法。接口允许多继承（用逗号分隔多个接口）。例：

```viola
interface Shape2D {
    public static uint32 KIND = 7;
    fn area() -> (double result);
}
```

类使用`impl`关键字实现接口，且必须实现接口的所有抽象方法。例：

```viola
class Circle impl Shape2D {
    public double radius;

    public sq __new__(double r) -> (this) {
        this.radius = r;
    }

    public fn area() -> (double result) {
        result = 3.14159 * this.radius * this.radius;
    }
}
```

## 枚举（enum）

枚举用`enum`关键字声明一组具名的常量。格式如下：

```viola
enum 枚举名 [extends 基于类型] {
    项名 [= 取值],
    ...
}
```

基于类型默认为`uint32`，也可以显式指定（如`enum Status extends int32 { ... }`）。
枚举项之间以逗号或分号分隔，允许尾随分隔符。省略取值的项按递增取值：第一项为
0，其后每一项为前一项的取值加一；显式给出取值后同样从该值继续递增：

```viola
enum Color {
    RED,        // 0
    GREEN = 5,  // 5
    BLUE        // 6
}
```

前一项的取值不是整数字面量（如`= 1 + 1`）时无法推算后续取值，此时后面的项必须
显式给出取值，否则报编译错误。

枚举是类型，枚举项通过枚举名访问：

```viola
Color c = Color.RED;
if (c == Color.GREEN) {
    ...
}
```

枚举类型的值在C层即其基于类型，因此可以与整数互相转换、参与算术与比较：

```viola
int v = Color.GREEN;      // 5
Color next = Color.BLUE;
```

枚举名与类一样是类型名，可以像类一样导出到其他模块使用（`from mylib import Color;`）。
基于类型相同的不同枚举是不同的类型，不能互相赋值。

**注意：枚举没有方法，也没有针对枚举的分支/匹配语法；枚举项不能像类的静态属性那样被赋值。**

## final

`final`关键字声明一个类或方法为最终的，不能被继承或重写。例：

```viola
final class FinalBox {
    public int value;

    public sq __new__(int v) -> (this) {
        this.value = v;
    }
}

class MyClass {
    final fn myMethod(...) -> (...) {...}
}
```

## static

`static`关键字声明类的静态方法或静态属性。静态属性是全局唯一的，且要求有初始值。例：

```viola
class Counter {
    static uint32 total = 0;

    public static fn getTotal() -> (uint32 result) {
        result = Counter.total;
    }
}
```

## unsafe与wrapper

`unsafe`作为成员声明的前缀，表示非安全成员。这种变量允许自身和属性被重新赋值，但是只允许作为`wrapper`类的成员，并且需要由用户手动管理内存。涉及到对`unsafe`变量进行写操作的语句会被强制串行化。`unsafe`变量允许存在于`wrapper`方法中，但不得被返回。例：

```viola
wrapper class MyClass {
    unsafe uint32 myProperty = 0x114514;
}
```

`unsafe`作为类声明的前缀，表示这一类型的所有对象都是非安全的。

`wrapper`作为类声明的前缀，表示非安全类的包装类。需要用户自行实现
`sq __del__() -> ();`方法来清理内部的`unsafe`对象，并且最后需要有`del(super);`语句
来确保普通成员也被释放。编译器会保证此方法被正常调用。基本数据类型的`unsafe`变量
不需要手动清理。例：

```viola
wrapper class MyClass {
    unsafe Pointer::<uint8> rawData;

    public sq __new__() -> (this) {
        // 分配rawData（通常通过C语言互操作）
    }

    public sq __del__() -> () {
        // 释放rawData
        del(super);
    }
}
```

## 丢弃变量（_）

`_`用于接收被丢弃的值。此变量可以在同一作用域内被多次声明和赋值，但是不可被读取。例：

```viola
int32 x, string _ = *(0x114514, "1919810");
```

## export

`export`关键字声明一个符号（类、函数等）需要导出为库，可被外部C代码链接。例：

```viola
export class MyClass {...}
export fn myFunction(...) -> (...) {...}
export sq mySequence(...) -> (...) {...}
```

## 多态

在Viola中，多态性是通过方法重写来实现的。如果要求一个类不能被实例化，应当使用abstract关键字，使之成为**抽象类**。
在抽象类中，可以声明**抽象方法**，要求非抽象的子类实现。例如：

```viola
abstract class Shape {
    public abstract fn area() -> (double result);
    public abstract fn perimeter() -> (double result);
    public abstract fn draw(Image img, uint x, uint y, double rotate, uint8[] color) -> (Image newImg);
}

abstract class Triangle extends Shape { // 抽象类Triangle继承抽象类Shape，不强制要求实现前述抽象方法
    double a;
    double b;
    double c;
    
    public fn perimeter() -> (double result) { // 重写抽象方法
        result = a + b + c;
    }
    
    public sq __new__(double a, double b, double c) -> (this) {
        this.a = a;
        this.b = b;
        this.c = c;
    }
}

class RightTriangle extends Triangle { // 不是抽象类，必须实现抽象方法
    public sq __new__(double a, double b) -> (this) {
        super = Triangle(a, b, sqrt(a * a + b * b)); // 调用父类构造函数初始化父类成员
    }
    
    public fn area() -> (double result) {
        result = 0.5 * this.a * this.b;
    }
    
    public fn draw(Image img, uint x, uint y, double rotate, uint8[] color) -> (Image newImg) {...}
}
```

## 泛型

**TODO: 实现泛型的类型约束，以及union类型。**

Viola支持泛型。泛型类和泛型函数（方法）的定义格式如下：

```viola
class 类名::<T1, T2, ..., TN> extends 父类 {...} // 其中T1、T2……TN为类型参数
```

例如：

```viola
class PCMWave::<T> {
    static uint8[] _RIFF = ascii("RIFF");
    uint32 riffSize;
    static uint8[] _WAVE = ascii("WAVE");
    static uint8[] _fmt = ascii("fmt ");
    uint32 fmtSize;
    uint16 fmtTag;
    uint16 channels;
    uint32 sampleRate;
    uint16 blockAlign;
    uint16 bitsPerSample;
    static T[] _data = ascii("data"); // 泛型类成员变量
    
    public sq __new__(...) -> (this) {...}
    public fn convertTo::<U>() -> (PCMWave::<U> result) {...} // 泛型方法
    public fn convertToBytes() -> (uint8[] result) {...}
    static public fn load(string path) -> (PCMWave::<T> wave) {...}
    public sq save(string path) -> () {...}
}
```

引用其他模块中定义的泛型类型时，类型名可以用模块别名或完整模块路径限定
（在声明与表达式两种位置均可用）：

```viola
import viola.util.array as array;

sq main() -> () {
    int[] data = [1, 2, 3];
    array.Array::<int> a(data);                          // 声明
    array.Array::<int> b = array.Array::<int>(data);     // 表达式
}
```

以`import viola.util.array;`引入时，也可以直接书写完整模块路径
（`viola.util.array.Array::<int>`）。注意同一文件中不要混用两种写法：
以别名导入时，完整模块路径不参与解析。

泛型类（如`viola.util.array.Array::<T>`）的实例由定义该泛型类的模块生成，
调用方模块只需引入该模块即可正常使用。

## 重载

在同一作用域内，可以声明多个同名函数（功能通常类似），但参数列表中的类型必须不同。这种做法称为**重载**。例如：

```viola
sq printNumber(int value) -> () {
    print("整数值为：");
    print(value.toString() + "\n");
}

sq printNumber(double value) -> () {
    print("浮点值为：");
    print(value.toString() + "\n");
}
```

我们还可以重载运算符。像这样：

```viola
class Vector2D {
    double x;
    double y;
    
    public sq __new__(double x, double y) -> (this) {
        this.x = x;
        this.y = y;
    }
    
    public fn __add__(Vector2D other) -> (Vector2D result) { // 重载运算符“+”
        result = Vector2D(this.x + other.x, this.y + other.y);
    }
}
```

在这种情况下，以下代码就是有效的：

```viola
Vector2D a(1, 2);
Vector2D b(3, 4);
Vector2D c = a + b;
```

可以重载的运算符如下：

| 类别      | 运算符                                                      |
|:--------|:---------------------------------------------------------|
| 双目算术运算符 | `+`（加） `-`（减） `*`（乘） `/`（除） `%`（取模） `**`（乘方） `@`（矩阵乘）    |
| 关系运算符   | `<`（小于） `>`（大于） `<=`（小于等于） `>=`（大于等于） `==`（等于） `!=`（不等于） |
| 单目运算符   | `+`（正号） `-`（负号） `~`（按位取反）                                |
| 位运算符    | `&`（按位与） `\|`（按位或） `^`（按位异或） `~`（按位取反） `<<`（左移） `>>`（右移） |
| 其他运算符   | `[]`（索引） `()`（调用）                                        |

## 异常处理

异常处理主要涉及到这四个关键字：`throw`、`try`、`catch`和`finally`。具体而言：

- 当出现异常时，使用`throw`关键字抛出一个异常。
- 使用`catch`关键字开始一个异常处理块，`catch`块中的代码处理异常。
- 使用`try`关键字以指定需要捕获异常的代码。
- 使用`finally`关键字执行一段无论是否发生异常都会被执行的代码。

具体的格式是：

```viola
try {
    // 保护代码
} catch Exception1 e {
    // 处理Exception1类型的异常
} catch Exception2 e {
    // 处理Exception2类型的异常
}
// ...
finally { // 可选
    // 无论是否发生异常，都会执行的代码
}
```

**注意：抛出和捕获的异常必须为`viola.lang.exception`的子类。**

## 引入其他文件中的声明

我们可以使用`import`关键字来引入其他文件中的相关声明与实现。格式如下：

```viola
import 包名1;
import 包名1.包名2;
import 包名1.包名2.包名3;
import 包名 as 别名;
// ...
from 包名 import 全局标识符1, 全局标识符2;
from 包名 import 全局标识符1 as 别名1, 全局标识符2 as别名2;
from 包名 import *;
```

**注意：`import`关键字只能出现在源文件的最前面。并且如果出现了循环导入，会报错。**

## 类型别名（using）

可以使用`using`关键字为类型定义别名。格式如下：

```viola
using 别名 = 类型;
```

别名可以指向任何类型，包括基本数据类型、数组、类与泛型类型：

```viola
using MyInt = int32;
using MyIntArray = int32[];
using MyString = viola.lang.string;
import viola.util.array as array;
using IntArray = array.Array::<int32>;
```

别名可以定义在模块的最外层（模块级），也可以定义在函数、方法体或任意语句
块内。函数体内的别名从声明处起，在其所在的块及其内层块中可见，离开该块后
不再可见（其他函数中也不可见）：

```viola
sq main() -> () {
    using LocalInt = int32;
    LocalInt v = 1;

    if (v == 1) {
        using NestedInt = LocalInt; // 内层块可以使用外层块的别名
        NestedInt w = 2;
    }
    // 此处不能再使用NestedInt
}
```

别名与它指向的类型完全等价：声明变量、作为形参/返回值类型、参与类型检查与
重载解析时都按被别名的类型处理，生成的C代码也使用被别名的类型，别名本身不
产生任何运行时开销。

类型别名可以出现在被别名类型之前，也可以指向另一个别名：

```viola
using EarlyAlias = LaterClass; // LaterClass在下面才定义
using Doubled = MyInt;
```

指向未知类型的别名、以及形成循环的别名（如`using A = B; using B = A;`）会报错。

别名是模块级的符号，因此可以像类与函数一样导出到其他模块使用：

```viola
import mylib; // 使用mylib.MyInt
from mylib import MyInt; // 使用MyInt
```

别名也可以在符号表中查到其定义（被别名的类型），便于调试。

## C语言兼容

**TODO: 添加对C结构体的兼容。**

Viola编译器最终会生成C代码，并且允许向Viola源代码中添加C代码。要定义C函数，请使用如下格式：

```viola
cpart sq 函数名(参数列表) -> (T) {函数体}
// T可以为任何数据类型
```

此外，还可以向Viola源代码中直接导入C代码。格式如下：

```viola
import cpart "文件名"; // 相当于#include "文件名"
import cpart <文件名>; // 相当于#include <文件名>
import cpart 宏定义; // 相当于#include 宏定义
```

但是导入后需要添加__del__()方法。例如：

```viola
import cpart "very_complex_struct.h";

class VeryComplexStruct_ViolaAPI {
    cpart VeryComplexStruct _s;

    // 若干类成员
    cpart sq __del__() -> () {
        _s->clean();
    }
}
```