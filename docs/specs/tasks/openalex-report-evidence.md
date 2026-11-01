# OpenAlex analysis/report evidence contract

Scope: only analysis and report evidence propagation. No retrieval/download changes.
Input: RetrievalResult with zero or more OpenAlex hits and fulltext passages.
Output: AnalysisResult and ReportResult retain all model-visible passages with paper identity,
source and location. Abstract IDs are never accepted as OpenAlex claim evidence.
Use existing DTOs and build_answer validation. No new data model.
No fulltext yields insufficient_evidence. Unknown references fail; cross-paper selections
must not become reported facts. Preserve existing identity and snapshot checks.
Acceptance: tests/unit/test_openalex_report_contract.py covers first/second/third passages,
mixed availability, no fulltext, empty retrieval, unknown and cross-paper references through
ResearchService.report. Offline model/retrieval doubles only; real snapshot verifier and graph.
Run targeted pytest then affected regression, Ruff and mypy. This is not live acceptance.

## Execution record (2026-11-01)

- First new-test run: 9 failed / 1 passed because the synthetic retrieval fixture
  did not assign stable ranks. Corrected fixture before changing production code.
- Valid pre-fix regression: 8 failed / 2 passed. Confirmed missing later passages
  and citation_invalid for reports with hits but no fulltext.
- After minimal business fix: 10 passed. Added 3 report tampering rejection cases.
- Affected regression first run: 199 passed / 9 setup errors (Windows system temp
  directory permission); rerun with workspace basetemp: 208 passed, 15.54 seconds.
- Ruff src/tests passed; mypy src passed (77 source files); scoped diff check passed.
- Existing tests were not changed. Cross-paper quote selection remains omitted
  under the existing selection contract; forged output pointers are rejected.
- Offline retrieval/model doubles were used. Real graph, analyzer, report builder,
  citation validation, rendering and snapshot verifier ran. Reviewer deliberately
  reports uncertain, so successful evidence transport is not semantic approval.
- No real network, model API, database or whole-project acceptance performed.

Commands (PowerShell, repository .venv):

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_openalex_report_contract.py --tb=short
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_openalex_report_contract.py tests/unit/test_citation_report.py tests/unit/test_evidence_analysis.py tests/unit/test_analysis_assembly.py tests/unit/test_analysis_epistemic_contract.py tests/unit/test_feasibility_analysis.py tests/unit/test_feedback_agents.py tests/unit/test_oa_fulltext.py tests/unit/test_research.py --tb=short --basetemp=.artifacts/tmp/report-contract-final
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
git diff --check -- src/clinical_agent/application/analysis.py src/clinical_agent/application/report.py
```

Unresolved outside scope: download fallback and budget diagnosis, real fulltext
availability and live combined end-to-end acceptance. Existing unrelated worktree
changes were preserved. No Phase completion is claimed.
