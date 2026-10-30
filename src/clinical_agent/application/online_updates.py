"""Complete bounded PubMed windows; frozen source replay before ordinary local ingestion."""

import os
import tempfile
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from clinical_agent.domain.governance import (
    BLOCKED_STATUSES,
    EvidenceBasis,
    StatusChange,
    pubmed_status,
)
from clinical_agent.domain.ingestion import BatchIngestionResult, document_id_for
from clinical_agent.domain.maintenance import OnlineUpdateRequest
from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest
from clinical_agent.domain.updates import UpdateRequest


def _snapshot_file(path: Path, body: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".pubmed-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class OnlineUpdateService:
    def __init__(
        self,
        *,
        search: Any,
        repository: Any,
        run_local: Any,
        reader: Any,
        governance: Any = None,
        prepare_publication: Callable[[Any], None] | None = None,
    ):
        self.prepare_publication = prepare_publication
        self.search, self.repository, self.run_local, self.reader, self.governance = (
            search,
            repository,
            run_local,
            reader,
            governance,
        )

    def run(self, request: OnlineUpdateRequest) -> dict[str, object]:
        request = OnlineUpdateRequest.model_validate(request)
        lease = nullcontext() if request.dry_run else self.repository.lease(request)
        with lease:
            snapshot = self.repository.load(request)
            if snapshot is None:
                snapshot = self.search.search(
                    PubMedSearchRequest(
                        question=request.query,
                        options=PubMedOptions(
                            query=request.query,
                            date_from=request.date_from,
                            date_to=request.date_to,
                            date_field="edat",
                            sort="pub_date",
                            max_results=20,
                        ),
                    )
                )
            if (
                snapshot.status != "complete"
                or snapshot.truncated
                or snapshot.missing_pmids
                or snapshot.total_count != len(snapshot.records)
            ):
                return {
                    "status": "window_incomplete",
                    "provenance": snapshot.provenance().model_dump(mode="json"),
                    "cursor_advanced": False,
                }
            metadata = [r.pmid for r in snapshot.records if not r.source_units]
            if request.dry_run:
                from hashlib import sha256

                candidates = []
                for record in snapshot.records:
                    status = "metadata_only"
                    if record.source_units:
                        old = self.reader.load(document_id_for("pubmed", record.pmid))
                        body = (
                            "<PubmedArticleSet>" + record.snapshot_xml + "</PubmedArticleSet>"
                        ).encode()
                        document = old.source.parsed.document if old else None
                        fields = ("title", "authors", "journal", "doi", "publication_date")
                        status = (
                            "created"
                            if document is None
                            else "updated"
                            if document.abstract != record.abstract
                            else "metadata_updated"
                            if any(getattr(document, k) != getattr(record, k) for k in fields)
                            or document.content_hash != sha256(body).hexdigest()
                            else "unchanged"
                        )
                    candidates.append(
                        {"pmid": record.pmid, "status": status, "content_hash": record.content_hash}
                    )
                return {
                    "status": "dry_run",
                    "provenance": snapshot.provenance().model_dump(mode="json"),
                    "candidates": candidates,
                    "cursor_advanced": False,
                }
            if self.prepare_publication is not None:
                self.prepare_publication(snapshot.records)
            elif self.governance is not None and any(
                r.publication_types or r.notices for r in snapshot.records
            ):
                raise ValueError("atomic_notice_store_required")
            self.repository.save(request, snapshot)
            root = request.staging_root.resolve()
            folder = root / request.batch_id
            folder.mkdir(parents=True, exist_ok=True)
            if not folder.resolve().is_relative_to(root):
                raise ValueError("staging_path_invalid")
            files = []
            for record in snapshot.records:
                if not record.source_units:
                    continue
                name = f"{request.batch_id}/{record.pmid}-{record.content_hash}.xml"
                path = (root / name).resolve()
                if not path.is_relative_to(root):
                    raise ValueError("staging_path_invalid")
                body = ("<PubmedArticleSet>" + record.snapshot_xml + "</PubmedArticleSet>").encode()
                if path.exists():
                    if path.read_bytes() != body:
                        raise ValueError("snapshot_file_conflict")
                else:
                    _snapshot_file(path, body)
                files.append(name)
            # The hook is inside UpdateService's per-file success boundary.
            outcome = None
            if files:
                records_by_id = {document_id_for("pubmed", r.pmid): r for r in snapshot.records}

                def notices_after_publish(batch: BatchIngestionResult) -> None:
                    for entry in batch.entries:
                        if entry.document_id in records_by_id:
                            self.apply_notice(records_by_id[entry.document_id])

                outcome = self.run_local(
                    UpdateRequest(
                        batch_id="pubmed-" + request.batch_id,
                        allowed_root=root,
                        files=files,
                        source_type="pubmed_xml",
                        window_label=request.signature(),
                    ),
                    after_publish=notices_after_publish,
                )
                if outcome.status != "completed":
                    result = {"status": "failed", "update": outcome.model_dump(mode="json")}
                    self.repository.finish(request, result)
                    return result
            for record in snapshot.records:
                self.apply_notice(record)
            result = {
                "status": "completed",
                "provenance": snapshot.provenance().model_dump(mode="json"),
                "metadata_only": metadata,
                "update": outcome.model_dump(mode="json") if outcome else None,
            }
            self.repository.finish(request, result)
            return result

    def apply_notice(self, record: Any) -> None:
        if self.governance is None:
            return
        identity = document_id_for("pubmed", record.pmid)
        if self.reader.load(identity) is None:
            return
        notices = "; ".join(record.publication_types + record.notices)
        status = pubmed_status(record.publication_types, record.notices)
        if status is None:
            return
        current = self.governance.inspect(identity)
        event_id = uuid5(NAMESPACE_URL, f"pubmed-status:{identity}:{record.content_hash}:{status}")
        if any(e["request"]["event_id"] == str(event_id) for e in current["events"]):
            return
        if current["state"]["status"] in BLOCKED_STATUSES and status not in BLOCKED_STATUSES:
            return
        self.governance.change_status(
            StatusChange(
                event_id=event_id,
                document_id=identity,
                status=status,
                expected_event_id=current["state"]["event_id"],
                evidence=EvidenceBasis(
                    uri=record.source_url,
                    snapshot_hash=record.content_hash,
                    quote=notices,
                    recorded_by="official-pubmed-metadata",
                ),
            )
        )
