# Bounded report budget and feedback admission

Scope: ResearchLimits defaults and ResearchService fulltext reservation/feedback gate.
Measured first passes took ~80 seconds; feedback lost final outputs at90 seconds.
Default total180s, retain per-call and fulltext60s limits; reserve60s after fulltext.
Feedback admission requires remaining90s for methods,135s for scout (45s search,
60s fulltext,30s downstream allowance). These are bounded admission thresholds,
not guarantees. If insufficient, return current report with budget_limit; preserve rejected
status and never promote uncertain claims. Existing round limit remains.
Tests use actual graph with controlled post-review clock advancement. Real validation uses
same ICU/AKI idea; report and cache evidence must be measured, never assumed.

## Offline verification
Before fix: 2 feedback-budget tests failed with research_timeout; 11 existing passed.
After fix: first affected run107 passed/2 failed: old tests hardcoded91 seconds for
old90-second default. Updated their elapsed time to ResearchLimits().max_seconds+1,
retaining timeout assertion. Final affected selection109 passed (5.02s).
Ruff src/tests passed; mypy src passed77 files; scoped git diff --check passed.
Commands:
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_feedback_agents.py tests/unit/test_research.py tests/unit/test_openalex_report_contract.py tests/unit/test_citation_report.py --tb=short --basetemp=.artifacts/tmp/budget-final2
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
```
Compatibility: default request ceiling180s instead of90s; explicitly supplied limits remain
respected. feedback_stop may now be budget_limit (existing free string field). No citation
or safety gates relaxed. Admission thresholds are conservative estimates based on observed
costs, not a guarantee against arbitrary external latency. No unknown exception fallback or
new abstractions added. Rejected reports remain rejected on budget stop.
