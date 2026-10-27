"""Detached business mapping and one-document atomic writes with source-unique arbitration."""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord
from clinical_agent.domain.chunking import ChunkingResult, TokenizedChunk
from clinical_agent.domain.embedding import EmbeddedChunk
from clinical_agent.domain.ingestion import (
    IngestionError,
    IngestionMetadata,
    ParsedSource,
    PreparedIngestion,
    StoreResult,
    equivalent_content,
)
from clinical_agent.domain.models import (
    EmbeddingInfo,
    EvidenceChunk,
    EvidenceLocation,
    LiteratureDocument,
    ParsedPdf,
    ParsedPubmedArticle,
    SourceMetadata,
)


def records_for(prepared: PreparedIngestion) -> tuple[DocumentRecord, list[ChunkRecord]]:
    prepared = PreparedIngestion.model_validate(prepared)
    source, profile, policy = prepared.source, prepared.chunking.profile, prepared.chunking.policy
    document = source.parsed.document
    data = document.model_dump(mode="json", exclude={"evidence_chunks"})
    data["ingestion_time"] = document.ingestion_time
    data["source_units"] = [unit.model_dump(mode="json") for unit in source.parsed.source_units]
    data["ingestion_metadata"] = IngestionMetadata(
        parser_name=source.parser_name,
        parser_version=source.parser_version,
        profile=profile,
        policy=policy,
    ).model_dump(mode="json")
    record = DocumentRecord(**data)
    rows = []
    for index, (original, encoded) in enumerate(
        zip(prepared.chunking.chunks, prepared.embedded, strict=True), 1
    ):
        evidence = encoded.evidence
        info = evidence.embedding_info
        if info is None:
            raise IngestionError("storage_corrupt")
        location = evidence.location
        rows.append(
            ChunkRecord(
                chunk_id=evidence.chunk_id,
                document_id=document.document_id,
                source_type=document.source_type,
                chunk_index=index,
                text=evidence.text,
                location_kind=location.kind,
                page=location.page,
                section=location.section,
                start_offset=location.start,
                end_offset=location.end,
                model_id=info.model_id,
                model_revision=info.model_revision,
                tokenizer_revision=info.tokenizer_revision,
                embedding_dimension=info.dimension,
                normalized=info.normalized,
                chunking_version=info.chunking_version,
                document_prefix=profile.document_prefix,
                token_count=original.token_count,
                max_tokens=policy.max_tokens,
                chunking_policy=policy.model_dump(mode="json"),
                embedding=encoded.vector.copy(),
            )
        )
    return record, rows


def prepared_from_records(document: DocumentRecord, rows: list[ChunkRecord]) -> PreparedIngestion:
    try:
        metadata = IngestionMetadata.model_validate(document.ingestion_metadata)
        data = {
            name: getattr(document, name)
            for name in LiteratureDocument.model_fields
            if name != "evidence_chunks"
        }
        doc = LiteratureDocument.model_validate({**data, "evidence_chunks": []})
        parsed: ParsedPdf | ParsedPubmedArticle
        if doc.source_type == "pdf":
            parsed = ParsedPdf.model_validate(
                {
                    "document": doc,
                    "source_units": document.source_units,
                    "page_count": len(document.source_units),
                    "parser_name": metadata.parser_name,
                    "parser_version": metadata.parser_version,
                }
            )
        else:
            parsed = ParsedPubmedArticle.model_validate(
                {"document": doc, "source_units": document.source_units}
            )
        source = ParsedSource(
            parsed=parsed, parser_name=metadata.parser_name, parser_version=metadata.parser_version
        )
        provenance = SourceMetadata.model_validate(
            doc.model_dump(include=set(SourceMetadata.model_fields))
        )
        originals, embedded = [], []
        for index, row in enumerate(rows, 1):
            if (
                row.chunk_index != index
                or row.document_id != doc.document_id
                or row.source_type != doc.source_type
                or row.chunking_policy != metadata.policy.model_dump()
                or row.document_prefix != metadata.profile.document_prefix
                or row.max_tokens != metadata.policy.max_tokens
            ):
                raise ValueError("Stored chunk metadata does not match its document")
            info = EmbeddingInfo(
                model_id=row.model_id,
                model_revision=row.model_revision,
                tokenizer_revision=row.tokenizer_revision,
                dimension=row.embedding_dimension,
                normalized=row.normalized,
                chunking_version=row.chunking_version,
            )
            evidence = EvidenceChunk(
                chunk_id=row.chunk_id,
                document_id=doc.document_id,
                text=row.text,
                location=EvidenceLocation.model_validate(
                    {
                        "kind": row.location_kind,
                        "page": row.page,
                        "section": row.section,
                        "start": row.start_offset,
                        "end": row.end_offset,
                    }
                ),
                embedding_info=info,
                source_metadata=provenance,
            )
            embedded.append(EmbeddedChunk(evidence=evidence, vector=row.embedding))
            originals.append(
                TokenizedChunk(
                    token_count=row.token_count,
                    evidence=EvidenceChunk.model_validate(
                        {**evidence.model_dump(), "embedding_info": None}
                    ),
                )
            )
        return PreparedIngestion(
            source=source,
            chunking=ChunkingResult(
                profile=metadata.profile, policy=metadata.policy, chunks=originals
            ),
            embedded=embedded,
        )
    except (ValueError, TypeError, AttributeError):
        raise IngestionError("storage_corrupt") from None


def _read(session: Session, document: DocumentRecord) -> PreparedIngestion:
    rows = list(
        session.scalars(
            select(ChunkRecord)
            .where(ChunkRecord.document_id == document.document_id)
            .order_by(ChunkRecord.chunk_index)
        )
    )
    return prepared_from_records(document, rows)


class PostgresStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with self._engine.connect() as connection:
            connection = connection.execution_options(isolation_level="READ COMMITTED")
            with Session(bind=connection) as session:
                yield session

    def load(self, document_id: UUID) -> PreparedIngestion | None:
        try:
            with self._session() as session:
                document = session.get(DocumentRecord, document_id)
                return None if document is None else _read(session, document)
        except SQLAlchemyError:
            raise IngestionError("storage_unavailable") from None

    def save(self, prepared: PreparedIngestion) -> StoreResult:
        prepared = PreparedIngestion.model_validate(prepared)
        document, chunks = records_for(prepared)
        values = {
            column.name: getattr(document, column.name)
            for column in DocumentRecord.__table__.columns
            if column.computed is None
        }
        identity = document.content_hash if document.source_type == "pdf" else document.pmid
        try:
            with self._session() as session, session.begin():
                inserted = session.scalar(
                    insert(DocumentRecord)
                    .values(**values)
                    .on_conflict_do_nothing(constraint="uq_documents_source")
                    .returning(DocumentRecord.document_id)
                )
                if inserted is not None:
                    session.add_all(chunks)
                    session.flush()
                    result = StoreResult(
                        status="imported", document_id=inserted, chunk_count=len(chunks)
                    )
                else:
                    existing = session.scalar(
                        select(DocumentRecord)
                        .where(
                            DocumentRecord.source_type == document.source_type,
                            DocumentRecord.source_identity == identity,
                        )
                        .with_for_update()
                    )
                    if existing is None:
                        raise IngestionError("storage_conflict")
                    stored = _read(session, existing)
                    status = (
                        "needs_update"
                        if stored.source.parsed.document.content_hash != document.content_hash
                        else "already_present"
                        if equivalent_content(stored, prepared)
                        else "conflict"
                    )
                    result = StoreResult.model_validate(
                        {
                            "status": status,
                            "document_id": existing.document_id,
                            "chunk_count": len(stored.embedded),
                        }
                    )
            return result
        except IntegrityError:
            raise IngestionError("storage_conflict") from None
        except SQLAlchemyError:
            raise IngestionError("storage_unavailable") from None
