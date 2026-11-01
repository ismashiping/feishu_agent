# Fulltext candidate fallback and diagnostics

Scope: existing OpenAlex download candidates and budget diagnostics only.
Input: OpenAlexRecord, shared monotonic deadline and mutable HTTP count.
Output: existing Acquisition; failures retain public fulltext codes with AcquisitionError.basis.
Single HTTP timeout and file size failure allow the next existing candidate. Shared deadline
or HTTP limit stops all attempts. No new URLs, relaxed security, retries or resource limits.
Preserve candidate order/dedup/cap, SSRF checks, redirects, identity and format validation.
Diagnostics: safe paper ID, candidate index, reason, elapsed time and remaining budget;
never URLs, response contents or credentials. Unexpected infrastructure failures must log
as failures, not no-address results.
Acceptance: offline controlled clock and HTTP tests for timeout/size/format fallback,
all failures, exhausted shared count/deadline, missing URL and existing security/identity
regression. Run prior report evidence contract regression. No live acceptance claimed.

## Verification (2026-11-01)

- Reproduction: 5 failed, 1 passed; timeout and file size aborted candidate fallback.
- Initial fix: 6 passed. Added pre-exhausted count/deadline and streaming deadline tests.
- Intermediate regression: 11 failed, 107 passed after Ruff automatic unused-binding
  cleanup removed a conditionally reused exception binding. Fixed with a separate
  caught/error binding; reran the full affected selection.
- Final affected regression: 118 passed in 10.88s. Includes prior report evidence contract,
  missing URL, identity mismatch, invalid URL/redirect safety, PDF parsing and cache tests.
- Ruff src/tests passed; mypy src passed (77 source files); scoped diff check passed.
- No existing tests changed. No real network/model/database tests performed.

Commands:
```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_fulltext_fallback.py --tb=short --basetemp=.artifacts/tmp/fallback-red
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/unit/test_fulltext_fallback.py tests/unit/test_oa_fulltext.py tests/unit/test_fulltext_rag.py tests/unit/test_openalex_report_contract.py tests/unit/test_citation_report.py tests/unit/test_evidence_analysis.py tests/unit/test_feedback_agents.py --tb=short --basetemp=.artifacts/tmp/fallback-final
.venv/Scripts/ruff.exe check src tests
.venv/Scripts/python.exe -X utf8 -m mypy src
git diff --check -- src/clinical_agent/integrations/oa_fulltext.py src/clinical_agent/application/oa_fulltext.py
```

Compatibility: fulltext_budget and fulltext_timeout strings retained; basis distinguishes
file_size/http_limit/deadline/http_timeout. HTTP timeout now uses AcquisitionError
(ValueError) rather than TimeoutError; repository fetch callers already accept ValueError.
Upper layer warnings append stage_deadline/paper_limit/chunk_limit basis. Consumers should
not assume warning strings without their existing semicolon detail suffix. Unexpected
upper-layer errors retain fulltext_failed and use safe exception-type logging.
Remaining limits and candidate ordering unchanged. Live URL availability, authentication,
external latency and complete real RAG/report acceptance remain unverified.
