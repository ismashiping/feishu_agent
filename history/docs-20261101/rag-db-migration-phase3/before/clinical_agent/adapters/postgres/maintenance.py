"""Frozen online scopes use the same session lease primitive as local updates."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, select, update
from sqlalchemy.dialects.postgresql import insert

from clinical_agent.adapters.postgres.models import OnlineUpdateBatchRecord
from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
from clinical_agent.domain.maintenance import OnlineUpdateRequest
from clinical_agent.domain.pubmed import PubMedSearchResult
from clinical_agent.domain.updates import UpdateRequest


class OnlineBatchRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def load(self, request: OnlineUpdateRequest) -> PubMedSearchResult | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(OnlineUpdateBatchRecord).where(
                        OnlineUpdateBatchRecord.batch_id == request.batch_id
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        if row["scope_hash"] != request.signature():
            raise ValueError("batch_scope_conflict")
        return PubMedSearchResult.model_validate(row["snapshot"])

    @contextmanager
    def lease(self, request: OnlineUpdateRequest) -> Iterator[None]:
        lock = UpdateRequest(
            batch_id="online-lock-" + request.batch_id,
            allowed_root=request.staging_root,
            files=["scope"],
            source_type="pubmed_xml",
            window_label=request.signature(),
        )
        with PostgresUpdateLedger(self.engine).lease(lock):
            yield

    def save(self, request: OnlineUpdateRequest, result: PubMedSearchResult) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(OnlineUpdateBatchRecord)
                .values(
                    batch_id=request.batch_id,
                    scope_hash=request.signature(),
                    snapshot=result.model_dump(mode="json"),
                    result={},
                )
                .on_conflict_do_nothing()
            )
        self.load(request)

    def finish(self, request: OnlineUpdateRequest, result: dict[str, object]) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(OnlineUpdateBatchRecord)
                .where(OnlineUpdateBatchRecord.batch_id == request.batch_id)
                .values(result=result)
            )
