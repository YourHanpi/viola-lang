# Viola版本迭代计划

## Viola 0.1

### 关键字

- `export`：声明一个符号需要导出为库。例：

```viola
export class MyClass {...}
export fn myFunction(...) -> (...) {...}
export sq mySequence(...) -> (...) {...}
```

- `final`：声明一个类或方法为最终的，不能被继承或重写。例：

```viola
final class MyClass {...}

class MyClass2 {
    final fn myMethod(...) -> (...) {...}
}
```

- `impl`：实现一个接口。例：

```viola
class MyClass impl MyInterface {
    fn myMethod(...) -> (...) {...}
}
```

- `interface`：声明一个接口。接口不能被实例化，且只允许包含方法和静态属性，其中的方法都是抽象方法。接口允许多继承。例：

```viola
interface MyInterface extends OtherInterfaceA, OtherInterfaceB {
    static uint32 myStaticProperty = 0x114514;
    fn myMethod(...) -> (...);
}
```

- `public`、`protected`、`private`：如果试图访问不应被访问的成员，应报出编译时错误。

- `return`：强制返回。如果编译器发现此时有返回值没有被赋值，应当报出编译时错误。**请注意：`return`后应当直接跟随分号，因为返回变量在函数声明处就已确定。**

- `static`：声明类的静态方法或静态属性。静态属性是全局唯一的，且要求有初始值。例：

```viola
class MyClass {
    static uint32 myStaticProperty = 0x114514;
    static fn myStaticMethod(...) -> (...) {...}
}
```

- `unsafe`：

（1）成员声明的前缀，表示非安全成员。这种变量允许自身和属性被重新赋值，但是只允许作为`wrapper`类的成员，并且需要由用户手动管理内存。涉及到对`unsafe`变量进行写操作的语句，会被强制串行化，无论其中是否有`async`语句。`unsafe`变量允许存在于`wrapper`方法中，但不得被返回。例：

```viola
wrapper class MyClass {
    unsafe uint32 myProperty = 0x114514;
}
```

（2）类声明的前缀，表示这一类型的所有对象都是非安全的。

- `wrapper`：类声明的前缀，表示非安全类的包装类。需要用户自行实现`sq __del__() -> ();`方法来清理内部的`unsafe`对象（最后需要有`del(super);`语句来确保普通成员也被释放）（基本数据类型的`unsafe`变量不需要手动清理），编译器会保证此方法被正常调用。例：

```viola
wrapper class MyClass {...}
```

- `_`：接收被丢弃的值。此变量可以在同一作用域内被多次声明和赋值，但是不可被读取。例：

```viola
int32 x, string _ = *(0x114514, "1919810");
```

### 运行库

注：运行库（包括标准库、扩展标准库和第三方库）的根目录为`viola_libs`。所有C源文件的对外接口都需要加上前缀。C标识符的生成规则如下：

```python
import os
# 假设与根目录的相对路径为path，原标识符为identifier
# 例：与根目录的相对路径为`viola/lang/global_resource_manager.c`，原标识符为`addThread`，则生成的标识符为`viola$lang$global_resource_manager$addThread`。
def get_prefix(path: str, identifier: str) -> str:
    return os.path.splitext(path)[0].replace(os.sep, "$") + "$" + identifier
```

- 编译器内置
    - 添加指针（`unsafe Pointer::<T>`）。
    - 添加`void`类型（等效于`()`类型）。
    -  将“无访问修饰符”的默认情况从`protected`改为`public`。
    -  添加对模块的访问修饰符语义。其中：
        - `public`：公共访问修饰符，表示该成员可以被任何其他模块访问。
        - `protected`：受保护访问修饰符，表示该成员只能被同一模块中的其他成员访问。
        - `private`：私有访问修饰符，表示该成员只能被自身访问。
        - 默认情况为`public`。
    -  将所有函数（无论静态还是动态）封装为结构体（`viola.lang.function.Function`类，原`Closure`类，视为`object`的子类），但调用静态函数时仍然传递函数指针。其中，`Function`类应至少包含以下成员：
        - `viola$lang$function$A$ *asyncPtr`（C声明）或`Pointer::<viola.lang.function.AsyncPtr> asyncPtr`（Viola声明）：异步函数指针。
        - `viola$lang$function$S$ *syncPtr`（C声明）或`Pointer::<viola.lang.function.SyncPtr> syncPtr`（Viola声明）：同步函数指针。
        - `void *capture`（C声明）或`Pointer::<Tuple> capture`（Viola声明）：捕获的环境，为元组类型。
        - `string[] argNames`（Viola声明）：参数名称（不包括捕获的环境参数）。
    -  将所有元组封装为`object`类的子类。
    -  支持闭包按参数名进行传参的功能。如果依赖于哈希表的实现，请推迟至0.2版本。
- `viola.io.files`
    - 添加对外部文件的串行读写系统：由子线程发起请求，主线程执行请求并返回相关数据。
    - 添加标准输入输出功能
- `viola.lang`
    - 为`string`类追加方法：
        - `fn count(string sub) -> (uint32 result);`
        - `fn find(string sub) -> (uint32 result);`
        - `fn float() -> (float64 result);`
        - `static fn fromFloat(float64 value) -> (string result);`
        - `static fn fromInt(int64 value, uint8 base = 10) -> (string result);`（只需支持2~16进制）
        - `fn index(string sub) -> (uint32 result);`
        - `fn int(uint8 base = 10) -> (int64 result);`（只需支持2~16进制）
        - `fn isalnum() -> (bool result);`
        - `fn isalpha() -> (bool result);`
        - `fn isdecimal() -> (bool result);`
        - `fn isdigit() -> (bool result);`
        - `fn isidentifier() -> (bool result);`
        - `fn islower() -> (bool result);`
        - `fn isnumeric() -> (bool result);`
        - `fn isprintable() -> (bool result);`
        - `fn isspace() -> (bool result);`
        - `fn isupper() -> (bool result);`
        - `fn ljust(uint32 length, string fillChar) -> (string result);`
        - `fn lstrip(string toRemove = " \t\n\r") -> (string result);`
        - `fn replace(string oldSub, string newSub, uint32 count = 0) -> (string result);`
        - `fn rfind(string sub) -> (uint32 result);`
        - `fn rindex(string sub) -> (uint32 result);`
        - `fn rjust(uint32 length, string fillChar) -> (string result);`
        - `fn rstrip(string toRemove = " \t\n\r") -> (string result);`
        - `fn strip(string toRemove = " \t\n\r") -> (string result);`
        - `fn swapcase() -> (string result);`
        - `fn zfill(uint32 length) -> (string result);`
- `viola.lang.global_resource_manager`
    - 添加`_Request`类型的声明（在相应C头文件的`viola$lang$global_resource_manager$Request`中定义，需要添加引用计数）。
    - 添加请求向量表的注册函数`sq register_request_handler(uint32 request_id, (_Request) -> () handler) -> ();`。
- `viola/lang/global_resource_manager.c`
    - 添加基于请求的全局资源管理器（见`viola_lib_dev_plan_zh.md`）。
- `viola.lang.thread`
    - 添加线程调度系统（见`viola_lib_dev_plan_zh.md`）。
- `viola.math`
    - 直接包含`math.h`并生成相关绑定函数。
    - 新增如下内容：
        - 常量：`nan`, `inf`, `tau`；
        - 双曲函数及反双曲函数；
        - 弧度制与角度制的互相转换函数；
        - 欧几里得距离计算函数`fn dist(double[] a, double[] b) -> (double result);`，要求`a`和`b`的长度相同；
        - 误差函数、补误差函数、伽马函数、阶乘函数；
        - 浮点数的指数与尾数的分离与组合函数；
        - 最大公约数和最小公倍数函数；
        - 欧几里得范数计算函数`fn hypot(double[] a) -> (double result);`；
        - 各种对数（包括一个重载：`fn log(double x, double base) -> (double result);`）；
        - 排列数和组合数的计算函数；
        - 整数部分和小数部分的分离函数`fn modf(double x) -> (double fractional, double integer);`；
        - IEEE 754风格的小数余数函数`fn remainder(double x, double y) -> (double result);`；
        - 各类无效值（包括无穷）的判断函数。
- `viola.os`
    - 绑定Windows和POSIX的相关接口，使用条件编译分别处理。
    - 新增如下内容（其中涉及到文件操作的，应当由子线程发送请求、由主线程串行执行）：
        - `int32 STDERR_FILENO;`
        - `int32 STDIN_FILENO;`
        - `int32 STDOUT_FILENO;`
        - `class Stat;`
        - `fn access(string path, uint32 mode) -> (bool result);`
        - `sq chdir(string path) -> ();`
        - `sq chflags(string path, uint32 flags) -> ();`
        - `sq chmod(string path, uint32 mode) -> ();`
        - `sq chown(string path, uint32 uid, uint32 gid) -> ();`
        - `sq chroot(string path) -> ();`
        - `sq close(int32 fd) -> ();`
        - `sq closerange(int32 fd1, int32 fd2) -> ();`
        - `fn dup(int32 fd) -> (int32 result);`
        - `fn dup2(int32 fd1, int32 fd2) -> (int32 result);`
        - `sq fchdir(int32 fd) -> ();`
        - `sq fchmod(int32 fd, uint32 mode) -> ();`
        - `sq fchown(int32 fd, uint32 uid, uint32 gid) -> ();`
        - `sq fdatasync(int32 fd) -> ();`
        - `sq fdopen(int32 fd) -> (FILE result);`
        - `fn fpathconf(int32 fd, int32 name) -> (int32 result);`
        - `fn fstat(int32 fd) -> (Stat result);`
        - `sq ftruncate(int32 fd, uint32 size) -> ();`
        - `fn getcwd() -> (string result);`
        - `fn getcwdb() -> (string result);`
        - `fn getgid() -> (uint32 result);`
        - `fn getuid() -> (uint32 result);`
        - `fn isatty(int32 fd) -> (bool result);`
        - `sq lchflags(string path, uint32 flags) -> ();`
        - `sq lchmod(string path, uint32 mode) -> ();`
        - `sq lchown(string path, uint32 uid, uint32 gid) -> ();`
        - `sq link(string path, string newPath) -> ();`
        - `fn listdir(string path) -> (string[] result);`
        - `sq lseek(int32 fd, int32 offset, int32 whence) -> (int32 result);`
        - `fn lstat(string path) -> (Stat result);`
        - `fn major(uint32 dev) -> (uint32 result);`
        - `fn makedev(uint32 major, uint32 minor) -> (uint32 result);`
        - `sq makedirs(string path, uint32 mode = 0o777) -> ();`
        - `fn minor(uint32 dev) -> (uint32 result);`
        - `sq mkdir(string path, uint32 mode = 0o777) -> ();`
        - `sq mkfifo(string path, uint32 mode = 0o666) -> ();`
        - `sq mknod(string path, uint32 mode = 0o666, uint32 dev = 0) -> ();`
        - `sq open(string path, uint32 flags, uint32 mode = 0o666) -> (int32 fd);`
        - `sq openpty() -> (int32 result);`
        - `fn pathconf(string path, int32 name) -> (int32 result);`
        - `sq pipe() -> (int32 result);`
        - `sq popen(string command, string mode) -> (FILE result);`
        - `sq read(int32 fd, uint32 nbyte) -> (string result);`
        - `sq readlink(string path) -> (string result);`
        - `sq remove(string path) -> ();`
        - `sq removedirs(string path) -> ();`
        - `sq rename(string oldPath, string newPath) -> ();`
        - `sq renames(string oldPath, string newPath) -> ();`
        - `sq rmdir(string path) -> ();`
        - `fn stat(string path) -> (Stat result);`
        - `sq stat_float_times(bool useFloat) -> ();`
        - `fn statvfs(string path) -> (StatVFS result);`
        - `fn tcgetpgrp(int32 fd) -> (int32 result);`
        - `sq tcsetpgrp(int32 fd, int32 pgid) -> ();`
        - `fn ttyname(int32 fd) -> (string result);`
        - `sq unlink(string path) -> ();`
        - `sq utime(string path, uint32 atime, uint32 mtime) -> ();`
        - `sq write(int32 fd, string data) -> (uint32 result);`
- `viola.os.path`
    - 添加路径处理功能，例如：
        - `string pathsep;`
        - `fn abspath(string path) -> (string result);`
        - `fn basename(string path) -> (string result);`
        - `fn commonpath(string[] paths) -> (string result);`
        - `fn commonprefix(string[] paths) -> (string result);`
        - `fn dirname(string path) -> (string result);`
        - `fn exists(string path) -> (bool result);`
        - `fn getatime(string path) -> (uint64 result);`
        - `fn getctime(string path) -> (uint64 result);`
        - `fn getmtime(string path) -> (uint64 result);`
        - `fn getsize(string path) -> (uint64 result);`
        - `fn isabs(string path) -> (bool result);`
        - `fn isdir(string path) -> (bool result);`
        - `fn isfile(string path) -> (bool result);`
        - `fn islink(string path) -> (bool result);`
        - `fn ismount(string path) -> (bool result);`
        - `fn join(string[] paths) -> (string result);`
        - `fn normpath(string path) -> (string result);`
        - `fn realpath(string path) -> (string result);`
        - `fn samefile(string path1, string path2) -> (bool result);`
        - `fn sameopenfile(int32 fd1, int32 fd2) -> (bool result);`
        - `fn split(string path) -> (string[] result);`
        - `fn splitext(string path) -> (string[] result);`
- `viola.stat`
    - 添加文件状态功能，例如：
        - `uint32 S_IFDIR;`
        - `uint32 S_IFREG;`
        - `uint32 S_IRGRP;`
        - `uint32 S_IROTH;`
        - `uint32 S_IRUSR;`
        - `uint32 S_IWGRP;`
        - `uint32 S_IWOTH;`
        - `uint32 S_IWUSR;`
        - `uint32 S_IXGRP;`
        - `uint32 S_IXOTH;`
        - `uint32 S_IXUSR;`
        - `fn S_ISBLK(uint32 mode) -> (bool result);`
        - `fn S_ISCHR(uint32 mode) -> (bool result);`
        - `fn S_ISDIR(uint32 mode) -> (bool result);`
        - `fn S_ISFIFO(uint32 mode) -> (bool result);`
        - `fn S_ISLNK(uint32 mode) -> (bool result);`
        - `fn S_ISREG(uint32 mode) -> (bool result);`
        - `fn S_ISSOCK(uint32 mode) -> (bool result);`
        - `fn filemode(uint32 mode) -> (string result);`
- `viola.util.control_flow`（即`viola/util/control_flow.vla`，其余类似）
    - 添加用于循环的函数：
        - `sq forEach::<T, U>(T[] iterable, (T) -> (U) mapper) -> (U[] result);`（和`map`函数的区别是，`forEach`保证顺序，而`map`不保证。）
        - `sq forEach::<T>(T[] iterable, (T) -> () mapper) -> ();`
        - `sq while::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);`
        - `sq doWhile::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);`
- `viola.util.functools`
    - 添加函数式编程原语：
        - `fn map::<T, U>(T[] iterable, (T) -> (U) mapper, bool useAsync) -> (U[] result);`
        - `fn filter::<T>(T[] iterable, (T) -> (bool) predicate, bool useAsync) -> (T[] result);`
        - `fn reduce::<T>(T[] iterable, (T[]) -> (T) reducer, uint32 reduceSize, bool useAsync) -> (T result);`
        - `fn expand::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);`（先将`inputs`拷贝一份到`results`，然后反复将最后`inputs.length`个元素送入`expander`，产生的新元素追加到`result`末尾，直至`result`的长度不小于`targetSize`。）
        - `fn expandWithCut::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);`（和`expand`类似，但是`result`中数目超过`targetSize`的多余元素会被丢弃。）

### 漏洞修复

- 修复函数类型在C语言层上的表示，使之符合语法。
- 修复元组类型在C语言层上的表示，使之成为包含`c_calling_type`所示类型成员的结构体。
- 修复尾递归优化。当前尾递归优化算法为：

```c
int recursive(T1 x, T2 y) {
// mark:
    return recursive(f(y), g(x));   // x = f(y); y = g(x); goto mark;
                                    // 这相当于x = f(y); y = g(f(y));，与语义不符
    // 应当为（或者类似于）：
    // T1 $new$x = f(y); T2 $new$y = g(x); x = $new$x; y = $new$y; goto mark;
    // 注意确保f(y)和g(x)的执行顺序，以免潜在的副作用导致混乱
}
```

- **（新增）** 修复原子引用计数的安全性：改用系统提供的原子变量进行计数。
- **（新增）** 移除Python的`re`模块相关调用和第三方库调用（如有），改用等效的手动实现，以便未来实现自举。

## Viola 0.2

### 语法

- 实现字典和集合的语法。例：

```viola
dict::<string, int32> myDict = {
    "key1": 1,
    "key2": 2,
    "key3": 3
};

set::<string> mySet = {
    "key1",
    "key2",
    "key3"
};
```

- 实现短lambda表达式，语法为`(T1 arg1, T2 arg2, ...) -> (retExpr1, retExpr2, ...)`。

- 实现装饰器。例：

```viola
fn decorator((int32, int32) -> (int32, int32) target) -> ((int32, int32) -> (int32, int32) result) {
    result = sq(int32 arg1, int32 arg2) -> (int32 ret1, int32 ret2) {
        println("Calling decorator...");
        ret1, ret2 = target(arg1, arg2);
        println("Decorator called.");
    };
}

@decorator
fn divmod(int32 a, int32 b) -> (int32 divResult, int32 modResult) {
    divResult = a / b;
    modResult = a % b;
}
```

- 实现联合类型及其静态和动态转换。其中，联合类型的语法是`T | U | V | ...`，表示`T`、`U`或`V`等等中的任意一种。
    - 符号`|`的优先级：`(T1, T2 | T3[], T4)`表示`T1`、`T2 | T3[]`、`T4`三个类型组成的元组。其中`T2 | T3[]`等效于`T2`和`T3[]`组成的联合类型。
    - 如有需要，可提前加入`typevar`关键字，以声明一个类型表达式。

### 运行库

- `viola.io.files`
    - 实现并发的按块读文件。
- `viola.lang.thread`
    - 实现启动临时线程，并提供相关的管理。
    - 定义类型`ThreadMarker`，用于将函数绑定到线程标记上，所有标记相同的函数都由同一线程执行。例：

```viola
ThreadMarker marker();

@marker
sq myFunction() -> () {
    println("Hello, world!");
}
```

- `viola.util.hashmap`
    - 定义接口`interface Hashable`，这一接口要求实现`fn hash() -> (uint32);`方法。
    - 用哈希表实现字典类`class dict::<K, V>`和集合类`class set::<T>`。哈希算法默认使用SipHash-2-4，但是允许用户自定义哈希算法，并作为参数传入。

