"""Local evidence retrieval contracts; scores are similarity, never evidence quality."""

from datetime import UTC
from typing import Annotated, Literal, Self, get_args
from uuid import UUID

from pydantic import AwareDatetime, BeforeValidator, Field, StringConstraints, model_validator

from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.models import (
    DTO,
    EmbeddingInfo,
    EvidenceChunk,
    LiteratureDocument,
    MetadataText,
    PositiveInteger,
    PublicationDate,
    PubMedID,
    SourceMetadata,
)

RetrievalCode = Literal[
    "retrieval_embedding_failed",
    "retrieval_model_mismatch",
    "retrieval_failed",
    "retrieval_corrupt",
    "retrieval_timeout",
]


class RetrievalError(ValueError):
    def __init__(self, code: RetrievalCode) -> None:
        if code not in get_args(RetrievalCode):
            code = "retrieval_failed"
        self.code = code
        super().__init__(code)


def retrieval_embedding_info() -> EmbeddingInfo:
    return EmbeddingInfo(
        model_id="intfloat/multilingual-e5-base",
        model_revision="d128750597153bb5987e10b1c3493a34e5a4502a",
        tokenizer_revision="d128750597153bb5987e10b1c3493a34e5a4502a",
        dimension=768,
        normalized=True,
        chunking_version="source-unit-v1",
    )


def validate_query_embedding(query: QueryEmbedding) -> QueryEmbedding:
    query = QueryEmbedding.model_validate(query)
    if query.embedding_info != retrieval_embedding_info():
        raise RetrievalError("retrieval_model_mismatch")
    return query


def _number(value: object) -> object:
    if type(value) not in (int, float):
        raise ValueError("Similarity must be a finite number")
    return value


Similarity = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False), BeforeValidator(_number)]
SourceType = Literal["pdf", "pubmed"]
ContentScope = Literal["abstract", "extracted_text", "full_text"]


class RetrievalOptions(DTO):
    top_k: Annotated[PositiveInteger, Field(le=20)] = 5
    min_similarity: Similarity = 0.0
    source_types: Annotated[list[SourceType], Field(min_length=1, max_length=2)] = ["pdf", "pubmed"]
    content_scopes: Annotated[list[ContentScope], Field(min_length=1, max_length=3)] = [
        "abstract",
        "extracted_text",
        "full_text",
    ]
    document_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)] | None = None

    @model_validator(mode="after")
    def validate_unique_filters(self) -> Self:
        for items in (self.source_types, self.content_scopes, self.document_ids):
            if items is not None and len(set(items)) != len(items):
                raise ValueError("Retrieval filters must not contain duplicate values")
        return self


class RetrievalRequest(DTO):
    question: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
    ]
    scope: Literal["local"] = "local"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class RetrievalLimits(DTO):
    max_seconds: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)] = 30.0


class DocumentSummary(SourceMetadata):
    document_id: UUID
    title: MetadataText
    title_origin: Literal["manual", "document_metadata", "filename", "pubmed_metadata"]
    authors: list[MetadataText]
    publication_date: PublicationDate
    journal: MetadataText | None
    doi: MetadataText | None
    pmid: PubMedID | None
    ingestion_time: AwareDatetime

    @classmethod
    def from_document(cls, document: LiteratureDocument) -> Self:
        document = LiteratureDocument.model_validate(document)
        return cls.model_validate(
            document.model_dump(exclude={"text", "abstract", "evidence_chunks"})
        )

    @model_validator(mode="after")
    def validate_bibliography(self) -> Self:
        origins = (
            {"manual", "document_metadata", "filename"}
            if self.source_type == "pdf"
            else {"manual", "pubmed_metadata"}
        )
        if self.title_origin not in origins or (self.source_type == "pubmed" and self.pmid is None):
            raise ValueError("Bibliographic identity must match the declared source type")
        self.ingestion_time = self.ingestion_time.astimezone(UTC)
        return self


class EvidenceHit(DTO):
    chunk: EvidenceChunk
    document: DocumentSummary
    score: Similarity
    score_type: Literal["cosine_similarity"] = "cosine_similarity"
    rank: PositiveInteger

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if self.chunk.embedding_info is None or self.chunk.document_id != self.document.document_id:
            raise ValueError("Hits require encoded evidence and its matching document")
        if any(
            getattr(self.chunk.source_metadata, name) != getattr(self.document, name)
            for name in SourceMetadata.model_fields
        ):
            raise ValueError("Hit source metadata must refer to one source snapshot")
        return self


class RetrievalResult(DTO):
    scope: Literal["local"] = "local"
    options: RetrievalOptions
    embedding_info: EmbeddingInfo
    hits: list[EvidenceHit]

    @model_validator(mode="after")
    def validate_hits(self) -> Self:
        if self.embedding_info != retrieval_embedding_info() or len(self.hits) > self.options.top_k:
            raise ValueError("Result model and hit count must match the retrieval contract")
        ids = [item.chunk.chunk_id for item in self.hits]
        if len(set(ids)) != len(ids):
            raise ValueError("Retrieval must not return duplicate chunks")
        order = [(-item.score, item.chunk.chunk_id.int) for item in self.hits]
        if order != sorted(order):
            raise ValueError("Hits must retain stable descending similarity order")
        for index, item in enumerate(self.hits, 1):
            if (
                item.rank != index
                or item.score < self.options.min_similarity
                or item.chunk.embedding_info != self.embedding_info
                or item.document.source_type not in self.options.source_types
                or item.document.content_scope not in self.options.content_scopes
                or (
                    self.options.document_ids is not None
                    and item.document.document_id not in self.options.document_ids
                )
            ):
                raise ValueError("Each hit must match rank, threshold, filters and query model")
        return self
