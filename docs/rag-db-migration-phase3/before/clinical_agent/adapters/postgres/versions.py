"""Atomic active projection replacement with immutable historical prepared evidence."""

import json
from hashlib import sha256
from uuid import UUID, uuid5

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import (
    ChunkRecord,
    DocumentRecord,
    DocumentVersionRecord,
)
from clinical_agent.adapters.postgres.store import PostgresStore, _read, records_for
from clinical_agent.application.updates import logical_content
from clinical_agent.domain.ingestion import IngestionError, PreparedIngestion, StoreResult


def fingerprint(prepared: PreparedIngestion) -> str:
    prepared = PreparedIngestion.model_validate(prepared)
    data = {
        "document": prepared.source.parsed.document.model_dump(
            mode="json", exclude={"document_id", "source_uri", "ingestion_time", "evidence_chunks"}
        ),
        "units": [u.model_dump(mode="json") for u in prepared.source.parsed.source_units],
        "profile": prepared.chunking.profile.model_dump(mode="json"),
        "policy": prepared.chunking.policy.model_dump(mode="json"),
        "parser": [prepared.source.parser_name, prepared.source.parser_version],
        "chunks": [
            {
                "text": c.evidence.text,
                "location": c.evidence.location.model_dump(),
                "tokens": c.token_count,
            }
            for c in prepared.chunking.chunks
        ],
    }
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def versioned(prepared: PreparedIngestion) -> tuple[PreparedIngestion, UUID]:
    identity = uuid5(prepared.source.parsed.document.document_id, fingerprint(prepared))
    data = prepared.model_dump(mode="json")
    for index, (original, encoded) in enumerate(
        zip(data["chunking"]["chunks"], data["embedded"], strict=True)
    ):
        key = str(uuid5(identity, str(index)))
        original["evidence"]["chunk_id"] = key
        encoded["evidence"]["chunk_id"] = key
    return PreparedIngestion.model_validate(data), identity


class VersionedPostgresStore(PostgresStore):
    def _published(self, session: Session, prepared: PreparedIngestion) -> None:
        """Optional same-transaction source metadata handling."""

    @staticmethod
    def version_id(prepared: PreparedIngestion) -> UUID:
        return uuid5(prepared.source.parsed.document.document_id, fingerprint(prepared))

    def load_version(self, identity: UUID) -> PreparedIngestion | None:
        try:
            with self._session() as session:
                record = session.get(DocumentVersionRecord, identity)
                return PreparedIngestion.model_validate(record.prepared) if record else None
        except IntegrityError:
            raise IngestionError("storage_conflict") from None
        except SQLAlchemyError:
            raise IngestionError("storage_unavailable") from None

    def save(self, prepared: PreparedIngestion) -> StoreResult:
        return self.publish(prepared)

    def publish(self, prepared: PreparedIngestion, *, dry_run: bool = False) -> StoreResult:
        incoming, version_id = versioned(PreparedIngestion.model_validate(prepared))
        document, chunks = records_for(incoming)
        values = {
            c.name: getattr(document, c.name)
            for c in DocumentRecord.__table__.columns
            if c.computed is None
        }
        try:
            with self._session() as session, session.begin():
                if dry_run:
                    existing = session.get(DocumentRecord, document.document_id)
                else:
                    inserted = session.scalar(
                        insert(DocumentRecord)
                        .values(**values)
                        .on_conflict_do_nothing(constraint="uq_documents_source")
                        .returning(DocumentRecord.document_id)
                    )
                    existing = session.scalar(
                        select(DocumentRecord)
                        .where(DocumentRecord.document_id == document.document_id)
                        .with_for_update()
                    )
                    if existing is None:
                        raise IngestionError("storage_conflict")
                    if inserted is not None:
                        session.add_all(chunks)
                        session.add(
                            DocumentVersionRecord(
                                version_id=version_id,
                                document_id=document.document_id,
                                fingerprint=fingerprint(incoming),
                                prepared=incoming.model_dump(mode="json"),
                                is_active=True,
                            )
                        )
                        session.flush()
                        self._published(session, incoming)
                        return StoreResult(
                            status="imported",
                            document_id=document.document_id,
                            chunk_count=len(chunks),
                        )
                old = _read(session, existing) if existing is not None else None
                if old is not None and (
                    old.chunking.profile != incoming.chunking.profile
                    or old.chunking.policy != incoming.chunking.policy
                ):
                    raise IngestionError("storage_conflict")
                status = (
                    "imported"
                    if old is None
                    else "already_present"
                    if fingerprint(old) == fingerprint(incoming)
                    else "metadata_updated"
                    if logical_content(old) == logical_content(incoming)
                    else "updated"
                )
                if (
                    not dry_run
                    and old is not None
                    and status not in {"already_present", "imported"}
                ):
                    if session.get(DocumentVersionRecord, version_id) is not None:
                        raise IngestionError("storage_conflict")
                    old_id = self.version_id(old)
                    if session.get(DocumentVersionRecord, old_id) is None:
                        session.add(
                            DocumentVersionRecord(
                                version_id=old_id,
                                document_id=document.document_id,
                                fingerprint=fingerprint(old),
                                prepared=old.model_dump(mode="json"),
                                is_active=False,
                            )
                        )
                        session.flush()
                    session.execute(
                        update(DocumentVersionRecord)
                        .where(DocumentVersionRecord.document_id == document.document_id)
                        .values(is_active=False)
                    )
                    session.execute(
                        delete(ChunkRecord).where(ChunkRecord.document_id == document.document_id)
                    )
                    session.execute(
                        update(DocumentRecord)
                        .where(DocumentRecord.document_id == document.document_id)
                        .values(**{k: v for k, v in values.items() if k != "document_id"})
                    )
                    session.add_all(chunks)
                    session.add(
                        DocumentVersionRecord(
                            version_id=version_id,
                            document_id=document.document_id,
                            fingerprint=fingerprint(incoming),
                            prepared=incoming.model_dump(mode="json"),
                            is_active=True,
                        )
                    )
                    session.flush()
                if not dry_run:
                    self._published(session, incoming)
                return StoreResult.model_validate(
                    {
                        "status": status,
                        "document_id": document.document_id,
                        "chunk_count": len(chunks),
                    }
                )
        except IntegrityError:
            raise IngestionError("storage_conflict") from None
        except SQLAlchemyError:
            raise IngestionError("storage_unavailable") from None
