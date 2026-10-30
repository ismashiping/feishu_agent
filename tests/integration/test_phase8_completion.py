from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import event

from tests.integration.test_postgres import engine as engine

pytestmark = [pytest.mark.integration, pytest.mark.database]


def test_online_real_db_freezes_and_replays(engine, tmp_path, fake_embedder):
    import httpx

    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.adapters.postgres.maintenance import OnlineBatchRepository
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.online_updates import OnlineUpdateService
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.ingestion import document_id_for
    from clinical_agent.domain.maintenance import OnlineUpdateRequest

    xml = (
        b"<PubmedArticleSet>"
        b"<PubmedArticle>"
        b"<MedlineCitation>"
        b"<PMID>82000001</PMID>"
        b"<Article>"
        b"<ArticleTitle>Online cohort</ArticleTitle>"
        b"<Abstract>"
        b"<AbstractText>Cohort evidence.</AbstractText>"
        b"</Abstract>"
        b"<PublicationTypeList>"
        b"<PublicationType>Retracted Publication</PublicationType>"
        b"</PublicationTypeList>"
        b"</Article>"
        b"</MedlineCitation>"
        b"</PubmedArticle>"
        b"</PubmedArticleSet>"
    )
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return (
            httpx.Response(200, json={"esearchresult": {"count": "1", "idlist": ["82000001"]}})
            if request.url.path.endswith("esearch.fcgi")
            else httpx.Response(200, content=xml)
        )

    from clinical_agent.adapters.postgres.online_publication import OnlinePublicationStore

    store = OnlinePublicationStore(engine)
    ingestion = IngestionService(
        reader=OfflineReader(tmp_path / "snapshots"),
        embedder=fake_embedder,
        store=store,
    )
    local = UpdateService(
        ledger=PostgresUpdateLedger(engine), publish=ingestion.ingest, reader=PostgresStore(engine)
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = OnlineUpdateService(
            search=PubMedClient(client, PubMedSettings()),
            repository=OnlineBatchRepository(engine),
            run_local=local.run,
            reader=PostgresStore(engine),
            governance=SourceGovernance(engine),
            prepare_publication=store.configure,
        )
        request = OnlineUpdateRequest(
            batch_id="online-real",
            query="cohort",
            date_from=date(2026, 10, 1),
            date_to=date(2026, 10, 2),
            staging_root=tmp_path / "staging",
        )
        dry = service.run(request.model_copy(update={"dry_run": True}))
        assert dry["status"] == "dry_run" and not (tmp_path / "staging").exists()
        identity = document_id_for("pubmed", "82000001")

        def fail_status(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO source_states"):
                raise RuntimeError("Injected atomic notice failure")

        event.listen(engine, "before_cursor_execute", fail_status)
        try:
            assert service.run(request)["status"] == "failed"
        finally:
            event.remove(engine, "before_cursor_execute", fail_status)
        assert PostgresStore(engine).load(identity) is None
        failed_calls = len(calls)
        checkpoint = local.ledger.checkpoint

        def crash(*args):
            raise RuntimeError("checkpoint unavailable")

        local.ledger.checkpoint = crash
        try:
            with pytest.raises(RuntimeError):
                service.run(request)
        finally:
            local.ledger.checkpoint = checkpoint
        assert SourceGovernance(engine).inspect(identity)["state"]["status"] == "retracted"
        first = service.run(request)
        assert len(calls) == failed_calls
        assert first["status"] == "completed"
        call_count = len(calls)
        assert service.run(request)["status"] == "completed" and len(calls) == call_count
        state = SourceGovernance(engine).inspect(document_id_for("pubmed", "82000001"))["state"]
        assert state["status"] == "retracted"
        assert (
            SourceGovernance(engine).statuses_for_pmids(["82000001"])["82000001"].status
            == "retracted"
        )
        from sqlalchemy import func, select

        from clinical_agent.adapters.postgres.models import DocumentVersionRecord

        with engine.connect() as conn:
            count = conn.scalar(
                select(func.count())
                .select_from(DocumentVersionRecord)
                .where(DocumentVersionRecord.document_id == identity)
            )
        overlap = request.model_copy(
            update={"batch_id": "online-overlap", "date_to": date(2026, 10, 3)}
        )
        assert service.run(overlap)["status"] == "completed"
        with engine.connect() as conn:
            assert (
                conn.scalar(
                    select(func.count())
                    .select_from(DocumentVersionRecord)
                    .where(DocumentVersionRecord.document_id == identity)
                )
                == count
            )
        with pytest.raises(ValueError, match="batch_scope_conflict"):
            service.run(request.model_copy(update={"query": "different"}))


def test_rebuild_stage_atomic_activation_and_stale_guard(
    engine, source_factory, prepared_factory, fake_embedder
):
    from clinical_agent.adapters.postgres.rebuild import KnowledgeRebuilder
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.maintenance import RebuildRequest

    store = VersionedPostgresStore(engine)
    original = prepared_factory(
        source_factory(text="Rebuild source evidence with enough text to split.")
    )
    store.save(original)
    identity = original.source.parsed.document.document_id
    rebuild = KnowledgeRebuilder(engine, fake_embedder)
    request = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    old = PostgresStore(engine).load(identity)
    assert rebuild.stage(request, evaluate=lambda _: "not_accepted")["status"] == "staged"
    with pytest.raises(ValueError, match="evaluation_required"):
        rebuild.activate(request.run_id)
    accepted = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    rebuild.stage(accepted, evaluate=rebuild.evaluate)
    assert (
        PostgresStore(engine).load(identity).embedded[0].evidence.chunk_id
        == old.embedded[0].evidence.chunk_id
    )

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO chunks"):
            raise RuntimeError("Injected activation failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError):
            rebuild.activate(accepted.run_id)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert (
        PostgresStore(engine).load(identity).embedded[0].evidence.chunk_id
        == old.embedded[0].evidence.chunk_id
    )
    assert rebuild.activate(accepted.run_id)["status"] == "activated"
    assert rebuild.activate(accepted.run_id)["status"] == "activated"
    assert len(PostgresStore(engine).load(identity).embedded) > len(old.embedded)
    assert store.load_version(store.version_id(original)) is not None
    stale = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    rebuild.stage(stale, evaluate=lambda _: "passed")
    store.save(prepared_factory(source_factory(text="Concurrent new document")))
    with pytest.raises(ValueError, match="source_changed"):
        rebuild.activate(stale.run_id)


def test_rebuild_model_guard_and_no_evaluation(engine, fake_embedder):
    from clinical_agent.adapters.postgres.rebuild import KnowledgeRebuilder
    from clinical_agent.domain.maintenance import RebuildRequest

    fake_embedder.tokenizer_profile = fake_embedder.tokenizer_profile.model_copy(
        update={"model_id": "unknown-model"}
    )
    with pytest.raises(ValueError, match="unsupported_rebuild_model"):
        KnowledgeRebuilder(engine, fake_embedder).stage(RebuildRequest(run_id=uuid4()))
    assert fake_embedder.calls == 0


@pytest.mark.external
def test_official_window_real_e5_and_database_rebuild(engine, tmp_path):
    """One actual official record, cached pinned E5 and disposable PostgreSQL only."""
    import json
    import os
    from pathlib import Path

    from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.adapters.postgres.maintenance import OnlineBatchRepository
    from clinical_agent.adapters.postgres.online_publication import OnlinePublicationStore
    from clinical_agent.adapters.postgres.rebuild import KnowledgeRebuilder
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.update_runs import PostgresUpdateLedger
    from clinical_agent.adapters.pubmed_online import open_pubmed
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.online_updates import OnlineUpdateService
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.ingestion import document_id_for
    from clinical_agent.domain.maintenance import OnlineUpdateRequest, RebuildRequest
    from clinical_agent.domain.retrieval import RetrievalOptions

    root = Path(__file__).resolve().parents[2]
    model = root / "models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a"
    embedder = load_local_embedder(LocalModelConfig(snapshot_dir=model))
    reader = PostgresStore(engine)
    store = OnlinePublicationStore(engine)
    ingestion = IngestionService(
        reader=OfflineReader(tmp_path / "snapshots"), embedder=embedder, store=store
    )
    local = UpdateService(
        ledger=PostgresUpdateLedger(engine), publish=ingestion.ingest, reader=reader
    )
    request = OnlineUpdateRequest(
        batch_id="official-one-record",
        query="26551272[uid]",
        date_from=date(2015, 11, 1),
        date_to=date(2015, 11, 30),
        staging_root=tmp_path / "staging",
    )
    with open_pubmed() as client:
        service = OnlineUpdateService(
            search=client,
            repository=OnlineBatchRepository(engine),
            run_local=local.run,
            reader=reader,
            governance=SourceGovernance(engine),
            prepare_publication=store.configure,
        )
        result = service.run(request)
        assert result["status"] == "completed"
        assert result["provenance"]["returned_count"] == 1
        frozen = service.repository.load(request)
        assert len(frozen.records) == 1 and frozen.records[0].pmid == "26551272"
        assert service.run(request)["status"] == "completed"
    identity = document_id_for("pubmed", "26551272")
    before = reader.load(identity)
    assert before is not None and before.source.parsed.document.pmid == "26551272"
    old_chunks = [str(v.evidence.chunk_id) for v in before.embedded]
    retriever = PostgresRetriever(engine)
    query = embedder.embed_query("intensive blood pressure control randomized trial")
    found = retriever.search(query, RetrievalOptions(document_ids=[identity]))
    assert found.hits and found.hits[0].document.pmid == "26551272"
    rebuilder = KnowledgeRebuilder(engine, embedder)
    rebuild_request = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=256))
    staged = rebuilder.stage(rebuild_request, evaluate=rebuilder.evaluate)
    assert staged["evaluation_status"] == "passed"
    assert [str(v.evidence.chunk_id) for v in reader.load(identity).embedded] == old_chunks
    active = rebuilder.activate(rebuild_request.run_id)
    assert active["status"] == "activated"
    assert retriever.search(query, RetrievalOptions(document_ids=[identity])).hits
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore

    history = VersionedPostgresStore(engine).load_version(store.version_id(before))
    assert [str(v.evidence.chunk_id) for v in history.embedded] == old_chunks
    evidence = Path(os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"])
    (evidence / "official-pipeline-result.json").write_text(
        json.dumps(
            {
                "online": result,
                "stage": staged,
                "activation": active,
                "old_chunk_ids": old_chunks,
                "model": "pinned-real-local-e5",
                "medical_review": "not_performed",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
