# 当前版本真实全链路验收：有界分批审核（2026-11-02）

## 结论
核心技术闭环通过本次两轮运行验证：真实规划→OpenAlex→全文获取/缓存→E5/PG
向量检索→研究对比/条件式可行性→多批模型审核→最终报告。整体科研质量正式验收
仍部分通过：证据/抽取/审核语义有未解决项，未标记Phase完成或医学人工签署。

## 入口与环境
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_batched_validation.py
```
当前源码open_research_service→ResearchService.report，原中文公开ICU数据AKI想法。
真实模型/OpenAlex、本地E5、独立库clinical_agent_test_context_20261102，保留既有缓存。
每批最多6条、字符上限32000，默认总预算180秒。无Mock、无改写模型输出。
本轮只增加测量和记录，无业务修改、无新增离线回归，不替代此前测试事实。
代码版本以source-hashes.json为证据；模型加载36.703秒在Graph预算前完成。
不是空库冷启动，不声称HTTP/API部署或飞书实收验收。

| 阶段 | first | repeat |
|---|---:|---:|
| 规划 | 4.375s | 3.907s |
| 在线检索含筛选 | 18.750s | 17.390s |
| 全文RAG（解析/分块/编码/入库/检索） | 44.266s | 52.078s |
| 分析 | 16.609s | 10.984s |
| 报告构建含全部审核 | 17.828s | 10.000s |
| 全流程 | 102.000s | 94.469s |
| 选中论文/有效全文/片段 | 5/5/15 | 4/2/6 |
| 最终报告 | 返回partial/verification_incomplete | 返回partial/verification_incomplete |
| 审核批数/论断 | 12批，67/67 | 6批，34/34 |
| 支持/部分支持/不确定 | 46/10/11 | 22/6/6 |
| 原句引用检查 | 67/67 | 36/36 |
| 最大审核输入字符 | 11250 | 11623 |
| cache_load真实命中 | 2 | 0 |
| 缓存索引/向量 前→后 | 6/275→9/363 | 9/363→11/511 |

逐批成功响应ID与请求集合完全一致，所有最终论断恰好覆盖一次，无重复、漏审、
not_reviewed或model_output_invalid。原始审核请求/响应均保存。
输入字段中用户想法实际存在。所有引用指针原句属于来源全文片段。
audit.json为独立核查结果，events.json为嵌套时序（不可重复相加）。

## 缓存与失败语义
first实际命中doi:10.1080/0886022x.2026.2690700和doi:10.1080/0886022x.2025.2611198，
后接同key的vector_search，无同论文download_parse。repeat选中不同论文，未命中；
不以总时间作复用证明。first新增31/30/27块，repeat新增94/54块，保留数据未清空。
first有openalex_assessment_invalid警告；repeat一篇invalid_file，一篇期限耗尽，
不能把未获取部分算有效全文。长token/fontTools警告仍保留，未安装或改限制。

## verification_incomplete实际原因
两轮审核全部实际完成，本次不是截断、批次跳过或汇总丢失。
first包括研究设计cohort分类缺直接证据、部分相似性/方法迁移支持不足及算力unknown；
repeat有研究类型、数据/结局unknown等。来源location_status均valid，identity和
metadata为not_applicable，不伪装成医学语义通过。
first在剩余约78秒时无法满足scout追加反馈135秒门槛，feedback_stop=budget_limit，
首轮审核已完成；repeat=no_actionable_feedback。没有总预算超时。

## 关键输出人工静态复核（非独立医学专家签署）
- 均提取方法/数据/指标等并输出用户想法比较、候选缺口、四维可行性；
  first为data/methods/validation conditional、compute unknown；
  repeat为data/compute unknown、methods conditional、validation reported_barrier。
- first样本量引文为外部验证370例脓毒症患者、61例AKI，保留原分组及单位；
  未强行推广为用户全体ICU人群样本量。
- repeat c6引用综述表格中某原始研究行，含23950/3954，作为综述sample_size；
  尽管没有再误填综述篇数，这仍存在“所引研究样本→综述自身字段”的归属错配，
  审核仅因逐字匹配判supported，未识别该语义风险。
- first缺口从有限亚人群研究推断通用ICU模型验证不足，审核判partial：
  引文不能证明缺乏覆盖全部ICU的模型。报告应作为候选假设，不能证明创新。
- 部分审核将未来核查建议缺少直接文献证据作为partial理由，
  需在今后校准事实支持与建议合理性的审核边界；本轮不改状态。

## 最终判断与下一步
运行链路、最终报告返回、多批完整审核、实际缓存复用本轮通过。
完整医学/科研质量验收仍部分通过，不能宣称所有论断成立或检全。
下一优先级：明确综述/原始研究/训练验证拆分的sample_size归属，不把引用存在
当作研究主体正确；应保存主体和单位并补回归，再校准审核，不简单提升状态。
该问题属于内容质量缺口，本轮未扩大范围修复。停止，不推进后续Phase。
