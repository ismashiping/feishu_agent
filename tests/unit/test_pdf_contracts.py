"""Page provenance and public parse policy, independent of actual PDF I/O."""

from uuid import UUID

import pytest
from pydantic import ValidationError


@pytest.mark.parametrize(
    "field,value", [("page", 0), ("page", True), ("normalization_version", "unknown")]
)
def test_source_units_reject_invalid_identity(field, value):
    from clinical_agent.domain.models import PdfSourceUnit

    with pytest.raises(ValidationError):
        PdfSourceUnit.model_validate({"page": 1, "text": "", field: value})


@pytest.mark.parametrize("text", ["A\r\nB", "A\0B"])
def test_canonical_page_text_cannot_keep_raw_controls(text):
    from clinical_agent.domain.models import PdfSourceUnit

    with pytest.raises(ValidationError):
        PdfSourceUnit(page=1, text=text)


def test_page_units_preserve_whitespace_and_empty_pages():
    from clinical_agent.domain.models import PdfSourceUnit

    for text in ("", "  A α🙂\n "):
        unit = PdfSourceUnit(page=1, text=text)
        assert unit.text == text and unit.normalization_version == "pdf-text-v1"
        assert PdfSourceUnit.model_validate_json(unit.model_dump_json()) == unit


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_file_bytes", 0),
        ("max_pages", True),
        ("max_seconds", float("inf")),
        ("max_seconds", 0.0),
    ],
)
def test_parse_limits_are_explicit_and_bounded(field, value):
    from clinical_agent.adapters.pdf import PdfParseLimits

    with pytest.raises(ValidationError):
        PdfParseLimits(**{field: value})


def _document_data():
    return {
        "document_id": "00000000-0000-4000-8000-000000000201",
        "title": "Synthetic",
        "title_origin": "filename",
        "authors": [],
        "publication_date": {"precision": "unknown"},
        "journal": None,
        "doi": None,
        "pmid": None,
        "abstract": None,
        "text": "  A α🙂\n ",
        "source_type": "pdf",
        "source_uri": "file:///fixtures/synthetic.pdf",
        "source_url": None,
        "content_hash": "a" * 64,
        "content_scope": "extracted_text",
        "ingestion_time": "2026-10-26T15:00:00Z",
        "evidence_chunks": [],
    }


@pytest.mark.parametrize("case", ["valid", "page", "end", "text", "document", "source"])
def test_page_chunk_is_rebuilt_from_its_own_source_unit(case):
    from clinical_agent.domain.models import EvidenceChunk, LiteratureDocument, ParsedPdf

    data = _document_data()
    document = LiteratureDocument.model_validate(data)
    parsed = ParsedPdf(
        document=document,
        source_units=[{"page": 1, "text": data["text"]}],
        page_count=1,
        parser_version="6.21.2",
    )
    chunk_data = {
        "chunk_id": str(UUID(int=202)),
        "document_id": str(document.document_id),
        "text": "A α🙂",
        "location": {"kind": "pdf_page", "page": 1, "start": 2, "end": 6},
        "embedding_info": None,
        "source_metadata": {
            key: data[key]
            for key in ("source_type", "source_uri", "source_url", "content_hash", "content_scope")
        },
    }
    if case == "page":
        chunk_data["location"]["page"] = 2
    if case == "end":
        chunk_data["location"].update(start=100, end=104)
    if case == "text":
        chunk_data["text"] = "B α🙂"
    if case == "document":
        chunk_data["document_id"] = str(UUID(int=203))
    if case == "source":
        chunk_data["source_metadata"]["content_hash"] = "b" * 64
    chunk = EvidenceChunk.model_validate(chunk_data)
    if case == "valid":
        assert parsed.validate_chunk(chunk) is None
    else:
        with pytest.raises(ValueError):
            parsed.validate_chunk(chunk)


@pytest.mark.parametrize("case", ["page_count", "page_order", "aggregate", "empty"])
def test_parsed_pdf_cannot_lie_about_page_units(case):
    from clinical_agent.domain.models import LiteratureDocument, ParsedPdf

    document = LiteratureDocument.model_validate(_document_data())
    payload = {
        "document": document,
        "source_units": [{"page": 1, "text": document.text}],
        "page_count": 1,
        "parser_version": "6.21.2",
    }
    if case == "page_count":
        payload["page_count"] = 2
    if case == "page_order":
        payload["source_units"][0]["page"] = 2
    if case == "aggregate":
        payload["source_units"][0]["text"] = "Different"
    if case == "empty":
        payload["source_units"] = []
    with pytest.raises(ValidationError):
        ParsedPdf.model_validate(payload)
