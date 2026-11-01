# Agents 结构迁移 Phase 1 冻结范围

目标：独立 State、六角色和 Graph 组装，保持 ResearchService 为业务入口。不推进 API/RAG/DB/飞书迁移，不改提示词、领域模型、算法、异常、预算和资源所有权。

输入：ResearchService 原构造参数及 QuestionRequest；输出：原 ResearchAnswer / AnalysisResult / ReportResult / ResearchReport。State、AgentStep、AgentPatch 的类型、字段及必需性原样迁移。Graph 构建函数接收现有服务和 planner 开关，只注册既有绑定节点与路由；通过 TYPE_CHECKING 避免运行时循环依赖，LangGraph 仍在构建时导入。

异常：反馈轮数校验、超时、检索/生成错误映射和反馈终止保持原实现；不新增异常分支。旧 application.workflow / application.agents 保留同对象重导出，不删除兼容入口。

验收：tests/fixtures/agents/phase0-contracts.json 为改动前现场冻结的双拓扑、类型和公开接口及 OpenAPI；新增测试检查完整节点/边、State 类型与 required/optional、公开签名及旧新对象身份。既有研究、反馈、请求隔离、超时、引用、入口和资源测试复用。全量离线与 Phase 0 JUnit 比较失败身份，不得新增失败；原29失败不标通过。真实依赖无需用于离线测试，数据库/Redis/LLM/飞书端到端未执行单列。

命令：.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/agents-phase1 --junitxml=docs/agents-migration-phase1/full.xml；.venv/Scripts/ruff.exe check src tests；新增测试为 tests/unit/test_agents_migration.py。阶段完成需补学习文档、实际结果及新增防御逻辑静态审查。
