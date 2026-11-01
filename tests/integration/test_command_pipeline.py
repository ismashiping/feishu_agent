"""Opt-in CLI composition with actual local E5/PostgreSQL and explicit HTTP stub."""

import json
import os
import socket
from functools import partial
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.external]


@pytest.mark.usefixtures("release_model_memory")
def test_cli_ingestion_and_retired_scope_with_real_model_database(
    tmp_path,
    pdf_factory,
    monkeypatch,
    capsys,
):
    from sqlalchemy import delete, func, select, text

    from clinical_agent import cli
    from clinical_agent.db.connection import DatabaseSettings, database_engine
    from clinical_agent.db.models import ChunkRecord, DocumentRecord
    from clinical_agent.integrations import llm as llm_api
    from clinical_agent.rag import embedding

    settings = DatabaseSettings()
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    model_dir = (
        Path(__file__).resolve().parents[2] / "models/multilingual-e5-base" / embedding.REVISION
    )
    assert model_dir.is_dir()
    monkeypatch.setenv("LLM_API_KEY", "synthetic-not-a-real-key")
    monkeypatch.setenv("LLM_MODEL", "protocol-fixture")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.test/v1")
    original_connect = socket.socket.connect

    def loopback_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
            raise AssertionError("Only the explicit local test database may be contacted")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback_only)

    # Reuse one actual model instance across CLI invocations inside this test process only.
    load = embedding.load_local_embedder
    loaded = []

    def cached(config):
        if not loaded:
            loaded.append(load(config))
        return loaded[0]

    monkeypatch.setattr(embedding, "load_local_embedder", cached)
    calls = []

    def handler(request):
        assert request.url.host == "api.example.test"
        context = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(context)
        if "evidence" not in context:
            raw = json.dumps(
                {
                    "question_type": "other",
                    "pico": dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
                    "terms": [],
                    "ambiguities": [],
                }
            )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"finish_reason": "stop", "message": {"role": "assistant", "content": raw}}
                    ]
                },
            )
        raw = json.dumps(
            {
                "claims": [
                    {
                        "text": "This fictional example does not establish efficacy.",
                        "kind": "uncertainty",
                        "evidence_chunk_ids": [context["evidence"][0]["chunk_id"]],
                        "limitations": ["Synthetic teaching data only."],
                    }
                ]
            }
        )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"role": "assistant", "content": raw}}
                ]
            },
        )

    monkeypatch.setattr(
        llm_api,
        "open_llm",
        partial(llm_api.open_llm, transport=httpx.MockTransport(handler)),
    )

    pdf = pdf_factory(
        tmp_path / "example.pdf",
        texts=(
            "This fictional teaching example has no control group and cannot establish efficacy.",
        ),
    )

    def ingest(path, kind):
        code = cli.main(
            [
                "ingest",
                "--source-type",
                kind,
                "--path",
                str(path),
                "--allowed-root",
                str(tmp_path),
                "--snapshot-dir",
                str(tmp_path / "snapshots"),
                "--model-dir",
                str(model_dir),
            ]
        )
        captured = capsys.readouterr()
        assert code == 0, captured.err
        return json.loads(captured.out)["result"]["entries"][0]

    with database_engine(settings) as engine:
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == "oa3003_0011"
            )
            assert connection.scalar(select(func.count()).select_from(DocumentRecord)) == 0
        try:
            first = ingest(pdf, "pdf")
            again = ingest(pdf, "pdf")
            assert first["status"] == "imported"
            assert (
                again["status"] == "already_present"
                and again["document_id"] == first["document_id"]
            )
            with pytest.raises(SystemExit) as rejected:
                cli.main(["ask", "--scope", "local", "--question", "test"])
            assert rejected.value.code == 2
            assert len(calls) == 0
            with engine.connect() as connection:
                documents = connection.scalar(select(func.count()).select_from(DocumentRecord))
                chunks = connection.scalar(select(func.count()).select_from(ChunkRecord))
            assert documents == 1 and chunks == 1
            report = {
                "cli": "main with production composition",
                "embedding": "real fixed E5 CPU; reused within test",
                "database": "real PostgreSQL/pgvector",
                "llm": "HTTPX MockTransport; NOT real model API",
                "ingestion_statuses": [first["status"], again["status"]],
                "documents": documents,
                "chunks": chunks,
                "retired_scope_exit_code": rejected.value.code,
                "http_requests": len(calls),
                "question_generation": "not run: local retired",
            }
            output = Path(os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"])
            (output / "real-cli-result.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        finally:
            with engine.begin() as connection:
                connection.execute(delete(DocumentRecord))
