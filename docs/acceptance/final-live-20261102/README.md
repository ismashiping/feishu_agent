# 当前版本真实全链路验收（2026-11-02）

## 结论
部分通过，不能标记整体正式验收通过。
两轮均从原中文ICU/AKI科研想法经正式ResearchService.report返回真实报告，
在线检索、全文、E5、DB入库和RAG实际执行。第二轮实际命中已存全文。
但两轮审核首批均model_output_invalid，全部论断仍not_reviewed/uncertain；
本次审核可靠性门槛未通过，不是单纯文献缺证据或模型判断不确定。

## 实际命令与边界
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_final_validation.py
```
只转发原实现的测量包装，真实模型/OpenAlex/E5，独立库clinical_agent_test_context_20261102。
无Mock，无业务代码/预算/校验修改，无新建或清空库。
库起点已有2篇75向量，不能称全库冷缓存。付费调用沿用户既有授权。
当前关键源码哈希见source-hashes.json；原始规划、分析响应和逐批审核输入已保存。
模型审核失败发生在适配器返回内容之前，无成功原始响应文件；不编造审核结果。

| 项目 | first | repeat |
|---|---:|---:|
| 总耗时 | 105.391s | 75.000s |
| 规划 | 4.531s | 4.031s |
| 检索含筛选 | 19.750s | 11.234s |
| 全文RAG | 60.875s | 40.141s |
| 分析 | 13.234s | 13.375s |
| 报告组装含审核 | 6.891s | 6.110s |
| 实际全文论文/片段 | 2/6 | 3/9 |
| 报告论断 | 38 | 49 |
| 审核成功论断 | 0 | 0 |
| 首批审核论断/输入字符 | 38/31459 | 40/31537 |
| 失败 | model_output_invalid | model_output_invalid |
| 引用指针原句检查 | 42/42匹配 | 50/50匹配 |
| cache_load命中 | 0 | 1 |
| 缓存索引/向量 前→后 | 2/75→4/174 | 4/174→6/275 |

第二轮首批失败后剩余9条未发送；保持uncertain是正确降级，不能说49条已审核。
ReportClaim.basis默认not_reviewed是非空字符串，不能用bool(basis)统计审核完成。
本轮audit.json使用basis!='not_reviewed'，逐批事件也证明成功数0。
两报告均partial/verification_incomplete；feedback_stop分别budget_limit和
no_actionable_feedback。后者不表示审核成功，当前反馈规则不因审核失败自动重试。

## 缓存证据
repeat读取 doi:10.1093/jamiaopen/ooaf065 命中（0.015s），随后同key向量检索
0.016s，无该论文download_parse/cache_publish。不能用总耗时差替代此证据。
该缓存来自以前真实运行；两次新选论文交集不作为命中依据。
新入库first：doi:10.1136/bmjopen-2024-087427(56块)、doi:10.1097/ccm.0000000000006359(43块)。
repeat：doi:10.1080/0886022x.2026.2690700(59块)、doi:10.1080/0886022x.2025.2611198(42块)。
所有运行保留必要下载失败与Embedding超时警告。

## 输出复核
- 两份报告均有研究对比、候选缺口、四维可行性字段。compute为unknown，
  其余conditional或reported_barrier，未保证用户实际资源或创新性。
- first样本量保留“334,812 ICU stays”的原单位，没有改成独立患者数；另一篇未报告。
  repeat三篇sample_size均未报告，没有把系统综述纳入篇数填作样本量。
- 文献存在、片段定位与原句匹配只证明引用链，不保证字段解释和推断正确。
- first候选缺口从有限子群/泛化研究推断更广人群空间，属于需要额外检索和反证的假设，
  没有足够审核支持将其当创新结论。
- 未由医学专家签署；本轮模型审核失败，不能将报告作为完成质量验收的科研结论。

## 下一步优先级
P0验收门槛：定位真实审核model_output_invalid。当前输入按字符分批，但一批38/40条
可能超过模型输出预算；这是怀疑，现有事件未保存finish_reason/输出token详情，
不能确定就是截断。最小下一步是捕获安全completion_details并回放同一审核输入，
据结果决定按输出条数/预算进一步分批，不能靠改状态通过。
P1：Embedding仍会用尽全文阶段预算；筛选曾有openalex_assessment_invalid。
P2：可选优化暂不推进。
本轮未执行离线回归（无业务改动），不借此前绿色结果替代本次真实失败。
