# sample_size语义修复与真实复验（2026-11-02）

改动仅domain/analysis.py：FieldSelection/InferenceSelection的模型字段说明和分析指令。
明确sample_size为实际患者/参与者、住院记录、实验样本数，保留单位和范围；
综述纳入研究篇数、预测次数、性能指标不能填入；没有适用计数就不报告。
综述明确给出汇总参与者数仍可保留，不用研究类型一刀切。
未新增输出字段、未修改引用/审核状态规则、缓存或检索逻辑。
这是模型契约澄清，不是程序可以确定医学语义正确的证明；错误仍由审核暴露。

回归先1 failed/2 passed，最终71 passed（5.03秒）。
覆盖2532患者、8000住院记录、综述汇总12000参与者保留原单位，以及47项研究
可进入design而sample_size留空；已有证据/审核回归继续通过。
Ruff src/tests、mypy77文件、范围diff检查通过。
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_sample_size_semantics.py tests/unit/test_analysis_assembly.py tests/unit/test_evidence_analysis.py tests/unit/test_review_context_bounds.py tests/unit/test_openalex_report_contract.py --tb=short --basetemp=.artifacts/tmp/sample-size-final2
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/check_sample_size.py
```

真实复验使用 ../live-report-context-restored-20261102/repeat-fulltext_rag.json 和原计划：
相同真实综述论文及片段，重新调用真实模型提取和真实ReportBuilder审核；无Mock。
不是全Graph重新检索验收，也不将新抽取全部变化归因为本次提示修改。
抽取8.062秒，审核5.531秒；sample_size.value=null、basis=not_reported。
报告没有unsupported条目，仍verification_incomplete，未伪造verified。
原始模型selection、analysis、report.json/md及result.json保留在本目录。
不证明未来所有输入都不会误标；本轮未推进后续任务。
