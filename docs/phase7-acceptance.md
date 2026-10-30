# Phase 7 P7-01 核心报告链路交付与验收记录

2026-10-28（Asia/Shanghai）。核心实现、六份学习材料与合成离线报告已交付；集中验收实际结果如下。**真实模型/真实依赖整链路与独立医学人工支持度复核待完成，不标 Phase 7 全部验收。** 用户本次明确指令开始 Phase 7，复用 Phase 6 技术基线；其真实模型/医学待审状态保留。

## 实现范围

先读取规则、进度、Phase6验收和最新SPEC及相关源码/测试；先冻结 [P7-01](specs/tasks/p7-01-citation-report.md) 与测试，再实现。同一 LangGraph 的 report 分支完成想法→规划/澄清→检索→Phase6分析→来源与支持度审核→结构化报告/Markdown，不要求调用者拼装分析。无新依赖、数据库表、Multi-Agent 或 Phase2/8/9实现。

新增 domain/report.py（报告/引用/支持度契约及确定性Markdown）、application/report.py（来源绑定、结论/方向构造、官方元数据和逐项审核、发布门禁）、adapters/report_snapshot.py（原文件/XML哈希与定位验证）。调整 ResearchService/LangGraph、通用 LangChainAnswerGenerator、PubMedClient 有界批量 EFetch、CLI/API装配及飞书worker/sender。

八部分报告与可信来源快照、定位、内容hash、文献身份、检索范围/时间/策略、模型ID/规则版本、逐项事实/推断/假设和支持状态齐备。研究方向为候选缺口的待调查表述，保留验证事项，不新增设计Agent。引用编号按首次使用稳定构造，未引用文献只留发现记录，不列为支持文献。

CLI `ask --report`（可 `--format markdown`）、POST `/v1/reports`、飞书 `/report 科研想法` 共用同一服务；原问答与分析入口保持。飞书先计算最多32段完整文本，每段重检lease/期限，失败即停止，部分发送不自动重试或称作完整交付。

## 集中测试与修正

解释器 .venv/Scripts/python.exe，项目根运行；日志 .artifacts/p7-*.txt。合成原文和开发者候选标签在 tests/unit/test_citation_report.py，复用 Phase6 fixture；不称独立医学人工审定。

| 范围 | 实际结果 |
| --- | --- |
| 首次目标 | 14 fixture errors，Ruff移除未显式重导出的共享fixture导入；修正fixture导入后14 passed（1.53秒），不算产品RED |
| 快照/官方/入口增强 | PDF篡改测试初次修改了RetrievalResult复制前的对象而未修改实际输入，修正fixture；DOI冲突场景初次无本地DOI，本应合法，补入真实的双侧冲突字段；随后26 passed（3.16秒），p7-target-final.txt |
| 首次完整默认回归 | 1197 passed/2 failed/103 deselected/1既有SDK警告（135.58秒），p7-regression.txt；飞书普通问答增加了一次多余guard，旧时序断言失败。恢复旧路径，仅报告分段增加guard |
| 在线摘要增强 | 发现Phase4在线片段跨摘要章节，调整为核对完整record.abstract，保留具名章节校验；新增跨章节合法/篡改回指测试。初次fixture把QuestionRequest直接传给RetrievalRequest校验，extra request_id导致1 failed/316 passed；修正为实际请求投影 |
| 最终相关联合 | **317 passed（15.36秒）**，p7-related-final.txt；覆盖报告、飞书发送/分派、Phase6、原RAG、PubMed、装配和API |
| 后续完整回归 | 1199 passed/1 failed/103 deselected/1既有警告（140.24秒），p7-regression-final.txt；该进程收集时在线测试fixture仍把QuestionRequest传给RetrievalRequest，已修正并经联合测试复验，不能标此批全部通过 |
| 固定版本完整回归 | **1200 passed/103 deselected/1既有SDK警告（136.91秒）**，p7-release.txt；命令目录p7-release-tmp/p7-release-cache。没有运行中修改源码 |
| 全量后新增边界 | 本地多记录XML回读复用原document_id_for规则；新增fixture首轮误用pubmed导入类型，修正为pubmed_xml后318 passed（11.30秒），p7-related-release.txt。再补飞书超过32段仅发送明确整体提示，最终受影响联合 **319 passed（11.13秒）**，p7-related-release2.txt。这两项后续修正未重跑完整全量，不将新测试加进旧1200计数 |
| 质量 | Ruff check src tests 与Phase7 Demo通过，format --check同范围102文件通过；mypy src 50源文件通过 |
| Demo | -X utf8 -I docs/learning/phase-07/demo.py 成功输出八部分，合成文献+替身审查，快照不存在且支持度uncertain，正确verification_incomplete；p7-demo-utf8.txt |

相关联合命令：`-I -m pytest tests/unit/test_citation_report.py tests/unit/test_feishu_sender.py tests/unit/test_feishu_worker.py tests/unit/test_evidence_analysis.py tests/unit/test_research.py tests/unit/test_pubmed_online.py tests/unit/test_api_runtime.py tests/unit/test_command_runtime.py tests/integration/test_api.py -q --tb=short --basetemp=.artifacts/p7-related-tmp -o cache_dir=.artifacts/p7-cache`。

默认全量命令：`-I -m pytest tests -q --tb=short --basetemp=.artifacts/p7-regression-tmp -o cache_dir=.artifacts/p7-regression-cache`；修复后参数目录分别为p7-regression-final-tmp/p7-final-cache，固定版本完整命令为 `-I -m pytest tests -q --tb=short --basetemp=.artifacts/p7-release-tmp -o cache_dir=.artifacts/p7-release-cache`；最后两项边界修正后联合命令与上述相关联合一致，只替换目录为p7-related-release2-tmp/p7-related-release-cache。排除项不算通过。

质量命令：`-m ruff check src tests docs/learning/phase-07/demo.py`、`-m ruff format --check src tests docs/learning/phase-07/demo.py`、`-m mypy src --cache-dir .artifacts/p7-mypy`。文档链接/围栏/空白核查不算产品或医学验收。

覆盖四类支持状态、未知引用/捏造引文/标题/hash/位置冲突、无DOI合法、官方批量协议和元数据不可用、PDF原文定位、跨章节在线XML、稳定编号、八部分渲染、空命中、假设不升级、有限飞书分段与实际线程、CLI/API和完整共享服务链路。模型审核异常或上下文超预算保持uncertain，确定性非法引用不发布；不删坏引用伪装修复。

## 未验证及剩余门槛

当前进程未配置LLM_BASE_URL/LLM_API_KEY/LLM_MODEL；没有真实模型/付费调用。官方EFetch使用HTTPX MockTransport与官方格式合成XML；本轮没有真实PubMed联网、真实E5/数据库/模型完整报告链路或飞书账号真实收发。PDF文件验证使用真实解析器与合成PDF，不代表真实医学样例。

真实文献冻结快照、独立医学支持度标注/精确率召回阈值及签署仍待完成。P7-01已明确须在真实测试前由人工评审冻结阈值；没有以模型自评或旧Phase4/5记录代替本次验收。Phase1/3/6旧缺口保留。

精确回指、官方身份及模型支持审核不能证明研究结论正确、检全、创新性或正式GRADE/RoB；反向证据遗漏与同研究不同发表仍需人工复核。来源文件缺失不能只凭hash标核验通过；官方元数据变化/更正保留待复核状态，不改写历史来源。长报告超32段需CLI/API获取，部分发送失败状态不代表完整交付。

学习入口：[Phase7六份教材与Demo](learning/phase-07/README.md)。本阶段剩余是上述真实依赖/医学验收；不自动开展Multi-Agent或其他阶段。


## 真实运行事实与最小基线归档（2026-10-28）

本地p7-real-20261028材料已冻结到evaluation/minimal-v1。2条真实想法各检索到2篇文献，官方再次EFetch身份匹配，4份XML哈希及摘要回放一致。现有数据库只读连接OperationalError，未替换数据库或伪造本地链路。

初次2条fresh均extraction_failed；补充span对象提示与短问题字符索引后规划通过，但2条fresh均context_limit。随后修正模型输入重复XML及审核Unicode预算计数，保留输出来源快照/原文校验；使用真实规划响应的回放续验进入真实分析调用后model_output_invalid，未生成有效报告、未进入支持审核。历史共5次模型调用（授权上限6），没有医学人工签署。最小基线命令不重复这些调用。

本次建立基线只复算这些事实：fresh成功0/2，来源回放4/4，医学质量未评价；不是新的真实端到端通过。完整失败、回放区分、调用与耗时见[基线结果](../evaluation/results/minimal-v1/results.md)及其JSON。Phase7仍未全部验收；后续先完善最小评价基线，再增量Multi-Agent，最后Phase8及完整Phase9。
