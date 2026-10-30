# SPEC 06：研究方法、相似研究与候选研究缺口分析

版本：0.3；日期：2026-10-28；状态：P6-01 核心实现及学习材料交付；离线集中验收结果见阶段记录，真实模型/医学人工验收未完成，不标阶段全部完成。

## 本轮核心范围与测试约定（2026-10-28）

本阶段实现契约与冻结场景见 [P6-01](tasks/p6-01-evidence-analysis.md)，实际结果见 [阶段记录](../phase6-acceptance.md)。以下为通用策略：实施前先细化本阶段 SPEC 和验收测试（含断言、fixtures/标注、实际测试文件/命令及真实依赖前提），再编写测试与最小实现。不在单次会话执行 RED/GREEN 或回归，阶段结束后集中执行核心测试、已有离线回归、受影响真实集成/外部冒烟、必要人工复核和质量检查。集中验收失败须修复并重跑受影响范围；未执行、失败、跳过或被排除的项目不得标记通过。下文 `-k` 为概要选择意图；P6-01 的实际测试入口与结果以任务 SPEC/阶段记录为准。

后续顺序固定为 Phase 3 → 4 → 5 → 6 → 7，不依赖延期 Phase 2 的 TaskRecord/receipt。复用现有 ResearchService/LangGraph、LangChain 通用模型边界、DTO 和存储/解析/引用模块。核心超时、错误分类、数据一致性及来源真实性必需；非核心健壮性、性能优化、复杂异常处理留 Phase 7 后收尾。核心验收及 `docs/learning/phase-06/` 六份真实学习材料齐备才标阶段完成。参见[开发计划](../development-plan.md)与[测试策略](../testing-strategy.md)。

## 1. 背景及目标

面向医生和医学科研人员，围绕用户科研想法，在可追溯检索结果上分析已有研究的方法、技术路线、重合程度、局限和候选研究缺口，为 Phase 7 科研选题现状调研报告提供结构化分析。保留研究类型、可比较性和潜在冲突能力。不能把检索分数、模型自评或仅有摘要的自动判断称为已完成临床证据质量评价。

## 2. 功能需求

- P6-F01：结合官方出版类型与实际文本识别研究设计，明确 metadata/text/model_inference 来源及 unknown 情形。
- P6-F02：提取有文本支持的人群、干预、对照、结局、时间窗、样本量及效应信息，未知保持空，不猜统计量。
- P6-F03：记录可观察的质量线索和局限，区分“未报告”与“方法存在缺陷”；每项判断关联具体证据块。
- P6-F04：比较同类问题的研究，输出支持/不一致/潜在冲突/不可比较及原因，不仅靠结论正负号判冲突。

- P6-F05：逐篇提取研究设计、数据来源（队列/数据库/采集方式等）、技术方法、评价指标、研究结果及局限性；每个字段关联实际片段，缺失标 not_reported/unknown，不从常识补全。
- P6-F06：以用户想法为基准，按研究问题、研究对象、数据、方法、结局逐维比较已有研究，输出 overlap/partial_overlap/different/unknown 及理由、用户原文定位和文献依据；不以标题相近、检索分数或单一总分替代比较。
- P6-F07：根据实际研究局限、方法差异和证据不一致提出候选研究缺口，列出依据、推理链、适用范围、反向证据和待验证事项。未检索到相关研究只表示当前检索范围内无命中，不得认定创新、研究空白或首次研究。
- P6-F08：所有分析项区分 reported_fact（文献明确报告）、model_inference（模型推断）、unverified_hypothesis（待验证假设）。事实必须回指原文；推断和假设必须关联其文献依据并注明推理及验证需求，无依据时仅记录待调查问题。

## 3. 非功能需求

分析须可回溯文本范围和版本；摘要只能支持摘要可见判断。抽取数值、单位和否定必须保留原文依据，不把模型可信度当临床证据等级。规则与生成分开，允许模型失败后返回未评估状态，不输出伪造完整分析。

## 4. 本阶段不实现的内容

不自动宣称完成 GRADE、RoB 等正式人工评价，不把研究类型简单排成绝对等级，不自动完成荟萃分析或产生治疗推荐。不把 observational 与 RCT 的不同结论直接解释成互相推翻。

## 5. 输入输出契约

输入 EvidenceAnalysisRequest(original_idea, question/QueryPlan, user_constraints, retrieved_evidence, search_provenance)。保留用户原文与研究问题映射，不强迫非干预类想法套入 PICO；缺关键比较维度时标 unknown 或请求澄清。检索范围、实际策略、时间、空结果/partial 状态随输入传递。

输出 EvidenceAnalysis(studies, limitations, comparisons, idea_similarities, candidate_gaps, unresolved_questions, analysis_scope, analysis_status)。analysis_status 区分 completed/partial/insufficient_evidence/not_evaluated；不改变原检索和依赖错误语义。此处为逻辑契约；P6-01 以 QuestionRequest + QueryPlan + RetrievalResult 输入、AnalysisResult 输出实现，具体字段见任务 SPEC 与 domain/analysis.py。

StudyAssessment 包含 document_id、study_type、type_basis、population/intervention/comparison/outcomes/time_window、quality_signals、missing_information 和 evidence_chunk_ids。Comparison 包含涉及文档及结局、relation、comparability、reason、supporting_chunk_ids；relation=potential_conflict 必须给出两侧来源。

## 6. 数据模型

StudyType 初选 trial/cohort/case_control/cross_sectional/systematic_review/guideline/other/unknown，进入阶段前细化与 PubMed 类型映射。QualitySignal(value, basis, scope, evidence_chunk_ids) 不预设综合分数；ReportedEffect 保存原始表述、可选结构化值/单位/区间和来源，不转换未明确定义的统计量。

补充拟议对象：MethodProfile(design, data_sources, technical_methods, evaluation_metrics, results, limitations)；每个字段使用 AnalysisItem(value, epistemic_kind, evidence_chunk_ids, source_location, content_scope, basis, missing_reason)。IdeaSimilarity(study_id, dimensions, overall_relation, reason) 中 dimensions 保留用户想法原文定位和逐维文献依据；不完整信息不得判完全重合或完全不同。CandidateGap(description, supporting_items, counter_evidence, reasoning, scope, verification_needed) 只能作为候选推断或假设，不得标作文献已证实的创新性。文献明确写出的未来工作是 reported_fact，其可行性及创新性仍待验证。

## 7. 核心业务流程

读取可信元数据及片段 → 识别研究设计与可见信息 → 结构化抽取及数值回指校验 → 形成范围/局限 → 先比较人群、干预、结局、时间及设计 → 呈现差异或潜在冲突 → 提取方法与技术路线 → 逐维比较用户想法与已有研究 → 基于证据提出候选缺口并标明推断/假设 → 为后续报告提供带证据的分析。不能用分析文本覆盖原始文献记录。

## 8. 异常与边界场景

无摘要/无方法部分、摘要与元数据类型不一致、同研究多篇发表、单位不一致、结局不同、不同随访期、小样本、缺区间、来源撤回、更正和模型数值误读。无法比较时返回 not_comparable/uncertain，不强制判一致或冲突。

## 9. 测试用例清单

- P6-T01：元数据和文本一致/不一致、研究类型未知及来源记录。
- P6-T02：摘要条件下缺失质量信息保持 unknown/not_reported。
- P6-T03：样本量、效应值、单位、否定词及引用回指，防数值补造。
- P6-T04：可比较的相反结果、结局不同不可比较、同研究重复。
- P6-T05：模型格式/来源错误、文献注入文本、分析失败与旧报告回归。

- P6-T06：设计/数据/方法/指标/结果/局限六类字段齐全且逐项回指；缺方法全文不能从摘要补造细节。
- P6-T07：与想法完全重合、部分重合、数据或结局不同、信息缺失四类固定样例，逐维标签和理由符合人工标注；未知维度保留 unknown。
- P6-T08：文献明确局限、模型推断、待验证假设三类不混淆；每个候选缺口有依据、推理、边界及验证事项；存在反向证据时不得隐去。
- P6-T09：空命中、检索 partial/失败、仅摘要、重复研究和撤回来源；空命中不产生创新性判定，失败不伪装空命中，重复论文不算独立支持。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k evidence_analysis`。人工构造片段的字段、来源和比较类别必须与固定标注一致；没有质量信息时不得生成“高质量”判断，没有两侧证据的冲突不得发布。

新增核心门槛：固定标注样例中所有事实/方法字段来源可定位，确定性来源检查通过率 100%；全部缺失字段不补造、空召回不判创新、三类认识状态不混淆；相似性逐维比较和候选缺口必须纳入验收，不能只完成旧证据质量分析即宣布 Phase 6 完成。

真实样例需人工复核设计识别、方法抽取、相似性、候选缺口、数值抽取和冲突误判，提前冻结样例与接受阈值，报告假阳性/遗漏及摘要范围限制。P6-01 已实现并执行合成样例的分析与确定性校验；真实模型/真实文献医学人工验收尚未完成，不作真实医学结论。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 5 验收与学习材料，不依赖 Phase 2。先冻结研究类型映射、方法字段、相似性维度、候选缺口证据规则及小型人工标注样例/接受标准。真实文献样例须记录 PMID/DOI（若有）、来源快照、片段、许可可用范围及人工标签；具体样例、模型阈值、测试文件和完整命令在实施前任务 SPEC 冻结，当前待定，不作为已通过项。阶段末集中验收研究类型、关键字段/数值回指、局限和双侧潜在冲突证据、真实样例人工复核与既有引用/入口回归；模型/规则版本记录和 docs/learning/phase-06/ 齐备后完成。大型质量评价体系、复杂异常组合和规模化统计留收尾，不自动进入正式临床评价。下一核心阶段为 Phase 7。
