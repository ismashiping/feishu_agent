"""Real pgvector distances, filtering, snapshot hydration and explicit model acceptance."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database]
ROOT = Path(__file__).resolve().parents[2]


def query(vector=None):
    from clinical_agent.domain.embedding import QueryEmbedding
    from clinical_agent.domain.retrieval import retrieval_embedding_info

    return QueryEmbedding(
        embedding_info=retrieval_embedding_info(),
        vector=vector if vector is not None else [1.0] + [0.0] * 767,
    )


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

    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    try:
        yield PostgresStore(engine)
    finally:
        with engine.begin() as connection:
            connection.execute(delete(DocumentRecord))


@pytest.fixture
def seed(store, source_factory, prepared_factory):
    def make(text, direction, index, kind="pdf"):
        from clinical_agent.domain.ingestion import PreparedIngestion

        prepared = prepared_factory(source_factory(text=text, kind=kind, pmid=str(index + 100)))
        data = prepared.model_dump()
        identity = UUID(int=index)
        data["chunking"]["chunks"][0]["evidence"]["chunk_id"] = identity
        data["embedded"][0]["evidence"]["chunk_id"] = identity
        data["embedded"][0]["vector"] = direction + [0.0] * (768 - len(direction))
        prepared = PreparedIngestion.model_validate(data)
        store.save(prepared)
        return prepared

    return make


def test_exact_distances_stable_ties_top_k_and_detached_hits(engine, seed):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult

    seed("Later UUID", [1.0], 20)
    first = seed("First UUID 中文 α🙂.", [1.0], 10)
    seed("Partial alignment", [0.6, 0.8], 30)
    seed("Orthogonal", [0.0, 1.0], 40)
    seed("Opposite", [-1.0], 50)
    result = PostgresRetriever(engine).search(
        query(), RetrievalOptions(top_k=20, min_similarity=-1)
    )
    assert [item.chunk.chunk_id.int for item in result.hits] == [10, 20, 30, 40, 50]
    assert [item.score for item in result.hits] == pytest.approx(
        [1.0, 1.0, 0.6, 0.0, -1.0], abs=1e-6
    )
    assert [item.rank for item in result.hits] == [1, 2, 3, 4, 5]
    first.source.parsed.validate_chunk(result.hits[0].chunk)
    assert RetrievalResult.model_validate_json(result.model_dump_json()) == result
    limited = PostgresRetriever(engine).search(query(), RetrievalOptions(top_k=1))
    assert limited.hits[0].chunk.chunk_id.int == 10
    assert '"vector":' not in result.model_dump_json()


@pytest.mark.parametrize("minimum,expected", [(1.0, [1]), (0.0, [1, 2]), (-1.0, [1, 2, 3])])
def test_inclusive_thresholds(engine, seed, minimum, expected):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    seed("Aligned", [1.0], 1)
    seed("Orthogonal", [0.0, 1.0], 2)
    seed("Opposite", [-1.0], 3)
    result = PostgresRetriever(engine).search(query(), RetrievalOptions(min_similarity=minimum))
    assert [item.chunk.chunk_id.int for item in result.hits] == expected


def test_filters_apply_before_limit_and_abstract_metadata_stays_abstract(engine, seed):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    pdf = seed("PDF aligned", [1.0], 1)
    abstract = seed("中文 α🙂 abstract only.", [0.6, 0.8], 2, "pubmed")
    retriever = PostgresRetriever(engine)
    result = retriever.search(
        query(),
        RetrievalOptions(
            top_k=1,
            source_types=["pubmed"],
            content_scopes=["abstract"],
            document_ids=[abstract.source.parsed.document.document_id],
        ),
    )
    assert len(result.hits) == 1 and result.hits[0].chunk.chunk_id.int == 2
    abstract.source.parsed.validate_chunk(result.hits[0].chunk)
    assert result.hits[0].document.pmid == "102"
    assert result.hits[0].document.content_scope == "abstract"
    assert retriever.search(query(), RetrievalOptions(document_ids=[uuid4()])).hits == []
    assert (
        retriever.search(
            query(), RetrievalOptions(source_types=["pdf"], content_scopes=["abstract"])
        ).hits
        == []
    )
    assert (
        retriever.search(
            query(), RetrievalOptions(document_ids=[pdf.source.parsed.document.document_id])
        )
        .hits[0]
        .chunk.chunk_id.int
        == 1
    )


def test_empty_corpus_is_a_successful_empty_result(engine, store):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    assert PostgresRetriever(engine).search(query(), RetrievalOptions()).hits == []


@pytest.mark.parametrize("kind", ["legacy", "source_units", "missing_chunk"])
def test_selected_corruption_is_an_error_not_zero_hits(
    engine, store, source_factory, prepared_factory, kind
):
    from sqlalchemy import delete, update

    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

    original = prepared_factory(source_factory(text="Long enough evidence."), max_tokens=13)
    store.save(original)
    with engine.begin() as connection:
        if kind == "legacy":
            connection.execute(update(DocumentRecord).values(ingestion_metadata=None))
        elif kind == "source_units":
            connection.execute(update(DocumentRecord).values(source_units=[{"bad": "data"}]))
        else:
            connection.execute(delete(ChunkRecord).where(ChunkRecord.chunk_index == 2))
    with pytest.raises(RetrievalError, match="^retrieval_corrupt$"):
        PostgresRetriever(engine).search(query(), RetrievalOptions())


def test_real_read_only_repeatable_read_and_three_data_queries(engine, seed):
    from sqlalchemy import event

    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    seed("Source A", [1.0], 1)
    seed("Source B", [1.0], 2)
    data_queries, properties = [], []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            data_queries.append(statement)
        if " <=> " in statement:
            properties.append(
                (
                    connection.get_isolation_level(),
                    connection.exec_driver_sql("SHOW transaction_read_only").scalar_one(),
                )
            )

    event.listen(engine, "before_cursor_execute", observe)
    try:
        parent = engine.execution_options(isolation_level="READ COMMITTED")
        assert len(PostgresRetriever(parent).search(query(), RetrievalOptions()).hits) == 2
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert properties == [("REPEATABLE READ", "on")]
    assert len(data_queries) == 3
    assert parent.get_execution_options()["isolation_level"] == "READ COMMITTED"


def test_candidate_and_hydration_share_snapshot_during_concurrent_update(engine, seed):
    from sqlalchemy import event, update

    from clinical_agent.adapters.postgres.models import DocumentRecord
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    original = seed("Original source", [1.0], 1)
    changed = []

    def after_candidate(connection, cursor, statement, parameters, context, executemany):
        if " <=> " in statement and not changed:
            changed.append(True)
            with engine.begin() as writer:
                writer.execute(update(DocumentRecord).values(title="Concurrent correction"))

    event.listen(engine, "after_cursor_execute", after_candidate)
    try:
        result = PostgresRetriever(engine).search(query(), RetrievalOptions())
    finally:
        event.remove(engine, "after_cursor_execute", after_candidate)
    assert changed and result.hits[0].document.title == original.source.parsed.document.title


def test_database_error_cannot_become_empty_result(engine, store):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError

    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

    def fail(connection, cursor, statement, parameters, context, executemany):
        if " <=> " in statement:
            raise OperationalError("synthetic retrieval", None, RuntimeError("private-password"))

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RetrievalError, match="^retrieval_failed$") as error:
            PostgresRetriever(engine).search(query(), RetrievalOptions())
        assert "private" not in str(error.value)
    finally:
        event.remove(engine, "before_cursor_execute", fail)


@pytest.mark.external
def test_actual_e5_query_and_document_vectors_return_traceable_hits(
    engine, store, tmp_path, pdf_factory, monkeypatch
):
    import socket

    from clinical_agent.adapters.embedding import REVISION, LocalModelConfig, load_local_embedder
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.ingestion import ImportRequest
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalRequest

    original_connect = socket.socket.connect

    def local_only(connection, address):
        assert address[0] in {"127.0.0.1", "::1"}
        return original_connect(connection, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)
    embedder = load_local_embedder(
        LocalModelConfig(snapshot_dir=ROOT / "models/multilingual-e5-base" / REVISION)
    )
    path = pdf_factory(tmp_path / "source.pdf", ("Evidence from a synthetic randomized trial.",))
    ingested = IngestionService(
        reader=OfflineReader(tmp_path / "cache"), embedder=embedder, store=store
    ).ingest(
        ImportRequest(
            source_type="pdf",
            path=path,
            allowed_root=tmp_path,
            ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        )
    )
    assert ingested.entries[0].status == "imported"
    result = RetrievalService(embedder=embedder, retriever=PostgresRetriever(engine)).retrieve(
        RetrievalRequest(
            question="What evidence does the synthetic trial provide?",
            options=RetrievalOptions(min_similarity=-1),
        )
    )
    assert len(result.hits) == 1
    assert result.hits[0].document.document_id == ingested.entries[0].document_id
    stored = store.load(ingested.entries[0].document_id)
    stored.source.parsed.validate_chunk(result.hits[0].chunk)
    assert result.hits[0].score_type == "cosine_similarity"
    assert '"vector":' not in result.model_dump_json()
    report = {
        "model_revision": REVISION,
        "dimension": result.embedding_info.dimension,
        "hit_count": len(result.hits),
        "score": result.hits[0].score,
        "score_type": result.hits[0].score_type,
        "content_scope": result.hits[0].document.content_scope,
        "document_id": str(result.hits[0].document.document_id),
        "chunk_id": str(result.hits[0].chunk.chunk_id),
        "slice_rebuilt": True,
    }
    (ROOT / ".artifacts/p1-08-20261027-01/real-retrieval-result.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
