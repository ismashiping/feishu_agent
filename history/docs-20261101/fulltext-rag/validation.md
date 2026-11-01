# Validation record

- RED: pytest tests/unit/test_fulltext_rag.py failed collection because pmc_fulltext did not yet exist.
- GREEN: 6 fulltext tests passed (actual installed llama-index-core 0.14.22).
- Focused regression: fulltext + ResearchService + Feishu sender, 133 passed.
- Runtime regression: api_runtime + command_runtime, 15 passed. Initial attempt had 8 temp-directory permission errors; rerun with workspace --basetemp passed.
- Earlier research/synthesis regression: 66 passed.
- Real external success: PMID 17299597 -> PMC1790863, CC BY, 70318-byte BioC XML, 120 passages. Saved tests/fixtures/pmc1790863.bioc.xml. Fixed source fixture tests are offline replays, not fresh external tests.
- Real external negative: PMID 17081967 had no verified PMCID in official identity response; acquisition refused.
- Real external discovery: legacy OA service returned HTTP 404. Replaced with official OAI license metadata and reverified the success case.
- Real database: docs/fulltext-rag/postgres_smoke.py passed publish, selected-PMID search isolation, cache hit, signature mismatch, content renewal and rollback after partial publication failure, against existing Docker PostgreSQL using temporary schema.
- No paid LLM calls. No genuine generated-answer A/B quality or token-billing comparison; do not infer medical answer quality from mocked tests.
- Full offline regression result is appended after completion below.

Full regression command: `.venv/Scripts/python -m pytest -q --basetemp=.pytest_fulltext_regression` initially completed with 1324 passed, 2 failed, 122 deselected (304.55s). Failures: safe reason-code mapping (fixed during run) and a pre-existing migration-head assertion requiring the previous head (updated to p1001_0008). New focused suite now includes deadline/no-download and fulltext citation roundtrip: 8 passed. Failed-test rerun result is recorded below. This is not a claim that the entire full suite was rerun after fixes.

Ruff passed all newly introduced production modules and modified integration modules. `git diff --check` passed (line-ending warnings only). Python compile checks passed.
`pytest tests/unit/test_fulltext_rag.py tests/unit/test_ingestion_mapping.py -q --basetemp=.pytest_fulltext_failures`: 19 passed, including both initially failing cases. No full-suite rerun after these fixes.
