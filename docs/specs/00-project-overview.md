# SPEC 00：项目总体与 Phase 0 工程初始化

框架职责修订（2026-10-27）：LangGraph 负责 Agent 编排，LangChain 负责标准化模型调用及通用 Agent 工具接口，DeepSeek 只作底层模型供应商。当前生成使用供应商无关 LangChainAnswerGenerator 与通过配置 URL 接入的通用 ChatOpenAI；数据库/解析/飞书 SDK 不强行包装为模型工具。详见[调整 SPEC](tasks/langchain-model-boundary.md)。

版本：0.9；日期：2026-10-27；状态：Phase 0 在 Windows 本地工程骨架范围验收完成；学习材料和结论见 [阶段验收报告](../phase0-acceptance.md)。Phase1完成P1-01–12离线入库、基础检索、RAG证据关联工作流、CLI、FastAPI与飞书纯事件过滤，飞书运行时及阶段验收未完成，实际范围见 [开发计划](../development-plan.md)。

## 1. 背景及目标

构建 Clinical Literature Research Agent：辅助医学文献检索、证据整理和科研问答，不承担自动诊断或治疗决策。参考项目仅提供业务设计输入，本项目独立实现。采用适度工程化的模块化单体；CLI、API、飞书复用应用服务，业务逻辑不依赖飞书 SDK。

本次 P0-04 只编写总体与阶段 SPEC，输入为用户需求、项目规则及 P0-01–03 调研；输出为本目录 10 份文档和更新后的开发计划。验收是文档完整性、契约一致性、阶段覆盖与边界核查；没有产品实现，不产生虚假 RED/GREEN。本次完成不代表 Phase 0 完成。

## 2. 功能需求

| 需求 ID | 能力 | 首次交付 |
| --- | --- | --- |
| G-01 | 离线 PDF、PubMed 导出文献及元数据导入 | Phase 1 |
| G-02 | 本地 Embedding、pgvector 检索、基础 RAG | Phase 1 |
| G-03 | 来源、片段定位、结论证据关联及基础引用约束 | Phase 1；Phase 7 深化 |
| G-04 | 官方飞书长连接、文本、过滤、去重、受限线程池、错误回复 | Phase 1 |
| G-05 | 快速受理、后台任务、超时和状态查询 | Phase 2 |
| G-06 | 问题分类、PICO 与查询规划 | Phase 3 |
| G-07 | PubMed 官方接口在线搜索及元数据获取 | Phase 4 |
| G-08 | 关键词/向量混合检索及融合排序 | Phase 5 |
| G-09 | 研究类型、证据局限与冲突呈现 | Phase 6 |
| G-10 | 自动引用核验与结构化研究报告 | Phase 7 |
| G-11 | 增量同步、更新版本和可重复执行 | Phase 8 |
| G-12 | 离线评估、引用准确性、性能与回归评估 | Phase 9；核心测试从 Phase 0 起 |

Phase 0 交付环境与源码调研、技术选型、总体和阶段 SPEC、架构、测试策略、锁定依赖、最小可运行骨架及学习文档。仅创建当前任务所需文件，不提前铺设未来模块。

## 3. 非功能需求

- 所有功能任务按需求 → SPEC → 设计 → 测试 → RED → GREEN → 必要重构 → 回归 → 验收；RED 必须是目标能力未实现导致，环境故障不算目标 RED。
- 外部 LLM、Embedding、存储、PubMed、飞书调用可替换；只在实际边界定义接口，不构建多层 Repository/Service/Factory。
- 密钥来自环境变量；导入模块不连服务、不下载模型、不加载重模型；资源在明确入口创建并关闭。日志有任务关联字段，不输出密钥或默认记录整份文献/完整问题。
- 外部调用有超时及有限重试预算；数据库事务不跨越模型推理；并发有上限，取消等待不等于停止线程。禁止无限等待和无限排队。
- 基础入库幂等、消息去重从 Phase 1 起验收。远端发送不宣称 exactly-once；结果不明确时暴露不确定状态。
- 先支持 Windows x64 开发、Linux x64 glibc 部署及 CPU 推理；具体解释器、版本与构建按 [技术选型](../tech-stack.md) 复核，不把研究清单视为运行通过。
- 文献原文视为数据，不得改变工具权限或系统规则；生成不因来源文本中的指令执行外部操作。

## 4. 本阶段不实现的内容

Phase 0 不实现入库、向量库业务表、RAG、飞书连接、PubMed 在线搜索、PICO、研究质量打分、业务报告、定时同步或评估引擎。不创建假的回答接口或把占位结果当业务 Demo；最小 Demo 只展示配置、日志、CLI 和测试执行。

不默认微服务、Kubernetes、分布式事务、观测平台、复杂异常体系、通用重试框架。真实服务验证未完成时明确列出，不能用 Mock 替代验收。

## 5. 输入输出契约

以下是跨阶段逻辑契约，不是已实现 API；Pydantic 字段约束、实际路由和模块位置由所属任务细化。

- `ImportRequest`：本地来源、格式、可选元数据；输出 `IngestionResult`，每项区分 imported / already_present / needs_update / conflict / rejected / failed，包含文档标识、原因及汇总。needs_update 表示已有相同外部身份但内容变化，Phase 1 不覆盖旧内容，Phase 8 再实现版本更新；不把跳过错误当成功。
- `QuestionRequest`：request_id、非空 question、检索范围；默认去首尾空白后 1–4000 字符，top_k 默认 5、允许 1–20。Phase 1 固定 local 范围，Phase 4 才允许 online/hybrid；不支持的选项显式拒绝。
- `ResearchAnswer`：request_id、status（answered / insufficient_evidence）、claims、sources、limitations、retrieval_scope、generated_at。依赖故障走错误契约，不伪装成证据不足。
- `ErrorInfo`：稳定 code、用户可读 message、request_id、retryable；使用扁平业务错误码及成熟异常即可。输入错误、无证据、外部不可用、引用无效、忙碌需可区分；不暴露堆栈和密钥。
- Phase 2 后，受理返回 task_id；任务状态契约见 [SPEC 02](02-async-experience.md)。

## 6. 数据模型

此处定义共享语义；ORM 与业务 DTO 分开。P1-01 已实现文献/证据及日期/来源/定位/Embedding 信息 DTO，实际字段与边界见 [详细契约](tasks/p1-01-literature-contracts.md)；ORM与持久化由[P1-06/07](tasks/p1-07-offline-ingestion.md)实现，claims/答案/引用DTO由[P1-09](tasks/p1-09-basic-rag.md)实现；不是等待后续阶段才补的契约。

| 对象 | 必需字段及规则 |
| --- | --- |
| LiteratureDocument | document_id、title、authors、publication_date、journal、doi、pmid、source_type、source_url、source_uri、abstract、text、content_scope、ingestion_time、content_hash、evidence_chunks。未知 DOI/PMID/期刊/日期可空，作者未知为空列表；字段仍存在，不造值 |
| PublicationDate | raw、year/month/day（可空）、precision（day/month/year/unknown）；不能把仅年份补成 1 月 1 日，日期精度须保留 |
| Source | source_type 为 pdf/pubmed；source_url 为实际可核验公开 URL 或 null；无公开 PDF URL 时记录本地 source_uri 和文件哈希，不生成虚假网址。公开报告不泄露机器绝对路径 |
| EvidenceChunk | chunk_id、document_id、text、location、embedding_info、source_metadata；location 可定位到文档页或摘要章节/字符区间；摘要不得标全文 |
| EmbeddingInfo | model_id、model_revision、tokenizer_revision、dimension、normalized、chunking_version；同一检索空间须一致。向量数值为存储/推理结果，普通回答 DTO 不返回大向量 |
| EvidenceClaim | claim_id、text、kind（evidence/inference/uncertainty）、evidence_chunk_ids、limitations；实质性医学结论不得无证据，推断明确标注且不能超过来源支持 |
| CitationSource | 从已入库或在线验证的可信元数据构造 document_id、标题、作者、日期、期刊、PMID/DOI、URL、使用范围及片段定位；不得接纳模型生成的新元数据 |

ingestion_time/generated_at 使用带时区 UTC；界面可按用户时区转换。document_id/chunk_id 为应用内不透明稳定标识，PMID 是外部标识，不混作内部主键。基础去重以来源身份或内容哈希约束实现；跨来源归并与版本更新在 Phase 8 扩展。

## 7. 核心业务流程

计划业务流：离线来源 → 解析及元数据核验 → 带定位分块 → Embedding → 单文档原子入库 → 检索 → 证据不足分支或有依据生成 → 引用标识检查 → 共享结果 DTO → CLI/API/飞书渲染。Phase 4 后才增加在线来源分支。

Phase 0 工程流：调研 → SPEC → 架构 → 测试策略/任务 SPEC → 干净环境和锁文件 → 最小任务逐个 RED/GREEN → 离线回归和质量检查 → 学习文档 → 阶段验收。任务顺序见 [开发计划](../development-plan.md)。

所有阶段的测试命令、实际结果、Fake 与真实服务验证、未验证项分别记录；功能验收未通过不进入下一阶段，完成文档编写不表示该功能已交付。

## 8. 异常与边界场景

无密钥的 Phase 0 CLI 仍可运行；只有启动需要某服务的入口时才要求相应配置。错误配置须早失败且脱敏。无文献与数据库断线、空检索与搜索失败、未找到证据与证据证明无效必须区分。

扫描件、损坏/加密 PDF、摘要缺失、日期不完整、重复消息、并发重复导入、模型维度变化、向量数量不符、伪造引用、来源撤回和远端发送结果不明都需进入所属阶段测试。文献文本含工具指令时按普通文本处理。

## 9. 测试用例清单

| ID | Phase 0 场景 | 预期 |
| --- | --- | --- |
| P0-T01 | 导入最小包，无密钥、无网络 | 无服务连接、无模型加载及下载 |
| P0-T02 | 默认配置、环境变量覆盖、非法数值/模式 | 明确验证错误，环境隔离后测试可重复 |
| P0-T03 | 日志事件、关联标识、异常与敏感字段 | 可解析结构化输出，不含测试密钥 |
| P0-T04 | CLI --help / 本地环境自检 | 无需外部服务；成功/配置错误有明确退出码 |
| P0-T05 | CLI 使用同一配置/应用装配入口 | 不复制配置和业务逻辑；用替身验证依赖传递 |
| P0-T06 | 新隔离环境按正式锁文件同步 | 依赖一致、安装及 import smoke test 可复现 |
| P0-T07 | Ruff、格式及 mypy | 对当前代码范围通过，不全局忽略类型错误 |

单元与 CLI 装配测试不访问真实服务；P0-T06 是环境集成验证。Phase 1 起另设真实数据库/Redis/模型/飞书测试，不提前给 Phase 0 赋予业务集成范围。

## 10. 可执行验收标准

P0-04 文档任务现在可执行：核对 00–09 文件齐全、每份含本规范要求的 11 节、需求 G-01–12 均映射阶段、相对链接有效、围栏闭合、无伪造“测试通过”记录，并检查空白错误。

P0-04制定时以下检查是Phase 0目标；P0-07/08已记录对应历史结果。下列sync只安装基础开发依赖；对当前仓库执行全量pytest前必须按[README](../../README.md)安装ml/db/rag/api四个extras，不能把历史命令当作当前全量环境准备。项目根目录的PowerShell命令为：

```powershell
$projectPython = Join-Path (Get-Location) '.venv/Scripts/python.exe'
& $projectPython -m uv sync --locked --group dev
& $projectPython -I -m pytest tests/unit tests/integration --cov=clinical_agent --cov-branch
& $projectPython -m ruff check src tests
& $projectPython -m ruff format --check src tests
& $projectPython -m mypy src
```

P0-06 已把 P0-T01–07 映射到实际文件/命令/退出码；P0-07a–d 保留功能 RED/GREEN，P0-07e 完成 Windows 缓存离线重建/wheel，P0-08 完成学习材料与 59 个既有测试复验。环境隔离、完整参数及未验证范围见 [开发记录](../development-plan.md)，不能用全部 skip 获得验收。依赖检查、源码格式检查不计作业务测试。

## 11. 阶段依赖及完成定义（DoD）

P0-01–03 调研已完成；P0-04 本文档组不表示工程完成。P0-05 产出 architecture.md；P0-06 产出 testing-strategy.md 和最小任务详细 SPEC；P0-07 逐个完成骨架、正式锁文件和真实 RED/GREEN；P0-08 验收并生成 docs/learning/phase-00/ 的 README、tutorial、code-walkthrough、exercises、interview、troubleshooting，均基于真实代码和命令。

以上产物、测试记录、可运行最小 Demo、调试与练习齐全且无必需验证缺口时，才可标记 Phase 0 完成。每次一个任务，等待下一任务指令；Phase 1–9 概要进入对应阶段前必须细化，不能直接拿概要一次性编码。

P0-08 已按 [独立清单](tasks/phase0-acceptance.md) 验收上述产物；阶段完成限于已记录的 Windows 骨架范围，不包含 Linux/无缓存下载或真实业务服务。P1-01–12已按各自任务范围交付；Phase 1仍须完成飞书运行时及阶段验收，当前任务表见[开发计划](../development-plan.md#phase-1-任务进度)。开发任务P1-xx与阶段测试场景P1-Txx不同，映射见[MVP](01-mvp.md#验收场景与开发任务的对应关系)。
