"""Offline teaching demo using the real graph and citation gate, synthetic ports."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from clinical_agent.application.research import ResearchService
from clinical_agent.domain.models import EvidenceChunk, SourceMetadata
from clinical_agent.domain.research import QuestionRequest, ResearchError
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalResult,
    retrieval_embedding_info,
)


def main():
    body = "Fictional teaching data: no control group; efficacy cannot be established."
    metadata = SourceMetadata(
        source_type="pdf",
        source_url=None,
        source_uri="file:///synthetic-teaching.pdf",
        content_hash=hashlib.sha256(body.encode()).hexdigest(),
        content_scope="extracted_text",
    )
    info = retrieval_embedding_info()
    chunk = EvidenceChunk(
        chunk_id=UUID(int=2),
        document_id=UUID(int=1),
        text=body,
        location={"kind": "pdf_page", "page": 1, "start": 0, "end": len(body)},
        embedding_info=info,
        source_metadata=metadata,
    )
    document = DocumentSummary(
        **metadata.model_dump(),
        document_id=UUID(int=1),
        title="Synthetic teaching data",
        title_origin="manual",
        authors=[],
        publication_date={"precision": "unknown"},
        journal=None,
        doi=None,
        pmid=None,
        ingestion_time=datetime.now(UTC),
    )
    hits = [EvidenceHit(chunk=chunk, document=document, score=1.0, rank=1)]

    class Retriever:
        empty = False

        def retrieve(self, request):
            return RetrievalResult(
                options=request.options, embedding_info=info, hits=[] if self.empty else hits
            )

    class Generator:
        invalid = False
        calls = 0

        def generate(self, context, *, timeout_seconds):
            self.calls += 1
            identity = UUID(int=999) if self.invalid else context.evidence[0].chunk_id
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": "The fictional example cannot establish efficacy.",
                            "kind": "uncertainty",
                            "evidence_chunk_ids": [str(identity)],
                            "limitations": ["Synthetic data only."],
                        }
                    ]
                }
            )

    retriever, generator = Retriever(), Generator()
    service = ResearchService(retriever=retriever, generator=generator)
    request = QuestionRequest(request_id=UUID(int=3), question="What are the limitations?")
    answered = service.answer(request)
    assert answered.sources[0].evidence[0].text == body
    retriever.empty = True
    empty = service.answer(request)
    assert generator.calls == 1 and not empty.claims and not empty.sources
    retriever.empty, generator.invalid = False, True
    try:
        service.answer(request)
    except ResearchError as error:
        assert error.code == "citation_invalid"
        invalid = error.code
    else:
        raise AssertionError("Unknown citation was accepted")
    print(
        json.dumps(
            {
                "answered": answered.status,
                "empty": empty.status,
                "invalid_citation": invalid,
                "external_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
