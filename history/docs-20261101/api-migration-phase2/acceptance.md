# API结构迁移 Phase 2 实际交付（2026-10-31）

## 1. 当前架构和执行链

临床API兼容入口clinical_agent.api:create_app → api/app.py工厂/lifespan/异常注册 → api/runtime.py显式资源装配 → api/middleware.py请求边界 → api/routes.py路由 → api/execution.py有界同步任务适配 → 原application服务。Schema和ApiSettings位于api/schemas.py，领域模型继续留在domain。

Lifespan仍用to_thread进入服务上下文；默认容量2、上限4，仍按实际Future完成释放名额；关闭先等待池再关闭ExitStack。不在导入或工厂调用时创建模型、数据库连接或后台线程。

## 2. 问题与修改依据

原api.py把应用创建、ASGI边界、错误响应、同步执行和路由放在一起，原api_runtime.py混合Schema、执行器和资源组装。本轮按明确职责提取原实现；迁移前现场源码保存在before-api.py/before-api_runtime.py，只作审查依据，未从HEAD覆盖用户未提交修改。

新API包若反向导入尚在初始化的旧api_runtime，会出现循环依赖风险。因此canonical资源组装迁入api/runtime.py，旧api_runtime只重导出。未新增资源类或抽象层。

## 3. 迁移计划与实际文件映射

- 原api.py移动并拆分为api/app.py、routes.py、middleware.py、execution.py。原文件路径由api包接替，不保留两套路由。
- 原api_runtime.py中的六个配置/DTO类→api/schemas.py；BusyError/WorkerPool→execution.py；ServiceBundle/open_api_runtime→runtime.py。
- api/__init__.py兼容导出原create_app、RuntimeFactory和原已导入的公共API类型/运行时对象；api_runtime.py保留同对象兼容导出。
- 新增tests/unit/test_api_migration.py、SPEC、源码快照、实际日志和六份学习文档与Demo。
- tests/unit/test_openalex.py中的源码位置检查跟随api/runtime.py，原无PubMed发现和共享科研装配断言保持。
- 当前架构/状态表只追加本轮事实。未改pyproject、锁文件、Docker/Compose、数据库、业务提示词、Agent和RAG算法；未删除废弃兼容入口。

## 4. 实际修改与核心Diff审查

路由函数、请求边界、错误映射、配置校验、池实现及lifespan均移动原实现。原execute闭包改为execute(state, request, operation)，路由注册提取为register_routes(app, state)，绑定的每应用state保持原语义。Ruff要求模块级泛型函数使用Python3.12类型参数execute[T]；池方法继续复用原TypeVar。

静态AST核对28个类/函数全部一致，见ast-review.json。核对仅归一化类型标注、泛型声明和execute显式state实参；lifespan、路由operation、错误分支及中间件处理算法均未改变。构造/注册的外围代码另经OpenAPI、隔离导入、双应用生命周期和既有资源测试覆盖。

新增生产逻辑没有防御分支、异常捕获、默认返回、重试或额外业务抽象；原有必要异常捕获及来源路径安全校验原样保留。runtime.py在最终审查中去掉不使用的兼容导出import，兼容导出仅放在旧模块和包入口。

## 5. 兼容性检查

全部OpenAPI与Phase0快照相同，路径、响应模型、状态声明和operation_id未变。请求ID、JSON/编码约束、默认16384字节限制/配置上限65536、流式计数、读体10秒、Retry-After、异常脱敏、local门禁和公开响应契约未改变。

ResearchService公开方法、Agent State与双Graph拓扑检查继续通过；API/CLI/飞书入口和资源关闭测试复用。新增在线scope错误测试避免历史local门禁遮挡，原失败测试未改断言。旧ApiSettings等类的__module__显示路径随迁移变化，旧新import取得相同对象；未承诺类型路径字符串不变。

## 6. 环境、命令与真实验证

Windows/PowerShell，仓库.venv Python3.12.16，使用-X utf8。未安装或升级依赖，未连接真实数据库/模型/第三方API。

- 首批专项：test_api_migration.py、test_api_runtime.py、test_agents_migration.py共54 passed，15.84秒，见targeted.txt/xml。
- 扩展专项：上述测试加test_package.py及test_new_runtime_contains_no_pubmed_discovery，101 passed，76.06秒，见targeted-final.txt/xml。
- 完整回归命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/api-phase2 --junitxml=docs/api-migration-phase2/full.xml`，stdout见full.txt。**1524 passed、29 failed、122 deselected、0 skipped、0 errors、1 SDK弃用警告，170.19秒**。对比Phase0失败身份：相同29，新增0、消失0，见failure-comparison.json。整库仍未通过。
- 全量收集后补充在线饱和/恢复场景，API契约共36 passed，11.62秒，见contracts-final.txt/xml。该项作为补充验证，不计入上述全量数量。
- 最终去掉runtime未使用导出import后重跑新子模块隔离导入和共享资源装配测试，见import-final.txt；不将该整理当作业务变更。
- `.venv/Scripts/ruff.exe check src tests`通过（首次新文件import排序、泛型风格及长行问题已修正）。199个src/tests/scripts/alembic Python文件AST语法检查通过，本轮git diff --check通过。
- `.venv/Scripts/python.exe -X utf8 -m mypy src --no-error-summary`仍失败193条；按API迁移文件位置和行号归一，新增0、消失0，见mypy.txt和mypy-comparison.json。不标类型检查通过。
- Demo实际运行成功：`.venv/Scripts/python.exe -X utf8 docs/learning/phase-02/api-migration/demo.py`，见demo.txt。两个模块入口--help成功，见cli-help.txt/feishu-help.txt。

## 7. 剩余风险与停止边界

相对既有基线的Phase2结构兼容门槛满足，整库原29失败、193条类型错误继续开放；旧local范围冲突和PubMed契约问题未借本轮修复。真实数据库/Redis、Embedding、模型、在线OpenAlex、飞书收发、部署和医学人工签署均未执行，122项排除不计通过。既有scripts的17个Ruff错误不在本轮修复范围。

学习材料位于docs/learning/phase-02/api-migration，包含README/tutorial/code-walkthrough/exercises/interview/troubleshooting及可运行demo.py。新增知识点：ASGI请求边界、显式状态传递、有界Future准入、lifespan资源顺序及兼容包导出。

本轮停止，等待用户确认架构Phase3 RAG/Integrations/DB整理，不自动进入下一阶段。该专项编号不改变历史业务Phase2的验收状态。
