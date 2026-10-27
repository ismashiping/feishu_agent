"""Real PostgreSQL ingestion; only the explicit external test loads an actual model."""

import copy
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database]
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine():
    from alembic.config import Config
    from sqlalchemy import text

    from alembic import command
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine

    settings = DatabaseSettings()
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    with database_engine(settings) as engine:
        with engine.begin() as connection:
            config = Config(str(ROOT / "alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "p107_0002"
        yield engine


@pytest.fixture
def store(engine):
    from sqlalchemy import delete

    from clinical_agent.adapters.postgres.models import DocumentRecord
    from clinical_agent.adapters.postgres.store import PostgresStore

    value = PostgresStore(engine)
    try:
        yield value
    finally:
        # This module owns the explicitly resettable test database during its sequential run.
        with engine.begin() as connection:
            connection.execute(delete(DocumentRecord))


@pytest.mark.parametrize("kind", ["pdf", "pubmed"])
def test_atomic_save_load_duplicate_and_non_overwrite(
    store, source_factory, prepared_factory, kind
):
    from clinical_agent.domain.ingestion import PreparedIngestion

    original = prepared_factory(source_factory(kind=kind))
    before = original.model_dump_json()
    first = store.save(original)
    second = store.save(original)
    assert first.status == "imported" and second.status == "already_present"
    assert first.document_id == second.document_id
    stored = store.load(first.document_id)
    assert stored == original and original.model_dump_json() == before
    assert PreparedIngestion.model_validate_json(stored.model_dump_json()) == stored
    correction = copy.deepcopy(original)
    correction.source.parsed.document.title = "Corrected title"
    assert store.save(correction).status == "conflict"
    assert store.load(first.document_id) == original


def test_pubmed_changed_snapshot_returns_needs_update_without_overwriting(
    store, source_factory, prepared_factory
):
    first = prepared_factory(source_factory(kind="pubmed"))
    store.save(first)
    changed = prepared_factory(source_factory(text="Changed abstract.", kind="pubmed"))
    result = store.save(changed)
    assert result.status == "needs_update"
    assert result.document_id == first.source.parsed.document.document_id
    assert store.load(result.document_id) == first


def test_changed_processing_policy_is_conflict(store, source_factory, prepared_factory):
    source = source_factory()
    store.save(prepared_factory(source))
    assert store.save(prepared_factory(source, max_tokens=32)).status == "conflict"


def test_source_duplicate_returns_database_canonical_id(store, source_factory, prepared_factory):
    source = source_factory()
    first = store.save(prepared_factory(source))
    other = source_factory()
    assert other.parsed.document.document_id != first.document_id
    result = store.save(prepared_factory(other))
    assert result.status == "already_present" and result.document_id == first.document_id


def test_non_source_chunk_constraint_rolls_back_document(store, source_factory, prepared_factory):
    from clinical_agent.domain.ingestion import IngestionError, PreparedIngestion

    first = prepared_factory()
    store.save(first)
    other = prepared_factory(source_factory(text="Different content."))
    data = other.model_dump()
    collision = first.embedded[0].evidence.chunk_id
    data["chunking"]["chunks"][0]["evidence"]["chunk_id"] = collision
    data["embedded"][0]["evidence"]["chunk_id"] = collision
    broken = PreparedIngestion.model_validate(data)
    with pytest.raises(IngestionError, match="^storage_conflict$"):
        store.save(broken)
    assert store.load(other.source.parsed.document.document_id) is None
    assert store.load(first.source.parsed.document.document_id) == first


def test_wrong_document_primary_key_is_not_reported_as_duplicate(
    store, source_factory, prepared_factory
):
    from clinical_agent.domain.ingestion import IngestionError

    first = prepared_factory()
    store.save(first)
    other_source = source_factory(
        text="Different", document_id=first.source.parsed.document.document_id
    )
    with pytest.raises(IngestionError, match="^storage_conflict$"):
        store.save(prepared_factory(other_source))
    assert store.load(first.source.parsed.document.document_id) == first


@pytest.mark.parametrize("case", ["legacy", "source_units", "count"])
def test_corrupt_storage_is_not_accepted_as_duplicate(store, engine, prepared_factory, case):
    from sqlalchemy import delete, update

    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord
    from clinical_agent.domain.ingestion import IngestionError

    original = prepared_factory(max_tokens=13)
    identity = store.save(original).document_id
    with engine.begin() as connection:
        if case == "legacy":
            connection.execute(update(DocumentRecord).values(ingestion_metadata=None))
        elif case == "source_units":
            connection.execute(update(DocumentRecord).values(source_units=[{"bad": "data"}]))
        else:
            connection.execute(delete(ChunkRecord).where(ChunkRecord.chunk_index == 1))
    with pytest.raises(IngestionError, match="^storage_corrupt$"):
        store.load(identity)
    with pytest.raises(IngestionError, match="^storage_corrupt$"):
        store.save(original)


def test_commit_failure_rolls_back_and_retry_succeeds(store, engine, prepared_factory):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError

    from clinical_agent.domain.ingestion import IngestionError

    original = prepared_factory()

    def fail(connection):
        raise OperationalError("synthetic commit", None, RuntimeError("secret-database-details"))

    event.listen(engine, "commit", fail)
    try:
        with pytest.raises(IngestionError, match="^storage_unavailable$"):
            store.save(original)
    finally:
        event.remove(engine, "commit", fail)
    assert store.load(original.source.parsed.document.document_id) is None
    assert store.save(original).status == "imported"
    assert store.save(original).status == "already_present"


def test_simultaneous_same_source_imports_have_one_canonical_commit(
    store, engine, prepared_factory
):
    from sqlalchemy import event, func, select
    from sqlalchemy.orm import Session

    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord

    original = prepared_factory()
    barrier = threading.Barrier(2, timeout=5)

    def synchronize(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO documents"):
            barrier.wait()

    event.listen(engine, "before_cursor_execute", synchronize)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: store.save(original), range(2)))
    finally:
        event.remove(engine, "before_cursor_execute", synchronize)
    assert sorted(r.status for r in results) == ["already_present", "imported"]
    assert results[0].document_id == results[1].document_id
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(DocumentRecord)) == 1
        assert session.scalar(select(func.count()).select_from(ChunkRecord)) == len(
            original.embedded
        )


def test_incremental_migration_preserves_legacy_row_without_fabrication(engine):
    from alembic.config import Config
    from sqlalchemy import text

    from alembic import command
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.domain.ingestion import IngestionError

    identity = uuid4()
    with engine.begin() as connection:
        config = Config(str(ROOT / "alembic.ini"))
        config.attributes["connection"] = connection
        command.downgrade(config, "p106_0001")
        connection.execute(
            text("""INSERT INTO documents(document_id,source_type,content_hash,source_uri,
        content_scope,title,title_origin,authors,publication_date,text,ingestion_time,source_units)
        VALUES(:id,'pdf',:hash,'file:///legacy.pdf','extracted_text','Legacy','filename','[]',
        CAST(:date AS jsonb),'Legacy',CURRENT_TIMESTAMP,CAST(:units AS jsonb))"""),
            {
                "id": identity,
                "hash": identity.hex * 2,
                "date": json.dumps({"precision": "unknown"}),
                "units": json.dumps([{"page": 1, "text": "Legacy"}]),
            },
        )
        command.upgrade(config, "head")
        command.check(config)
        assert connection.scalar(
            text("SELECT ingestion_metadata IS NULL FROM documents WHERE document_id=:id"),
            {"id": identity},
        )
    try:
        with pytest.raises(IngestionError, match="^storage_corrupt$"):
            PostgresStore(engine).load(identity)
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM documents WHERE document_id=:id"), {"id": identity}
            )


def test_actual_pdf_and_xml_application_chain_uses_no_db_connection_until_store(
    store,
    engine,
    tmp_path,
    pdf_factory,
    fake_embedder,
):
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.domain.ingestion import ImportRequest

    original = fake_embedder.embed_chunks

    def encode(source):
        assert engine.pool.checkedout() == 0
        return original(source)

    fake_embedder.embed_chunks = encode
    app = IngestionService(
        reader=OfflineReader(tmp_path / "cache"), embedder=fake_embedder, store=store
    )
    path = pdf_factory(tmp_path / "original.pdf")
    request = ImportRequest(
        source_type="pdf",
        path=path,
        allowed_root=tmp_path,
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
    )
    first = app.ingest(request)
    assert first.entries[0].status == "imported"
    path.rename(tmp_path / "renamed.pdf")
    second = app.ingest(ImportRequest(**{**request.model_dump(), "path": tmp_path / "renamed.pdf"}))
    assert second.entries[0].status == "already_present"
    loaded = store.load(first.entries[0].document_id)
    assert [unit.page for unit in loaded.source.parsed.source_units] == [1, 2, 3]
    for encoded in loaded.embedded:
        loaded.source.parsed.validate_chunk(encoded.evidence)

    xml = tmp_path / "source.xml"
    xml.write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
    <Article><ArticleTitle>Fixture</ArticleTitle><Abstract><AbstractText Label="RESULTS">
    中文 α🙂 evidence.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>
    <PubmedArticle><MedlineCitation><PMID>456</PMID><Article>
    <ArticleTitle>No abstract</ArticleTitle>
    </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
    )
    xml_result = app.ingest(
        ImportRequest(
            source_type="pubmed_xml",
            path=xml,
            allowed_root=tmp_path,
            ingestion_time=request.ingestion_time,
        )
    )
    assert [entry.status for entry in xml_result.entries] == ["imported", "rejected"]
    assert xml_result.entries[1].error_code == "pubmed_no_abstract"
    abstract = store.load(xml_result.entries[0].document_id)
    assert abstract.source.parsed.document.content_scope == "abstract"
    for encoded in abstract.embedded:
        abstract.source.parsed.validate_chunk(encoded.evidence)


@pytest.mark.external
def test_real_pdf_e5_postgres_end_to_end(store, tmp_path, pdf_factory, monkeypatch):
    import socket

    from clinical_agent.adapters.embedding import REVISION, LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.domain.ingestion import ImportRequest

    path = pdf_factory(tmp_path / "real-model-source.pdf")
    # The database is on 127.0.0.1; reject all non-loopback network destinations.
    original_connect = socket.socket.connect

    def local_only(connection, address):
        assert address[0] == "127.0.0.1"
        return original_connect(connection, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)
    embedder = load_local_embedder(
        LocalModelConfig(snapshot_dir=ROOT / "models/multilingual-e5-base" / REVISION)
    )
    app = IngestionService(reader=OfflineReader(tmp_path / "cache"), embedder=embedder, store=store)
    request = ImportRequest(
        source_type="pdf",
        path=path,
        allowed_root=tmp_path,
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
    )
    first, repeated = app.ingest(request), app.ingest(request)
    assert first.entries[0].status == "imported"
    assert repeated.entries[0].status == "already_present"
    identity = first.entries[0].document_id
    loaded = store.load(identity)
    path.rename(tmp_path / "moved-original.pdf")
    assert len(loaded.embedded) == 2
    for encoded in loaded.embedded:
        loaded.source.parsed.validate_chunk(encoded.evidence)
        assert len(encoded.vector) == 768
    report = {
        "statuses": [first.entries[0].status, repeated.entries[0].status],
        "document_id": str(identity),
        "chunks": len(loaded.embedded),
        "model_revision": REVISION,
        "dimension": 768,
        "token_counts": [item.token_count for item in loaded.chunking.chunks],
        "parser_version": loaded.source.parser_version,
        "snapshot_survives_original_move": (
            tmp_path / "cache" / f"{loaded.source.parsed.document.content_hash}.pdf"
        ).is_file(),
    }
    assert report["snapshot_survives_original_move"]
    (ROOT / ".artifacts/p1-07-20261027-01/real-chain-result.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )


def test_store_sets_read_committed_even_for_snapshot_isolation_engine(
    engine, store, prepared_factory
):
    from sqlalchemy import event

    from clinical_agent.adapters.postgres.store import PostgresStore

    levels = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO documents"):
            levels.append(connection.get_isolation_level())

    parent = engine.execution_options(isolation_level="REPEATABLE READ")
    event.listen(engine, "before_cursor_execute", observe)
    try:
        assert PostgresStore(parent).save(prepared_factory()).status == "imported"
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert levels == ["READ COMMITTED"]
    assert parent.get_execution_options()["isolation_level"] == "REPEATABLE READ"
