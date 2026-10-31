# RAG / Integrations / DB 结构迁移 Phase 3 冻结SPEC

目标：移动21个现有适配模块，保持业务算法、公开接口和持久化契约；不新增框架或后续能力。

映射：adapters.embedding/offline/pdf/pubmed_xml→rag同名模块；adapters.llm/langchain_generation/openalex/pubmed_online/oa_fulltext/report_snapshot→integrations同名模块；adapters.postgres的11个独立实现→db同名模块。application的摄取/检索/全文/科研/分析/报告/更新用例及Protocol继续保留，domain.chunking及全部领域契约保留。rag本地解析与在线OA下载适配分开，application.oa_fulltext保留索引和证据业务规则；不引入重复RAG流程。

输入输出：所有函数/类/配置及Protocol不变，仅模块位置变化。外部数据、HTTP请求和数据库行仍由原边界验证；原异常分类、超时、事务、去重、签名和医学引用真实性检查保留。动态导入sentence_transformers及TYPE_CHECKING/函数内依赖导入保持原时机。engine由原runtime管理，HTTP由既有上下文关闭，embedder仍显式加载复用。

兼容：旧模块用sys.modules绑定canonical模块对象，保留旧import、内部辅助符号和monkeypatch全局变量注入。旧postgres包不整体别名，避免以两个模块名重复加载ORM类。此为明确的旧调用者兼容要求，不新增通用代理/工厂。不得移除兼容路径。

活动src和scripts调用者迁到新导入；alembic/env.py仅调整metadata/engine导入。alembic/versions全部文件按SHA256冻结且不编辑，不运行迁移。历史docs/demo继续旧import兼容，不批量改写历史。tests大多继续旧路径验证；架构/隔离检查跟随canonical位置，断言不放宽I/O禁止条件，仅允许模块已声明SQLAlchemy/httpx导入。

测试先编写：tests/fixtures/migration/phase3-contracts.json冻结映射、全部表/索引DDL及迁移文件hash；新增完整模块身份/monkeypatch、双导入顺序、声明依赖下无I/O导入、规范模块无旧导入、domain无外部依赖及原实现AST等价检查。源快照位于本目录before供审查，非运行入口。复用原解析/Embedding/HTTP/检索/全文/引用/事务/资源/入口测试。

验收命令：.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/rag-db-phase3 --junitxml=docs/rag-db-migration-phase3/full.xml；.venv/Scripts/ruff.exe check src tests；mypy src对照Phase2归一化结果；alembic heads只静态读取revision。默认排除external/performance/database/redis，真实DB/模型/API/飞书未运行单列。全量不新增未解决失败，原29失败及193类型错误不标通过。阶段交付六份学习材料与Demo后停止，不迁飞书、不部署。
