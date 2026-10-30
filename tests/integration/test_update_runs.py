import pytest

from tests.integration.test_postgres import engine as engine

pytestmark = [pytest.mark.integration, pytest.mark.database]


def test_update_resume_dry_run_and_rescan(engine, tmp_path, pdf_factory):
    from uuid import uuid4

    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.ingestion import BatchIngestionResult, IngestionResult
    from clinical_agent.domain.updates import UpdateRequest

    for name in ["a.pdf", "b.pdf"]:
        pdf_factory(tmp_path / name)
    ledger = PostgresUpdateLedger(engine)
    fail = [True]
    calls = []

    def publish(request):
        calls.append(request.path.name)
        if request.path.name == "b.pdf" and fail[0]:
            return BatchIngestionResult(entries=[], error_code="source_failed")
        return BatchIngestionResult(
            entries=[
                IngestionResult(
                    index=1,
                    status="already_present",
                    document_id=uuid4(),
                    chunk_count=1,
                    error_code=None,
                )
            ]
        )

    class Reader:
        def load(self, identity):
            return None

    service = UpdateService(ledger=ledger, publish=publish, reader=Reader())
    request = UpdateRequest(
        batch_id="resume", allowed_root=tmp_path, files=["a.pdf", "b.pdf"], source_type="pdf"
    )
    first = service.run(request)
    assert first.status == "failed" and first.cursor_after == 1
    fail[0] = False
    second = service.run(request)
    assert second.status == "completed" and second.cursor_before == 1 and second.cursor_after == 2
    assert calls == ["a.pdf", "b.pdf", "b.pdf"]
    before = ledger.position(request)
    service.run(request.model_copy(update={"dry_run": True}))
    assert ledger.position(request) == before
    assert service.run(request).items == []
    assert service.run(request.model_copy(update={"rescan": True})).cursor_after == 2
    with ledger.lease(request):
        with pytest.raises(ValueError, match="busy"):
            service.run(request)


def test_evaluation_failure_is_not_quality_pass(engine, tmp_path, pdf_factory):
    from uuid import uuid4

    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.ingestion import BatchIngestionResult, IngestionResult
    from clinical_agent.domain.updates import UpdateRequest

    pdf_factory(tmp_path / "q.pdf")

    def publish(request):
        return BatchIngestionResult(
            entries=[
                IngestionResult(
                    index=1, status="updated", document_id=uuid4(), chunk_count=1, error_code=None
                )
            ]
        )

    def evaluate():
        raise RuntimeError("fixed regression unavailable")

    result = UpdateService(
        ledger=PostgresUpdateLedger(engine), publish=publish, reader=object(), evaluate=evaluate
    ).run(UpdateRequest(batch_id="eval", allowed_root=tmp_path, files=["q.pdf"], source_type="pdf"))
    assert result.cursor_after == 1 and result.evaluation_status == "failed"


def test_publication_commit_before_cursor_crash_replays_idempotently(
    engine, tmp_path, pdf_factory, fake_embedder
):
    from sqlalchemy import func, select

    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.models import DocumentVersionRecord
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.updates import UpdateRequest

    pdf_factory(tmp_path / "pipeline.pdf", texts=("Local update pipeline evidence.",))
    snapshots = tmp_path / "snapshots"
    store = VersionedPostgresStore(engine)
    ingestion = IngestionService(
        reader=OfflineReader(snapshots), embedder=fake_embedder, store=store
    )

    class CrashLedger(PostgresUpdateLedger):
        def checkpoint(self, request, result):
            raise RuntimeError("Crash after document commit")

    request = UpdateRequest(
        batch_id="crash-pipeline", allowed_root=tmp_path, files=["pipeline.pdf"], source_type="pdf"
    )
    ledger = PostgresUpdateLedger(engine)
    normal = UpdateService(ledger=ledger, publish=ingestion.ingest, reader=store)
    before = normal.run(request.model_copy(update={"dry_run": True}))
    assert before.counts == {"created": 1} and not snapshots.exists() and fake_embedder.calls == 0
    with pytest.raises(RuntimeError):
        UpdateService(ledger=CrashLedger(engine), publish=ingestion.ingest, reader=store).run(
            request
        )
    assert ledger.position(request) == 0
    recovered = normal.run(request)
    assert recovered.status == "completed" and recovered.counts == {"unchanged": 1}
    assert ledger.position(request) == 1
    dry = normal.run(request.model_copy(update={"dry_run": True}))
    assert dry.counts == {"unchanged": 1} and fake_embedder.calls == 2
    from hashlib import sha256

    from clinical_agent.domain.ingestion import document_id_for

    identity = document_id_for("pdf", sha256((tmp_path / "pipeline.pdf").read_bytes()).hexdigest())

    with engine.connect() as conn:
        assert (
            conn.scalar(
                select(func.count())
                .select_from(DocumentVersionRecord)
                .where(DocumentVersionRecord.document_id == identity)
            )
            == 1
        )


def test_xml_metadata_plan_matches_real_publication(engine, tmp_path, fake_embedder):
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.updates import UpdateRequest
    from tests.unit.test_pubmed_online import article, xml

    path = tmp_path / "metadata.xml"
    path.write_bytes(xml(article("98765099")))
    store = VersionedPostgresStore(engine)
    ingestion = IngestionService(
        reader=OfflineReader(tmp_path / "snapshots"), embedder=fake_embedder, store=store
    )
    service = UpdateService(
        ledger=PostgresUpdateLedger(engine), publish=ingestion.ingest, reader=store
    )
    request = UpdateRequest(
        batch_id="xml-metadata",
        allowed_root=tmp_path,
        files=["metadata.xml"],
        source_type="pubmed_xml",
    )
    assert service.run(request).counts == {"created": 1}
    path.write_bytes(xml(article("98765099").replace("Synthetic", "Corrected")))
    assert service.run(request.model_copy(update={"dry_run": True})).counts == {
        "metadata_updated": 1
    }
    result = service.run(request.model_copy(update={"rescan": True}))
    assert result.counts == {"metadata_updated": 1}
