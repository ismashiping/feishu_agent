# RAG / Integrations / DB 结构迁移 Phase 3 实际交付（2026-10-31）

## 1. 当前架构和执行链

原runtime显式装配rag.embedding/OfflineReader、db.connection/store及integrations.llm/openalex等组件；application协调摄取、检索、科研、全文、分析、报告及更新。领域切分和引用规则仍在domain，Agents/API保持前两阶段结构。

本地：IngestionService→rag.offline→rag.pdf/pubmed_xml→domain.chunking→rag.embedding→db.store/versions。研究：ResearchService/Agents→原应用用例→integrations的模型/OpenAlex/开放全文/来源复核适配，全文索引仍由application.fulltext/oa_fulltext协调并写入db.fulltext。普通检索依然经application.retrieval→db.retrieval，未另做一套RAG流程。

## 2. 问题与修改依据

原adapters混放本地解析、HTTP适配及持久化；模块具有清晰职责，可以移动原文件。现有测试在旧模块上patch create_engine、load_local_embedder等，简单重导出函数会丢失相同模块全局注入。因此兼容文件用sys.modules把旧键绑定到唯一canonical模块；两个import顺序均验证同一对象与单一Base.metadata。旧postgres包不整体别名，避免子模块以旧全名重复执行。

21个源码现场快照保存在before/，仅供审查、保留未提交修改与回退依据，不是生产入口。不会将对HEAD的历史业务Diff全部算作本轮变化。

## 3. 迁移计划及实际映射

详见migration-map.md：4个模块→rag（embedding/offline/pdf/pubmed_xml），6个→integrations（llm/langchain_generation/openalex/pubmed_online/oa_fulltext/report_snapshot），11个PostgreSQL模块→db（connection/models/store/retrieval/fulltext/versions/update_runs/governance/maintenance/rebuild/online_publication）。所有持久化独立职责文件保留。

application的用例与Protocol、domain模型和切分均留原位；不替换pypdf、E5、LlamaIndex或pgvector，不修改新旧科研来源业务契约。

## 4. 实际修改与审查

- 新增rag/integrations/db三个轻量包，将21个当前工作区实现移动到唯一新位置，旧21文件仅保留模块别名；未删除任何旧兼容文件或用户数据。
- src活动调用者及scripts导入改用canonical模块；alembic/env.py仅换engine/metadata导入，九份versions文件字节保持原样。scripts/audit_repository.py的领域边界检查加入三个新基础设施命名空间。
- 新增tests/unit/test_rag_db_migration.py及tests/fixtures/migration/phase3-contracts.json。test_package.py只为新canonical模块允许其原已声明SQLAlchemy/httpx导入，网络、线程、配置实例化和日志副作用守卫保持原样。
- 更新当前架构主表及状态记录；新增冻结SPEC、映射、日志及学习教材。未改依赖、锁文件、Docker/Compose、数据库内容、Schema、索引或事务边界；未迁飞书。

AST对比全部21个实现与现场快照一致，仅归一化明确模块路径和Ruff连续导入块排序；不忽略可执行语句。新增兼容代码没有异常捕获、默认值、回退分支、重试、Factory或Repository。原必要的超时、来源校验、事务、幂等和资源释放保留。

## 5. 兼容性检查

- 21组旧新模块对象身份与patch可见性一致，两种全新进程导入顺序通过；ORM仅一个注册表。
- 10张表及其全部声明索引DDL与改动前fixture一致；九份迁移文件SHA256相同，静态alembic heads仍为oa3001_0009。
- 动态sentence_transformers导入仍只在原显式加载路径，find_spec依赖检查、Protocol和运行时资源所有权不变。HTTP/DB/Embedding关闭和错误路径由既有测试覆盖。
- API完整OpenAPI、Agent State、双Graph及ResearchService接口检查继续通过；解析、摄取、检索、全文及引用的原测试断言保留，未修改业务算法或提示词。
- 类型的__module__/模块__file__路径随迁移变化，旧import和monkeypatch保持同对象；不声称显示路径字符串不变。

## 6. 环境、命令与实际结果

Windows/PowerShell，仓库.venv Python3.12.16，-X utf8；未安装依赖或连接真实DB/模型/第三方系统。

1. 冻结后的首批专项（迁移测试、command_runtime/api_runtime/postgres）：91 passed、7 failed，47.68秒，见targeted.txt/xml。7失败均为新增AST检查未允许Ruff导入排序；没有业务或DDL失败。不伪称首轮全绿。
2. 修正AST比较为仅归一化连续import块排序后：全部21模块对比通过，0.63秒，见ast.txt/xml；业务代码未因该比较问题改变。
3. `.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/tmp/rag-db-phase3 --junitxml=docs/rag-db-migration-phase3/full.xml`，实际 **1595 passed、29 failed、122 deselected、0 skipped、0 errors、1 SDK弃用警告，211.65秒**。见full.txt/xml。本阶段70个新增测试全部通过；原29失败身份与Phase2完全一致，新增0、消失0，见failure-comparison.json。整库仍未通过。
4. `.venv/Scripts/ruff.exe check src tests alembic/env.py docs/learning/phase-03/rag-db-migration/demo.py`通过；scripts import排序已随迁移修正，`ruff check scripts`仍为原17个E402，未借本轮修复已禁用脚本。
5. `.venv/Scripts/python.exe -X utf8 -m mypy src --no-error-summary`失败，193条，与Phase2按迁移路径/行号归一后新增0、消失0，见mypy.txt和mypy-comparison.json。不标类型检查通过。
6. src/tests/scripts/alembic共224个Python文件AST语法检查通过；本轮src/scripts/Alembic入口/测试git diff --check通过。两个模块入口--help成功，见cli-help.txt和feishu-help.txt。
7. 学习Demo首跑漏传parse_pdf必需document_id导致TypeError；修正为使用真实PDF内容hash调用原document_id_for后退出0，解析15页、离线编译10表metadata并确认Embedding别名身份，见demo.txt。pypdf警告缺少可选fontTools，本轮未安装依赖；不据此声称所有字体编码提取完整。Demo未调用真实Embedding、模型或数据库。

## 7. 剩余风险、教材与停止边界

相对既有基线的Phase3结构兼容门槛满足。原29失败（旧PubMed科研契约/local业务范围冲突）及193类型错误继续开放；真实PostgreSQL事务/向量、Redis、Embedding模型、LLM、在线文献/全文、飞书收发及医学人工签署均未验证，122排除不计通过。未部署或运行迁移。DDL/AST一致不能代替真实集成验收。

教材位于docs/learning/phase-03/rag-db-migration：六份学习文档及demo.py。新增知识点：基础设施职责、模块身份兼容、ORM单注册表、离线DDL与迁移hash冻结、显式资源所有权。

旧模块和历史教材导入继续兼容，删除须在Phase5提供引用证据和回滚方案并获明确确认。下一候选为用户确认后的架构Phase4飞书与工程配置整理，本轮停止；不改变历史业务Phase3或医学验收状态。
