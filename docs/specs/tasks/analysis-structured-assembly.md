# 分析结构的确定性构造

2026-10-30。单任务：模型选择已编号的证据，程序构造事实字段、补齐缺失方法字段，并按维度计算总体关系。不放宽校验，不改检索、路由、LangGraph 或预算，不部署。

## 规则

- `reported_fact_quote`：事实值必须逐字等于其 evidence.quote，且 basis 为 text。
- `method_fields_required`：14 个方法字段都必须出现。没有报告的字段用空值和 `not_reported`，不能省略，也不能引用无关句子。
- `overall_relation`：任一维度为 unknown 则总体为 unknown；维度一致则取该关系；已知维度不一致则为 partial_overlap。不是多数投票。

## 构造

模型返回的是证据选择，不是完整 AnalysisDraft。`quote_id` 必须来自本次目录。程序把选中句子原样写入事实值和指针。对照角色、无关角色和其他论文的句子不会写入本篇事实。推断仍要自带 `verification_needed`。旧的完整 AnalysisDraft 输入仍走原来的校验。一次业务修正保留。

图神经网络题此前停在规划 `expansion_not_anchor`，本任务不改规划。

## 真实复验

2026-10-30，deepseek-v4-pro，分析预算 16384。三题都生成了合法 AnalysisResult，`analysis_status` 均为 partial：方法字段有合法空缺，总体关系均为 unknown，摘要来源不能标成全文完成。

| 题 | 意图 | 筛选 | 命中 | 结果 |
| --- | --- | --- | --- | --- |
| MedSAM 跨医院少样本分割 | feasibility | records=21，screened=15，screening_failed=1，eligible=4 | 4 | 4 篇；可行性 unknown/conditional/conditional/unknown；事实 48、推断 8；指针 18；空缺字段 38 |
| 钙钛矿界面稳定性 | feasibility | records=32，screened=23，screening_failed=1，screening_budget=2，eligible=21 | 5 | 5 篇；可行性 unknown/conditional/unknown/conditional；事实 65、推断 5；指针 21；空缺字段 49 |
| 蛋白质结构预测的少样本学习 | feasibility | records=25，screened=22，screening_failed=2，screening_budget=1，eligible=3 | 3 | 3 篇；可行性 unknown/conditional/unknown/unknown；事实 42；指针 6；空缺字段 36 |

命中上限是检索 `top_k=5`。eligible 少于 5 时命中数等于 eligible。MedSAM 先前出现过 eligible=7/6/2，本轮 eligible=4，是筛选当次可用文献数变化，不是分析丢掉论文。

同一蛋白质题在来源过滤之前失败过一次：`evidence_validation` / `source_identity_mismatch` / `studies.metadata_basis`，retries=0，schema accepted，finish_reason=stop。模型填写的出版类型不属于该来源。构造阶段改为只保留来源上真实存在的类型；对不上则研究类型降为 unknown。过滤后的复验已通过。

更早一次三题在调用模型前因 `context_limit` 失败：原文和句子目录各放了一份。提示里的来源证据改为只保留 chunk_id 与 location，句子只出现在 quotes。该次不是校验失败。

未部署。不代表医学签署。
