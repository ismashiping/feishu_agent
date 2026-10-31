"""Bounded, offline PDF text-layer extraction through pypdf."""

from contextlib import closing
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic
from typing import Literal
from uuid import UUID

import pypdf
from pydantic import Field, FileUrl, HttpUrl
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from clinical_agent.domain.models import (
    DTO,
    LiteratureDocument,
    MetadataText,
    ParsedPdf,
    PdfSourceUnit,
    PositiveInteger,
    PublicationDate,
    PubMedID,
)


class PdfParseLimits(DTO):
    max_file_bytes: PositiveInteger = 20 * 1024 * 1024
    max_pages: PositiveInteger = 200
    max_page_stream_bytes: PositiveInteger = 10 * 1024 * 1024
    max_total_characters: PositiveInteger = 1_000_000
    max_seconds: float = Field(default=30.0, gt=0, strict=True, allow_inf_nan=False)


class PdfMetadataOverrides(DTO):
    title: MetadataText | None = None
    authors: list[MetadataText] | None = None
    publication_date: PublicationDate | None = None
    journal: MetadataText | None = None
    doi: MetadataText | None = None
    pmid: PubMedID | None = None
    source_url: HttpUrl | None = None


class PdfParseError(Exception):
    """A flat parser error whose text contains only a stable public code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def parse_pdf(
    path: Path,
    *,
    allowed_root: Path,
    document_id: UUID,
    ingestion_time: datetime,
    metadata: PdfMetadataOverrides | None = None,
    limits: PdfParseLimits | None = None,
) -> ParsedPdf:
    policy = limits if limits is not None else PdfParseLimits()
    overrides = metadata if metadata is not None else PdfMetadataOverrides()
    deadline = monotonic() + policy.max_seconds

    def check_deadline() -> None:
        if monotonic() > deadline:
            raise PdfParseError("pdf_timeout")

    try:
        root = allowed_root.resolve(strict=True)
        resolved = path.resolve(strict=True)
        if not root.is_dir() or not resolved.is_relative_to(root) or not resolved.is_file():
            raise PdfParseError("pdf_path_invalid")
    except OSError:
        raise PdfParseError("pdf_path_invalid") from None

    try:
        with resolved.open("rb") as source:
            snapshot = source.read(policy.max_file_bytes + 1)
    except OSError:
        raise PdfParseError("pdf_io_error") from None
    if len(snapshot) > policy.max_file_bytes:
        raise PdfParseError("pdf_too_large")
    check_deadline()

    units: list[PdfSourceUnit] = []
    characters = 0
    try:
        with BytesIO(snapshot) as stream, closing(PdfReader(stream, strict=True)) as reader:
            if reader.is_encrypted:
                raise PdfParseError("pdf_encrypted")
            page_count = len(reader.pages)
            if page_count == 0:
                raise PdfParseError("pdf_no_pages")
            if page_count > policy.max_pages:
                raise PdfParseError("pdf_page_limit")
            for number, page in enumerate(reader.pages, start=1):
                check_deadline()
                contents = page.get_contents()
                if contents is not None and len(contents.get_data()) > policy.max_page_stream_bytes:
                    raise PdfParseError("pdf_stream_limit")
                text = (
                    (page.extract_text() or "")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                    .replace("\0", "")
                )
                check_deadline()
                characters += len(text) + (2 if units else 0)
                if characters > policy.max_total_characters:
                    raise PdfParseError("pdf_text_limit")
                units.append(PdfSourceUnit(page=number, text=text))
            if not any(unit.text.strip() for unit in units):
                raise PdfParseError("pdf_no_text")
            info = reader.metadata
            pdf_title = info.title if info is not None else None
            pdf_author = info.author if info is not None else None
    except (PyPdfError, ValueError, KeyError, TypeError, RecursionError):
        raise PdfParseError("pdf_invalid") from None
    except OSError:
        raise PdfParseError("pdf_io_error") from None

    title_origin: Literal["manual", "document_metadata", "filename"]
    if overrides.title is not None:
        title, title_origin = overrides.title, "manual"
    elif isinstance(pdf_title, str) and pdf_title.strip():
        title, title_origin = pdf_title, "document_metadata"
    else:
        title, title_origin = resolved.stem, "filename"
    authors = overrides.authors
    if authors is None:
        authors = [pdf_author] if isinstance(pdf_author, str) and pdf_author.strip() else []

    document = LiteratureDocument(
        document_id=document_id,
        title=title,
        title_origin=title_origin,
        authors=authors,
        publication_date=overrides.publication_date or PublicationDate(precision="unknown"),
        journal=overrides.journal,
        doi=overrides.doi,
        pmid=overrides.pmid,
        source_type="pdf",
        source_url=overrides.source_url,
        source_uri=FileUrl(resolved.as_uri()),
        content_scope="extracted_text",
        content_hash=sha256(snapshot).hexdigest(),
        ingestion_time=ingestion_time,
        abstract=None,
        text="\n\n".join(unit.text for unit in units),
        evidence_chunks=[],
    )
    return ParsedPdf(
        document=document,
        source_units=units,
        page_count=len(units),
        parser_version=pypdf.__version__,
    )
