# 审核状态与缓存未命中诊断（2026-11-02）

本轮只读诊断，未修改业务代码、未调用模型、未写数据库。
依据 ../live-report-context-restored-20261102 的两轮原始JSON、源码及本轮真实load回读。

## verification_incomplete
cold: 23条均有basis，9 supported、10 partially_supported、4 uncertain。
repeat: 26条均有basis，23 supported、2 partially_supported、1 uncertain。
来源location均valid，identity/metadata为not_applicable，不是unavailable/invalid。
无批次失败/超限跳过说明；没有证据显示部分审核结果未正确汇总。
源码逐批要求claim_id集合恰好覆盖本批且无重复，然后写入原claim对象。
因未保存原始审核响应/逐批明细，只能确认最终覆盖，不能逐字重放模型响应。

明确原因：
- cold c22 / repeat c25: compute unknown且information_missing=true，无算力证据；
  程序强制保持uncertain是正确行为，不能改为verified。
- cold c1: cohort分类证据仅说明前瞻验证，审核不能充分支持研究设计分类。
- cold c11/c14: 数据公开性、人群/排除标准等不被所引原句充分支持。
- cold c9: XGBoost引文止于“0.”，数值不完整；保存片段本身已以0.结束，
  不能仅凭此证明句子分割正则错误，需另查上游分块和正文边界。
- cold部分相似性审核指出缺少用户约束；review_context只含claims/sources/schema，
  没有original_idea、idea_quote或结构化约束。这是确定的审核输入缺口，
  不等于汇总遗漏；它会使本可核对的比较变成不确定。
- repeat c10: sample_size字段用了47项研究/常用模型句子，字段语义错配。
- repeat c24: 方法可行性添加LASSO/专家特征选择，但所引原句未支持该部分。
  这些是内容质量问题，保持partially_supported合理。

cold中间报告在ResearchService反馈门槛之前已经verification_incomplete。
总104.156秒，180秒还剩约75.8秒；scout反馈要求135秒，故budget_limit停止。
这是“追加反馈准入预算不足”，不是首次审核未完成/总180秒耗尽。
repeat无需触发反馈，no_actionable_feedback，因为现有feedback规则不针对
partially_supported/uncertain重跑。这一状态名称不表示证据充分。
ReportBuilder任一claim非supported就incomplete；所以两轮状态均符合既有契约。

## 缓存
同一自然语言问题不等于同一执行检索式。两轮规划生成不同概念组与扩展，
第二轮还重复出现machine learning/deep learning概念组；查询、筛选均不同。
cold选中：
- doi:10.1136/bmjopen-2021-054092（成功，写27向量）
- doi:10.1093/ckj/sfaa145（编码超时，无发布）
- doi:10.1016/j.ijmedinf.2025.105815（阶段期限，无发布）
repeat选中：
- doi:10.1093/jamiaopen/ooaf065（成功，写48向量）
- doi:10.1097/ccm.0000000000006359（编码超时）
- doi:10.1080/0886022x.2022.2036619（阶段期限）
- doi:10.1186/s12967-022-03364-0（阶段期限）
- doi:10.1093/ckj/sfac181（阶段期限）
两轮选中集合交集为零，repeat自然不可能复用cold唯一发布的论文。
缓存key优先规范DOI加doi:前缀；无DOI才用OpenAlex ID，以上均走DOI。
load条件key相等、SIGNATURE相等、expires_at>now；publish事务内写索引及向量，
30天有效期，不使用用户查询作为缓存key。

本轮只读数据库实际核查：两行签名均匹配、未过期，passages/vectors分别27/27、48/48。
调用真实PostgresFulltextStore.load(key,SIGNATURE)均命中；其余未发布论文不命中。
见cache-readback.json。这证明已写缓存可读；不是正式入口热缓存命中验收，
也没有依总耗时判断缓存有效。
未发现这两轮存在key错配、签名错误、过期或事务发布缺失。
不外推为并发/所有论文身份场景均已验证。

```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/diagnose_cache.py
```

建议后续最小任务：审核上下文加入原始想法及必要的用户比较维度，再验证相似性审核；
新增持久化的原因分类应区分缺证据、模型不确定、反馈预算不足和审核执行失败。
修复字段抽取语义及截断数值另立范围；缓存无证据支持修复，先保持实现。
真实复用验收可再次执行原问题并记录所选论文与key，只有实际load命中才记通过。
