# SPEC: on-demand fulltext enrichment

Selected PubMed evidence remains the discovery and governance boundary. Add optional enrichment after scout selection, before generation. Keep PubMed abstract snapshots unchanged. Structured, licensed PMC OA BioC passages are supplemental evidence with stable IDs and original offsets. No DOI/title fuzzy identity matching, PDF crawler, new agent, model, or database service.

Persistence requires a minimal new cache table in existing PostgreSQL: PMID + pipeline/model signature + expiry, atomic JSON passage snapshot and pgvector chunks. Never publish incomplete indexes. Cache hits bypass download and passage embedding. TTL permits revalidation; content hashes permit unchanged-content reuse. Limit 3 papers, 9 requests, 20 seconds, 128 chunks/paper, 2 context passages/paper, bounded response bytes; total research deadline wins.

Tests: identity mismatch; unknown license; malformed XML; abstract fallback; section/offset retention; repeated content; selected-only search; per-paper cap; deadline/download cap; untrusted instructions remain data. Real external and database tests must be reported separately. Existing citation checks and 24000-character limit remain.

Compatibility: new optional ResearchService enrichment port and supplemental passage fields default empty; existing callers continue unchanged. Supplemental passage IDs must pass the existing citation gate before use. No migration is applied automatically.
