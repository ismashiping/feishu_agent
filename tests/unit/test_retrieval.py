"""Retrieval contracts and orchestration without model/network/database work."""

import copy
from uuid import UUID

import pytest
from pydantic import ValidationError


def hit(prepared, score=1.0, rank=1):
    from clinical_agent.domain.retrieval import DocumentSummary, EvidenceHit

    return EvidenceHit(
        chunk=prepared.embedded[0].evidence,
        document=DocumentSummary.from_document(prepared.source.parsed.document),
        score=score,
        score_type="cosine_similarity",
        rank=rank,
    )


@pytest.mark.parametrize("value", ["", " \n ", b"secret-question", None, 123, "a" * 4001])
def test_question_is_strict_trimmed_and_bounded(value):
    from clinical_agent.domain.retrieval import RetrievalRequest

    with pytest.raises(ValidationError):
        RetrievalRequest(question=value)


def test_question_normalization_and_local_only():
    from clinical_agent.domain.retrieval import RetrievalRequest

    assert RetrievalRequest(question="  中文 query  ").question == "中文 query"
    with pytest.raises(ValidationError):
        RetrievalRequest(question="query", scope="unavailable_scope")


@pytest.mark.parametrize(
    "field,value",
    [
        ("top_k", 0),
        ("top_k", 21),
        ("top_k", True),
        ("top_k", "5"),
        ("min_similarity", float("nan")),
        ("min_similarity", float("inf")),
        ("min_similarity", -1.01),
        ("min_similarity", 1.01),
        ("min_similarity", True),
        ("min_similarity", "0.6"),
        ("source_types", []),
        ("source_types", ["other"]),
        ("source_types", ["pdf", "pdf"]),
        ("content_scopes", ["abstract", "abstract"]),
        ("document_ids", []),
        ("document_ids", [UUID(int=1), UUID(int=1)]),
        ("document_ids", [UUID(int=i) for i in range(1, 102)]),
    ],
)
def test_retrieval_options_are_explicit(field, value):
    from clinical_agent.domain.retrieval import RetrievalOptions

    with pytest.raises(ValidationError):
        RetrievalOptions(**{field: value})


@pytest.mark.parametrize("kind", ["pdf", "pubmed"])
def test_hit_keeps_bibliography_position_scope_without_full_document_or_vector(
    source_factory,
    prepared_factory,
    kind,
):
    from clinical_agent.domain.retrieval import EvidenceHit

    prepared = prepared_factory(source_factory(kind=kind))
    result = hit(prepared)
    prepared.source.parsed.validate_chunk(result.chunk)
    assert EvidenceHit.model_validate_json(result.model_dump_json()) == result
    assert result.document.publication_date.precision == "unknown"
    assert result.document.source_type == kind
    assert result.document.content_scope == ("abstract" if kind == "pubmed" else "extracted_text")
    assert not {"text", "abstract", "evidence_chunks"} & result.document.model_dump().keys()
    assert '"vector":' not in result.model_dump_json()


@pytest.mark.parametrize("case", ["doc", "hash", "uncoded", "nan", "bool", "range", "rank"])
def test_hit_rejects_inconsistent_provenance_or_score(prepared_factory, case):
    from clinical_agent.domain.retrieval import EvidenceHit

    data = hit(prepared_factory()).model_dump()
    if case == "doc":
        data["document"]["document_id"] = UUID(int=999)
    elif case == "hash":
        data["document"]["content_hash"] = "b" * 64
    elif case == "uncoded":
        data["chunk"]["embedding_info"] = None
    elif case == "rank":
        data["rank"] = 0
    else:
        data["score"] = {"nan": float("nan"), "bool": True, "range": 1.1}[case]
    with pytest.raises(ValidationError):
        EvidenceHit.model_validate(data)


@pytest.mark.parametrize(
    "case", ["rank", "duplicate", "model", "threshold", "filter", "order", "limit"]
)
def test_result_revalidates_all_hits_and_query_contract(prepared_factory, source_factory, case):
    from clinical_agent.domain.retrieval import (
        RetrievalOptions,
        RetrievalResult,
        retrieval_embedding_info,
    )

    first = hit(prepared_factory(), 1.0, 1).model_dump()
    second = hit(prepared_factory(source_factory(text="Other source.")), 0.5, 2).model_dump()
    options = RetrievalOptions().model_dump()
    if case == "rank":
        second["rank"] = 3
    elif case == "duplicate":
        second = copy.deepcopy(first)
        second["rank"] = 2
    elif case == "model":
        second["chunk"]["embedding_info"]["model_revision"] = "other"
    elif case == "threshold":
        options["min_similarity"] = 0.7
    elif case == "filter":
        options["source_types"] = ["pubmed"]
    elif case == "order":
        first["score"], second["score"] = 0.1, 0.5
    else:
        options["top_k"] = 1
    with pytest.raises(ValidationError):
        RetrievalResult(
            hits=[first, second], options=options, embedding_info=retrieval_embedding_info()
        )
