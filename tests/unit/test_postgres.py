"""PostgreSQL schema/connection contracts without opening a database connection."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", " "),
        ("user", ""),
        ("name", "bad/name"),
        ("name", "a" * 64),
        ("port", 0),
        ("port", 65536),
        ("port", True),
        ("port", 3.4),
        ("password", ""),
    ],
)
def test_database_config_rejects_invalid_values(field, value):
    from clinical_agent.adapters.postgres.connection import DatabaseSettings

    with pytest.raises(ValidationError):
        DatabaseSettings(**{"password": "synthetic-secret", field: value})


def test_database_config_is_explicit_and_password_hidden(monkeypatch, tmp_path):
    from clinical_agent.adapters.postgres.connection import DatabaseSettings

    for name in tuple(os.environ):
        if name.startswith("CLINICAL_AGENT_DB_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("CLINICAL_AGENT_DB_PASSWORD=forbidden-dotenv", encoding="utf-8")
    with pytest.raises(ValidationError):
        DatabaseSettings()
    monkeypatch.setenv("CLINICAL_AGENT_DB_PASSWORD", "synthetic-secret")
    monkeypatch.setenv("CLINICAL_AGENT_DB_PORT", "55433")
    actual = DatabaseSettings()
    assert actual.port == 55433
    assert "synthetic-secret" not in repr(actual)
    assert "synthetic-secret" not in actual.model_dump_json()
    assert actual.password.get_secret_value() == "synthetic-secret"


def test_engine_options_and_finally_dispose(monkeypatch):
    from clinical_agent.adapters.postgres import connection

    seen = []

    class Engine:
        def dispose(self):
            seen.append("disposed")

    def create(url, **kwargs):
        seen.append((url, kwargs))
        return Engine()

    monkeypatch.setattr(connection, "create_engine", create)
    password = "synthetic/@:%secret"
    settings = connection.DatabaseSettings(password=password)
    with pytest.raises(LookupError, match="body failed"):
        with connection.database_engine(settings):
            raise LookupError("body failed")
    url, options = seen[0]
    assert url.drivername == "postgresql+psycopg"
    assert url.password == password and password not in str(url)
    assert options["hide_parameters"] and not options["echo"]
    assert options["pool_size"] == 5 and options["max_overflow"] == 0
    assert options["pool_timeout"] == 5 and options["pool_pre_ping"]
    assert options["connect_args"]["connect_timeout"] == 5
    assert "statement_timeout=10000" in options["connect_args"]["options"]
    assert "lock_timeout=2000" in options["connect_args"]["options"]
    assert seen[-1] == "disposed"


def test_postgres_ddl_and_metadata_are_distinct_from_dtos():
    from pydantic import BaseModel
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from clinical_agent.adapters.postgres.models import Base, ChunkRecord, DocumentRecord

    assert set(Base.metadata.tables) == {
        "documents",
        "chunks",
        "document_versions",
        "update_cursors",
        "update_runs",
        "source_aliases",
        "source_status_events",
        "source_states",
        "online_update_batches",
        "rebuild_runs",
    }
    assert not issubclass(DocumentRecord, BaseModel)
    assert not issubclass(ChunkRecord, BaseModel)
    document = DocumentRecord.__table__
    chunk = ChunkRecord.__table__
    assert document.c.document_id.default is None
    assert document.c.source_identity.computed.persisted
    assert document.c.ingestion_time.type.timezone
    assert chunk.c.embedding.type.dim == 768
    assert {"source_units", "publication_date", "authors"} <= set(document.c.keys())
    ddl = "\n".join(
        str(CreateTable(table).compile(dialect=postgresql.dialect())) for table in (document, chunk)
    )
    assert "VECTOR(768)" in ddl and "JSONB" in ddl
    assert "GENERATED ALWAYS AS" in ddl and "STORED" in ddl
    assert "uq_documents_source" in ddl and "uq_chunks_position" in ddl
    assert "ON DELETE CASCADE" in ddl
    assert "vector_norm(embedding)" in ddl
    assert "end_offset - start_offset = char_length(text)" in ddl
    assert not Base.metadata.tables["chunks"].c.embedding.nullable


def test_offline_migration_is_complete_without_database_config(tmp_path):
    path = ROOT / "alembic.ini"
    assert path.is_file(), "P1-06 migration configuration is not implemented"
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("CLINICAL_AGENT_DB_")
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(path), "upgrade", "head", "--sql"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    sql = result.stdout
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "CREATE TABLE documents" in sql and "CREATE TABLE chunks" in sql
    assert "VECTOR(768)" in sql
    assert "p106_0001" in sql
