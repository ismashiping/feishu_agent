"""Opt-in real PostgreSQL tests; require a dedicated explicitly resettable test database."""

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
REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"


def _migration(engine, action, target=None):
    from alembic.config import Config

    from alembic import command

    config = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        if target is None:
            getattr(command, action)(config)
        else:
            getattr(command, action)(config, target)


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    from sqlalchemy import text

    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine

    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    settings = DatabaseSettings()
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    with database_engine(settings) as engine:
        _migration(engine, "upgrade", "head")
        with engine.connect() as connection:
            report = {
                "postgres_version": connection.scalar(text("SELECT version()")),
                "vector_version": connection.scalar(
                    text("SELECT extversion FROM pg_extension WHERE extname='vector'")
                ),
                "server_encoding": connection.scalar(text("SHOW server_encoding")),
                "statement_timeout": connection.scalar(text("SHOW statement_timeout")),
                "lock_timeout": connection.scalar(text("SHOW lock_timeout")),
                "revision": connection.scalar(text("SELECT version_num FROM alembic_version")),
            }
        assert report["vector_version"] == "0.8.7"
        assert report["postgres_version"].startswith("PostgreSQL 16.")
        assert report["revision"] == "p107_0002"
        evidence = Path(
            os.environ.get(
                "CLINICAL_AGENT_TEST_EVIDENCE_DIR",
                str(tmp_path_factory.mktemp("postgres-evidence")),
            )
        )
        output = evidence / "database-version.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        yield engine


@pytest.fixture
def session(engine):
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        try:
            yield session
        finally:
            session.rollback()


def _document(source="pdf", **overrides):
    from clinical_agent.adapters.postgres.models import DocumentRecord

    identity = uuid4()
    body = "甲α🙂"
    data = dict(
        document_id=identity,
        source_type=source,
        content_hash=identity.hex * 2,
        source_uri="file:///synthetic.pdf",
        source_url=None,
        content_scope="extracted_text",
        title="Synthetic source",
        title_origin="filename",
        authors=["Example, Ada", "研究协作组"],
        publication_date={
            "precision": "year",
            "year": 2020,
            "month": None,
            "day": None,
            "raw": "2020",
        },
        journal=None,
        doi=None,
        pmid=None,
        abstract=None,
        text=body,
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        source_units=[{"page": 1, "text": body, "normalization_version": "pdf-text-v1"}],
    )
    if source == "pubmed":
        data.update(
            source_uri="file:///synthetic.xml",
            content_scope="abstract",
            text=None,
            abstract=body,
            pmid="1234567890",
            title_origin="pubmed_metadata",
            source_units=[
                {
                    "index": 1,
                    "text": body,
                    "label": "RESULTS",
                    "category": None,
                    "start": 0,
                    "end": 3,
                    "normalization_version": "pubmed-xml-text-v1",
                }
            ],
        )
    return DocumentRecord(**{**data, **overrides})


def _chunk(document, **overrides):
    from clinical_agent.adapters.postgres.models import ChunkRecord

    data = dict(
        chunk_id=uuid4(),
        document_id=document.document_id,
        source_type=document.source_type,
        chunk_index=1,
        text="甲α🙂",
        location_kind="pdf_page" if document.source_type == "pdf" else "abstract",
        page=1 if document.source_type == "pdf" else None,
        section=None if document.source_type == "pdf" else "RESULTS",
        start_offset=0,
        end_offset=3,
        model_id="intfloat/multilingual-e5-base",
        model_revision=REVISION,
        tokenizer_revision=REVISION,
        embedding_dimension=768,
        normalized=True,
        chunking_version="source-unit-v1",
        document_prefix="passage: ",
        token_count=8,
        max_tokens=512,
        chunking_policy={"max_tokens": 512},
        embedding=[1.0] + [0.0] * 767,
    )
    return ChunkRecord(**{**data, **overrides})


def test_migrations_upgrade_downgrade_reupgrade_and_no_drift(engine):
    from sqlalchemy import inspect, text

    _migration(engine, "upgrade", "head")
    _migration(engine, "check")
    try:
        _migration(engine, "downgrade", "base")
        assert not {"documents", "chunks"} & set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT extversion FROM pg_extension WHERE extname='vector'")
                )
                == "0.8.7"
            )
    finally:
        _migration(engine, "upgrade", "head")
    _migration(engine, "check")


@pytest.mark.parametrize("source", ["pdf", "pubmed"])
def test_commit_roundtrip_survives_other_session_and_cascade(engine, source):
    from sqlalchemy import delete, select
    from sqlalchemy.orm import Session

    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord

    document = _document(source)
    chunk = _chunk(document)
    doc_id, chunk_id = document.document_id, chunk.chunk_id
    units, publication_date = document.source_units, document.publication_date
    expected_identity = document.content_hash if source == "pdf" else document.pmid
    try:
        with Session(engine) as writer, writer.begin():
            writer.add(document)
            writer.flush()
            writer.add(chunk)
        with Session(engine) as reader:
            saved = reader.get(DocumentRecord, doc_id)
            saved_chunk = reader.get(ChunkRecord, chunk_id)
            assert saved.source_identity == expected_identity
            assert saved.source_units == units and saved.publication_date == publication_date
            assert saved.authors == ["Example, Ada", "研究协作组"]
            assert saved.source_url is saved.doi is saved.journal is None
            assert saved.ingestion_time == datetime(2026, 10, 27, tzinfo=UTC)
            assert saved_chunk.text == saved.source_units[0]["text"]
            assert saved_chunk.end_offset - saved_chunk.start_offset == len("甲α🙂")
            assert isinstance(saved_chunk.embedding, list)
            assert saved_chunk.embedding == [1.0] + [0.0] * 767
            assert reader.scalar(
                select(ChunkRecord.embedding.cosine_distance([1.0] + [0.0] * 767)).where(
                    ChunkRecord.chunk_id == chunk_id
                )
            ) == pytest.approx(0.0)
            assert reader.scalar(
                select(ChunkRecord.embedding.cosine_distance([0.0, 1.0] + [0.0] * 766)).where(
                    ChunkRecord.chunk_id == chunk_id
                )
            ) == pytest.approx(1.0)
        with engine.begin() as connection:
            connection.execute(delete(DocumentRecord).where(DocumentRecord.document_id == doc_id))
        with Session(engine) as reader:
            assert reader.get(ChunkRecord, chunk_id) is None
    finally:
        with engine.begin() as connection:
            connection.execute(delete(DocumentRecord).where(DocumentRecord.document_id == doc_id))


@pytest.mark.parametrize("source", ["pdf", "pubmed"])
def test_source_identity_unique_across_uuid_path_and_content(session, source):
    from sqlalchemy.exc import IntegrityError

    first = _document(source)
    session.add(first)
    session.flush()
    other = _document(source, source_uri="file:///different-file")
    if source == "pdf":
        other.content_hash = first.content_hash
    session.add(other)
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.diag.constraint_name == "uq_documents_source"


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " "),
        ("source_type", "unknown"),
        ("content_hash", "bad"),
        ("pmid", "0123"),
        ("publication_date", []),
        ("authors", {}),
        ("source_units", []),
        ("content_scope", "abstract"),
        ("title_origin", "pubmed_metadata"),
    ],
)
def test_invalid_document_rejected_by_database(session, field, value):
    from sqlalchemy.exc import IntegrityError

    session.add(_document(**{field: value}))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize(
    "field,value",
    [
        ("chunk_index", 0),
        ("text", " "),
        ("start_offset", -1),
        ("end_offset", 4),
        ("page", None),
        ("page", 0),
        ("location_kind", "abstract"),
        ("source_type", "pubmed"),
        ("model_id", "other"),
        ("model_revision", "main"),
        ("tokenizer_revision", "other"),
        ("normalized", False),
        ("embedding_dimension", 384),
        ("chunking_version", "other"),
        ("document_prefix", "query: "),
        ("token_count", 513),
        ("max_tokens", 513),
        ("chunking_policy", []),
        ("embedding", [0.0] * 768),
        ("document_id", uuid4()),
    ],
)
def test_invalid_chunk_rejected_by_database(session, field, value):
    from sqlalchemy.exc import IntegrityError

    document = _document()
    session.add(document)
    session.flush()
    session.add(_chunk(document, **{field: value}))
    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_chunk_position_is_rejected(session):
    from sqlalchemy.exc import IntegrityError

    document = _document()
    session.add(document)
    session.flush()
    session.add(_chunk(document))
    session.flush()
    session.add(_chunk(document))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.diag.constraint_name == "uq_chunks_position"


@pytest.mark.parametrize("vector", ["[1,0]", "[NaN]", "[Infinity]"])
def test_server_rejects_invalid_vectors_without_python_type_adapter(session, vector):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    document = _document()
    session.add(document)
    session.flush()
    chunk = _chunk(document)
    session.add(chunk)
    session.flush()
    with pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE chunks SET embedding=CAST(:vector AS vector) WHERE chunk_id=:id"),
            {"vector": vector, "id": chunk.chunk_id},
        )


def test_invalid_chunk_rolls_back_the_new_document(engine):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from clinical_agent.adapters.postgres.models import DocumentRecord

    document = _document()
    identity = document.document_id
    with pytest.raises(IntegrityError):
        with Session(engine) as writer, writer.begin():
            writer.add(document)
            writer.flush()
            writer.add(_chunk(document, end_offset=999))
    with Session(engine) as reader:
        assert reader.get(DocumentRecord, identity) is None


def test_concurrent_source_uniqueness_is_enforced_by_database(engine):
    from sqlalchemy import delete, func, select
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from clinical_agent.adapters.postgres.models import DocumentRecord

    content_hash = uuid4().hex * 2
    barrier = threading.Barrier(2, timeout=5)

    def write():
        with Session(engine) as session:
            session.add(_document(content_hash=content_hash))
            barrier.wait()
            try:
                session.commit()
                return "committed"
            except IntegrityError as error:
                session.rollback()
                return error.orig.diag.constraint_name

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: write(), range(2)))
        assert sorted(outcomes) == ["committed", "uq_documents_source"]
        with Session(engine) as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(DocumentRecord)
                    .where(DocumentRecord.content_hash == content_hash)
                )
                == 1
            )
    finally:
        with engine.begin() as connection:
            connection.execute(
                delete(DocumentRecord).where(DocumentRecord.content_hash == content_hash)
            )


def test_same_file_uri_does_not_merge_different_pdf_content(session):
    first, second = _document(), _document()
    assert first.source_uri == second.source_uri
    session.add_all([first, second])
    session.flush()
    assert first.source_identity != second.source_identity


def test_composite_fk_rejects_parent_source_even_when_child_location_is_valid(session):
    from sqlalchemy.exc import IntegrityError

    document = _document()
    session.add(document)
    session.flush()
    session.add(_chunk(document, source_type="pubmed", location_kind="abstract", page=None))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.diag.constraint_name == "fk_chunks_document_source"


@pytest.mark.parametrize(
    "field,value",
    [
        ("pmid", None),
        ("content_scope", "full_text"),
        ("title_origin", "filename"),
    ],
)
def test_pubmed_specific_document_constraints(session, field, value):
    from sqlalchemy.exc import IntegrityError

    session.add(_document("pubmed", **{field: value}))
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize(
    "overrides,constraint",
    [
        ({"embedding": [1.1] + [0.0] * 767}, "ck_chunks_norm"),
        ({"token_count": 0}, "ck_chunks_tokens"),
    ],
)
def test_norm_and_token_constraints_independently(session, overrides, constraint):
    from sqlalchemy.exc import IntegrityError

    document = _document()
    session.add(document)
    session.flush()
    session.add(_chunk(document, **overrides))
    with pytest.raises(IntegrityError) as error:
        session.flush()
    assert error.value.orig.diag.constraint_name == constraint
