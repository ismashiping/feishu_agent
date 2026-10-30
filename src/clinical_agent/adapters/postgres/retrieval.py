"""Snapshot-consistent vector/FTS candidates, rank fusion and validated evidence hydration."""

import math
import re
from time import monotonic
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Engine, Integer, case, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord, SourceStateRecord
from clinical_agent.adapters.postgres.store import prepared_from_records
from clinical_agent.domain.embedding import QueryEmbedding
from clinical_agent.domain.governance import BLOCKED_STATUSES, GovernanceState
from clinical_agent.domain.hybrid import keyword_text, rank_candidates
from clinical_agent.domain.ingestion import IngestionError
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalError,
    RetrievalOptions,
    RetrievalResult,
    retrieval_embedding_info,
    validate_query_embedding,
)


class PostgresRetriever:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def search(self, query: QueryEmbedding, options: RetrievalOptions) -> RetrievalResult:
        return self.search_hybrid("", query, options, timeout_seconds=30.0)

    def search_hybrid(
        self,
        question: str,
        query: QueryEmbedding | None,
        options: RetrievalOptions,
        *,
        timeout_seconds: float,
    ) -> RetrievalResult:
        options = RetrievalOptions.model_validate(options)
        if options.mode != "keyword":
            if query is None:
                raise RetrievalError("retrieval_model_mismatch")
            query = validate_query_embedding(query)
        if options.mode != "vector":
            question = keyword_text(question, options)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise RetrievalError("retrieval_timeout")
        deadline = monotonic() + min(timeout_seconds, 30.0)

        def check(session: Session) -> None:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise RetrievalError("retrieval_timeout")
            # Only a locally computed integer enters this SET statement, never user SQL.
            session.connection().exec_driver_sql(
                f"SET LOCAL statement_timeout = {max(1, min(10000, int(remaining * 1000)))}"
            )

        try:
            with self._engine.connect() as connection:
                connection = connection.execution_options(isolation_level="REPEATABLE READ")
                with connection.begin():
                    connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                    with Session(bind=connection) as session:
                        channels: dict[str, list[tuple[UUID, UUID, float]]] = {}
                        for channel in (
                            ["vector"]
                            if options.mode == "vector"
                            else ["keyword"]
                            if options.mode == "keyword"
                            else ["keyword", "vector"]
                        ):
                            check(session)
                            channels[channel] = self._candidates(
                                session, channel, question, query, options
                            )
                        # Hydrate only the final output, not up to 200 candidate source graphs.
                        if options.mode == "hybrid":
                            identities: dict[UUID, UUID] = {}
                            for candidates in channels.values():
                                for document_id, chunk_id, _ in candidates:
                                    if (
                                        chunk_id in identities
                                        and identities[chunk_id] != document_id
                                    ):
                                        raise RetrievalError("retrieval_corrupt")
                                    identities[chunk_id] = document_id
                            ranking = rank_candidates(
                                [r[1] for r in channels["keyword"]],
                                [r[1] for r in channels["vector"]],
                                options,
                            )
                            rows = [
                                (identities[identity], identity, 0.0)
                                for identity, _, _, _ in ranking
                            ]
                        else:
                            rows = channels[options.mode][: options.top_k]
                        check(session)
                        hydrated = self._hydrate(session, rows)
                        check(session)
                        if options.mode == "hybrid":
                            lookup = {hit.chunk.chunk_id: hit for hit in hydrated}
                            # Retain the original ranks, including non-final candidate positions.
                            hits: list[EvidenceHit] = []
                            for identity, keyword_rank, vector_rank, score in ranking:
                                data = lookup[identity].model_dump()
                                data.update(
                                    score=score,
                                    score_type="rrf",
                                    keyword_rank=keyword_rank,
                                    vector_rank=vector_rank,
                                    fusion_score=score,
                                    rank=len(hits) + 1,
                                )
                                hits.append(EvidenceHit.model_validate(data))
                        else:
                            hits = []
                            for rank, hit in enumerate(hydrated, 1):
                                data = hit.model_dump()
                                data.update(rank=rank)
                                if options.mode == "keyword":
                                    data.update(score_type="fts_rank", keyword_rank=rank)
                                else:
                                    data.update(vector_rank=rank)
                                hits.append(EvidenceHit.model_validate(data))
                        warnings = ["source_governance_local_policy"]
                        if options.mode != "vector":
                            warnings.append("keyword_simple_ascii")
                        if options.date_from is not None:
                            warnings.append("local_dates_require_day_precision")
                        return RetrievalResult.model_validate(
                            dict(
                                options=options,
                                embedding_info=retrieval_embedding_info(),
                                hits=hits,
                                channel_status={
                                    "keyword": "not_requested"
                                    if options.mode == "vector"
                                    else "ok",
                                    "vector": "not_requested"
                                    if options.mode == "keyword"
                                    else "ok",
                                },
                                strategy_version={
                                    "vector": "vector-v1",
                                    "keyword": "fts-simple-v1",
                                    "hybrid": "rrf-v1",
                                }[options.mode],
                                warnings=warnings,
                            )
                        )
        except (IngestionError, ValidationError, StopIteration):
            raise RetrievalError("retrieval_corrupt") from None
        except SQLAlchemyError as error:
            if getattr(getattr(error, "orig", None), "sqlstate", None) == "57014":
                raise RetrievalError("retrieval_timeout") from None
            raise RetrievalError("retrieval_failed") from None

    def _candidates(
        self,
        session: Session,
        channel: str,
        question: str,
        query: QueryEmbedding | None,
        options: RetrievalOptions,
    ) -> list[tuple[UUID, UUID, float]]:
        info = retrieval_embedding_info()
        filters = [
            ~select(SourceStateRecord.document_id)
            .where(
                SourceStateRecord.document_id == DocumentRecord.document_id,
                SourceStateRecord.status.in_(BLOCKED_STATUSES),
            )
            .exists(),
            DocumentRecord.source_type.in_(options.source_types),
            DocumentRecord.content_scope.in_(options.content_scopes),
            ChunkRecord.model_id == info.model_id,
            ChunkRecord.model_revision == info.model_revision,
            ChunkRecord.tokenizer_revision == info.tokenizer_revision,
            ChunkRecord.embedding_dimension == info.dimension,
            ChunkRecord.normalized == info.normalized,
            ChunkRecord.chunking_version == info.chunking_version,
            ChunkRecord.document_prefix == "passage: ",
        ]
        if options.document_ids is not None:
            filters.append(DocumentRecord.document_id.in_(options.document_ids))
        if options.date_from is not None:
            publication = DocumentRecord.publication_date
            day = func.make_date(
                publication["year"].astext.cast(Integer),
                publication["month"].astext.cast(Integer),
                publication["day"].astext.cast(Integer),
            )
            filters.extend(
                [
                    publication["precision"].astext == "day",
                    day >= options.date_from,
                    day <= options.date_to,
                ]
            )
        score: ColumnElement[float]
        matches: ColumnElement[bool]
        if channel == "vector":
            assert query is not None
            distance = ChunkRecord.embedding.cosine_distance(query.vector)
            score = func.greatest(-1.0, func.least(1.0, 1.0 - distance))
            filters.append(score >= options.min_similarity)
            ordering = [distance, ChunkRecord.chunk_id]
        else:
            expression = func.plainto_tsquery("simple", question)
            matches = ChunkRecord.search_vector.op("@@")(expression)
            exact = (
                DocumentRecord.pmid == question
                if re.fullmatch(r"[1-9][0-9]*", question)
                else func.lower(DocumentRecord.doi) == question.lower()
                if re.fullmatch(r"10\.[0-9]{4,9}/\S+", question, re.IGNORECASE)
                else None
            )
            score = func.ts_rank_cd(ChunkRecord.search_vector, expression, 32)
            if exact is not None:
                matches = or_(matches, exact)
                score = case((exact, 1.0), else_=score)
            filters.append(matches)
            ordering = [score.desc(), ChunkRecord.chunk_id]
        limit = options.top_k if options.mode == "vector" else options.candidate_limit
        statement = (
            select(
                ChunkRecord.document_id,
                ChunkRecord.chunk_id,
                distance if channel == "vector" else score,
            )
            .join(DocumentRecord, DocumentRecord.document_id == ChunkRecord.document_id)
            .where(*filters)
            .order_by(*ordering)
            .limit(limit)
        )
        rows = []
        for document_id, chunk_id, raw in session.execute(statement):
            if (
                not isinstance(raw, float)
                or not math.isfinite(raw)
                or not (0 - 1e-6 <= raw <= 2 + 1e-6 if channel == "vector" else 0 <= raw <= 1)
            ):
                raise RetrievalError("retrieval_corrupt")
            value = 1.0 - raw if channel == "vector" else raw
            rows.append((document_id, chunk_id, max(-1.0, min(1.0, value))))
        return rows

    def _hydrate(
        self, session: Session, candidates: list[tuple[UUID, UUID, float]]
    ) -> list[EvidenceHit]:
        if not candidates:
            return []
        document_ids = {row[0] for row in candidates}
        document_rows = list(
            session.execute(
                select(DocumentRecord, SourceStateRecord)
                .outerjoin(
                    SourceStateRecord, SourceStateRecord.document_id == DocumentRecord.document_id
                )
                .where(DocumentRecord.document_id.in_(document_ids))
            )
        )
        documents = [document for document, _ in document_rows]
        states = {
            document.document_id: state for document, state in document_rows if state is not None
        }
        rows = list(
            session.scalars(
                select(ChunkRecord)
                .where(ChunkRecord.document_id.in_(document_ids))
                .order_by(ChunkRecord.document_id, ChunkRecord.chunk_index)
                .limit(len(document_ids) * 128 + 1)
            )
        )
        if len(rows) > len(document_ids) * 128 or len(documents) != len(document_ids):
            raise RetrievalError("retrieval_corrupt")
        prepared = {
            document.document_id: prepared_from_records(
                document, [row for row in rows if row.document_id == document.document_id]
            )
            for document in documents
        }
        hits: list[EvidenceHit] = []
        for document_id, chunk_id, score in candidates:
            source = prepared[document_id]
            selected = next(
                item.evidence for item in source.embedded if item.evidence.chunk_id == chunk_id
            )
            summary = DocumentSummary.from_document(source.source.parsed.document)
            if document_id in states:
                state = states[document_id]
                summary.governance = GovernanceState.model_validate(
                    dict(status=state.status, event_id=state.event_id, evidence=state.evidence)
                )
            hits.append(
                EvidenceHit(
                    chunk=selected,
                    document=summary,
                    score=score,
                    rank=len(hits) + 1,
                )
            )
        return hits
