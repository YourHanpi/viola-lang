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

/* 工作线程槽。槽位单独分配且永不移动，因此工作线程持有的指针在
   增删线程时始终有效（viola$threads$threads的下标即线程号，
   0为主线程，1..workerNum为工作线程）。 */
typedef struct WorkerSlot {
    pthread_t thread;
    viola$lang$uint32 id;       /* 对应的viola$threads$threads下标 */
    volatile int shouldExit;    /* 请求该工作线程在完成当前任务后退出 */
    int started;
} WorkerSlot;

static WorkerSlot **s_workers = NULL;
static viola$lang$uint32 s_workerNum = 0;

/* 线程数组的容量与退役块。
   viola$threads$threads会被运行中的工作线程经pushStackA/popStackA等并发读取，
   因此增删线程时不释放旧数组块（realloc/收缩会让并发读者访问已释放内存），
   改为按容量增长并在容量足够时复用；退役块留存至进程结束。
   见开发疑问记录86。 */
static viola$lang$uint32 s_threadsCapacity = 0;
static viola$threads$Thread **s_retiredThreads[64];
static viola$lang$uint32 s_retiredThreadsNum = 0;

/* 确保线程数组容量足够容纳newSize个线程槽（不释放旧块） */
static void reserveThreadSlots(viola$lang$uint32 newSize) {
    if (newSize <= s_threadsCapacity) {
        return;
    }
    viola$lang$uint32 newCapacity = s_threadsCapacity == 0 ? 4 : s_threadsCapacity;
    while (newCapacity < newSize) {
        newCapacity *= 2;
    }
    viola$threads$Thread **newArray = (viola$threads$Thread **)malloc(
        sizeof(viola$threads$Thread *) * newCapacity);
    for (viola$lang$uint32 i = 0; i < s_threadsCapacity; i++) {
        newArray[i] = viola$threads$threads[i];
    }
    if (viola$threads$threads != NULL && s_retiredThreadsNum < 64) {
        /* 旧块暂不释放：可能有工作线程仍持有其指针 */
        s_retiredThreads[s_retiredThreadsNum++] = viola$threads$threads;
    }
    viola$threads$threads = newArray;
    s_threadsCapacity = newCapacity;
}

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

/* 运行时初始化状态：0=未初始化，1=初始化中，2=已初始化。
   global_resource_manager.init()经initListener()回调到本函数，本函数
   又回调init()，形成相互递归；以状态机保证幂等，递归重入时直接返回，
   避免一次性重复分配/泄漏（见开发疑问记录#100）。 */
static int s_runtimeState = 0;

/* 工作线程入口 */
static void *workerMain(void *arg) {
    WorkerSlot *slot = (WorkerSlot *)arg;
    for (;;) {
        viola$threads$FuncCall *call = NULL;
        pthread_mutex_lock(&s_queueMutex);
        while (!slot->shouldExit && viola$threads$queue->size == 0) {
            pthread_cond_wait(&s_queueCond, &s_queueMutex);
        }
        if (slot->shouldExit) {
            /* 该线程被请求移除：不再取新任务，直接退出
               （已完成当前任务，等待中的任务仍留在队列里由其他线程执行） */
            pthread_mutex_unlock(&s_queueMutex);
            break;
        }
        call = viola$threads$queue->queue[viola$threads$queue->head];
        viola$threads$queue->head = (viola$threads$queue->head + 1) % viola$threads$queue->capacity;
        viola$threads$queue->size--;
        pthread_mutex_unlock(&s_queueMutex);
        if (call != NULL) {
            call->listener->currentThreadId = slot->id;
            ((void (*)(void *, void *, viola$threads$Listener *))call->func)(
                call->args, call->rets, call->listener);
            call->listener->done = 1;
        }
    }
    return NULL;
}

/* 新增一个工作线程（真实创建pthread），并扩展线程槽数组 */
static void addWorker(void) {
    /* 1. 扩展viola$threads$threads（线程号即下标） */
    reserveThreadSlots(viola$threads$threadsNum + 1);
    viola$threads$threads[viola$threads$threadsNum] = createThread();
    viola$threads$threadsNum++;
    /* 2. 槽位单独分配，指针数组扩容不会移动已分配槽位 */
    s_workers = (WorkerSlot **)realloc(s_workers, sizeof(WorkerSlot *) * (s_workerNum + 1));
    WorkerSlot *slot = (WorkerSlot *)malloc(sizeof(WorkerSlot));
    slot->id = viola$threads$threadsNum - 1;
    slot->shouldExit = 0;
    slot->started = 1;
    s_workers[s_workerNum] = slot;
    s_workerNum++;
    pthread_create(&slot->thread, NULL, workerMain, slot);
}

/* 移除最后一个工作线程：请求其退出并等待其完成当前任务，
   同时销毁对应的线程槽（保持线程号与下标一致） */
static void removeWorker(void) {
    if (s_workerNum == 0) {
        return;
    }
    WorkerSlot *slot = s_workers[s_workerNum - 1];
    pthread_mutex_lock(&s_queueMutex);
    slot->shouldExit = 1;
    pthread_cond_broadcast(&s_queueCond);
    pthread_mutex_unlock(&s_queueMutex);
    pthread_join(slot->thread, NULL);
    s_workerNum--;
    free(slot);
    /* 销毁对应的线程槽。
       不收缩数组（容量保留）：运行中的其他线程可能正在读取该数组，
       收缩/realloc会让它们访问已释放的块。 */
    if (viola$threads$threadsNum > 1) {
        viola$lang$uint32 last = viola$threads$threadsNum - 1;
        destroyThread(viola$threads$threads[last]);
        viola$threads$threads[last] = NULL;
        viola$threads$threadsNum--;
    }
}

/* 确保运行时已初始化（线程数组、任务队列、工作线程、资源管理器） */
static void ensureRuntime(void) {
    if (s_runtimeState != 0) {
        return;
    }
    s_runtimeState = 1;
    viola$threads$queue = createQueue();
    /* 主线程（线程0） */
    viola$threads$threadsNum = 1;
    reserveThreadSlots(1);
    viola$threads$threads[0] = createThread();
    /* 默认1个工作线程（主线程 + 1个工作线程，共2个） */
    addWorker();
    s_runtimeState = 2;
    /* 资源管理器的初始化会回调initListener->ensureRuntime，
       此时s_runtimeState已为2，递归调用直接返回 */
    viola$lang$global_resource_manager$init();
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

viola$lang$exception$Exception *viola$threads$waitListener(viola$threads$Listener *listener) {
    while (!listener->done) {
        /* 主线程在等待期间处理全局资源请求（如文件读写） */
        if (listener->currentThreadId == 0) {
            viola$lang$global_resource_manager$drainRequests();
        }
        yieldCPU();
    }
    /* 取出任务未捕获的异常后再销毁监听器：调用方据此把异步调用
       抛出的异常传播到自己的try/catch */
    viola$lang$exception$Exception *exception = listener->exception;
    listener->exception = NULL;
    free(listener);
    return exception;
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
    for (viola$lang$uint32 i = 0; i < num; i++) {
        addWorker();
    }
}

void viola$threads$delThread(viola$lang$uint32 num, viola$threads$Listener *listener) {
    ensureRuntime();
    /* 主线程（线程0）不可删除：最多删除到只剩主线程 */
    if (num >= viola$threads$threadsNum) {
        num = viola$threads$threadsNum - 1;
    }
    for (viola$lang$uint32 i = 0; i < num; i++) {
        removeWorker();
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
