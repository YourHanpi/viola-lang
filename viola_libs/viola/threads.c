/* -*- coding: utf-8 -*-
 * Viola线程调度系统实现。
 *
 * 模型：主线程（线程0）执行入口main函数；工作线程执行任务队列中的异步调用。
 * 主线程在waitListener中空闲等待时，顺带处理全局资源管理器中的请求。
 * 线程间同步使用pthread（MinGW-w64提供winpthreads）。
 */
#include "threads.h"
#include "lang/global_resource_manager.h"

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sched.h>
#endif

/* ================= 全局状态 ================= */
viola$threads$Thread **viola$threads$threads = NULL;
viola$lang$uint32 viola$threads$threadsNum = 0;
viola$threads$TaskQueue *viola$threads$queue = NULL;

static pthread_mutex_t s_queueMutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t s_queueCond = PTHREAD_COND_INITIALIZER;
static int s_running = 0;
static pthread_t *s_workers = NULL;
static viola$lang$uint32 s_workerNum = 0;

/* ================= 内部工具 ================= */

static viola$threads$TaskQueue *createQueue(void) {
    viola$threads$TaskQueue *q = (viola$threads$TaskQueue *)malloc(sizeof(viola$threads$TaskQueue));
    q->capacity = 64;
    q->queue = (viola$threads$FuncCall **)malloc(sizeof(viola$threads$FuncCall *) * q->capacity);
    q->head = 0;
    q->tail = 0;
    q->size = 0;
    return q;
}

static viola$threads$StackA *createStackA(void) {
    viola$threads$StackA *stack = (viola$threads$StackA *)malloc(sizeof(viola$threads$StackA));
    stack->size = 0;
    stack->capacity = 64;
    stack->stack = (viola$threads$Mark **)malloc(sizeof(viola$threads$Mark *) * stack->capacity);
    return stack;
}

static viola$threads$StackB *createStackB(void) {
    viola$threads$StackB *stack = (viola$threads$StackB *)malloc(sizeof(viola$threads$StackB));
    stack->size = 0;
    stack->capacity = 64;
    stack->stack = (viola$threads$ThreadInfo *)malloc(sizeof(viola$threads$ThreadInfo) * stack->capacity);
    return stack;
}

static viola$threads$Thread *createThread(void) {
    viola$threads$Thread *thread = (viola$threads$Thread *)malloc(sizeof(viola$threads$Thread));
    thread->stackA = createStackA();
    thread->stackB = createStackB();
    return thread;
}

static void destroyThread(viola$threads$Thread *thread) {
    if (thread == NULL) {
        return;
    }
    if (thread->stackA != NULL) {
        free(thread->stackA->stack);
        free(thread->stackA);
    }
    if (thread->stackB != NULL) {
        free(thread->stackB->stack);
        free(thread->stackB);
    }
    free(thread);
}

static void yieldCPU(void) {
#ifdef _WIN32
    Sleep(0);
#else
    sched_yield();
#endif
}

/* 确保运行时已初始化（线程数组、任务队列、资源管理器） */
static void ensureRuntime(void) {
    if (viola$threads$threads != NULL) {
        return;
    }
    viola$lang$global_resource_manager$init();
    viola$threads$queue = createQueue();
    viola$threads$threadsNum = 2; /* 主线程 + 1个工作线程 */
    viola$threads$threads = (viola$threads$Thread **)malloc(
        sizeof(viola$threads$Thread *) * viola$threads$threadsNum);
    for (viola$lang$uint32 i = 0; i < viola$threads$threadsNum; i++) {
        viola$threads$threads[i] = createThread();
    }
    s_running = 1;
}

/* 工作线程入口 */
static void *workerMain(void *arg) {
    viola$lang$uint32 workerId = (viola$lang$uint32)(uintptr_t)arg;
    while (s_running) {
        viola$threads$FuncCall *call = NULL;
        pthread_mutex_lock(&s_queueMutex);
        while (s_running && viola$threads$queue->size == 0) {
            pthread_cond_wait(&s_queueCond, &s_queueMutex);
        }
        if (!s_running) {
            pthread_mutex_unlock(&s_queueMutex);
            break;
        }
        call = viola$threads$queue->queue[viola$threads$queue->head];
        viola$threads$queue->head = (viola$threads$queue->head + 1) % viola$threads$queue->capacity;
        viola$threads$queue->size--;
        pthread_mutex_unlock(&s_queueMutex);
        if (call != NULL) {
            call->listener->currentThreadId = workerId;
            ((void (*)(void *, void *, viola$threads$Listener *))call->func)(
                call->args, call->rets, call->listener);
            call->listener->done = 1;
        }
    }
    return NULL;
}

static void startWorkers(void) {
    pthread_mutex_lock(&s_queueMutex);
    s_running = 1;
    s_workerNum = viola$threads$threadsNum > 0 ? viola$threads$threadsNum - 1 : 0;
    s_workers = (pthread_t *)malloc(sizeof(pthread_t) * (s_workerNum > 0 ? s_workerNum : 1));
    for (viola$lang$uint32 i = 0; i < s_workerNum; i++) {
        pthread_create(&s_workers[i], NULL, workerMain, (void *)(uintptr_t)(i + 1));
    }
    pthread_mutex_unlock(&s_queueMutex);
}

/* ================= 对外接口 ================= */

void viola$threads$initListener(viola$threads$Listener *listener, viola$lang$uint32 senderThreadId) {
    ensureRuntime();
    memset(listener, 0, sizeof(viola$threads$Listener));
    listener->currentThreadId = senderThreadId;
    listener->done = 1;
}

void viola$threads$enqueue(viola$threads$FuncCall *call) {
    ensureRuntime();
    if (s_workers == NULL) {
        startWorkers();
    }
    call->listener->done = 0;
    pthread_mutex_lock(&s_queueMutex);
    if (viola$threads$queue->size >= viola$threads$queue->capacity) {
        viola$lang$uint32 newCapacity = viola$threads$queue->capacity * 2;
        viola$threads$FuncCall **newQueue = (viola$threads$FuncCall **)malloc(
            sizeof(viola$threads$FuncCall *) * newCapacity);
        for (viola$lang$uint32 i = 0; i < viola$threads$queue->size; i++) {
            newQueue[i] = viola$threads$queue->queue[
                (viola$threads$queue->head + i) % viola$threads$queue->capacity];
        }
        free(viola$threads$queue->queue);
        viola$threads$queue->queue = newQueue;
        viola$threads$queue->head = 0;
        viola$threads$queue->tail = viola$threads$queue->size;
        viola$threads$queue->capacity = newCapacity;
    }
    viola$threads$queue->queue[viola$threads$queue->tail] = call;
    viola$threads$queue->tail = (viola$threads$queue->tail + 1) % viola$threads$queue->capacity;
    viola$threads$queue->size++;
    pthread_cond_signal(&s_queueCond);
    pthread_mutex_unlock(&s_queueMutex);
}

void viola$threads$waitListener(viola$threads$Listener *listener) {
    while (!listener->done) {
        /* 主线程在等待期间处理全局资源请求（如文件读写） */
        if (listener->currentThreadId == 0) {
            viola$lang$global_resource_manager$drainRequests();
        }
        yieldCPU();
    }
    free(listener);
}

void viola$threads$pushStackA(viola$lang$uint32 threadId, viola$threads$Mark *mark) {
    ensureRuntime();
    viola$threads$StackA *stack = viola$threads$threads[threadId]->stackA;
    if (stack->size >= stack->capacity) {
        stack->capacity *= 2;
        stack->stack = (viola$threads$Mark **)realloc(stack->stack,
                                                       sizeof(viola$threads$Mark *) * stack->capacity);
    }
    stack->stack[stack->size++] = mark;
}

void viola$threads$popStackA(viola$lang$uint32 threadId) {
    ensureRuntime();
    viola$threads$StackA *stack = viola$threads$threads[threadId]->stackA;
    if (stack->size > 0) {
        stack->size--;
    }
}

void viola$threads$pushStackB(viola$lang$uint32 threadId) {
    ensureRuntime();
    viola$threads$StackB *stack = viola$threads$threads[threadId]->stackB;
    if (stack->size >= stack->capacity) {
        stack->capacity *= 2;
        stack->stack = (viola$threads$ThreadInfo *)realloc(
            stack->stack, sizeof(viola$threads$ThreadInfo) * stack->capacity);
    }
    viola$threads$ThreadInfo info;
    info.targetStackASize = 0;
    info.targetThreadId = 0;
    info.stackASize = viola$threads$threads[threadId]->stackA->size;
    stack->stack[stack->size++] = info;
}

void viola$threads$popStackB(viola$lang$uint32 threadId) {
    ensureRuntime();
    viola$threads$StackB *stack = viola$threads$threads[threadId]->stackB;
    if (stack->size > 0) {
        stack->size--;
    }
}

void viola$threads$addThread(viola$lang$uint32 num, viola$threads$Listener *listener) {
    ensureRuntime();
    viola$lang$uint32 newNum = viola$threads$threadsNum + num;
    viola$threads$threads = (viola$threads$Thread **)realloc(
        viola$threads$threads, sizeof(viola$threads$Thread *) * newNum);
    for (viola$lang$uint32 i = viola$threads$threadsNum; i < newNum; i++) {
        viola$threads$threads[i] = createThread();
    }
    viola$threads$threadsNum = newNum;
}

void viola$threads$delThread(viola$lang$uint32 num, viola$threads$Listener *listener) {
    ensureRuntime();
    if (num >= viola$threads$threadsNum) {
        num = viola$threads$threadsNum - 1;
    }
    for (viola$lang$uint32 i = viola$threads$threadsNum - num; i < viola$threads$threadsNum; i++) {
        destroyThread(viola$threads$threads[i]);
        viola$threads$threads[i] = NULL;
    }
    viola$threads$threadsNum -= num;
    if (viola$threads$threadsNum == 0) {
        viola$threads$threadsNum = 1;
        viola$threads$threads[0] = createThread();
    }
}

void viola$threads$getThreadsNum(viola$lang$uint32 *result, viola$threads$Listener *listener) {
    ensureRuntime();
    *result = viola$threads$threadsNum;
}

void viola$threads$setThreadsNum(viola$lang$uint32 num, viola$threads$Listener *listener) {
    ensureRuntime();
    if (num == 0) {
        num = 1;
    }
    while (viola$threads$threadsNum > num) {
        viola$threads$delThread(1, NULL);
    }
    while (viola$threads$threadsNum < num) {
        viola$threads$addThread(1, NULL);
    }
}
