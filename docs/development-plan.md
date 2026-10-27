# 开发进度与任务记录

## 通用模型 API 接入调整（2026-10-27）

用户进一步明确：DeepSeek 只是通过 URL 指定的 API 服务商，项目不保留专属适配器或专属业务逻辑。本次按[修订 SPEC](specs/tasks/langchain-model-boundary.md)移除 `adapters/deepseek.py`、专属 Settings/Generator/工厂及 `langchain-deepseek` 依赖；新增 `adapters/llm.py` 的 `LLMSettings/open_llm`，通过通用 LangChain ChatOpenAI 接入兼容 Chat Completions API。生成仍由 LangChainAnswerGenerator 执行，Agent 编排仍由 LangGraph 执行，领域引用规则保持独立。

配置统一为必填 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，以及可选 `LLM_MAX_TOKENS`；无域名白名单或供应商默认值，不读取旧变量，也不提供旧供应商名称兼容入口。模型 API 需支持标准消息、JSON mode、max_tokens 和非流式响应；私有推理扩展不参与业务。`.env.example` 中 DeepSeek URL/模型名仅为示例数据。

修改涉及模型适配器、CLI/API 装配与 CLI 帮助、Compose 共享环境、依赖/锁文件、协议与装配/在线测试入口、README/PROJECT/架构/技术选型/RAG/入口操作/学习文档。协议测试重命名为 `tests/integration/test_llm.py`，当前源码、测试、manifest、lock 和 Compose 均无 DeepSeek 专属标识；已安装专属集成包也已卸载。历史 SPEC 与真实调用记录保留原时点，并明确迁移说明。

验证：

- RED：通用协议与 URL/模型切换测试 25 failed，均因 `clinical_agent.adapters.llm` 尚未创建。
- GREEN：通用协议、LangChain 生成及 CLI/API 装配测试 48 passed；实际使用 ChatOpenAI/SDK 与 HTTPX MockTransport，覆盖两个远端 URL、网关路径前缀和本地回环 URL，未联网。
- 默认回归：`pytest -q --basetemp=.artifacts/generic-llm-regression-tmp -o cache_dir=.artifacts/generic-llm-cache`，1039 passed / 95 deselected，167.27s；1 项既有飞书 protobuf 弃用警告。
- `ruff check src tests`、新文件格式检查通过；`mypy src` 39 个源文件通过；`uv lock --check --offline --cache-dir .artifacts/generic-llm-uv-cache` 通过，110 条锁记录；CLI help 正常且描述通用模型 API。
- 文件/导入检查确认专属模块不存在、专属集成包已卸载；未发起真实付费模型调用或重建/部署容器。既有线上与容器验收不视为本次迁移后验收。

本项完成；Phase1 医学人工审查仍待完成，后续按既有计划选择任务，不自动进入新阶段。官方接口依据：[ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai)，本次仅使用兼容标准字段。


## 框架职责调整（2026-10-27 历史快照，已由下述通用接入替代）

按用户指定完成单项架构调整，SPEC 为 [LangChain 模型调用边界](specs/tasks/langchain-model-boundary.md)。LangGraph 保留 Agent 状态和分支；新增 `adapters/langchain_generation.py`，用 LangChain BaseChatModel、标准消息与 invoke 统一生成；`adapters/deepseek.py` 改为官方 ChatDeepSeek 装配、显式供应商配置及受限传输，保留兼容入口、响应包门禁和引用规则。通用 Agent 工具接口约定使用 LangChain，当前没有新增未来阶段工具或在线 PubMed。

依赖直接固定 langchain-core 1.7.0 / langchain-deepseek 1.1.1，锁定新增 langchain-openai 1.7.3、openai 3.39.0、jiter 0.18.0 和 tiktoken 0.14.0。已同步 CLI/API 的可选依赖检查、轻量导入审计、README、PROJECT、总体/MVP SPEC、架构/技术选型及 Phase1 学习说明。官方依据：[ChatDeepSeek 标准调用](https://docs.langchain.com/oss/python/integrations/chat/deepseek)。未使用的 LangChain 顶层包不额外安装。

验证记录：

- RED：`pytest tests/unit/test_langchain_generation.py -q`，6 failed，原因是新适配器模块缺失；后续修正测试输入，使合成证据满足现有非空契约。
- GREEN：标准生成器、真实 LangGraph 与 DeepSeek 协议目标测试，80 passed。
- 默认回归：`pytest -q --basetemp=.artifacts/langchain-regression-tmp -o cache_dir=.artifacts/langchain-cache`，1032 passed / 95 deselected，137.65s；1 项既有飞书 SDK protobuf 弃用警告。
- 随后补充标准消息/JSON mode/预算传递和总期限测试，与供应商协议测试合计 28 passed。这两项新增测试不计入上面的 1032。
- `ruff check src tests` 通过；`mypy src`，39 个源文件通过；本地 doctor 返回 ok。`uv lock --check --offline --cache-dir .artifacts/langchain-uv-cache` 验证 111 条锁记录。

全部模型调用验证使用真实 LangChain/ChatDeepSeek 与 HTTPX MockTransport 或标准假模型，不发送真实付费请求；已有容器和真实模型历史验收不视为迁移后的新验收。Phase1 医学人工审查状态保持待完成，本任务不进入后续阶段。后续任务仍按既有阶段计划选择。


更新时间：2026-10-27（Asia/Shanghai）。Phase0已完成；Phase1当前完成P1-01–16：离线入库、基础向量检索、RAG证据关联工作流、CLI、FastAPI、飞书纯事件过滤、Redis原子去重、有界研究任务分派及文本渲染/受限发送；P1-16已通过SDK真实收发、鉴权/装配、Linux共享镜像及隔离Compose验收，边界如下；P1-17技术验收与学习材料已交付，医学支持关系人工审查按用户选择待完成，Phase1未整体验收。Phase0结论见 [阶段报告](phase0-acceptance.md)。

2026-10-27已完成[文档一致性核对](documentation-audit.md)：补充编号映射、MVP剩余任务规划，修正过期当前状态及环境说明；本轮为文档维护，不是新业务任务验收。

本文件记录 Phase 0 执行顺序与 Phase 0–9 阶段路线。总体契约见 [SPEC 00](specs/00-project-overview.md)，未来阶段是概要基线，进入各阶段前必须按最小任务细化，不据此一次性实现全部项目。

| 任务 | 内容 | 状态 | 验收证据 |
| --- | --- | --- | --- |
| P0-01 | 目录、规则和环境检查 | 完成 | [环境检查](research/environment-audit.md) |
| P0-02 | 参考仓库固定版本源码分析 | 完成 | [分析与验收记录](research/reference-repository-analysis.md) |
| P0-03 | 官方文档、PyPI、Python 兼容性与技术选型 | 完成（技术研究） | [技术选型](tech-stack.md)、[核查记录](research/p0-03-validation.md)；研究用版本/哈希清单与 P0-07 正式锁文件分开 |
| P0-04 | 总体 SPEC 和 Phase 0–9 阶段概要 | 完成（SPEC 文档验收） | specs/00–09 十份文档及本阶段路线；不代表 Phase 0 工程验收 |
| P0-05 | 架构、目录、模块边界及核心数据流 | 完成（架构设计验收） | [架构设计](architecture.md)；仅设计与静态核查，尚无业务代码 |
| P0-06 | 最小骨架任务 SPEC、测试清单及测试策略 | 完成（任务 SPEC 与策略文档验收） | [详细任务 SPEC](specs/tasks/phase0-implementation.md)、[测试策略](testing-strategy.md)；制定时尚未创建测试，P0-07 随任务落地 |
| P0-07 | 按任务执行最小骨架 TDD 与环境验证 | 完成（P0-07a–e） | 包/配置/日志/runtime/CLI 真实 RED/GREEN；原/新开发环境各 59 passed，Windows wheel 独立安装与 12 项 CLI 冒烟通过 |
| P0-08 | 学习文档和 Phase 0 验收 | 完成 | [学习导航](learning/phase-00/README.md)、[独立验收报告](phase0-acceptance.md)；最新 59 passed，4 Python/3 PowerShell 示例与 12 项 CLI 复验通过 |

## Phase 1 任务进度

`P1-xx`是开发任务ID；MVP中的`P1-Fxx`是功能需求、`P1-Txx`是验收场景，三者不是同一编号序列。场景与任务的多对多关系见[MVP映射表](specs/01-mvp.md#验收场景与开发任务的对应关系)。下表是当前任务状态入口；后文“本次执行/下一任务”均保留对应历史时点，不能当作当前待办。

| 任务 | 状态 | 范围与证据 |
| --- | --- | --- |
| P1-01 文献与证据 DTO、来源和定位契约 | 完成 | [详细 SPEC](specs/tasks/p1-01-literature-contracts.md)；97 目标用例、158 全量回归通过，无真实解析/数据库/模型调用 |
| P1-02 PDF 文本层解析与逐页来源单元 | 完成 | [详细 SPEC](specs/tasks/p1-02-pdf-parsing.md)；44 目标用例、204 全量回归，真实合成 PDF 与来源页内切片核验 |
| P1-03 本地 PubMed XML 解析与元数据映射 | 完成 | [详细 SPEC](specs/tasks/p1-03-pubmed-xml.md)；74 目标用例、279 全量回归，安全离线映射/逐条结果与摘要定位 |
| P1-04 基于来源单元的分块与 tokenizer 长度契约 | 完成 | [详细 SPEC](specs/tasks/p1-04-source-chunking.md)；38 目标用例、318 全量回归；真实合成 PDF/XML 回建，tokenizer 为显式替身 |
| P1-05 本地 Embedding 与真实 tokenizer 适配 | 完成 | [详细 SPEC](specs/tasks/p1-05-local-embedding.md)；61 单元目标、381 默认回归及 1 项真实 E5 CPU 测试；[使用说明](local-embedding.md) |
| P1-06 PostgreSQL + pgvector 持久化模型与迁移 | 完成 | [SPEC](specs/tasks/p1-06-postgres-schema.md)；13单元目标、47真实数据库、397默认回归；[数据库操作](postgres.md) |
| P1-07 离线入库服务与事务/幂等映射 | 完成 | [SPEC](specs/tasks/p1-07-offline-ingestion.md)；43目标、62数据库、1真实E5+PG链路、445默认回归；[操作说明](offline-ingestion.md) |
| P1-08 基础向量检索与证据命中DTO | 完成 | [SPEC](specs/tasks/p1-08-vector-retrieval.md)；55目标、74数据库、1真实E5+PG检索、503默认回归；[操作说明](vector-retrieval.md) |
| P1-09 基础RAG工作流与证据关联回答 | 完成（Python服务/独立生成验收） | [SPEC](specs/tasks/p1-09-basic-rag.md)；74目标、581默认回归、1真实DeepSeek合成证据测试；[操作说明](basic-rag.md)；未验收真实E5/PG/LLM整链路 |
| P1-10 CLI离线入库与问答入口 | 完成 | [SPEC](specs/tasks/p1-10-cli-entrypoints.md)；43目标、625默认回归、1真实E5/PG+HTTP替身集成；[操作说明](cli.md) |
| P1-11 FastAPI入库与问答入口 | 完成 | [SPEC](specs/tasks/p1-11-fastapi.md)；60目标、687默认、1真实Uvicorn/E5/PG+HTTP替身集成；[操作说明](api.md) |
| P1-12 飞书消息契约与事件过滤 | 完成（纯事件边界） | [SPEC](specs/tasks/p1-12-feishu-events.md)；88事件目标、34隔离导入、777默认回归；[契约说明](feishu-events.md)；本任务不含SDK/Redis/工作池/发送；Redis现由P1-13交付 |
| P1-13 Redis原子消息去重 | 完成（独立去重边界） | [SPEC](specs/tasks/p1-13-redis-dedup.md)、[说明](feishu-dedup.md)；76单元+12真实Redis，854默认回归；原子占位/owner/有限续租/完成与释放/故障隔离通过；其任务验收时工作池/发送未实现，worker现由P1-14交付 |
| P1-14 飞书有界任务分派与服务复用 | 完成（独立分派边界） | [SPEC](specs/tasks/p1-14-feishu-worker.md)、[说明](feishu-worker.md)；43 worker目标、243联合、898默认回归通过；实际线程结束释放容量、去重联动、共享ResearchService及有限关闭；其任务验收时发送/SDK未实现；sender现由P1-15交付 |
| P1-15 飞书文本渲染与受限发送 | 完成（离线发送边界） | [SPEC](specs/tasks/p1-15-feishu-sender.md)、[说明](feishu-sender.md)；72 sender目标、316联合、971默认回归通过；完整来源/局限、双层字节预算、单线程有界队列及官方REST协议；真实租户收发/鉴权装配待P1-16 |
| P1-16 官方SDK长连接、装配与Compose入口 | 完成（任务范围验收） | [SPEC](specs/tasks/p1-16-feishu-runtime.md)、[说明](feishu-runtime.md)；368联合、1023默认回归；真实SDK/Redis/官方回复1 passed（合成研究）；Linux共享镜像、现有迁移/API空库/机器人连接与SIGTERM退出通过，隔离资源已清理 |
| P1-17 MVP阶段验收与学习文档 | 验收中（技术/教材交付，医学人工待审查） | [SPEC](specs/tasks/p1-17-mvp-acceptance.md)、[阶段报告](phase1-acceptance.md)、[学习导航](learning/phase-01/README.md)；真实E5/PG/LLM两样例、Redis组合、安全构建升级；人工签署待完成 |

P1-13/14/15已按下文独立任务范围验收；P1-16已细化并实施，外部验收按上表单列；P1-17已由本次用户指令启动，仅实施既有阶段验收与教材范围；医学人工审查仍待完成，不新增Phase2–9功能。每次仅在用户指定后细化并完成其中一项；若实施前需调整拆分，应同步本表及MVP映射，不重编号已交付任务。

## P0-02 本次执行

执行前已读取项目规则、已有环境记录并检查文件与 Git 状态；当前没有已有业务代码、测试或 specs 目录。任务范围和验收场景记录在调研报告第 1 节。

使用 GitHub 连接器核实默认分支并固定提交，获取完整树，分批读取全部非空文件；无 API 调用失败或响应截断。完成调用链、数据模型、依赖及测试性质交叉核查。

文件变更：新增 `docs/research/reference-repository-analysis.md`、`docs/development-plan.md`。原环境检查保留为历史事实；其中“尚未验证参考仓库”的描述是 P0-01 时点记录，已由 P0-02 报告补充。

测试结果：未运行 pytest，无应用实现、无 RED/GREEN；本任务采用源码核查验收，不能解释为参考项目或本项目功能测试通过。实际执行两次 `git diff --no-index --check -- /dev/null <文档路径>`，无空白错误，仅有 Git 的 LF → CRLF 提示。PowerShell 检查分析报告的 6 个 Markdown 围栏，均成对；进度文档无围栏；两个相对链接目标的 `Test-Path` 均为 True。最终 `git status --short` 显示原两份说明及 docs/ 尚未跟踪，未创建提交。

后续：P0-03 技术选型；每次一个当前阶段任务。Phase 1 第一个任务将在 MVP SPEC 完成后明确，当前不开始业务实现。

## P0-03 本次执行

已按任务约定核查官方文档及 25 个候选包的 PyPI 元数据；保存版本、Python 要求、依赖、发布时间和发行哈希。选择 Python 3.12 独立环境、Pydantic v2、结构化日志、PostgreSQL + pgvector、SQLAlchemy/Alembic、官方飞书 SDK 等按阶段引入的方案；PDF 默认采用 pypdf，PyMuPDF 与 Biopython 列为备选。具体 LLM 供应商与模型 revision 留待有对应输入和验收的任务确定。

实际验证：Phase 0 / Phase 1 / ML 的 Windows 与 Linux 解析共 6 项成功，另增 CPU 变体 2 项成功。直接版本约束和传递哈希输出保存在 research/dependencies/；内联静态检查通过。未安装候选包或 Python 3.12，未运行 pytest，未修改共享 Conda 环境，也未验证真实外部服务；无产品实现及 RED/GREEN。

本次文件：新增 tech-stack.md、research/p0-03-validation.md、research/pypi-metadata-2026-10-26.json、research/dependencies/ 下的 3 个输入、8 个解析输出、2 个结果 JSON；新增 .gitignore 排除本地研究缓存；更新本进度文档。

下一任务：P0-04 总体 SPEC 与 Phase 0–9 阶段概要。仍未进入 Phase 1，阶段学习文档和 Phase 0 完整验收尚未开始。

## Phase 0–9 阶段路线

| 阶段 / SPEC | 需求映射与交付目标 | 核心验收证据 | 当前状态 |
| --- | --- | --- | --- |
| [Phase 0](specs/00-project-overview.md) | 调研、SPEC、架构、测试框架、锁文件及最小离线骨架 | 真实 RED/GREEN、干净环境安装、CLI Demo、代码检查及学习文档 | 完成：P0-01–08；范围/局限见独立验收报告 |
| [Phase 1](specs/01-mvp.md) | G-01–04：离线入库、本地 RAG、可追溯证据及官方飞书接入 | 单文档原子幂等、真实 pgvector/Redis、引用门禁、模型和长连接收发 | 进行中；P1-01–15完成离线入库/检索/基础RAG结构工作流、CLI、API、飞书纯事件过滤、Redis原子去重、有界分派及渲染/受限发送；飞书运行时与阶段完整真实验收未完成 |
| [Phase 2](specs/02-async-experience.md) | G-05：快速受理、任务状态、后台执行与超时 | Fake clock 终态测试、真实任务存储、满载/重启/通知故障 | 未开始 |
| [Phase 3](specs/03-pico.md) | G-06：分类、部分 PICO、可解释查询计划 | 中英标注 fixtures、缺失/否定/来源区间、模型评估与回归 | 未开始 |
| [Phase 4](specs/04-pubmed-search.md) | G-07：官方在线检索、元数据、分页与限流 | MockTransport fixtures、失败与零结果区分、少量真实接口冒烟 | 未开始 |
| [Phase 5](specs/05-hybrid-retrieval.md) | G-08：全文关键词及向量融合检索 | 手算融合、真实双通道、过滤一致、冻结检索对比集 | 未开始 |
| [Phase 6](specs/06-evidence-analysis.md) | G-09：研究设计、局限、可比较性及潜在冲突 | 判断回指、摘要范围限制、固定标注及人工复核 | 未开始 |
| [Phase 7](specs/07-citation-report.md) | G-03/G-10：完整引用核验及结构化报告 | 身份/定位/论断分别核验、注入错误全部检出、官方元数据核验 | 未开始 |
| [Phase 8](specs/08-knowledge-update.md) | G-11：增量游标、版本更新、跨来源冲突及幂等 | 重放/并发/中断、旧证据可追溯、原子发布与小型回归触发 | 未开始 |
| [Phase 9](specs/09-evaluation.md) | G-12：检索/回答/引用/性能评价与回归门禁 | 指标手算、冻结集及门槛、失败样本计数、固定环境性能结果 | 未开始 |

依赖严格按 Phase 0 → 1 → … → 9 验收推进；阶段内每次一个任务。测试和引用正确性从初次实现起保障，Phase 7/8/9 是深化，不是推迟基础质量。

## 各阶段共同进入条件与完成定义

进入条件：上一阶段验收记录和学习文档齐备；阅读已有 SPEC/代码/测试；为当前任务明确 ID、文件变更、输入输出、边界及失败测试。未来概要里的阈值、默认值和命令路径须在其实现任务开始前冻结；有影响该任务的待决项不能靠实现时猜测跳过。

完成条件：目标功能的 RED 是因未实现而失败，GREEN 后保留测试并做必要回归；外部替身与真实服务记录分开；实际命令、结果及未验证项完整；配置/迁移/版本锁定可复现；无密钥入库。基础安全及医学来源约束失败不能用平均分抵消。

每个阶段必须有 `docs/learning/phase-XX/` 的 README.md、tutorial.md、code-walkthrough.md、exercises.md、interview.md、troubleshooting.md。按“是什么 → 为什么 → 原理 → Demo → 真实代码 → 流程 → 调试测试 → 练习 → 面试表达”解释，并包括实际流程图与取舍。没有代码时不提前编造教程，缺学习文档不标阶段完成。

## Phase 0 后续最小任务路线

以下为工作拆分；[Phase 0 详细任务 SPEC](specs/tasks/phase0-implementation.md) 和 [测试策略](testing-strategy.md) 已定义输入输出、未来测试文件与执行命令，P0-07 再逐个实现。路径与命令的存在于文档中不等于代码/测试文件已创建或已执行。

| 顺序 | 工作范围 | 关联验收 |
| --- | --- | --- |
| P0-05 | 推荐目录、模块边界、资源生命周期、数据流和必要设计取舍 | architecture.md；不创建未来空模块 |
| P0-06 | 测试策略、Phase 0 最小任务 SPEC、Fake 与真实服务边界 | testing-strategy.md；P0-T01–07 映射真实计划 |
| P0-07a | 独立解释器、最小包声明、正式锁文件及可导入骨架 | 已完成：P0-T01 包导入、P0-T06 本次安装/同步；全新重建/wheel 仍留 P0-07e |
| P0-07b | 显式配置、环境覆盖及非法输入校验 | 已完成：P0-T02 真实 RED/GREEN，全量回归 19 passed |
| P0-07c | 最小结构化日志、关联字段与密钥脱敏 | 已完成：P0-T03 真实 RED/GREEN，全量回归 23 passed；采用允许字段筛选 |
| P0-07d | 无服务依赖的 CLI 帮助/本地自检与装配 | 已完成：P0-T04、P0-T05 分别取得真实 RED/GREEN，全量回归 59 passed |
| P0-07e | 骨架回归、格式/lint/类型检查、复现说明 | 已完成：P0-T01–07 综合验证；新开发环境与 wheel 运行隔离，正式锁/源码/测试未改 |
| P0-08 | 基于真实代码的学习材料、Demo 与 Phase 0 验收 | 已完成：P0-A01–06 与 P0-T01–07 均有证据，仍无 Phase 1 业务 |

Phase 1 的首任务确定为 **P1-01：文献与证据 DTO、来源和定位契约**，对应 P1-T01。需 Phase 0 验收后才细化并执行；不将 PDF、数据库和飞书打包进一个实现任务。

## P0-04 本次执行

执行前已读取用户更新后的 AGENTS.md.txt（含适度工程化原则）、PROJECT.md.txt、开发进度、技术选型和 P0-03 核查记录，并检查文件/Git 状态。当前无已有业务代码、测试或 specs 文档；本次以新总体 SPEC 作为后续基线。

文件范围：新增 specs/00-project-overview.md、01-mvp.md、02-async-experience.md、03-pico.md、04-pubmed-search.md、05-hybrid-retrieval.md、06-evidence-analysis.md、07-citation-report.md、08-knowledge-update.md、09-evaluation.md；更新本计划。不新增 Python 实现、测试模块、依赖、容器或调度。

核查场景：10 个文件齐全；各有 11 个必要章节；G-01–12 映射完整；共享字段、引用范围、阶段依赖和未来 DoD 一致；链接可达本地文件、Markdown 围栏闭合、无尾随空白。当前任务是 SPEC 文档验收，不运行 pytest、不声称 RED/GREEN 或功能通过。

实际验证命令与结果：

- 指定 Conda Python 执行 `python -c <内联只读文档核查>`：检查十个约定文件名，每份 11 个有序标题、至少 5 个独立测试 ID、未实现状态、上一阶段依赖；检查 G-01–12 和必需来源字段；遍历 docs/ 检查相对链接与代码围栏，并确认 src/、tests/ 尚不存在。退出码 0，结果为 **10 份 SPEC / 110 章节 / 63 个计划测试场景**，全部结构检查通过。该检查不验证自然语言需求是否充分，契约与范围另经阅读核查。
- 对十份 SPEC 和本文件逐个执行 `git -c core.autocrlf=false diff --no-index --check -- /dev/null <文件>`，结果 `Whitespace diagnostics: 0 / 11 files`。
- `git status --short` 显示原项目说明及 docs/ 等尚未跟踪；未创建提交，未修改用户规则和原调研事实。

语义核查覆盖：Phase 1 基础引用约束与 Phase 7 完整语义/身份核验区分；正常空召回与生成错误区分；Phase 1 幂等与 Phase 8 版本更新区分；SDK 协议确认与 Phase 2 用户受理区分；超时不等于杀线程；研究成功与通知结果分开；Phase 8 小型回归不依赖 Phase 9 尚未实现的评价引擎。

P0-04 文档验收完成，未运行 pytest、未安装依赖、无业务实现或真实服务验证。未来阶段的性能/评价阈值等已列为实施前冻结项，不能把概要当作立即编码的详细任务 SPEC。architecture.md、testing-strategy.md、正式锁文件、最小工程骨架与学习文档仍待后续任务；Phase 0 未完成。

下一任务：**P0-05 架构设计**，设计推荐目录、模块边界、资源生命周期及核心数据流；本次不自动开始。

## P0-05 本次执行

依据：已复查 AGENTS.md.txt、PROJECT.md.txt、SPEC 00–09、技术选型、开发计划及目录状态。执行范围为架构设计，不进入测试策略或实现任务。

文件变更：新增 architecture.md，更新本计划；另补齐 specs/00-project-overview.md 中 IngestionResult 的 needs_update 枚举，与既有 SPEC 01 的“同身份内容变化不覆盖”一致，不提前实现 Phase 8。

设计内容：Phase 0 最小 src 布局与 Phase 1 目标目录分开；核心包 clinical_agent 和 src/feishu 的打包边界明确；少量外部能力契约与显式 bootstrap 装配；DTO/ORM 分离；入库/问答/飞书数据流；来源与位置贯穿；五个飞书模块及有界研究/发送；事务、会话、图状态、模型及客户端生命周期；后续阶段扩展位置与待决事项。

核查场景 A-01–09 定义在架构文档：目录范围、依赖方向、来源链、原子入库、问答错误、飞书容量/租约、资源关闭、总体需求映射、文档结构。当前只有设计表与图，不能冒称实际 import 图或并发行为已验证。

实际验证命令与结果：

- 指定解释器 `C:\Users\11091\.conda\envs\medical-agent\python.exe -c <内联只读文档核查>`：确认 13 个有序章节、A-01–09 九个设计检查、G-01–12 映射、五个飞书职责模块、五个 Mermaid 源码块；从第一张设计依赖图提取 16 条箭头并检查有向无环；检查全部 16 份 Markdown 的本地链接与围栏；确认 needs_update 枚举一致，以及 src/、tests/、Docker 配置、正式项目声明/锁文件均未创建。退出码 0，全部静态断言通过。设计图无环不代表实际 import 图测试通过。
- 对 architecture.md、development-plan.md、specs/00-project-overview.md 分别执行 `git -c core.autocrlf=false diff --no-index --check -- /dev/null <文件>`：输出 `Whitespace diagnostics: 0 / 3 files`。
- 阅读核查 A-01–08：应用依赖方向、显式装配、DTO/ORM 映射、来源与位置、事务/并发去重、空证据/错误区别、研究/发送容量、发送前 owner/期限复查及资源关闭职责与 SPEC 对齐；实际参数及外部 SDK 能力仍待所属实现任务验证。
- `git status --short` 显示项目规则及 docs/ 等仍未跟踪；未创建提交，也未修改项目规则、候选依赖或共享环境。

P0-05 架构设计验收完成。未运行 pytest，无实现及 RED/GREEN，没有实际 import/数据库/并发/SDK 测试；Mermaid 仅核查源码结构，未运行渲染器，不声称渲染已通过。Phase 0 尚未完成，后续实现必须用相应 SPEC 与实际测试证明设计有效。

下一任务：**P0-06 详细任务 SPEC 与测试策略**，把 P0-T01–07 落到最小任务、测试文件、RED 命令及验收步骤；本次不自动开始。

## P0-06 本次执行

执行前复查项目规则、总体 SPEC、架构及进度；当前仍无 src/、tests/、pyproject.toml 或正式锁文件。本次只新增 testing-strategy.md、specs/tasks/phase0-implementation.md，并更新本计划。

已细化 P0-07a–e 的文件范围、最小行为及顺序：先隔离环境与无副作用安装包，再配置、日志、runtime/CLI，最后综合验证。固定两个当前有用的配置字段、stderr JSON 日志及允许字段、CLI help/doctor 与 0/1/2 退出码、本地检查 DTO、注入与上下文协议。P0-T01–07 映射到五份计划测试文件及环境/质量验证。

RED 约定先解决解释器/pytest 前提，再在同一 .venv 中测试目标能力缺失；不以不存在测试路径/依赖安装失败当 RED。P0-07d 在写 bootstrap/CLI 前分别观察目标 RED；P0-07e 无新增功能不造假 RED，发现真实缺陷再补重现测试。Fake、真实集成、外部、性能和人工复核分开；Phase 0 无需真实外部服务。

补充核查了 setuptools 83.0.0 的官方 PyPI 版本/发布日期/Python 要求和官方 pyproject 配置文档，作为后续构建后端精确候选；没有安装或构建。还核查 uv 的隔离工具/partial sync、pytest src/importlib 实践及 structlog 标准日志集成文档，来源链接在新文档中；网页说明不替代本项目运行验证。

本次核查场景：详细 SPEC 11 项结构、P0-T01–07 映射、五个顺序任务/五个测试文件、13 个计划测试函数名称、核心配置与 CLI 契约、RED/GREEN/回归和干净环境/wheel 步骤；文档本地链接、片段锚点、围栏和空白检查；确认没有提前创建产品文件。

实际验证命令与结果：

- 指定 Conda 解释器执行 `python -c <内联只读文档核查>`，退出码 0：详细 SPEC 11 章节、策略 10 章节、P0-T01–07 全映射、P0-07a–e 五个任务，13 个计划测试函数分布在 5 个未来文件；全部 18 份 Markdown 的 58 个本地链接、1 个片段锚点和代码围栏通过；确认未创建 src/、tests/、pyproject.toml、uv.lock、.python-version、.env.example、README 或 Docker 文件。
- 用 PowerShell `System.Management.Automation.Language.Parser.ParseInput` 解析新文档的 4 段 PowerShell 代码块，语法错误 0；只解析未执行，不证明工具环境或命令运行成功。
- 本机引导环境执行 `python -m uv export --help` / `sync --help`，确认该本机 0.13.1 版本列出 --no-dev、--output-file、--no-emit-project、--locked、--no-install-project 选项；目标 0.13.5 仍须 P0-07a 隔离执行验证，未安装。
- 对三份本次文档执行 `git -c core.autocrlf=false diff --no-index --check -- /dev/null <文件>`，输出 `Whitespace diagnostics: 0 / 3 files`。
- 阅读核查环境准备与目标 RED 区分、未实现模块的收集方式、stdout/stderr、安全错误、成功结果在上下文退出后发布、pytest 环境注入启动前清理、Fake/真实验证及阶段范围一致性。静态检查不能替代后续行为测试。

P0-06 文档验收完成。未运行 pytest、未安装依赖、无实现或 RED/GREEN，未改变共享环境、现有依赖清单或项目规则；Phase 0 尚未完成。下一任务为 **P0-07a：隔离环境、最小包与正式锁文件**，本次不自动开始。

## P0-07a 本次执行

任务范围：隔离工具/解释器/.venv、正式依赖声明与锁文件、可安装最小包以及导入安全测试。实施前重读项目规则、详细任务 SPEC、测试策略和进度，确认无既有 src/、tests/、.venv。本次没有创建 config、日志、CLI、API、飞书或业务代码。

### 环境事实与显式修订

1. 原引导解释器 `C:\Users\11091\.conda\envs\medical-agent\python.exe` 的 uv 仍为 0.13.1；通过 `python -m uv tool run --from uv==0.13.5 uv ...` 使用隔离 uv 0.13.5，未向共享 Conda 安装包。
2. 首次沙箱工具执行因默认用户 tools 目录不可写而失败；获联网执行批准后，设置 UV_CACHE_DIR=.research-cache/uv、UV_TOOL_DIR=.tools/uv-tools、UV_PYTHON_INSTALL_DIR=.tools/python。此为环境准备，不算 RED。
3. `uv python install 3.12.16` 退出 1：No download found。通过官方 GitHub 发行 API 核实 standalone latest=20261021，Windows x64 3.12 构建为 3.12.15；向用户明确说明并将详细 SPEC 0.2/.python-version 修订到 3.12.15。原兼容范围 >=3.12,<3.13 不变；3.12.16 安全修订仍待可用构建升级，当前不做外部业务或部署验收。[官方发行](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021)。
4. 3.12.15 下载时官方 releases.astral.sh 镜像失败，uv 自动回退 GitHub 官方资产后成功。首次安装默认创建了用户级 python3.12.exe；随后在已核实的项目解释器根目录下用 uv uninstall 撤销本次安装，再以 `python install 3.12.15 --no-bin --no-registry` 重装；用户入口 Test-Path 为 False。未修改用户 PATH。
5. 解释器实际为 `.tools/python/cpython-3.12.15-windows-x86_64-none/python.exe`，项目虚拟环境为 `.venv/`。`uv lock` 解析 25 个包（含根包）；`uv sync --locked --group dev --no-install-project` 安装 24 个依赖，pytest 9.1.1 可用，根包尚未安装；仅创建空 src/，未提前写 __init__.py。

### 实际 RED → GREEN → 回归

目标：P0-T01 / `tests/unit/test_package.py::test_package_import_is_isolated_and_quiet[clinical_agent]`。测试在临时 cwd 的隔离子进程中安装资源失败哨兵，再 import 目标；检查导入来源、输出、网络/线程尝试、重库导入及日志 handler。没有共用 fixture 需求，因此未创建 conftest.py。

执行 pytest 前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束后恢复。首次收集输出的 shell 因 .artifacts/ 父目录尚不存在报 out-file 错误，此次不计 RED；创建测试产物目录后重新执行。

| 步骤 | 实际命令 | 结果 |
| --- | --- | --- |
| RED（2026-10-26 21:09:04 +08:00） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit/test_package.py -q --basetemp=.artifacts/pytest-p0-07a` | 退出 1，1 failed / 0.43s；测试成功收集，子进程 error=ModuleNotFoundError、name=clinical_agent，确认目标缺失 |
| 最小实现 | 创建 src/clinical_agent/__init__.py，仅含包说明 docstring；`uv sync --locked --group dev` 安装根包 | 构建成功，clinical-literature-agent 0.1.0 已安装；没有额外行为 |
| GREEN（2026-10-26 21:11:19 +08:00） | 与 RED 相同目标命令 | 退出 0，1 passed / 0.24s；未弱化测试 |
| 重构 | 无必要重构，保留最小实现 | 不人为改坏已有行为造红灯 |
| 回归 | `& '.venv/Scripts/python.exe' -I -m pytest tests -q --basetemp=.artifacts/pytest-p0-07a-regression` | 退出 0，1 passed / 0.24s；当前仅这一个测试，无 skipped/xfail |

本机原始输出存放忽略目录 .artifacts/p0-07a-red.txt、p0-07a-green.txt、p0-07a-regression.txt。没有数据库/SDK/医学业务集成测试，不能把这一个导入测试扩大成其他能力通过。

### 环境与质量验证

以下 uv 命令由项目 `.venv/Scripts/python.exe -m uv` 执行，版本 0.13.5；环境变量指向项目内工具和 Python/cache 目录。

| 命令/检查 | 实际结果 |
| --- | --- |
| `uv lock --check --offline` | 通过，Resolved 25 packages |
| `uv pip check --python .venv/Scripts/python.exe` | Checked 25 packages，All installed packages are compatible |
| `uv sync --locked --group dev --offline` | 通过，现有环境一致；锁文件 SHA256 同步前后相同 |
| 项目 Python `-I -c` 导入包并读 importlib.metadata | Python 3.12.15，sys.prefix 为项目 .venv，包路径为项目 src/clinical_agent/__init__.py，发行版本 0.1.0，uv 0.13.5 |
| 真实运行依赖 import smoke | pydantic 2.14.1、pydantic-settings 2.16.1、structlog 26.1.0 均可导入；没有构造应用配置或连接外部服务 |
| `python -m ruff check src tests` | All checks passed |
| `python -m ruff format --check src tests` | 2 files already formatted |
| `python -m mypy src` | Success: no issues found in 1 source file |
| `git check-ignore .venv .tools .artifacts .research-cache` | 四类本地产物均已排除；没有把临时环境作为源码交付 |

交付静态核查：项目 Python 使用 tomllib 检查正式声明/锁文件、解释器/base_prefix/.venv 隔离、3 个运行依赖与 6 个开发依赖、25 个锁定包及锁哈希；确认 src 仅有 __init__.py、tests 仅有包测试且未注册 CLI。19 份 Markdown 的 65 个本地链接/锚点、围栏及原始 RED/GREEN 日志存在性检查通过；12 个本次文件的 `git -c core.autocrlf=false diff --no-index --check` 输出 `Whitespace diagnostics: 0 / 12 files`。这些是交付材料核查，不额外计作产品测试。

正式 uv.lock SHA256：`0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8`。setuptools 83.0.0 是 build-system 精确依赖，隔离构建时取得，不混作运行依赖；历史 research 清单保留为调研证据，不作为正式锁文件。

文件变更：新增 pyproject.toml、uv.lock、.python-version、README.md、src/clinical_agent/__init__.py、tests/unit/test_package.py；扩展 .gitignore；更新详细 SPEC/技术选型中的实际 Python 构建差异、架构和测试策略的当前状态，以及本计划。没有创建 .env 或提交密钥，没有创建 Git 提交。

P0-07a 验收完成：目标真实 RED/GREEN、现有回归、当前安装/锁检查与基础质量检查通过。P0-T06 的完整干净重建/wheel 验证仍属 P0-07e；Linux 运行、配置、日志、CLI、所有真实业务服务及模型均未验证，P0-08 学习材料尚未生成，Phase 0 未完成。

下一任务：**P0-07b：显式配置与验证**，按已细化的两字段契约先写失败测试；本次不自动开始。

## P0-07b 本次执行

范围依据：重读项目规则、详细任务 SPEC、测试策略、现有包/测试/依赖声明及进度；使用既有 Python 3.12.15 / .venv 和已安装 pydantic-settings 2.16.1，不新增依赖。实现前通过本地已安装库源码核实 SettingsConfigDict 的 env_prefix/case_sensitive/env_file 与 hide_input_in_errors 配置能力。

### 场景与最小实现

- tests/unit/test_config.py 的四个计划测试函数参数化为 17 个用例：默认无凭据、全部合法环境/级别与不同大小写变量名、重新读取环境且不修改旧实例、非法枚举/空值/数字字符串/秘密哨兵、当前或父目录 .env 不隐式读取。
- 所有配置用例在临时 cwd 运行，按项目前缀清理环境并通过 monkeypatch 恢复，不读写真实 .env。测试函数体内才 import 目标，确保目标缺失时测试仍能收集。
- src/clinical_agent/config.py 仅提供 Settings 和 load_settings：两项 Literal 字段、环境变量前缀、明确 env_file=None、隐藏异常输入；不创建全局实例/缓存，不加未来服务配置。
- tests/unit/test_package.py 增加 clinical_agent.config 导入参数；在独立子进程给公共 BaseSettings 构造函数设失败哨兵，连同网络/线程/重库/日志检查，验证导入不实例化配置。
- 新增 .env.example，仅含 development/INFO 示例及“不自动读取”的说明。无日志、CLI、SDK 或其他业务实现。

### 真实 TDD 记录

执行前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，命令结束后恢复；原始输出在忽略目录 .artifacts/。时间按 Asia/Shanghai 表示。

| 步骤 | 实际命令 | 结果 |
| --- | --- | --- |
| RED（2026-10-26 21:25:21 +08:00） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit/test_config.py -q --tb=short --basetemp=.artifacts/pytest-p0-07b` | 退出 1，17 failed / 0.40s；全部已收集，原因均为缺失 clinical_agent.config |
| 最小实现 | 添加 config.py 和 .env.example | 成熟 Settings 机制完成读取和验证，没有自写环境解析器 |
| 首次 GREEN 尝试（21:26:09） | 同一目标命令 | 未通过：16 passed、1 failed / 0.54s。测试把 info 在正常帮助文本 information 中的子串误判成泄漏，非输入确实被输出 |
| 断言纠错 | 只调整泄漏检测为完整 token 匹配，补充 input_type 不可出现断言 | 保留全部非法值及秘密哨兵用例，未删除测试、放宽配置值或修改产品绕过；错误尝试日志另存 p0-07b-first-green-attempt.txt |
| GREEN（21:27:39） | 与 RED 相同目标命令 | 退出 0，17 passed / 0.68s |
| 回归 | `& '.venv/Scripts/python.exe' -I -m pytest tests -q --tb=short --basetemp=.artifacts/pytest-p0-07b-regression` | 退出 0，19 passed / 2.70s（17 个配置场景 + 2 个隔离导入场景）；无 skipped/xfail |

重构：最小配置实现已足够简洁，没有必要增加 helper/抽象或重构业务。上述断言纠错单列为测试假阳性修正，没有将首次尝试伪称 GREEN。

### 质量与环境验证

| 实际命令/检查 | 结果 |
| --- | --- |
| `python -m ruff check src tests` | All checks passed |
| `python -m ruff format --check src tests` | 4 files already formatted |
| `python -m mypy src` | Success: no issues found in 2 source files |
| `python -m uv lock --check --offline` | Resolved 25 packages，退出 0 |
| Get-FileHash uv.lock | SHA256 仍为 0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8 |
| 显式 test/DEBUG 环境下 `python -I -c` 调用 load_settings().model_dump_json() | 实际返回 {"app_env":"test","log_level":"DEBUG"}；结束恢复原环境 |
| `git check-ignore --no-index .env` / `.env.example` | 本地 .env 被忽略，示例可跟踪；未创建真实 .env |

交付材料静态核查通过：正式锁哈希未变；src 仅最小包/config，tests/unit 仅包/配置测试，无 CLI 或真实 .env；示例仅两项非秘密默认值。RED、中间失败尝试、GREEN 与回归四份原始日志均保留；19 份 Markdown 的 65 个本地链接/锚点与围栏通过，9 个本次文件空白诊断为 0。这些不另计作行为测试。

文件变更：新增 config.py、test_config.py、.env.example；扩展 test_package.py；更新 README、详细 SPEC、架构/测试策略当前状态及本计划。pyproject.toml、uv.lock、解释器、共享 Conda 和项目规则未修改，未创建 Git 提交。

P0-07b 验收完成：目标 RED/GREEN、当前全量回归和质量检查通过。错误文本隐藏输入的保证不等于任意错误结构都已脱敏；将来 CLI 使用固定安全错误，结构化错误需 include_input=False。当前没有日志/CLI、数据库/Redis、模型、LLM、飞书或 PubMed 验证，Phase 0 未完成。

下一任务：**P0-07c：结构化日志与敏感字段控制**，仍先写失败测试，本次不自动开始。

## P0-07c 本次执行

范围依据：重读项目规则、现有 SPEC、架构、配置与测试；继续使用既有隔离环境和 structlog 26.1.0，不新增依赖。实现前核对已安装库的 ProcessorFormatter/处理器源码及 [官方标准日志集成文档](https://www.structlog.org/en/stable/standard-library.html)，细化详细 SPEC 5.3 的字符串上下文、禁止原始异常/堆栈、生成时间/级别与项目 handler 所有权契约。

### 场景与文件范围

- 新增 tests/unit/test_logging_config.py，三个测试函数在独立子进程使用真实 structlog 与标准 logging：JSON 字段/UTC/stderr；级别过滤/重复配置/已有 logger 更新/第三方资源保留；秘密哨兵、嵌套 payload、异常堆栈、禁止序列化对象及标准日志位置参数。
- 测试只继承必要 OS 环境，使用临时 cwd。handler 生命周期通过公共 close 方法的计数替身检查，不读取私有关闭属性；该调整发生在实现前，未删除或弱化用例。
- 新增 src/clinical_agent/logging_config.py：显式 configure_logging、成熟 ProcessorFormatter/JSONRenderer、短小允许字段筛选；仅替换自有命名 handler，不向 root 传播。
- 扩展 test_package.py 为三模块隔离导入检查，并阻止导入时调用 structlog.configure；更新 README、详细任务 SPEC、架构、测试策略和本进度。未添加 CLI、runtime 或医学业务。

### 真实 TDD 记录

执行 pytest 前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束恢复。原始输出保存在本机忽略目录 .artifacts/p0-07c-red.txt、p0-07c-green.txt、p0-07c-regression.txt。时间为 Asia/Shanghai。

| 步骤 | 实际命令 | 结果 |
| --- | --- | --- |
| RED（2026-10-26 21:40:21 +08:00） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit/test_logging_config.py -q --tb=short --basetemp=.artifacts/pytest-p0-07c` | 退出 1，3 failed / 2.53s；成功收集，均因 clinical_agent.logging_config 缺失 |
| 最小实现 | 添加 logging_config.py | 使用既有日志库实现限定字段与输出契约，没有自建日志框架 |
| GREEN（21:42:18） | 与 RED 相同目标命令 | 退出 0，3 passed / 2.64s |
| 首次回归 | `& '.venv/Scripts/python.exe' -I -m pytest tests -q --tb=short --basetemp=.artifacts/pytest-p0-07c-regression` | 退出 0，23 passed / 6.64s |
| 格式整理及加强导入哨兵后回归 | 与首次回归相同命令 | 退出 0，23 passed / 5.31s；17 配置 + 3 日志集成 + 3 隔离导入，无 skipped/xfail |

重构：实现保持最小结构，无需额外抽象。首次格式检查指出一个测试列表的排版问题，执行 `python -m ruff format tests/unit/test_logging_config.py` 后仅调整该列表布局，后续回归通过；未修改产品行为或缩减测试。

### 质量与环境验证

以下 python 均为项目 .venv/Scripts/python.exe；uv 的缓存/解释器目录显式指向项目 .research-cache/uv 和 .tools/python。

| 实际命令/检查 | 结果 |
| --- | --- |
| `python -m ruff check src tests` | All checks passed |
| `python -m ruff format --check src tests` | 6 files already formatted |
| `python -m mypy src` | Success: no issues found in 3 source files |
| `python -m uv lock --check --offline` | Resolved 25 packages，退出 0 |
| `Get-FileHash uv.lock -Algorithm SHA256` | 仍为 0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8 |

pyproject.toml、uv.lock、解释器、共享 Conda 与项目规则均未修改；无真实 .env、凭据、Git 提交或新依赖。日志测试使用真实库与内存 handler，未连接外部服务。

交付静态核查通过：19 份 Markdown 的 65 个本地链接/锚点及围栏闭合；源码/测试各仅三个预期文件，无真实 .env；三份 RED/GREEN/回归原始日志存在，正式锁哈希未变。8 个本次文件执行 `git -c core.autocrlf=false diff --no-index --check`，空白诊断为 0。这些材料检查不另计作产品测试。

P0-07c 验收完成：真实 RED/GREEN、当前全量回归和质量检查通过。允许字段中的字符串必须由应用控制，此方案不识别任意字符串中的秘密；只保证本模块 handler 的输出，不接管外部/用户另加 handler。尚未验证 CLI、干净环境/wheel、Linux 或数据库/模型/飞书/PubMed，Phase 0 仍未完成。

下一任务：**P0-07d：本地 runtime 装配与 CLI**，按既有 SPEC 先写失败测试，本次不自动开始。

## P0-07d 本次执行

执行前已重读 AGENTS.md.txt/PROJECT.md.txt、详细任务 SPEC、架构、测试策略、进度、现有源码/测试与依赖声明。仅进入 P0-07d，不执行干净重建或 wheel 验证，也不添加医学业务。实现前核对 [argparse 官方文档](https://docs.python.org/3.12/library/argparse.html)、[contextlib 官方文档](https://docs.python.org/3.12/library/contextlib.html) 及 [PyPA 脚本声明文档](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#creating-executable-scripts)；使用标准库与现有 Pydantic，无新增依赖。先细化 SPEC 5.4 的成功/失败事件、上下文阶段错误分类与脚本声明。

### 场景、实现与文件范围

- 新增 bootstrap.py：Runtime 为 frozen dataclass，仅 settings/request_id；open_runtime 在进入时加载一次配置、显式配置日志，并生成或使用注入 UUID；显式 Settings 不再读环境。当前没有外部资源，不增加虚假 close/清理机制，也不将冻结字段绑定表述为深度冻结配置。
- 新增 cli.py：标准 argparse 先解析 help/命令，doctor 才装配；DoctorReport 为明确 Pydantic 模型，外部服务检查固定 false。支持注入上下文工厂，成功退出上下文后才记录完成事件、发布 stdout JSON。
- 新增 __main__.py，与 pyproject.toml 中 clinical-agent 脚本共同委托同一 main；导入 __main__ 不执行 CLI。通过离线 uv sync 正式重装根包生成可执行入口，不手写 .exe/脚本。
- 新增 tests/unit/test_bootstrap.py（2 个装配场景、7 个生命周期场景）；新增 tests/integration/test_cli.py（24 个场景，含两个真实入口和注入解析路径）。扩展包导入测试到六个模块。更新 README、详细 SPEC、架构、测试策略与本进度。
- 覆盖显式配置优先、默认延迟读取一次、UUID、冻结字段；无参数/help/doctor help 在非法环境仍成功；unknown 命令/参数；INFO/WARNING 日志；stdout/stderr、关联 ID、临时 cwd/.env、无网络/线程；上下文进入/body/退出失败，ValidationError 按发生阶段分类，错误不泄漏假秘密或异常原文。

### 分步真实 TDD 记录

pytest 启动前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束后恢复。以下均使用 .venv/Scripts/python.exe、隔离导入 -I，时间为 Asia/Shanghai；日志存放本机忽略目录 .artifacts/。

| 步骤 | 实际命令 | 结果 |
| --- | --- | --- |
| runtime RED（2026-10-26 21:56:50 +08:00） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit/test_bootstrap.py -q --tb=short --basetemp=.artifacts/pytest-p0-07d-runtime` | 退出 1，2 failed / 0.18s；成功收集，缺失 bootstrap；日志 p0-07d-runtime-red.txt |
| runtime 最小实现 | 添加 bootstrap.py | 配置/日志复用现有接口，没有 CLI 或外部服务 |
| runtime GREEN（21:57:06） | 与 runtime RED 相同命令 | 退出 0，2 passed / 0.37s；日志 p0-07d-runtime-green.txt |
| CLI RED（21:58:08） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit/test_bootstrap.py tests/integration/test_cli.py -q --tb=short --basetemp=.artifacts/pytest-p0-07d-cli` | 退出 1，31 failed、2 passed / 2.25s；缺 cli/__main__/已安装 console 入口，runtime 原用例仍通过；日志 p0-07d-cli-red.txt |
| CLI 最小实现与安装 | 添加 cli.py/__main__.py 和 project.scripts；`python -m uv sync --locked --group dev --offline` | 本地缓存离线构建/重装根包成功，25 包解析；无依赖版本变动、无锁文件同步改动 |
| CLI GREEN（21:59:28） | 与 CLI RED 相同命令 | 退出 0，33 passed / 17.55s；日志 p0-07d-cli-green.txt |
| 整理与加强边界 | Ruff 整理 4 个文件的布局/导入；扩展六模块导入哨兵和错误日志字段/无秘密断言 | 没有删除/弱化原用例或添加跳过，产品实现无需额外抽象 |
| 全量回归（22:00:22） | `& '.venv/Scripts/python.exe' -I -m pytest tests/unit tests/integration -q --tb=short --basetemp=.artifacts/pytest-p0-07d-regression` | 退出 0，59 passed / 19.85s；35 单元 + 24 CLI 集成，无 skipped/xfail；日志 p0-07d-regression.txt |

runtime 第一轮测试文件当时只有 2 个装配用例，之后在同一文件加入 CLI 生命周期用例；不能把现有 9 个参数化用例误报为第一轮已验证。命令相同、文件逐步扩展的过程在上表分开记录。

### 质量、安装与实际 Demo

首次质量检查发现 2 处行长及 1 处导入顺序问题，格式检查指出 3 个文件需整理；mypy 已通过。之后执行 `python -m ruff format`（包括随后扩展的导入测试，共 4 文件），再运行下列检查及全量回归，全部通过。格式检查失败不计作功能 RED。

| 实际命令/检查 | 结果 |
| --- | --- |
| `python -m ruff check src tests` | All checks passed |
| `python -m ruff format --check src tests` | 11 files already formatted |
| `python -m mypy src` | Success: no issues found in 6 source files |
| `python -m uv lock --check --offline` | Resolved 25 packages，退出 0 |
| `python -m uv pip check --python .venv/Scripts/python.exe` | Checked 25 packages，All installed packages are compatible |
| uv.lock SHA256 | 仍为 0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8 |
| `python -I -m clinical_agent --help` | 实际显示 doctor 帮助，退出 0 |
| test/INFO 下 `python -I -m clinical_agent doctor` 与 `.venv/Scripts/clinical-agent.exe doctor` | 两入口退出 0，各输出本地 JSON 与关联日志；python_version=3.12.15，external_services_checked=false，UUID 每次不同 |

上述 uv 命令使用项目内 .research-cache/uv 与 .tools/python；Demo 临时设置 test/INFO 后恢复原环境。真实服务、网络数据库、SDK 或模型没有被冒充为已验证。Fake 上下文的退出测试只证明 CLI 的上下文使用边界。

交付材料核查：19 份 Markdown 的 65 个本地链接/锚点及围栏闭合检查通过；源码严格为六模块、测试为五文件，安装元数据中的 clinical-agent 指向 clinical_agent.cli:main；五份 TDD/回归日志存在，无真实 .env，锁哈希不变。12 个本次文件运行 `git -c core.autocrlf=false diff --no-index --check`，空白诊断为 0；这些静态检查不另计作产品测试。

P0-07d 验收完成：两组独立 RED/GREEN、现有全量回归、质量检查及已安装双入口 Demo 通过。依赖版本/正式锁/共享 Conda/解释器/规则文件未修改，无真实 .env、凭据或 Git 提交。尚未验证全新环境/wheel、Linux 或任何医学业务/真实外部服务；Phase 0 未完成。

下一任务：**P0-07e：骨架回归、干净环境与 wheel 验证**。本次停止，不自动执行；P0-08 学习材料与阶段独立验收仍在其后。

## P0-07e 本次执行

范围：重读项目规则、任务 SPEC 10.1/10.2、架构/测试策略、现有源码/测试和依赖声明；核对本地 uv 0.13.5 的 build/export/venv 命令帮助，再细化 SPEC 的独立目录、哈希安装和覆盖率边界。只执行 P0-T01–07 综合验收，无新产品功能，无缺陷修复；依照 SPEC 不人为制造 RED。本轮结果是回归/环境验证，不冒充新的 RED/GREEN。

### 环境、命令约定与原始证据

本次唯一目录 R 为 `E:/02_Projects/chatgpt_project/clinical_agent/.artifacts/p0-07e-20261026-01`，创建前确认不存在，不复用/删除旧环境；所有路径均在工作区内。以下 `python` 是原 .venv/Scripts/python.exe，`basePython` 是项目 .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe；`reproPython`、`wheelPython` 分别为 R/repro-venv/Scripts/python.exe、R/wheel-venv/Scripts/python.exe。uv 缓存与解释器目录显式指向项目 .research-cache/uv 与 .tools/python，无网络访问、无新依赖或解释器下载。

启动前记录 baseline.json，覆盖 16 个受保护文件（6 个源模块、5 个测试、正式声明/锁/解释器声明和两份项目规则）的 SHA256。UV_PROJECT_ENVIRONMENT 临时指向 R/repro-venv，同步后恢复；pytest 启动前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束恢复。每个测试进程独立设置并恢复 COVERAGE_FILE，使用不同 basetemp/pytest cache/覆盖率产物，避免相互覆盖。

| 实际命令或检查 | 结果 / R 下证据 |
| --- | --- |
| `python -m uv lock --check --offline` | Resolved 25 packages，退出 0；lock-check.txt |
| `python -m uv sync --locked --group dev --offline` | 原环境 Checked 25 packages，无版本变动；original-sync.txt |
| 指定新 UV_PROJECT_ENVIRONMENT 后 `python -m uv sync --locked --group dev --offline --python <basePython> --no-python-downloads` | 新建 repro-venv，Installed 25 packages；repro-sync.txt |
| `python -m uv pip check --python <original/reproPython>` | 两环境各 25 个包一致性通过；original-pip-check.txt、repro-pip-check.txt |
| `python -m uv build --wheel --no-sources --offline --python <basePython> --no-python-downloads --out-dir <R/wheel-build>` | setuptools 隔离构建成功；wheel-build.txt，仅本次明确路径产物 |
| `python -m uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file <R/runtime-requirements.txt> --offline --quiet` | 导出含哈希的 8 个运行依赖，排除根包/开发依赖；runtime-requirements.txt |
| `python -m uv venv <R/wheel-venv> --python <basePython> --no-python-downloads --offline` | 新建独立无系统 site-packages 的环境；wheel-venv-create.txt |
| `python -m uv pip install --python <wheelPython> --require-hashes -r <R/runtime-requirements.txt> --offline` | 哈希约束安装 8 个运行依赖；wheel-runtime-install.txt |
| `python -m uv pip install --python <wheelPython> --no-deps <本次 wheel 的完整路径> --offline` | 仅安装项目 wheel；wheel-project-install.txt |
| `python -m uv pip check --python <wheelPython>` | Checked 9 packages，全部兼容；wheel-pip-check.txt |

同步时 uv 提示主机 VIRTUAL_ENV=.venv 与新项目环境不同并忽略它；后续实际 sys.prefix、包清单和新解释器执行结果确认目标正确，没有因警告转用原环境。构建提示缓存目录在源码根内“可能进入分发物”；实际 zip 清单/源码字节/RECORD 核查确认本次 wheel 不含缓存或环境，不据此扩展为 sdist 已验证。

### 原环境与干净开发环境回归

2026-10-26 22:08:12 +08:00 分别启动两次完整测试。实际参数相同，解释器明确不同，输出/缓存路径各自隔离：

```powershell
& $testPython -I -m pytest tests/unit tests/integration --strict-markers --strict-config --import-mode=importlib --cov=clinical_agent --cov-branch --cov-report=term-missing --cov-report=json:<R/coverage-label.json> --basetemp=<R/pytest-label> -o cache_dir=<R/pytest-cache-label> -q
```

其中 label 为 original/repro，上述尖括号表示记录中替换成对应绝对路径的参数，不是可直接执行的 PowerShell 重定向表达式；README 提供可复制的新目录步骤。

| 环境 | 实际结果 | 原始记录 |
| --- | --- | --- |
| 原 .venv，Python 3.12.15 | 退出 0，59 passed / 23.03s | regression-original.txt、coverage-original.json、.coverage-original |
| 新 repro-venv，Python 3.12.15 | 退出 0，59 passed / 27.17s | regression-repro.txt、coverage-repro.json、.coverage-repro |

每次均为原有 35 单元 + 24 集成场景，无 skipped/xfail，不把重复执行计成 118 个不同测试。两环境 coverage 结果一致：汇总 77.57%（显示 78%），语句 77/95=81.05%，分支 6/12=50%。bootstrap、config、cli 的父进程语句覆盖 100%；logging_config 显示 34%，__main__ 显示 0%，其真实执行主要发生在未开启采集的独立子进程。已有日志/模块入口断言仍通过，不声称覆盖率已包含它们，也不改测试或忽略代码来提高比例。

原环境与 repro-venv 均分别执行 `python -m ruff check src tests`、`python -m ruff format --check src tests`、`python -m mypy src --cache-dir <R/mypy-cache-label>`：All checks passed；11 files already formatted；Success: no issues found in 6 source files。各保存 ruff-label.txt、format-label.txt、mypy-label.txt。没有出现需要修复的行为、格式或类型错误，因此没有新一轮产品 RED/修改/重跑。

### 本次 wheel 与独立安装冒烟

产物绝对路径：`E:/02_Projects/chatgpt_project/clinical_agent/.artifacts/p0-07e-20261026-01/wheel-build/clinical_literature_agent-0.1.0-py3-none-any.whl`。

SHA256：`dea64436482b1700a1be54e38c6129e9da2f8ee7b9d11b44f882d88d55fd4a92`。只标识本次构建，不承诺重复构建字节级一致。

R/verify-wheel.py 是本轮忽略目录中的验证脚本，不是新增应用模块或正式 pytest 用例。实际运行 `python -I <R/verify-wheel.py>`，退出 0；结果保存在 wheel-verification.json/.txt 和逐命令 smoke-commands.json：

- zip 仅 11 个文件：六个源码模块 + 五个 dist-info；逐个源码字节与当前源码相同，RECORD 中内容哈希/大小验证通过，项目名称/版本/运行依赖/脚本声明正确，无缓存、虚拟环境或密钥。
- 原/新开发环境的 25 包名称/版本完全一致，wheel 环境为九包（八运行依赖 + 根包），版本为开发锁中对应版本，无 pytest/uv/Ruff/mypy；没有通过手写启动器或源码路径注入绕过安装。
- 三环境均确认 sys.prefix 指向目标、base_prefix 指向项目受控 Python、系统 site-packages 关闭且 -I 下用户 site 禁用。开发环境模块来自项目 src；wheel 环境六个模块全部来自自身 Lib/site-packages，无 editable 安装/源码 sys.path。
- 所有 CLI 命令从 R/smoke-cwd 执行，子进程仅继承必要系统变量、10 秒超时。原/新开发/wheel 三套环境各执行模块/脚本 doctor，共六次；test/INFO 下成功，stdout 本地报告，stderr 一条完成日志，其 request_id 对应，六份报告除随机 UUID 外稳定字段完全相同。
- wheel 另执行模块/脚本各自的无参数、--help、非法配置 doctor，共六次；非法配置不影响 help，无参数/help 退出 0，坏配置退出 2、固定安全错误、无结果或秘密泄漏。合计 **12 项 CLI 冒烟**，不混作 pytest 新增用例。

### 完整性、变更与验收边界

运行 integrity-verification 后，baseline 中 16 个受保护文件哈希全部未变；正式 uv.lock SHA256 仍为 `0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8`。未修改源码、测试、pyproject.toml、依赖、解释器、共享 Conda 或项目规则，未创建 Git 提交、项目根 .env 或真实凭据。新环境、构建输出、临时验证脚本和日志均在既有忽略规则内（build/ 与 egg-info 也是忽略的生成物）。本次仅修改 README、详细任务 SPEC、架构/测试策略当前状态及本进度。

最终交付静态核查通过：19 份 Markdown、66 个本地链接/锚点及围栏闭合；再次检查 16 个受保护文件哈希、两份完整回归日志和明确 wheel 产物哈希。5 个本次文档执行 `git -c core.autocrlf=false diff --no-index --check`，空白诊断为 0；git check-ignore 确认 R、build 和 egg-info 被排除。这些材料核查不另计作 pytest 或产品功能测试。

P0-07e 验收完成，P0-07a–e 工程任务已完成。证据限于 Windows x64、Python 3.12.15、本地缓存离线的安装/构建/运行；未验证无缓存联网下载、Linux、sdist、真实数据库/Redis/模型/LLM/飞书/PubMed 或性能。Python 安全修订升级问题继续保留原 SPEC 说明，不将 wheel 标签视为其他平台通过。Phase 0 仍未完成。

下一任务：**P0-08：学习文档与 Phase 0 独立验收**；需基于真实代码与 Demo 完成六份学习材料、设计取舍和阶段总结后验收。本次停止，不提前生成学习材料或进入 Phase 1。

## P0-08 本次执行

执行前重读项目规则、总体/详细 SPEC、测试策略、现有六个源模块/五个测试与 P0-07e 证据。目录检查确认学习目录尚不存在，这是本次文档交付缺口，不计功能 RED。先创建 [P0-08 SPEC](specs/tasks/phase0-acceptance.md)，冻结 P0-A01–06，再编写学习资料和验收报告；未新增功能、依赖或正式测试用例，不制造 RED。独立验收指按单独清单重新核验，由本次执行者完成，不虚构其他审阅者。

### 文件与学习内容

新增 docs/learning/phase-00/README.md、tutorial.md、code-walkthrough.md、exercises.md、interview.md、troubleshooting.md；新增 docs/specs/tasks/phase0-acceptance.md 和 docs/phase0-acceptance.md。更新根 README、总体 SPEC、工程任务 SPEC、架构/测试策略当前状态和本进度，共 14 份 Markdown。源码、测试、项目规则、正式依赖和解释器保持不变。

学习顺序由导航映射“是什么 → 为什么 → 原理 → Demo → 真实代码 → 流程 → 调试测试 → 修改练习 → 独立实现 → 面试表达”。教程解释环境/发行包/导入、配置优先级、日志字段、上下文；代码解析逐步说明两入口、参数解析、open_runtime/yield、报告构造/发布与失败阶段，并提供 Mermaid 流程图。练习定义独立副本的 --version 修改作业和 lab-status 独立实现，给出 SPEC/RED/GREEN/回归标准，均未改成产品功能。面试包含 30 秒口述和追问，排错提供解释器/安装/日志/错误阶段的检查路径。

### 本次可执行复验

新建且只使用 `.artifacts/p0-08-20261026-01/`（下称 R）；其中 baseline.json 记录 16 个受保护文件。原始日志、临时示例/验证脚本保存在 R，不覆盖 P0-07e 的产物或历史记录。所有命令使用项目 .venv/Scripts/python.exe；pytest 启动前清理/结束恢复 PYTEST_ADDOPTS/PYTEST_PLUGINS，COVERAGE_FILE 同样保存恢复。uv 缓存/解释器目录仍指向项目内部。

| 检查 | 实际命令与结果 | R 下证据 |
| --- | --- | --- |
| 完整回归（2026-10-26 22:24:57 +08:00 启动） | `python -I -m pytest tests/unit tests/integration --cov=clinical_agent --cov-branch --cov-report=term-missing --cov-report=json:<R/coverage.json> --basetemp=<R/pytest-final> -o cache_dir=<R/pytest-cache> -q`；退出 0，59 passed / 21.77s，无 skip/xfail | regression.txt、coverage.json、.coverage |
| 代码检查 | `python -m ruff check src tests`；All checks passed | ruff.txt |
| 格式检查 | `python -m ruff format --check src tests`；11 files already formatted | format.txt |
| 类型检查 | `python -m mypy src --cache-dir <R/mypy-cache>`；Success: no issues found in 6 source files | mypy.txt |
| 离线锁检查 | `python -m uv lock --check --offline`；Resolved 25 packages，退出 0 | lock-check.txt |
| 安装一致性 | `python -m uv pip check --python .venv/Scripts/python.exe`；Checked 25 packages，全部兼容 | pip-check.txt |
| 教程与产物验证 | `python -I <R/verify-learning.py>`；退出 0，4 Python + 3 PowerShell 围栏全部真实执行通过，12 项 CLI 冒烟通过 | demo-verification.json/.txt、demo-executions.json、抽取的 .py 示例 |

尖括号表示执行时替换成 R 下对应绝对路径；不是可直接运行的 PowerShell 表达式。正式测试仍为 35 单元 + 24 集成，父进程汇总覆盖率 78%（语句 81%、分支 50%）；未采集子进程的边界与 P0-07e 一致，不虚称完整执行覆盖。排错手册中的 1 生命周期节点 + 17 配置场景再次运行是文档验证，不算新增 pytest 用例。

verify-learning.py 在新子进程、最小系统环境下执行四个 Python 示例（临时 cwd、-I/-B、10 秒超时），使用本机 PowerShell -NoProfile/-NonInteractive 执行三个实际文档块。还从 R/cwd 分别调用项目/既有 wheel 的模块和脚本入口：help 配坏环境、test/INFO doctor、坏配置 doctor，共 12 项；全部输出/退出码符合契约，稳定报告字段相等，日志 request_id 对应。wheel 导入来源再次确认为其 Lib/site-packages，未靠源码路径运行。

### 历史证据、人工内容复核与验收决定

检查 P0-07a/b/c 和 P0-07d runtime/CLI 的十份真实 RED/GREEN 输出存在且结果标记对应；P0-07e 原/新开发环境的 59 passed 日志、wheel 内容/安装来源/九包清单及 12 项历史冒烟证据存在。既有 wheel SHA256 仍为 dea64436482b1700a1be54e38c6129e9da2f8ee7b9d11b44f882d88d55fd4a92，源码载荷逐字节与当前 src 相同。本次复验该既有产物，没有重新构建/重建环境的声明。

按源代码逐项审阅六文档：模块/函数确实存在；help 先于读取配置；yield 交接而非虚构资源清理；body/退出 ValidationError 返回 1；成功退出后才输出报告；字段筛选不承诺任意秘密检测；frozen 不等于深度冻结；练习和未来医学能力明确未实施。P0-A01–06 和 P0-T01–07 的逐项证据映射及阶段新知识/取舍见 [验收报告](phase0-acceptance.md)。

16 个受保护文件 SHA256 均未变，正式 uv.lock 仍为 0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8；未更改共享 Conda、解释器、源码/测试/依赖/规则，未创建 Git 提交或项目根真实 .env。未发现需要修改产品行为的缺陷；本次没有新的功能 RED/GREEN。

最终文档验收：27 份 Markdown 的 144 个本地链接/锚点有效、围栏闭合；P0-08 SPEC 的 11 节齐备，六份学习文件/真实流程图/练习验收要求存在，源码仍六模块、测试仍五文件。14 份本次文档执行 `git -c core.autocrlf=false diff --no-index --check`，空白诊断为 0；本次 .artifacts 目录被忽略。静态结果保存在 R/documentation-audit.json，不另计为 pytest 或医学业务测试。

P0-08 与 Phase 0 验收完成，范围限 Windows x64/Python 3.12.15/uv 0.13.5 本地骨架和已记录的缓存离线验证。Linux、无缓存下载、sdist、真实服务、医学效果与性能未验证；Python 安全修订构建升级仍按既有 SPEC 在外部业务/部署前复核，不用 doctor=ok 替代这些能力。

下一任务：**P1-01：文献与证据 DTO、来源和定位契约**，先细化 SPEC，再写 P1-T01 失败测试；本次停止，不提前创建业务模块或实现 Phase 1。

## P1-01 本次执行

范围依据：重读 AGENTS.md.txt、总体/MVP SPEC、架构和现有代码/测试，确认 Phase 0 已验收。先写 P1-01 的 11 节详细 SPEC，冻结来源快照、日期精度、字符区间、摘要范围和跨对象关系，再写目标测试，未同时引入解析、ORM、数据库、RAG 或飞书。

实现前核对 [Pydantic 官方验证器文档](https://docs.pydantic.dev/latest/concepts/validators/)、[类型文档](https://docs.pydantic.dev/latest/api/types/#pydantic.types.AwareDatetime)，并在已安装 2.14.1 中核实 FileUrl/HttpUrl/AwareDatetime/StrictInt/StrictBool 可用。继续使用现有依赖与 Python 3.12.15，没有新增或升级包，不把官方文档的 latest 当成已安装版本；实际兼容性由本轮测试验证。

### 最小设计与文件

- 新增 domain/__init__.py（包说明）和 domain/models.py。六个公开业务 DTO 为 PublicationDate、SourceMetadata、EvidenceLocation、EmbeddingInfo、EvidenceChunk、LiteratureDocument；一个短小 Pydantic 配置基类统一额外字段/错误文本/实例重验规则，没有接口继承树或持久化抽象。
- 日期保留 raw/precision 和未知组件，严格整数/真实日历验证；不自动补日月。来源保留离线 file URI、可空 HTTP(S) URL、快照 hash/范围，不读取文件或请求 URL；拒绝 URL 凭据。
- 证据保留原字符/空白、Unicode 码点右开区间和单页/摘要位置；校验字符数、类型、归属、来源快照一致、重复 chunk ID、摘要切片及声明的 Embedding 身份一致性。不含向量值，不自动生成模型信息。
- 文献要求已有可用文本，摘要范围不允许 text 冒充全文；作者/标识等未知数据明确 []/null。时间来自调用方的带时区 ISO 日期时间/datetime，归一化 UTC，不从 epoch 或当前时间推导。
- tests/unit/test_literature_models.py 使用合成 Unicode/空白文本、虚构 fixture 标识/URI 和假秘密；不访问真实文献。扩展 test_package.py 到 domain/domain.models，八模块继续验证无配置/网络/线程/日志装配副作用。
- 更新 README、总体/MVP/任务 SPEC、架构、测试策略和本进度；在 Phase 0 报告/学习导航注明历史快照，避免旧 wheel 被误用于新增 domain。没有创建 application/adapters、数据库、解析器、claims/答案/引用 DTO 或新 CLI。

### 真实 TDD 与发现的边界缺陷

以下命令均用项目 .venv/Scripts/python.exe；启动前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束恢复。R 为本次新建的 `.artifacts/p1-01-20261026-01/`，没有覆盖旧证据；时间为 Asia/Shanghai。

目标命令：`python -I -m pytest tests/unit/test_literature_models.py -q --tb=short --basetemp=<R/pytest-target>`，尖括号在执行时为对应绝对路径。

| 步骤与实际时间 | 结果 | R 下原始记录 |
| --- | --- | --- |
| 首轮 RED（2026-10-26 22:53:13 +08:00） | 退出 1，93 failed / 1.74s；成功收集，全部缺 clinical_agent.domain | red.txt |
| 最小实现后 GREEN（22:54:27） | 同一目标命令退出 0，93 passed / 0.38s | green.txt |
| 补 epoch 边界 RED（22:55:28） | 新增三个反例，退出 1，3 failed、93 passed / 0.63s；字符串/bytes epoch 被 Pydantic 隐式接受 | epoch-red.txt |
| epoch 最小修复 GREEN（22:56:01） | 标准 datetime.fromisoformat 约束字符串，其他只接受 datetime，再交 AwareDatetime 校验；退出 0，96 passed / 0.41s | epoch-green.txt |
| 补错误回显 RED（22:57:14） | 新增假秘密非法时间用例，退出 1，1 failed、96 passed / 0.67s；fromisoformat 的 ValueError 消息包含原始输入，hide_input_in_errors 本身无法隐藏该消息 | datetime-error-red.txt |
| 固定安全错误 GREEN（22:57:36） | 捕获该解析 ValueError，映射固定原因且不传播原始消息；原用例保留，退出 0，97 passed / 0.39s | datetime-error-green.txt |

上面两个额外 RED 是实际契约缺陷，均在修复前重现，没有删改原断言或将失败改成 skip。日期采用标准库解析/日历规则，非自写解析框架。重构仅对新增测试文件执行 Ruff 排版；首次格式检查提示一个文件需整理，之后通过。没有引入无当前用途的抽象。

### 全量回归与质量

| 实际命令/检查 | 结果 | R 下证据 |
| --- | --- | --- |
| `python -I -m pytest tests/unit tests/integration -q --tb=short --cov=clinical_agent.domain --cov-branch --cov-report=term-missing --cov-report=json:<R/coverage.json> --basetemp=<R/pytest-regression> -o cache_dir=<R/pytest-cache>`（22:58:15 启动） | 退出 0，158 passed / 25.52s；134 单元 + 24 CLI 集成，无 skip/xfail | regression.txt、coverage.json、.coverage |
| `python -m ruff check src tests` | All checks passed | ruff.txt |
| `python -m ruff format --check src tests` | 14 files already formatted | format.txt |
| `python -m mypy src --cache-dir <R/mypy-cache>` | Success: no issues found in 8 source files | mypy.txt |
| `python -m uv lock --check --offline` | Resolved 25 packages，退出 0 | lock-check.txt |
| 年份精度 DTO 的真实构造/JSON 冒烟 | year=2020，month/day=null，未补齐日月 | date-smoke.txt |

本次覆盖率只采集 clinical_agent.domain，显示 99%（142 条语句、50 分支，1 行/1 分支未覆盖）；不与 Phase 0 的全包父进程 78% 混算，不宣称所有路径覆盖。只验证本地真实 Pydantic 集成，没有数据库/模型/SDK 集成；没有为凑比例增加用例。

正式 uv.lock SHA256 保持 0B510F3B2C2E67A4BD3301D308CCD2C90214CC4465346EA970CFDFAC57B9BBF8。包声明、解释器、共享 Conda、规则文件和已有六个源模块未改；已有测试仅增加两个导入参数，不弱化旧断言。没有创建 Git 提交或真实凭据；全部文献样例是合成数据。交付时发现已有本地 .env，元数据确认创建时间早于目标测试，本次未创建/读取内容/修改；git check-ignore 确认已排除，config 的 env_file=None 仍由回归验证。临时材料核查初版把“.env 必须不存在”误作前提而失败，改为检查忽略规则后再核查；这不是功能 RED，也没有修改产品测试或放宽配置契约。

最终交付核查通过：28 份 Markdown、本地链接/锚点与围栏有效；P1-01 SPEC 的 11 节齐全，源码八文件/测试六文件，RED/GREEN/回归/质量证据存在。已有 15 个文件基线中仅 test_package.py 的两个导入参数发生变化，其余已有源码/测试/声明/规则哈希未改。13 个本次文件执行 `git -c core.autocrlf=false diff --no-index --check`，空白诊断为 0；R 被忽略。材料核查不另计作行为测试，详情在 R/delivery-audit.json。

P1-01 验收完成，Phase 1 未完成。DTO 只验证声明结构/内部关系，不证明文献、标识、来源 URL 或医学结论真实；PDF 页数/页内切片真实性、实际 hash/模型维度以及重复入库/并发必须在后续解析/编码/真实数据库任务验证。旧 Phase 0 wheel 不含新增 domain，本次未重建 wheel。Phase 0 的 Python 安全修订构建问题仍需在外部业务/部署前复核。

下一任务：**P1-02：PDF 文本层解析与逐页来源单元**；先细化 SPEC 并核实解析依赖，然后失败测试。本次停止，不提前实现或生成 Phase 1 完成学习材料。

## P1-02 本次执行

执行前重读项目规则、P1-01/MVP/总体 SPEC、架构、选型、现有源码与测试；先建立 11 节 P1-02 SPEC，再准备依赖/写测试。范围只含本地 PDF 文本层解析、逐页单元和证据页内回建，不实现分块、模型、存储、XML 或新 CLI，也不把适配器说成入库服务。

### 组件核实与环境准备

沿用 P0-03 选择的 pypdf，重新核对 [6.21.2 PyPI 页面](https://pypi.org/project/pypdf/6.21.2/)、[官方提取文档](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)、[Reader API](https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html)：Python>=3.9、BSD-3-Clause、2026-10-21 发布，纯 Python wheel；适合当前文本层，OCR/复杂版面不在范围。官方内容提示解析单个内容流可能占较多内存，因此预算明确为协作检查，不冒充硬隔离。

本次 R 为新建 `.artifacts/p1-02-20261026-01/`；先记录 baseline.json（已有 18 文件哈希），不改旧证据。项目内 Python 请求 PyPI JSON 初次被沙箱网络权限拒绝（WinError 10013），官方网页核查成功；随后 `uv add pypdf==6.21.2 --offline` 因缓存无包失败，均为前置问题，不计功能 RED。通过允许的联网执行 `python -m uv add pypdf==6.21.2 --default-index https://pypi.org/simple` 成功下载、构建/重装根包并同步环境，发生一次网络重试后成功；未使用 --frozen 绕过解析，未修改共享 Conda。

pyproject.toml/uv.lock 正式增加且仅增加 pypdf 6.21.2 基础包，运行依赖现在四个，总包数 26；未安装 crypto/image/OCR extras。已安装 Requires-Python 与 PyPI 一致，锁中 wheel SHA256 为 `1d44d1a3a200f25062adff0085b02040e4646431ac2ccac22e42679e91466084`，与官方文件一致。原有 25 包版本保持不变，依赖安装联网与后续离线产品测试分开记录。

### 最小设计与交付文件

- domain/models.py 增加 PdfSourceUnit/ParsedPdf；单页允许空文本但保留页号/规范化版本，聚合文献必须与所有页单元对应；validate_chunk 验证来源/文献/页号/区间/切片。没有用聚合正文重新猜页内偏移。
- 新增 adapters/__init__.py 和 adapters/pdf.py；公开 parse_pdf、PdfParseLimits、PdfMetadataOverrides、单个扁平 PdfParseError。路径必须解析到显式根内普通文件，读取至多 20 MiB+1，原始 bytes 用于哈希及 Reader；reader/文件/BytesIO 均有确定关闭边界。
- 文本按 CRLF/CR→LF、去 NUL 最小规范化，保留其他空白/Unicode；空白页不重排，内容范围固定 extracted_text。标题人工/PDF 元数据/文件名分级并记录 origin；/Author 不猜拆署名，/CreationDate 不充当出版日期，未知 DOI/PMID/期刊/出版日期不补造。
- 默认预算：200 页、单页解码流 10 MiB、总聚合正文 1,000,000 字符（包括页间两个 LF）、协作计时 30 秒，均显式可注入。一次同步解码/提取不可强制中断，长度解码后才能检查，未做硬内存/时间沙箱或并发文件系统攻击隔离。
- 新增 tests/unit/test_pdf_contracts.py（20 场景）、tests/integration/test_pdf.py（24 场景）；真实 PdfWriter/Reader 合成多页、混合空白、图像-only、默认 RC4 加密/空密码、损坏/空文件；局部 monkeypatch 只用于计时、提取故障、规范化、读取权限和快照变化，明确不是现实论文效果验证。合成图像 fixture 为建立间接流使用库的 _add_object，运行时不依赖该私有写 API，也不自写 PDF 解析。
- test_package.py 新增 adapters 两个导入参数，十个模块均不在导入时连服务/读配置/建线程/打开文献。更新 README、总体/MVP/任务 SPEC、架构、技术选型、测试策略和本进度；没有创建学习六文件或提前标 Phase 1 完成。

### 真实 TDD 过程

目标命令为 `python -I -m pytest tests/unit/test_pdf_contracts.py tests/integration/test_pdf.py -q --tb=short --basetemp=<R/pytest-target>`；python 均为项目 .venv/Scripts/python.exe，时间为 Asia/Shanghai。启动前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束恢复。尖括号在实际执行中是 R 下的绝对路径。

| 步骤与实际时间 | 结果 | R 下原始输出 |
| --- | --- | --- |
| RED（2026-10-26 23:20:24 +08:00） | 退出 1，41 failed / 1.22s；成功收集，均缺 PdfSourceUnit/ParsedPdf 或 adapters 目标模块 | red.txt |
| 最小实现 GREEN（23:22:27） | 原命令退出 0，41 passed / 1.01s | first-green-attempt.txt（实际通过） |
| 规范化边界 RED（23:23:35） | 新增两例发现 DTO 可声称 pdf-text-v1 却包含 CR/NUL；退出 1，2 failed、41 passed / 1.13s | canonical-red.txt |
| 规范化 GREEN（23:24:20） | DTO 拒绝未规范化输入，不修改其余字符；原目标命令退出 0，43 passed / 0.96s | canonical-green.txt |
| 聚合预算边界 RED（23:30:58） | 明确预算包含页间分隔符后新增反例，原实现只数单页；退出 1，1 failed、43 passed / 1.25s | separator-red.txt |
| 聚合预算 GREEN（23:31:26） | 每个新增页计入两个 LF；退出 0，44 passed / 0.97s | separator-green.txt |

没有删除/弱化旧用例，没有制造环境失败红灯。源码核对发现 PdfReader 初始化自身会尝试空密码，故将“完全不尝试解密”的描述修正为应用不主动供密码/调用 decrypt、不采用解密内容、已识别加密全部拒绝；测试名称同步澄清，原拒绝断言不变。未支持算法/依赖在初始化失败时映射 pdf_invalid；未声称各种 AES 已实测。

首次质量检查有 16 条布局/行长问题和 2 条 mypy 参数类型问题；通过 Ruff 格式化、明确 title_origin Literal 和 FileUrl 构造修正，不改业务断言。后续格式门禁又发现 domain 中一个条件布局未整理，已格式化。先后两轮 203 passed（50.72s、48.11s）分别保留为 first-regression.txt、formatted-regression.txt；因后续分隔符预算行为修改，重新执行最终完整回归，而不拿旧结果冒充当前实现。

### 最终回归、兼容与冒烟

| 实际命令/检查 | 结果 | R 下证据 |
| --- | --- | --- |
| `python -I -m pytest tests/unit tests/integration -q --tb=short --cov=clinical_agent.adapters.pdf --cov=clinical_agent.domain --cov-branch --cov-report=term-missing --cov-report=json:<R/coverage.json> --basetemp=<R/pytest-regression> -o cache_dir=<R/pytest-cache>`（23:31:55 启动） | 退出 0，204 passed / 49.48s；156 单元 + 48 集成，无 skip/xfail | regression.txt、coverage.json、.coverage |
| `python -m ruff check src tests` | All checks passed | ruff.txt |
| `python -m ruff format --check src tests` | 18 files already formatted | format.txt（旧失败另存 first-format-check.txt） |
| `python -m mypy src --cache-dir <R/mypy-cache>` | Success: no issues found in 10 source files | mypy.txt |
| `python -m uv lock --check --offline` | Resolved 26 packages，退出 0 | lock-check.txt |
| `python -m uv pip check --python .venv/Scripts/python.exe` | Checked 26 packages，全部兼容 | pip-check.txt |
| 真实合成 PDF→parse_pdf→EvidenceChunk→validate_chunk 冒烟 | 三页保持 1/2/3，中间空白，第 3 页 Beta 切片可回建；scope=extracted_text、parser_version=6.21.2 | smoke.txt、smoke-result.json、synthetic-smoke.pdf |

覆盖率本轮只采集 PDF 适配器与 domain，汇总显示 99%（270 语句、90 分支，2 行/1 分支未覆盖），不把它推导为 OCR/中文字体/复杂版面/硬资源隔离/全部路径均通过。既有 CLI/DTO 行为完整回归，测试与 smoke 不联网；Windows Python 3.12.15 下验证成功，Linux 尚未执行。源码示例全部是合成数据，不读取现有 .env 内容，也不使用真实医学文献或密钥。

新增依赖后正式 uv.lock SHA256 为 `74BA09814492A0E4A76E1586BA4BEBD38DAB408228B17BAF2EF9A4350697A41E`；旧 0B510F... 是 Phase 0/P1-01 历史锁，不覆盖或伪改历史证据。共享 Conda、解释器、规则及其余旧模块/测试保持原状，既有本地 .env 不读取/修改且已忽略；没有 Git 提交或 Phase 1 wheel 重建。

收尾基线检查另发现 cli.py 于 23:35:20 出现两处说明注释改动，并非 PDF 实现写入；完整回归已在此之前完成。使用旧 wheel 中与基线 SHA256 完全相同的 cli.py 对照 AST，确认只有注释/排版、程序逻辑等价，保留注释原文后仅 Ruff 排版，再次运行全量 Ruff/格式/mypy 均通过；cli-comment-check.json 保存核对记录。材料核查没有回退并发工作区改动，也不将其说成新 CLI 功能。

最终交付核查通过：29 份 Markdown、169 个本地链接/锚点有效且围栏闭合；P1-02 SPEC 的 11 节齐备，源码十文件、测试八文件。18 文件基线中预期变更为声明/锁、domain.models、两个新增导入参数及上述 AST 等价 CLI 注释；其余旧文件哈希不变。旧环境 25 个包的名称/版本逐项与当前比较，仅增加 pypdf==6.21.2；全部 RED/GREEN/回归/质量/冒烟证据存在。17 个本次/并发排版文件的 `git -c core.autocrlf=false diff --no-index --check` 空白诊断为 0，R 被忽略；详情在 R/delivery-audit.json。这些材料核查不另计产品测试。

P1-02 验收完成，Phase 1 整体未完成。当前只读同一内存快照，未持久化快照/来源单元；需要 OCR 的文件无可用文本时明确拒绝。外部元数据真实核验、现实论文版面/中文字体效果、AES 各算法和进程级资源隔离未验证；未来对外接收不可信文件前须处理硬资源限制及既有 Python 安全修订升级事项。

下一任务：**P1-03：本地 PubMed XML 解析与元数据映射**；先细化 SPEC，再写失败测试。本次停止，不提前开始 XML、分块或入库。

## P1-03 本次执行

执行前重读项目规则、总体/MVP/P1-01–02 SPEC、架构和现有源码/测试；先写 11 节 P1-03 SPEC，冻结本地 XML 字段、分节偏移、逐项拒绝、安全预算和 ID 工厂，再写测试。任务跨越本地午夜，以下时间均为 Asia/Shanghai；R 沿用开始时创建的 `.artifacts/p1-03-20261026-01/`，不改旧任务证据。

### 官方结构与组件核查

读取 [NLM 2026 公告](https://www.nlm.nih.gov/pubs/techbull/jf26/jf26_PubMed_2026_BaselineRelease.html)，确认 2026 沿用 pubmed_250101.dtd。浏览工具对原始 DTD 返回 unsupported content-type；Python urllib 在本机 TLS 验证遇到自签链错误。未关闭证书校验，改用系统证书的 Invoke-WebRequest 成功从 NLM 官方下载 14,430 字节 DTD 到 R/pubmed_250101.dtd；核对 PubmedArticleSet、Article、PubDate、AbstractText、Author、ArticleId 等声明。下载属于结构调研，运行时 XML 不获取此文件。

结合 [Python XML 安全文档](https://docs.python.org/3.12/library/xml.html)、[defusedxml 官方发行](https://pypi.org/project/defusedxml/0.7.1/) 选择 defusedxml 0.7.1 基础包，PSFL、纯 Python、2021-03-08 发布。稳定版较旧，未声称近期维护活跃；与原生 lxml、当前未使用的 Entrez 集成相比，这里只需要标准树 API 和明确实体拦截，不引入多套 XML 框架。PyPI 宽泛 Python 要求不作为兼容证明，当前实际为 Python 3.12.15/Expat 2.8.5。

离线 uv add 因无缓存失败，不计功能 RED；随后执行 `python -m uv add defusedxml==0.7.1 --default-index https://pypi.org/simple` 成功从官方索引安装，精确锁定后共 27 包，未用 --frozen 绕过解析或改共享 Conda。预检命令一次 shell 嵌套引号造成 SyntaxError，改为单引号保护完整脚本后成功验证真实 iterparse 的三个安全参数及正常外部 DOCTYPE 不加载；前者是命令准备错误，不是产品 RED。

### 实现与修改范围

- 新增 adapters/pubmed_xml.py；只从 allowed_root 内普通文件读取一次有界 bytes，文件关闭后用同一内存快照校验 XML、做 hash 和字段映射。安全 parser 显式 forbid_entities/forbid_external，允许正常 DOCTYPE，不全局 monkeypatch，不解析压缩输入或完整 NLM DTD。
- domain/models.py 增加 AbstractSourceUnit、ParsedPubmedArticle、PubmedXmlEntry、PubmedXmlBatch 及固定条目错误码；规范化后摘要节保留标签/类别和全摘要 Unicode 码点右开区间，保证拼接/来源/状态/身份一致，validate_chunk 不允许跨节或错标签引用。
- PMID/标题/摘要必需；个人/团体署名按来源映射，DOI 来自显式节点且冲突拒绝。出版日期只取 Journal PubDate，支持已知精度，MedlineDate/Season/未知月份保留 raw/unknown，不从 History/ArticleDate 补日期，不造已访问 URL。
- PubmedArticleSet 每个顶层条目顺序保留 parsed/rejected。书籍/删除指令等未支持格式显式拒绝；已 parsed PMID 同批再出现拒绝，不宣称跨文件幂等。工厂只对通过映射的有效非重复 PMID 调用，异常/非法 UUID 保留为调用方问题，不广泛吞成坏文献。
- 文件 10 MiB、1000 顶层条目、深度 64、100000 节点、每篇摘要 1000000 字符、30 秒协作计时，参数均显式可注入。语法/安全/全局预算失败整体抛错，映射/摘要预算按条拒绝；不是硬内存/时间/并发文件系统攻击沙箱。
- 新增 tests/unit/test_pubmed_contracts.py（27 场景）、tests/integration/test_pubmed_xml.py（47 场景），test_package.py 增加一个导入参数。真实安全库处理合成 UTF-8/UTF-16/混合标签/日期/署名/实体；网络、读取权限、时钟、回调变化为局部替身，未下载真实医学文献。
- 更新 README、总体/MVP/任务 SPEC、架构、技术选型、测试策略、进度；新增唯一运行依赖 defusedxml，不提前新增应用服务、数据库、分块、在线查询或 Phase 1 学习完成文档。

### 真实 TDD 过程

python 均指项目 .venv/Scripts/python.exe；启动前保存并清理 PYTEST_ADDOPTS/PYTEST_PLUGINS，结束恢复。目标命令为 `python -I -m pytest tests/unit/test_pubmed_contracts.py tests/integration/test_pubmed_xml.py -q --tb=short --basetemp=<R/pytest-target>`；尖括号在执行时替换为 R 下对应绝对路径。

| 步骤与实际时间 | 结果 | R 下原始记录 |
| --- | --- | --- |
| RED（2026-10-26 23:56:37 +08:00） | 退出 1，68 failed / 2.28s；收集成功，缺摘要 DTO 或 XML 模块 | red.txt |
| 最小实现 GREEN（23:59:53） | 原命令退出 0，68 passed / 1.44s | first-green-attempt.txt（实际通过） |
| 映射边界 RED（2026-10-27 00:01:16） | 空白 Label/Category 引起全局 ValidationError；Year=0000 在未知精度分支被接受；新增三反例，退出 1，3 failed、68 passed / 1.61s | mapping-edge-red.txt |
| 映射边界 GREEN（00:02:32） | 空属性归 null；已知非法年份先拒绝，再考虑未知月份/季节。原目标退出 0，71 passed / 1.34s | mapping-edge-green.txt |
| 日值边界 RED（00:05:23） | 未知月份不能掩盖已知 Day=99；新增反例及合法 UTF-16 验证，退出 1，1 failed、72 passed / 1.64s | day-edge-red.txt |
| 日值 GREEN（00:07:08） | 先校验已知日值，保持 unknown 精度不补造日期；追加读取权限安全码场景，退出 0，74 passed / 1.45s | day-edge-green.txt |

每个缺陷均先保留失败，再修复；没有删/弱化旧断言或增加跳过。第一次类型检查指出一个多余 ignore，删除后 mypy 通过，仅保留第三方未标类型的两个精确 import-untyped 隔离。Ruff 整理四个文件布局、import 顺序与 XML fixture 行长；fixture 仅增加元素间空白/属性换行，既有规范化结果断言不改，没有全局 ignore_errors。

### 回归、依赖与真实冒烟

| 实际命令/检查 | 结果 | R 下证据 |
| --- | --- | --- |
| 首轮完整回归（00:03:48 启动） | 276 passed / 65.58s；之后有日值行为修复，所以不作为最终实现结果 | first-regression.txt |
| `python -I -m pytest tests/unit tests/integration -q --tb=short --cov=clinical_agent.adapters.pubmed_xml --cov=clinical_agent.domain --cov-branch --cov-report=term-missing --cov-report=json:<R/coverage.json> --basetemp=<R/pytest-regression> -o cache_dir=<R/pytest-cache>`（00:08:58 启动） | 退出 0，279 passed / 64.46s；184 单元 + 95 集成，无 skip/xfail | regression.txt、coverage.json、.coverage |
| `python -m ruff check src tests` | All checks passed | ruff.txt |
| `python -m ruff format --check src tests` | 21 files already formatted | format.txt |
| `python -m mypy src --cache-dir <R/mypy-cache>` | Success: no issues found in 11 source files | mypy.txt |
| `python -m uv lock --check --offline` | Resolved 27 packages，退出 0 | lock-check.txt |
| `python -m uv pip check --python .venv/Scripts/python.exe` | Checked 27 packages，全部兼容 | pip-check.txt |
| 合成 XML→批次→分节→EvidenceChunk→validate_chunk 冒烟 | 一篇 parsed、一篇 invalid_pmid 拒绝；BACKGROUND/RESULTS 两节，RESULTS 的全摘要 [22,24) 回建 α🙂；scope=abstract | smoke.txt、smoke-result.json、synthetic-smoke.xml |

覆盖率仅采集当前 XML 适配器与 domain，汇总显示 97%（461 语句、192 分支，8 行/9 分支未覆盖），不是全包/全部库算法/医学正确性的证明。安全反例使用真实 defusedxml 拦截 UTF-8/UTF-16 自定义/外部实体；正常 DOCTYPE 在网络阻断下通过，语法截断不会分配前半文献 ID；未宣称所有 XML 攻击或全部官方 DTD 变体都验证。计时在事件/记录边界检查，不含强制中断能力。

正式 uv.lock SHA256 现为 `38963B49EB47281BF0DA7882D84C5B73D595766BFEDB7A12BF962A3FB656689A`；新增 defusedxml wheel SHA256 为 `a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61`，与 PyPI 一致。其 Requires-Dist=null；原有包版本不变，未增其他运行/开发包、未改共享 Conda/解释器/项目规则。没有 Git 提交或新 wheel 构建，已有本地 .env 仅确认忽略，不读取内容或修改。

最终交付核查通过：30 份 Markdown、180 个本地链接/锚点和围栏检查通过；P1-03 SPEC 的 11 节齐备，源码十一个文件、测试十个文件。22 文件基线仅声明/锁、domain.models 和一个新增导入参数变更，其余旧源码/测试/规则哈希不变；旧 26 包名称/版本逐项与当前比较，仅增加 defusedxml==0.7.1。官方 DTD 和所有 RED/GREEN/回归/质量/冒烟证据存在，15 个本次文件的 `git -c core.autocrlf=false diff --no-index --check` 空白诊断为 0，R 被忽略。结果在 R/delivery-audit.json，材料核查不另计行为测试。

P1-03 验收完成，Phase 1 整体未完成。只支持受限本地 PubmedArticleSet 的 PubmedArticle 摘要映射，未做持久化快照/入库、压缩/全量基线、外部 PMID/DOI 核验、完整 DTD 校验、在线 PubMed 搜索或医学效果评估。defusedxml 发行较旧、Windows/Python 3.12 当前实测不等同 Linux/未来环境兼容；对外接收不可信文件前仍需硬资源隔离与既有 Python 安全修订升级复核。

下一任务：**P1-04：基于来源单元的分块与 tokenizer 长度契约**；需先细化 SPEC、核实模型/tokenizer，再写失败测试。本次停止，不提前进入分块/Embedding 或入库。

## P1-04 本次执行（2026-10-27）

已读取项目规则、MVP/架构/技术选型、已实现 DTO/解析器和测试，保存全部既有 Python 源码/测试哈希基线。先创建 [详细 SPEC](specs/tasks/p1-04-source-chunking.md) 十一节，再编写目标测试。重新访问 E5 作者模型卡和 Transformers tokenizer 官方文档；本任务冻结计数边界，未选择或安装新的依赖版本。

实际修改：新增 domain/chunking.py、tests/unit/test_chunking.py、tests/integration/test_chunking.py 与任务 SPEC；扩展 test_package.py 的独立进程导入审计；更新 MVP、architecture、tech-stack 和本进度文件。最终核对另发现 models.py 并发新增多行中文注释；移除注释并恢复空行后与执行前哈希完全一致，且 AST 相同，确认没有业务逻辑变化。保留中文内容并进行 Ruff 格式化/长注释换行，证据 models-concurrent-edit.json、check-concurrent-comments.py。其余既有 Python 文件、正式依赖/锁文件不变。

- chunk_source 注入 tokenizer/profile/policy/ID 工厂，输出带版本、预算和实测 token_count 的 ChunkingResult。计数传入完整 document_prefix + 原切片，特殊 token 的处理属于计数接口契约，禁止 padding/truncation。
- PDF 页内、PubMed 全摘要 Unicode 码点偏移；不跨页/摘要节，原文切片不 decode、不重写，全部输出经 parsed.validate_chunk 回建验证。跳过片段前空白，保留片段内及已接纳的末尾空白；不保证句子或字素簇边界。
- 逐码点探测首次超预算后收块，不依赖 tokenizer 单调性；输入字符、候选字符、调用次数、片段数量有上限。首字符无法容纳、非法计数、重复 ID 和外部计数故障明确失败，不返回部分结果。默认 100,000 次调用是工作量保护，不是生产吞吐结论；真实模型性能尚待验证。
- 未编码 evidence.embedding_info=null，避免伪造维度或编码身份。模型/tokenizer 声明来自显式调用者；当前测试中的 fixture 身份和字符计数均为替身。

证据目录：`.artifacts/p1-04-20261027-01/`。pytest 前保存/清除 PYTEST_ADDOPTS、PYTEST_PLUGINS 并在 finally 恢复。每次使用独立 basetemp，没有清理历史目录。

| 顺序 | 实际命令（项目根目录） | 结果 / 文件 |
| --- | --- | --- |
| 首次 RED 尝试 | `.venv/Scripts/python.exe -m pytest tests/unit/test_chunking.py tests/integration/test_chunking.py -q` | 33 failed 因缺模块；另 1 error 因系统临时目录拒绝访问。red.txt；临时目录错误不算功能 RED |
| 有效 RED | 同上，加 `--basetemp=.artifacts/p1-04-20261027-01/red-temp` | 34 failed，全部缺少 clinical_agent.domain.chunking，0.80s；red-confirmed.txt |
| 最小 GREEN | 同上，basetemp 改为 green-temp | 34 passed，0.47s；green.txt |
| 候选字符工作量限制 RED | 同上，basetemp 改为 bounds-red-temp | 1 failed / 36 passed，0.64s；bounds-red.txt。SPEC 先补充字符上限，目标新增行为尚不存在 |
| 限制实现、格式化及真实 PDF 集成扩展 | 同上，basetemp 改为 final-target-temp | 38 passed，0.74s；final-target.txt |
| 全量回归 | `.venv/Scripts/python.exe -m pytest -q --basetemp=.artifacts/p1-04-20261027-01/regression-temp --cov=clinical_agent.domain.chunking --cov-report=term-missing --cov-report=json:.artifacts/p1-04-20261027-01/coverage.json` | 318 passed，53.67s；regression.txt。仅分块模块行覆盖率 99%（91 statements / 1 missed），不是整个项目覆盖率 |
| 格式和静态检查 | `.venv/Scripts/python.exe -m ruff format --check src tests`；`-m ruff check src tests`；`-m mypy src` | 24 文件格式、Ruff、12 源码类型检查全部通过；format.txt、ruff.txt、mypy.txt |
| 依赖验证 | `.venv/Scripts/python.exe -m uv lock --check --offline`；`-m uv pip check` | 27 包解析/兼容检查通过；lock.txt、pip-check.txt |

初次静态检查发现测试 zip 缺显式 strict，以及 model_dump.include 使用 dict_keys 与类型声明不匹配；分别明确 strict=False、改为 set，不改变断言含义。全量回归在这些修改后执行。最终另对并发中文注释做纯格式整理，AST 核验一致，重新检查全部 24 个 Python 文件格式通过；没有为纯注释格式变化重复运行全量测试。

本任务验收边界：真实合成 PDF/XML 经实际解析器再分块、来源/切片核验通过；没有真实模型 tokenizer、权重、Embedding、数据库、外部 API 或飞书验证。无共享 Conda 修改，无模型下载，不读取或改写用户 .env。锁文件 SHA256 仍为 `38963B49EB47281BF0DA7882D84C5B73D595766BFEDB7A12BF962A3FB656689A`。没有将测试替身通过等同模型验证；P1-F02 真实 tokenizer 验收仍开放。Phase 1 未完成，不创建阶段完成学习材料。

交付静态核对：运行 `.venv/Scripts/python.exe .artifacts/p1-04-20261027-01/check-concurrent-comments.py` 与 `audit-delivery.py`，确认注释外模型 AST/基线一致，31 份 Markdown、185 个本地链接/锚点及十一节 SPEC 完整，21 个既有 Python 文件仅导入审计与并发注释有变化；当前 12 源码/12 测试文件、27 个唯一包、锁文件及 RED/GREEN/回归证据存在。delivery-audit.json/txt 保存结果。注释变更后 Ruff 与全部格式检查再次通过。新增/修改的交付文件通过 `git -c core.autocrlf=false diff --no-index --check -- /dev/null <路径>` 空白诊断；无提交操作。

下一任务：**P1-05：本地 Embedding 与真实 tokenizer 适配**。先冻结模型/revision、实际 tokenizer、CPU/内存与时间预算、输入前缀和编码数量/维度契约，再按 TDD 实现与真实模型冒烟。本次停止，不自动进入下一任务。

## P1-05 本次执行（2026-10-27）

执行前读取 AGENTS.md.txt、PROJECT.md.txt、MVP/架构/技术选型、分块和现有测试；保存 24 份既有 Python 文件哈希及原 pyproject/lock。先创建 [十一节任务 SPEC](specs/tasks/p1-05-local-embedding.md)，明确固定模型、接口、预算、错误与真实验收条件，再编写失败测试。仅本地 Embedding/tokenizer，不实现持久化或问答入口。

技术核查：官方 PyPI 元数据确认 sentence-transformers 6.2.0 / Python>=3.10、transformers 5.21.0 / Python>=3.11、torch 2.14.1 / Python>=3.10；sentence-transformers 依赖 transformers>=5,<6 与 torch>=2.2，当前选型满足要求。官方 SDK 文档、模型卡和固定提交配置均已查看。模型 revision 固定为 d128750597153bb5987e10b1c3493a34e5a4502a；真实 768 维、最大 512 token。精确依赖放 ml extra，torch 映射 explicit=true 官方 CPU 索引，其余 PyPI 继续用官方索引。uv 通用锁含 67 项（含平台分支），Windows 实装 65 个唯一包、torch 2.14.1+cpu；原 27 包版本保持不变。没有改共享 Conda。

实际交付：

- domain/embedding.py：EmbeddedChunk、QueryEmbedding；有限严格浮点、维度与模型身份一致、非零与归一化范数校验；不依赖 ML 框架。
- adapters/embedding.py：显式本地快照/hash 验证、惰性官方 SDK 加载；count_tokens、tokenizer_profile、embed_chunks、embed_query。重新验证可变 DTO、完整前缀计数和预算，批次预检后编码，数量不符拒绝，补齐身份只返回新副本，失败无部分结果。
- 单实例锁串行、1 秒等待、每批 8 条、最多 128 片段，输入字符与操作/加载协作预算明确；不启动线程池，不声称能抢占单次模型调用或硬内存隔离。
- tests/unit/test_embedding.py、tests/integration/test_embedding_real.py；扩展导入隔离；新增 [模型操作说明](local-embedding.md)、[固定提交九份资产 manifest](research/p1-05-model-manifest.json)，更新 README/MVP/架构/技术选型/进度。无数据库/应用服务目录扩张。

所有执行输出位于 `.artifacts/p1-05-20261027-01/`。pytest 前保存/清除 PYTEST_ADDOPTS、PYTEST_PLUGINS，在 finally 恢复；真实模型执行期间 OMP_NUM_THREADS=2、MKL_NUM_THREADS=2，执行后恢复。每次独立 basetemp，不清理历史证据。

| 顺序 | 实际命令（项目根目录） | 结果 / 证据 |
| --- | --- | --- |
| RED | `.venv/Scripts/python.exe -m pytest tests/unit/test_embedding.py -q --basetemp=.artifacts/p1-05-20261027-01/red-temp` | 44 failed，1.25s，目标模块不存在；red.txt |
| 首次 GREEN 尝试 | 同上，basetemp 改为 first-green-temp | 43 passed / 1 failed，0.84s；first-green-attempt.txt。超长测试 fixture 在调用目标前因 token_count=513 被既有 DTO 拒绝，属于测试构造错误 |
| GREEN | 同上，basetemp 改为 green-temp | 44 passed，0.52s；green.txt。修正 fixture 为合法 DTO 后显式篡改文本/定位与声明计数，仍断言真实重计数拒绝；没有删除或弱化断言 |
| 扩展契约回归 | 同上，basetemp 改为 target-final-temp | 59 passed，1.05s；target-final.txt。增加快照实际 hash/缺文件/大小、加载异常/超时、计数契约、后续批次失败不修改输入等保障；小资产 fixture 明确替换可信权重摘要，不冒充 E5 |
| 正式锁与安装 | `.venv/Scripts/python.exe -m uv lock --system-certs`；`-m uv sync --locked --extra ml --system-certs` | 成功；lock-resolution.txt、install.txt。离线首次无缓存解析失败另存 lock-offline-attempt.txt，不算 RED；网络受限后使用已授权官方源下载 |
| 首轮真实模型 | `.venv/Scripts/python.exe -m pytest tests/integration/test_embedding_real.py -m external -q --basetemp=.artifacts/p1-05-20261027-01/real-temp` | 1 passed / 1 warning，119.93s；real-model-first.txt/json。加载 112.812s，分块/推理 6.713s，峰值 1,988,247,552 bytes |
| 当前 API 复验 | 同上，加 `-o faulthandler_timeout=180`，basetemp 改为 real-final-temp | 1 passed，31.88s，无警告；real-model-before-privacy.txt、real-model-before-privacy-result.json。SDK 旧方法改名警告经已安装官方源码核实后改为 get_embedding_dimension，再实际复验 |
| 首轮全量默认回归 | `.venv/Scripts/python.exe -m pytest -q --basetemp=.artifacts/p1-05-20261027-01/regression-temp --cov=clinical_agent.adapters.embedding --cov=clinical_agent.domain.embedding --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-05-20261027-01/coverage.json` | 379 passed / 1 deselected，64.99s；regression-before-privacy.txt。external 默认排除，与单独真实测试分开计数 |
| 严格文本/错误隐私 RED | `.venv/Scripts/python.exe -m pytest tests/unit/test_embedding.py -k input_error_does_not_leak_or_decode_bytes -q --basetemp=.artifacts/p1-05-20261027-01/privacy-red-temp` | 2 failed / 59 deselected，0.57s；privacy-red.txt。确认默认自动解码 bytes 与严格输入契约不符 |
| 严格文本/错误隐私 GREEN | `.venv/Scripts/python.exe -m pytest tests/unit/test_embedding.py -q --basetemp=.artifacts/p1-05-20261027-01/privacy-green-temp` | 61 passed，0.79s；privacy-green.txt。TypeAdapter 开启 strict 与 hide_input_in_errors，拒绝普通/非法 UTF-8 bytes 且错误文字无敏感原始值 |
| 最终默认回归 | 首轮回归命令，basetemp 改为 final-regression-temp | 381 passed / 1 deselected，63.91s；regression.txt、coverage.json。仅新增两模块含分支综合覆盖率 94%，不是全项目覆盖率，默认覆盖率未采集真实模型进程 |
| 最终真实模型复验 | 当前 API 复验命令，basetemp 改为 real-privacy-final-temp | 1 passed，31.30s，无警告；real-model.txt、real-model-result.json；严格文本修改后重新验证真实模型 |
| 静态及依赖 | `.venv/Scripts/python.exe -m ruff check src tests`；`-m ruff format --check src tests`；`-m mypy src`；`-m uv lock --check --offline`；`-m uv pip check` | Ruff、28 文件格式、14 源码类型检查、67 项锁、65 包兼容检查均通过；ruff/format/mypy/lock-check/pip-check.txt |
| 不含 ML 的干净环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-05-20261027-01/base-venv`；`.venv/Scripts/python.exe -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe` | 建立 11 包基础环境；base-install.txt。验证未安装 torch/sentence_transformers，适配器/业务 DTO 导入不加载 transformers，base-smoke.txt；该环境 `python -m clinical_agent doctor` 成功，base-doctor.txt；不是重复完整 pytest/wheel 验收 |

真实验收使用固定本地九份运行资产，网络连接函数全部阻断并记录，结果 network_attempts=[]。query 512 token 接受，513 token 报 embedding_token_limit；长中英摘要来源分块的 token_count=[11,512,96] 与实际模型 tokenize attention_mask 长度完全一致。所有片段能按原摘要全局偏移回建，输出768维、范数误差<=1e-4，重复查询向量最大差<1e-6。最终加载25.454s，分块/推理5.532s（分块1.608s），峰值工作集1,961,541,632 bytes，均在 SPEC 阈值内。这是固定合成样例的资源测量，不是医学检索效果或生产性能结论。

准备资产时读取官方固定提交并使用 HTTPS/系统证书下载，约1.11 GB safetensors SHA256 与官方 `a18a44fad1d0b46ded15928144138cff1135d5cc8233bdd90be5f18822de09a7` 一致；未下载或执行远程 Python 实现。第一次尝试读取仓库不存在的 config_sentence_transformers.json 返回 Entry not found，随后按实际目录冻结九份资产；未假造该配置。Get-CimInstance 硬件总内存读取受系统权限限制，没有声称取得该值，实际进程峰值由 Windows GetProcessMemoryInfo 测量。依赖解析出现旧元数据 `>= '2.7'` 规范化警告，安装缓存 rename 暂时拒绝访问后 uv 自动重试成功；不是无警告安装。基础环境 VIRTUAL_ENV 与目标不同的提醒已记录，uv 按显式 UV_PROJECT_ENVIRONMENT 正确隔离。

本轮 models.py 有并发中文学习注释更新，当前 AST 与 P1-04 已验收 AST 完全一致，concurrent-models-ast.json 保存核验；保留注释并 Ruff 格式化后再做全量回归。其他既有 Python 逻辑不变。正式 uv.lock SHA256 为 `D6BDB512BF14CAD9BC318D28C0B184C62A4C905FC87CAC91084AEC8C638B741B`。没有读取/改写用户 .env；models/、缓存和本地环境均忽略，不提交密钥或权重。

任务验收：本地模型、真实 tokenizer、默认回归及基础环境隔离通过。未验证 Linux/macOS/GPU、模型医学适用性、任意输入性能、硬超时/硬内存隔离、数据库/检索/RAG/LLM/飞书。没有生成 Phase 1 完成学习材料或宣称阶段完成。

交付静态核对：`.venv/Scripts/python.exe .artifacts/p1-05-20261027-01/audit-delivery.py` 通过；33 份 Markdown、201 个本地链接/锚点、十一节任务 SPEC 完整。24 份既有 Python 文件只有导入审计及上述并发注释变动，模型 AST 仍与既有验收一致；当前 14 源码/14 测试文件。基础依赖/开发组/构建约束不变，旧27包版本全部保持，新增38包均锁定，官方 CPU 分支无 CUDA 包。固定 manifest 与本地副本一致，真实模型/RED/GREEN/默认回归和基础环境证据存在；.env 和模型权重均被忽略。delivery-audit.json/txt 保存结果；本次16份新增/修改交付文件另做 Git 空白诊断，无提交操作。

下一任务：**P1-06：PostgreSQL + pgvector 持久化模型与迁移**。需用户指定后，先冻结单文档事务、身份/向量维度与唯一约束、迁移及测试数据库隔离。本次停止，不自动进入下一任务。

## P1-06 本次执行（2026-10-27）

执行前读取规则、MVP、架构、现有DTO/分块/Embedding、代码与测试；保存28份Python源码/测试哈希、原pyproject和uv.lock。先创建 [十一节SPEC](specs/tasks/p1-06-postgres-schema.md)，列明文件/场景，再写并运行失败测试。范围为ORM/显式连接/Alembic/数据库基础设施，未新增入库应用服务或store映射。

官方核查SQLAlchemy2.1.6（Python>=3.11）、Alembic1.20.1、psycopg3.3.6、pgvector0.5.1（后3项Python>=3.10），选择现有稳定API并精确加入db可选extra。实际解析/安装成功，74项锁、72个Windows已安装唯一包；新增SQLAlchemy、Alembic、Mako、psycopg、psycopg-binary、pgvector、tzdata，既有65包版本不变。没有修改ML模型、共享Conda或核心DTO逻辑。

本次文件：新增adapters/postgres/__init__.py、models.py、connection.py；alembic.ini、alembic/env.py、script.py.mako、versions/p106_0001_initial_postgres_schema.py；docker-compose.yml；tests/unit/test_postgres.py、tests/integration/test_postgres.py；本任务SPEC、postgres.md。更新pyproject/lock、.env.example、导入审计、README/MVP/架构/技术选型/进度。没有为后续服务创建空模块。

核心约束：generated来源身份（PDF hash/PubMed PMID）、来源唯一、文献/分块版本/序号唯一、组合来源外键及删除级联；书目/精度日期/原文/canonical来源单元保留；片段位置、token预算和固定E5身份/768维/单位范数检查。ORM不是对外DTO，JSONB深层业务和切片一致性留给下一任务映射器，不把结构性约束当全部医学事实核验。

Docker CLI最初引擎未运行，启动现有Docker Desktop后使用专用配置目录与Linux engine pipe；读取用户默认Docker配置被沙箱拒绝，未读取其内容，改用空的隔离Docker配置。引擎pipe/网络访问需工具提升，自动审批通过，没有绕过拒绝或索取额外人工确认。实际拉取官方pgvector/pgvector:0.8.7-pg16，digest为 `sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a`。独立project=clinical-agent-p106-20261027、database=clinical_agent_test_p106_20261027、127.0.0.1:55432；密码随机生成，仅忽略的本次测试文件保存并注入环境。所有Compose命令明确 `--env-file .env.example`，未读取用户.env；未连接/清理现有用户库。

证据目录 `.artifacts/p1-06-20261027-01/`。pytest前保存/清除PYTEST_ADDOPTS、PYTEST_PLUGINS并finally恢复；各次独立basetemp。后续使用独立cache_dir，避免跨权限缓存写入告警。

| 顺序 | 实际命令/操作 | 结果及证据 |
| --- | --- | --- |
| RED | `.venv/Scripts/python.exe -m pytest tests/unit/test_postgres.py -q --basetemp=.artifacts/p1-06-20261027-01/red-temp` | 13 failed，6.95s，缺目标postgres模块/迁移配置；red.txt |
| 依赖 | `python -m uv lock --system-certs`；`python -m uv sync --locked --extra ml --extra db --system-certs`（python为.venv/Scripts/python.exe） | 成功；lock-resolution.txt、install.txt。首次offline缺缓存另存lock-offline-attempt.txt，不算功能RED |
| 基础设施 | `docker ... compose -p clinical-agent-p106-20261027 --env-file .env.example config --quiet`；`up -d --wait postgres` | 实际healthy；compose-start.txt、image-pull.txt、image-digest.txt；限定本次project/volume |
| 迁移生成 | `.venv/Scripts/python.exe -m alembic revision --autogenerate -m initial_postgres_schema --rev-id p106_0001` | 官方Alembic针对专用空库生成；migration-generation.txt。审查后显式添加CREATE EXTENSION、保留降级扩展、整理长SQL字符串，版本文件不依赖当前ORM |
| GREEN | RED命令，basetemp改为green-temp | 13 passed，3.26s；green.txt。offline SQL无密码、无连接依赖，含扩展/表/向量/版本 |
| 首次真实数据库 | `.venv/Scripts/python.exe -m pytest tests/integration/test_postgres.py -m database -q --basetemp=.artifacts/p1-06-20261027-01/db-first-temp` | 38 passed / 2 failed，2.75s；db-first.txt。当前pgvector读出list，测试错误调用.tolist()；另有2条共享pytest缓存权限警告 |
| 真实数据库GREEN | 同上，basetemp=db-green-temp，加 `-o cache_dir=.artifacts/p1-06-20261027-01/db-pytest-cache` | 40 passed，2.45s，无警告；db-green.txt。明确assert list并保留768项数值断言，不删/弱化测试 |
| 最终真实数据库 | 同上，basetemp=db-final-temp，cache_dir=db-final-cache | 47 passed，2.62s；database.txt。补齐独立组合来源FK、同URI不同内容、PubMed必需数据、范数/token边界 |
| 默认完整回归 | `.venv/Scripts/python.exe -m pytest -q -o cache_dir=.artifacts/p1-06-20261027-01/core-cache --basetemp=.artifacts/p1-06-20261027-01/regression-temp --cov=clinical_agent.adapters.postgres --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-06-20261027-01/coverage.json` | 397 passed / 48 deselected，66.31s；regression.txt。默认排除47数据库+1模型测试；postgres模块81语句/2分支覆盖100%，不表示迁移子进程/所有SQL语义或全项目覆盖率 |
| 静态/锁 | `python -m ruff check src tests alembic`；`-m ruff format --check src tests alembic`；`-m mypy src`；`-m uv lock --check --offline`；`-m uv pip check` | Ruff、35文件格式、17源码类型、74锁/72包兼容均通过；ruff/format/mypy/lock-check/pip-check.txt。mypy发现pgvector已带类型，移除最初多余的import-untyped忽略，无全局放宽 |
| 干净基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-06-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe` | 11包，无SQLAlchemy/torch，postgres包命名空间/核心DTO导入及doctor通过；base-install/base-smoke/base-doctor.txt。不是完整pytest或新wheel验收 |
| 最终数据库核对 | `python .artifacts/p1-06-20261027-01/verify-database.py`（专用环境下） | revision=p106_0001、vector(768)、documents/chunks均0残留fixture行，实际constraint清单；database-audit.json/txt |
| 清理运行资源 | 同一project `compose ... stop postgres`，不删除volume | exited；compose-stop.txt、container-final-state.txt。保留本次卷和Docker Desktop，不关闭其他用户资源；下一任务需显式启动数据库 |

实际服务证据：database-version.json记录PostgreSQL16.15（Debian16.15-1.pgdg12+2）、pgvector0.8.7、UTF8、statement_timeout=10s、lock_timeout=2s；数据库在Linux容器中，客户端Python3.12.15运行于Windows。47项真实测试包括重复upgrade、downgrade保留vector、re-upgrade、Alembic可检测差异检查；跨会话commit读取作者/精度日期/Unicode/来源单元/向量，cosine手算0/1；非法文档/片段/维度/NaN/Infinity拒绝；片段失败文献回滚；两个独立Session并发仅一条提交、另一条命中uq_documents_source。不是完整导入应用的幂等结果测试，也未运行生产负载性能验证。

正式uv.lock SHA256=`09A02B68AD9160039522B894D4B76882945F15A6D9FE025C099D382776F9E165`。未重跑未改动的真实模型推理、未重建wheel、未实现DTO映射/导入/检索/RAG/Redis/飞书。生产权限分离、ANN索引/规模性能、源文件受控快照和深层JSONB业务验证仍待后续任务。Phase1未验收，不创建完成学习材料。

交付核对：运行 `.venv/Scripts/python.exe .artifacts/p1-06-20261027-01/audit-delivery.py`，35份Markdown、214个本地链接/锚点、十一节SPEC齐备；28份既有Python文件仅导入审计修改，核心逻辑文件未变。65个既有包版本/ML extra/基础依赖/构建约束保持，新增7包锁定；当前17源码/16测试。RED/GREEN、47真实数据库/397默认回归、基础环境及容器停止证据存在；秘密文件及用户.env均被忽略。delivery-audit.json/txt保存结果，21份本次交付文件做Git空白检查，未创建提交。

下一任务：**P1-07：离线入库服务与事务/幂等映射**。用户指定后先冻结DTO/ORM映射、canonical来源核验、单文档事务、重复/更新/冲突结果及回滚测试。本次停止，不自动开始。

## P1-07 本次执行（2026-10-27）

先读规则、现有SPEC/架构及解析/编码/数据库代码和测试，保存35份既有Python源码/测试/迁移哈希、原manifest和lock。创建 [十一节SPEC](specs/tasks/p1-07-offline-ingestion.md)，明确本地快照、事务和结果语义，再写失败测试。核查SQLAlchemy2.1官方Session/ON CONFLICT/Connection选项与psycopg诊断文档；复用已安装锁定版本，未新增/升级依赖。

实际新增：domain/ingestion.py；application/__init__.py、ingestion.py；adapters/offline.py、postgres/store.py；alembic/versions/p107_0002_ingestion_metadata.py；tests/conftest.py、unit/test_ingestion.py、unit/test_ingestion_mapping.py、integration/test_offline_reader.py、integration/test_ingestion.py；本任务SPEC和offline-ingestion.md。修改postgres/models.py新增nullable元数据及CHECK；导入审计增加5个模块并仅允许store显式导入SQLAlchemy；原数据库测试改验当前head、证据写当前指定目录/临时目录，保留历史P106证据；更新README/MVP/架构/技术选型/数据库说明/进度。

实现范围：

- 核心服务只依赖SourceReader/Embedder/IngestionStore最小协议，外部reader/编码/store可替换；批次最多32、每篇最多128块、120秒协作预算，错误码封闭，不把异常原文/路径/正文拼入结果。
- 受控SHA256快照、临时文件/fsync/同目录排他硬链接、并发一致性与损坏缓存拒绝。PDF filename标题保留原文件stem。原文件移走后，受控快照和canonical来源单元仍可核验；没有自动清理用户文件或孤立快照。
- PreparedIngestion重验证来源、顺序、覆盖、位置、模型、数量/向量；完整映射保留真实parser/profile/policy。p107_0002为旧行保留NULL，legacy/坏数据拒绝当重复，不伪造版本。读取返回脱离会话的业务DTO。
- 来源定向ON CONFLICT DO NOTHING；新文献和全部片段短事务提交，冲突后只读取合法winner分类。already_present返回规范旧ID；内容快照变化needs_update、元数据/配置变化conflict均不覆盖。其他PK/片段约束失败不能冒充重复。重试仍可重复编码，非exactly-once承诺。
- 借用连接上、Session事务前设置READ COMMITTED，使用现有连接池且不改变调用者engine。解析/分块/模型阶段无数据库连接；任一片段/commit失败回滚，已知commit成功不因其后预算到期改报失败。

证据目录 `.artifacts/p1-07-20261027-01/`。各次pytest保存/清除PYTEST_ADDOPTS、PYTEST_PLUGINS并finally恢复，使用新basetemp/cache_dir；真实模型临时OMP/MKL线程数2，执行后恢复。Docker使用独立project=clinical-agent-p107-20261027、database=clinical_agent_test_p107_20261027、仅127.0.0.1:55432，新随机密码在忽略的测试文件保存并注入进程环境；所有Compose明确--env-file .env.example，未读取用户.env或P106密码，未修改P106卷。

| 顺序 | 实际命令/变体（python=.venv/Scripts/python.exe） | 结果与证据 |
| --- | --- | --- |
| 初始RED | `python -m pytest tests/unit/test_ingestion.py tests/integration/test_offline_reader.py -q -o cache_dir=.artifacts/p1-07-20261027-01/red-cache --basetemp=.artifacts/p1-07-20261027-01/red-temp` | 26 failed，0.85s，目标模块不存在；red.txt |
| 初始GREEN | 同上，目录改green-cache/green-temp | 26 passed，0.91s；first-green.txt |
| 映射/迁移RED | `python -m pytest tests/unit/test_ingestion_mapping.py -q`，本次mapping-red-cache/temp | 11 failed，1.63s，缺store/元数据列/新head；mapping-red.txt |
| 映射GREEN | 三份目标测试同跑（加test_ingestion_mapping.py），mapping-green-cache/temp | 37 passed，1.89s；mapping-green.txt。类型检查发现联合来源单元不能直接访问start，改为显式分支构造位置元组，没有忽略类型错误 |
| 真实XML批次边界RED | `pytest tests/integration/test_offline_reader.py -k actual_xml_application_batch_limit -q`，batch-red-cache/temp | 1 failed / 6 deselected，0.79s；batch-red.txt，超限误报source_failed。先补SPEC，保留固定batch_limit业务信号，不透传未知异常码 |
| 错误码封闭RED | `pytest tests/unit/test_ingestion.py -k error_codes_are_closed -q`，codes-red-cache/temp | 3 failed / 22 deselected，0.64s；codes-red.txt。原MetadataText允许任意原文，改封闭Literal集合 |
| 目标最终GREEN | `python -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_mapping.py tests/integration/test_offline_reader.py -q`，target-final-cache/temp | 43 passed，1.93s；target-final.txt，包含预算后已确认commit仍成功、异常不泄漏等正向回归 |
| 首次真实数据库 | `python -m pytest tests/integration -m "database and not external" -q`，db-first-cache/temp | 60 passed / 1 failed / 106 deselected，5.07s；database-first.txt。失败为测试内嵌JSON冒号被text()当绑定参数，改为CAST绑定JSON参数，保留legacy数据断言，不是产品RED |
| 真实数据库GREEN | 同上，db-green-cache/temp | 61 passed / 106 deselected，4.20s；database.txt，含P106的47项实际数据库回归 |
| 隔离级别RED | `pytest tests/integration/test_ingestion.py -m database -k store_sets_read_committed -q`，isolation-red-cache/temp | 1 failed / 15 deselected，2.29s；isolation-red.txt，传入RR engine后实际事务RR |
| 隔离首次修复尝试 | 整套数据库，db-final-cache/temp | 1 failed / 61 passed / 106 deselected，4.96s；isolation-first-attempt.txt。仅嵌套engine.execution_options未生效，实际测试拒绝该实现 |
| 最终数据库验收 | 整套数据库，db-corrected-cache/temp；借出的Connection上显式设置隔离 | 62 passed / 106 deselected，4.06s；database-final.txt。验证调用者RR engine不变，实际写事务RC |
| 首轮真实E5+PG链路 | `python -m pytest tests/integration/test_ingestion.py -m "database and external" -q -o faulthandler_timeout=180`，real-cache/temp | 1 passed / 14 deselected，72.11s；real-chain-before-isolation.txt及对应-result.json。修复隔离后未以旧结果代替复验 |
| 最终真实E5+PG链路 | 同上，real-final-cache/temp | 1 passed / 15 deselected，32.03s；real-chain.txt、real-chain-result.json。实际PDF快照→E5编码→PG提交→重复返回→脱离会话读取/回建，768维，两块token_count=[6,6]，原件移走后快照保留 |
| 最终默认回归 | `python -m pytest -q -o cache_dir=.artifacts/p1-07-20261027-01/core-final-cache --basetemp=.artifacts/p1-07-20261027-01/regression-final-temp --cov=clinical_agent.domain.ingestion --cov=clinical_agent.application.ingestion --cov=clinical_agent.adapters.offline --cov=clinical_agent.adapters.postgres.store --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-07-20261027-01/coverage.json` | 445 passed / 64 deselected，80.13s；regression.txt。排除62数据库+2真实模型，和单独验收分开计数；只四个新增模块含分支覆盖83%，默认覆盖未计入真实SQL/模型进程，不是全项目覆盖率 |
| 静态/依赖 | `python -m ruff check src tests alembic`；`-m ruff format --check src tests alembic`；`-m mypy src`；`-m uv lock --check --offline`；`-m uv pip check` | Ruff、46文件格式、22源码类型、74锁/72包兼容均通过；ruff/format/mypy/lock-check/pip-check.txt。提取逐篇方法消除循环闭包警告，未禁用规则 |
| 干净基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-07-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe` | 11包、无SQLAlchemy/torch；核心入库DTO/应用服务/离线reader导入及doctor通过；base-install/base-smoke/base-doctor.txt。不是新wheel或完整pytest验证 |
| 最终资源核对 | `python .artifacts/p1-07-20261027-01/verify-database.py`；本次project `compose ... stop postgres` | p107_0002、vector(768)、nullable metadata、0文献/0片段fixture残留；database-audit.json/txt。容器exited，卷保留；compose-stop.txt、container-final-state.txt。未停止其他容器或Docker Desktop |

真实数据库为PostgreSQL16.15/vector0.8.7（database-version.json / database-audit.json）。新测试验证同内容/改名/不同输入ID返回规范旧ID，元数据/policy冲突与同PMID内容变化不覆盖；片段PK和错误文献PK不当重复、实际commit故障回滚与重试、损坏/legacy记录拒绝；barrier使两个独立事务在INSERT前同步，最终一个imported一个already_present且只有一套片段。实际PDF/XML混合条目应用链路用明确编码替身验证，另有真正固定E5 CPU链路。全部记录使用合成文献，不声称医学效果得到评估。

依赖/正式锁未变，uv.lock SHA256仍为 `09A02B68AD9160039522B894D4B76882945F15A6D9FE025C099D382776F9E165`，无新模型下载、共享Conda修改或用户原文件删除。未实现CLI/API/检索/RAG/飞书、更新覆盖、自动孤立快照清理、生产负载/硬超时。Phase1未整体验收，不生成完成学习文档；本任务使用说明不是阶段完成材料。

交付核对：`.venv/Scripts/python.exe .artifacts/p1-07-20261027-01/audit-delivery.py`通过；37份Markdown、230个本地链接/锚点及十一节SPEC齐备。35份既有Python文件仅postgres/models.py、原数据库测试及导入审计变化；旧迁移/核心DTO/模型编码器未改。manifest/lock逐字节不变，仍72包；当前22源码、20测试文件及3迁移Python文件。P106历史revision证据未覆盖，当前RED/GREEN/默认/数据库/真实模型链路、基础环境和容器停止证据齐备；用户.env及随机测试密码文件被忽略。delivery-audit.json/txt保存结果，22份交付文件做Git空白诊断，未创建提交。

下一任务：**P1-08：基础向量检索与证据命中DTO**。用户指定后先冻结query模型身份、检索范围/阈值/排序和证据返回/来源回建契约。本次停止，不自动进入。


## P1-08 本次执行（2026-10-27）

执行前读取项目规则、既有SPEC及源码/测试，保存46份Python文件哈希、原manifest与lock。先冻结[十一节SPEC](specs/tasks/p1-08-vector-retrieval.md)，列明本次文件和测试场景，再写实际失败测试。新增domain/retrieval.py、application/retrieval.py、adapters/postgres/retrieval.py及两个test_retrieval.py；仅修改既有test_package.py的导入隔离审计。另新增本任务SPEC和[运行说明](vector-retrieval.md)，更新README/MVP/架构/技术选型/进度。没有实现生成、引用报告、CLI/API/飞书入口，也没有改动既有业务逻辑或迁移。

固定当前E5完整身份，拒绝仅维度相同的其他向量空间；query仅编码一次，编码在DB事务前。SQL精确余弦距离，先过滤来源/获取范围/指定文献/模型及阈值，再distance与UUID稳定排序、limit。只读REPEATABLE READ事务内最多三条数据SELECT，批量完整映射选中文献及有界片段；来源损坏明确失败，不冒充空结果。EvidenceHit保留来源/位置、可信书目、score_type与rank，不携带向量值或整篇全文。内部source_uri仍是本机快照路径，未来输出适配器必须专门渲染。

本轮证据目录 `.artifacts/p1-08-20261027-01/`。pytest保存/清除PYTEST_ADDOPTS及PYTEST_PLUGINS并finally恢复，各轮独立basetemp/cache_dir。下表python均为`.venv/Scripts/python.exe`，路径均相对项目根目录；TEMP/CACHE表示该证据目录中的各次独立子目录。

| 顺序 | 实际命令/操作 | 结果及证据 |
| --- | --- | --- |
| RED | `python -m pytest tests/unit/test_retrieval.py -q --basetemp=TEMP -o cache_dir=CACHE` | 50 failed，1.03s；red.txt，因目标模块尚未实现 |
| GREEN | 同一目标命令，独立TEMP/CACHE | 50 passed，1.22s；green.txt |
| 错误码补充RED | 目标测试 `-k untrusted_boundary_error_code` | 1 failed / 50 deselected，0.48s；error-red.txt。自定义adapter错误码回显异常文字，新增运行时闭集校验后51 passed，1.25s，target-final.txt |
| 最终目标 | `python -m pytest tests/unit/test_retrieval.py -q --basetemp=TEMP -o cache_dir=CACHE` | 补齐正向DTO/阈值/边界用例后55 passed，1.31s；target-complete.txt |
| 真实数据库回归 | `python -m pytest tests/integration -m "database and not external" -q --basetemp=TEMP -o cache_dir=CACHE` | 74 passed / 107 deselected，5.14s；database-first.txt、database.txt，含既有62项和新增12项 |
| 默认全量回归 | `python -m pytest -q --basetemp=TEMP -o cache_dir=CACHE --cov=clinical_agent.domain.retrieval --cov=clinical_agent.application.retrieval --cov=clinical_agent.adapters.postgres.retrieval --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-08-20261027-01/coverage.json` | 503 passed / 77 deselected，84.37s；regression.txt。仅本轮3模块含分支综合78%，不含另跑的数据库/模型进程，不是全项目覆盖率 |
| 真实模型检索 | `python -m pytest tests/integration/test_retrieval.py -m "database and external" -q --basetemp=TEMP -o cache_dir=CACHE` | 1 passed / 12 deselected，31.92s；real-retrieval.txt/result.json；OMP/MKL线程2，临时恢复原设置，阻止非loopback网络 |
| 静态/依赖 | `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src`；`python -m uv lock --check --offline`；`python -m uv pip check` | Ruff/51文件格式/25源码类型检查通过，74项锁/72个唯一包兼容；ruff/format/mypy/lock-check/pip-check.txt |
| 无db/ml基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-08-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe`；新环境`python -m clinical_agent doctor` | 11包；核心检索DTO/应用服务可导入且无SQLAlchemy/torch，doctor通过；base-install/base-smoke/base-doctor.txt。不是新wheel或完整新环境pytest验收 |
| 数据库收尾 | `python .artifacts/p1-08-20261027-01/verify-database.py`；专用project的`compose ... stop postgres` | head=p107_0002、vector(768)、0文献/0片段；database-audit.json/txt。容器exited，卷保留；compose-stop/container-final-state.txt |

数据库使用独立project=clinical-agent-p108-20261027、库clinical_agent_test_p108_20261027、127.0.0.1:55432、随机测试密码和reset显式开关；Compose明确`--env-file .env.example`、独立docker-config及Linux engine pipe。访问Docker/localhost按工具审批通过，没有读取用户.env或其他库/密码；只停止本次容器，不关闭Docker Desktop或其他项目，不删卷。PostgreSQL16.15/vector0.8.7，沿用固定digest镜像，schema未变。

真实SQL验证1/0/-1及约0.6余弦分数、阈值含等号、同分UUID顺序、过滤先于limit、摘要切片/Unicode、legacy/坏来源/丢片段、受控DB失败、READ ONLY/RR及调用者隔离选项不变。候选读取后从另一连接更新标题，hydration仍使用原快照。实际E5链路使用既有固定revision d128750597153bb5987e10b1c3493a34e5a4502a本地资产，无新下载：768维query/document向量，1个命中score=0.8736043127054858，获取范围extracted_text，按保存来源切片回建成功；仅合成样例技术链路，不是医学检索质量结论。

mypy首轮发现Literal列表default_factory推断过宽，使用Pydantic按实例复制的直接列表默认值解决，无放宽类型检查。Ruff仅作格式整理；补充错误码测试先RED再修复，没有删除/弱化断言。未新增/升级依赖，正式uv.lock SHA256仍为09A02B68AD9160039522B894D4B76882945F15A6D9FE025C099D382776F9E165。未重新运行未改动的wheel/任意平台部署；未评价医学召回率、ANN/生产规模性能、硬超时或生成内容支持关系。Phase1仍未完成，不生成阶段完成材料。

下一任务：**P1-09：基础RAG工作流与证据关联回答**。用户指定后先细化SPEC及LLM/工作流/引用门禁测试；本次停止，不自动进入。

交付核对：`python .artifacts/p1-08-20261027-01/audit-delivery.py`通过，39份Markdown、246个本地链接/锚点及十一节SPEC齐备；46份既有Python文件仅导入审计test_package.py改变，既有业务代码/迁移未变。25源码、22测试文件、3迁移Python文件；manifest/lock逐字节一致，72个唯一包/74项锁。RED/GREEN、55目标/503默认/74数据库/1真实模型检索、11包基础环境、0残留fixture及容器停止证据存在；P1-06/P1-07历史数据库证据保留。.env与测试秘密被忽略。首次Git空白诊断遇到Windows CRLF及输出解码问题，文档统一LF并按原始bytes诊断后13份交付文件通过；无提交操作。delivery-audit.json/txt与whitespace.txt保存结果。


## P1-09 本次执行（2026-10-27）

执行前读取AGENTS/PROJECT、总体/MVP/架构与技术选型、既有DTO/检索/导入审计及fixtures，保存51份既有Python文件哈希和旧manifest/lock。先创建[十一节任务SPEC](specs/tasks/p1-09-basic-rag.md)，明确文件、接口、预算和测试，再写实际RED。用户随后明确提供DeepSeek端点、模型与密钥用于真实测试；密钥仅在外部测试进程环境临时注入并finally恢复，不写入源码、文件、示例或测试输出，没有读取用户.env。

本次新增4个生产模块domain/research.py、domain/citations.py、application/research.py、adapters/deepseek.py；新增tests/unit/test_research.py、tests/integration/test_deepseek.py及test_research_live.py。已有Python文件只修改test_package.py，增加四个导入审计并阻止导入httpx/langsmith。新增任务SPEC和basic-rag.md，更新README/总体/MVP/架构/技术选型/测试策略/开发计划、pyproject/uv.lock及.env.example。没有修改既有业务实现/迁移，没有开启业务入口或进入Phase2。

官方复核：LangGraph1.2.17、LangSmith0.14.12均Python>=3.10，HTTPX0.28.1>=3.8；实际当前Python3.12.15安装/锁/运行通过。使用rag extra精确固定三项，LangSmith显式关闭自动追踪，HTTPX实现用户指定单供应商官方JSON协议；未引入OpenAI SDK、LangChain顶层包或通用客户端框架。传递依赖含langchain-core1.7.0、checkpoint/prebuilt/sdk等，未实际使用其预置Agent/持久化/网络平台。新增25个包，旧74条锁记录（73个唯一名称，包括同名CPU变体）版本全部保持；当前99条锁记录/98个唯一名称，97个已安装唯一包。官方PyPI响应分别保存在本轮*-pypi.json；单一compile文档链接一次返回unsupported content-type，改读官方graph-api和实际API验证，不假定该链接可读取。

证据目录 `.artifacts/p1-09-20261027-01/`；下表python为`.venv/Scripts/python.exe`。所有pytest显式保存/清除PYTEST_ADDOPTS/PYTEST_PLUGINS并finally恢复，每轮独立`--basetemp`和`-o cache_dir`。TEMP/CACHE表示本轮证据目录下对应命令的独立目录，未用共享pytest缓存。

| 顺序 | 实际命令/操作 | 结果及证据 |
| --- | --- | --- |
| 核心RED | `python -m pytest tests/unit/test_research.py -q --basetemp=TEMP -o cache_dir=CACHE` | 27 failed /14 errors，1.43s；red.txt。均因新research/citations模块缺失，14项fixture依赖该模块；没有把环境/依赖安装故障算RED |
| 依赖 | `python -m uv lock --system-certs`；`python -m uv sync --locked --extra ml --extra db --extra rag --system-certs` | 正式锁定及安装成功；lock-resolution.txt、install.txt；共享Conda不变 |
| 核心首轮GREEN尝试 | 核心目标命令，独立TEMP/CACHE | 40 passed /1 failed，4.53s；green.txt。失败为测试helper试图JSON编码bytes，未到被测逻辑。改为JSON可表达的None负例，并独立保留DraftClaim bytes拒绝测试，未删弱断言 |
| HTTP RED | `python -m pytest tests/integration/test_deepseek.py -q --basetemp=TEMP -o cache_dir=CACHE` | 19 failed，0.87s；http-red.txt，因DeepSeek模块尚未实现 |
| 合并GREEN | `python -m pytest tests/unit/test_research.py tests/integration/test_deepseek.py -q --basetemp=TEMP -o cache_dir=CACHE` | 61 passed，1.59s；combined-green.txt |
| 扩展目标与隔离 | 上述两文件加`tests/unit/test_package.py` | 101 passed /1 failed，33.74s；target.txt。注入字符串测试超出fixture默认64 token预算，实际分块正确，测试改用明确512预算保留全段验证，不修改生产分块逻辑 |
| 补充目标 | 两目标文件命令 | 73 passed，1.65s；target-final.txt。含追踪关闭、三种kind均需引用、并发隔离、来源快照冲突等 |
| 配置补充RED | `python -m pytest tests/integration/test_deepseek.py -k mutated_settings -q --basetemp=TEMP -o cache_dir=CACHE` | 1 failed /19 deselected，0.98s；config-red.txt。已验证的Settings后续修改端点可绕过检查；增加revalidate_instances=always，客户端创建前重验 |
| 最终目标GREEN | 两目标文件命令 | 74 passed，1.42s；target-complete.txt，54核心+20HTTP协议场景 |
| 默认全量回归 | `python -m pytest -q --basetemp=TEMP -o cache_dir=CACHE --cov=clinical_agent.domain.research --cov=clinical_agent.domain.citations --cov=clinical_agent.application.research --cov=clinical_agent.adapters.deepseek --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-09-20261027-01/coverage.json` | 581 passed /78 deselected，84.95s；regression.txt/coverage.json。新增四模块含分支综合94%，不含独立真实LLM进程，不是全项目覆盖率 |
| 真实LLM首轮 | `python -m pytest tests/integration/test_research_live.py -m external -q --tb=short --basetemp=TEMP -o cache_dir=CACHE` | 1 failed，3.74s；real-llm-first.txt。回答已通过引用/范围断言，测试记录器把压缩传输字节直接UTF-8解码，保存response_model阶段失败；不能称该轮通过 |
| 真实LLM复验 | 同上，修复测试记录器按HTTP Content-Encoding解码，独立TEMP/CACHE | 1 passed，3.32s；real-llm.txt、real-llm-result.json、real-llm-answer.json。共执行2次小型付费合成请求，无自动重试，未发送真实库内容 |
| 静态与依赖 | `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src`；`python -m uv lock --check --offline`；`python -m uv pip check` | Ruff/58文件格式/29源码类型、99条锁/97包兼容均通过；ruff/format/mypy/lock-check/pip-check.txt。首轮mypy补字典明确类型，未放宽检查；初轮Ruff排版问题格式化后通过 |
| 干净基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-09-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe`；新环境`python -m clinical_agent doctor` | 11包，四新模块可导入，无rag/db/ml包，doctor成功；base-install/base-smoke/base-doctor.txt |
| 干净rag环境 | 同上，目标改为rag-venv且加`--extra rag`，运行注入Empty/Never端口的实际ResearchService | 44包，实际LangGraph空证据分支成功，生成器未调用，无SQLAlchemy/torch；rag-install/rag-smoke.txt。不是全量新环境pytest或新wheel验收 |

核心行为：编译一次StateGraph，retrieve→empty或prepare→generate→validate；每请求状态独立，模型与数据库事务解耦。生成输入是问题/片段/位置/范围/固定规则/schema，书目从可信命中挑选，来源只列实际使用片段。模型不可新增书目字段、空引用或未知chunk_id；重复JSON键/NaN/超大输出/截断响应拒绝整个回答。返回kind区分证据/推断/不确定，固定局限不宣称覆盖最新研究或语义事实已核实。来源无本机路径字段/向量，未知书目不补造；独立引用函数不依赖LangGraph或HTTP。

DeepSeekSettings只接受官方HTTPS origin及/v1，SecretStr隐藏密钥、不加载.env，创建客户端前强制重验证。HTTPX无自动重试/重定向/环境代理，TLS校验保持，连接池4，connect/write/pool最多5秒，read和逐块计时受生成预算约束，响应有解压后128000 bytes上限；失败不输出body/凭据/原始异常。研究总预算默认90秒/生成60秒，均为协作检查，不能抢占外部执行。追踪开启环境下测试实际仍enabled=False、socket连接被阻止且环境不被修改。

真实请求模型deepseek-chat，响应model=deepseek-flash；用户别名兼容性已实测，但不是不可变版本。得到5条claims/1个source：明确虚构教学、12名虚构参与者、无对照组、不能确立治疗效果/指导照护；推断和不确定性分别标注。编码助手逐条阅读来源与回答后的核对见synthetic-answer-review.json，不是独立医学专家人工评审；没有医学检索/回答质量评估。该测试检索为人工fixture，使用Fake tokenizer/embedding，不是实际E5或PostgreSQL；P1-08的真实E5/PG记录保留，不能拼接独立测试冒充E5→PG→LLM整链路。

本轮没有改动DB/检索/入库实现或迁移，没有重复启动数据库、重跑旧真实模型或构建wheel。实际LLM复验之后仅修正配置对象重验证，已用原有效配置的完整协议/回归覆盖，没有因此再次发起付费请求。环境变量不持久化、无创建提交、无改动用户.env；真实密钥已在聊天出现，已建议轮换。

下一步建议：**P1-10：CLI离线入库与问答入口**。需用户指定后先细化SPEC；本次停止。Phase1入口/飞书、真实整链路、医学人工审查及阶段完成学习材料尚未完成，不标记Phase1验收。

交付核对：`python .artifacts/p1-09-20261027-01/audit-delivery.py`通过；41份Markdown、265个本地链接/锚点及十一节SPEC完整，20份交付文件Git空白检查通过（识别Windows CRLF）。51份既有Python文件只有导入审计修改，29源码/25测试文件/3迁移Python文件。旧依赖版本、基础依赖/dev组/构建约束及db/ml extras保持；正式锁SHA256=7EB9F27E43DAB21E8D811F1AE5E768D2A3C936A807733C022BAEDBD438F06CDB。74目标/581默认/1真实LLM、11包基础/44包rag环境证据存在；P1-06/07/08历史数据库报告保留。审计脚本首次误用旧报告字段documents，按其实际document_rows_after_tests键修正后通过，未更改历史报告。仅扫描本轮交付及根层文本证据，无密钥格式值，未读取用户.env，其忽略规则有效。delivery-audit.json/txt保存结果，无提交操作。


## P1-10 本次执行（2026-10-27）

执行前读取AGENTS/PROJECT、现有MVP/架构/前序任务SPEC、CLI/bootstrap、入库/模型/数据库/问答契约及测试，保存58份既有Python文件哈希和原manifest/lock。按[十一节任务SPEC](specs/tasks/p1-10-cli-entrypoints.md)先冻结命令、文件、输出/退出/生命周期和测试范围，再执行RED。官方复核Python3.12 argparse/contextlib API，无新组件或依赖；保留Python3.12.15实际环境，不把在线文档3.12.16标题当本机版本。

生产仅修改cli.py，新增command_runtime.py。命令复用现有IngestionService/ResearchService等，不修改任何入库、分块、模型、数据库、检索、RAG、HTTP业务实现或迁移。测试新增test_command_cli.py、test_command_runtime.py、test_command_entrypoints.py、test_command_pipeline.py，修改test_package.py加入装配模块的隔离导入。另新增本任务SPEC和cli.md，更新README/总体/MVP/架构/技术选型/测试策略/开发计划及RAG说明。没有修改pyproject/uv.lock/.env.example，没有新依赖、schema、API或飞书。

命令ingest强制显式source-type/path/allowed-root/snapshot-dir/model-dir，提供单文件PDF/XML服务入口；ask接受question/model-dir/top-k/min-similarity，只检索local并走已配置DeepSeek。关联UUID可显式提供或生成，导入UTC时间由CLI建立。help/参数校验先于资源，所需环境配置先于模型加载；模型不自动下载，数据库不自动迁移，不读用户.env。stdout一个JSON文档，stderr日志/受控错误；ASCII转义Unicode保证非UTF8 Windows管道可解析。资源context退出后才输出结果，HTTP先于engine关闭，不伪造模型close接口。退出0/3/2/1/130的完整定义见CLI说明。

证据目录 `.artifacts/p1-10-20261027-01/`。下表python为`.venv/Scripts/python.exe`；每轮pytest保存/清除PYTEST_ADDOPTS与PYTEST_PLUGINS并finally恢复，使用独立`--basetemp`和`-o cache_dir`，表中TEMP/CACHE为本轮证据下相应目录。

| 顺序 | 实际命令/操作 | 结果及证据 |
| --- | --- | --- |
| CLI RED | `python -m pytest tests/unit/test_command_cli.py -q --basetemp=TEMP -o cache_dir=CACHE` | 27 failed，1.07s；red.txt，因目标命令/注入接口缺失 |
| 装配RED | `python -m pytest tests/unit/test_command_runtime.py -q --basetemp=TEMP -o cache_dir=CACHE` | 4 failed，0.44s；runtime-red.txt，因command_runtime缺失 |
| GREEN | 两个目标单元文件命令，独立TEMP/CACHE | 31 passed，2.40s；green.txt |
| 扩展目标/入口 | `python -m pytest tests/unit/test_command_cli.py tests/unit/test_command_runtime.py tests/integration/test_command_entrypoints.py -q --basetemp=TEMP -o cache_dir=CACHE` | 43 passed，12.79s；target.txt。增加完整answered字段/混合批次/已知依赖分类和8项module/console子进程 |
| 真实DB准备 | 专用Compose `up -d --wait postgres`；`python -m alembic upgrade head` | 启动独立空库并迁移p107_0002；compose-start.txt、migration.txt。CLI本身不迁移 |
| 真实CLI/E5/PG | `python -m pytest tests/integration/test_command_pipeline.py -m "database and external" -q --basetemp=TEMP -o cache_dir=CACHE` | 1 passed，62.03s；real-cli.txt/result.json；实际固定E5 CPU、真实PostgreSQL/pgvector，LLM明确HTTPX MockTransport |
| 默认完整回归 | `python -m pytest -q --basetemp=TEMP -o cache_dir=CACHE --cov=clinical_agent.cli --cov=clinical_agent.command_runtime --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-10-20261027-01/coverage.json` | 625 passed /79 deselected，121.46s；regression.txt/coverage.json。两目标模块含分支综合97%，不含独立外部或CLI子进程的覆盖采集，不是全项目覆盖率 |
| 静态及依赖 | `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src`；`python -m uv lock --check --offline`；`python -m uv pip check` | Ruff/63文件格式/30源码类型、99条锁/97个已装包兼容均通过；ruff/format/mypy/lock-check/pip-check.txt |
| 干净基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-10-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe` | 11包，无torch/SQLAlchemy/LangGraph/HTTPX；分别module/console的help、ingest help、ask help、doctor、缺依赖共10项通过，子进程cp936管道；base-install/base-smoke.txt |
| DB收尾 | `python .artifacts/p1-10-20261027-01/verify-database.py`；专用project的`compose ... stop postgres` | head=p107_0002、vector(768)、文献/片段均0；database-audit.json/txt。容器exited，卷保留；compose-stop/container-final-state.txt |

实际测试项目clinical-agent-p110-20261027，数据库clinical_agent_test_p110_20261027、127.0.0.1:55432，明确ALLOW_TEST_RESET=1及独立随机密码文件/环境；Compose始终--env-file .env.example与独立docker-config/已知Linux engine pipe。按工具自动审批访问本机数据库/Docker，不读取用户.env或默认Docker凭据；没有审批拒绝或要求额外人工许可。结束只停本次容器，不关闭Desktop、其他项目或删除卷。

真实测试通过cli.main调用生产装配，PDF导入/重复/XML导入结果为imported/already_present/imported；实际2文献/2片段，问答answered，1来源及1次HTTP协议替身请求，chunk关联检查通过。测试在同进程复用一次实际固定E5实例，未声称每次重新加载或通过console进程执行了真实业务；module/console解析/配置/帮助独立用子进程验证。socket只允许loopback，DeepSeek为显式MockTransport，未发送任何外部文献或付费模型请求。当前DEEPSEEK_API_KEY环境未配置，未读取.env或重用前次聊天披露的旧密钥，真实付费CLI整链路未验证。

mypy首轮4项错误来自BaseSettings的环境必需字段与静态构造签名差异；装配处显式窄化零参数环境构造Callable，没有修改设置契约、使用全局ignore或放宽检查。Ruff首轮排版/长行经格式化处理；真实测试后一条XML fixture长行拆分为空白，不改变规范化摘要内容或生产逻辑，没有为此重复启动模型。其余实际验收均首轮通过，未删除/弱化用例。

本轮不重复执行旧全套数据库或实际付费LLM，未构建新wheel、验证Linux/生产性能/医学语义质量。正式manifest/lock逐字节保持，SHA256仍7EB9F27E43DAB21E8D811F1AE5E768D2A3C936A807733C022BAEDBD438F06CDB。入库commit后如关闭或输出失败，CLI可能退出1而写入已完成，文档说明需按幂等重入核对，不宣称过程失败等于数据库回滚。

下一步建议：**P1-11：FastAPI入库与问答入口**，待用户指定后先细化SPEC，本次停止。Phase1的API/飞书、真实付费整链路、医学人工审查及阶段完成学习材料尚未完成，不标记Phase1验收。

交付核对：`python .artifacts/p1-10-20261027-01/audit-delivery.py`通过。43份Markdown、284个本地链接/锚点与十一节SPEC完整；17份交付文件Git空白检查通过。58份既有Python文件仅cli.py和导入审计修改，其他核心/迁移保持；当前30源码/29测试文件/3迁移Python文件。manifest/lock逐字节不变，97个唯一包兼容；43目标/625默认/1实际E5-PG-HTTP替身、11包基础环境10项CLI检查证据存在。数据库0残留fixture且容器停止、卷保留；历史P1-08/09交付证据保留。交付及根层文本证据无密钥格式值，用户.env未读取且与测试密码文件均被忽略。delivery-audit.json/txt保存结果，无提交操作。


## P1-11 本次执行（2026-10-27）

执行前读取AGENTS/PROJECT、MVP/架构、P1-10及现有CLI/装配/业务DTO、资源与测试。保存63份既有Python文件哈希及原manifest/lock，先冻结[十一节SPEC](specs/tasks/p1-11-fastapi.md)，明确文件、HTTP契约/目录权限/容量/关闭与测试，再写实际RED。沿用用户撤销草案后的基础RAG，不恢复四节点/RAGAS/LangSmith修订或P1-10A–E任务。

新增生产api.py与api_runtime.py，复用原入库/检索/问答服务及DTO，没有改动CLI或任何既有核心/适配器/迁移。测试新增tests/integration/test_api.py、test_api_pipeline.py及tests/unit/test_api_runtime.py，修改test_package.py加入2个导入参数并阻止导入FastAPI/Uvicorn。新增任务SPEC和api.md；更新pyproject/uv.lock、.env.example、README/总体/MVP/架构/技术选型/测试策略/开发计划以及CLI/RAG说明。没有添加业务后台任务、Redis、飞书或Docker服务镜像。

官方复核FastAPI0.162.0与Uvicorn0.54.0均Python>=3.10，实际Python3.12.15安装/类型/运行通过；api extra明确固定这两项及已有HTTPX0.28.1，使用最小发行。FastAPI官方PyPI完整元数据保存fastapi-pypi.json；urllib直接读取Uvicorn元数据共3次TLS EOF，没有关闭TLS验证，改由官方PyPI web工具核验0.54.0、>=3.10及依赖，结果来源说明保存在uvicorn-metadata-verification.json。原www.uvicorn.org/settings读取timeout，改读官方uvicorn.dev/settings成功。当前4个新增包含Starlette1.10.0及FastAPI依赖opentelemetry-api1.45.1，没有安装遥测SDK/导出器或standard全家桶；103条正式锁、101个当前安装唯一包，旧99条锁的名称/版本全部保持。

证据目录 `.artifacts/p1-11-20261027-01/`。下表python为`.venv/Scripts/python.exe`；每轮pytest保存/清除PYTEST_ADDOPTS及PYTEST_PLUGINS并finally恢复，使用独立`--basetemp`和`-o cache_dir`，TEMP/CACHE为本轮证据下相应目录。真实模型进程OMP/MKL临时设2并恢复。

| 顺序 | 实际命令/操作 | 结果及证据 |
| --- | --- | --- |
| HTTP RED | `python -m pytest tests/integration/test_api.py -q --basetemp=TEMP -o cache_dir=CACHE` | 34 errors，1.34s；red.txt，因新api模块缺失，fixture失败；不是环境安装故障 |
| 依赖 | `python -m uv lock --system-certs`；`python -m uv sync --locked --extra ml --extra db --extra rag --extra api --system-certs` | 正式锁与实际安装成功；lock-resolution.txt、install.txt，既有环境/共享Conda未升级 |
| 运行时RED | `python -m pytest tests/unit/test_api_runtime.py -q --basetemp=TEMP -o cache_dir=CACHE` | 9 failed，1.46s；runtime-red.txt，因api_runtime模块尚未实现 |
| 首次GREEN尝试 | 上述两个目标文件命令，独立TEMP/CACHE | 42 passed /1 failed，4.47s；green.txt。测试同时缺JSON Content-Type并设置超大Content-Length，先触发415；为该体积用例补正确媒体类型，保留413断言，不改生产判定顺序 |
| GREEN | 同上，独立TEMP/CACHE | 43 passed，5.42s；green-final.txt |
| 关闭/文档补充RED | 两文件加`-k "shutdown_failure or openapi_describes"` | 2 failed /43 deselected，1.72s；privacy-red.txt。关闭异常回显原始文字、OpenAPI仍是框架默认422 schema；先复现再修复 |
| 关闭/文档GREEN | 两文件完整目标命令 | 45 passed，5.58s；target.txt。关闭失败固定shutdown_failed，统一ApiError OpenAPI |
| 扩展目标 | 两文件完整目标命令 | 58 passed，4.71s；target-complete.txt。增加批次六状态、坏header/JSON、无lifespan/not_ready、解析逃逸、关闭等待等 |
| 框架边界RED | `python -m pytest tests/integration/test_api.py -k "unhandled_framework or non_utf8_json" -q --basetemp=TEMP -o cache_dir=CACHE` | 2 failed /47 deselected，1.81s；framework-red.txt。默认未知500及非UTF8 JSON400未采用API错误契约，补统一处理且不泄漏输入 |
| 最终目标GREEN | 两文件完整目标命令 | 60 passed，5.07s；target-final.txt，49 HTTP+11运行时场景 |
| 首轮默认回归 | `python -m pytest -q --basetemp=TEMP -o cache_dir=CACHE --cov=clinical_agent.api --cov=clinical_agent.api_runtime --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-11-20261027-01/coverage.json` | 684 passed /1 failed /80 deselected，139.63s；regression-first.txt/coverage-first.json。与实际模型验收并行时，旧CLI unsupported子进程超过原10秒；没有放宽测试。该轮是最终2项边界测试加入前的685项集合，不算TDD RED |
| 最终默认回归 | 同上，独立final TEMP/CACHE，无模型验收并行负载 | 687 passed /80 deselected，110.00s；regression.txt/coverage.json。新增两模块含分支综合97%，不含独立外部/CLI子进程覆盖采集，不是全项目覆盖率；旧CLI超时断言保持 |
| 真实网络/业务准备 | 专用Compose `up -d --wait postgres`；`python -m alembic upgrade head` | 独立空库迁移至p107_0002；compose-start.txt/migration.txt。API不自动迁移 |
| 真实API/E5/PG | `python -m pytest tests/integration/test_api_pipeline.py -m "database and external" -q --basetemp=TEMP -o cache_dir=CACHE` | 1 passed，75.32s；real-api.txt/result.json。实际Uvicorn TCP+E5/PG，LLM明确为HTTPX MockTransport，生命周期仅加载模型一次 |
| 静态/依赖 | `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src`；`python -m uv lock --check --offline`；`python -m uv pip check` | Ruff/68文件格式/32源码类型、103条锁/101包兼容通过；ruff/format/mypy/lock-check/pip-check.txt。首次Ruff排版/导入问题格式化后通过，无全局放宽 |
| 干净基础环境 | `UV_PROJECT_ENVIRONMENT=.artifacts/p1-11-20261027-01/base-venv`；`python -m uv sync --locked --no-dev --offline --no-python-downloads --python .tools/python/cpython-3.12.15-windows-x86_64-none/python.exe` | 11包、无api/db/ml/rag，api/api_runtime可导入，模块help/ask help/doctor均通过；base-install/base-smoke.txt |
| 干净API环境 | 同上，目标api-venv并加`--extra api` | 23包、无torch/SQLAlchemy/LangGraph，注入业务替身的实际FastAPI lifespan/ready/questions通过；api-install/api-smoke.txt。不是实际业务或新wheel验收 |
| DB收尾 | `python .artifacts/p1-11-20261027-01/verify-database.py`；本次project `compose ... stop postgres` | head=p107_0002、vector(768)、0文献/0片段；database-audit.json/txt；容器exited，卷保留，compose-stop/container-final-state.txt |

API只接受服务器固定import_root内相对文件路径，拒绝客户端配置目录/凭据、穿越/解析逃逸，不做上传或公网授权。X-Request-ID经UUID校验，统一响应header/JSON，错误无原始input/body/路径/异常。16KiB声明与实际ASGI分片大小、10秒body读取预算、JSON媒体类型边界明确；超出业务容量503并含Retry-After。QuestionBody复用原检索契约，答案保留kind、来源/位置及limitations，所有有结构的导入批次结果200但逐条状态必须检查。

标准ThreadPoolExecutor加非阻塞接纳，默认2、最多4，限制实际运行/已提交工作而非无限排队。取消await不等于取消运行中的线程，容量由底层Future完成回调回收；关闭先停止接纳、等待实际工作，再关HTTP/engine，服务不承诺硬杀线程/硬关闭期限。健康探针不占业务池或调用外部服务；ready只说明生命周期资源已装配，不保证上游当前连通。边界护栏使用少量ASGI代码，路由/校验/OpenAPI/HTTP服务均用成熟组件，没有自建Web框架。

真实验收使用project=clinical-agent-p111-20261027、库clinical_agent_test_p111_20261027、127.0.0.1:55432、随机测试密码及显式reset；Compose始终--env-file .env.example、独立docker-config与已知Linux engine pipe。按工具自动审批访问本机，不读取用户.env或默认Docker凭据，不连接现有用户库。实际启动Uvicorn0.54.0/FastAPI0.162.0并用HTTPX通过loopback TCP调用：PDF导入/重入/XML导入为imported/already_present/imported，2文献/2片段，问答answered、一次HTTP替身请求且chunk关联一致，模型仅启动加载一次。socket只允许loopback，未使用旧聊天密钥/发起付费LLM请求，不能称真实DeepSeek整链路。结束只停本次容器，不删除卷/关闭其他资源。

真实TCP集成后新增的最后两项变更仅为框架400/500错误处理，已由最终实际FastAPI测试及完整回归覆盖，未为此重复启动模型/数据库。Path.resolve逃逸使用明确替身，未验证Windows真实符号链接创建权限。未新增Docker镜像/服务部署、构建wheel、Linux部署、生产吞吐或医学专家语义评价。103条正式锁SHA256=7DFFFAB9F236157807D31DAEC5BB9957B85C3C179A9C94A5BF0001092F832227；旧包版本保持。

下一步建议：**P1-12：飞书消息契约与事件过滤**，待用户指定后细化SPEC，本次停止。Phase1仍有飞书、真实付费整链路/医学人工审查及完整阶段学习验收，不标记Phase1完成，已撤销四节点草案保持撤销。

交付核对：`python .artifacts/p1-11-20261027-01/audit-delivery.py`通过。45份Markdown、304个本地链接/锚点、十一节SPEC完整；20份交付文件Git空白检查通过。63份既有Python文件仅导入审计修改，原CLI/核心/迁移保持；32源码/32测试文件/3迁移Python文件。manifest仅新增api extra，旧锁版本保持，103条锁/101个安装唯一包；60目标/687默认/1实际TCP-E5-PG-HTTP替身、11包基础/23包api-only证据存在。数据库0残留fixture，容器停止、卷保留；用户.env未读取且与测试密码文件均忽略，交付/证据无密钥格式值。已撤销草案及其引用保持不存在，历史交付不改写。delivery-audit.json/txt保存结果，无提交操作。


## P1-12 本次执行（2026-10-27）

按顺序读取AGENTS.md.txt/PROJECT.md.txt、当前进度、MVP/架构相关边界、核心DTO及导入测试。PROJECT.md.txt的“Phase0”是旧状态，以本进度及仓库源码为当前事实。开始时Git干净，尚无飞书源码、测试及详细任务SPEC；先新增[十一节SPEC](specs/tasks/p1-12-feishu-events.md)，冻结纯事件过滤范围，再写测试观察RED，不依赖历史聊天或扩展到机器人运行时。

新增src/feishu/__init__.py及events.py：EventPolicy、MessageEnvelope、EventDecision和filter_event。处理解码字典，过滤目标应用/事件类型/自身/机器人/非文本/不支持会话；单聊允许、群聊要求真实open_id对应的完整@占位符。校验JSON/Unicode/重复键、32KiB内容、最终1–4000字符及最多100 mentions。message_id优先、event_id回退，三元组区分应用及ID类型，UUID5稳定关联；accepted只代表过滤通过，重复事件仍accepted，不冒充原子去重。只用现有Pydantic，不读取环境或创建资源/调用研究服务。

新增tests/unit/test_feishu_events.py，修改test_package.py增加feishu及feishu.events的隔离导入并按顶层包核对源码路径。新增任务SPEC、feishu-events.md，更新README、总体/MVP/架构/测试策略及本进度，共12份交付文件。原clinical_agent源码、迁移、pyproject.toml及uv.lock均未修改；未修改用户规则或过时历史记录。

证据目录`.artifacts/p1-12-20261027-01/`。以下python均为`.venv/Scripts/python.exe`；每轮pytest保存/清理PYTEST_ADDOPTS与PYTEST_PLUGINS并finally恢复，使用独立`--basetemp`及`-o cache_dir`。

| 实际命令/操作 | 结果与证据 |
| --- | --- |
| `python -m pytest tests/unit/test_feishu_events.py -q`（red-temp/red-cache） | 72 failed，2.13s；red.txt，均因缺少feishu模块，非环境故障 |
| 同目标命令（green-temp/green-cache） | 72 passed，0.28s；green.txt |
| `python -m pytest tests/unit/test_feishu_events.py tests/unit/test_package.py -q`（target-temp/target-cache） | 122 passed，42.58s；target.txt：扩展88事件场景+34隔离导入 |
| `python -m pytest -q --cov=feishu.events --cov-branch --cov-report=term-missing --cov-report=json:.artifacts/p1-12-20261027-01/coverage.json`（regression-temp/regression-cache） | 777 passed /80 deselected，105.87s；regression.txt/coverage.json。仅新事件模块含分支综合99%，两行防御性ValidationError兜底未触发；不是全项目覆盖率 |
| `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src` | 全部通过，71个格式文件/34源码；ruff.txt、format.txt、mypy.txt。初轮未使用导入/排版及Literal.__args__类型错误已修正为get_args，无放宽规则 |
| `python -m uv lock --check --offline`；`python -m uv pip check`（UV_CACHE_DIR临时设仓库.research-cache/uv并恢复） | 103条锁、101已安装包兼容通过；lock-check.txt、pip-check.txt。初轮默认用户缓存目录无写权限，改用项目缓存后成功，无依赖变更 |
| 既有P1-11基础环境`python -I -c <导入与无重依赖断言>` | base-import.txt通过；复用原基础环境，仅验证新模块导入及策略构造，不声称本轮新建环境/构建wheel |
| 本地链接/围栏/空白、十一节SPEC及文档Python示例执行；`git diff --check` | 文档示例与静态交付核查通过；delivery-audit.txt、diff-check.txt。UTF8文档链接有效，原核心/迁移/manifest/lock无diff |

事件字段参照SPEC所链飞书官方文档；官方正文直读为空壳，搜索索引提供事件头/sender等结构，未使用参考项目代码或宣称真实SDK验证。未安装SDK/Redis、无网络业务调用、无凭据读取、无数据库/模型/LLM/飞书真实服务测试。SDK认证/对象映射、长连接、去重租约、工作池及发送仍待对应任务；本过滤器不能直接充当公网Webhook。当前任务无遗留阻塞，Phase1仍未整体验收，不提前生成完整阶段学习材料。

下一任务建议：**P1-13：Redis原子消息去重**，待用户指定后细化SPEC。本次停止，不自动开发后续模块；不创建提交。


## 文档一致性核对（2026-10-27，P1-12后）

按用户要求核对原49份Markdown/项目规则文本，完整问题及处理见[核对报告](documentation-audit.md)。明确G/P1-F/P1-T/P1开发任务四类编号，MVP的P1-T11不是第11个开发任务；Redis去重属于P1-F07、P1-T08/09/10。补齐P1-13–17规划但未细化SPEC、未实施，保留Phase 0–9边界。同步PROJECT/README/架构/技术基线/使用说明，区分历史任务契约、旧计数和当前状态；不改写旧验收结论。

验证：原49份修订后文档374个本地链接/锚点及11段Python示例语法通过，新增报告及引用后全量复核结果见`.artifacts/docs-audit-20261027/verification.json`。`python -m pytest --collect-only -q`为777/857 collected、80 deselected，0.72秒，仅收集，不冒充本轮业务测试通过。73份既有源码/测试/迁移/manifest/lock哈希与本轮开始一致；`git diff --check`检查当前变更。证据目录`.artifacts/docs-audit-20261027/`。

仍待闭环：原Python构建升级/外部业务启用前重核要求、飞书实际运行链路、真实E5/PG/LLM完整链路、医学人工审查及完整Phase 1学习/验收。无新代码、依赖或环境升级，不重新执行P1-12，不开始P1-13。


## P1-13 本次执行（2026-10-27）

按AGENTS.md.txt/PROJECT.md.txt → 当前开发进度 → MVP/既定架构 → P1-12消息DTO与隔离测试顺序核对，当前仓库只有纯事件过滤，无P1-13详细SPEC或Redis实现。保留开始时已有的大量未提交文档/P1-12改动；不依赖聊天记录、不重构已定架构。先新增[十一节SPEC](specs/tasks/p1-13-redis-dedup.md)，再写失败测试、最小实现、边界RED修复和完整回归。

新增src/feishu/dedup.py：规范身份JSON的SHA256版本键；SET NX PX原子占位；UUID4 owner；Redis TIME固定总期限；单键Lua原子check/renew/complete/release。renew不延长总期限，complete使用独立短期TTL，旧owner不能删除/修改新租约。Redis错误/未知响应固定unavailable，无内存降级、无自动重试、无盲删；响应丢失即使服务端已占位也不继续。工厂显式URL、1秒连接/读超时、最多16连接、禁用重试，拒绝URL参数/片段及非法数据库路径；模块导入无Redis/环境/网络副作用。

依赖仅新增dedup extra的redis8.1.0（Python>=3.10，MIT，官方PyPI核查）；uv.lock增加一个包，既有版本保持，104条锁/102个当前安装包。采用本机已有Redis7.4.11镜像执行隔离测试，未新部署生产Redis8；只用基础Lua/SET/TTL，不依赖8系列新命令。没有启用外部业务/升级Python构建；原Python构建升级前置事项继续留给外部业务/部署启用前闭环。

文件范围：新增模块、tests/unit/test_feishu_dedup.py（76项）、tests/integration/test_feishu_dedup_redis.py（12项）、任务SPEC和docs/feishu-dedup.md；test_package.py只追加feishu.dedup隔离导入；pyproject.toml/uv.lock增加可选Redis依赖与专用集成标记；同步PROJECT、README、MVP、架构、技术基线、事件说明、测试策略及本进度。没有修改既有核心业务/事件过滤实现/迁移/生产Compose，不创建提交。

证据目录`.artifacts/p1-13-20261027-01/`。命令中的python为`.venv/Scripts/python.exe`；每轮pytest清理PYTEST_ADDOPTS/PYTEST_PLUGINS并finally恢复，使用独立basetemp/cache，Redis URL也恢复。

| 实际命令/操作 | 结果与证据 |
| --- | --- |
| `python -m pytest tests/unit/test_feishu_dedup.py -q` | 首次72 failed/1.55s；red.txt。尚无dedup及Redis依赖，部分故障用例因缺Redis依赖失败，不能全部当作纯功能RED |
| 仅增加可选依赖/标记后，`python -m pytest tests/unit/test_feishu_dedup.py tests/integration/test_feishu_dedup_redis.py -m "not external and not database" -q` | 73 failed/8 errors，2.59s；red-final.txt。依赖已就绪，全部因缺少feishu.dedup实现，是有效功能RED |
| 同目标命令，注入专用Redis URL | 81 passed，3.83s；green.txt（最初72单元+9真实Redis） |
| 扩展目标加test_feishu_events.py/test_package.py，采集模块覆盖 | 210 passed/1 failed，47.35s；target.txt。新增非法数据库路径用例发现redis-py静默回退，没有放宽断言，补工厂前置校验 |
| 最终去重两个目标文件，同-m选择，`--cov=feishu.dedup --cov-branch --cov-report=term-missing --cov-report=json:.../coverage-final.json` | 88 passed，5.23s；target-final.txt。76单元+12真实Redis；Python模块含分支综合98%，工厂异常兜底两行未覆盖；该百分比不覆盖Lua语句，Lua行为由真实Redis测试验证 |
| `python -m pytest -q` | 854 passed/92 deselected，86.73s；regression.txt。包含原事件过滤及35项隔离导入；默认排除80项既有外部/DB测试及12项Redis集成，Redis已经独立执行，不以deselected冒充通过 |
| `python -m ruff check src tests alembic`；`python -m ruff format --check src tests alembic`；`python -m mypy src` | 全部通过；ruff-final.txt/format-final.txt/mypy-final.txt，74格式文件/35源码；首轮导入/排版问题只修新增文件，未放宽规则 |
| `python -m uv lock --check --offline`；`python -m uv pip check` | 104条锁、102已安装包兼容通过；lock-check.txt/pip-check.txt。UV_CACHE_DIR临时设项目研究缓存并恢复；正式锁只增加Redis |
| 专用容器启动/实际服务核验/收尾 | Redis7.4.11、12独立客户端并发同身份仅一个owner；过期/续租/总期限/完成/释放/旧owner/损坏键/拒绝连接/已写入但响应丢失等通过。redis-audit.json确认0残留键；redis-image.txt/redis-stop.txt/redis-final-state.txt记录digest与exited |

真实Redis使用本次容器`clinical-agent-p113-20261027`（任务标签p1-13）、127.0.0.1:53806、无卷/快照/AOF；镜像`redis@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499`。Docker指定独立配置与本机Linux engine pipe，不读用户.env/默认Docker凭据；fixture只清理本次UUID前缀，未执行FLUSHALL/FLUSHDB；核实标签后只停止本次容器，不影响其他服务。并发通过Barrier同步12个独立客户端，不把Fake或串行读写当成原子性证明。

交付核对：10份相关文档的212个本地链接均存在，围栏闭合、任务SPEC十一节完整；旧锁定版本全部保持，唯一新增包Redis；delivery-audit.json保存核查结果。git diff --check通过（只有既有文件LF/CRLF提示），新增源码/测试/文档无尾随空白。

P1-13无任务内遗留阻塞。局限：短期租约不是exactly-once；失去租约/故障的调用方必须停止业务，发送前再check，检查和远端发送之间无法跨系统原子化。工作池/续租调度、实际RAG次数、发送未知结果和SDK收发尚未实现，满载联动须由P1-14补齐；生产Compose/外部业务、Python构建前置重核、真实完整模型/PG/LLM链路、医学人工审查及Phase1学习材料仍待后续任务。不因此标记Phase1完成。

下一任务：**P1-14：飞书有界任务分派与服务复用**（仍仅规划，未细化SPEC/未开始）。本次停止，不自动进入。


## P1-14 本次执行（2026-10-27）

按项目规则AGENTS.md.txt/PROJECT.md.txt → 当前进度 → MVP/任务SPEC → 已有相关源码与测试顺序核对。当前仓库是唯一代码依据；已有P1-12事件契约、P1-13去重及ResearchService，没有P1-14 SPEC或worker。先补[十一节SPEC](specs/tasks/p1-14-feishu-worker.md)，再写失败测试，最小实现后验证。保留开始时已有文档、依赖、P1-12/13等未提交改动；不重新设计核心架构，不进入P1-15。

新增src/feishu/worker.py：标准ThreadPoolExecutor、Semaphore和Condition/RLock；容量先于Redis acquire；重复/故障/满载不调用研究；提交失败清理自己的租约。实际Future结束及清理回调才释放容量，调用方等待超时/cancel不提前放行运行中的线程；未开始的取消释放一次。显式注入共享ResearchPort，以消息text/request_id构造独立QuestionRequest，复用已有ResearchService和LangGraph，不改RAG/事件/去重实现。研究前后检查owner及处理预算，非法输出/服务异常转固定research_failed；无凭据/原文异常回显。

定义非阻塞DeliveryPort交接，携带合法答案/错误、租约及单调发送截止时间；队列拒绝时owner release，交接异常为unknown并保留TTL，不盲删/重试。worker不提前complete；P1-15 sender须出队再核对deadline/owner并按实际投递结果处理完成标记。默认研究90秒、交接发送15秒及5秒裕量，要求显式至少110秒Redis租期；测试用120秒。采用覆盖预算的固定租约，无续租调度线程，不改变P1-13默认策略。

close停止接纳、停止线程池接收新提交，并有期限等待实际工作及清理回调；返回False不杀线程、不关闭借用资源，调用方必须继续等待。取得接纳锁前已在进行的Redis调用受其自身1秒I/O超时约束。排空研究后还需排空sender才能关闭共享服务/Redis，生产装配属于P1-16。

文件范围：新增worker.py、tests/unit/test_feishu_worker.py、任务SPEC、docs/feishu-worker.md；test_package.py只新增worker隔离导入；更新PROJECT、README、MVP、架构、测试策略、去重说明及本进度。无新依赖、迁移、核心业务变更、SDK、生产Compose或提交。

证据目录`.artifacts/p1-14-20261027/`；python均为仓库`.venv/Scripts/python.exe`。pytest每轮清理并finally恢复PYTEST_ADDOPTS/PYTEST_PLUGINS，独立basetemp/cache；uv临时使用项目研究缓存并恢复UV_CACHE_DIR。

| 实际操作 | 结果 |
| --- | --- |
| `python -m pytest tests/unit/test_feishu_worker.py -q`，首次 | 12 failed/16 errors，0.90秒，均缺feishu.worker；red.txt，真实功能RED |
| 最小实现后同目标测试 | 28 passed，1.22秒；green.txt |
| 扩展取消/快照/容量/故障/真实图证据测试 | 41 passed/1 failed，2.07秒；boundary.txt。失败为测试误用不存在的citations属性，依当前ResearchAnswer.sources修正；不算功能RED |
| 新增发送截止时间测试 | 42 passed/1 failed，1.88秒；deadline-red.txt，Delivery缺deadline的真实功能RED；补字段与有界期限后通过 |
| worker/events/dedup/package联合测试，含`--cov=feishu.worker --cov-branch` | 243 passed，47.28秒；target.txt/coverage.json，worker 133语句/26分支均覆盖，100%；不代表真实服务或医学语义验收 |
| 最终`python -m pytest -q` | 898 passed/92 deselected，89.32秒；regression.txt。含43 worker目标及36隔离导入；最终真实图生成测试用Barrier强制两请求重叠，直接服务调用完整DTO一致，问题/来源/定位不串请求 |
| `python -m ruff check src tests alembic`、`python -m ruff format --check src tests alembic`、`python -m mypy src` | 全通过；ruff.txt/format.txt/mypy-final.txt，76格式文件/36源码。只修新增代码排版及已校验身份的类型标注，未放宽规则 |
| `python -m uv lock --check --offline`、`python -m uv pip check` | 全通过；lock-check.txt/pip-check.txt，104锁定包/102已安装包，无依赖修改 |

独立真实Redis脚本仍以P1-13记录为证，本轮未重跑真实Redis，未连接模型/PG/LLM/飞书；Fake仅验证分派协议联动，不冒充Redis原子性。真实线程与真实LangGraph已运行，检索/生成端口使用合成证据替身。默认排除的92项不能当作通过。真实Redis与worker组合、官方发送、长连接、生产生命周期和全链路验收仍待后续任务。

P1-14任务内无阻塞。限制：同步阻塞调用不能强杀，容量只能等其实际结束；发送交接必须遵守非阻塞有界端口契约；租约与网络发送没有跨系统原子性，不是exactly-once。Phase1未整体验收，原Python构建升级前置核查、真实完整模型/PG/LLM链路、医学人工审查及Phase1学习材料继续保留。下一任务：**P1-15 飞书文本渲染与受限发送**（规划，未细化SPEC/未开始）；本次停止，不自动进入。

交付核对：本任务9份相关文档的197个本地链接存在，Markdown围栏闭合、SPEC十一节齐全，新文件无尾随空白；git diff --check通过（仅已有文件LF/CRLF提示）。delivery-audit.json保存代码/测试/SPEC/说明哈希与核查结果。


## P1-15 本次执行（2026-10-27）

按仓库AGENTS.md.txt/PROJECT.md.txt → 当前开发进度 → MVP/任务SPEC → 相关源码和测试顺序核对。当前仓库是唯一代码依据；已有events/dedup/worker与DeliveryPort，尚无P1-15 SPEC、sender或目标测试。先补十一节[SPEC](specs/tasks/p1-15-feishu-sender.md)，再真实RED/GREEN；沿用既有五模块架构，无研究服务/Redis Lua修改，无新依赖、迁移、SDK、生产入口、Compose或提交。保留启动时全部已有未提交改动。

新增src/feishu/sender.py：ResearchAnswer重校验，渲染结论类型/来源编号/chunk、结论与全局局限、文献元数据/范围/document/hash及页码/摘要节和字符区间；不编造元数据、不输出本地URI，尖括号等转为全角防止at标签，来源URL仅允许无凭据HTTP(S)。内部content 24000字节/完整外层30000字节，双层JSON转义计入；超长整体替换固定提示，避免断裂引用，不分段发送。无证据不解释为无效。

Sender以标准Queue、锁内在途计数及单个标准线程承接DeliveryPort。容量含执行中与排队，满载/关闭非阻塞False不接管租约；有效交接重校验并深复制。默认8项、发送5秒、通知5秒；research_failed/busy/unavailable/invalid_input固定通知共用容量，无伪造owner。出队、渲染后及token取得后临HTTP再检查owner/deadline。真实执行和清理结束才释放发送容量。

OfficialMessageAPI使用已有锁定httpx 0.28.1调用官方REST（有message_id为reply，仅event_id为chat_id create），不另建鉴权缓存；借用client和有期限token提供者，不读密钥/配置、不关闭借用资源。token/SDK长连接与生产装配仍待P1-16。注入客户端必须禁用重试/重定向，不附默认鉴权/参数或敏感日志hooks。每项最多一次消息POST，明确成功才owner complete；确定未发/明确失败owner release；未知/失租/Redis不可用保留TTL，无递归错误或重试。标准logger仅记录request_id及固定结果字段，生产handler装配留P1-16。

close有期限等待实际排空，False不杀线程、不能提前关闭借用资源；先研究池排空，再sender，最后客户端。httpx阶段超时不是硬墙钟总期限，已开始调用无法撤回，晚到确认仍尝试complete并记录实际结果；Redis/HTTP无跨系统原子性，不承诺exactly-once。

文件范围：新增sender.py、tests/unit/test_feishu_sender.py、任务SPEC和docs/feishu-sender.md；test_package.py只加sender隔离导入；更新PROJECT、README、开发进度、MVP、架构、测试策略、worker/dedup说明。任务学习说明见sender文档；Phase1仍未整体验收，不提前生成完整阶段学习材料。

所有Python命令使用仓库.venv/Scripts/python.exe；证据`.artifacts/p1-15-20261027/`。执行子进程移除PYTEST_ADDOPTS/PYTEST_PLUGINS（父环境不修改），每轮独立basetemp/cache；UV_CACHE_DIR仅在子进程指向研究缓存。初始lint控制台曾因GBK无法打印测试中的emoji，日志已写入；随后显式UTF-8输出并完成复核。没有因输出编码问题跳过测试。

| 实际检查 | 结果与证据 |
| --- | --- |
| 首次目标RED | 35 failed/27 errors，2.35秒，均缺feishu.sender；red.txt |
| 最小实现GREEN | 62 passed，2.34秒；green.txt |
| 扩展外层预算RED | 70 passed/1 failed，3.53秒；outer-red.txt。引号使content在外层再次转义而超预算，属真实功能缺口 |
| 外层预算修复及边界GREEN | 71 passed，3.89秒；boundary-green.txt |
| 正常/错误Dispatcher→Sender联动、完整飞书/隔离导入联合 | 316 passed，52.52秒；target.txt，含72 sender目标及37包隔离导入；sender 232语句/76分支，综合覆盖96%，coverage.json（不等同于所有异常或医学语义已验收） |
| 最终默认pytest | 971 passed/92 deselected，90.98秒；regression.txt。排除的外部服务/数据库/Redis/性能项不算通过 |
| ruff check、ruff format --check src tests alembic、mypy src | 全通过；ruff.txt/format.txt/mypy.txt，78格式文件、37源码。仅修新文件排版和maketrans映射类型，不放宽规则 |
| uv lock --check --offline、uv pip check | 全通过；lock-check.txt/pip-check.txt，104锁定包/102安装包；无依赖/锁变更 |

协议依据为2026-10-27核查的飞书官方reply/create与text结构文档（链接见SPEC及发送说明）；网页正文部分为空壳，文本结构搜索索引可核对content和at语义；离线MockTransport才是本项目请求结构的执行证据。不使用第三方镜像作为技术依据，不宣称真实SDK或真实租户验证。

真实Queue/线程/Event与Dispatcher已执行，Redis和消息HTTP/token是明确替身；全部来源为合成数据。本轮未连接真实飞书/Redis/模型/PG/LLM，无真实用户消息发送；未新增真实租户收发的验收结论。任务内无阻塞；生产token提供者、官方SDK长连接/接收映射、日志handler与资源装配/Compose留P1-16。真实完整模型/PG/LLM链路、医学人工审查、原Python构建前置核查及Phase1学习材料留阶段验收。下一任务：**P1-16 官方SDK长连接、装配与Compose入口**（规划，未细化/未开始）；本次完成P1-15后停止。

交付核对：10份相关文档的212个本地链接可达，围栏闭合、SPEC十一节齐全，新文件无尾随空白；git diff --check通过（仅已有文件换行转换提示）。代码/测试/说明/SPEC哈希与检查结果保存delivery-audit.json。


## P1-16 本次执行（2026-10-27）

按仓库AGENTS.md.txt/PROJECT.md.txt → 开发进度 → MVP/当前任务SPEC → 相关源码测试顺序核对。仓库原无P1-16详细SPEC/main.py，已先补十一节SPEC再TDD；保留全部已有未提交改动，不依赖历史聊天，不改研究服务或去重Lua，不进入P1-17。

实现第五模块src/feishu/main.py：官方SDK DTO显式映射至既有filter_event、固定通知路由、按deadline单次获取官方tenant token（无新缓存）、共享open_research/Redis/HTTP/Sender/Dispatcher装配、启动失败回滚、worker→sender→客户端逆序排空。超时不提前关闭依赖，CLI继续有期限排空；日志只含固定事件/UTC时间/request_id/固定状态，关闭异常也不回显原文。单独入口clinical-feishu与python -m feishu.main，help/导入不创建外部资源。

官方lark-oapi固定1.7.5；下载wheel核查后将缺timeout的SDK发现请求集中适配为5秒HTTP，并复用其EndpointResp/ClientConfig、帧/心跳/重连；_connect/_ping_loop/_disconnect与SDK模块loop是明确私有兼容点，运行拒绝其他版本。SIGINT/SIGTERM、后台任务终止、任务取消及信号/日志状态恢复均有离线测试。正式锁新增SDK/pycryptodome，websockets由17.3降至SDK兼容的15.0.1；未扩大为新框架。

Dockerfile以uv.lock安装api/rag/db/ml/feishu共用镜像，非root用户、只读模型挂载、构建上下文允许清单；Compose保留postgres并新增Redis、API与feishu_bot，显式profiles、依赖健康检查、API ready检查和130秒停止宽限期。不自动迁移/导入/下载模型，不启动普通用户机器人。

文件范围：新增main.py、tests/unit/test_feishu_main.py、tests/unit/test_feishu_deployment.py、显式external/redis集成测试、任务SPEC、docs/feishu-runtime.md、Dockerfile/.dockerignore；更新Compose、pyproject/uv.lock、隔离导入测试、README/PROJECT/环境样例、MVP/架构/发送/工作池/去重/测试策略及本进度。任务级学习/取舍/执行流程见运行说明，Phase1六份阶段学习材料仍留P1-17。

项目解释器.venv/Scripts/python.exe；证据.artifacts/p1-16-20261027。默认检查子进程移除PYTEST_ADDOPTS/PYTEST_PLUGINS，独立basetemp/cache；UTF-8输出。最初审批因额度不可用而未执行写入，用户继续后重试成功，不绕过审批。初次同步尚未结束时的GREEN尝试产生SDK导入失败，等待安装完成后重跑；真实冷导入栈诊断显示生成模块导入耗时。早期测试替身缺future及合成protobuf帧缺四个必填字段已修正，未通过放宽断言使其通过。

| 实际检查 | 结果与证据 |
| --- | --- |
| 初始目标RED | 41 failed，1.45秒；red.txt，全部缺feishu.main |
| 部署RED | 2 failed，0.42秒；deploy-red.txt，Compose缺服务/Dockerfile不存在 |
| SDK后台终止RED | 1 failed，2.08秒；background-red.txt，原入口一直等待；修复后有明确固定错误退出 |
| 日志/关闭隐私RED | 2 failed，1.00秒；privacy-red.txt，缺UTC字段与原始清理异常传播；已修复 |
| 初步目标GREEN | 47 passed，20.46秒；target-green.txt；后补3项协议帧/日志/关闭测试 |
| 最终飞书/包隔离联合 | 367 passed，68.27秒；target-pass.txt，含48运行时、2部署、38包隔离及全部既有飞书测试 |
| 最终默认回归 | 1022 passed, 93 deselected, 1 warning in 106.53s (0:01:46)；regression-delivery.txt；被排除的服务/模型/性能项不算通过 |
| Ruff/格式/mypy | 全通过；ruff-delivery.txt/format-delivery.txt/mypy-delivery.txt，82格式文件、38源码；不放宽规则 |
| 锁与安装一致性 | uv lock --check --offline、uv pip check通过；lock-delivery.txt/pip-delivery.txt，106锁定包、104安装包 |
| Compose config | 通过；compose.json/compose-errors.txt；空env文件+合成凭据，仅结构验证，未泄露真实.env |
| 共享镜像构建 | 实际尝试失败；docker-build.txt，Docker Hub鉴权服务网络超时，尚未下载基础镜像/安装Linux依赖，不声称构建或容器运行通过 |
| 真实官方身份接口 | 用户提供凭据后，经隐藏终端输入执行；auth与bot info均HTTP200/code0。密钥仅在测试进程内存/子进程环境使用，不写代码、文档、日志或配置文件 |
| 真实SDK/Redis/消息冒烟 | 实际1 failed，185.34秒；真实SDK连接已确认，但180秒测试窗口内未收到指定口令（No matching test nonce received），未发生已确认测试回复；不得标真实收发通过；live-external.txt |

真实测试只接纳明确口令P116_SMOKE_20261027，使用临时隔离Redis容器与合成ResearchPort，绝不据此声称验证了真实医学问题/E5/PG/付费LLM链路。早期冒烟就绪钩子误用SDK仅重连时触发的on_reconnected，已停止并修正为实际_connect成功；不把等待或中断记作成功。测试后清理临时Redis和接收进程。SDK自身有datetime/事件循环弃用警告，未全局屏蔽，升级仍须兼容性复验。

未解决：共享镜像构建因Docker Hub网络失败，Linux安装与容器启动/停止尚未验收；真实口令收发也未闭环，不能将P1-16或Phase1标记完整验收。Python构建升级前置核查、真实完整模型/PG/LLM链路、医学支持关系人工审查与Phase1整体验收/学习文档仍留P1-17；本任务不自动开始P1-17。

交付复核：22份本次交付文件的本地链接/围栏、SPEC十一节及无尾随空白已核对；git diff --check修正本次追加段落的EOF空行后通过。文件哈希与结果见delivery-audit.json。临时Redis容器与测试进程已退出，未提交Git commit。


最终真实联调补记：用户重发并核对接收方式后，显式延长窗口至600秒；实际1 failed、606.82秒，已建立SDK连接但仍未收到指定口令/消息事件。不能确认原因是订阅方式、未生效权限、测试目标或其他客户端接收中的哪一项；未声称发送成功。需在开放平台选择使用长连接接收事件，添加im.message.receive_v1并发布所需权限后重新联调。最后证据live-external-600s.txt；接收进程与临时Redis均已清理。

## P1-16 发布后真实收发补验（2026-10-27）

用户在开放平台发布配置后再次执行既有external+redis测试：**1 passed、1个SDK弃用警告，34.38秒**。实际输出依次为P116_LIVE_CONNECTED、P116_LIVE_EVENT accepted/eligible、P116_LIVE_SENT；真实官方SDK收到指定口令，官方reply接口明确成功，真实Redis owner complete返回owned。证据`.artifacts/p1-16-20261027/live-external-published.txt`。旧180/600秒未收到事件的失败保留为当时事实，本次已补齐指定口令收发验收；不能将旧记录当作当前收发状态。

研究端口为明确的合成ResearchPort，仅回复本地范围/合成测试的证据不足文本，未执行真实医学检索、E5/PG/付费LLM完整链路，也未把HTTP成功当成医学正确性。沿用当前实现，没有因联调成功修改核心代码或放宽测试。凭据仅通过隐藏终端输入及进程环境传递，不写源码或证据；运行结束SDK进程及临时隔离Redis已退出。

当前剩余P1-16验收为Linux共享镜像构建、Compose容器启动/停止；不因真实收发成功自动标记部署或Phase1完成。P1-17未开始。

## P1-16 Linux容器最终验收（2026-10-27）

本次完成P1-16剩余验收，以下结论取代此前“镜像网络阻塞/容器待验收”的当前状态；旧失败保留为历史。

Docker直连Hub超时后，只读确认既有本机7890代理可访问官方registry。使用官方google/go-containerregistry的crane v0.22.1（校验官方release SHA256）获取固定python:3.12.15-slim-bookworm及redis:8.2.2-alpine的linux/amd64镜像；未使用不明镜像源、未关闭TLS/摘要检查、未改Docker/系统全局代理。Python源platform manifest为57d96f71de145a98e7ceca18ee4ade77bba4103a33a72dfaea026b23625c6bf0，Redis为3f835dae62fe5012baf5a768293967c93bc09cf9e848d415351dfba04ee87537。导入后以临时HTTP_PROXY/HTTPS_PROXY build args和正式uv.lock构建共用镜像；生产镜像未保留代理或凭据ENV。89个Linux运行包安装并uv pip check通过，CLI help与非root配置通过。

首次Compose脚本在机器人就绪日志上超时，不能算通过。定位发现_LOG=logging.getLogger(__name__)在python -m入口下成为__main__，脱离feishu JSON handler。新增真实runpy别名测试先RED（1 failed/48 deselected，entrypoint-red.txt），固定logger名称为feishu.main后GREEN（1 passed/48 deselected，entrypoint-green.txt）；仅这一行应用修复，不改SDK/研究/去重/发送算法。第二次脚本仍超时，核查是验收辅助脚本仅采集docker logs的stdout，漏掉了JSON日志所在的stderr；修正为日志命令合并两流，未放宽就绪条件，旧失败另存compose-accept-result-initial.json与compose-accept-result-stdout-only.json。修复后368联合（94.44秒）及1023 passed/93 deselected默认回归（155.73秒）通过；Ruff/format（82文件）/mypy（38源码）通过。证据container-fix-*.txt。

最终Compose使用独立项目clinical-p116-accept-20261027、全新测试卷及空env文件，端口通过验收override移除，避免触碰既有数据库/服务。PostgreSQL/Redis健康、现有Alembic迁移、真实E5只读挂载、API runtime ready与空库问答insufficient_evidence/零claims/零sources均通过；未调用付费LLM。生产python -m feishu.main入口加载共享研究装配并连接真实SDK；API/机器人使用同一镜像、UID10001、只读模型。收到SIGTERM后机器人exit_code=0，API exit_code=143且日志明确Application shutdown complete/Finished server process，两者OOMKilled=false。Uvicorn0.54会在优雅关闭后重新抛出已捕获信号，因此Linux API的143可为正常信号退出，不能单独据此判定失败或成功；已按实际源码及关闭日志修正验收判据，旧误判记录另存compose-accept-result-api143.json。随后只删除本次项目的容器、卷及网络，清理断言通过。实际脚本耗时111.28秒，脚本断言通过，不冒称pytest用例数量。

最终应用镜像ID：sha256:013d6909cef814039ea1f610e5bd4f4c1f60fc65e683714d2bde603266e50a9c。证据docker-build-proxy.txt、python-base-pull.txt、redis-base-pull.txt、image-check.json、compose-accept-result.json、compose-accept-commands.json及compose-accept-api/feishu_bot.log。真实口令收发仍以此前live-external-published.txt的1 passed/34.38秒为准（研究为合成替身）；本次生产容器验证启动/连接/停止，不追加真实医学消息。

P1-16任务内无阻塞，Phase1尚未整体验收。真实E5/PG/付费LLM完整研究链路、医学支持关系人工审查、解释器升级前置要求与phase-01六份学习文档仍归P1-17；未自动开始。原有未提交改动保留，未创建Git提交。

## P1-17 本次执行（2026-10-27）

按规则→当前进度→MVP与新细化SPEC→相关源码测试顺序推进；未依赖历史聊天、重做架构或进入Phase2。完成学习材料缺失RED/GREEN；补真实Redis/Dispatcher/Sender组合与真实E5/PG/DeepSeek闭环测试。合成PDF和固定NCBI摘要各一次真实付费请求，累计2次后停止；固定医学样例输出10条claims及逐条人工审查包，用户选择保留待审查，不伪造签署。

补齐docs/learning/phase-01六份教材和demo.py；新增阶段报告、详细SPEC与tests/integration/test_phase1_acceptance.py。安全版本一致性断言先RED，再将.python-version/Dockerfile及正式.venv升级为3.12.16；原环境备份.venv-p117-prior。官方standalone校验、候选独立环境、Linux候选镜像、默认/真实服务复验的实际证据见[阶段报告](phase1-acceptance.md)。未修改现有研究服务、SDK兼容层、Redis Lua或正式依赖锁。

原3.12.15：默认1024 passed/95 deselected、PG74、Redis13、实际E5/CLI/API/入库/检索5、真实合成闭环1通过。3.12.16候选：默认1024、PG74、Redis13、医学闭环1通过；首次模型组合4通过/1加载失败，独立检索通过，串行复验结果见最新报告；mypy旧缓存内部错误改为独立新缓存后38源码通过。真实失败记录保留，不计作成功。正式环境最终检查以.artifacts/p1-17-20261027/final-*.txt为准。

模型组合串行复验仍失败后捕获底层os1455页面文件不足；新增显式真实模型测试夹具，恢复测试patch后gc.collect回收已结束的图/ASGI/模型引用，原五项同进程组合最终5 passed/80.74秒。只修改tests/conftest.py及六个显式模型测试的夹具标记，不修改生产内存/模型配置。mypy最终使用独立缓存。安全解释器引导脚本install-python.ps1固定官方资产SHA256且已实测本地路径。

未解决：真实医学样例的支持关系人工审核仍待签署（用户已明确保留待审查）；因此P1-17/Phase1不标完成，不自动开始Phase2。其他执行结果/升级限制以阶段报告为准。保留原有未提交改动，未创建Git提交。

P1-17最终交付复核：正式Python3.12.16默认回归1025 passed/95 deselected/1 SDK弃用警告（266.94秒），Ruff、84文件格式、38源码mypy、106锁定包/104安装包检查全部通过。3.12.16真实PG74、Redis13、修复后的模型组合5通过；真实LLM两样例各1通过。升级后Linux共享镜像与隔离Compose API迁移/只读E5/空库问答/非root/SIGTERM关闭通过（0次付费调用），所有本轮临时容器/卷/网络已清理；API正常退出143结合完整关闭日志判定。首次Compose辅助日志GBK解码失败保留并修正为UTF-8，未放宽产品判据。医学人工审核仍待签署，P1-17/Phase1保持验收中；不进入Phase2。交付文件链接/围栏/十一节SPEC与git diff --check通过，详delivery-audit.json。
