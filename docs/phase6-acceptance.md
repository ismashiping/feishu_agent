# Phase 6 P6-01 核心实现与验收记录

2026-10-28（Asia/Shanghai）。核心实现、离线集中验收及六份学习材料交付；实际结果如下。真实模型/真实文献医学人工验收未完成，**Phase 6 不标全部验收**，不进入 Phase 7 或 Multi-Agent。

## 基线和交付

按本地规则、最新进度、SPEC 和源码/测试核查：Phase 5 核心已验收，已有规划/澄清、PubMed、FTS/RRF、可信来源门禁；未有证据分析模块。先冻结 [P6-01](specs/tasks/p6-01-evidence-analysis.md) 与合成样例测试，再实现，阶段末集中验证。原未提交修改及历史验收保留。

- domain/analysis.py：六方法字段及相关研究字段、五维相似性、候选缺口、双侧研究比较、事实/推断/假设与缺失约束。
- application/analysis.py：一次有期限/上下文/输出预算的模型分析，复用 build_answer 来源门禁；精确引文/数字、文献归属、用户原文、重复研究和双侧来源验证。撤回来源剔除、更正/摘要/缺失/未知维度保持 partial，空命中跳过模型，不判创新。
- ResearchService/LangGraph：显式 analysis_requested 分支，复用 plan/clarify/retrieve，新 analyze 节点；旧 answer 默认路径保持。LangChainAnswerGenerator.analyze_evidence 复用原 _invoke，无新供应商逻辑、依赖或表。
- CLI ask --analyze、POST /v1/analyses：相同服务和结果，复用 API 请求边界及错误处理；结果保留可信文献快照/定位/hash/范围、实际检索选项和追溯，不返回 source_uri。记录配置 model_id（未提供时为空）及 evidence-analysis-v1。
- [六份学习材料与可运行离线 Demo](learning/phase-06/README.md)，API/CLI/架构与阶段进度同步。没有生成 Phase 7 最终报告，没有 Multi-Agent。

## 集中验证证据

项目根解释器 .venv/Scripts/python.exe；日志位于忽略的 .artifacts/p6-*.txt。

| 批次 | 实际结果及说明 |
| --- | --- |
| 初次目标 | 24 errors，均为新 fixture 遗漏 RetrievalResult.options，初始化失败，不是产品 RED；补齐后 24 passed（1.73 秒） |
| 双研究/入口增强 | 26 passed/1 failed，第二研究 fixture 未同步 chunk 来源 hash；修正后 27 passed（2.33 秒） |
| 预算/澄清增强 | 29 passed/1 failed，新 PICO fixture 缺四个显式 null 字段；修正后最终目标 30 passed（2.35 秒），p6-target-final.txt |
| 第一轮默认回归 | 1167 passed/103 deselected/1 既有飞书 SDK 警告（130.19 秒），p6-regression.txt；对应当时 24 个新目标测试 |
| 第二轮默认回归 | 1160 passed/13 failed/103 deselected/1 警告（128.68 秒），p6-regression-final.txt；运行中补充 model_id 导致进程内新旧模块不一致，extra_forbidden，不能作为固定源码验收；停止源码编辑后重新完整运行 |
| 最终相关联合 | 190 passed（7.47 秒），p6-related-final2.txt；含新分析、原 RAG/PICO、装配与 API 合约 |
| 最终完整默认回归 | 1173 passed/103 deselected/1 既有飞书 SDK 警告（122.62 秒），p6-regression-release.txt；固定最终源码，无运行中源码编辑 |
| 质量 | Ruff check src tests 与学习 Demo 通过；mypy src 47 源文件通过；format --check src tests 与 Demo 最终 98 文件通过 |
| Demo | -I docs/learning/phase-06/demo.py 成功，合成片段返回 partial、方法引文与 unknown，不生成缺口；p6-demo.txt |

质量命令：`-m ruff check src tests docs/learning/phase-06/demo.py`、`-m ruff format --check src tests docs/learning/phase-06/demo.py`、`-m mypy src --cache-dir .artifacts/p6-mypy`。文档本地链接与围栏检查、相关 diff 空白检查通过，不计功能验收。

目标命令：`-I -m pytest tests/unit/test_evidence_analysis.py -q --tb=short --basetemp=.artifacts/p6-target-tmp -o cache_dir=.artifacts/p6-cache`。

最终联合命令：`-I -m pytest tests/unit/test_evidence_analysis.py tests/unit/test_research.py tests/unit/test_pico.py tests/unit/test_command_runtime.py tests/unit/test_api_runtime.py tests/integration/test_api.py -q --tb=short --basetemp=.artifacts/p6-related-final2-tmp -o cache_dir=.artifacts/p6-related-cache`。

最终完整命令：`-I -m pytest tests -q --tb=short --basetemp=.artifacts/p6-regression-release-tmp -o cache_dir=.artifacts/p6-release-cache`。排除项不算通过。

合成标注及原文固定在 tests/unit/test_evidence_analysis.py：cohort/20/MRI/AUC 0.8、小样本示例，逐维四类关系、unknown 聚合、假设与验证事项、双侧比较与相同 hash 重复、撤回来源、超时/预算、未知/捏造引用、空检索/检索故障和澄清、真实 LangChain 假模型消息及共享 CLI/API。此为开发者候选标签，不是独立医学人工审定，也不代表召回或医学质量评价。

## 未验证项与完成边界

当前进程未配置 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL；没有真实模型/付费调用。没有本次真实文献冻结快照及医学人工签署，不能以合成样例替代事实抽取、相似性、缺口及冲突的医学质量验收。真实模型/真实 PubMed/数据库完整分析链路未执行；现有离线/装配替身验证和历史 Phase 4/5 验收不能算本次真实链路通过。

精确引文只验证回指，不能自动证明研究类型判定、推断、可比较性或反向证据完整；未完成 GRADE/RoB、创新性鉴定或全文审查。模型可能遗漏反证或误读引文，必须人工复核。相同 hash/PMID/DOI 可拦截明显重复，未自动识别同一试验的不同发表；这类样例仍需人工审定，不把多篇论文数量当独立支持。

阶段剩余：冻结真实医学文献快照与独立标签，配置真实依赖，集中补验并签署人工复核；通过后再更新完整阶段状态。Phase 1/3 既有人工/真实模型缺口照旧保留；不自动进入 Phase 7。
