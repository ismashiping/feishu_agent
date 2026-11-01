# Planner relation contract alignment

Freeze scope: retain QueryPlan validators and query compilation. Clarify the model-facing
required/relation contract in schema and prompt; never silently relabel or drop constraints.
Input/output remain ClassificationRequest/QueryPlan. Invalid outputs remain extraction_failed.
Captured actual failing response: docs/acceptance/planner-20261101/raw-before.json.
Tests replay that response and assert rejection; model-facing schema must explicitly state
which relation values permit required=true. Real revalidation uses original ICU/AKI sample.
Run offline planner regressions before two real report calls. No timeout or search changes.

## Implementation and offline verification
Captured actual response in docs/acceptance/planner-20261101/raw-before.json: risk prediction
was related_concept with required=true. Preserved original response; no silent normalization.
Changed only domain/pico.py: model-facing required field description and explicit prompt rule,
including a faithful required task anchor and optional related expression example.
Existing QueryPlan validation and retrieval compilation unchanged.
Regression includes captured-response rejection, model schema rule, and valid anchor + optional
expansion preserving task in compiled queries. First run 1 failed/1 passed; final affected
selection 89 passed. Ruff src/tests, mypy src (77 files), scoped diff check passed.
Commands:
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_planner_live_contract.py tests/unit/test_pico.py tests/unit/test_recall_relations.py tests/unit/test_openalex_report_contract.py tests/unit/test_intent_routing.py tests/unit/test_query_plan_diagnostics.py --tb=short --basetemp=.artifacts/tmp/planner-expanded
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
```
Real before/after evidence remains in docs/acceptance. This prompt/schema clarification does
not guarantee every future model response is valid; invalid outputs continue to fail fast.
