# SPEC 06：证据分析、研究类型与冲突

版本：0.1；状态：未来阶段概要，开发前细化；未实现。

## 1. 背景及目标

在可追溯检索结果上整理研究设计、适用范围、局限和潜在冲突，帮助科研阅读。不能把检索分数、模型自评或仅有摘要的自动判断称为已完成临床证据质量评价。

## 2. 功能需求

- P6-F01：结合官方出版类型与实际文本识别研究设计，明确 metadata/text/model_inference 来源及 unknown 情形。
- P6-F02：提取有文本支持的人群、干预、对照、结局、时间窗、样本量及效应信息，未知保持空，不猜统计量。
- P6-F03：记录可观察的质量线索和局限，区分“未报告”与“方法存在缺陷”；每项判断关联具体证据块。
- P6-F04：比较同类问题的研究，输出支持/不一致/潜在冲突/不可比较及原因，不仅靠结论正负号判冲突。

## 3. 非功能需求

分析须可回溯文本范围和版本；摘要只能支持摘要可见判断。抽取数值、单位和否定必须保留原文依据，不把模型可信度当临床证据等级。规则与生成分开，允许模型失败后返回未评估状态，不输出伪造完整分析。

## 4. 本阶段不实现的内容

不自动宣称完成 GRADE、RoB 等正式人工评价，不把研究类型简单排成绝对等级，不自动完成荟萃分析或产生治疗推荐。不把 observational 与 RCT 的不同结论直接解释成互相推翻。

## 5. 输入输出契约

输入 EvidenceAnalysisRequest(question/QueryPlan, retrieved_evidence)。输出 EvidenceAnalysis(studies, limitations, comparisons, unresolved_questions, analysis_scope)。

StudyAssessment 包含 document_id、study_type、type_basis、population/intervention/comparison/outcomes/time_window、quality_signals、missing_information 和 evidence_chunk_ids。Comparison 包含涉及文档及结局、relation、comparability、reason、supporting_chunk_ids；relation=potential_conflict 必须给出两侧来源。

## 6. 数据模型

StudyType 初选 trial/cohort/case_control/cross_sectional/systematic_review/guideline/other/unknown，进入阶段前细化与 PubMed 类型映射。QualitySignal(value, basis, scope, evidence_chunk_ids) 不预设综合分数；ReportedEffect 保存原始表述、可选结构化值/单位/区间和来源，不转换未明确定义的统计量。

## 7. 核心业务流程

读取可信元数据及片段 → 识别研究设计与可见信息 → 结构化抽取及数值回指校验 → 形成范围/局限 → 先比较人群、干预、结局、时间及设计 → 呈现差异或潜在冲突 → 为后续报告提供带证据的分析。不能用分析文本覆盖原始文献记录。

## 8. 异常与边界场景

无摘要/无方法部分、摘要与元数据类型不一致、同研究多篇发表、单位不一致、结局不同、不同随访期、小样本、缺区间、来源撤回、更正和模型数值误读。无法比较时返回 not_comparable/uncertain，不强制判一致或冲突。

## 9. 测试用例清单

- P6-T01：元数据和文本一致/不一致、研究类型未知及来源记录。
- P6-T02：摘要条件下缺失质量信息保持 unknown/not_reported。
- P6-T03：样本量、效应值、单位、否定词及引用回指，防数值补造。
- P6-T04：可比较的相反结果、结局不同不可比较、同研究重复。
- P6-T05：模型格式/来源错误、文献注入文本、分析失败与旧报告回归。

## 10. 可执行验收标准

实施时运行 `uv run pytest tests/unit tests/integration -k evidence_analysis`。人工构造片段的字段、来源和比较类别必须与固定标注一致；没有质量信息时不得生成“高质量”判断，没有两侧证据的冲突不得发布。

真实样例需人工复核设计识别、数值抽取和冲突误判，提前冻结样例与接受阈值，报告假阳性/遗漏及摘要范围限制。当前只有测试设计，未运行证据分析，也不作任何真实医学结论。

## 11. 阶段依赖及完成定义（DoD）

依赖 Phase 5 验收。细化研究类型和可比较规则后 TDD；完成固定标注评估、引用链与异步回归、模型/规则版本记录以及 docs/learning/phase-06/。下一阶段把分析纳入核验报告，不自动进入正式临床评价。
