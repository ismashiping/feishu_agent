"""PostgreSQL schema declarations; schema evolution belongs to Alembic."""

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_type", "source_identity", name="uq_documents_source"),
        UniqueConstraint("document_id", "source_type", name="uq_documents_id_source"),
        CheckConstraint("source_type IN ('pdf','pubmed')", name="ck_documents_source_type"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_documents_hash"),
        CheckConstraint("btrim(title) <> '' AND btrim(source_uri) <> ''", name="ck_documents_text"),
        CheckConstraint("pmid IS NULL OR pmid ~ '^[1-9][0-9]*$'", name="ck_documents_pmid"),
        CheckConstraint(
            "(source_type='pubmed' AND pmid IS NOT NULL AND content_scope='abstract') OR "
            "(source_type='pdf' AND content_scope IN ('extracted_text','full_text'))",
            name="ck_documents_scope",
        ),
        CheckConstraint(
            "(source_type='pdf' AND title_origin IN ('manual','document_metadata','filename')) OR "
            "(source_type='pubmed' AND title_origin IN ('manual','pubmed_metadata'))",
            name="ck_documents_title_origin",
        ),
        CheckConstraint(
            "(content_scope='abstract' AND abstract IS NOT NULL AND btrim(abstract)<>'' "
            "AND text IS NULL) OR (content_scope<>'abstract' AND text IS NOT NULL "
            "AND btrim(text)<>'')",
            name="ck_documents_content",
        ),
        CheckConstraint("jsonb_typeof(authors)='array'", name="ck_documents_authors"),
        CheckConstraint("jsonb_typeof(publication_date)='object'", name="ck_documents_date"),
        CheckConstraint(
            "jsonb_typeof(source_units)='array' AND jsonb_array_length(source_units)>0",
            name="ck_documents_units",
        ),
        CheckConstraint(
            "ingestion_metadata IS NULL OR jsonb_typeof(ingestion_metadata)='object'",
            name="ck_documents_ingestion_metadata",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(Text)
    source_identity: Mapped[str] = mapped_column(
        Text,
        Computed("CASE WHEN source_type='pdf' THEN content_hash ELSE pmid END", persisted=True),
    )
    content_hash: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    content_scope: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    title_origin: Mapped[str] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(JSONB)
    publication_date: Mapped[dict[str, object]] = mapped_column(JSONB)
    journal: Mapped[str | None] = mapped_column(Text)
    doi: Mapped[str | None] = mapped_column(Text)
    pmid: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    ingestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_units: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
    ingestion_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))


class ChunkRecord(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "source_type"],
            ["documents.document_id", "documents.source_type"],
            name="fk_chunks_document_source",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "document_id", "chunking_version", "chunk_index", name="uq_chunks_position"
        ),
        CheckConstraint("chunk_index > 0", name="ck_chunks_index"),
        CheckConstraint("btrim(text) <> ''", name="ck_chunks_text"),
        CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset AND "
            "end_offset - start_offset = char_length(text)",
            name="ck_chunks_span",
        ),
        CheckConstraint(
            "(source_type='pdf' AND location_kind='pdf_page' AND page IS NOT NULL AND page>0) OR "
            "(source_type='pubmed' AND location_kind='abstract' AND page IS NULL)",
            name="ck_chunks_location",
        ),
        CheckConstraint(
            "model_id='intfloat/multilingual-e5-base' AND "
            "model_revision='d128750597153bb5987e10b1c3493a34e5a4502a' AND "
            "tokenizer_revision='d128750597153bb5987e10b1c3493a34e5a4502a' AND "
            "embedding_dimension=768 AND normalized IS TRUE AND "
            "chunking_version='source-unit-v1' AND document_prefix='passage: '",
            name="ck_chunks_model",
        ),
        CheckConstraint(
            "max_tokens>0 AND max_tokens<=512 AND token_count>0 AND token_count<=max_tokens",
            name="ck_chunks_tokens",
        ),
        CheckConstraint("jsonb_typeof(chunking_policy)='object'", name="ck_chunks_policy"),
        CheckConstraint("abs(vector_norm(embedding)-1.0)<=0.0001", name="ck_chunks_norm"),
    )

    chunk_id: Mapped[UUID] = mapped_column(primary_key=True)
    document_id: Mapped[UUID]
    source_type: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    location_kind: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    model_id: Mapped[str] = mapped_column(Text)
    model_revision: Mapped[str] = mapped_column(Text)
    tokenizer_revision: Mapped[str] = mapped_column(Text)
    embedding_dimension: Mapped[int] = mapped_column(Integer)
    normalized: Mapped[bool] = mapped_column(Boolean)
    chunking_version: Mapped[str] = mapped_column(Text)
    document_prefix: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    max_tokens: Mapped[int] = mapped_column(Integer)
    chunking_policy: Mapped[dict[str, object]] = mapped_column(JSONB)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(768))
