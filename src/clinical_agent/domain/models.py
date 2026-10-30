"""Validated offline literature provenance; validation does not verify a source."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FileUrl,
    HttpUrl,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Text must contain non-whitespace characters")
    return value


# 去除首尾空白后，至少有 1 个字符。
# MetadataText 适合标题、标签、名称等字段，因为通常不希望存储首尾多余的空格。
# PreservedText 适合正文、原始文本等需要保留格式的字段，因为空格、换行可能具有实际意义。

MetadataText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PreservedText = Annotated[str, AfterValidator(_nonblank)]  # 不能全是空白字符
PositiveInteger = Annotated[StrictInt, Field(gt=0)]
NonnegativeInteger = Annotated[StrictInt, Field(ge=0)]
SnapshotHash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PubMedID = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]*$")]


class DTO(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",  # 已有模型实例再次参与模型校验时
    )


class PublicationDate(DTO):
    precision: Literal["unknown", "year", "month", "day"]
    raw: PreservedText | None = None  # 保存原始日期文本
    year: Annotated[StrictInt, Field(ge=1, le=9999)] | None = None
    month: Annotated[StrictInt, Field(ge=1, le=12)] | None = None
    day: Annotated[StrictInt, Field(ge=1, le=31)] | None = None

    @model_validator(mode="after")
    def validate_precision(self) -> Self:
        required = {
            "unknown": (False, False, False),
            "year": (True, False, False),
            "month": (True, True, False),
            "day": (True, True, True),
        }
        actual = (self.year is not None, self.month is not None, self.day is not None)
        if actual != required[self.precision]:
            raise ValueError("Date components must match the declared precision")
        if self.precision != "unknown" and self.raw is None:
            raise ValueError("A known publication date must retain its raw value")
        if self.year is not None and self.month is not None and self.day is not None:
            date(self.year, self.month, self.day)
        return self


class SourceMetadata(DTO):
    source_type: Literal["pdf", "pubmed", "openalex"]
    source_url: HttpUrl | None  # 原始网络地址
    source_uri: FileUrl | HttpUrl  # 离线文件或真实在线来源 URI
    content_hash: SnapshotHash
    content_scope: Literal["abstract", "extracted_text", "full_text"]  # 当前保存内容的范围

    @field_validator("source_url")
    @classmethod
    def reject_url_credentials(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and (value.username is not None or value.password is not None):
            raise ValueError("Source URL must not contain credentials")
        return value

    @model_validator(mode="after")
    def validate_acquisition_scope(self) -> Self:
        if isinstance(self.source_uri, HttpUrl) and (
            self.source_type not in {"pubmed", "openalex"} or self.source_uri != self.source_url
        ):
            raise ValueError("Online URI must match the acquired public PubMed source")
        if self.source_type in {"pubmed", "openalex"} and self.content_scope != "abstract":
            raise ValueError("Offline PubMed content must be identified as abstract")
        return self


class EvidenceLocation(DTO):
    kind: Literal["pdf_page", "abstract", "fulltext"]
    page: PositiveInteger | None = None
    section: MetadataText | None = None
    start: NonnegativeInteger
    end: PositiveInteger

    @model_validator(mode="after")
    def validate_position(self) -> Self:
        if (self.kind == "pdf_page" and self.page is None) or (
            self.kind == "abstract" and self.page is not None
        ):
            raise ValueError("PDF locations require pages; abstract locations cannot have pages")
        if self.end <= self.start:
            raise ValueError("Location must be a nonempty half-open interval")
        return self


class EmbeddingInfo(DTO):
    model_id: MetadataText
    model_revision: MetadataText
    tokenizer_revision: MetadataText
    dimension: PositiveInteger
    normalized: StrictBool
    chunking_version: MetadataText


class EvidenceChunk(DTO):
    chunk_id: UUID
    document_id: UUID
    text: PreservedText
    location: EvidenceLocation
    embedding_info: EmbeddingInfo | None
    source_metadata: SourceMetadata

    @model_validator(mode="after")
    def validate_evidence_span(self) -> Self:
        expected = "pdf_page" if self.source_metadata.source_type == "pdf" else "abstract"
        if self.location.kind != expected:
            raise ValueError("Location kind must match the source type")
        if self.location.end - self.location.start != len(self.text):
            raise ValueError("Character interval must match the preserved evidence length")
        return self


class LiteratureDocument(SourceMetadata):
    document_id: UUID
    title: MetadataText
    title_origin: Literal["manual", "document_metadata", "filename", "pubmed_metadata"]
    authors: list[MetadataText]
    publication_date: PublicationDate
    journal: MetadataText | None
    doi: MetadataText | None
    pmid: PubMedID | None
    abstract: PreservedText | None
    text: PreservedText | None
    ingestion_time: AwareDatetime
    evidence_chunks: list[EvidenceChunk]

    @field_validator("ingestion_time", mode="before")
    @classmethod
    def reject_epoch_time(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Ingestion time must be an ISO datetime with timezone") from None
        if not isinstance(value, datetime):
            raise ValueError("Ingestion time must be an ISO datetime or datetime object")
        return value

    @field_validator("ingestion_time")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        if self.content_scope == "abstract":
            if self.abstract is None or self.text is not None:
                raise ValueError("Abstract-only documents require abstract and no full text")
        elif self.text is None:
            raise ValueError("Non-abstract documents require acquired text")
        if self.source_type == "pubmed" and self.pmid is None:
            raise ValueError("Offline PubMed documents require a PMID")
        if self.title_origin == "pubmed_metadata" and self.source_type != "pubmed":
            raise ValueError("PubMed title origin requires a PubMed source")
        if self.title_origin in {"filename", "document_metadata"} and self.source_type != "pdf":
            raise ValueError("PDF title origin requires a PDF source")

        seen: set[UUID] = set()
        identity: EmbeddingInfo | None = None
        for chunk in self.evidence_chunks:
            if chunk.document_id != self.document_id or chunk.chunk_id in seen:
                raise ValueError("Chunks must belong to this document and have unique IDs")
            seen.add(chunk.chunk_id)
            if any(
                getattr(chunk.source_metadata, field) != getattr(self, field)
                for field in SourceMetadata.model_fields
            ):
                raise ValueError("Chunk source snapshot must match the document")
            if chunk.location.kind == "abstract":
                if (
                    self.abstract is None
                    or chunk.location.end > len(self.abstract)
                    or self.abstract[chunk.location.start : chunk.location.end] != chunk.text
                ):
                    raise ValueError("Evidence must equal the located abstract slice")
            if chunk.embedding_info is not None:
                if identity is not None and identity != chunk.embedding_info:
                    raise ValueError("Document chunks must share one embedding identity")
                identity = chunk.embedding_info
        return self


class PdfSourceUnit(DTO):
    """Canonical per-page text; empty pages retain their original page number."""

    page: PositiveInteger
    text: str
    normalization_version: Literal["pdf-text-v1"] = "pdf-text-v1"

    @field_validator("text")
    @classmethod
    def require_canonical_text(cls, value: str) -> str:
        if "\r" in value or "\0" in value:
            raise ValueError("PDF source text must already use pdf-text-v1 normalization")
        return value


class ParsedPdf(DTO):
    document: LiteratureDocument
    source_units: list[PdfSourceUnit]
    page_count: PositiveInteger
    parser_name: Literal["pypdf"] = "pypdf"
    parser_version: MetadataText

    @model_validator(mode="after")
    def validate_pages(self) -> Self:
        if len(self.source_units) != self.page_count or any(
            unit.page != index for index, unit in enumerate(self.source_units, start=1)
        ):
            raise ValueError("PDF source units must retain consecutive original page numbers")
        if not any(unit.text.strip() for unit in self.source_units):
            raise ValueError("PDF source units require some extractable text")
        if (
            self.document.source_type != "pdf"
            or self.document.content_scope != "extracted_text"
            or self.document.evidence_chunks
            or self.document.text != "\n\n".join(unit.text for unit in self.source_units)
        ):
            raise ValueError("Parsed PDF document must match its unchunked source units")
        return self

    def validate_chunk(self, chunk: EvidenceChunk) -> None:
        """Validate an existing chunk against a page, without creating new evidence."""
        if chunk.document_id != self.document.document_id or any(
            getattr(chunk.source_metadata, field) != getattr(self.document, field)
            for field in SourceMetadata.model_fields
        ):
            raise ValueError("Evidence must refer to this PDF snapshot")
        location = chunk.location
        if location.kind != "pdf_page" or location.page is None or location.page > self.page_count:
            raise ValueError("Evidence must locate an existing PDF page")
        text = self.source_units[location.page - 1].text
        if location.end > len(text) or text[location.start : location.end] != chunk.text:
            raise ValueError("Evidence must equal its located page text")


class AbstractSourceUnit(DTO):
    index: PositiveInteger
    text: PreservedText
    label: MetadataText | None = None
    category: MetadataText | None = None
    start: NonnegativeInteger
    end: PositiveInteger
    normalization_version: Literal["pubmed-xml-text-v1"] = "pubmed-xml-text-v1"

    @model_validator(mode="after")
    def validate_span(self) -> Self:
        if " ".join(self.text.split()) != self.text or self.end - self.start != len(self.text):
            raise ValueError("Abstract source unit must have canonical text and an exact interval")
        return self


class ParsedPubmedArticle(DTO):
    document: LiteratureDocument
    source_units: list[AbstractSourceUnit]

    @model_validator(mode="after")
    def validate_sections(self) -> Self:
        if (
            self.document.source_type != "pubmed"
            or self.document.content_scope != "abstract"
            or self.document.evidence_chunks
            or not self.source_units
            or self.document.abstract != "\n\n".join(unit.text for unit in self.source_units)
        ):
            raise ValueError("PubMed source units must match the unchunked abstract document")
        offset = 0
        for index, unit in enumerate(self.source_units, start=1):
            if unit.index != index or unit.start != offset:
                raise ValueError("Abstract sections must retain consecutive indices and offsets")
            offset = unit.end + 2
        return self

    def validate_chunk(self, chunk: EvidenceChunk) -> None:
        if chunk.document_id != self.document.document_id or any(
            getattr(chunk.source_metadata, field) != getattr(self.document, field)
            for field in SourceMetadata.model_fields
        ):
            raise ValueError("Evidence must refer to this PubMed source snapshot")
        location = chunk.location
        abstract = self.document.abstract
        if (
            location.kind != "abstract"
            or abstract is None
            or location.end > len(abstract)
            or abstract[location.start : location.end] != chunk.text
        ):
            raise ValueError("Evidence must equal its located abstract text")
        if not any(
            unit.start <= location.start < location.end <= unit.end
            and (location.section is None or location.section == unit.label)
            for unit in self.source_units
        ):
            raise ValueError("Evidence must stay inside one declared abstract section")


PubmedRejectionCode = Literal[
    "pubmed_unsupported_record",
    "pubmed_invalid_pmid",
    "pubmed_pmid_conflict",
    "pubmed_duplicate_pmid",
    "pubmed_missing_title",
    "pubmed_no_abstract",
    "pubmed_invalid_author",
    "pubmed_invalid_date",
    "pubmed_doi_conflict",
    "pubmed_text_limit",
]


class PubmedXmlEntry(DTO):
    index: PositiveInteger
    status: Literal["parsed", "rejected"]
    article: ParsedPubmedArticle | None
    error_code: PubmedRejectionCode | None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.status == "parsed":
            if self.article is None or self.error_code is not None:
                raise ValueError("Parsed entries require an article and no rejection")
        elif self.article is not None or self.error_code is None:
            raise ValueError("Rejected entries require a rejection and no article")
        return self


class PubmedXmlBatch(DTO):
    source: SourceMetadata
    entries: list[PubmedXmlEntry]
    parser_name: Literal["defusedxml"] = "defusedxml"
    parser_version: MetadataText

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        if self.source.source_type != "pubmed" or self.source.content_scope != "abstract":
            raise ValueError("PubMed XML batches require an abstract source")
        pmids: set[str] = set()
        identities: set[UUID] = set()
        for index, entry in enumerate(self.entries, start=1):
            if entry.index != index:
                raise ValueError("Batch entries must retain consecutive source indices")
            if entry.article is not None:
                document = entry.article.document
                if (
                    document.pmid is None
                    or document.pmid in pmids
                    or document.document_id in identities
                ):
                    raise ValueError("Parsed entries require distinct PMIDs and document IDs")
                pmids.add(document.pmid)
                identities.add(document.document_id)
                if any(
                    getattr(self.source, field) != getattr(document, field)
                    for field in SourceMetadata.model_fields
                ):
                    raise ValueError("Parsed articles must retain their batch source snapshot")
        return self
