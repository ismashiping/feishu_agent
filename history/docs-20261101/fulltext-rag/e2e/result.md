# Final E2E result — 2026-10-29

## Verdict
Final v3 processing/storage/retrieval and real-generation/citation stages pass. A fully live final-v3 E2E run does NOT pass: PMC acquisition failed with TLS UNEXPECTED_EOF twice. Earlier v2 full live acquisition/E5/storage/retrieval did pass, but still indexed redundant abstracts; do not substitute that result for final-v3 live acceptance.

This tests workspace Python ResearchService/LangGraph, not the already-running container HTTP deployment. Existing containers were reused; production schema was not migrated. Test migrations used unique temporary schemas, removed afterwards. No existing volumes or business records were removed.

## Actual final results
Selected live PubMed PMID 17299597 / PMC1790863. Final acquisition source is previously identity/license-verified real BioC XML fixture (not fresh PMC network).

| Case | Processing/generation mode | Time | Context characters | Retrieved body chunks | Passage embedding calls |
|---|---|---:|---:|---:|---:|
| Abstract | live PubMed; fixed generator | 2.22s | 6625 | 0 | 0 |
| Fulltext first use | real XML replay + real E5/PG; fixed generator | 26.52s | 8810 | 2 | 1 |
| Fulltext cache hit | real PG cache + real E5 query; fixed generator | 1.69s | 8810 | 2 | 0 |
| Abstract real generation | captured context + configured real LLM + actual citation gate | 3.83s | 6625 | 0 | 0 |
| Fulltext real generation | captured context + configured real LLM + actual citation gate | 3.41s | 8810 | 2 | 0 |

66 body chunks persisted in temporary PostgreSQL tables. Cache repeat performed zero source acquisitions and zero passage embeddings. Replay source acquisition counters reflect fixture reads, not HTTP downloads. Context cost rose ~33%; no actual provider token usage/billing was captured. Raw vector payload is about 198 KiB, plus stored text/JSON and PostgreSQL overhead. Existing E5 and LLM reused; no new model or paid service.

Real LLM comparison: abstract answer acknowledges missing estimation details; fulltext answer identifies maximum-likelihood estimation, likelihood-ratio confidence intervals, and the two-virus extrapolation limitation. Retrieved body sections were RESULTS / Estimates of Phenotypic Complexity for VSV and ΦX174 and DISCUSS / Viral Estimates of Phenotypic Complexity. Model statements are traceable to supplied body passages; this single example is not a general medical accuracy evaluation. Paper is a pipeline test, not liver-cancer domain validation.

## Fixes prompted by tests
- Adapt blank LlamaIndex tokenizer calls to strict E5 count_tokens interface.
- Repair same-version LlamaIndex installation with copied resources (hardlinks were rejected by runtime).
- Separate 15s acquisition budget and 35s enrichment budget, within original 90s research deadline.
- Exclude references, standalone titles and duplicate abstract paragraphs; retain titles as subsection locators. Bump pipeline signature v3.
- Accept verified fulltext IDs in actual citation gate, preserving paper ownership and exact kind=fulltext offsets.

## Regression
Final core/fulltext/research: 65 passed. Renderer/synthesis/migration: 93 passed. Citation-report/PubMed boundary: 56 passed. Suites overlap; counts are not a unique combined total. Ruff and modified-file diff checks passed. No full-suite rerun during this E2E follow-up.

## Evidence
- summary.json: final source-replay infrastructure cases
- live-final-summary.json: failed live final-v3 attempt
- real-generation-summary.json: actual real model and gate results
- *-context.json: exact evidence contexts
- *-real-draft.json and *-real-answer.json: actual model claims and trusted citation output

Remaining acceptance: successful final-v3 live PMC network run, deployed HTTP smoke after reviewed migration/deployment, analyze/report fulltext integration and broader multilingual/scientific retrieval quality cases. Original no-fulltext fallback remains covered by unit tests; the TLS-failure live runs additionally showed valid abstract answers with no false fulltext-success claim.
