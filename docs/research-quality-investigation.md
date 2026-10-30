# 科研检索质量：第一阶段调查（2026-10-29）

本轮仅调查及记录基线，未修改生产逻辑。工作区起点已有大量已修改和未跟踪文件；HEAD 为 49e111072d2fc1ec5493a2122fb839e54557a40f，但 HEAD 不能代表本次测试源码。既有修改保留。

## 实际调用链

ResearchService.answer/analyze/report → plan → IdeaPlannerAgent → PicoPlanner.plan → LangChainAnswerGenerator.extract（PICO_INSTRUCTIONS 与 ExtractionDraft schema）→ QueryPlan → LiteratureScoutAgent → 本地 RetrievalPort / PubMedRetrievalService.retrieve → PubMedSearchRequest.query_text → PubMedClient.search → ESearch → EFetch → parse_pubmed_response → PubMedRecord → EvidenceHit → merge_sources。

answer 分支：_prepare → generate → parse_draft → build_answer；analyze/report 分支：EvidenceAnalyzer → PriorArtGapAnalystAgent → ResearchDesignAgent → ReportBuilder / EvidenceReviewerAgent → render_report。不能把 report 的语义审核能力等同于 answer 的引用标识校验。

## 已确认事实、根因与影响

1. `domain/pubmed.py:50` 当前已经组内 OR、组间 AND，不是全局 OR。`docs/specs/pubmed-relevance-fix.md` 的旧根因描述与现状不一致。不能将历史故障直接归因于当前布尔拼接。
2. 同一函数仅在 blocking_ambiguities==[] 且 concept_groups 非空时使用分组，否则返回原问题。`domain/pico.py` 允许 concept_groups 缺省为空，旧格式 terms 扩展被忽略。已有 exploratory 测试复现：英文扩展未进入 query_text。影响所有仅提供 terms 的旧计划，不限疾病。没有证据表明真实模型每次都会遗漏 concept_groups。
3. `domain/pico.py:112,142` 通过指令要求同义词分组，但校验不验证组内是否真为同义概念；search_intent 仍是临床分类，没有独立科研意图字段。other 不触发专门过滤或降权；没有发现 other 导致该 PMID 丢失的证据。要求探索问题仍提供疾病与主题组可能诱导无疾病方法综述增加限制，尚待模型实测。
4. `adapters/pubmed_online.py:206,269` 按相关性默认排序分页，每页最多10条，总量默认10、最多20；仅抓取 ESearch 所选 ID，按其顺序重排 EFetch 结果。每次 search 最多8次 HTTP 尝试，含重试，30秒上限并受传入剩余 deadline 限制。不是全库候选评分。
5. `application/pubmed.py:65-117` 治理/摘要/来源过滤后，按原始排名取前 top_k，没有问题相关性筛选。后排直接研究可能在已获取后仍被截断；这是机制事实，历史具体论文是否遭此截断未知。
6. `application/pubmed.py:128-178` 合并固定预留 ceil(top_k/2) 本地名额，随后填在线；不比较本地向量分数与在线分数这一点符合要求，但名额分配不考虑直接相关性。PMID去重对 pubmed_rank 命中生效，本地同文多块仍可能占多个名额。直接研究被替代的实际程度待固定标注样例验证。
7. `domain/pubmed.py:110,146` 审计保留 query_sent/translation、数量、截断、缺失 PMID，但 provenance 排除 records，也没有完整 ESearch ID 列表。成功抓取但未入选的记录无法仅凭最终 provenance 还原。不能仅依最终引用反推未召回。
8. `application/research.py:187` answer 上下文提供正文、chunk、位置和scope，未传 QueryPlan、来源书目信息或截断信息；`domain/citations.py` 最终附加范围局限并校验标识，不验证医学语义蕴含，也不要求覆盖所有已选研究。存在生成端忽略直接证据的可能，但未取得故障原始模型输入输出，不能确认发生。
9. `domain/report.py:93` 默认报告正文直接输出结构化计划、检索JSON、UUID、hash及多次chunk标识。审计与科研展示混合是可确认的展示问题。

## 可复现基线

命令（项目根目录）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_pubmed_concept_groups.py tests/unit/test_pubmed_online.py tests/unit/test_pubmed_contracts.py tests/unit/test_exploratory_discovery.py tests/unit/test_research.py tests/unit/test_evidence_analysis.py tests/unit/test_citation_report.py -q --basetemp=.pytest_tmp_investigation --tb=short
```

结果：176 passed，7 failed，6.18秒。完整输出位于根目录 investigation-baseline.txt。首轮默认临时目录权限导致4项setup错误；指定工作区basetemp后消失，不属于业务失败。

7项失败均在 test_exploratory_discovery：1项直接查询断言，6项在线/混合分发组合。后6项 Search替身先断言英文扩展存在，断言失败被Scout包装为retrieval_failed；不是6种独立网络故障。当前分组专用测试只有字段存在及显式query覆盖，不验证真实分组行为或召回质量。

## 尚无法验证

在 tests/evaluation/docs 搜索三个PMID，仅发现39752907用于显式query覆盖测试；没有找到三篇文献的已验证XML、历史ESearch/EFetch请求记录。已有minimal-v1快照包含其他主题，不能替代故障现场。尚未调用真实PubMed、数据库或模型，因此不能给出故障查询的真实translation、命中总数、ID列表，也不能断言三篇文献未召回、被过滤或生成阶段遗漏。已有测试通过不等于科研质量验收。

## 下一阶段SPEC与可测验收设计（尚未实施）

- 先冻结不含特定疾病规则的固定响应与人工相关性标注，再写失败测试。覆盖疾病+方法、领域探索、纯方法综述、同义词、稀少证据、跨疾病混合、大量截断、多来源重复；留独立疾病/方法组合不参与规则制定。
- 查询指标：必要概念保留率、非必要约束误加数、旧计划兼容性；验证实际请求，不只检查字段存在。
- 候选指标：固定候选内直接证据 recall@k、precision@k、方法综述相关证据保留率、同文占位；分开报告 ESearch召回与后续选择损失，不能以PMID强插结果。
- 回答指标：代表性直接证据覆盖、引用原文支持、跨疾病误归属、未报告结果臆造、截断时绝对否定。模型质量使用来源快照人工核查，不能用prompt字符串断言替代。
- 预算指标：HTTP尝试数≤既有8次/调用，候选≤既有20，top_k与总deadline不变；反馈路径需单独核查累计请求，不能把单次上限误称全流程上限。
- 最小修改候选：旧计划兼容策略、现有候选范围内选择、审计保留候选去向、生成输入范围信息及报告展示。是否分层检索须先以固定标注证明收益及预算可容纳；目前没有理由直接增加检索阶段。
- 顺序按用户本次要求 SPEC → RED → GREEN → 回归 → 验收。此次只有修改前基线，未开始GREEN，未宣称质量改善。
