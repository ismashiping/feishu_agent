# 分批上下文审核验收（2026-11-02）

本轮保留工作区已有分析侧精简与句子裁剪，新增报告审核有界分批。
每批只传完整论断、所属论文元数据、实际引用原句和原定位；不传无关全文快照。
按原max_context_characters分批，不提高预算、不截断原句。模型返回必须恰好覆盖
该批；缺少证据/信息缺失的条目仍uncertain，失败批次及未运行批次保持uncertain。
单条无法容纳时明确记录；现有deadline仍有效。

测试：首次fixture缺少case导入，修正后旧实现回归1 failed（审核整体跳过，0批）；
实现后首轮56 passed，最终相关分析/报告回归89 passed（9.29秒）。
分析回归确认裁剪后模型上下文<=24000、两篇都有句子、来源仍保留；
审核回归确认每批<=5000、原句存在、所有论断恰好覆盖一次。
Ruff src/tests通过，mypy77文件通过，范围内diff检查通过。
没有把工作区原有分析修复声称为本轮新实现。

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_review_context_bounds.py tests/unit/test_citation_report.py tests/unit/test_feedback_agents.py tests/unit/test_openalex_report_contract.py tests/unit/test_analysis_output_budget.py tests/unit/test_evidence_analysis.py --tb=short --basetemp=.artifacts/tmp/context-final
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
```

真实重验：先因记录目录已存在退出，改用本目录后在docker inspect失败。
```powershell
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/run_reports_context.py
docker ps -a --format '{{.Names}} {{.Status}}'
```
原clinical-agent-e2e-api-1不存在，docker ps -a为空；与既有目录记录的历史Docker
管道故障不同，本轮引擎可响应但没有原容器。未重建环境、未替换配置、没有模型
请求/全文下载/数据库写入。本轮真实报告返回、分批模型支持度审核均未验证。
此前2026-11-01的缓存命中和报告不替代本轮结果。

恢复条件：恢复现有验收配置、模型API和独立测试数据库运行环境后，用新产物目录
运行脚本。继续保留付费调用授权；不需要再次授权，但不得擅自重建未知数据环境。
多批可能增加调用数和耗时；没有承诺任意论文数量下都能完成全量审核。
