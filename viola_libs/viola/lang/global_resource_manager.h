/* -*- coding: utf-8 -*-
 * Viola全局资源管理器（基于请求）。
 *
 * 命名空间：viola.lang.global_resource_manager
 * （C标识符前缀 viola$lang$global_resource_manager$）。
 * 模型：子线程通过submitRequest发起请求，主线程在waitListener的空闲期间
 * 通过drainRequests执行请求并返回相关数据。
 * 所有接口均在头文件中声明。
 */
#ifndef VIOLA_GLOBAL_RESOURCE_MANAGER_H
#define VIOLA_GLOBAL_RESOURCE_MANAGER_H

#include <stdint.h>

/* 前置声明 */
typedef struct viola$threads$Listener viola$threads$Listener;

/* 请求类型编码 */
typedef uint32_t viola$lang$global_resource_manager$RequestType;

/* 请求结构体，其中的第一个成员是请求类型编码，类型为RequestType。
   0.1起包含引用计数（提交方持有初始引用，处理完成后释放）。 */
typedef struct viola$lang$global_resource_manager$Request viola$lang$global_resource_manager$Request;
struct viola$lang$global_resource_manager$Request {
    viola$lang$global_resource_manager$RequestType type;
    uint32_t $refCount;
};

/* 请求向量表 */
typedef struct viola$lang$global_resource_manager$RequestHandlerVector {
    uint32_t size;
    uint32_t capacity;
    void (**handler)(viola$lang$global_resource_manager$Request *request);
} viola$lang$global_resource_manager$RequestHandlerVector;

/* 请求队列 */
typedef struct viola$lang$global_resource_manager$RequestQueue {
    viola$lang$global_resource_manager$Request **queue;
    uint32_t head;
    uint32_t tail;
    uint32_t size;
    uint32_t capacity;
} viola$lang$global_resource_manager$RequestQueue;

extern viola$lang$global_resource_manager$RequestHandlerVector
    *viola$lang$global_resource_manager$handlerVector; /* 请求向量表实例 */
extern viola$lang$global_resource_manager$RequestQueue
    *viola$lang$global_resource_manager$queue;         /* 请求队列实例 */

/* 处理请求。此函数由主线程调用。 */
void viola$lang$global_resource_manager$handleRequest(viola$lang$global_resource_manager$Request *request);
/* 初始化资源管理器（由运行时统一调用）。 */
void viola$lang$global_resource_manager$init(void);
/* 注册请求处理器。 */
void viola$lang$global_resource_manager$registerHandler(
    viola$lang$global_resource_manager$RequestType type,
    void (*handler)(viola$lang$global_resource_manager$Request *request));
/* 将请求加入请求队列（由各资源模块的子线程调用）。 */
void viola$lang$global_resource_manager$enqueueRequest(viola$lang$global_resource_manager$Request *request);
/* 主线程处理所有待处理请求（在waitListener的空闲期间调用）。 */
void viola$lang$global_resource_manager$drainRequests(void);
/* 0.1新增：以Viola函数（Function结构体）注册请求处理器。
   声明文件见viola/lang/global_resource_manager.vla：
   sq register_request_handler(uint32 request_id, (_Request) -> () handler) -> (); */
void viola$lang$global_resource_manager$register_request_handler(
    viola$lang$uint32 request_id, viola$lang$function$Function *handler,
    viola$threads$Listener *listener);
/* 请求析构（引用计数减一，归零时释放） */
void viola$lang$global_resource_manager$Request$__del__$_0(
    viola$lang$global_resource_manager$Request *_this, viola$threads$Listener *listener);

#endif /* VIOLA_GLOBAL_RESOURCE_MANAGER_H */
