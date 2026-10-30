# 按研究问题检索与论文身份核验

2026-10-30。状态：任务SPEC冻结，待实现/阶段集中验收。

## 需求、边界与输入输出

复用QueryPlan、OpenAlexRetrievalService、CandidateAssessment及来源快照。任务意图影响检索与筛选，但不增加Agent/模型调用。feasibility在直接主题检索后补查技术路线与瓶颈；所有补查保留研究对象/任务约束。不将肝脏亚区自动替换成肿瘤亚区。论文解释与定义优先查用户指定论文或方法原始研究，不能被最新应用论文替代。

新增可选PaperTarget(kind=doi/title/method, source_text)：必须逐字来自用户输入；doi必须可规范化，title不由模型补造，method只表达用户原名。明确DOI/完整题名优先；没有明确论文标识但要求原方法论文/定义则使用method，其他任务可空。既有计划缺该字段可读；新paper_explanation/definition缺目标时拒绝将候选当成目标论文，记录unresolved，不猜测身份。

CandidateAssessment新增origin_quote（可空、最多1500字符）：原方法身份需要真实摘要原句，校验必须是摘要连续原文。仅新任务的method身份要求study_role=method_origin、非空origin_quote及目标方法原名/锚定同义名在题名的完整名称匹配；U-Net不可命中nnU-Net或Auto-nnU-Net。身份语义仍为模型有来源支持的判定，不等于独立人工签署。DOI规范化严格相等、题名仅大小写/Unicode/标点/空白规范化相等；缺元数据为unresolved，错配为mismatch。相似题名、预印本与期刊不同DOI不能擅自视为同一指定论文。

新增provenance.identity_checks字典记录候选身份状态；新增查询purpose记录。筛选上下文传task_intent、paper_target、元数据DOI，但完整snapshot不进模型。DOI/题名对新paper_explanation/definition候选实施硬门禁；方法原文同样需要来源支持。所有身份检查独立于constraints_match/相关性，主题约束不放宽，未知或错配保留审计。不新增数据库字段或网络API。

## 查询与预算

沿用两轮、每轮最多两HTTP，总四HTTP、四十候选、两筛选、45秒检索/30秒网络子预算及外层总deadline。feasibility第一轮直接查询（相关性/日期），第二轮在保留原概念约束的表达后分别追加methods与limitations/challenges焦点；这些焦点只是补检，不成为筛选强制条件。身份型查询使用目标DOI/题名或method及已有锚定同义表达；优先相关性排序，不对未指定日期的原论文添加近期限制。显式options.query继续优先，不混入自动焦点；显式日期约束不被身份查询绕过。comparison复用已有双方法补检，不重建旧逻辑。

## 正反例与标注

tests/fixtures/research_identity包含从既有真实OpenAlex快照提取的nnU-Net原研究、Auto-nnU-Net变体、肝脏整体分割、胰腺亚区负例；manifest记录来源文件、hash与本轮AI工程标注，人工签署为空。U-Net书目身份另依据作者官网与arXiv/出版方信息记录，不伪造OpenAlex响应或全文。所有标注为工程初判，不作医学金标准；无全文新增下载，保留旧来源许可证边界。

## 验收断言与命令

先编写tests/unit/test_research_identity.py：feasibility补检保留核心约束且四HTTP内；原论文查询不限近期；显式查询不被改写；错误DOI即使模型direct也拒绝；正确DOI仍需相关性通过；题名相似/错DOI不偷换版本；方法原文支持与变体拒绝；伪origin_quote拒绝；缺目标/缺元数据不伪匹配；身份状态及查询目的可追溯。真实快照hash与来源校验，人工标签不冒充签署。另复用现有日期、筛选预算、引用、快照、全文身份测试。

阶段集中执行：.venv/Scripts/python.exe -m pytest tests/unit/test_research_identity.py tests/unit/test_openalex.py tests/unit/test_research_quality_v2.py tests/unit/test_pico.py tests/unit/test_intent_routing.py tests/unit/test_oa_fulltext.py；随后既有默认离线pytest、Ruff。真实复验使用同一四题，需要配置LLM/OpenAlex、业务库/E5/Redis/飞书；部署/真实命令在阶段集中验收批次冻结。当前仅静态检查，不执行pytest/真实问答，不部署，不将原失败标为修复。本任务不实现可行性报告写作或新增学术来源。

## 中断后交付记录补齐

实现前已冻结四条真实快照及AI工程初判标签（manifest人工签署为空），先编写test_research_identity，再实现PaperTarget、任务焦点补检、来源支持的原方法身份判定及DOI/题名约束。Ruff五文件check通过；未运行pytest、真实问答或部署。精确DOI目标保留不同DOI同文本版本，避免旧去重遮蔽目标。方法身份仍受模型语义判断限制，不等于独立确认。任务随后由用户转入可行性分析，当前保持待阶段验收，不标完整通过。
