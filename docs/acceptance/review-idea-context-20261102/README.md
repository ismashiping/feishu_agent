# 审核用户想法上下文修复与复验（2026-11-02）

## 改动
application/report.py review_context新增original_idea、research_constraints和
与当前批次证据相交的idea_comparisons（论文ID/维度/用户原句/关系/理由/引用）。
domain/report.py审核提示说明用户想法是比较目标而非论文证据，不应自动认可关系。
仍逐批受原字符上限和期限约束，无缓存修改，无状态放宽。
新增回归先1 failed/2 passed，最终受影响59 passed（5.68s），Ruff通过、
mypy77文件通过、范围diff检查通过。覆盖无计划、有真实计划、真实用户原句和分批上限。

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_review_context_bounds.py tests/unit/test_citation_report.py tests/unit/test_feedback_agents.py tests/unit/test_openalex_report_contract.py --tb=short --basetemp=.artifacts/tmp/review-idea-final
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/review_idea_context.py
```

## 真实复验方法
原始基线 ../live-report-context-restored-20261102 的两份真实analysis/retrieval，
保持同一论断、证据及用户想法不变，只重新调用真实DeepSeek审核。
实际ReportBuilder和SnapshotVerifier，未用Mock。不是重新执行检索或全Graph。
对新旧claim_id/text逐项断言不变，保存每批完整输入、原始模型响应、耗时及对照。
两个请求均1批；cold上下文19392字符，repeat18719字符，小于32000。
此次真实并未触发多批，离线批次边界覆盖仍保留。

| 基线 | 新审核耗时 | 相似性5维结果（旧→新） | 新报告状态 |
|---|---:|---|---|
| cold | 6.891s | data uncertain→partial；methods partial→partial；outcomes partial→supported；population uncertain→partial；question partial→supported | verification_incomplete |
| repeat | 6.313s | data/methods/population/question保持supported；outcomes supported→partial | rejected |

cold新审核不再以“未提供用户约束”作为理由；仍指出公开性、人群排除标准等
未被原句支持，XGBoost数值截断。population虽然由uncertain变partial，其理由
仍为证据不足，不能解释成证实了人群范围。模型审核存在波动，不能把所有变化
严格归因为单一输入改变；本轮同时补齐上下文和澄清审核指令。
repeat的outcomes认为AUROC指标不等于结局定义，故降为部分支持。
repeat c10被判unsupported：47项纳入研究并非患者样本量，sample_size字段误标。
据原有规则报告rejected，未伪装verified。该抽取问题不在本轮修复范围。

## 结论
审核输入缺口已补齐，真实调用已接收到用户想法/约束/比较维度并返回可追溯判断。
并不保证审核全部通过；证据不足、字段错配、模型判断波动仍存在。
原检索、缓存、全文、分析结果未更改，本轮无数据库读写。
summary.json保存逐维审核理由前后对比，*-batches.json保存真实请求和响应。
