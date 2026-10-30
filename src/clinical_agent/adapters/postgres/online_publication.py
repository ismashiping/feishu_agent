"""Official frozen metadata governance committed with its document publication."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from clinical_agent.adapters.postgres.models import SourceStateRecord, SourceStatusEventRecord
from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
from clinical_agent.domain.governance import (
    BLOCKED_STATUSES,
    EvidenceBasis,
    StatusChange,
    pubmed_status,
)
from clinical_agent.domain.ingestion import PreparedIngestion
from clinical_agent.domain.pubmed import PubMedRecord


class OnlinePublicationStore(VersionedPostgresStore):
    records: dict[str, PubMedRecord]

    def configure(self, records: list[PubMedRecord]) -> None:
        self.records = {r.pmid: r for r in records}

    def _published(self, session: Session, prepared: PreparedIngestion) -> None:
        document = prepared.source.parsed.document
        record = getattr(self, "records", {}).get(document.pmid)
        if record is None:
            return
        notices = "; ".join(record.publication_types + record.notices)
        status = pubmed_status(record.publication_types, record.notices)
        if status is None:
            return
        identity = document.document_id
        state = session.get(SourceStateRecord, identity)
        if (
            state is not None
            and state.status in BLOCKED_STATUSES
            and status not in BLOCKED_STATUSES
        ):
            return
        event_id = uuid5(NAMESPACE_URL, f"pubmed-status:{identity}:{record.content_hash}:{status}")
        if session.get(SourceStatusEventRecord, event_id) is not None:
            return
        change = StatusChange(
            event_id=event_id,
            document_id=identity,
            status=status,
            expected_event_id=state.event_id if state else None,
            evidence=EvidenceBasis(
                uri=record.source_url,
                snapshot_hash=record.content_hash,
                quote=notices,
                recorded_by="official-pubmed-metadata",
            ),
        )
        session.add(
            SourceStatusEventRecord(
                event_id=event_id, document_id=identity, request=change.model_dump(mode="json")
            )
        )
        session.flush()
        if state is None:
            state = SourceStateRecord(document_id=identity)
            session.add(state)
        state.status, status_id = status, event_id
        state.event_id = status_id
        state.evidence = change.evidence.model_dump(mode="json")
        session.flush()
