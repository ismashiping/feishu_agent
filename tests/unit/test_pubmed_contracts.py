"""Abstract offsets and per-record status contracts, without XML I/O."""

from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError


def _payload():
    return {
        "document_id": str(UUID(int=401)),
        "title": "Synthetic",
        "title_origin": "pubmed_metadata",
        "authors": [],
        "publication_date": {"precision": "unknown"},
        "journal": None,
        "doi": None,
        "pmid": "1234567890",
        "source_type": "pubmed",
        "source_uri": "file:///fixtures/pubmed.xml",
        "source_url": None,
        "content_hash": "a" * 64,
        "content_scope": "abstract",
        "ingestion_time": "2026-10-26T16:00:00Z",
        "abstract": "A α🙂\n\nResult",
        "text": None,
        "evidence_chunks": [],
    }


def _article_data():
    return {
        "document": _payload(),
        "source_units": [
            {
                "index": 1,
                "text": "A α🙂",
                "start": 0,
                "end": 4,
                "label": "BACKGROUND",
                "category": "BACKGROUND",
            },
            {
                "index": 2,
                "text": "Result",
                "start": 6,
                "end": 12,
                "label": "RESULTS",
                "category": "RESULTS",
            },
        ],
    }


@pytest.mark.parametrize(
    "patch",
    [
        {"index": 0},
        {"start": -1},
        {"end": 3},
        {"text": " A α🙂"},
        {"text": "A\r\nB"},
        {"normalization_version": "unknown"},
    ],
)
def test_abstract_units_must_have_canonical_text_and_exact_span(patch):
    from clinical_agent.domain.models import AbstractSourceUnit

    with pytest.raises(ValidationError):
        AbstractSourceUnit.model_validate({**_article_data()["source_units"][0], **patch})


@pytest.mark.parametrize(
    "case", ["valid", "document", "source", "section", "cross_section", "outside", "text"]
)
def test_chunk_rebuild_is_confined_to_one_abstract_section(case):
    from clinical_agent.domain.models import EvidenceChunk, ParsedPubmedArticle, SourceMetadata

    result = ParsedPubmedArticle.model_validate(_article_data())
    data = {
        "chunk_id": str(UUID(int=402)),
        "document_id": str(result.document.document_id),
        "text": "α🙂",
        "location": {"kind": "abstract", "start": 2, "end": 4, "section": "BACKGROUND"},
        "source_metadata": SourceMetadata.model_validate(
            {k: v for k, v in _payload().items() if k in SourceMetadata.model_fields}
        ),
        "embedding_info": None,
    }
    if case == "document":
        data["document_id"] = str(UUID(int=403))
    if case == "source":
        data["source_metadata"].content_hash = "b" * 64
    if case == "section":
        data["location"]["section"] = "OTHER"
    if case == "cross_section":
        data["text"] = _payload()["abstract"]
        data["location"].update(start=0, end=12)
    if case == "outside":
        data["location"].update(start=100, end=102)
    if case == "text":
        data["text"] = "β🙂"
    chunk = EvidenceChunk.model_validate(data)
    if case == "valid":
        assert result.validate_chunk(chunk) is None
        assert ParsedPubmedArticle.model_validate_json(result.model_dump_json()) == result
    else:
        with pytest.raises(ValueError):
            result.validate_chunk(chunk)


@pytest.mark.parametrize("case", ["gap", "order", "abstract", "empty"])
def test_article_sections_cannot_disagree_with_the_document(case):
    from clinical_agent.domain.models import ParsedPubmedArticle

    data = _article_data()
    if case == "gap":
        data["source_units"][1].update(start=7, end=13)
    if case == "order":
        data["source_units"][1]["index"] = 3
    if case == "abstract":
        data["document"]["abstract"] = "Different"
    if case == "empty":
        data["source_units"] = []
    with pytest.raises(ValidationError):
        ParsedPubmedArticle.model_validate(data)


@pytest.mark.parametrize(
    "case",
    ["rejected_article", "parsed_without_article", "rejected_without_code", "parsed_with_error"],
)
def test_entry_status_is_not_ambiguous(case):
    from clinical_agent.domain.models import PubmedXmlEntry

    data = {"index": 1, "status": "parsed", "article": _article_data(), "error_code": None}
    if case == "rejected_article":
        data.update(status="rejected", error_code="pubmed_no_abstract")
    if case == "parsed_without_article":
        data["article"] = None
    if case == "rejected_without_code":
        data.update(status="rejected", article=None)
    if case == "parsed_with_error":
        data["error_code"] = "pubmed_no_abstract"
    with pytest.raises(ValidationError):
        PubmedXmlEntry.model_validate(data)


@pytest.mark.parametrize("case", ["order", "source", "duplicate_id"])
def test_batch_cannot_mix_sources_or_identities(case):
    from clinical_agent.domain.models import PubmedXmlBatch, SourceMetadata

    data = {
        "source": {k: v for k, v in _payload().items() if k in SourceMetadata.model_fields},
        "entries": [
            {"index": 1, "status": "parsed", "article": _article_data(), "error_code": None}
        ],
        "parser_version": "0.7.1",
    }
    if case == "order":
        data["entries"][0]["index"] = 2
    if case == "source":
        data["source"]["content_hash"] = "b" * 64
    if case == "duplicate_id":
        duplicate = deepcopy(data["entries"][0])
        duplicate["index"] = 2
        duplicate["article"]["document"]["pmid"] = "1234567891"
        data["entries"].append(duplicate)
    with pytest.raises(ValidationError):
        PubmedXmlBatch.model_validate(data)


@pytest.mark.parametrize(
    "field,value", [("max_depth", 0), ("max_records", True), ("max_seconds", float("inf"))]
)
def test_xml_limits_are_bounded(field, value):
    from clinical_agent.adapters.pubmed_xml import PubmedXmlLimits

    with pytest.raises(ValidationError):
        PubmedXmlLimits(**{field: value})
