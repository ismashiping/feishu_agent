"""Session-level scoped exclusion; checkpoints use short independent transactions."""

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256

from sqlalchemy import Engine, select, text, update
from sqlalchemy.dialects.postgresql import insert

from clinical_agent.adapters.postgres.models import UpdateCursorRecord, UpdateRunRecord
from clinical_agent.domain.updates import UpdateRequest, UpdateResult


class PostgresUpdateLedger:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def position(self, request: UpdateRequest) -> int:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    select(UpdateCursorRecord).where(
                        UpdateCursorRecord.batch_id == request.batch_id
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return 0
            if row["scope_hash"] != request.signature():
                raise ValueError("batch_scope_conflict")
            return int(row["position"])

    @contextmanager
    def lease(self, request: UpdateRequest) -> Iterator[None]:
        key = int.from_bytes(sha256(request.batch_id.encode()).digest()[:8], signed=True)
        with self.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as owner:
            if not owner.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}):
                raise ValueError("update_busy")
            try:
                with self.engine.begin() as conn:
                    conn.execute(
                        insert(UpdateCursorRecord)
                        .values(
                            batch_id=request.batch_id, scope_hash=request.signature(), position=0
                        )
                        .on_conflict_do_nothing()
                    )
                    if (
                        conn.scalar(
                            select(UpdateCursorRecord.scope_hash).where(
                                UpdateCursorRecord.batch_id == request.batch_id
                            )
                        )
                        != request.signature()
                    ):
                        raise ValueError("batch_scope_conflict")
                    conn.execute(
                        update(UpdateRunRecord)
                        .where(
                            UpdateRunRecord.batch_id == request.batch_id,
                            UpdateRunRecord.status == "running",
                        )
                        .values(status="interrupted")
                    )
                yield
            finally:
                owner.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    def start(self, request: UpdateRequest, result: UpdateResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                insert(UpdateRunRecord).values(
                    run_id=result.run_id,
                    batch_id=request.batch_id,
                    status="running",
                    result=result.model_dump(mode="json"),
                )
            )
            if request.rescan:
                conn.execute(
                    update(UpdateCursorRecord)
                    .where(UpdateCursorRecord.batch_id == request.batch_id)
                    .values(position=0)
                )

    def checkpoint(self, request: UpdateRequest, result: UpdateResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(UpdateCursorRecord)
                .where(UpdateCursorRecord.batch_id == request.batch_id)
                .values(position=result.cursor_after)
            )
            conn.execute(
                update(UpdateRunRecord)
                .where(UpdateRunRecord.run_id == result.run_id)
                .values(status=result.status, result=result.model_dump(mode="json"))
            )
