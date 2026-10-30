"""Bounded LlamaIndex enrichment of already selected PubMed evidence."""

from hashlib import sha256
from time import monotonic
from uuid import NAMESPACE_URL, uuid5

from clinical_agent.domain.fulltext import FulltextPassage
from clinical_agent.domain.governance import BLOCKED_STATUSES
from clinical_agent.domain.retrieval import retrieval_embedding_info

SIGNATURE = "pmc-bioc-llama-0.14.22-v3:" + retrieval_embedding_info().model_dump_json()


class FulltextService:
    def __init__(self, source, store, embedder, *, oa_source=None, oa_store=None, clock=monotonic):
        self.source, self.store, self.embedder = source, store, embedder
        self.oa_source, self.oa_store = oa_source, oa_store
        self.clock = clock

    def enrich(self, question, retrieval, *, deadline):
        from llama_index.core import Document
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.node_parser import SentenceSplitter

        result = retrieval.model_copy(deep=True)
        deadline = min(deadline, self.clock() + 35.0)
        acquisition_deadline = min(deadline, self.clock() + 15.0)
        selected = {}
        for hit in result.hits:
            if hit.document.pmid and hit.document.source_type == "pubmed":
                selected.setdefault(hit.document.pmid, hit)
        query = None
        for index, (pmid, hit) in enumerate(selected.items()):
            reason = "fulltext_budget"
            if index < 3 and self.clock() < deadline:
                try:
                    if hit.document.governance.status in BLOCKED_STATUSES:
                        raise ValueError("fulltext_governance_blocked")
                    payload = self.store.load(pmid, SIGNATURE)
                    if payload is None:
                        pmcid, license_name, url, raw, passages = self.source.fetch(
                            pmid, acquisition_deadline
                        )
                        digest = sha256(raw).hexdigest()
                        reuse = getattr(self.store, "reuse_content", lambda *args: False)
                        if not reuse(pmid, SIGNATURE, digest):
                            chunks = []
                            for section, offset, body in passages:
                                if section.split(" / ", 1)[0].upper() in {
                                    "REF",
                                    "REFERENCES",
                                    "ABSTRACT",
                                    "TITLE",
                                }:
                                    continue
                                # One source paragraph per Document prevents section mixing.
                                nodes = IngestionPipeline(
                                    transformations=[
                                        SentenceSplitter(
                                            chunk_size=300,
                                            chunk_overlap=30,
                                            tokenizer=lambda s: list(
                                                range(self.embedder.count_tokens(s))
                                                if s.strip()
                                                else []
                                            ),
                                            include_metadata=False,
                                        )
                                    ]
                                ).run(documents=[Document(text=body)])
                                cursor = 0
                                for node in nodes:
                                    content = node.get_content()
                                    position = body.find(content, max(0, cursor - len(content)))
                                    if position < 0:
                                        raise ValueError("fulltext_unlocatable_chunk")
                                    cursor = position + len(content)
                                    identity = uuid5(
                                        NAMESPACE_URL,
                                        f"{pmid}:{digest}:{section}:{offset + position}:"
                                        f"{SIGNATURE}",
                                    )
                                    chunks.append(
                                        FulltextPassage(
                                            chunk_id=identity,
                                            pmid=pmid,
                                            pmcid=pmcid,
                                            title=hit.document.title,
                                            doi=hit.document.doi,
                                            section=section,
                                            start=offset + position,
                                            end=offset + position + len(content),
                                            text=content,
                                            content_hash=digest,
                                            source_url=url,
                                            license=license_name,
                                        ).model_dump(mode="json")
                                    )
                                    if len(chunks) > 128 or self.clock() >= deadline:
                                        raise ValueError("fulltext_processing_budget")
                            vectors = self.embedder.embed_passages(
                                [c["text"] for c in chunks], deadline=deadline
                            )
                            if self.clock() >= deadline:
                                raise TimeoutError("fulltext_timeout")
                            self.store.publish(
                                pmid,
                                SIGNATURE,
                                {"passages": chunks, "content_hash": digest},
                                vectors,
                            )
                    if query is None:
                        query = self.embedder.embed_query(question).vector
                    hit.fulltext = [
                        FulltextPassage.model_validate(p) for p in self.store.search(pmid, query, 2)
                    ]
                    reason = "fulltext_available"
                except Exception as error:
                    reason = (
                        str(error)
                        if str(error)
                        in {
                            "fulltext_license_not_allowed",
                            "fulltext_no_verified_pmcid",
                            "fulltext_identity_mismatch",
                            "fulltext_timeout",
                            "fulltext_budget",
                            "fulltext_processing_budget",
                            "fulltext_governance_blocked",
                        }
                        else "fulltext_failed"
                    )
            result.warnings.append(f"{pmid}:{reason[:100]}")
        if self.oa_source is not None:
            from clinical_agent.application.oa_fulltext import enrich_openalex

            result = enrich_openalex(self, question, result, deadline=deadline)
        return result
