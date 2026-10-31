"""Attach OpenAlex full text to already selected works. Abstracts stay out of evidence."""

from time import monotonic


class FulltextService:
    def __init__(self, source, store, embedder, *, clock=monotonic):
        self.embedder = embedder
        self.oa_source = source
        self.oa_store = store
        self.clock = clock

    def enrich(self, question, retrieval, *, deadline):
        if self.oa_source is None or self.oa_store is None:
            result = retrieval.model_copy(deep=True)
            result.warnings.append("fulltext_unavailable")
            return result
        from clinical_agent.application.oa_fulltext import enrich_openalex

        return enrich_openalex(self, question, result=retrieval, deadline=deadline)
