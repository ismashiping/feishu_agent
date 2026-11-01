# 最小评价基线 v1

2026-10-28；用户明确授权建立基线。Phase7真实端到端和医学人工门槛仍未通过，本次建立可复核失败基线，不据此标阶段完成。只离线冻结、复算，不运行模型/网络/业务库，不实施Multi-Agent、Phase8或完整Phase9。

输入：本地p7-real-20261028两条想法、真实PubMed JSON、首次及修正后全链路记录、断点续验记录、5次模型调用账本与原始规划响应。冻结至evaluation/minimal-v1，SHA256 manifest约束每份证据及人工待标注模板。历史运行跨未提交源码版本：记录当前源码hash仅代表冻结时点，不伪称历史每次运行的源码版本均可精确重建。

输出：results.json及results.md，报告2个独立想法的最新fresh尝试成功率、停止节点/错误，单列回放续验，不将其当完整启动；复算4篇真实XML哈希/身份/摘要一致性；原样列出实际调用数与各步耗时。模型质量、方法字段准确/遗漏、相似性、候选缺口、支持度/创新宣称等无人工真值和有效报告时一律null/not_evaluated，不用0分、空集满分或模型自评代替。未签署人工标签的阈值保持pending，不接受机器修改模板作为医学签署。

门槛：证据hash全部一致、2条想法分母固定、回放不能计入fresh成功、来源复核4/4、人工缺失不伪标通过、无LLM调用。证据失效命令退出2；证据有效但fresh失败/医学未审退出1；只有fresh全部成功且医学审查齐备才可考虑退出0，v1不实现人工自动判分。因此当前预期退出1，不代表评价工具自身失败。

先写tests/unit/test_minimal_baseline.py，再实现scripts/evaluate_minimal_baseline.py。阶段末只运行此目标测试、离线评价命令及相关质量检查，不重复旧全量。命令：.venv/Scripts/python.exe -X utf8 -I scripts/evaluate_minimal_baseline.py；目标pytest文件同上。后续候选版本复制数据schema与独立人工标注，使用--bundle及--output明确输出，不覆盖v1证据；固定样例不是检索覆盖/医学效果全面评价。
