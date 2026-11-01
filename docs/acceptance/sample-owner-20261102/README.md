# 样本量主体归属修复（2026-11-02）

## 问题与最小修改
此前final-live-batched-20261102/repeat中，综述表格单项原始研究行的23950/3954
被填到综述sample_size，逐字引用正确但主体错误，模型审核未识别。
本轮修改：
- domain/analysis.py FieldSelection新增内部sample_size_scope：current_study、
  review_aggregate、cited_study、unknown，可空表示尚无归属依据。
- application/analysis.py build_draft在既有引用ID/所属论文校验之后，
  原始研究仅接纳current_study，systematic_review仅接纳review_aggregate；
  cited_study/unknown/空或与类型不符时保留缺失，不将子研究数字当当前研究样本。
  sample_size不再从模型推断填充，只保留明确归属的报告事实。
- domain/report.py审核指令要求检查数字主体，患者/住院记录、训练/验证队列范围，
  不能因字面匹配就认可综述汇总样本。
公共AnalysisResult未新增字段；来源和原文不删除；缓存/检索/Graph未改。
这是当前AnalysisSelection契约，历史AnalysisDraft隔离路径未借此重构。
模型仍可能错标scope，不能证明语义永远正确，审核仍必须保留。

## 离线过程与结果
先新增反例3 failed/5 passed：两个新增字段不被原schema接纳，缺失scope则
错误进入sample_size。测试最初姓名缩写被断句，改为完整无缩写句子以准确测试主体。
最终109 passed（8.35s），Ruff通过、mypy77文件通过、范围diff检查通过。
原有显式样本测试按新内部契约补scope，没有删除原样本量/单位断言。
覆盖2532患者、8000住院记录、综述汇总12000参与者；单篇被引研究、归属不明、
类型不符和推断补造均不进入当前研究sample_size。
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_sample_size_semantics.py tests/unit/test_analysis_assembly.py tests/unit/test_evidence_analysis.py tests/unit/test_review_context_bounds.py tests/unit/test_openalex_report_contract.py tests/unit/test_citation_report.py --tb=short --basetemp=.artifacts/tmp/sample-owner-final
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
.venv/Scripts/python.exe -X utf8 docs/acceptance/live-20261101/check_sample_owner.py
```

## 真实复验
使用原repeat-fulltext_rag.json和repeat-plan.json，同样例、同一实际全文证据，
真实模型重新提取并经ReportBuilder审核，无Mock、无改写模型结果。
两篇都识别为systematic_review，原始reported列表均未选择sample_size，
最终均value=null、basis=not_reported；没有再次将表格单项研究挂为综述样本。
抽取10.828秒，审核9.265秒，无unsupported条目，报告verification_incomplete。
raw-selection.json/analysis.json/report.json/report.md/result.json保留。
这不是重新执行全Graph或实时检索验收，不覆盖所有可能的主体误标。
本轮完成后停止，不扩大到通用数量模型或其余字段重构。
