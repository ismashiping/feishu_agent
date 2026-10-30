"""Convert acquired PubMed abstract snapshots to the existing evidence/citation chain."""

from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from pydantic import HttpUrl

from clinical_agent.domain.governance import BLOCKED_STATUSES, GovernanceState, pubmed_status
from clinical_agent.domain.models import EvidenceChunk, EvidenceLocation, SourceMetadata
from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest, PubMedSearchResult
from clinical_agent.domain.research import ResearchError
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalRequest,
    RetrievalResult,
)


class SearchPort(Protocol):
    def search(
        self, request: PubMedSearchRequest, *, timeout_seconds: float = 30.0
    ) -> PubMedSearchResult: ...


class GovernanceLookup(Protocol):
    def statuses_for_pmids(self, pmids: list[str]) -> dict[str, GovernanceState]: ...


class PubMedRetrievalService:
    def __init__(self, searcher: SearchPort, *, governance: GovernanceLookup | None = None) -> None:
        self._searcher = searcher
        self._governance = governance

    def retrieve(
        self,
        request: RetrievalRequest,
        *,
        query_plan: QueryPlan | None = None,
        timeout_seconds: float = 30.0,
    ) -> RetrievalResult:
        request = RetrievalRequest.model_validate(request).model_copy(deep=True)
        result = PubMedSearchResult.model_validate(
            self._searcher.search(
                PubMedSearchRequest(
                    question=request.question,
                    options=request.pubmed or PubMedOptions(),
                    query_plan=query_plan,
                ),
                timeout_seconds=timeout_seconds,
            )
        )
        if result.status == "partial" and not result.records:
            raise ResearchError("pubmed_failed")
        try:
            states = (
                self._governance.statuses_for_pmids([r.pmid for r in result.records])
                if self._governance is not None
                else {}
            )
        except Exception:
            raise ResearchError("pubmed_failed") from None
        hits: list[EvidenceHit] = []
        for position, record in enumerate(result.records, 1):
            if (
                states.get(record.pmid, GovernanceState()).status in BLOCKED_STATUSES
                or pubmed_status(record.publication_types, record.notices) in BLOCKED_STATUSES
                or record.content_scope == "metadata_only"
                or "pubmed" not in request.options.source_types
                or "abstract" not in request.options.content_scopes
            ):
                continue
            # One contiguous abstract passage retains all sections.
            identity = uuid5(NAMESPACE_URL, record.source_url + "#" + record.content_hash)
            metadata = SourceMetadata(
                source_type="pubmed",
                source_url=HttpUrl(record.source_url),
                source_uri=HttpUrl(record.source_url),
                content_hash=record.content_hash,
                content_scope="abstract",
            )
            chunk = EvidenceChunk(
                chunk_id=uuid5(identity, f"abstract:0:{len(record.abstract)}"),
                document_id=identity,
                text=record.abstract,
                location=EvidenceLocation(kind="abstract", start=0, end=len(record.abstract)),
                embedding_info=None,
                source_metadata=metadata,
            )
            document = DocumentSummary(
                **metadata.model_dump(),
                document_id=identity,
                title=record.title,
                title_origin="pubmed_metadata",
                authors=record.authors,
                journal=record.journal,
                doi=record.doi,
                pmid=record.pmid,
                publication_date=record.publication_date,
                ingestion_time=result.fetched_at,
                snapshot_xml=record.snapshot_xml,
                governance=states.get(record.pmid, GovernanceState()),
                publication_types=record.publication_types,
                source_notices=record.notices,
            )
            hits.append(
                EvidenceHit(
                    chunk=chunk,
                    document=document,
                    score=1.0 / position,
                    score_type="pubmed_rank",
                    rank=len(hits) + 1,
                )
            )
            if len(hits) >= request.options.top_k:
                break
        return RetrievalResult(
            scope="online",
            options=request.options,
            embedding_info=None,
            hits=hits,
            search_provenance=result.provenance(),
            warnings=["source_governance_known_pmids"] if self._governance is not None else [],
        )


def merge_sources(local: RetrievalResult, online: RetrievalResult) -> RetrievalResult:
    """Local then online, reserving half the budget; no cross-channel score fusion."""
    limit = local.options.top_k
    chosen: list[EvidenceHit] = []
    seen_documents: set[str] = set()
    seen_chunks: set[str] = set()

    def add(hit: EvidenceHit) -> None:
        document = (
            "pmid:" + hit.document.pmid if hit.document.pmid else str(hit.document.document_id)
        )
        if str(hit.chunk.chunk_id) in seen_chunks or (
            document in seen_documents and hit.score_type == "pubmed_rank"
        ):
            return
        chosen.append(hit)
        seen_chunks.add(str(hit.chunk.chunk_id))
        seen_documents.add(document)

    for hit in local.hits[: (limit + 1) // 2]:
        add(hit)
    for hit in online.hits:
        if len(chosen) == limit:
            break
        add(hit)
    for hit in local.hits:
        if len(chosen) == limit:
            break
        add(hit)
    chosen.sort(
        key=lambda h: (
            0 if h.score_type != "pubmed_rank" else 1,
            -h.score,
            h.chunk.chunk_id.int,
        )
    )
    return RetrievalResult(
        scope="hybrid",
        options=local.options,
        embedding_info=local.embedding_info,
        hits=[hit.model_copy(update={"rank": i}) for i, hit in enumerate(chosen, 1)],
        search_provenance=online.search_provenance,
        channel_status=local.channel_status,
        strategy_version=local.strategy_version,
        warnings=list(dict.fromkeys([*local.warnings, *online.warnings])),
    )
