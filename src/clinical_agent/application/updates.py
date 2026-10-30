"""Bounded local update orchestration, including genuinely encoding-free plans."""

from collections import Counter
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Literal, Protocol, cast
from uuid import UUID, uuid4

from clinical_agent.domain.ingestion import (
    BatchIngestionResult,
    ImportRequest,
    PreparedIngestion,
    document_id_for,
)
from clinical_agent.domain.models import ParsedPdf, ParsedPubmedArticle
from clinical_agent.domain.updates import UpdateRequest, UpdateResult


class UpdateLedger(Protocol):
    def position(self, request: UpdateRequest) -> int: ...
    def lease(self, request: UpdateRequest) -> AbstractContextManager[None]: ...
    def start(self, request: UpdateRequest, result: UpdateResult) -> None: ...
    def checkpoint(self, request: UpdateRequest, result: UpdateResult) -> None: ...


class HistoricalReader(Protocol):
    def load(self, identity: UUID) -> PreparedIngestion | None: ...


def logical_content(prepared: PreparedIngestion) -> object:
    parsed = prepared.source.parsed
    return [
        parsed.document.text,
        parsed.document.abstract,
        [u.model_dump(mode="json") for u in parsed.source_units],
    ]


def dry_plan(request: UpdateRequest, reader: HistoricalReader) -> list[dict[str, object]]:
    from hashlib import sha256

    from clinical_agent.adapters.pdf import parse_pdf
    from clinical_agent.adapters.pubmed_xml import parse_pubmed_xml

    root = request.allowed_root.resolve(strict=True)
    items: list[dict[str, object]] = []
    parsed: list[ParsedPdf | ParsedPubmedArticle]
    for name in request.files:
        path = (root / name).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("source_path_invalid")
        if request.source_type == "pdf":
            with path.open("rb") as stream:
                data = stream.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise ValueError("source_too_large")
            digest = sha256(data).hexdigest()
            parsed = [
                parse_pdf(
                    path,
                    allowed_root=root,
                    document_id=document_id_for("pdf", digest),
                    ingestion_time=datetime.now(UTC),
                )
            ]
        else:
            batch = parse_pubmed_xml(
                path,
                allowed_root=root,
                ingestion_time=datetime.now(UTC),
                document_id_factory=lambda pmid: document_id_for("pubmed", pmid),
            )
            if any(e.article is None for e in batch.entries):
                raise ValueError("source_record_invalid")
            parsed = [e.article for e in batch.entries if e.article]
        for value in parsed:
            old = reader.load(value.document.document_id)
            content = [
                value.document.text,
                value.document.abstract,
                [u.model_dump(mode="json") for u in value.source_units],
            ]
            exclude = {"document_id", "source_uri", "ingestion_time", "evidence_chunks"}
            status = (
                "created"
                if old is None
                else "updated"
                if logical_content(old) != content
                else "unchanged"
                if old.source.parsed.document.model_dump(exclude=exclude)
                == value.document.model_dump(exclude=exclude)
                else "metadata_updated"
            )
            items.append(
                {"path": name, "document_id": str(value.document.document_id), "status": status}
            )
    return items


class UpdateService:
    def __init__(
        self,
        *,
        ledger: UpdateLedger,
        publish: Callable[[ImportRequest], BatchIngestionResult],
        reader: HistoricalReader,
        evaluate: Callable[[], str] | None = None,
    ) -> None:
        self.ledger, self.publish, self.reader, self.evaluate = ledger, publish, reader, evaluate

    def run(
        self,
        request: UpdateRequest,
        *,
        after_publish: Callable[[BatchIngestionResult], None] | None = None,
    ) -> UpdateResult:
        request = UpdateRequest.model_validate(request).model_copy(deep=True)
        if request.dry_run:
            before = self.ledger.position(request) if hasattr(self.ledger, "position") else 0
            plan = dry_plan(request, self.reader)
            return UpdateResult(
                run_id=uuid4(),
                status="dry_run",
                cursor_before=before,
                cursor_after=before,
                items=plan,
                counts=dict(Counter(str(item["status"]) for item in plan)),
                scope_hash=request.signature(),
                window_label=request.window_label,
            )
        with self.ledger.lease(request):
            before = 0 if request.rescan else self.ledger.position(request)
            result = UpdateResult(
                run_id=uuid4(),
                status="running",
                cursor_before=before,
                cursor_after=before,
                items=[],
                scope_hash=request.signature(),
                window_label=request.window_label,
            )
            self.ledger.start(request, result)
            for index in range(before, len(request.files)):
                name = request.files[index]
                try:
                    root = request.allowed_root.resolve(strict=True)
                    path = (root / name).resolve(strict=True)
                    if not path.is_relative_to(root) or not path.is_file():
                        raise ValueError("source_path_invalid")
                    outcome = self.publish(
                        ImportRequest(
                            source_type=request.source_type,
                            path=path,
                            allowed_root=root,
                            ingestion_time=datetime.now(UTC),
                        )
                    )
                    if (
                        after_publish is not None
                        and outcome.error_code is None
                        and outcome.entries
                        and all(
                            e.status
                            in {"imported", "updated", "metadata_updated", "already_present"}
                            for e in outcome.entries
                        )
                    ):
                        after_publish(outcome)
                    for entry in outcome.entries:
                        key = {
                            "imported": "created",
                            "already_present": "unchanged",
                            "conflict": "conflicted",
                        }.get(entry.status, entry.status)
                        result.counts[key] = result.counts.get(key, 0) + 1
                    if outcome.error_code is not None:
                        result.counts["failed"] = result.counts.get("failed", 0) + 1
                    success = (
                        outcome.error_code is None
                        and bool(outcome.entries)
                        and all(
                            e.status
                            in {"imported", "updated", "metadata_updated", "already_present"}
                            for e in outcome.entries
                        )
                    )
                    result.items.append(
                        {
                            "path": name,
                            "status": "committed" if success else "failed",
                            "result": outcome.model_dump(mode="json"),
                        }
                    )
                except Exception as error:
                    result.counts["failed"] = result.counts.get("failed", 0) + 1
                    success = False
                    result.items.append(
                        {"path": name, "status": "failed", "error_type": type(error).__name__}
                    )
                if success:
                    result.cursor_after = index + 1
                else:
                    result.status = "failed"
                self.ledger.checkpoint(request, result)
                if not success:
                    break
            else:
                result.status = "completed"
            if result.status == "completed" and self.evaluate is not None and result.items:
                try:
                    status = self.evaluate()
                    result.evaluation_status = (
                        cast(Literal["passed", "not_accepted", "failed"], status)
                        if status in {"passed", "not_accepted", "failed"}
                        else "failed"
                    )
                except Exception:
                    result.evaluation_status = "failed"
            self.ledger.checkpoint(request, result)
            return result
