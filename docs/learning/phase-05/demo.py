"""Pure RRF demo with explicitly synthetic encoded evidence contracts."""

from datetime import UTC, datetime
from uuid import UUID

from clinical_agent.domain.hybrid import rank_fusion
from clinical_agent.domain.models import EvidenceChunk, EvidenceLocation, SourceMetadata
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalOptions,
    retrieval_embedding_info,
)


def hit(number: int) -> EvidenceHit:
    source = SourceMetadata.model_validate(
        {
            "source_type": "pdf",
            "source_url": None,
            "source_uri": "file:///synthetic.pdf",
            "content_hash": str(number) * 64,
            "content_scope": "extracted_text",
        }
    )
    document = DocumentSummary.model_validate(
        {
            **source.model_dump(),
            "document_id": UUID(int=number),
            "title": "Synthetic teaching record",
            "title_origin": "manual",
            "authors": [],
            "publication_date": {"precision": "unknown"},
            "journal": None,
            "doi": None,
            "pmid": None,
            "ingestion_time": datetime.now(UTC),
        }
    )
    chunk = EvidenceChunk(
        chunk_id=UUID(int=number),
        document_id=document.document_id,
        text="Synthetic",
        location=EvidenceLocation(kind="pdf_page", page=1, start=0, end=9),
        embedding_info=retrieval_embedding_info(),
        source_metadata=source,
    )
    return EvidenceHit(chunk=chunk, document=document, score=0.8, rank=1)


if __name__ == "__main__":
    a, b = hit(1), hit(2)
    result = rank_fusion([a, b], [b, a], RetrievalOptions(mode="hybrid"))
    print(result.model_dump_json())
