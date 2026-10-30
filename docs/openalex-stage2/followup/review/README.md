# 第二阶段独立候选复核

共106个“问题—论文”条目，来自已保存的公开OpenAlex快照。items.json按问题和ID的稳定hash排序，隐藏模型排名、判定、入选状态及筛选理由。这里的“隐藏”是复核流程约束，不是访问控制；复核前请不要打开父目录的模型输出。

1. 先读原问题，再核对条目的标题、日期与摘要。
2. 在decisions.json按review_id填写population_match、task_match、modality_match、time_match：true/false；问题没有该约束时填字符串not_applicable，缺信息填unknown。
3. directness填写direct/partial/irrelevant/uncertain；support_quote须逐字来自该条目的标题或摘要，reason解释判断。缺摘要不得假定全文结论。
4. 对“最新”按2026-10-29向前24个日历月，即2024-10-29至2026-10-29；“近三年”从2023-10-29起。方法比较不自动限制年份；“目前”在本次冻结契约中不自动添加24个月窗口。
5. 区分器官分割、病灶整体分割、病灶内部亚区以及亚区特征下游预测。比较问题可分别收集两种方法的证据，不要求每篇同时研究二者；不得跨数据集直接排名。
6. 完成后再填写signoff.json的真实reviewer、signed_at与decision（approved/revisions_required）。当前全部未填写，禁止将空白当通过。

这是候选内相关性审查，不能凭它计算全库Recall。它也不包含全文或最终回答医学支持度审查。source_sha256将复核绑定到原live-check.json，替换输入必须重新冻结复核批次。
