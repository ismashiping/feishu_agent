"""Real PostgreSQL FTS/pgvector/migrations; synthetic vectors isolate ranking behavior."""

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).parents[2]
CASES = json.loads((ROOT / "tests/fixtures/hybrid/cases.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.database


def migrate(engine, action, target="head"):
    from alembic.config import Config

    from alembic import command

    config = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, action)(config, target)


@pytest.fixture(scope="module")
def engine():
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine

    settings = DatabaseSettings()
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    with database_engine(settings) as engine:
        migrate(engine, "upgrade")
        yield engine


@pytest.fixture
def seed(engine, source_factory, prepared_factory):
    from sqlalchemy import delete

    from clinical_agent.adapters.postgres.models import DocumentRecord
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.domain.ingestion import PreparedIngestion

    prepared = []

    def save(text, direction, identity, **kwargs):
        value = prepared_factory(source_factory(text=text, **kwargs)).model_dump()
        for branch in [value["chunking"]["chunks"][0], value["embedded"][0]]:
            branch["evidence"]["chunk_id"] = UUID(int=identity)
        value["embedded"][0]["vector"] = direction + [0.0] * (768 - len(direction))
        item = PreparedIngestion.model_validate(value)
        PostgresStore(engine).save(item)
        prepared.append(item)
        return item

    yield save
    with engine.begin() as connection:
        connection.execute(delete(DocumentRecord))


def query():
    from clinical_agent.domain.embedding import QueryEmbedding
    from clinical_agent.domain.retrieval import retrieval_embedding_info

    return QueryEmbedding(embedding_info=retrieval_embedding_info(), vector=[1.0] + [0.0] * 767)


def test_fixed_three_mode_comparison_and_source_chain(engine, seed, tmp_path):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    for row in CASES["documents"]:
        seed(row["text"], row["vector"], row["id"])
    retriever = PostgresRetriever(engine)
    report = {}
    for mode in ["keyword", "vector", "hybrid"]:
        options = RetrievalOptions(mode=mode, top_k=CASES["top_k"])
        result = retriever.search_hybrid(
            CASES["query"], None if mode == "keyword" else query(), options, timeout_seconds=10
        )
        identities = [h.chunk.chunk_id.int for h in result.hits]
        assert identities == CASES["expected"][mode]
        assert 1 in identities
        assert all(
            h.chunk.source_metadata.content_hash == h.document.content_hash for h in result.hits
        )
        report[mode] = result.model_dump(mode="json")
    (tmp_path / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    from uuid import uuid4

    from clinical_agent.application.research import ResearchService
    from clinical_agent.application.retrieval import RetrievalService
    from clinical_agent.domain.research import QuestionRequest

    class Embedder:
        def embed_query(self, question):
            return query()

    class Generator:
        def generate(self, context, *, timeout_seconds):
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": "Only supplied synthetic evidence.",
                            "kind": "uncertainty",
                            "evidence_chunk_ids": [str(context.evidence[0].chunk_id)],
                            "limitations": [],
                        }
                    ]
                }
            )

    service = ResearchService(
        retriever=RetrievalService(
            embedder=Embedder(), retriever=retriever, hybrid_retriever=retriever
        ),
        generator=Generator(),
    )
    answer = service.answer(
        QuestionRequest(
            request_id=uuid4(), question=CASES["query"], options=RetrievalOptions(mode="hybrid")
        )
    )
    assert answer.status == "answered" and answer.local_retrieval_strategy == "rrf-v1"
    assert answer.claims[0].evidence_chunk_ids == [UUID(int=1)]
    assert answer.local_channel_status == {"keyword": "ok", "vector": "ok"}


def test_migration_backfills_keeps_ids_and_index_on_reupgrade(engine, seed):
    from sqlalchemy import text

    item = seed("aspirin trial", [1.0], 10)
    migrate(engine, "downgrade", "p107_0002")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM chunks")) == 1
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

    try:
        with pytest.raises(RetrievalError, match="retrieval_failed"):
            PostgresRetriever(engine).search_hybrid(
                "aspirin", None, RetrievalOptions(mode="keyword"), timeout_seconds=10
            )
    finally:
        migrate(engine, "upgrade")
    with engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT search_vector @@ plainto_tsquery('simple','aspirin') "
                "FROM chunks WHERE chunk_id=:id"
            ),
            {"id": UUID(int=10)},
        )
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE indexname='ix_chunks_search_vector' "
                    "AND indexdef LIKE '%USING gin%'"
                )
            )
            == 1
        )
        assert (
            connection.scalar(
                text("SELECT document_id FROM chunks WHERE chunk_id=:id"), {"id": UUID(int=10)}
            )
            == item.source.parsed.document.document_id
        )


@pytest.mark.parametrize("mode", ["keyword", "hybrid"])
def test_filters_and_precise_dates_apply_before_both_limits(engine, seed, mode):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    seed("aspirin unknown date", [1.0], 1)
    kept = seed(
        "aspirin eligible",
        [0.6, 0.8],
        2,
        publication_date={
            "precision": "day",
            "raw": "2020-02-02",
            "year": 2020,
            "month": 2,
            "day": 2,
        },
    )
    options = RetrievalOptions(
        mode=mode,
        top_k=1,
        candidate_limit=1,
        date_from="2020-01-01",
        date_to="2020-12-31",
        document_ids=[kept.source.parsed.document.document_id],
    )
    result = PostgresRetriever(engine).search_hybrid(
        "aspirin", None if mode == "keyword" else query(), options, timeout_seconds=10
    )
    assert [h.chunk.chunk_id.int for h in result.hits] == [2]
    seed(
        "aspirin abstract",
        [1.0],
        3,
        kind="pubmed",
        publication_date={
            "precision": "day",
            "raw": "2020-02-02",
            "year": 2020,
            "month": 2,
            "day": 2,
        },
    )
    filtered = RetrievalOptions(
        mode=mode, top_k=1, candidate_limit=1, source_types=["pubmed"], content_scopes=["abstract"]
    )
    result = PostgresRetriever(engine).search_hybrid(
        "aspirin", None if mode == "keyword" else query(), filtered, timeout_seconds=10
    )
    assert [h.chunk.chunk_id.int for h in result.hits] == [3]


def test_exact_identifiers_and_ascii_language_boundary(engine, seed):
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

    seed(
        "Study without identifier in passage",
        [1.0],
        1,
        kind="pubmed",
        pmid="12345",
        doi="10.1234/example",
    )
    retriever = PostgresRetriever(engine)
    for value in ["12345", "10.1234/example"]:
        assert (
            len(
                retriever.search_hybrid(
                    value, None, RetrievalOptions(mode="keyword"), timeout_seconds=10
                ).hits
            )
            == 1
        )
    with pytest.raises(RetrievalError, match="retrieval_language_unsupported"):
        retriever.search_hybrid(
            "阿司匹林", None, RetrievalOptions(mode="keyword"), timeout_seconds=10
        )


def test_dual_channels_and_hydration_share_one_read_only_snapshot(engine, seed):
    from sqlalchemy import event

    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.retrieval import RetrievalOptions

    seed("aspirin", [1.0], 1)
    connections = []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            connections.append(connection)
            assert connection.get_isolation_level() == "REPEATABLE READ"

    event.listen(engine, "before_cursor_execute", observe)
    try:
        PostgresRetriever(engine).search_hybrid(
            "aspirin", query(), RetrievalOptions(mode="hybrid"), timeout_seconds=10
        )
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert len(connections) == 4 and len({id(c) for c in connections}) == 1
