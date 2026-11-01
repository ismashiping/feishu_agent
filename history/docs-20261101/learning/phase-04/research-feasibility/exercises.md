# 修改与独立练习

最小Demo命令见README。重点断言：同次计划仅一次、阻断歧义不检索、方法名不偷换变体、伪引文被拒、未知可行性不能被审核器提升成supported。

修改练习：在test_feasibility_analysis.payload中把compute改unknown，并清空assessment.value/evidence，设置basis=unknown；观察为何报告保持待核验。不要修改生产代码来掩盖测试数据的错误。

独立练习：使用现有AnalysisItem为一个合成研究编写候选实验，列假设、基线、步骤、指标和失败判据；保留证据和待验证语义。再构造不存在的gap_index，确认失败。不得用合成DOI作为真实论文。

调试顺序：计划→查询purpose→候选identity_checks→筛选→引用→审核→投递。先定位失败层，不用重启替代诊断。
