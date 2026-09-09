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
- 有两种函数关键字：`sq`（顺序执行）和`fn`（按需执行）。

详细语法设计请参阅[参考手册](manual_zh.md)。

# 开发进度

目前，0.1版本已经完成开发与测试。0.1版本的开发计划见
[versions_dev_plan_zh.md](versions_dev_plan_zh.md)，包含：
`export`、`final`、`impl`/`interface`、`public`/`protected`/`private`、
`return`、`static`、`unsafe`、`wrapper`、丢弃变量`_`等关键字，
以及`viola.io`、`viola.lang`、`viola.math`、`viola.os`、
`viola.os.path`、`viola.stat`、`viola.threads`、
`viola.util.control_flow`、`viola.util.functools`、
`viola.util.array`等运行库模块（详见[参考手册](manual_zh.md)）。
测试方式见`violac/whole_test/run_full_test.py`
（编译全部模板工程、用gcc链接运行库并运行，检查退出码）
与`violac/unit_test`（编译器单元测试）。

本项目欢迎任何人提出善意的建议和意见，并允许贡献代码。

**请注意：为了未来能够自举，请不要使用第三方库，以及C语言没有原生实现的标准库功能（包括但不限于正则表达式等）。**

## 语法解析

这一部分（编译器前端）使用递归下降法编写，目前已经基本完成，正在进行测试。源代码见[链接](violac/src/frontend)。

## 语义分析和目标代码生成

这一部分（编译器后端）负责生成C代码，目前已经基本完成，正在进行测试。源代码见[链接](violac/src/backend)。

语义分析部分预计包含以下功能：

1. 符号检查：检查类型和函数是否定义、变量是否声明且未多次赋值。
2. 常量折叠：尽可能在编译期尝试对表达式求值。
3. 类型检查：尝试对类型进行静态检查，以及生成dynamic cast代码。
4. 类继承和接口实现检查。
5. 变量生命周期检查，并在生命周期结束时自动插入释放代码。
6. 导入符号检查。

目标代码生成部分预计包含以下功能：

1. 函数定义和调用的代码生成，包括同步调用和异步调用。
2. 表达式生成。
3. 语句生成。
4. 类定义生成、类的多态调用。
5. 变量、类型和字面量生成。
6. 每个模块生成一个.c文件和.h文件。

# 标准库

标准库位于`viola_libs`目录下，使用C语言和Viola语言混合编写。
0.1版本已完成以下模块（详细接口见[参考手册](manual_zh.md)与各模块的
Viola声明文件`viola_libs/viola/*.vla`）：

- `viola.io`：标准输入输出（print/perror/input）与文件读写
  （open/read/readBytes/write/writeBytes，经全局资源管理器串行执行）。
- `viola.lang`：`string`类（连接、比较、切片、分割、大小写转换、
  数字互转、空白与字符类别判断等）、`exception`（Exception类）、
  `function`（函数值Function结构体）、`slice`、`object`。
- `viola.lang.global_resource_manager`：基于请求的全局资源管理器
  （子线程发起请求、主线程串行执行），支持以Viola函数注册请求处理器。
- `viola.threads`：线程调度系统（addThread/delThread/getThreadsNum/
  setThreadsNum，以及任务队列、监听器、traceback双栈等内部实现）。
- `viola.math`：数学常量（pi/e/tau/inf/nan）与math.h绑定函数，
  以及双曲/反双曲函数、弧度角度互转、距离与范数、误差/伽马/阶乘、
  指数尾数分离、gcd/lcm、排列组合、modf/remainder、无效值判断等。
- `viola.os`：Windows/POSIX系统接口（条件编译），包括标准文件
  描述符、O_*常量、文件与目录操作、Stat/StatVFS文件状态等。
- `viola.os.path`：路径处理（basename/dirname/join/normpath/
  abspath/realpath/exists/isdir/isfile/split/splitext等）。
- `viola.stat`：文件类型与权限位常量（S_IF*/S_IRWX*）、
  文件类型判断（S_IS*）与filemode。
- `viola.util.control_flow`：循环函数（forEach/while/doWhile）。
- `viola.util.functools`：函数式编程原语（map/filter/reduce/
  expand/expandWithCut）。
- `viola.util.array`：泛型数组类Array::&lt;T&gt;。

运行库与编译器生成的C代码一起由gcc编译链接（构建脚本
`viola_libs/build.py`，测试入口`violac/whole_test/run_full_test.py`）。

## 线程调度的内部实现（viola.threads）

- 接口：`addThread`（`sq addThread(uint32 number) -> ();`）、
  `delThread`（`sq delThread(uint32 number) -> ();`，有空闲线程则直接
  移除；空闲线程不足则等待直到一个线程完成当前任务，然后移除该线程，
  并将其所有未执行任务移入任务队列）、`getThreadsNum`
  （`fn getThreadsNum() -> (uint32 number);`）、`setThreadsNum`
  （`sq setThreadsNum(uint32 number) -> ();`）。
- 内部C接口（前缀`viola$threads$`）：`enqueue(FuncCall *call)`、
  `initListener(Listener *listener, uint32_t executerThreadId)`、
  `pushStackA/popStackA`、`pushStackB/popStackB`、`waitListener`
  （结束前销毁监听器）；结构体`FuncCall`、`Listener`、
  `ThreadInfo`、`StackA`（traceback标记栈）、`StackB`（线程信息栈）、
  `TaskQueue`。
- traceback实现：每个线程设置两个栈A和B，A栈存放traceback标记，
  B栈存放`ThreadInfo`（切换线程时的目标栈大小与目标线程ID）。
  调用函数时A栈压栈、返回时退栈；异步函数在任务队列中取出任务时
  B栈压栈、异步包装函数返回时退栈。