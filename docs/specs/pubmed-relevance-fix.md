# PubMed relevance correction

Root cause: domain/pubmed.py query_text flattens question and expansions with OR. ESearch retrieves at most max_results, EFetch fetches only those IDs, application/pubmed.py further caps top_k. merge_sources reserves local slots without topical comparison. Individual historical PMID losses cannot be attributed without request snapshots.

Scope: explicit bounded synonym concept groups in existing QueryPlan; OR within groups and AND across groups; preserve explicit query override, ambiguity handling and all transport budgets. No classification label change.

Acceptance: deterministic query tests, no dependence on PubMed ranking. Remaining work: bounded fallback provenance, topical selection and answer rendering; known PMID metadata fixtures require verified source snapshots.
