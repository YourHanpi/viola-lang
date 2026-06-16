# Viola编译器

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
- `int` - 整型（相当于C `int`）
    - `int8` - 8位整型（相当于C `int8_t`）
    - `int16` - 16位整型（相当于C `int16_t`）
    - `int32` - 32位整型（相当于C `int32_t`）
    - `int64` - 64位整型（相当于C `int64_t`）
    - `uint` - 无符号整型（相当于C `unsigned int`）
    - `uint8` - 8位无符号整型（相当于C `uint8_t`）
    - `uint16` - 16位无符号整型（相当于C `uint16_t`）
    - `uint32` - 32位无符号整型（相当于C `uint32_t`）
    - `uint64` - 64位无符号整型（相当于C `uint64_t`）
    - `size_t` - 数据长度类型（相当于C `size_t`）
- `float` - 浮点型（相当于C `float`)
    - `float32` - 32位浮点型（相当于C `float32_t`）
    - `float64` - 64位浮点型（相当于C `float64_t`）
    - `double` - 双精度浮点型（相当于C `double`）
    - `long double` - 四精度浮点型（相当于C `long double`）

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

| 运算符  | 描述                   | 调用方式         | 调用的魔术方法                                                                                                         |
|:-----|:---------------------|:-------------|:----------------------------------------------------------------------------------------------------------------|
| `+`  | 把两个操作数相加             | `x = a + b`  | `fn __add__(T1 other) -> T2`<br>`fn __radd__(T1 other) -> T2`\*<br>\*当`a`所在类的`__add__`方法未定义时，调用`b`的此方法          |
| `-`  | 将前一操作数减去后一操作数        | `x = a - b`  | `fn __sub__(T1 other) -> T2`<br>`fn __rsub__(T1 other) -> T2`\*<br>\*当`a`所在类的`__sub__`方法未定义时，调用`b`的此方法          |
| `*`  | 把两个操作数相乘             | `x = a * b`  | `fn __mul__(T1 other) -> T2`<br>`fn __rmul__(T1 other) -> T2`\*<br>\*当`a`所在类的`__mul__`方法未定义时，调用`b`的此方法          |
| `/`  | 将前一操作数除以后一操作数        | `x = a / b`  | `fn __div__(T1 other) -> T2`<br>`fn __rdiv__(T1 other) -> T2`\*<br>\*当`a`所在类的`__div__`方法未定义时，调用`b`的此方法          |
| `%`  | 取前一操作数除以后一操作数的余数     | `x = a % b`  | `fn __mod__(T1 other) -> T2`<br>`fn __rmod__(T1 other) -> T2`\*<br>\*当`a`所在类的`__mod__`方法未定义时，调用`b`的此方法          |
| `**` | 取前一操作数的幂，指数为后一操作数    | `x = a ** b` | `fn __pow__(T1 other) -> T2`<br>`fn __rpow__(T1 other) -> T2`\*<br>\*当`a`所在类的`__pow__`方法未定义时，调用`b`的此方法          |
| `@`  | 进行矩阵乘法，将前一操作数右乘后一操作数 | `x = a @ b`  | `fn __matmul__(T1 other) -> T2`<br>`fn __rmatmul__(T1 other) -> T2`\*<br>\*当`a`所在类的`__matmul__`方法未定义时，调用`b`的此方法 |

一元算术运算符：

| 运算符 | 描述   | 调用方式     | 调用的魔术方法                |
|:----|:-----|:---------|:-----------------------|
| `+` | 取正数  | `x = +a` | `fn __pos__() -> T`    |
| `-` | 取负数  | `x = -a` | `fn __neg__() -> T`    |
| `~` | 按位取反 | `x = ~a` | `fn __invert__() -> T` |

关系运算符：

| 运算符  | 描述                 | 调用方式         | 调用的魔术方法                     |
|:-----|:-------------------|:-------------|:----------------------------|
| `==` | 判断两个操作数是否相等        | `x = a == b` | `fn __eq__(T1 other) -> T2` |
| `!=` | 判断两个操作数是否不相等       | `x = a != b` | `fn __ne__(T1 other) -> T2` |
| `>`  | 判断前一操作数是否大于后一操作数   | `x = a > b`  | `fn __gt__(T1 other) -> T2` |
| `<`  | 判断前一操作数是否小于后一操作数   | `x = a < b`  | `fn __lt__(T1 other) -> T2` |
| `>=` | 判断前一操作数是否大于等于后一操作数 | `x = a >= b` | `fn __ge__(T1 other) -> T2` |
| `<=` | 判断前一操作数是否小于等于后一操作数 | `x = a <= b` | `fn __le__(T1 other) -> T2` |

逻辑运算符：

| 运算符    | 描述  | 调用方式           | 调用的魔术方法 |
|:-------|:----|:---------------|:--------|
| `&&`   | 逻辑与 | `x = a && b`   | 无       |
| `\|\|` | 逻辑或 | `x = a \|\| b` | 无       |
| `!`    | 逻辑非 | `x = !a`       | 无       |

位运算符：

| 运算符  | 描述   | 调用方式         | 调用的魔术方法                                                                                                                      |
|:-----|:-----|:-------------|:-----------------------------------------------------------------------------------------------------------------------------|
| `&`  | 按位与  | `x = a & b`  | `fn __and__(T1 other) -> T2`<br>`fn __rand__(T1 other) -> T2 `\*<br>\*当`a`所在类的`__and__`方法未定义时，调用`b`的`__rand__`方法             |
| `\|` | 按位或  | `x = a \| b` | `fn __or__(T1 other) -> T2`<br>`fn __ror__(T1 other) -> T2 `\*<br>\*当`a`所在类的`__or__`方法未定义时，调用`b`的`__ror__`方法                 |
| `^`  | 按位异或 | `x = a ^ b`  | `fn __xor__(T1 other) -> T2`<br>`fn __rxor__(T1 other) -> T2 `\*<br>\*当`a`所在类的`__xor__`方法未定义时，调用`b`的`__rxor__`方法             |
| `~`  | 按位取反 | `x = ~a`     | `fn __not__() -> T2`                                                                                                         |
| `<<` | 左移   | `x = a << b` | `fn __lshift__(T1 other) -> T2`<br>`fn __rlshift__(T1 other) -> T2 `\*<br>\*当`a`所在类的`__lshift__`方法未定义时，调用`b`的`__rlshift__`方法 |
| `>>` | 右移   | `x = a >> b` | `fn __rshift__(T1 other) -> T2`<br>`fn __rrshift__(T1 other) -> T2 `\*<br>\*当`a`所在类的`__rshift__`方法未定义时，调用`b`的`__rrshift__`方法 |

其他运算符：

| 运算符       | 描述   | 调用方式              | 调用的魔术方法                          |
|:----------|:-----|:------------------|:---------------------------------|
| `.`       | 属性访问 | `x = obj.prop`    | 无                                |
| `(as T)`  | 类型转换 | `x = (as T)value` | 无                                |
| `[index]` | 索引访问 | `x = obj[index]`  | `fn __getitem__(T1 index) -> T2` |

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

**注意：由于数据不可变性，Viola不提供循环。如有需要，请使用递归。**

**TODO: 提供用于循环的库函数（声明见下）。**

```viola
sq forEach::<T, U>(T[] iterable, (T) -> (U) mapper) -> (U[] result);
sq forEach::<T>(T[] iterable, (T) -> () mapper) -> ();
sq while::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);
sq doWhile::<T>(T inputs, (T) -> (T) updater) -> (T result);
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
    // Viola没有return关键字和语句，以及类似功能的关键字和语句
}
```

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

## 输入与输出

Viola提供了一些用于输入与输出的函数。

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

**注意：尚不确定是否会采用文件句柄这一形式，因为目前已知的方法都可能导致死锁。**

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
    uint channels; // 属性，默认为protected，但也支持public和private，也可以显式写出protected
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
        pixels = zeros<uint8>(height * width * channels);
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
Image img3(3, 100, 100, zeros<uint8>(30000)); // 相当于Image img3 = Image(3, 100, 100, zeros<uint8>(30000));
```

类似基本数据类型，我们也可以直接将类类型的数据传入函数。例如：

```viola
sq toBytes(Image img) -> (uint8[] result) {...}
```

### 访问修饰符

**TODO: 实现访问修饰符，而不是忽略它们。**

对于前述的访问修饰符public、protected和private，和其他大多数语言一样，有这样的访问类型（其中“+”表示可以访问，“-”表示不可以访问）：

| 访问者 | public | protected | private |
|-----|--------|-----------|---------|
| 自身  | +      | +         | +       |
| 子类  | +      | +         | -       |
| 其他类 | +      | -         | -       |

这种修饰符不是强制性的。如确有必要，仍然可以访问，但是通常不推荐。

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
        this.super = __new__(a, b, sqrt(a * a + b * b));
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

## 重载

在同一作用域内，可以声明多个同名函数（功能通常类似），但参数列表中的类型必须不同。这种做法称为**重载**。例如：

```viola
sq printNumber(int value) -> () {
    print("整数值为：");
    println(toString(value));
}

sq printNumber(double value) -> () {
    print("浮点值为：");
    println(toString(value));
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