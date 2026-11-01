# 有界预算修复与真实验收（2026-11-01）

结论：本轮正式报告返回与真实缓存命中通过；完整质量验收仍部分通过。
首轮context_limit保留为失败；第二轮返回partial/verification_incomplete报告。

## 修改
- domain/research.py ResearchLimits.max_seconds默认90→180秒，仍有硬期限。
- application/research.py 全文结束后预留60秒（原30秒）；全文自身仍最多60秒。
- _report只在剩余时间至少90秒（methods）或135秒（scout）时允许反馈，
  原轮数限制继续有效。不足时feedback_stop=budget_limit，保留当前报告；
  rejected不改成通过。不捕获或隐藏未知异常。
- 新增两项实际Graph的受控时间回归，验证methods/scout在预算不足时停止；
  旧超时测试的硬编码91改为配置上限+1，继续断言超时。
- 未修改检索、下载、引用门禁、数据库架构。

离线验证109 passed；Ruff src/tests通过，mypy77文件通过，范围内diff检查通过。
SPEC和完整命令见 ../../specs/tasks/report-budget.md。

## 真实执行
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports_budget.py
```
真实现有模型/OpenAlex/E5/独立测试库，原ICU/AKI中文样例，正式ResearchService.report。
计时包装只转发原实现，无Mock或模型输出改写。运行前库有2篇81向量，
未删除已有数据，因此称有缓存运行，不冒充全库冷启动。

| 指标 | warm | repeat |
|---|---:|---:|
| 正式入口 | context_limit失败 | 返回报告 |
| 总耗时 | 78.156s | 68.625s |
| 规划 | 4.766s | 4.406s |
| 检索含筛选 | 21.156s | 13.266s |
| 全文RAG | 52.141s | 36.766s |
| 全文论文/片段 | 3/9 | 2/6 |
| 分析 | 0.047s（上下文拒绝） | 14.062s |
| 报告构建 | 未执行 | 0.047s（模型支持度审核因上下文预算未执行） |
| 实际缓存命中 | 1 | 1 |
| 库中索引/向量 前→后 | 2/81→4/178 | 4/178→5/243 |

阶段时间嵌套，不重复相加。缓存命中后执行vector_search，中间无该论文下载。
所有缓存命中均来自正式调用链，不强制替换在线选中的论文。
repeat实际新下载解析一篇61单元、65块，Embedding14.281s、发布0.594s；
另一个候选下载失败，失败警告保留。原字体和长token警告仍存在。

## 报告与证据
repeat-report.md/json为最终正式返回结果；repeat-analysis.json为真实分析。
报告partial/verification_incomplete，feedback_stop=no_actionable_feedback，
本轮真实成功路径未触发反馈预算门槛，门槛行为由离线Graph回归验证。
2项研究、38条论断、2项参考来源、6个全文片段；两项location_status=valid。
支持度审核上下文超预算，所有support_status保留uncertain，不表示语义审核通过。
四维可行性：data conditional、methods conditional、compute unknown、validation reported_barrier。
reported_barrier仅代表文献报告的限制，不证明用户存在相同限制。
额外逐项检查40个论断证据指针均存在且原句匹配，全部片段location.kind=fulltext，
见citation-check.json；这不等于医学语义审核。

## 剩余问题与边界
P0：多篇全文的分析输入仍可能超过32000字符，首轮已真实复现context_limit。
P1：报告模型支持度审核可能因上下文预算跳过，本次最终报告属于此情况；
现有门禁如实保持uncertain。需要另行设计有界上下文选择，不能简单放宽引用。
预算门槛是基于实测的准入估算，不保证任意外部延迟都不会超时；
显式更小总预算仍可能无法完成首轮，不能保证返回结果。
本轮没有解决所有研究质量或正式医学验收门槛，没有推进下一Phase。
