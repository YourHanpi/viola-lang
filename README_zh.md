# Viola语言

Viola是一个以内存安全、高并发简化和高性能为设计目标的编译型语言。

- 语法与Java类似，但更简单。
- 兼容C语言生态。
- 设计时考虑了自动内存管理，目前使用ARC+数据不可变。
- 所有基本数据类型都是值类型，所有对象都是指针类型。
- 除非类中包含C结构体，否则不需要手动定义析构函数。
- 运行时使用C99标准，也支持C++。
- **所有数据一经初始化则不可变**。
- 支持闭包、运算符重载和编译期泛型。
- 有两种函数关键字：`sq`（顺序式）和`fn`（声明式）。

详细语法设计请参阅[参考手册](manual_zh.md)。

# 开发进度

目前，第一个版本尚未成型。
本项目欢迎任何人提出善意的建议和意见，并允许贡献代码。

**请注意：为了未来能够自举，请不要使用第三方库和C语言没有原生实现的标准库功能（包括但不限于正则表达式等）实现以下部分：**

- **词法分析、语法分析；**
- **语义分析、目标代码生成；**
- **viola.lang命名空间的标准库。**

## 语法解析


## 语义分析和目标代码生成

这一部分（编译器后端）负责生成C代码，初稿已经基本完成，但未进行测试。源代码见[链接](violac/src/backend)。

语义分析部分预计包含以下功能：

1. 符号检查：检查类型和函数是否定义、变量是否声明且未多次赋值。
2. 常量折叠：尽可能在编译期尝试对表达式求值。
3. 类型检查：尝试对类型进行静态检查，以及生成dynamic cast代码。
4. 类继承和接口实现检查。
5. 变量生命周期检查，并在生命周期结束时自动插入释放代码。
6. 导入符号检查 **（未完成）**。

目标代码生成部分预计包含以下功能：

1. 函数定义和调用的代码生成，包括同步调用和异步调用。
2. 表达式生成。
3. 语句生成。
4. 类定义生成、类的多态调用。
5. 变量、类型和字面量生成。
6. 每个模块生成一个.c文件和.h文件。

# 标准库

这一部分尚未开始编写，预计将会使用C语言和Viola语言混合编写。目前考虑至少加入以下内容：

## viola.lang

- `array<T>`类。
- `expand`函数，声明为`sq expand<T>(T[] inputs, (T[]) -> (T) predicate, size_t size) -> (T[] results);`，运行时将调用predicate函数对最后input.length个元素进行迭代，并返回迭代至长度为size的数组。
- `filter`函数，声明为`fn filter<T>(T[] inputs, (T) -> (bool) predicate, bool useAsync) -> (T[] results);`。
- `map`函数，声明为`fn map<T, U>(T[] inputs, (T) -> (U) mapper, bool useAsync) -> (U[] results);`。
- `reduce`函数，声明为`fn reduce<T>(T[] inputs, (T, T) -> (T) reducer, T initialValue, bool useAsync) -> (T result);`。
- `string`类。

### viola.lang.thread

- `enqueue`C函数，声明为`void viola$lang$thread$enqueue(FuncCall *call);`。
- `FuncCall`C结构体。
- `initListener`C函数，声明为`void viola$lang$thread$initListener(Listener *listener, uint32_t executerThreadId);`。
- `Listener`C结构体。
- `popStackA`和`popStackB`C函数，声明为`void viola$lang$thread$popStackA(uint32_t threadId);`和`void viola$lang$thread$popStackB(uint32_t threadId);`。
- `pushStackA`和`pushStackB`C函数，声明为`void viola$lang$thread$pushStackA(uint32_t threadId, viola$lang$string *string);`和`void viola$lang$thread$pushStackB(uint32_t threadId, viola$lang$thread$ThreadInfo threadInfo);`。
- `StackA`和`StackB`C结构体。关于这两个结构体的解释见traceback的实现。
- `waitListener`C函数，声明为`void viola$lang$thread$waitListener(Listener *listener);`。此函数会销毁传入的Listener。

### traceback的实现

- 每个线程设置两个栈A和B，其中A栈存放`traceback`标记，B栈存放结构体`viola$lang$thread$ThreadInfo`。
- `viola$lang$thread$ThreadInfo`结构体定义如下： 

```c
typedef struct {
    uint32_t targetStackASize; // 切换线程时，目标线程栈A的大小
    uint32_t targetThreadId; // 目标线程ID
    uint64_t stackASize; // 当前线程栈A的大小
} viola$lang$thread$ThreadInfo;
```

- A栈每当调用函数时就压栈，函数返回时退栈；B栈调用异步函数时压栈，异步函数返回时退栈。
- B栈的压栈操作在从任务队列获取任务时完成，退栈操作在异步包装函数中完成。stackASize从委托方线程传入的listener中获取。
- traceback打印代码：

```c
viola$lang$string *viola_getTraceback(uint32_t threadId) {
    viola$lang$string *traceback = viola$lang$string$fromCharString("");
    viola$thread$Thread *thread;
    uint64_t to;
    uint32_t targetThreadId;
    uint32_t targetStackASize;
    uint32_t stackBIndex = thread->stackB->size;
    viola$thread$StackB *stackB;
    viola$lang$string *stackAStrings;
    viola$lang$thread$ThreadInfo threadData;
    viola$lang$string *newTraceback;
    uint64_t from;
    while (to > 0) {
        thread = viola$thread$threads[threadId];
        from = thread->stackA->size;
        stackB = thread->stackB;
        do {
            threadData = stackB->stack[stackBIndex];
            to = threadData.stackASize;
        } while(to >= from);
        targetThreadId = threadData.targetThreadId;
        targetStackASize = threadData.targetThreadASize;
        stackAStrings = thread->stackA->stack;
        for (uint32_t i = from; i >= to; i--) {
            viola$lang$string$concat(traceback, stackAStrings[i], &newTraceback);
            free(traceback);
            traceback = newTraceback;
        }
        threadId = targetThreadId;
    }
    return traceback;
}
```