# API架构迁移 Phase 2 冻结SPEC

目标：按职责拆分HTTP应用、路由、Schema、边界和有界执行适配；不修改医学业务。输入仍为ApiSettings、RuntimeFactory及既有HTTP请求；输出仍为既有JSON Schema/状态/错误码/响应头。

文件映射：api.py→api/app.py（create_app、lifespan、异常注册）、routes.py（原路由）、middleware.py（原ASGI边界与错误响应）、execution.py（原WorkerPool、同步执行适配及每应用运行状态）；api_runtime.py的DTO/配置→api/schemas.py。ServiceBundle及open_api_runtime资源组装迁至api/runtime.py，api_runtime.py重导出旧Schema、执行类及资源装配，避免重复实现。clinical_agent.api:create_app通过包__init__同对象导出。旧api.py实现由api包接替，不保留两套路由，不清理其他旧入口。

必须保持：全部路由/OpenAPI、Request ID、请求大小/媒体类型/读体10秒限制、错误码和状态、Retry-After；每应用状态隔离；显式DI；启动才装配资源；to_thread、wrap_future和实际Future完成释放容量；关闭先等待池再关闭上下文；启动/关闭失败脱敏；local门禁和历史失败均原样保留。数据模型仍继承领域契约，不迁移领域模型。

测试先编写：复用Phase0完整OpenAPI fixture、新增在线scope的全部错误映射测试（避免旧local门禁遮挡）、新模块无可选依赖隔离导入、兼容对象身份、懒启动及每应用生命周期隔离。复用既有API/runtime/包导入、RAG、Agent和飞书回归。模型/DB/HTTP调用用Fake/Mock隔离，不连接真实服务。

冻结命令：.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/api-phase2 --junitxml=docs/api-migration-phase2/full.xml；.venv/Scripts/ruff.exe check src tests；mypy src与Phase1错误基线对比。pytest默认排除external/performance/database/redis。全量原29失败允许继续开放，不允许新增未解决失败；不伪称整库通过。针对失败修复后重跑受影响范围；阶段交付学习教材及实际记录后停止。

改动前源码快照before-api.py/before-api_runtime.py只用于迁移审查和回退依据，不是运行入口，不包含环境配置或密钥。仅移动当前工作区内容，不用HEAD覆盖未提交修改。删除兼容包装与后续RAG迁移不在本轮范围。

装配边界修订：避免独立导入旧api_runtime时包初始化反向读取尚未定义的ServiceBundle，资源装配放入api/runtime.py，app只依赖新路径；旧模块仅重导出。已有源码检查test_new_runtime_contains_no_pubmed_discovery跟随新装配位置，原断言保持。新增隔离导入包含runtime模块。
