# 从HTTP请求到同步业务

## 是什么
FastAPI管理路由、请求解析和响应Schema。ASGI中间件处理底层scope/receive/send，lifespan管理进程内共享资源。项目业务服务仍同步运行，通过有界线程池适配HTTP异步入口。

## 为什么需要
研究可能耗时，直接在事件循环调用同步检索和模型会阻塞健康检查。无界排队又会占用过多资源。这里保留原线程池容量与拒绝策略，只将代码放到明确位置。

## 原理
create_app只声明应用，lifespan进入时验证配置并在to_thread中打开资源。WorkerPool在submit前获取BoundedSemaphore名额，实际Future完成时释放。asyncio.wrap_future让请求等待同步结果；取消等待者不等于运行中的同步任务停止，不能提前释放容量。关闭先等待线程池，再关闭ExitStack中的服务上下文。

## 最小Demo
运行demo.py。观察构建应用后events为空，进入TestClient才出现enter，退出后出现exit。健康响应的request_id与头一致。Fake不实现研究能力，所以不要用该Demo调用/v1/questions。

## 工程取舍
api/runtime.py仅保留原API资源装配；research_runtime仍负责共享科研服务。execution.py的_State是每个应用的状态容器，没有新增巨大Runtime类。旧api_runtime和包级api导出同一对象，避免两套实现。canonical模块不依赖旧兼容模块，避免循环导入；FastAPI和重依赖仍延迟导入。
