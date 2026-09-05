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
- `viola.io.files`
    - 添加对外部文件的串行读写系统：由子线程发起请求，主线程执行请求并返回相关数据。
    - 添加标准输入输出功能
- `viola/lang/global_resource_manager.c`
    - 添加基于请求的全局资源管理器（见`viola_lib_dev_plan_zh.md`）。
- `viola.lang.thread`
    - 添加线程调度系统（见`viola_lib_dev_plan_zh.md`）。
- `viola.math`
    - 直接包含`math.h`并生成相关绑定函数。
- `viola.os`
    - 绑定Windows和POSIX的相关接口，使用条件编译分别处理。
- `viola.util.control_flow`（即`viola/util/control_flow.vla`，其余类似）
    - 添加用于循环的函数：
        - `sq forEach::<T, U>(T[] iterable, (T) -> (U) mapper) -> (U[] result);`（和`map`函数的区别是，`forEach`保证顺序，而`map`不保证。）
        - `sq forEach::<T>(T[] iterable, (T) -> () mapper) -> ();`
        - `sq while::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);`
        - `sq doWhile::<T>(T inputs, (T) -> (T) updater, (T) -> (bool) predicate) -> (T result);`
- `viola.util.functools`
    - 添加函数式编程原语：
        - `fn map::<T, U>(T[] iterable, (T) -> (U) mapper, booluseAsync) -> (U[] result);`
        - `fn filter::<T>(T[] iterable, (T) -> (bool) predicate, bool useAsync) -> (T[] result);`
        - `fn reduce::<T>(T[] iterable, (T[]) -> (T) reducer, uint32 reduceSize, bool useAsync) -> (T result);`
        - `fn expand::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);`（先将`inputs`拷贝一份到`results`，然后反复将最后`inputs.length`个元素送入`expander`，产生的新元素追加到`result`末尾，直至`result`的长度不小于`targetSize`。）
        - `fn expandWithCut::<T>(T[] inputs, (T[]) -> (T[]) expander, uint32 targetSize) -> (T[] result);`（和`expand`类似，但是`result`中数目超过`targetSize`的多余元素会被丢弃。）

### 漏洞修复

- 修复函数类型在C语言层上的表示，使之符合语法。
- 修复元组类型在C语言层上的表示，使之成为包含`c_calling_type`类型成员的结构体。

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
    - 定义接口`interface Hashable`，要求实现`fn hash() -> (uint32);`方法。
    - 用哈希表实现字典类`class dict::<K, V>`和集合类`class set::<T>`。

