# Compact bounded model contexts

Scope: application analysis/report model inputs only. Audit DTOs, sources, identity and
citation gates remain complete. Remove metadata unused by model reasoning and duplicate
fulltext copies; preserve original question, required research constraints, quote IDs,
verbatim evidence, document ownership and locations. Keep32000-character hard cap.
Regression: replay saved real retrieval/analysis with offline models, ensure model invoked,
all evidence preserved and review no longer skipped solely for duplicate metadata.
If irreducible input still exceeds cap, retain explicit context_limit/uncertain behavior.
No new dependencies, budget expansion, evidence truncation or semantic approval claims.

## Offline verification (2026-11-02 continuation)
Saved-real-data regressions first failed2/2: three-paper analysis never reached model,
and two-paper report skipped reviewer. After compacting unused metadata, reviewer ran;
three-paper case still exceeded limit. Added deterministic whole-sentence selection:
reduce papers with most sentences first, remove longest sentence within that group,
retain at least one sentence per paper; never truncate a quote. Mark limitations and partial
when selected quotes reduced. Complete analysis.sources and citation gates unchanged.
If minimum input still cannot fit, explicit context_limit remains.
Final affected regression106 passed (8.75s), Ruff src/tests passed, mypy77 files passed,
scoped diff check passed. A temporary Ruff import-order and missing counts type annotation
failure was corrected before final checks.

Commands:
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_compact_context.py tests/unit/test_citation_report.py tests/unit/test_evidence_analysis.py tests/unit/test_analysis_assembly.py tests/unit/test_openalex_report_contract.py tests/unit/test_feedback_agents.py --tb=short --basetemp=.artifacts/tmp/context-final2
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
```
Audit payloads retain all evidence. Only model-facing projection is compacted: analysis keeps
original idea, intent and constraints, source ownership/locations, quote catalog and schema;
review keeps claims, original passages/locations and source notices without duplicated
FulltextPassage objects. Source provenance verification still runs before review.
No increased context limit, new dependencies or prompt-external knowledge.
