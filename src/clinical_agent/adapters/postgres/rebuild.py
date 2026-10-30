"""Explicit isolated staging and all-document atomic rebuild activation."""

import json
from collections.abc import Callable
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid5

from sqlalchemy import Engine, delete, select, text, update
from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import (
    ChunkRecord,
    DocumentRecord,
    DocumentVersionRecord,
    RebuildRunRecord,
)
from clinical_agent.adapters.postgres.store import _read, records_for
from clinical_agent.adapters.postgres.versions import VersionedPostgresStore, fingerprint
from clinical_agent.application.ingestion import Embedder
from clinical_agent.domain.chunking import chunk_source
from clinical_agent.domain.ingestion import PreparedIngestion, chunk_id_for
from clinical_agent.domain.maintenance import RebuildRequest


def signature(values: list[PreparedIngestion]) -> str:
    return sha256(
        json.dumps(
            sorted((str(v.source.parsed.document.document_id), fingerprint(v)) for v in values)
        ).encode()
    ).hexdigest()


def _sources(session: Session) -> list[PreparedIngestion]:
    documents = list(
        session.scalars(select(DocumentRecord).order_by(DocumentRecord.document_id).limit(101))
    )
    if len(documents) > 100:
        raise ValueError("rebuild_document_limit")
    return [_read(session, doc) for doc in documents]


def _summary(record: RebuildRunRecord) -> dict[str, object]:
    return {
        "run_id": str(record.run_id),
        "status": record.status,
        "evaluation_status": record.evaluation_status,
        "source_signature": record.source_signature,
        "documents": len(cast(list[object], record.payload["prepared"])),
    }


class KnowledgeRebuilder:
    def __init__(self, engine: Engine, embedder: Embedder | None = None):
        self.engine, self.embedder = engine, embedder

    def plan(self) -> dict[str, object]:
        with (
            self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
            conn.begin(),
            Session(bind=conn) as session,
        ):
            sources = _sources(session)
            return {
                "status": "dry_run",
                "documents": len(sources),
                "source_signature": signature(sources),
                "supported_model": "intfloat/multilingual-e5-base",
                "dimension": 768,
            }

    def stage(
        self,
        request: RebuildRequest,
        *,
        evaluate: Callable[[list[PreparedIngestion]], str] | None = None,
    ) -> dict[str, object]:
        request = RebuildRequest.model_validate(request)
        with Session(self.engine) as session:
            existing = session.get(RebuildRunRecord, request.run_id)
            if existing is not None:
                if existing.payload["request"] != request.model_dump(mode="json"):
                    raise ValueError("rebuild_scope_conflict")
                return _summary(existing)
        if self.embedder is None:
            raise ValueError("embedder_required")
        profile = self.embedder.tokenizer_profile
        if (
            profile.model_id != "intfloat/multilingual-e5-base"
            or profile.model_revision != "d128750597153bb5987e10b1c3493a34e5a4502a"
            or profile.tokenizer_revision != profile.model_revision
            or profile.document_prefix != "passage: "
            or profile.model_max_tokens != 512
        ):
            raise ValueError("unsupported_rebuild_model")
        with (
            self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
            conn.begin(),
            Session(bind=conn) as session,
        ):
            sources = _sources(session)
        if not sources:
            raise ValueError("empty_knowledge_base")
        prepared = []
        for old in sources:
            parsed = old.source.parsed

            def chunk_identity(index: int, identity: UUID = parsed.document.document_id) -> UUID:
                return uuid5(
                    request.run_id, str(chunk_id_for(identity, profile, request.policy, index))
                )

            chunks = chunk_source(
                parsed,
                tokenizer=self.embedder.count_tokens,
                profile=profile,
                policy=request.policy,
                chunk_id_factory=chunk_identity,
            )
            new = PreparedIngestion(
                source=old.source, chunking=chunks, embedded=self.embedder.embed_chunks(chunks)
            )
            prepared.append(new)
        evaluation = "not_run"
        if evaluate is not None:
            try:
                result = evaluate(prepared)
                evaluation = result if result in {"passed", "not_accepted", "failed"} else "failed"
            except Exception:
                evaluation = "failed"
        record = RebuildRunRecord(
            run_id=request.run_id,
            status="staged",
            source_signature=signature(sources),
            payload={
                "request": request.model_dump(mode="json"),
                "prepared": [v.model_dump(mode="json") for v in prepared],
            },
            evaluation_status=evaluation,
        )
        with Session(self.engine) as session, session.begin():
            session.add(record)
            session.flush()
            return _summary(record)

    def activate(self, run_id: UUID) -> dict[str, object]:
        with Session(self.engine) as session, session.begin():
            # Blocks writers only for the final switch, never during encoding/evaluation.
            session.execute(text("LOCK TABLE documents IN SHARE ROW EXCLUSIVE MODE"))
            record = session.scalar(
                select(RebuildRunRecord).where(RebuildRunRecord.run_id == run_id).with_for_update()
            )
            if record is None:
                raise ValueError("rebuild_not_found")
            if record.status == "activated":
                return _summary(record)
            if record.evaluation_status != "passed":
                raise ValueError("evaluation_required")
            old_sources = _sources(session)
            if signature(old_sources) != record.source_signature:
                raise ValueError("source_changed")
            incoming = [
                PreparedIngestion.model_validate(v)
                for v in cast(list[object], record.payload["prepared"])
            ]
            if {p.source.parsed.document.document_id for p in incoming} != {
                p.source.parsed.document.document_id for p in old_sources
            }:
                raise ValueError("rebuild_set_mismatch")
            for old, new in zip(old_sources, incoming, strict=True):
                if old.source != new.source:
                    raise ValueError("rebuild_source_mismatch")
                identity = old.source.parsed.document.document_id
                old_id = VersionedPostgresStore.version_id(old)
                # A rebuild uses a run-specific version, preserving prior evidence IDs.
                if session.get(DocumentVersionRecord, old_id) is None and not session.scalar(
                    select(DocumentVersionRecord.version_id).where(
                        DocumentVersionRecord.document_id == identity,
                        DocumentVersionRecord.is_active,
                    )
                ):
                    session.add(
                        DocumentVersionRecord(
                            version_id=old_id,
                            document_id=identity,
                            fingerprint=fingerprint(old),
                            prepared=old.model_dump(mode="json"),
                            is_active=False,
                        )
                    )
                    session.flush()
                session.execute(
                    update(DocumentVersionRecord)
                    .where(DocumentVersionRecord.document_id == identity)
                    .values(is_active=False)
                )
                document, chunks = records_for(new)
                values = {
                    c.name: getattr(document, c.name)
                    for c in DocumentRecord.__table__.columns
                    if c.computed is None and c.name != "document_id"
                }
                session.execute(delete(ChunkRecord).where(ChunkRecord.document_id == identity))
                session.execute(
                    update(DocumentRecord)
                    .where(DocumentRecord.document_id == identity)
                    .values(**values)
                )
                session.add_all(chunks)
                session.add(
                    DocumentVersionRecord(
                        version_id=uuid5(run_id, str(identity)),
                        document_id=identity,
                        fingerprint=fingerprint(new),
                        prepared=new.model_dump(mode="json"),
                        is_active=True,
                    )
                )
                session.flush()
            record.status = "activated"
            session.flush()
            return _summary(record)

    def evaluate(self, prepared: list[PreparedIngestion]) -> str:
        """Real isolated PG canaries, not medical quality or an LLM self-review."""
        import re
        from uuid import uuid4

        from clinical_agent.adapters.postgres.models import Base
        from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
        from clinical_agent.adapters.postgres.store import PostgresStore
        from clinical_agent.domain.embedding import QueryEmbedding
        from clinical_agent.domain.retrieval import RetrievalOptions

        schema = "rebuild_check_" + uuid4().hex
        created = False
        try:
            with self.engine.begin() as conn:
                conn.execute(text(f"CREATE SCHEMA {schema}"))
                created = True
            isolated = self.engine.execution_options(schema_translate_map={None: schema})
            Base.metadata.create_all(isolated)
            store = PostgresStore(isolated)
            retriever = PostgresRetriever(isolated)
            for value in prepared:
                store.save(value)
                evidence = value.embedded[0]
                assert evidence.evidence.embedding_info is not None
                query = QueryEmbedding(
                    vector=evidence.vector, embedding_info=evidence.evidence.embedding_info
                )
                words = re.findall(r"[A-Za-z][A-Za-z0-9_]*", evidence.evidence.text)
                terms = value.source.parsed.document.pmid or (words[0] if words else "evidence")
                for mode in ("vector", "keyword", "hybrid"):
                    result = retriever.search_hybrid(
                        terms,
                        query,
                        RetrievalOptions(
                            mode=mode, document_ids=[value.source.parsed.document.document_id]
                        ),
                        timeout_seconds=10.0,
                    )
                    if (
                        mode != "keyword" or words or value.source.parsed.document.pmid
                    ) and not result.hits:
                        return "not_accepted"
                    if any(
                        h.document.document_id != value.source.parsed.document.document_id
                        for h in result.hits
                    ):
                        return "not_accepted"
                    for hit in result.hits:
                        value.source.parsed.validate_chunk(hit.chunk)
            return "passed"
        except Exception:
            return "failed"
        finally:
            if created:
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
