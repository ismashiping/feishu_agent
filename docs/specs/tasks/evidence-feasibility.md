# 证据驱动可行性分析

2026-10-30；当前任务范围冻结，待阶段集中测试/验收。

目标：复用同一次EvidenceAnalyzer联合抽取和原report审核，以数据/标注、方法适配、算力成本、实验条件四维判断支撑研究方向评估。现有studies/idea_similarities/candidate_gaps保留已有工作与技术路线；不新增模型调用、Agent、评分或医学结论。

数据模型：AnalysisDraft增加feasibility列表（FeasibilityAssessment：dimension、status、assessment:AnalysisItem、next_check），维度data/methods/compute/validation，状态unknown/conditional/reported_barrier；unknown必须value=None，其他状态需要带真实引用的AnalysisItem；conditional只能为推断/假设。reported_barrier必须为原文事实，不能把文献中的资源限制当作用户当前限制。next_check是待执行核查建议，不当作已完成事实。新feasibility任务必须覆盖四维且不能重复，旧任务默认空列表保持契约。

增加experiments列表（CandidateExperiment）：gap_index、hypothesis、baseline、experiment、metrics、failure_criterion，文本均用AnalysisItem绑定来源并保持推断/待验证性质，不得作为已证实方案。gap_index必须指向当前候选缺口。上限5个，不强制凑数。指标/资源未报告则不编造具体数值。不声称做过实验或验证了创新性。

外部模型边界：复用现有Pydantic和EvidencePointer校验；四维引用及实验引用必须来自当前eligible来源、原文连续quote，未知项不携带伪造证据。实验不能借用不存在的gap。新字段收集为ReportClaim进入原支持度/来源审核，未知项保持information_missing/uncertain。报告默认展示四维核查项与候选最小实验，不产生未审核的额外正文。

无检索证据：不调用分析模型，四维均unknown，列出数据权限/标注、可复现基线、实测资源、小规模验证等核查问题，不生成假瓶颈/候选缺口/实验。不推导“没人做过”或“没有研究价值”。澄清分支仍不检索。

先编写tests/unit/test_feasibility_analysis.py，合成fixture复用test_evidence_analysis.case；覆盖四维合法/缺失/重复、无证据、伪引用/假gap/事实化实验拒绝、报告审核与渲染。合成结果不作医学签署。阶段命令：.venv/Scripts/python.exe -m pytest tests/unit/test_feasibility_analysis.py tests/unit/test_evidence_analysis.py tests/unit/test_citation_report.py tests/unit/test_feedback_agents.py tests/unit/test_intent_routing.py；阶段末再执行默认离线及真实四题、独立内容复核与学习文档。本任务只做Ruff静态检查，不运行pytest/真实依赖、不部署；所有新代码待测试验收。

## 本任务交付

先写合成测试，再扩展domain/analysis、application/analysis与application/report。复用AnalysisItem严格引用与事实/推断契约，新增四维状态一致性、实验gap索引和候选性质校验；外部模型边界核查新引用，报告收集为审核条目。没有新增LLM调用、Agent、重试、数据库表或通用包装。缺信息明确unknown，非成功降级；空检索不调用模型。

测试文件覆盖新字段合法输出、重复/缺维度、伪引用、假gap、事实化实验、无证据、审核/渲染与未知条件门禁。四个Python文件Ruff check及format --check通过；首次行长/导入问题经格式与导入修正。未执行pytest、真实LLM/外部依赖或部署，新测试均待阶段末集中验收，不能用历史测试成绩代替。本任务尚不证明科学质量或医学签署通过。

下一任务为飞书呈现与端到端集中验收；学习文档在阶段验收后生成。本轮停止，不自动开展下一任务。
