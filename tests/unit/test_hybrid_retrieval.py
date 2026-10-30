"""RRF hand calculations, explicit channel failures and shared retrieval contracts."""

from uuid import UUID

import pytest
from pydantic import ValidationError


def hit(prepared, identity, score=0.8):
    from clinical_agent.domain.retrieval import DocumentSummary, EvidenceHit

    return EvidenceHit(
        chunk=prepared.embedded[0].evidence.model_copy(update={"chunk_id": UUID(int=identity)}),
        document=DocumentSummary.from_document(prepared.source.parsed.document),
        score=score,
        rank=1,
    )


def test_hand_calculated_rrf_and_stable_tie(prepared_factory, source_factory):
    from clinical_agent.domain.hybrid import rank_fusion
    from clinical_agent.domain.retrieval import RetrievalOptions

    a = hit(prepared_factory(source_factory(text="aspirin trial")), 1)
    b = hit(prepared_factory(source_factory(text="analgesic outcomes")), 2)
    result = rank_fusion([a, b], [b, a], RetrievalOptions(mode="hybrid", top_k=2))
    assert [h.chunk.chunk_id.int for h in result.hits] == [1, 2]
    assert result.hits[0].fusion_score == pytest.approx(1 / 61 + 1 / 62)
    assert result.hits[0].keyword_rank == 1 and result.hits[0].vector_rank == 2
    assert result.channel_status == {"keyword": "ok", "vector": "ok"} and not result.degraded


def test_one_channel_empty_duplicate_chunks_and_same_document_preserved(prepared_factory):
    from clinical_agent.domain.hybrid import rank_fusion
    from clinical_agent.domain.retrieval import RetrievalOptions

    source = prepared_factory()
    a, b = hit(source, 1), hit(source, 2)
    result = rank_fusion([a, a, b], [], RetrievalOptions(mode="hybrid"))
    assert [h.chunk.chunk_id.int for h in result.hits] == [1, 2]
    assert all(h.vector_rank is None for h in result.hits)
    assert len({h.document.document_id for h in result.hits}) == 1


def test_same_chunk_with_different_snapshot_is_not_fused(prepared_factory, source_factory):
    from clinical_agent.domain.hybrid import rank_fusion
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

    a, b = hit(prepared_factory(), 1), hit(prepared_factory(source_factory(text="Different")), 1)
    with pytest.raises(RetrievalError, match="retrieval_corrupt"):
        rank_fusion([a], [b], RetrievalOptions(mode="hybrid"))


@pytest.mark.parametrize(
    "values",
    [
        {"mode": "other"},
        {"candidate_limit": 0},
        {"candidate_limit": 101},
        {"top_k": 10, "candidate_limit": 5},
        {"mode": "hybrid", "min_similarity": 0.2},
        {"keyword_query": "aspirin"},
        {"date_from": "2020-01-01"},
        {"date_from": "2021-01-01", "date_to": "2020-01-01"},
    ],
)
def test_invalid_hybrid_options(values):
    from clinical_agent.domain.retrieval import RetrievalOptions

    with pytest.raises(ValidationError):
        RetrievalOptions(**values)


@pytest.mark.parametrize("mode", ["keyword", "hybrid"])
def test_language_is_explicit_and_never_silently_degrades(mode):
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions, RetrievalRequest

    with pytest.raises(RetrievalError, match="retrieval_language_unsupported"):
        RetrievalService(embedder=object(), retriever=object(), hybrid_retriever=object()).retrieve(
            RetrievalRequest(question="阿司匹林 aspirin", options=RetrievalOptions(mode=mode))
        )


def test_keyword_skips_embedding_and_explicit_english_terms_keep_original_question():
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.retrieval import (
        RetrievalOptions,
        RetrievalRequest,
        RetrievalResult,
        retrieval_embedding_info,
    )

    calls = []

    class Ranked:
        def search_hybrid(self, question, query, options, *, timeout_seconds):
            calls.append((question, query, options))
            return RetrievalResult(
                options=options,
                embedding_info=retrieval_embedding_info(),
                hits=[],
                strategy_version="fts-simple-v1",
                channel_status={"keyword": "ok", "vector": "not_requested"},
            )

    request = RetrievalRequest(
        question="成人的阿司匹林证据？",
        options=RetrievalOptions(mode="keyword", keyword_query="aspirin"),
    )
    result = RetrievalService(
        embedder=object(), retriever=object(), hybrid_retriever=Ranked()
    ).retrieve(request)
    assert result.hits == [] and calls[0][0] == "aspirin" and calls[0][1] is None
    assert request.question == "成人的阿司匹林证据？"


def test_hybrid_embeds_once_and_fails_closed():
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions, RetrievalRequest

    calls = []

    class Embedder:
        def embed_query(self, question):
            calls.append(question)
            from clinical_agent.domain.embedding import QueryEmbedding
            from clinical_agent.domain.retrieval import retrieval_embedding_info

            return QueryEmbedding(
                embedding_info=retrieval_embedding_info(), vector=[1.0] + [0.0] * 767
            )

    class Bad:
        def search_hybrid(self, *args, **kwargs):
            raise RetrievalError("retrieval_failed")

    with pytest.raises(RetrievalError, match="retrieval_failed"):
        RetrievalService(embedder=Embedder(), retriever=object(), hybrid_retriever=Bad()).retrieve(
            RetrievalRequest(question="aspirin", options=RetrievalOptions(mode="hybrid"))
        )
    assert calls == ["aspirin"]


def test_no_hits_is_success_and_is_distinct_from_a_failed_channel():
    from clinical_agent.domain.hybrid import rank_fusion
    from clinical_agent.domain.retrieval import RetrievalOptions

    result = rank_fusion([], [], RetrievalOptions(mode="hybrid"))
    assert result.hits == [] and result.channel_status == {"keyword": "ok", "vector": "ok"}


def test_cli_api_and_graph_keep_keyword_strategy(tmp_path, capsys):
    import json
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.cli import main
    from clinical_agent.domain.retrieval import RetrievalResult, retrieval_embedding_info

    class Ranked:
        def search_hybrid(self, question, query, options, *, timeout_seconds):
            assert question == "aspirin" and query is None
            return RetrievalResult(
                options=options,
                hits=[],
                embedding_info=retrieval_embedding_info(),
                strategy_version="fts-simple-v1",
                channel_status={"keyword": "ok", "vector": "not_requested"},
            )

    def research():
        return ResearchService(
            retriever=RetrievalService(
                embedder=object(), retriever=object(), hybrid_retriever=Ranked()
            ),
            generator=object(),
        )

    @contextmanager
    def cli_runtime(model_dir):
        yield research()

    assert (
        main(
            [
                "ask",
                "--scope",
                "local",
                "--model-dir",
                ".",
                "--question",
                "中文问题",
                "--retrieval-mode",
                "keyword",
                "--keyword-query",
                "aspirin",
            ],
            research_factory=cli_runtime,
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert (
        result["local_retrieval_mode"] == "keyword"
        and result["local_retrieval_strategy"] == "fts-simple-v1"
    )

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=research())

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as api:
        response = api.post(
            "/v1/questions",
            json={
                "scope": "local",
                "question": "中文问题",
                "options": {"mode": "keyword", "keyword_query": "aspirin"},
            },
        )
    assert (
        response.status_code == 200
        and response.json()["local_retrieval_strategy"] == "fts-simple-v1"
    )


def test_partial_mixed_sources_dates_and_keyword_notes_fit_existing_answer_contract(
    source_factory, prepared_factory
):
    import json
    from datetime import UTC, datetime
    from uuid import uuid4

    from clinical_agent.domain.citations import build_answer, parse_draft
    from clinical_agent.domain.models import PublicationDate, SourceMetadata
    from clinical_agent.domain.pubmed import SearchProvenance
    from clinical_agent.domain.research import QuestionRequest
    from clinical_agent.domain.retrieval import (
        RetrievalOptions,
        RetrievalResult,
        retrieval_embedding_info,
    )

    local = hit(prepared_factory(), 1)
    local.document.publication_date = PublicationDate(
        precision="day", raw="2020-02-02", year=2020, month=2, day=2
    )
    score = 2 / 61
    local = local.model_copy(
        update={
            "score_type": "rrf",
            "score": score,
            "keyword_rank": 1,
            "vector_rank": 1,
            "fusion_score": score,
        }
    )
    online = hit(prepared_factory(source_factory(kind="pubmed", pmid="123")), 2)
    metadata = SourceMetadata.model_validate(
        {
            **online.chunk.source_metadata.model_dump(),
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/123/",
            "source_uri": "https://pubmed.ncbi.nlm.nih.gov/123/",
        }
    )
    online.chunk = online.chunk.model_copy(
        update={"embedding_info": None, "source_metadata": metadata}
    )
    online.document = online.document.model_copy(
        update={**metadata.model_dump(), "source_notices": ["ErratumIn:456"]}
    )
    online = online.model_copy(update={"score_type": "pubmed_rank", "score": 1.0, "rank": 2})
    options = RetrievalOptions(mode="hybrid", date_from="2020-01-01", date_to="2020-12-31")
    provenance = SearchProvenance(
        query_sent="aspirin",
        query_translation=None,
        total_count=5,
        requested_limit=10,
        returned_count=3,
        truncated=True,
        fetched_at=datetime.now(UTC),
        date_from=None,
        date_to=None,
        date_field="pdat",
        sort="relevance",
        status="partial",
        warnings=["fetch_batch_failed"],
        missing_pmids=["999"],
    )
    retrieval = RetrievalResult(
        scope="hybrid",
        options=options,
        embedding_info=retrieval_embedding_info(),
        hits=[local, online],
        search_provenance=provenance,
        channel_status={"keyword": "ok", "vector": "ok"},
        strategy_version="rrf-v1",
    )
    raw = json.dumps(
        {
            "claims": [
                {
                    "text": "Only supplied evidence is available.",
                    "kind": "uncertainty",
                    "evidence_chunk_ids": [str(local.chunk.chunk_id), str(online.chunk.chunk_id)],
                    "limitations": [],
                }
            ]
        }
    )
    answer = build_answer(
        QuestionRequest(request_id=uuid4(), question="aspirin", scope="hybrid", options=options),
        retrieval,
        parse_draft(raw, max_bytes=32000),
        generated_at=datetime.now(UTC),
    )
    assert answer.status == "answered" and len(answer.limitations) == 10
    assert any("simple ASCII" in note and "完整出版日期" in note for note in answer.limitations)
