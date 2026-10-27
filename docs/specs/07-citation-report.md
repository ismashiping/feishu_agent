# SPEC 07：自动引用核验与结构化报告

版本：0.2；状态：未来阶段概要，开发前细化；未实现。

## 1. 背景及目标

在 Phase 1 基础标识校验之上，核验文献身份、元数据一致性及结论证据匹配，生成可追溯、可复核的医学研究报告。引用存在不代表支持某个结论；来源获取失败也不代表文献不存在。

## 2. 功能需求

- P7-F01：校验报告引用是否来自本次实际检索/验证来源，检查 chunk_id/document_id、标题、PMID、DOI 和来源身份一致性。
- P7-F02：本地来源校验快照、哈希和定位；有 PMID 的来源通过官方元数据核对，按已有超时/缓存/配额规则执行。没有 DOI 的文献照常合法。
- P7-F03：逐条结论核查证据关联，区分 supported/partially_supported/unsupported/uncertain；模型建议须标明，不能称作确定性事实校验。
- P7-F04：输出结构化报告及 Markdown 渲染，包含问题、检索范围/时间/策略、结论与证据、冲突、局限、未解决问题和参考文献。
- P7-F05：身份不符或未知引用阻止正常报告发布；核验服务不可用时提供明确 verification_incomplete 状态和已验证范围，不贴“全部核验通过”。

## 3. 非功能需求

报告从可信来源字段渲染元数据，禁止模型自由生成作者/标题/PMID/DOI；输出稳定引用编号，正文编号与参考列表可双向对应。保留使用的版本快照和核验时间，避免后续更新让历史证据不可找。远端核验有总预算，不能无限逐条查询。

## 4. 本阶段不实现的内容

不以 DOI 能解析就认定文章结论被证实，不保证全文开放，不自动完成同行评议或系统综述；不实现学术排版编辑器和多种办公文档导出。外部 DOI 注册库核验如需新增服务，先核查其官方接口再扩展 SPEC，不临时抓第三方网页。

## 5. 输入输出契约

输入 ReportRequest 包含 QuestionRequest/QueryPlan、实际证据快照及 EvidenceAnalysis。输出 ResearchReport(report_id, version, question, search_provenance, findings, evidence_table, conflicts, limitations, uncertainties, references, verification, generated_at)。

CitationVerification 包含 source_id、identity_status、metadata_status、location_status、checked_at、errors；ClaimVerification 包含 claim_id、support_status、evidence_chunk_ids、basis。报告级 status 为 verified / verification_incomplete / rejected；verified 仅表示所定义检查完成，不等于临床结论必然正确。

## 6. 数据模型

Reference 由来源快照构造，编号按首次引用顺序稳定生成，未使用来源不得列为“支持文献”。保留原标识和规范化值以发现冲突，不能在发现 DOI/PMID 不一致时自动改写文献身份。LocalSource 可标 not_applicable 的外部身份核验，但必须通过内容/定位追溯；外部来源请求失败为 unavailable，不标 invalid。

## 7. 核心业务流程

整理待发布结论与所用证据 → 确定性身份/位置/范围校验 → 必要官方元数据核验 → 结论支持度检查 → 汇总失败与不确定 → 按策略拒绝、标为不完整或输出报告 → 同一结构化结果渲染 API/CLI/飞书文本。不能仅删掉坏引用再发布原有无依据结论。

## 8. 异常与边界场景

伪造 PMID、DOI 指向别文、标题细微差异、作者截断、重复参考、无 DOI、摘要冒充全文、失效链接、来源快照缺失、片段越界、模型错误支持判断、核验超时、撤回/更正。失效网页不等于研究被撤回，未能核验不等于证据证明无效。

## 9. 测试用例清单

- P7-T01：未知引用、身份冲突、别篇 DOI、无 DOI/PMID 的本地来源。
- P7-T02：正文和参考编号双向一致、重复来源去重、未用来源不列支持。
- P7-T03：哈希/页码/字符区间及摘要全文范围校验。
- P7-T04：结论 supported/partially_supported/unsupported/uncertain，禁止静默修剪引用掩盖无依据结论。
- P7-T05：官方核验失败与身份无效区分，配额/缓存、撤回/更正标记。
- P7-T06：结构化 JSON 与 Markdown 同一来源，历史报告版本追溯和所有入口回归。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k citation_report`。对人工注入伪造 ID/元数据冲突/越界片段的 fixture，拒绝率必须 100%；所有合法引用可定位，编号映射完整，无 DOI 的合法文献不能误拒绝。

模型支持度判断以人工冻结标注集另测精确率/召回，阈值开发前确定；外部故障实验只返回不完整或失败，不得将报告标全核验。真实 PubMed 核验继承 Phase 4 external 记录。当前未生成实际研究报告。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 6 验收；先细化身份容错、支持度、发布门禁和来源快照保留策略。完成确定性验证、真实官方核验冒烟、标注评估、格式一致性/历史回归与 docs/learning/phase-07/ 后验收。Phase 8 才扩展知识库版本更新。
