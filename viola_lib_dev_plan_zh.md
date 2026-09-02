# Viola标准库开发计划

## 基本定义

所有标准库源码都位于`viola_libs`目录下。需要提供Windows和Unix平台的实现。

## 第1批：并发调度、字符串和文件读写

### 并发调度

基本信息：

- 引用方式：`viola.lang.thread`
- 源码路径：`viola/lang/thread.c`

接口声明（除非特别注明，否则不提供Viola接口）（所有接口名称都需要加上`viola$lang$threads$`前缀，并且在头文件中声明，无论是否提供Viola接口）（结构体声明时应使用`typedef`去掉`struct`前缀）：

```c
extern ThreadPool *pool;                                            // 线程池实例。
extern TaskQueue *queue;                                            // 任务队列实例。

struct FuncCall {...};                                              // 函数调用。
struct Listener {...};                                              // 任务监听器。
struct StackA {...};                                                // 线程A栈。存放traceback字符串指针。调用函数时压栈，函数返回时退栈。
struct StackB {...};                                                // 线程B栈。存放ThreadInfo结构体指针。调用异步函数时压栈，异步函数返回时退栈。
struct ThreadInfo {                                                 // 线程信息。
    uint32_t targetStackASize;                                      // 切换线程时，目标线程栈A的大小。
    uint32_t targetThreadId;                                        // 目标线程ID。
    uint64_t stackASize;                                            // 当前线程栈A的大小。
};

void addThread(uint32_t num);                                       // 添加线程。此函数提供Viola接口。
void delThread(uint32_t num);                                       // 删除线程。此函数提供Viola接口。
void enqueue(FuncCall *call);                                       // 将函数调用加入任务队列。
uint32_t getThreadsNum();                                           // 获取线程数量。此函数提供Viola接口。
void initListener(Listener *listener, uint32_t senderThreadId);     // 初始化任务监听器。请注意：senderThreadId指的是发出任务的线程ID。
void popStackA(uint32_t threadId);                                  // 对相应线程的A栈进行退栈。
void popStackB(uint32_t threadId);                                  // 对相应线程的B栈进行退栈。
void setThreadsNum(uint32_t num);                                   // 设置线程数量。此函数提供Viola接口。
void waitListener(Listener *listener);                              // 等待监听器。此操作应当在结束前销毁监听器。
```

### 字符串

基本信息：

- 引用方式：`viola.lang.string`
- 源码路径：`viola/lang/string.vla`

接口声明（含有`dict`类型和`set`类型的接口可以推迟实现）：

```viola
wrapper class string {
    unsafe protected Pointer::<uint16> data;                                            // 字符串数据指针
    public uint64 size;                                                                 // 字符串长度
    public fn __add__(string s) -> (string result);                                     // 字符串连接，等效于concat方法
    public sq __del__() -> ();                                                          // 析构函数，需要释放字符串数据指针
    public fn __eq__(string s) -> (bool result);                                        // 判断字符串是否相等
    public fn __getitem__(slice s) -> (string result);                                  // 返回字符串切片
    public fn __getitem__(int64 index) -> (string ch);                                  // 返回字符串中第index个字符
    public fn __mul__(uint64 times) -> (string result);                                 // 字符串重复，等效于repeat方法
    public fn __ne__(string s) -> (bool result);                                        // 判断字符串是否不相等
    public fn __rmul__(uint64 times) -> (string result);                                // 字符串重复，等效于repeat方法
    public fn concat(string s) -> (string result);                                      // 字符串连接
    public fn format(string[] args, dict::<string, string> kwargs) -> (string result);  // 格式化字符串
    public fn endswith(string s) -> (bool result);                                      // 判断字符串是否以参数s结尾
    public fn isascii() -> (bool result);                                               // 判断字符串是否为ASCII字符串
    public fn join(string[] s) -> (string result);                                      // 使用分隔符连接字符串
    public fn lower() -> (string result);                                               // 返回字符串小写
    public fn repeat(uint64 times) -> (string result);                                  // 字符串重复
    public fn rsplit(string s, uint64 maxsplit = -1) -> (string[] results);             // 从右按分隔符分割字符串
    public fn split(string s, uint64 maxsplit = -1) -> (string[] results);              // 按分隔符分割字符串（-1会被强制转换为uint32的最大值）
    public fn startswith(string s) -> (bool result);                                    // 判断字符串是否以参数s开头
    public fn unicode() -> (uint16[] result);                                           // 返回字符串的Unicode编码数组
    public fn upper() -> (string result);                                               // 返回字符串大写
}
```

```c
viola$lang$string$String *viola$lang$string$fromCharString(const char *str);    // 从C语言字符串创建Viola字符串。
```

### 文件读写

基本信息：

- 引用方式：`viola.io.file`
- 源码路径：`viola/io/file.vla`和`viola/lang/global_resource_manager.c`

接口声明（`viola/lang/global_resource_manager.c`）：

（不提供Viola接口）（所有接口名称都需要加上`viola$lang$global_resource_manager$`前缀，并且在头文件中声明，无论是否提供Viola接口）（结构体声明时应使用`typedef`去掉`struct`前缀）

```c
typedef uint32_t RequestType;                                                   // 请求类型编码。
struct Request {...};                                                           // 请求结构体，其中的第一个成员是请求类型编码，类型为RequestType。
struct RequestHandlerVector {                                                   // 请求向量表。
    uint32_t size;
    uint32_t capacity;
    void (*handler)(Request *request);
};

extern RequestHandlerVector *handlerVector;                                     // 请求向量表实例。
extern RequestQueue *queue;                                                     // 请求队列实例。

void handleRequest(Request *request) {                                          // 处理请求。此函数由主线程调用。
    handlerVector->handler[request->type](request);
}
```