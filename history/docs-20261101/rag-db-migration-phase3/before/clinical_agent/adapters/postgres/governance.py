"""Local manual governance, serialized assertions without rewriting source evidence."""

from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import (
    DocumentRecord,
    SourceAliasRecord,
    SourceStateRecord,
    SourceStatusEventRecord,
)
from clinical_agent.domain.governance import (
    AliasClaim,
    GovernanceState,
    Namespace,
    StatusChange,
    normalize_alias,
)


def _lock(session: Session, key: str) -> None:
    number = int.from_bytes(sha256(key.encode()).digest()[:8], "big", signed=True)
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": number})


def _state(record: SourceStateRecord | None) -> dict[str, object]:
    return GovernanceState.model_validate(
        dict(status=record.status, event_id=record.event_id, evidence=record.evidence)
        if record
        else {}
    ).model_dump(mode="json")


def _resolve(session: Session, namespace: str, value: str) -> dict[str, object]:
    records = list(
        session.scalars(
            select(SourceAliasRecord)
            .where(SourceAliasRecord.namespace == namespace, SourceAliasRecord.value == value)
            .order_by(SourceAliasRecord.document_id)
        )
    )
    native_filter = (
        DocumentRecord.pmid == value
        if namespace == "pmid"
        else (DocumentRecord.source_type == "pdf") & (DocumentRecord.content_hash == value)
        if namespace == "pdf_sha256"
        else func.lower(
            func.regexp_replace(
                DocumentRecord.doi, r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", "i"
            )
        )
        == value
    )
    identities = {r.document_id for r in records} | set(
        session.scalars(select(DocumentRecord.document_id).where(native_filter))
    )
    return {
        "namespace": namespace,
        "value": value,
        "status": "unmapped"
        if not identities
        else "resolved"
        if len(identities) == 1
        else "conflicted",
        "document_ids": sorted(str(i) for i in identities),
    }


class SourceGovernance:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def claim(self, request: AliasClaim) -> dict[str, object]:
        request = AliasClaim.model_validate(request)
        try:
            with Session(self.engine) as session, session.begin():
                _lock(session, "alias:" + request.namespace + ":" + request.value)
                document = session.scalar(
                    select(DocumentRecord)
                    .where(DocumentRecord.document_id == request.document_id)
                    .with_for_update()
                )
                if document is None:
                    raise ValueError("document_not_found")
                native = (
                    document.pmid
                    if request.namespace == "pmid" and document.source_type == "pubmed"
                    else document.content_hash
                    if request.namespace == "pdf_sha256" and document.source_type == "pdf"
                    else None
                )
                if native is not None and native != request.value:
                    raise ValueError("native_identity_conflict")
                key = (request.namespace, request.value, request.document_id)
                if session.get(SourceAliasRecord, key) is None:
                    session.add(
                        SourceAliasRecord(
                            namespace=request.namespace,
                            value=request.value,
                            document_id=request.document_id,
                            evidence=request.evidence.model_dump(mode="json"),
                        )
                    )
                    session.flush()
                return _resolve(session, request.namespace, request.value)
        except SQLAlchemyError:
            raise ValueError("governance_storage_failed") from None

    def resolve(self, namespace: Namespace, value: str) -> dict[str, object]:
        value = normalize_alias(namespace, value)
        try:
            with Session(self.engine) as session:
                return _resolve(session, namespace, value)
        except SQLAlchemyError:
            raise ValueError("governance_storage_failed") from None

    def change_status(self, request: StatusChange) -> dict[str, object]:
        request = StatusChange.model_validate(request)
        data = request.model_dump(mode="json")
        try:
            with Session(self.engine) as session, session.begin():
                # Lock event ID first as it can otherwise be reused across two documents.
                _lock(session, "status-event:" + str(request.event_id))
                document = session.scalar(
                    select(DocumentRecord)
                    .where(DocumentRecord.document_id == request.document_id)
                    .with_for_update()
                )
                if document is None:
                    raise ValueError("document_not_found")
                prior = session.get(SourceStatusEventRecord, request.event_id)
                state = session.get(SourceStateRecord, request.document_id)
                if prior is not None:
                    if prior.request != data:
                        raise ValueError("event_conflict")
                    return _state(state)
                if (state.event_id if state else None) != request.expected_event_id:
                    raise ValueError("stale_status")
                session.add(
                    SourceStatusEventRecord(
                        event_id=request.event_id, document_id=request.document_id, request=data
                    )
                )
                session.flush()
                if state is None:
                    state = SourceStateRecord(document_id=request.document_id)
                    session.add(state)
                state.event_id, state.status = request.event_id, request.status
                state.evidence = request.evidence.model_dump(mode="json")
                session.flush()
                return _state(state)
        except SQLAlchemyError:
            raise ValueError("governance_storage_failed") from None

    def inspect(self, document_id: UUID) -> dict[str, object]:
        try:
            with self.engine.connect() as connection:
                connection = connection.execution_options(isolation_level="REPEATABLE READ")
                with connection.begin(), Session(bind=connection) as session:
                    if session.get(DocumentRecord, document_id) is None:
                        raise ValueError("document_not_found")
                    return {
                        "document_id": str(document_id),
                        "state": _state(session.get(SourceStateRecord, document_id)),
                        "aliases": [
                            {"namespace": r.namespace, "value": r.value, "evidence": r.evidence}
                            for r in session.scalars(
                                select(SourceAliasRecord)
                                .where(SourceAliasRecord.document_id == document_id)
                                .order_by(SourceAliasRecord.namespace, SourceAliasRecord.value)
                            )
                        ],
                        "events": [
                            {"request": r.request, "recorded_at": r.recorded_at.isoformat()}
                            for r in session.scalars(
                                select(SourceStatusEventRecord)
                                .where(SourceStatusEventRecord.document_id == document_id)
                                .order_by(
                                    SourceStatusEventRecord.recorded_at,
                                    SourceStatusEventRecord.event_id,
                                )
                            )
                        ],
                    }
        except SQLAlchemyError:
            raise ValueError("governance_storage_failed") from None

    def statuses_for_pmids(self, pmids: list[str]) -> dict[str, GovernanceState]:
        """Exact native PMID only; aliases never propagate source status implicitly."""
        if not pmids:
            return {}
        try:
            with Session(self.engine) as session:
                rows = session.execute(
                    select(DocumentRecord.pmid, SourceStateRecord)
                    .join(
                        SourceStateRecord,
                        SourceStateRecord.document_id == DocumentRecord.document_id,
                    )
                    .where(DocumentRecord.source_type == "pubmed", DocumentRecord.pmid.in_(pmids))
                )
                return {
                    pmid: GovernanceState.model_validate(_state(record))
                    for pmid, record in rows
                    if pmid is not None
                }
        except SQLAlchemyError:
            raise ValueError("governance_storage_failed") from None
