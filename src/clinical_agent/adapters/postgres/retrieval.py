"""Exact pgvector retrieval with bounded, snapshot-consistent evidence hydration."""

import math

from pydantic import ValidationError
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord
from clinical_agent.adapters.postgres.store import prepared_from_records
from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.ingestion import IngestionError
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalError,
    RetrievalOptions,
    RetrievalResult,
    validate_query_embedding,
)


class PostgresRetriever:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def search(self, query: QueryEmbedding, options: RetrievalOptions) -> RetrievalResult:
        query = validate_query_embedding(query)
        options = RetrievalOptions.model_validate(options)
        info = query.embedding_info
        distance = ChunkRecord.embedding.cosine_distance(query.vector).label("distance")
        # Filter the same displayed score, avoiding cancellation in 1 - min_similarity.
        similarity = func.greatest(-1.0, func.least(1.0, 1.0 - distance))
        statement = (
            select(ChunkRecord.document_id, ChunkRecord.chunk_id, distance)
            .join(DocumentRecord, DocumentRecord.document_id == ChunkRecord.document_id)
            .where(
                DocumentRecord.source_type.in_(options.source_types),
                DocumentRecord.content_scope.in_(options.content_scopes),
                ChunkRecord.model_id == info.model_id,
                ChunkRecord.model_revision == info.model_revision,
                ChunkRecord.tokenizer_revision == info.tokenizer_revision,
                ChunkRecord.embedding_dimension == info.dimension,
                ChunkRecord.normalized == info.normalized,
                ChunkRecord.chunking_version == info.chunking_version,
                ChunkRecord.document_prefix == "passage: ",
                similarity >= options.min_similarity,
            )
            .order_by(distance, ChunkRecord.chunk_id)
            .limit(options.top_k)
        )
        if options.document_ids is not None:
            statement = statement.where(DocumentRecord.document_id.in_(options.document_ids))
        try:
            with self._engine.connect() as connection:
                connection = connection.execution_options(isolation_level="REPEATABLE READ")
                with connection.begin():
                    connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                    with Session(bind=connection) as session:
                        candidates = list(session.execute(statement))
                        if not candidates:
                            return RetrievalResult(hits=[], options=options, embedding_info=info)
                        document_ids = {item[0] for item in candidates}
                        documents = list(
                            session.scalars(
                                select(DocumentRecord).where(
                                    DocumentRecord.document_id.in_(document_ids)
                                )
                            )
                        )
                        rows = list(
                            session.scalars(
                                select(ChunkRecord)
                                .where(ChunkRecord.document_id.in_(document_ids))
                                .order_by(ChunkRecord.document_id, ChunkRecord.chunk_index)
                                .limit(len(document_ids) * 128 + 1)
                            )
                        )
                        if len(rows) > len(document_ids) * 128 or len(documents) != len(
                            document_ids
                        ):
                            raise RetrievalError("retrieval_corrupt")
                        prepared = {
                            document.document_id: prepared_from_records(
                                document,
                                [row for row in rows if row.document_id == document.document_id],
                            )
                            for document in documents
                        }
                        hits = []
                        for rank, (document_id, chunk_id, raw_distance) in enumerate(candidates, 1):
                            if (
                                not isinstance(raw_distance, float)
                                or not math.isfinite(raw_distance)
                                or not -1e-6 <= raw_distance <= 2.0 + 1e-6
                            ):
                                raise RetrievalError("retrieval_corrupt")
                            source = prepared[document_id]
                            selected = next(
                                (
                                    item.evidence
                                    for item in source.embedded
                                    if item.evidence.chunk_id == chunk_id
                                ),
                                None,
                            )
                            if selected is None:
                                raise RetrievalError("retrieval_corrupt")
                            hits.append(
                                EvidenceHit(
                                    chunk=selected,
                                    document=DocumentSummary.from_document(
                                        source.source.parsed.document
                                    ),
                                    score=max(-1.0, min(1.0, 1.0 - raw_distance)),
                                    rank=rank,
                                )
                            )
                        return RetrievalResult(hits=hits, options=options, embedding_info=info)
        except (IngestionError, ValidationError):
            raise RetrievalError("retrieval_corrupt") from None
        except SQLAlchemyError:
            raise RetrievalError("retrieval_failed") from None
