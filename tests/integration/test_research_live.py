"""Opt-in paid DeepSeek smoke: only explicit synthetic evidence leaves this process."""

import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.external]


def test_real_deepseek_synthetic_evidence(source_factory, prepared_factory):
    from clinical_agent.adapters.deepseek import DeepSeekSettings, deepseek_generator
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.research import QuestionRequest
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    # Missing configuration is a failed opt-in test, never a passing skip.
    settings = DeepSeekSettings()
    text = (
        "This is a fictional teaching example, not clinical evidence. "
        "The simulated study included 12 invented participants and had no control group. "
        "It cannot establish treatment efficacy or guide patient care."
    )
    prepared = prepared_factory(source_factory(text=text), max_tokens=512)
    hits = [
        EvidenceHit(
            chunk=item.evidence,
            document=DocumentSummary.from_document(prepared.source.parsed.document),
            score=1.0 - index * 0.1,
            rank=index + 1,
        )
        for index, item in enumerate(prepared.embedded)
    ]

    class SyntheticRetriever:
        def retrieve(self, request):
            return RetrievalResult(
                options=request.options, embedding_info=retrieval_embedding_info(), hits=hits
            )

    captured = bytearray()
    response_headers = {}

    class RecordingStream(httpx.SyncByteStream):
        def __init__(self, stream):
            self.stream = stream

        def __iter__(self):
            for block in self.stream:
                if len(captured) + len(block) <= 128000:
                    captured.extend(block)
                yield block

        def close(self):
            self.stream.close()

    class RecordingTransport(httpx.HTTPTransport):
        def handle_request(self, request):
            assert request.url.host == "api.deepseek.com"
            response = super().handle_request(request)
            response_headers.update(response.headers)
            response.stream = RecordingStream(response.stream)
            return response

    with deepseek_generator(
        settings, transport=RecordingTransport(retries=0, trust_env=False)
    ) as generator:
        answer = ResearchService(retriever=SyntheticRetriever(), generator=generator).answer(
            QuestionRequest(
                request_id=uuid4(), question="这个虚构教学样例有什么局限？不要推断真实治疗效果。"
            )
        )
    assert answer.status == "answered" and answer.claims
    assert {identity for claim in answer.claims for identity in claim.evidence_chunk_ids} <= {
        hit.chunk.chunk_id for hit in hits
    }
    assert all(
        source.title == "Synthetic"
        and source.pmid is None
        and source.doi is None
        and source.content_scope == "extracted_text"
        for source in answer.sources
    )
    assert "source_uri" not in answer.model_dump_json()
    report = {
        "requested_model": settings.model,
        "response_model": httpx.Response(200, headers=response_headers, content=bytes(captured))
        .json()
        .get("model"),
        "status": answer.status,
        "claims": len(answer.claims),
        "sources": len(answer.sources),
        "citation_membership": "passed",
        "retriever": "synthetic fixture (not E5/PG)",
        "medical_quality_evaluation": "not performed",
    }
    directory = Path(os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "real-llm-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (directory / "real-llm-answer.json").write_text(
        answer.model_dump_json(indent=2), encoding="utf-8"
    )
