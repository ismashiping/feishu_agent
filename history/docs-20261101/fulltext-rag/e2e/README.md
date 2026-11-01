# End-to-end test notes (2026-10-29)

Scope: selected PMID 17299597 via live PubMed request and existing governance; live official PMC identity/license/BioC; actual local multilingual E5; actual existing PostgreSQL/pgvector in unique temporary schema; actual migration; ResearchService graph and citation gate. Containers and production schemas unchanged. Test schema removed in finally.

Initial attempts exposed these independent failures:
1. Cold fulltext silently fell back (assertion correctly rejected it).
2. Isolated reproduction showed SentenceSplitter requests token counts for empty metadata; E5 count_tokens rejects blank strings. Fixed the LlamaIndex tokenizer adapter to return zero tokens for blank strings. Added strict-token-counter regression; related suite: 74 passed.
3. Live reruns encountered PubMed timeout and generation_failed. These are recorded failures, not passing fulltext tests.
4. Detailed E2E diagnostics identified a PermissionError reading LlamaIndex packaged NLTK stopwords installed as uv hardlinks. Reinstalled exactly llama-index-core 0.14.22 with --link-mode copy in the same venv. No relaxation of runtime access checks.

Test script supports FULLTEXT_E2E_REAL_LLM=1 for real generation. Default uses a deterministic quoted-evidence generator; that verifies context/citation plumbing but is explicitly not model-quality acceptance. summary.json records generation mode. Outputs contain public paper evidence only, no secrets.

Follow-up: after copied-resource repair, real E5 reached embedding but exceeded the initial 20-second enrichment budget. Excluded BioC REF/REFERENCES passages (33 reference paragraphs in the chosen paper). Split network acquisition budget (15 seconds total) from total enrichment budget (35 seconds), still bounded by existing ResearchService deadline minus 5 seconds. Targeted regression after change: 63 passed. Earlier 20-second documentation describes the initial implementation and is superseded by these measured limits.

Additional E2E-driven fixes:
- Permit generated citations to verified fulltext chunk IDs, resolve them to the selected parent paper, and emit kind=fulltext with exact source offsets. Unknown IDs remain rejected. A direct-fulltext-citation gate regression passes.
- BioC title_* nodes become section/subsection locators instead of standalone vector evidence. Initial model output honestly reported that retrieved headings could not support methods; this failed the quality goal despite passing plumbing.
- Exclude reference lists, redundant ABSTRACT and TITLE passages. Pipeline signature v3 invalidates old heading/abstract indexes.
- Targeted core tests after citation/heading fixes: 65 passed. Renderer/synthesis/migration regression: 93 passed. Fulltext focused suite: 11 passed. These overlapping counts must not be summed as unique tests.

Final live v3 attempt and one retry failed at PMC acquisition with ConnectError / SSL UNEXPECTED_EOF_WHILE_READING. The live test returned a valid abstract answer, but correctly failed the required-fulltext assertion; preserved in live-final-summary.json. No relaxation of TLS validation or unbounded retries.

Final v3 verification uses the previously identity/license-verified XML fixture as the PMC source (explicit replay), with live PubMed selection, real E5, real PostgreSQL and actual citation gate. Acquisition-call counters in this replay count fixture reads, NOT network downloads. summary.json source_mode distinguishes this from the earlier fully live v2 pass. Real-generation replay is separately labeled and uses captured contexts rather than refetching the source.
