# 审核输出截断诊断和修复（2026-11-02）

## 根因已证实
真实回放final-live-20261102第一批38条：finish_reason=length、output_tokens=1500，
恰好达到配置max_tokens1500，input_tokens11011。模型适配器按既有规则拒绝非stop响应，
不是文献证据不足或报告审核结果汇总丢失。before-diagnostic.json保留安全诊断。
此前仅按输入字符分批，未限制输出结果条数，导致38/40条一次生成被截断。

## 最小修改
application/report.py：每批最多6条完整论断，同时满足原字符限制；共享原期限。
domain/report.py：审核basis要求简洁一句、最多200字符（指令，不伪造截断文本）。
integrations/llm.py：安全错误details新增finish_reason白名单，用量诊断继续保留。
不提高公共max_tokens、不接受截断JSON、不取消超时、不无限重试。
错误批次和未执行条目仍not_reviewed/uncertain。
6条上限按当前1500-token配置保守选择，不保证任意小预算/模型都能完成。

## 离线
先1 failed/4 passed复现多论断未分批；首次受影响62 passed/6 failed，
原因是反馈fixture将审核调用数当作报告轮数。改为按每轮c1计数，保留轮数断言。
最终69 passed（11.65秒），包括输出条数、恰好覆盖、无重复、截断安全诊断。
Ruff、mypy77文件、范围diff检查通过。
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_review_context_bounds.py tests/unit/test_citation_report.py tests/unit/test_feedback_agents.py tests/unit/test_openalex_report_contract.py tests/unit/test_langchain_generation.py --tb=short --basetemp=.artifacts/tmp/review-output-final2
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
```

## 真实复验
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/diagnose_review_output.py
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/review_output_fixed.py
```
保持final-live-20261102保存的同一analysis/retrieval/全部论断，调用真实模型和
ReportBuilder、SnapshotVerifier；无重新生成论断、无Mock、无检索/缓存修改。
新旧claim_id/text逐项断言相同。逐批实际输入和原始输出保存在相邻
../review-output-budget-fixed-20261102/*-batches.json（仅科研数据，无凭据）。

| 组 | 真实审核批数 | 覆盖 | 最大输入字符 | 耗时 | supported/partial/uncertain |
|---|---:|---:|---:|---:|---:|
| first | 7 | 38/38 | 10059 | 11.735s | 18/17/3 |
| repeat | 9 | 49/49 | 10236 | 13.781s | 36/5/8 |
每批最多6条，逐批响应ID恰好匹配、跨批无重复无遗漏，全部basis非not_reviewed，
无审核失败/跳过提示，报告仍verification_incomplete。audit.json保存独立覆盖核查。

## 结论及边界
本次真实“同证据重新审核”截断修复通过；剩余状态来自部分支持/不确定，未改verified。
本轮没有重跑完整ResearchService.report，也没有重新验证实时检索/缓存命中；
此前全链路失败记录仍保留，不用局部复验替换整体验收事实。
后续若要标记当前版本完整验收，需再次通过正式入口测量总耗时与多批审核。
