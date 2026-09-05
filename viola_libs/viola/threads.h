/* -*- coding: utf-8 -*-
 * Viola线程调度系统。
 *
 * 命名空间：viola.threads（C标识符前缀 viola$threads$）。
 * 所有接口均在头文件中声明。
 */
#ifndef VIOLA_THREADS_H
#define VIOLA_THREADS_H

#include <stdint.h>

/* 前置声明 */
typedef struct viola$lang$exception$Exception viola$lang$exception$Exception;
typedef struct viola$lang$string viola$lang$string;

/* 函数调用 */
typedef struct viola$threads$FuncCall viola$threads$FuncCall;
struct viola$threads$FuncCall {
    void *args;                              /* 参数元组 */
    void *rets;                              /* 返回元组（无返回值时为NULL） */
    void *func;                              /* 被调用的函数（$async形式） */
    struct viola$threads$Listener *listener; /* 关联的任务监听器 */
};

/* 任务监听器 */
typedef struct viola$threads$Listener viola$threads$Listener;
struct viola$threads$Listener {
    viola$lang$exception$Exception *exc;     /* 当前异常 */
    viola$lang$uint32 currentThreadId;       /* 当前执行线程 */
    volatile uint8_t done;                   /* 任务是否已完成 */
};

/* 调试标记（traceback） */
typedef struct viola$threads$Mark {
    void *path;                              /* 源文件路径字符串 */
    viola$lang$uint32 line;                  /* 行号 */
    viola$lang$string *text;                 /* 文本 */
} viola$threads$Mark;

/* 线程A栈：存放traceback字符串指针。调用函数时压栈，函数返回时退栈。 */
typedef struct viola$threads$StackA {
    viola$lang$uint32 size;
    viola$lang$uint32 capacity;
    viola$threads$Mark **stack;
} viola$threads$StackA;

/* 线程信息 */
typedef struct viola$threads$ThreadInfo {
    viola$lang$uint32 targetStackASize;      /* 切换线程时，目标线程栈A的大小 */
    viola$lang$uint32 targetThreadId;        /* 目标线程ID */
    viola$lang$uint64 stackASize;            /* 当前线程栈A的大小 */
} viola$threads$ThreadInfo;

/* 线程B栈：存放ThreadInfo结构体指针。调用异步函数时压栈，异步函数返回时退栈。 */
typedef struct viola$threads$StackB {
    viola$lang$uint32 size;
    viola$lang$uint32 capacity;
    viola$threads$ThreadInfo *stack;
} viola$threads$StackB;

/* 线程 */
typedef struct viola$threads$Thread {
    viola$threads$StackA *stackA;
    viola$threads$StackB *stackB;
} viola$threads$Thread;

/* 任务队列 */
typedef struct viola$threads$TaskQueue {
    viola$threads$FuncCall **queue;
    viola$lang$uint32 head;
    viola$lang$uint32 tail;
    viola$lang$uint32 size;
    viola$lang$uint32 capacity;
} viola$threads$TaskQueue;

extern viola$threads$Thread **viola$threads$threads;   /* 线程实例数组 */
extern viola$lang$uint32 viola$threads$threadsNum;     /* 线程数量 */
extern viola$threads$TaskQueue *viola$threads$queue;   /* 任务队列实例 */

/* 添加线程。此函数提供Viola接口。 */
void viola$threads$addThread(viola$lang$uint32 num, viola$threads$Listener *listener);
/* 删除线程。此函数提供Viola接口。 */
void viola$threads$delThread(viola$lang$uint32 num, viola$threads$Listener *listener);
/* 将函数调用加入任务队列。 */
void viola$threads$enqueue(viola$threads$FuncCall *call);
/* 获取线程数量。此函数提供Viola接口。 */
void viola$threads$getThreadsNum(viola$lang$uint32 *result, viola$threads$Listener *listener);
/* 初始化任务监听器。senderThreadId指的是发出任务的线程ID。 */
void viola$threads$initListener(viola$threads$Listener *listener, viola$lang$uint32 senderThreadId);
/* 对相应线程的A栈进行退栈。 */
void viola$threads$popStackA(viola$lang$uint32 threadId);
/* 对相应线程的B栈进行退栈。 */
void viola$threads$popStackB(viola$lang$uint32 threadId);
/* 对相应线程的A栈进行压栈。 */
void viola$threads$pushStackA(viola$lang$uint32 threadId, viola$threads$Mark *mark);
/* 对相应线程的B栈进行压栈。 */
void viola$threads$pushStackB(viola$lang$uint32 threadId);
/* 设置线程数量。此函数提供Viola接口。 */
void viola$threads$setThreadsNum(viola$lang$uint32 num, viola$threads$Listener *listener);
/* 等待监听器。此操作应当在结束前销毁监听器。 */
void viola$threads$waitListener(viola$threads$Listener *listener);

#endif /* VIOLA_THREADS_H */
