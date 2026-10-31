# 2026-10-31 架构收敛记录

## 范围与基线

这是专项重构，不是业务 Phase 验收。工作区开始时已有大量源码、测试、文档修改及生成物删除；不恢复、不覆盖这些改动，也不把它们计为本轮成果。未变更数据库、密钥、用户数据或部署。

检查入口、runtime、应用/适配器职责、动态导入、依赖锁定、Docker/Compose、CI、测试与当前架构。Python 模块静态清单为 `.artifacts/architecture-inventory.json`（187 文件）；静态清单本身不能证明无动态调用。已安装 llama-index-core 0.14.22、LangGraph 1.2.17、pypdf 6.21.2、FastAPI 0.162.0、Pydantic 2.14.1、SQLAlchemy 2.1.6、sentence-transformers 6.2.0，与声明一致。

## 问题与实际修改

1. `api_runtime.open_api_runtime` 与 `command_runtime.open_research` 重复装配 Retriever、全文源/存储、Planner、Analyzer、Reporter、OpenAlex 和 LangGraph 服务。新增 `research_runtime.open_research_service` 作为唯一科研装配，删除两处重复构造。它有真实资源所有权职责，不是参数转发层。保留入口自身配置、engine/model 生命周期，以及 API 入库装配。
2. `application/fulltext.py` 仍接受不再使用的 PMC 槽位及 OA 关键词替换参数。删除旧关键词契约，更新集成脚本和测试的实际调用，不保留永久适配层。缺失 source/store 的明确 unavailable 行为仍保留。
3. 全文 HTTP 变量由 pmc_client 改为 fulltext_client，符合当前实际 OpenAlex URL 获取职责。

本轮改动文件：`src/clinical_agent/{research_runtime,api_runtime,command_runtime}.py`、`src/clinical_agent/application/fulltext.py`、`scripts/oa_fulltext_integration.py`、`tests/unit/{test_oa_fulltext,test_research_quality_v2}.py` 及本轮 SPEC、架构和报告文档。其他工作区 diff 不属于本轮成果。

## 最终调用关系与保留决策

- API → lifespan/WorkerPool → 共享 ResearchService；CLI/飞书 → open_research → 同一装配。飞书仍由 SDK 事件、Redis 租约、worker、sender 处理消息。
- ResearchService → 唯一 LangGraph → 角色步骤 → Planner/OpenAlexRetrievalService/FulltextService/Analyzer/ReportBuilder。当前为固定角色编排，不应虚构为另一套通用 Tool Calling 注册框架。
- OpenAlex Works 发现 → 返回的真实全文 URL → OAFulltextSource 安全下载/身份检查 → PDF/TEI 解析 → LlamaIndex SentenceSplitter → E5 → pgvector → 段落排序 → 引用核验。未修改 Top-K、过滤、排序、签名或持久化格式。
- 离线 PDF/XML → OfflineReader 内容快照 → source-unit-v1 切分 → E5 → 事务入库。该切分具有精确源区间、预算和版本契约，不能因存在 SentenceSplitter 就直接替换。未引入 VectorStoreIndex 或第二套向量表；现有 SQL 检索还承担版本/治理语义。
- PDF 临时目录释放、公网 IP 固定、HTTPS/重定向检查、体积/超时、格式与身份检查保留。版本发布、来源治理和显式维护入口保留；不因在线科研不用历史摘要就删除维护功能和迁移。

## 验证

- 初次 runtime 验证暴露本轮遗漏的 ResearchLimits import，已修复；系统临时目录拒绝访问后改用仓库内 basetemp。
- `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_api_runtime.py tests/unit/test_command_runtime.py -q --tb=short --basetemp=.artifacts/architecture-runtime`：15 passed。
- 受影响五个测试文件集中验证：首次 3 failed、51 passed，原因是三处未迁移的旧构造参数；更新调用后重跑 `.artifacts/architecture-targeted-final.txt`：54 passed。未削弱任何断言。
- `.venv/Scripts/ruff.exe check src tests`：通过。本轮修改文件加集成脚本 Ruff check 通过。
- `ruff check src tests scripts`：17 个 E402，位于已有改动的禁用 PubMed 脚本，其顶部 SystemExit 后仍有历史代码。本轮未覆盖这些用户改动。
- 格式检查：六个本轮源码/测试文件通过；集成脚本有一处既有字符串引号格式差异，未顺带改写。
- 默认离线回归实际结果追加于下方。真实数据库、模型、Redis、飞书、外部下载及远端 CI 未复验；既有医学缺口保持开放。

## 剩余限制

本轮完成有证据、可验证的装配收敛及旧参数清理；不能据此证明全仓没有其他冗余。全量工作区原本存在大量未验收业务增量，需要依据失败项继续定位，不能声称整个项目已全面验收。未对用途不明的缓存、生成目录或历史验收作批量删除。

## 默认回归实际结果

命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short --basetemp=.artifacts/architecture-tests`。1468 passed、41 failed、122 deselected（192.49s），日志 `.artifacts/architecture-regression.txt`。运行期间完成了三处全文调用修复；因此此日志仍记录修复前的三项失败，其后专项54项已通过。另一本轮源码位置断言需跟随装配迁移：现在检查三入口模块没有 open_pubmed、API/CLI 调用共享装配、共享装配包含 OpenAlexRetriever，未取消检查。

其余37个失败位于 API/CLI、本地/旧 PubMed 与探索分派等测试；例如 API 原预期200/503，当前工作区提前报 local_corpus_not_evidence。该业务门禁属于任务开始前已有改动，不为使历史测试通过而撤销安全/证据规则或修改预期。本轮未证明这些失败在干净历史版本的结果，不能把它们全部定性为环境问题。完整验收未通过。

迁移后的入口源码检查单独重跑：`pytest tests/unit/test_openalex.py::test_new_runtime_contains_no_pubmed_discovery -q --basetemp=.artifacts/architecture-registration`：1 passed。随后 `ruff check src tests` 再次通过。全量回归没有再次执行，不将修复后的专项结果冒充全量通过。

## 2026-10-31 后续归因

修复后的最新回归及37项逐项归因见[专项报告](regression-attribution/README.md)：1480 passed、29 failed、122 deselected。此处上文为原执行事实，未覆盖旧结果。
