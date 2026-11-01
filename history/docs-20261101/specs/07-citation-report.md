# SPEC 07：科研选题现状调研报告与引用核验

版本：0.4；日期：2026-10-28；状态：P7-01 核心实现、离线集中验证与学习材料交付；真实依赖和医学人工待验收，不标阶段全部完成。

## 本轮核心范围与测试约定（2026-10-28）

本阶段具体契约见 [P7-01](tasks/p7-01-citation-report.md)，实际验收见 [阶段记录](../phase7-acceptance.md)。后文为阶段通用规则；实施前先细化本阶段 SPEC 和验收测试（含断言、fixtures/标注、实际测试文件/命令及真实依赖前提），再编写测试与最小实现。不在单次会话执行 RED/GREEN 或回归，阶段结束后集中执行核心测试、已有离线回归、受影响真实集成/外部冒烟、必要人工复核和质量检查。集中验收失败须修复并重跑受影响范围；未执行、失败、跳过或被排除的项目不得标记通过。下文 `-k` 命令为未来选择意图，实际目标测试为 tests/unit/test_citation_report.py，执行结果以阶段记录为准。

后续顺序固定为 Phase 3 → 4 → 5 → 6 → 7，不依赖延期 Phase 2 的 TaskRecord/receipt。复用现有 ResearchService/LangGraph、LangChain 通用模型边界、DTO 和存储/解析/引用模块。核心超时、错误分类、数据一致性及来源真实性必需；非核心健壮性、性能优化、复杂异常处理留 Phase 7 后收尾。核心验收及 `docs/learning/phase-07/` 六份真实学习材料齐备才标阶段完成。参见[开发计划](../development-plan.md)与[测试策略](../testing-strategy.md)。

## 1. 背景及目标

在 Phase 1 基础标识校验之上，核验文献身份、元数据一致性及结论证据匹配，为医生和医学科研人员生成可追溯、可复核的「科研选题现状调研报告」。必须打通科研想法输入、问题理解、检索规划、实际检索、Phase 6 分析、引用/支持度审核到最终报告输出的完整链路；只完成引用组件或孤立渲染不能验收本阶段。引用存在不代表支持某个结论；来源获取失败也不代表文献不存在。

## 2. 功能需求

- P7-F01：校验报告引用是否来自本次实际检索/验证来源，检查 chunk_id/document_id、标题、PMID、DOI 和来源身份一致性。
- P7-F02：本地来源校验快照、哈希和定位；有 PMID 的来源通过官方元数据核对，按已有超时/配额规则执行；缓存为可选优化，不新增前置缓存体系。没有 DOI 的文献照常合法。
- P7-F03：逐条结论核查证据关联，区分 supported/partially_supported/unsupported/uncertain；模型建议须标明，不能称作确定性事实校验。
- P7-F04：输出结构化报告及 Markdown 渲染，固定包含八部分：用户科研想法与研究问题；检索范围、策略和时间；已有相关研究；研究方法与技术路线对比；与用户想法的相似性分析；已有研究局限及候选研究缺口；可供考虑的研究方向；可追溯文献引用及证据支持状态。冲突、未解决问题与检索限制纳入对应章节；缺信息时保留章节并说明原因。
- P7-F05：身份不符或未知引用阻止正常报告发布；核验服务不可用时提供明确 verification_incomplete 状态和已验证范围，不贴“全部核验通过”。

- P7-F06：提供从科研想法到报告的一体应用链路并复用现有 CLI/API/飞书入口；不要求调用者手工拼装 EvidenceAnalysis 才能获得报告。保留既有问答兼容边界，具体请求选项与飞书长文本分段在实施前冻结，不依赖 Phase 2 持久任务机制。
- P7-F07：研究方向逐项关联 Phase 6 候选缺口/已有研究依据，标明推断或待验证假设、适用条件、需进一步调查事项；不得输出“已证明创新”或将空检索当创新证据。Research Design Agent 的方案设计留后续改造。

## 3. 非功能需求

报告从可信来源字段渲染元数据，禁止模型自由生成作者/标题/PMID/DOI；输出稳定引用编号，正文编号与参考列表可双向对应。保留使用的版本快照和核验时间，避免后续更新让历史证据不可找。远端核验有总预算，不能无限逐条查询。

## 4. 本阶段不实现的内容

不以 DOI 能解析就认定文章结论被证实，不保证全文开放，不自动完成同行评议或系统综述；不实现学术排版编辑器和多种办公文档导出。外部 DOI 注册库核验如需新增服务，先核查其官方接口再扩展 SPEC，不临时抓第三方网页。

## 5. 输入输出契约

对外输入为用户科研想法（original_idea）、研究问题/用户约束及现有检索选项；应用内部 ReportRequest 包含原始输入、QuestionRequest/QueryPlan、实际检索追溯、证据快照及 EvidenceAnalysis。输出 ResearchReport(report_id, version, question, search_provenance, findings, evidence_table, conflicts, limitations, uncertainties, references, verification, generated_at)，并扩展 original_idea、related_studies、methods_comparison、idea_similarities、candidate_gaps、research_directions，与上述八部分一一映射。逻辑契约由 ResearchReport/ReportResult 实现，原 ResearchAnswer 不承担报告字段；实际命名/边界见 P7-01 与源码。

CitationVerification 包含 source_id、identity_status、metadata_status、location_status、checked_at、errors；ClaimVerification 包含 claim_id、support_status、evidence_chunk_ids、basis。报告级 status 为 verified / verification_incomplete / rejected；verified 仅表示所定义检查完成，不等于临床结论必然正确。

## 6. 数据模型

Reference 由来源快照构造，编号按首次引用顺序稳定生成，未使用来源不得列为“支持文献”。保留原标识和规范化值以发现冲突，不能在发现 DOI/PMID 不一致时自动改写文献身份。LocalSource 可标 not_applicable 的外部身份核验，但必须通过内容/定位追溯；外部来源请求失败为 unavailable，不标 invalid。

各分析/方向保留 claim_id、epistemic_kind（reported_fact/model_inference/unverified_hypothesis）、evidence_chunk_ids、support_status 和验证事项。三类认识状态与四类支持状态分开：有引用的假设也不能自动成为事实。报告记录 content_status（complete/partial/insufficient_evidence）与独立 verification 状态，核验完成不代表检索完整；空检索只能输出明确证据不足的报告，不生成有依据的缺口或方向。检索失败保留错误，不渲染为证据不足。

## 7. 核心业务流程

科研想法输入 → 问题理解/必要澄清 → 现有查询规划与本地/在线/混合检索 → Phase 6 方法、相似性及候选缺口分析 → 形成待验证研究方向 → 整理待发布结论与所用证据 → 确定性身份/位置/范围校验 → 必要官方元数据核验 → 结论支持度检查 → 汇总失败与不确定 → 按策略拒绝、标为不完整或输出报告 → 同一结构化结果渲染 API/CLI/飞书文本。不能仅删掉坏引用再发布原有无依据结论。

## 8. 异常与边界场景

伪造 PMID、DOI 指向别文、标题细微差异、作者截断、重复参考、无 DOI、摘要冒充全文、失效链接、来源快照缺失、片段越界、模型错误支持判断、核验超时、撤回/更正。失效网页不等于研究被撤回，未能核验不等于证据证明无效。

## 9. 测试用例清单

- P7-T01：未知引用、身份冲突、别篇 DOI、无 DOI/PMID 的本地来源。
- P7-T02：正文和参考编号双向一致、重复来源去重、未用来源不列支持。
- P7-T03：哈希/页码/字符区间及摘要全文范围校验。
- P7-T04：结论 supported/partially_supported/unsupported/uncertain，禁止静默修剪引用掩盖无依据结论。
- P7-T05：官方核验失败与身份无效区分，必要配额、撤回/更正标记（缓存优化延期）。
- P7-T06：结构化 JSON 与 Markdown 同一来源，本次来源快照追溯和已有入口回归；跨更新版本追溯留 Phase 8。

- P7-T07：从原始科研想法经正式共享服务到 JSON/Markdown 报告，不手工注入分析结果；八部分与 Phase 6 分析、引用和支持状态一致，CLI/API/飞书使用同一结果，长文本不得截断引用和证据状态。
- P7-T08：有近似研究、部分相似、仅摘要、空命中、partial、需澄清、检索故障和核验故障分别贯通；澄清不检索，故障不伪装成功，空命中不判创新。
- P7-T09：候选缺口和方向保留依据、推理/假设标签及待验证条件；无依据、反向证据被省略或模型将假设改成事实时触发门禁或明确不支持状态，不得正常发布为确定结论。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k citation_report`。对人工注入伪造 ID/元数据冲突/越界片段的 fixture，拒绝率必须 100%；所有合法引用可定位，编号映射完整，无 DOI 的合法文献不能误拒绝。

模型支持度判断以人工冻结标注集另测精确率/召回，阈值开发前确定；外部故障实验只返回不完整或失败，不得将报告标全核验。真实 PubMed 核验继承 Phase 4 external 记录。完整链路须在阶段末集中执行：离线固定文献/标注集验证八部分及状态断言，真实 PubMed、数据库/检索和配置模型验证代表性科研想法到报告的实际链路，医学人工复核方法对比、相似性、缺口和研究方向的依据；替身结果不能替代真实依赖或人工验收。各入口验证同一报告及引用完整性。样例、支持度阈值、预算、实际测试文件和完整命令均须实施前冻结；真实样例阈值与医学签署当前待定；已生成合成离线报告，不作为真实医学报告或真实依赖验收。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 6 验收与学习材料，复用 Phase 4 官方客户端和 Phase 1 领域引用规则，不依赖 Phase 2/8/9。先冻结身份核对、支持度判定、发布门禁和本次来源快照保留策略。阶段末集中验收确定性身份/定位、真实官方核验、少量人工标注支持度样例、JSON/Markdown 一致性、已有快照/入口及完整核心链路回归，交付 docs/learning/phase-07/ 后完成。未知/冲突引用不得正常发布，核验不可用不得标 verified。跨更新版本生命周期留 Phase 8；Phase 7 完成后先建立[最小评价基线](../minimal-evaluation-baseline-plan.md)，再按[后续多 Agent 计划](../multi-agent-roadmap.md)增量改造，之后实施 Phase 8 和完整 Phase 9；不把多 Agent 当作本阶段验收前提。Phase 2/8/9 及非核心任务继续延期，与改造的执行关系届时确认，不在本次扩展或自动开始。
