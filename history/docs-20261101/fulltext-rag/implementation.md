# Investigation and implementation record

## Existing capabilities reused
- QueryPlan and LiteratureScoutAgent retain discovery and final candidate selection.
- PubMedRetrievalService/PubMedClient retain identity, snapshots, request gate and governance.
- EvidenceHit gains optional supplemental passages. Its original abstract chunk and source hash remain unchanged.
- Existing multilingual-e5-base (768 dimensions, pinned revision), passage prefix, CPU backend and embedding lock are reused. No paid service or new model.
- Existing PostgreSQL/pgvector gains two additive tables via p1001_0008. Existing document/chunk constraints prohibit representing PMC XML, so they were preserved.
- ResearchService and its LangGraph remain. Optional fulltext dependency defaults to None; API and CLI runtime wire it with a managed httpx client. Feishu paths using open_research inherit that wiring.
- GenerationEvidence and CitationEvidence gain optional fulltext lists. Parent abstract chunk IDs remain the citation gate identity; attached passage IDs, PMID, PMCID, DOI, section, original BioC offset, hash, license and URL remain available in structured output. The gate checks identity, not medical entailment.

## Acquisition and indexing
Only selected PubMed hits enter enrichment. Cache-first lookup uses pipeline/model signature and 30-day validity. On miss: official PMID/PMCID conversion, official OAI JATS license metadata, official OA BioC XML. Unknown/custom/restrictive licenses are rejected; current conservative whitelist accepts CC BY 4.0 / CC0 1.0 URI metadata. No paywall bypass, PDF crawling, retries or unbounded downloads.

The legacy oa.fcgi endpoint actually returned 404 during testing on 2026-10-29; implementation uses OAI instead. References: https://pmc.ncbi.nlm.nih.gov/tools/developers/ and https://developers.llamaindex.ai/python/framework/module_guides/loading/ingestion_pipeline/transformations/ .

Each BioC paragraph becomes a LlamaIndex Document. IngestionPipeline with SentenceSplitter keeps paragraph/section boundaries, 300 token target and 30 overlap using the existing token counter. Each node must map back to an actual source substring. Maximum 128 nodes; excessive documents fall back instead of publishing partial indexes. Atomic publication stores JSON passage metadata and vectors in existing PostgreSQL. Identical fresh signatures bypass download and passage embeddings; expired unchanged content revalidates hash and renews expiry without passage embedding.

## Retrieval and costs
A single question embedding is reused across up to 3 selected papers. pgvector cosine search is restricted by selected PMID; at most 2 passages per paper. No extra LLM call. The model receives abstract plus selected supplemental passages, never whole papers. Context selection removes supplementary passages from the end until the existing 24000-character serialized limit is satisfied and records fulltext_context_trimmed. If the original abstract context already exceeds the limit, existing context_limit failure remains.

Per request: at most 3 selected papers / 9 HTTP calls, 5 MiB per response, 20-second acquisition/processing budget bounded by research deadline minus a 5-second reserve. In-flight HTTP/model work is cooperative; individual blocking operations can consume their configured timeout. Cache stores at most 128 vectors x 768 x 4 bytes (~384 KiB raw vector payload) per processed paper, plus JSON text metadata and PostgreSQL overhead. Two context passages/paper; actual generated-token and quality differences have NOT been measured.

## Deliberate incomplete boundaries
This is a working answer-path foundation, NOT full task acceptance.
- Production migration has not been applied; API safely falls back when tables are absent. Apply reviewed p1001_0008 through the existing migration process before enabling persistent production enrichment.
- analyze/report have separate evidence-pointer and quote review contracts. They remain abstract-only; do not claim fulltext analysis there.
- No PDF fallback or supplementary attachment acquisition.
- No distributed pre-embedding lease: concurrent first requests can duplicate download/embedding work, although atomic publication prevents incomplete indexes.
- Content changes are detected at TTL revalidation, not immediately; old content embeddings are not reused individually after a changed document hash.
- Licensing is conservative and does not cover every permitted PMC license.
- Citations attach fulltext passages under the existing parent evidence ID, rather than allowing direct generated references to individual fulltext chunk IDs.
- Still needed: generated answer A/B comparison with the same question/paper, multilingual Methods/Results retrieval quality evaluation using the real E5 model, richer failure/budget/injection tests, and full report-path integration.

## Docker
Read-only inventory found clinical-agent-e2e postgres/redis/api/feishu_bot containers. Compose name fixed to clinical-agent-e2e. No up/down/build/recreate, volume removal or existing-table migration was performed. Adapter verification used a UUID-named temporary schema and removed only that schema.
