"""Local evidence retrieval contracts; scores are similarity, never evidence quality."""

from datetime import UTC, date
from hashlib import sha256
from typing import Annotated, Literal, Self, get_args
from uuid import UUID

from pydantic import AwareDatetime, BeforeValidator, Field, StringConstraints, model_validator

from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.fulltext import FulltextPassage
from clinical_agent.domain.governance import GovernanceState
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
from clinical_agent.domain.openalex import OpenAlexOptions, OpenAlexProvenance, OpenAlexRecord
from clinical_agent.domain.pubmed import PubMedOptions, SearchProvenance

RetrievalCode = Literal[
    "retrieval_language_unsupported",
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
SourceType = Literal["pdf", "pubmed", "openalex"]
ContentScope = Literal["abstract", "extracted_text", "full_text"]


class RetrievalOptions(DTO):
    mode: Literal["vector", "keyword", "hybrid"] = "vector"
    candidate_limit: Annotated[PositiveInteger, Field(le=100)] = 50
    keyword_query: (
        Annotated[
            str,
            StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000),
        ]
        | None
    ) = None
    date_from: date | None = None
    date_to: date | None = None
    top_k: Annotated[PositiveInteger, Field(le=20)] = 5
    min_similarity: Similarity = 0.0
    source_types: Annotated[list[SourceType], Field(min_length=1, max_length=3)] = [
        "pdf",
        "pubmed",
        "openalex",
    ]
    content_scopes: Annotated[list[ContentScope], Field(min_length=1, max_length=3)] = [
        "abstract",
        "extracted_text",
        "full_text",
    ]
    document_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)] | None = None

    @model_validator(mode="after")
    def validate_unique_filters(self) -> Self:
        if self.candidate_limit < self.top_k:
            raise ValueError("Candidate limit must cover top_k")
        if self.mode == "vector" and self.keyword_query is not None:
            raise ValueError("Keyword query requires keyword or hybrid mode")
        if self.mode != "vector" and self.min_similarity != 0:
            raise ValueError("Cosine threshold is not an FTS or RRF threshold")
        if (
            (self.date_from is None) != (self.date_to is None)
            or self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("Supply an ordered pair of local date bounds")
        for items in (self.source_types, self.content_scopes, self.document_ids):
            if items is not None and len(set(items)) != len(items):
                raise ValueError("Retrieval filters must not contain duplicate values")
        return self


class RetrievalRequest(DTO):
    question: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
    ]
    scope: Literal["local", "online", "hybrid"] = "local"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)
    pubmed: PubMedOptions | None = None
    openalex: OpenAlexOptions | None = None

    @model_validator(mode="after")
    def validate_scope_options(self) -> Self:
        if self.scope == "local" and (self.pubmed is not None or self.openalex is not None):
            raise ValueError("PubMed options require an online scope")
        if self.scope == "online" and (
            self.options.mode != "vector"
            or self.options.date_from is not None
            or self.options.keyword_query is not None
        ):
            raise ValueError("Local ranking options do not apply to online-only searches")
        if self.scope != "local" and (
            self.options.document_ids is not None or self.options.min_similarity != 0
        ):
            raise ValueError("Online sources do not support local IDs or a cosine threshold")
        return self


class RetrievalLimits(DTO):
    max_seconds: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)] = 30.0


class DocumentSummary(SourceMetadata):
    governance: GovernanceState = Field(default_factory=GovernanceState)
    document_id: UUID
    title: MetadataText
    title_origin: Literal[
        "manual", "document_metadata", "filename", "pubmed_metadata", "openalex_metadata"
    ]
    authors: list[MetadataText]
    publication_date: PublicationDate
    journal: MetadataText | None
    doi: MetadataText | None
    pmid: PubMedID | None
    openalex_record: OpenAlexRecord | None = None
    snapshot_xml: str | None = None
    publication_types: list[str] = Field(default_factory=list)
    source_notices: list[str] = Field(default_factory=list)
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
            else {"openalex_metadata"}
            if self.source_type == "openalex"
            else {"manual", "pubmed_metadata"}
        )
        if self.title_origin not in origins or (self.source_type == "pubmed" and self.pmid is None):
            raise ValueError("Bibliographic identity must match the declared source type")
        if self.snapshot_xml is not None and (
            self.source_type != "pubmed"
            or sha256(self.snapshot_xml.encode()).hexdigest() != self.content_hash
        ):
            raise ValueError("Online source snapshot must match its hash")
        if self.source_type == "openalex":
            if self.openalex_record is None:
                raise ValueError("OpenAlex evidence requires acquired snapshot")
            r = self.openalex_record
            r.verify_snapshot()
            if (
                self.title,
                self.doi,
                self.authors,
                self.journal,
                self.publication_date,
                self.content_hash,
                str(self.source_url),
            ) != (
                r.title,
                r.doi,
                r.authors,
                r.journal,
                r.publication_date,
                r.content_hash,
                r.openalex_id,
            ) or self.pmid is not None:
                raise ValueError("OpenAlex metadata must match acquired snapshot")
        self.ingestion_time = self.ingestion_time.astimezone(UTC)
        return self


class EvidenceHit(DTO):
    fulltext: list[FulltextPassage] = Field(default_factory=list)
    chunk: EvidenceChunk
    document: DocumentSummary
    score: Similarity
    keyword_rank: PositiveInteger | None = None
    vector_rank: PositiveInteger | None = None
    fusion_score: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)] | None = None
    score_type: Literal["cosine_similarity", "pubmed_rank", "openalex_rank", "fts_rank", "rrf"] = (
        "cosine_similarity"
    )
    rank: PositiveInteger

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if len(self.fulltext) > (3 if self.document.source_type == "openalex" else 2) or any(
            (
                passage.paper_key
                != (
                    "doi:" + self.document.doi
                    if self.document.doi
                    else self.document.openalex_record.openalex_id
                )
                if self.document.source_type == "openalex"
                else passage.pmid != self.document.pmid
            )
            for passage in self.fulltext
        ):
            raise ValueError("Fulltext passages must belong to the selected PMID")
        if self.chunk.document_id != self.document.document_id or (
            self.score_type not in {"pubmed_rank", "openalex_rank"}
            and self.chunk.embedding_info is None
        ):
            raise ValueError("Hits require encoded evidence and its matching document")
        if self.score_type == "rrf":
            expected = sum(
                1.0 / (60 + rank)
                for rank in [self.keyword_rank, self.vector_rank]
                if rank is not None
            )
            if not expected or self.fusion_score != expected or self.score != expected:
                raise ValueError("RRF score must match channel ranks")
        elif self.fusion_score is not None:
            raise ValueError("Fusion scores are only valid for RRF hits")
        if self.score_type == "fts_rank" and (
            self.keyword_rank is None or self.vector_rank is not None or self.score < 0
        ):
            raise ValueError("FTS hits require their keyword rank")
        if self.score_type in {"pubmed_rank", "openalex_rank"} and (
            self.chunk.embedding_info is not None
            or self.document.source_type
            != ("openalex" if self.score_type == "openalex_rank" else "pubmed")
            or self.document.source_url is None
            or self.score <= 0
        ):
            raise ValueError(
                "PubMed ranks require actual online metadata, without fabricated embeddings"
            )
        if self.document.source_type == "openalex":
            record = self.document.openalex_record
            loc = self.chunk.location
            if record.abstract[loc.start : loc.end] != self.chunk.text:
                raise ValueError("OpenAlex evidence must match acquired abstract")
        if any(
            getattr(self.chunk.source_metadata, name) != getattr(self.document, name)
            for name in SourceMetadata.model_fields
        ):
            raise ValueError("Hit source metadata must refer to one source snapshot")
        return self


ChannelStatus = dict[Literal["keyword", "vector"], Literal["ok", "not_requested"]]


def _vector_channels() -> ChannelStatus:
    return {"keyword": "not_requested", "vector": "ok"}


class RetrievalResult(DTO):
    channel_status: ChannelStatus = Field(default_factory=_vector_channels)
    degraded: Literal[False] = False
    warnings: list[str] = Field(default_factory=list)
    strategy_version: Literal["vector-v1", "fts-simple-v1", "rrf-v1"] = "vector-v1"
    scope: Literal["local", "online", "hybrid"] = "local"
    search_provenance: SearchProvenance | OpenAlexProvenance | None = None
    options: RetrievalOptions
    embedding_info: EmbeddingInfo | None
    hits: list[EvidenceHit]

    @model_validator(mode="after")
    def validate_hits(self) -> Self:
        if (
            (self.embedding_info is not None and self.embedding_info != retrieval_embedding_info())
            or (self.scope == "local" and self.embedding_info is None)
            or (self.scope == "online" and self.embedding_info is not None)
            or len(self.hits) > self.options.top_k
        ):
            raise ValueError("Result model and hit count must match the retrieval contract")
        ids = [item.chunk.chunk_id for item in self.hits]
        if len(set(ids)) != len(ids):
            raise ValueError("Retrieval must not return duplicate chunks")
        if self.scope != "local" and self.search_provenance is None:
            raise ValueError("Online search provenance is required")
        if self.scope != "online":
            expected_type = {"vector": "cosine_similarity", "keyword": "fts_rank", "hybrid": "rrf"}[
                self.options.mode
            ]
            if (
                any(
                    h.score_type not in {expected_type, "pubmed_rank", "openalex_rank"}
                    for h in self.hits
                )
                or self.scope == "local"
                and any(h.score_type in {"pubmed_rank", "openalex_rank"} for h in self.hits)
            ):
                raise ValueError("Local hit types must match the requested retrieval mode")
            expected_status = {
                "keyword": "not_requested" if self.options.mode == "vector" else "ok",
                "vector": "not_requested" if self.options.mode == "keyword" else "ok",
            }
            if (
                self.channel_status != expected_status
                or self.strategy_version
                != {"vector": "vector-v1", "keyword": "fts-simple-v1", "hybrid": "rrf-v1"}[
                    self.options.mode
                ]
            ):
                raise ValueError("Channel state must match the requested strategy")
        if self.scope == "online" and any(
            h.score_type not in {"pubmed_rank", "openalex_rank"} for h in self.hits
        ):
            raise ValueError("Online retrieval must contain only official ranked hits")
        order = [
            (
                0 if item.score_type not in {"pubmed_rank", "openalex_rank"} else 1,
                -item.score,
                item.chunk.chunk_id.int,
            )
            for item in self.hits
        ]
        if order != sorted(order):
            raise ValueError("Hits must retain stable descending similarity order")
        for index, item in enumerate(self.hits, 1):
            if self.options.date_from is not None and item.score_type not in {
                "pubmed_rank",
                "openalex_rank",
            }:
                publication = item.document.publication_date
                if (
                    publication.precision != "day"
                    or publication.year is None
                    or publication.month is None
                    or publication.day is None
                    or self.options.date_to is None
                    or not self.options.date_from
                    <= date(publication.year, publication.month, publication.day)
                    <= self.options.date_to
                ):
                    raise ValueError("Local dates require an actual day-precise publication date")
            if (
                item.rank != index
                or (
                    item.score_type == "cosine_similarity"
                    and (
                        item.score < self.options.min_similarity
                        or item.chunk.embedding_info != self.embedding_info
                    )
                )
                or (
                    item.score_type not in {"pubmed_rank", "openalex_rank"}
                    and item.chunk.embedding_info != self.embedding_info
                )
                or item.document.source_type not in self.options.source_types
                or item.document.content_scope not in self.options.content_scopes
                or (
                    self.options.document_ids is not None
                    and item.document.document_id not in self.options.document_ids
                )
            ):
                raise ValueError("Each hit must match rank, threshold, filters and query model")
        return self
