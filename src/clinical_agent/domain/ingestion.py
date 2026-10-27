"""Offline ingestion contracts and provenance validation, without infrastructure imports."""

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, Field, field_validator, model_validator

from clinical_agent.domain.chunking import ChunkingPolicy, ChunkingResult, TokenizerProfile
from clinical_agent.domain.embedding import EmbeddedChunk
from clinical_agent.domain.models import (
    DTO,
    MetadataText,
    NonnegativeInteger,
    ParsedPdf,
    ParsedPubmedArticle,
    PositiveInteger,
    PubmedRejectionCode,
)

OperationCode = Literal[
    "source_failed",
    "ingestion_invalid",
    "chunking_failed",
    "embedding_failed",
    "storage_failed",
    "ingestion_timeout",
    "batch_limit",
    "storage_corrupt",
    "storage_conflict",
    "storage_unavailable",
    "source_invalid",
]


class IngestionError(ValueError):
    def __init__(self, code: OperationCode) -> None:
        self.code = code
        super().__init__(code)


def document_id_for(source_type: str, identity: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"clinical-literature-agent:v1:{source_type}:{identity}")


def chunk_id_for(
    document_id: UUID, profile: TokenizerProfile, policy: ChunkingPolicy, index: int
) -> UUID:
    identity = json.dumps(
        {"profile": profile.model_dump(), "policy": policy.model_dump(), "index": index},
        sort_keys=True,
        ensure_ascii=False,
    )
    return uuid5(document_id, identity)


class ImportRequest(DTO):
    source_type: Literal["pdf", "pubmed_xml"]
    path: Path
    allowed_root: Path
    ingestion_time: AwareDatetime

    @field_validator("ingestion_time", mode="before")
    @classmethod
    def require_explicit_datetime(cls, value: object) -> object:
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("An explicit timezone-aware datetime is required")
        return value


class ParsedSource(DTO):
    parsed: ParsedPdf | ParsedPubmedArticle
    parser_name: Literal["pypdf", "defusedxml"]
    parser_version: MetadataText

    @model_validator(mode="after")
    def validate_parser(self) -> Self:
        if isinstance(self.parsed, ParsedPdf):
            if self.parser_name != "pypdf" or self.parser_version != self.parsed.parser_version:
                raise ValueError("PDF parser identity must match its parsed source")
        elif self.parser_name != "defusedxml":
            raise ValueError("XML parser identity must match its parsed source")
        return self


class ParsedEntry(DTO):
    index: PositiveInteger
    source: ParsedSource | None
    error_code: PubmedRejectionCode | None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if (self.source is None) == (self.error_code is None):
            raise ValueError("Each parsed entry requires exactly one source or rejection")
        return self


class ParsedBatch(DTO):
    entries: list[ParsedEntry]

    @model_validator(mode="after")
    def validate_indices(self) -> Self:
        if any(item.index != i for i, item in enumerate(self.entries, 1)):
            raise ValueError("Entries must retain consecutive source indices")
        return self


class IngestionMetadata(DTO):
    schema_version: Literal[1] = 1
    parser_name: Literal["pypdf", "defusedxml"]
    parser_version: MetadataText
    profile: TokenizerProfile
    policy: ChunkingPolicy


class PreparedIngestion(DTO):
    source: ParsedSource
    chunking: ChunkingResult
    embedded: list[EmbeddedChunk]

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        parsed, profile, policy = self.source.parsed, self.chunking.profile, self.chunking.policy
        if not 0 < len(self.embedded) == len(self.chunking.chunks) <= 128:
            raise ValueError("A document requires a complete bounded set of encoded chunks")
        if (
            profile.model_id != "intfloat/multilingual-e5-base"
            or profile.model_revision != "d128750597153bb5987e10b1c3493a34e5a4502a"
            or profile.tokenizer_revision != profile.model_revision
            or profile.document_prefix != "passage: "
            or profile.model_max_tokens != 512
        ):
            raise ValueError("The persistence model identity must match the verified E5 model")
        for original, encoded in zip(self.chunking.chunks, self.embedded, strict=True):
            parsed.validate_chunk(original.evidence)
            parsed.validate_chunk(encoded.evidence)
            info = encoded.evidence.embedding_info
            if original.evidence.embedding_info is not None or info is None:
                raise ValueError("Prepared input and encoded output must retain their states")
            actual = encoded.evidence.model_dump()
            actual["embedding_info"] = None
            if actual != original.evidence.model_dump() or (
                info.model_id != profile.model_id
                or info.model_revision != profile.model_revision
                or info.tokenizer_revision != profile.tokenizer_revision
                or info.dimension != 768
                or not info.normalized
                or info.chunking_version != policy.chunking_version
            ):
                raise ValueError(
                    "Encoded evidence must match its ordered source and model identity"
                )
        keys: list[tuple[int, int]] = []
        units: list[tuple[str, int, int | None]]
        if isinstance(parsed, ParsedPdf):
            units = [(unit.text, 0, unit.page) for unit in parsed.source_units]
        else:
            units = [(unit.text, unit.start, None) for unit in parsed.source_units]
        for unit_index, (unit_text, offset, page) in enumerate(units):
            cursor = 0
            for item in self.chunking.chunks:
                location = item.evidence.location
                belongs = (
                    location.page == page
                    if page is not None
                    else offset <= location.start < location.end <= offset + len(unit_text)
                )
                if not belongs:
                    continue
                start, end = location.start - offset, location.end - offset
                if start < cursor or unit_text[cursor:start].strip():
                    raise ValueError("Chunks must not overlap or omit non-whitespace source text")
                keys.append((unit_index, start))
                cursor = end
            if unit_text[cursor:].strip():
                raise ValueError("Chunks must cover all non-whitespace source text")
        ordered = [
            (item.evidence.location.page or 0, item.evidence.location.start)
            for item in self.chunking.chunks
        ]
        if ordered != sorted(ordered) or len(keys) != len(self.chunking.chunks):
            raise ValueError("Chunks must retain source-unit order")
        return self


def equivalent_content(one: PreparedIngestion, two: PreparedIngestion) -> bool:
    def signature(value: PreparedIngestion) -> dict[str, object]:
        value = PreparedIngestion.model_validate(value)
        doc = value.source.parsed.document
        document = doc.model_dump(
            exclude={"document_id", "ingestion_time", "source_uri", "evidence_chunks"}
        )
        if doc.title_origin == "filename":
            document.pop("title")
        return {
            "document": document,
            "units": [unit.model_dump() for unit in value.source.parsed.source_units],
            "parser": (value.source.parser_name, value.source.parser_version),
            "profile": value.chunking.profile.model_dump(),
            "policy": value.chunking.policy.model_dump(),
            "chunks": [
                {
                    "text": item.evidence.text,
                    "location": item.evidence.location.model_dump(),
                    "token_count": item.token_count,
                }
                for item in value.chunking.chunks
            ],
        }

    return signature(one) == signature(two)


class StoreResult(DTO):
    status: Literal["imported", "already_present", "needs_update", "conflict"]
    document_id: UUID
    chunk_count: PositiveInteger


class IngestionResult(DTO):
    index: PositiveInteger
    status: Literal["imported", "already_present", "needs_update", "conflict", "rejected", "failed"]
    document_id: UUID | None
    chunk_count: NonnegativeInteger
    error_code: OperationCode | PubmedRejectionCode | None

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.status in {"failed", "rejected"}:
            if self.document_id is not None or self.chunk_count != 0 or self.error_code is None:
                raise ValueError("Failed entries require an error and no claimed document")
        elif self.document_id is None or self.chunk_count == 0 or self.error_code is not None:
            raise ValueError("Stored entries require a canonical document and no error")
        return self


class BatchIngestionResult(DTO):
    entries: list[IngestionResult]
    error_code: OperationCode | None = None

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        if (self.error_code is not None and self.entries) or any(
            item.index != i for i, item in enumerate(self.entries, 1)
        ):
            raise ValueError("Batch errors and ordered per-entry outcomes must be distinct")
        return self


class IngestionLimits(DTO):
    max_documents: PositiveInteger = 32
    max_seconds: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)] = 120.0
