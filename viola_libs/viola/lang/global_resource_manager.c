/* -*- coding: utf-8 -*-
 * Viola全局资源管理器（基于请求）实现。
 *
 * 模型：子线程通过enqueueRequest发起请求，主线程在waitListener的空闲期间
 * 通过drainRequests执行请求并返回相关数据。
 */
#include "global_resource_manager.h"
#include "../threads.h"

#include <pthread.h>
#include <stdlib.h>

/* ================= 全局状态 ================= */
viola$lang$global_resource_manager$RequestHandlerVector
    *viola$lang$global_resource_manager$handlerVector = NULL;
viola$lang$global_resource_manager$RequestQueue
    *viola$lang$global_resource_manager$queue = NULL;

static pthread_mutex_t s_mutex = PTHREAD_MUTEX_INITIALIZER;

/* 初始化状态机：0=未初始化，1=初始化中，2=已初始化。
   init()会经initListener()回调到threads.ensureRuntime()，后者又会
   回调init()，形成相互递归；以状态机保证幂等，递归重入时直接返回，
   避免重复分配与泄漏（见开发疑问记录#100）。 */
static int s_initState = 0;

/* 0.1新增：以Viola函数注册的请求处理器表（按request_id索引） */
static viola$lang$function$Function **s_violaHandlers = NULL;
static uint32_t s_violaHandlerCapacity = 0;
/* 请求处理器分发时使用的监听器（请求由主线程执行） */
static viola$threads$Listener s_handlerListener;

/* 将Viola处理器的调用适配为C层请求处理器 */
static void violaHandlerDispatch(viola$lang$global_resource_manager$Request *request) {
    viola$lang$function$Function *fn = NULL;
    if (request->type < s_violaHandlerCapacity) {
        fn = s_violaHandlers[request->type];
    }
    if (fn != NULL && fn->syncPtr != NULL) {
        ((void (*)(viola$lang$global_resource_manager$Request *,
                   viola$threads$Listener *, void *))fn->syncPtr)(
            request, &s_handlerListener, fn->$capture);
    }
}

void viola$lang$global_resource_manager$init(void) {
    /* 幂等：已初始化或正在初始化（递归重入）时直接返回 */
    if (s_initState != 0) {
        return;
    }
    s_initState = 1;
    viola$lang$global_resource_manager$handlerVector =
        (viola$lang$global_resource_manager$RequestHandlerVector *)malloc(
            sizeof(viola$lang$global_resource_manager$RequestHandlerVector));
    viola$lang$global_resource_manager$handlerVector->size = 0;
    viola$lang$global_resource_manager$handlerVector->capacity = 16;
    viola$lang$global_resource_manager$handlerVector->handler =
        (void (**)(viola$lang$global_resource_manager$Request *))malloc(
            sizeof(void (*)(viola$lang$global_resource_manager$Request *)) * 16);
    viola$lang$global_resource_manager$queue =
        (viola$lang$global_resource_manager$RequestQueue *)malloc(
            sizeof(viola$lang$global_resource_manager$RequestQueue));
    viola$lang$global_resource_manager$queue->capacity = 64;
    viola$lang$global_resource_manager$queue->queue =
        (viola$lang$global_resource_manager$Request **)malloc(
            sizeof(viola$lang$global_resource_manager$Request *) * 64);
    viola$lang$global_resource_manager$queue->head = 0;
    viola$lang$global_resource_manager$queue->tail = 0;
    viola$lang$global_resource_manager$queue->size = 0;
    /* 请求处理器分发监听器（请求在主线程执行）。
       此处会回调threads.ensureRuntime()，进而递归调用本函数；
       s_initState已为1，递归调用直接返回，不会重复分配。 */
    viola$threads$initListener(&s_handlerListener, 0);
    /* 注册各资源模块的请求处理器 */
    viola$io$registerFileHandlers();
    viola$os$registerOsHandlers();
    viola$os$path$registerPathHandlers();
    s_initState = 2;
}

void viola$lang$global_resource_manager$handleRequest(
        viola$lang$global_resource_manager$Request *request) {
    /* 未初始化、未注册处理器或类型越界时静默丢弃。
       handlerVector->handler的realloc新增区间未清零，size以外的槽位
       是垃圾值；注册表未初始化（未调用init）时handlerVector为NULL
       （见开发疑问记录#100）。 */
    if (request == NULL ||
        viola$lang$global_resource_manager$handlerVector == NULL ||
        request->type >= viola$lang$global_resource_manager$handlerVector->size) {
        return;
    }
    void (*handler)(viola$lang$global_resource_manager$Request *) =
        viola$lang$global_resource_manager$handlerVector->handler[request->type];
    if (handler == NULL) {
        return;
    }
    handler(request);
}

void viola$lang$global_resource_manager$registerHandler(
        viola$lang$global_resource_manager$RequestType type,
        void (*handler)(viola$lang$global_resource_manager$Request *request)) {
    if (type >= viola$lang$global_resource_manager$handlerVector->capacity) {
        uint32_t newCapacity = viola$lang$global_resource_manager$handlerVector->capacity;
        while (type >= newCapacity) {
            newCapacity *= 2;
        }
        viola$lang$global_resource_manager$handlerVector->handler =
            (void (**)(viola$lang$global_resource_manager$Request *))realloc(
                viola$lang$global_resource_manager$handlerVector->handler,
                sizeof(void (*)(viola$lang$global_resource_manager$Request *)) * newCapacity);
        viola$lang$global_resource_manager$handlerVector->capacity = newCapacity;
    }
    viola$lang$global_resource_manager$handlerVector->handler[type] = handler;
    if (type + 1 > viola$lang$global_resource_manager$handlerVector->size) {
        viola$lang$global_resource_manager$handlerVector->size = type + 1;
    }
}

void viola$lang$global_resource_manager$enqueueRequest(
        viola$lang$global_resource_manager$Request *request) {
    pthread_mutex_lock(&s_mutex);
    if (viola$lang$global_resource_manager$queue->size >=
        viola$lang$global_resource_manager$queue->capacity) {
        uint32_t newCapacity = viola$lang$global_resource_manager$queue->capacity * 2;
        viola$lang$global_resource_manager$Request **newQueue =
            (viola$lang$global_resource_manager$Request **)malloc(
                sizeof(viola$lang$global_resource_manager$Request *) * newCapacity);
        for (uint32_t i = 0; i < viola$lang$global_resource_manager$queue->size; i++) {
            newQueue[i] = viola$lang$global_resource_manager$queue->queue[
                (viola$lang$global_resource_manager$queue->head + i) %
                viola$lang$global_resource_manager$queue->capacity];
        }
        free(viola$lang$global_resource_manager$queue->queue);
        viola$lang$global_resource_manager$queue->queue = newQueue;
        viola$lang$global_resource_manager$queue->head = 0;
        viola$lang$global_resource_manager$queue->tail =
            viola$lang$global_resource_manager$queue->size;
        viola$lang$global_resource_manager$queue->capacity = newCapacity;
    }
    viola$lang$global_resource_manager$queue->queue[
        viola$lang$global_resource_manager$queue->tail] = request;
    viola$lang$global_resource_manager$queue->tail =
        (viola$lang$global_resource_manager$queue->tail + 1) %
        viola$lang$global_resource_manager$queue->capacity;
    viola$lang$global_resource_manager$queue->size++;
    pthread_mutex_unlock(&s_mutex);
}

void viola$lang$global_resource_manager$drainRequests(void) {
    while (viola$lang$global_resource_manager$queue != NULL) {
        pthread_mutex_lock(&s_mutex);
        if (viola$lang$global_resource_manager$queue->size == 0) {
            pthread_mutex_unlock(&s_mutex);
            break;
        }
        viola$lang$global_resource_manager$Request *request =
            viola$lang$global_resource_manager$queue->queue[
                viola$lang$global_resource_manager$queue->head];
        viola$lang$global_resource_manager$queue->head =
            (viola$lang$global_resource_manager$queue->head + 1) %
            viola$lang$global_resource_manager$queue->capacity;
        viola$lang$global_resource_manager$queue->size--;
        pthread_mutex_unlock(&s_mutex);
        viola$lang$global_resource_manager$handleRequest(request);
        /* 引用计数为0的请求在入队时由调用方清零（如文件请求由提交方自行释放），
           仅在请求携带引用计数（>0）时由管理器释放 */
        if (request->$refCount > 0) {
            request->$refCount--;
            if (request->$refCount == 0) {
                free(request);
            }
        }
    }
}

/* 0.1新增：以Viola函数注册请求处理器 */
void viola$lang$global_resource_manager$register_request_handler(
        viola$lang$uint32 request_id, viola$lang$function$Function *handler,
        viola$threads$Listener *listener) {
    (void)listener;
    if (handler == NULL) {
        return;
    }
    if (s_violaHandlers == NULL) {
        s_violaHandlerCapacity = 16;
        s_violaHandlers = (viola$lang$function$Function **)calloc(
            (size_t)s_violaHandlerCapacity, sizeof(viola$lang$function$Function *));
    }
    while (request_id >= s_violaHandlerCapacity) {
        uint32_t newCapacity = s_violaHandlerCapacity * 2;
        s_violaHandlers = (viola$lang$function$Function **)realloc(
            s_violaHandlers, sizeof(viola$lang$function$Function *) * newCapacity);
        memset(s_violaHandlers + s_violaHandlerCapacity, 0,
               sizeof(viola$lang$function$Function *) * (newCapacity - s_violaHandlerCapacity));
        s_violaHandlerCapacity = newCapacity;
    }
    s_violaHandlers[request_id] = handler;
    viola$lang$global_resource_manager$registerHandler(request_id, violaHandlerDispatch);
}

/* 请求析构：引用计数减一，归零时释放 */
void viola$lang$global_resource_manager$Request$__del__$_0(
        viola$lang$global_resource_manager$Request *_this, viola$threads$Listener *listener) {
    (void)listener;
    if (_this == NULL) {
        return;
    }
    if (_this->$refCount > 0) {
        _this->$refCount--;
        if (_this->$refCount == 0) {
            free(_this);
        }
    }
}
