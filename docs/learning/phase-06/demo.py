"""Offline teaching data; no clinical claim, model download or network."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.analysis import DIMENSIONS, METHOD_FIELDS
from clinical_agent.domain.models import EvidenceChunk, SourceMetadata
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalResult,
    retrieval_embedding_info,
)


def main():
    text = "Synthetic cohort of 20."
    document_id, chunk_id = uuid4(), uuid4()
    source = SourceMetadata(
        source_type="pdf",
        source_url=None,
        source_uri="file:///synthetic.pdf",
        content_hash=sha256(text.encode()).hexdigest(),
        content_scope="extracted_text",
    )
    document = DocumentSummary(
        **source.model_dump(),
        document_id=document_id,
        title="Synthetic teaching sample",
        title_origin="manual",
        authors=[],
        publication_date={"precision": "unknown"},
        journal=None,
        doi=None,
        pmid=None,
        ingestion_time=datetime.now(UTC),
    )
    chunk = EvidenceChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        location={"kind": "pdf_page", "page": 1, "start": 0, "end": len(text)},
        embedding_info=retrieval_embedding_info(),
        source_metadata=source,
    )
    retrieval = RetrievalResult(
        options={},
        embedding_info=retrieval_embedding_info(),
        hits=[EvidenceHit(chunk=chunk, document=document, rank=1, score=1.0)],
    )
    missing = dict(
        value=None,
        epistemic_kind="reported_fact",
        evidence=[],
        basis="not_reported",
        verification_needed=None,
    )
    fields = {k: dict(missing) for k in sorted(METHOD_FIELDS)}
    refs = [dict(chunk_id=str(chunk_id), quote=text)]
    fields["design"] = dict(
        value=text,
        epistemic_kind="reported_fact",
        evidence=refs,
        basis="text",
        verification_needed=None,
    )
    draft = dict(
        studies=[
            dict(
                document_id=str(document_id),
                study_type="cohort",
                type_basis="text",
                type_evidence=refs,
                metadata_basis=[],
                fields=fields,
            )
        ],
        idea_similarities=[
            dict(
                document_id=str(document_id),
                dimensions={
                    k: dict(
                        relation="unknown", idea_quote=None, evidence=[], reason="Not specified"
                    )
                    for k in sorted(DIMENSIONS)
                },
                overall_relation="unknown",
            )
        ],
        candidate_gaps=[],
        comparisons=[],
    )

    class Model:
        def analyze_evidence(self, context, *, timeout_seconds):
            return json.dumps(draft)

    result = EvidenceAnalyzer(model=Model()).analyze(
        QuestionRequest(request_id=uuid4(), question="Study a cohort"), retrieval
    )
    assert result.analysis_status == "partial" and not result.candidate_gaps
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
