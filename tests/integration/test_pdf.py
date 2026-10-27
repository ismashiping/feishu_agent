"""Real synthetic PDF parsing; fake clocks/failures only at explicit boundaries."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

pytestmark = pytest.mark.integration
DOC_ID = UUID("00000000-0000-4000-8000-000000000201")
NOW = datetime(2026, 10, 26, 15, tzinfo=UTC)


def _write_pdf(path: Path, texts=("Alpha", "", "Beta"), metadata=None, password=None):
    with PdfWriter() as writer:
        for text in texts:
            page = writer.add_blank_page(width=300, height=300)
            if text:
                font = DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
                page[NameObject("/Resources")] = DictionaryObject(
                    {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
                )
                stream = DecodedStreamObject()
                stream.set_data(b"BT /F1 12 Tf 20 250 Td (" + text.encode("ascii") + b") Tj ET")
                page.replace_contents(stream)
        if metadata:
            writer.add_metadata(metadata)
        if password is not None:
            writer.encrypt(password)
        writer.write(path)
    return path


def _parse(module, path, root, **kwargs):
    return module.parse_pdf(
        path, allowed_root=root, document_id=DOC_ID, ingestion_time=NOW, **kwargs
    )


def test_real_pdf_retains_pages_snapshot_metadata_and_roundtrip(tmp_path):
    from clinical_agent.adapters import pdf
    from clinical_agent.domain.models import ParsedPdf

    path = _write_pdf(
        tmp_path / "synthetic.pdf",
        metadata={
            "/Title": " Synthetic title ",
            "/Author": "Group A; Group B",
            "/CreationDate": "D:20200101000000Z",
        },
    )
    snapshot = path.read_bytes()
    result = _parse(pdf, path, tmp_path)
    assert result.page_count == 3
    assert [unit.page for unit in result.source_units] == [1, 2, 3]
    assert [unit.text for unit in result.source_units] == ["Alpha", "", "Beta"]
    assert {unit.normalization_version for unit in result.source_units} == {"pdf-text-v1"}
    document = result.document
    assert document.document_id == DOC_ID and document.ingestion_time == NOW
    assert document.content_hash == hashlib.sha256(snapshot).hexdigest()
    assert str(document.source_uri) == path.resolve().as_uri()
    assert document.content_scope == "extracted_text"
    assert document.title == "Synthetic title" and document.title_origin == "document_metadata"
    assert document.authors == ["Group A; Group B"]
    assert document.publication_date.precision == "unknown"
    assert document.doi is document.pmid is document.journal is document.source_url is None
    assert document.text == "Alpha\n\n\n\nBeta"
    assert document.abstract is None and document.evidence_chunks == []
    assert result.parser_name == "pypdf" and result.parser_version == "6.21.2"
    assert ParsedPdf.model_validate_json(result.model_dump_json()) == result


def test_filename_fallback_and_manual_overrides(tmp_path):
    from clinical_agent.adapters import pdf
    from clinical_agent.domain.models import PublicationDate

    path = _write_pdf(tmp_path / "fixture title.pdf", texts=("Alpha",))
    fallback = _parse(pdf, path, tmp_path)
    assert fallback.document.title == "fixture title"
    assert fallback.document.title_origin == "filename"
    assert fallback.document.authors == []
    overrides = pdf.PdfMetadataOverrides(
        title="Manual fixture",
        authors=[],
        doi="10.synthetic/test",
        pmid="1234567890",
        journal="Synthetic journal",
        publication_date=PublicationDate(precision="year", raw="2020", year=2020),
        source_url="https://example.org/fixture",
    )
    result = _parse(pdf, path, tmp_path, metadata=overrides)
    assert result.document.title_origin == "manual"
    assert result.document.title == "Manual fixture" and result.document.authors == []
    assert result.document.publication_date.year == 2020
    assert result.document.publication_date.month is None
    assert result.document.doi == "10.synthetic/test" and result.document.pmid == "1234567890"
    assert result.document.journal == "Synthetic journal"


@pytest.mark.parametrize("contents", [b"", b"not a PDF PRIVATE_SENTINEL", b"%PDF-1.7\nbroken"])
def test_damaged_pdf_has_safe_error(tmp_path, contents):
    from clinical_agent.adapters import pdf

    path = tmp_path / "PRIVATE_FILENAME.pdf"
    path.write_bytes(contents)
    with pytest.raises(pdf.PdfParseError) as caught:
        _parse(pdf, path, tmp_path)
    assert caught.value.code == "pdf_invalid"
    assert str(caught.value) == "pdf_invalid"


@pytest.mark.parametrize("password", ["", "fixture-password"])
def test_encrypted_pdf_is_rejected_even_with_empty_password(tmp_path, password):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "encrypted.pdf", password=password)
    with pytest.raises(pdf.PdfParseError, match="^pdf_encrypted$"):
        _parse(pdf, path, tmp_path)


@pytest.mark.parametrize("texts,code", [((), "pdf_no_pages"), (("", ""), "pdf_no_text")])
def test_empty_documents_are_not_success(tmp_path, texts, code):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "empty.pdf", texts=texts)
    with pytest.raises(pdf.PdfParseError, match="^" + code + "$"):
        _parse(pdf, path, tmp_path)


def test_image_only_document_has_no_text_and_no_ocr(tmp_path):
    from clinical_agent.adapters import pdf

    path = tmp_path / "image-only.pdf"
    with PdfWriter() as writer:
        page = writer.add_blank_page(width=100, height=100)
        image = DecodedStreamObject()
        image.set_data(bytes([0, 0, 0]))
        from pypdf.generic import NumberObject

        image.update(
            {
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(1),
                NameObject("/Height"): NumberObject(1),
                NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                NameObject("/BitsPerComponent"): NumberObject(8),
            }
        )
        # Only the synthetic image fixture needs an indirect image stream.
        image_ref = writer._add_object(image)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): image_ref})}
        )
        drawing = DecodedStreamObject()
        drawing.set_data(b"q 50 0 0 50 0 0 cm /Im0 Do Q")
        page.replace_contents(drawing)
        writer.write(path)
    with pytest.raises(pdf.PdfParseError, match="^pdf_no_text$"):
        _parse(pdf, path, tmp_path)


@pytest.mark.parametrize("case", ["missing", "directory", "outside"])
def test_paths_must_be_real_files_under_explicit_root(tmp_path, case):
    from clinical_agent.adapters import pdf

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    path = allowed / "missing.pdf"
    if case == "directory":
        path = allowed
    if case == "outside":
        path = _write_pdf(tmp_path / "outside.pdf")
    with pytest.raises(pdf.PdfParseError, match="^pdf_path_invalid$"):
        _parse(pdf, path, allowed)


@pytest.mark.parametrize(
    "name,value,code",
    [
        ("max_file_bytes", 1, "pdf_too_large"),
        ("max_pages", 1, "pdf_page_limit"),
        ("max_page_stream_bytes", 1, "pdf_stream_limit"),
        ("max_total_characters", 1, "pdf_text_limit"),
    ],
)
def test_budgets_reject_instead_of_returning_partial_documents(tmp_path, name, value, code):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "budget.pdf")
    limits = pdf.PdfParseLimits(**{name: value})
    with pytest.raises(pdf.PdfParseError, match="^" + code + "$"):
        _parse(pdf, path, tmp_path, limits=limits)


def test_cooperative_deadline_checked_after_extraction(tmp_path, monkeypatch):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "timeout.pdf", texts=("Alpha",))
    done = []
    original = PageObject.extract_text

    def delayed(page, *args, **kwargs):
        result = original(page, *args, **kwargs)
        done.append(True)
        return result

    monkeypatch.setattr(PageObject, "extract_text", delayed)
    monkeypatch.setattr(pdf, "monotonic", lambda: 40.0 if done else 0.0)
    with pytest.raises(pdf.PdfParseError, match="^pdf_timeout$"):
        _parse(pdf, path, tmp_path)


@pytest.mark.parametrize("failure", [False, True])
def test_files_streams_and_reader_close_on_success_or_failure(tmp_path, monkeypatch, failure):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "closing.pdf")
    streams, readers, closed, files = [], [], [], []

    class TrackingReader(PdfReader):
        def __init__(self, stream, **kwargs):
            streams.append(stream)
            super().__init__(stream, **kwargs)
            readers.append(self)

        def close(self):
            closed.append(self)
            super().close()

    original_open = Path.open

    def tracking_open(target, *args, **kwargs):
        stream = original_open(target, *args, **kwargs)
        if target == path:
            files.append(stream)
        return stream

    monkeypatch.setattr(pdf, "PdfReader", TrackingReader)
    monkeypatch.setattr(Path, "open", tracking_open)
    if failure:

        def broken(*args, **kwargs):
            raise PdfReadError("PRIVATE_ERROR_SENTINEL")

        monkeypatch.setattr(PageObject, "extract_text", broken)
        with pytest.raises(pdf.PdfParseError, match="^pdf_invalid$"):
            _parse(pdf, path, tmp_path)
    else:
        _parse(pdf, path, tmp_path)
    assert len(readers) == len(closed) == len(streams) == 1
    assert files and all(stream.closed for stream in files + streams)


def test_hash_and_parse_share_one_snapshot_even_if_original_changes(tmp_path, monkeypatch):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "snapshot.pdf", texts=("Original",))
    snapshot = path.read_bytes()

    def reader(stream, **kwargs):
        path.write_bytes(b"Changed by synthetic test after snapshot")
        return PdfReader(stream, **kwargs)

    monkeypatch.setattr(pdf, "PdfReader", reader)
    result = _parse(pdf, path, tmp_path)
    assert result.document.content_hash == hashlib.sha256(snapshot).hexdigest()
    assert result.source_units[0].text == "Original"


def test_normalization_is_minimal_and_versioned(tmp_path, monkeypatch):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "normalization.pdf", texts=("Alpha",))
    monkeypatch.setattr(PageObject, "extract_text", lambda *args, **kwargs: "  A\r\nB\rC\0 ")
    result = _parse(pdf, path, tmp_path)
    assert result.source_units[0].text == "  A\nB\nC "
    assert result.source_units[0].normalization_version == "pdf-text-v1"


def test_file_io_failure_is_safe(tmp_path, monkeypatch):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "io.pdf")

    def denied(*args, **kwargs):
        raise PermissionError("PRIVATE_FILE_SENTINEL")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(pdf.PdfParseError, match="^pdf_io_error$"):
        _parse(pdf, path, tmp_path)


def test_total_text_budget_includes_page_separators(tmp_path):
    from clinical_agent.adapters import pdf

    path = _write_pdf(tmp_path / "separators.pdf", texts=("A", "B"))
    with pytest.raises(pdf.PdfParseError, match="^pdf_text_limit$"):
        _parse(pdf, path, tmp_path, limits=pdf.PdfParseLimits(max_total_characters=2))
