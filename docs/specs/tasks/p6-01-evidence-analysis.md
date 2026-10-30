# P6-01：带来源约束的研究方法、相似研究及候选缺口分析

2026-10-28。对应 P6-F01–08、P6-T01–09；实施前冻结，未验收。只开发 Phase 6，不生成 Phase 7 报告或多 Agent。

基线：ResearchService 已有 PICO/澄清、local/online/hybrid 来源与本地 FTS/RRF、期限和领域引用校验；缺分析 DTO、分析模型调用、分析验证器和入口。新增独立 analyze 方法复用上述规划/检索，不改变 answer 默认行为。CLI ask --analyze 与 POST /v1/analyses 返回结构化分析及可信来源快照。

输入为现有 QuestionRequest（question 原文即科研想法；用户约束保留在原文/QueryPlan）。内部分析请求携带 QueryPlan 和 RetrievalResult，含检索追溯。输出 AnalysisResult 记录请求、原始想法、状态、研究/方法、相似性、候选缺口、双侧研究比较、待调查问题、来源快照及时间。固定六方法字段和 population/intervention/comparison/outcomes/time_window/sample_size/effects/quality_signals；每字段为已报告项或明确 not_reported/unknown。分析项分 reported_fact/model_inference/unverified_hypothesis；事实直接保留原文切片作为 value，推断/假设需依据及验证事项。证据引用用 chunk_id 与精确引文；输出附可信来源定位、hash、摘要/全文范围。

研究类型枚举沿 SPEC 06；metadata_basis 只允许来自真实 publication_types，text 需原文，推断明确标注。不自动将 PubMed Clinical Trial 升级为随机试验。类型元数据与文本冲突保留两者并提示。相似性固定 question/population/data/methods/outcomes 五维，均含用户原文片段、关系与依据；用户未说明或文献未报告时 unknown。整体关系有 unknown 则必须 unknown，不能平均成完全相同。比较需两个不同研究的证据和可比较性理由；potential_conflict 两侧缺一即拒绝。相同 PMID/规范 DOI/内容 hash 归为重复来源组，不能做独立研究比较。

候选缺口仅允许推断/假设，必须有依据、推理、范围、待验证事项，反向证据显式列出；所有检索证据均传给模型，要求列出反向证据。确定性校验只能证明回指，不能证明模型未遗漏反证或医学语义正确，必须人工审查。撤回来源不用于正向分析，保留来源警告；更正/其他 notice 降为 partial。空结果跳过模型，仅 insufficient_evidence，无创新/缺口。模型故障、非法 JSON、未知引用、捏造引文拒绝分析，不静默生成完整结果；整体期限/上下文/输出预算沿 ResearchLimits，单次分析调用，无循环。

先编写 tests/unit/test_evidence_analysis.py，再实现；合成 fixture 的标签为开发者候选标签，不称医学人工审定。固定场景：六方法字段/缺失、数值原文、逐维关系与 unknown、假设标签与验证事项、双侧比较、重复来源、撤回/更正、空命中、格式/注入/来源错误、期限、共享入口与旧 answer 回归。所有确定性追溯门禁拒绝注入比例 100%，合法样例全部回指；人工样例接受条件为逐项事实/数字/标签无错误、相似性及候选缺口均经复核，有误修正后重新验收，不以模型自评代替。

阶段末命令（项目根，.venv/Scripts/python.exe）：

- -I -m pytest tests/unit/test_evidence_analysis.py -q
- -I -m pytest tests -q（默认排除真实外部依赖，不将 deselected 算通过）
- -m ruff check src tests；-m ruff format --check src tests；-m mypy src
- -I docs/learning/phase-06/demo.py

真实依赖验收：配置 LLM_BASE_URL/LLM_API_KEY/LLM_MODEL 后用真实模型处理冻结的真实文献快照；复用 Phase 4 PubMed/Phase 5 数据库检索集成覆盖受影响链路，所需隔离库与网络显式记录。真实文献样例、医学人工签署及真实模型配置在当前本地仓库未齐备时，必须记为待验收，不能称 Phase 6 全部完成；实现与离线验收可独立完成。集中测试失败在本批修复重跑。学习目录 phase-06 六份教材和 Demo 仍必需。
