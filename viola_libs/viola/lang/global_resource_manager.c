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

void viola$lang$global_resource_manager$init(void) {
    if (viola$lang$global_resource_manager$handlerVector != NULL) {
        return;
    }
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
    /* 注册文件请求处理器 */
    viola$io$registerFileHandlers();
}

void viola$lang$global_resource_manager$handleRequest(
        viola$lang$global_resource_manager$Request *request) {
    viola$lang$global_resource_manager$handlerVector->handler[request->type](request);
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
    }
}
