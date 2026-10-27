"""Synthetic provenance contracts; no file, model, database or network access."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

DOCUMENT_ID = "00000000-0000-4000-8000-000000000101"
CHUNK_ID = "00000000-0000-4000-8000-000000000102"
DELETE = object()


def _source(kind="pdf"):
    return {
        "source_type": kind,
        "source_url": None,
        "source_uri": "file:///fixtures/synthetic.pdf"
        if kind == "pdf"
        else "file:///fixtures/synthetic.xml",
        "content_hash": "a" * 64,
        "content_scope": "extracted_text" if kind == "pdf" else "abstract",
    }


def _embedding():
    return {
        "model_id": "synthetic-encoder",
        "model_revision": "fixture-r1",
        "tokenizer_revision": "fixture-t1",
        "dimension": 3,
        "normalized": True,
        "chunking_version": "fixture-c1",
    }


def _document(kind="pdf"):
    source = _source(kind)
    chunk_text = "合成证据 α🙂" if kind == "pdf" else "合成摘要"
    start = 2 if kind == "pdf" else 3
    return {
        **source,
        "document_id": DOCUMENT_ID,
        "title": "Synthetic fixture only",
        "title_origin": "filename" if kind == "pdf" else "pubmed_metadata",
        "authors": [],
        "publication_date": {"precision": "unknown", "raw": None},
        "journal": None,
        "doi": None,
        "pmid": None if kind == "pdf" else "1234567890",
        "abstract": None if kind == "pdf" else "背景：合成摘要。结果：甲乙。",
        "text": "  合成证据 α🙂  " if kind == "pdf" else None,
        "ingestion_time": "2026-10-26T22:00:00+08:00",
        "evidence_chunks": [
            {
                "chunk_id": CHUNK_ID,
                "document_id": DOCUMENT_ID,
                "text": chunk_text,
                "location": {
                    "kind": "pdf_page" if kind == "pdf" else "abstract",
                    "page": 1 if kind == "pdf" else None,
                    "start": start,
                    "end": start + len(chunk_text),
                    "section": None,
                },
                "embedding_info": None,
                "source_metadata": deepcopy(source),
            }
        ],
    }


def _replace(data, path, value):
    target = data
    for part in path[:-1]:
        target = target[part]
    if value is DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value


@pytest.mark.parametrize(
    "date",
    [
        {"precision": "unknown"},
        {"precision": "unknown", "raw": "Spring 2020 or 2021"},
        {"precision": "year", "raw": " 2020 ", "year": 2020},
        {"precision": "month", "raw": "2020 Feb", "year": 2020, "month": 2},
        {"precision": "day", "raw": "2020-02-29", "year": 2020, "month": 2, "day": 29},
    ],
)
def test_publication_date_preserves_precision(date):
    from clinical_agent.domain.models import PublicationDate

    result = PublicationDate.model_validate(date)
    assert result.raw == date.get("raw")
    for field in ("year", "month", "day"):
        assert getattr(result, field) == date.get(field)
    assert PublicationDate.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "date",
    [
        {"precision": "unknown", "year": 2020},
        {"precision": "year", "raw": "2020"},
        {"precision": "year", "year": 2020},
        {"precision": "year", "raw": "2020", "year": 2020, "month": 1},
        {"precision": "month", "raw": "2020", "year": 2020},
        {"precision": "day", "raw": "2021-02-29", "year": 2021, "month": 2, "day": 29},
        {"precision": "day", "raw": "2020-04-31", "year": 2020, "month": 4, "day": 31},
        {"precision": "year", "raw": "0", "year": 0},
        {"precision": "year", "raw": "10000", "year": 10000},
        {"precision": "year", "raw": "2020", "year": "2020"},
        {"precision": "year", "raw": "true", "year": True},
        {"precision": "month", "raw": "2020-13", "year": 2020, "month": 13},
        {"precision": "unknown", "raw": "   "},
        {"precision": "season", "raw": "Spring 2020"},
        {"precision": "unknown", "extra": "unexpected"},
    ],
)
def test_publication_date_rejects_inconsistent_or_invented_components(date):
    from clinical_agent.domain.models import PublicationDate

    with pytest.raises(ValidationError):
        PublicationDate.model_validate(date)


@pytest.mark.parametrize("kind", ["pdf", "pubmed"])
def test_document_roundtrip_preserves_unknowns_and_evidence(kind):
    from clinical_agent.domain.models import LiteratureDocument

    data = _document(kind)
    result = LiteratureDocument.model_validate(data)
    assert result.document_id == UUID(DOCUMENT_ID)
    assert result.authors == []
    assert result.journal is result.doi is None
    assert result.publication_date.model_dump() == {
        "raw": None,
        "year": None,
        "month": None,
        "day": None,
        "precision": "unknown",
    }
    assert result.ingestion_time == datetime(2026, 10, 26, 14, tzinfo=UTC)
    assert result.text == data["text"] and result.abstract == data["abstract"]
    chunk = result.evidence_chunks[0]
    assert chunk.text == data["evidence_chunks"][0]["text"]
    assert chunk.embedding_info is None
    assert chunk.location.end - chunk.location.start == len(chunk.text)
    assert LiteratureDocument.model_validate_json(result.model_dump_json()) == result
    dumped = result.model_dump(mode="json")
    assert dumped["source_url"] is None
    assert dumped["pmid"] == data["pmid"]


@pytest.mark.parametrize(
    "patch",
    [
        {"source_type": "web"},
        {"source_url": "ftp://example.org/paper"},
        {"source_url": "https://user:FAKE_SECRET@example.org/paper"},
        {"source_url": "file:///private/paper.pdf"},
        {"source_uri": "relative.pdf"},
        {"source_uri": "https://example.org/snapshot"},
        {"source_uri": None},
        {"content_hash": "xyz"},
        {"content_hash": "A" * 64},
        {"content_scope": "unknown"},
        {"source_type": "pubmed", "content_scope": "full_text"},
        {"untrusted_payload": "fake"},
    ],
)
def test_source_metadata_rejects_invalid_shapes(patch):
    from clinical_agent.domain.models import SourceMetadata

    with pytest.raises(ValidationError) as caught:
        SourceMetadata.model_validate({**_source(), **patch})
    assert "FAKE_SECRET" not in str(caught.value)


def test_source_and_embedding_can_be_declared_without_external_calls():
    from clinical_agent.domain.models import EmbeddingInfo, SourceMetadata

    source = SourceMetadata.model_validate({**_source(), "source_url": "https://example.org/paper"})
    assert str(source.source_url) == "https://example.org/paper"
    assert str(source.source_uri) == "file:///fixtures/synthetic.pdf"
    embedding = EmbeddingInfo.model_validate(_embedding())
    assert embedding.dimension == 3 and embedding.normalized is True
    assert embedding.model_dump() == _embedding()


@pytest.mark.parametrize(
    "field,value",
    [
        ("dimension", 0),
        ("dimension", -1),
        ("dimension", True),
        ("dimension", "3"),
        ("normalized", "true"),
        ("normalized", 1),
        ("model_id", " "),
        ("model_revision", DELETE),
        ("tokenizer_revision", ""),
        ("chunking_version", None),
        ("vector", [0.0, 0.0, 1.0]),
    ],
)
def test_embedding_declarations_require_complete_typed_identity(field, value):
    from clinical_agent.domain.models import EmbeddingInfo

    data = _embedding()
    _replace(data, (field,), value)
    with pytest.raises(ValidationError):
        EmbeddingInfo.model_validate(data)


@pytest.mark.parametrize(
    "kind,patch",
    [
        ("pdf", {"page": 0}),
        ("pdf", {"page": True}),
        ("pdf", {"page": "1"}),
        ("pdf", {"page": None}),
        ("pdf", {"start": -1}),
        ("pdf", {"start": True}),
        ("pdf", {"end": 2}),
        ("pdf", {"end": 1}),
        ("pdf", {"section": " "}),
        ("pdf", {"kind": "unknown"}),
        ("pubmed", {"page": 1}),
    ],
)
def test_locations_reject_ambiguous_or_invalid_positions(kind, patch):
    from clinical_agent.domain.models import EvidenceLocation

    data = {**_document(kind)["evidence_chunks"][0]["location"], **patch}
    with pytest.raises(ValidationError):
        EvidenceLocation.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("text", " "),
        ("embedding_info", DELETE),
        ("chunk_id", "not-a-uuid"),
        ("location", {"kind": "abstract", "start": 0, "end": 8}),
        ("location", {"kind": "pdf_page", "page": 1, "start": 0, "end": 999}),
        ("source_metadata", DELETE),
    ],
)
def test_chunks_require_matching_origin_and_character_span(field, value):
    from clinical_agent.domain.models import EvidenceChunk

    data = _document()["evidence_chunks"][0]
    _replace(data, (field,), value)
    with pytest.raises(ValidationError):
        EvidenceChunk.model_validate(data)


@pytest.mark.parametrize(
    "path,value",
    [
        (("document_id",), DELETE),
        (("title",), "  "),
        (("authors",), [" "]),
        (("authors",), DELETE),
        (("publication_date",), None),
        (("journal",), " "),
        (("doi",), " "),
        (("pmid",), "0"),
        (("pmid",), "0123"),
        (("pmid",), 123),
        (("title_origin",), "pubmed_metadata"),
        (("title_origin",), "guessed"),
        (("ingestion_time",), "2026-10-26T14:00:00"),
        (("ingestion_time",), 0),
        (("text",), None),
        (("text",), " \n"),
        (("extra",), "not-allowed"),
        (("evidence_chunks", 0, "document_id"), "00000000-0000-4000-8000-000000000199"),
        (("evidence_chunks", 0, "source_metadata", "content_hash"), "b" * 64),
        (("evidence_chunks", 0, "source_metadata", "source_url"), "https://example.org/different"),
        (("evidence_chunks", 0, "source_metadata", "content_scope"), "full_text"),
    ],
)
def test_documents_reject_missing_unknown_or_inconsistent_data(path, value):
    from clinical_agent.domain.models import LiteratureDocument

    data = _document()
    _replace(data, path, value)
    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate(data)


@pytest.mark.parametrize(
    "patch",
    [
        {"text": "Pretend full text"},
        {"abstract": None},
        {"pmid": None},
        {"title_origin": "filename"},
        {"content_scope": "full_text"},
    ],
)
def test_pubmed_abstract_cannot_masquerade_as_full_text(patch):
    from clinical_agent.domain.models import LiteratureDocument

    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate({**_document("pubmed"), **patch})


@pytest.mark.parametrize("start,end,text", [(100, 104, "合成摘要"), (0, 4, "合成摘要")])
def test_pubmed_chunk_must_equal_the_located_abstract_slice(start, end, text):
    from clinical_agent.domain.models import LiteratureDocument

    data = _document("pubmed")
    chunk = data["evidence_chunks"][0]
    chunk.update(text=text)
    chunk["location"].update(start=start, end=end)
    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate(data)


def test_document_rejects_duplicate_chunks_and_mixed_embedding_identities():
    from clinical_agent.domain.models import LiteratureDocument

    data = _document()
    data["evidence_chunks"].append(deepcopy(data["evidence_chunks"][0]))
    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate(data)
    data["evidence_chunks"][1]["chunk_id"] = "00000000-0000-4000-8000-000000000103"
    for chunk in data["evidence_chunks"]:
        chunk["embedding_info"] = _embedding()
    assert len(LiteratureDocument.model_validate(data).evidence_chunks) == 2
    data["evidence_chunks"][1]["embedding_info"]["model_revision"] = "fixture-r2"
    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate(data)


def test_unprepared_documents_and_metadata_normalization_remain_explicit():
    from clinical_agent.domain.models import LiteratureDocument

    data = _document()
    data.update(
        title="  Synthetic fixture only  ",
        authors=[" Group A ", "Author B"],
        doi="10.synthetic/fixture",
        evidence_chunks=[],
    )
    result = LiteratureDocument.model_validate(data)
    assert result.title == "Synthetic fixture only"
    assert result.authors == ["Group A", "Author B"]
    assert result.doi == "10.synthetic/fixture"
    assert result.evidence_chunks == []


@pytest.mark.parametrize("value", ["0", "1761444000", b"0"])
def test_ingestion_time_cannot_implicitly_decode_an_epoch(value):
    from clinical_agent.domain.models import LiteratureDocument

    data = _document()
    data["ingestion_time"] = value
    with pytest.raises(ValidationError):
        LiteratureDocument.model_validate(data)


def test_invalid_datetime_error_does_not_echo_source_input():
    from clinical_agent.domain.models import LiteratureDocument

    data = _document()
    data["ingestion_time"] = "INVALID_TIME_FAKE_SECRET"
    with pytest.raises(ValidationError) as caught:
        LiteratureDocument.model_validate(data)
    assert "INVALID_TIME_FAKE_SECRET" not in str(caught.value)
