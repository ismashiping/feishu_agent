"""Opt-in actual Uvicorn TCP + E5 + PostgreSQL; explicitly stubbed DeepSeek HTTP."""

import json
import os
import socket
import threading
import time
from functools import partial
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.external]


def test_real_http_api_ingestion_and_question(tmp_path, pdf_factory, monkeypatch):
    import uvicorn
    from sqlalchemy import delete, func, select, text

    from clinical_agent.adapters import deepseek, embedding
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord
    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings

    database = DatabaseSettings()
    assert database.host == "127.0.0.1" and database.name.startswith("clinical_agent_test_")
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    model_dir = (
        Path(__file__).resolve().parents[2] / "models/multilingual-e5-base" / embedding.REVISION
    )
    assert model_dir.is_dir()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-api-test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "protocol-fixture")
    connect = socket.socket.connect

    def loopback_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
            raise AssertionError("Only local test infrastructure may be contacted")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", loopback_only)
    loaded = []
    load = embedding.load_local_embedder

    def observed_load(config):
        loaded.append(config.snapshot_dir)
        return load(config)

    monkeypatch.setattr(embedding, "load_local_embedder", observed_load)
    calls = []

    def handler(request):
        context = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(context)
        raw = json.dumps(
            {
                "claims": [
                    dict(
                        text="This fictional example cannot establish efficacy.",
                        kind="uncertainty",
                        evidence_chunk_ids=[context["evidence"][0]["chunk_id"]],
                        limitations=["Synthetic teaching data only."],
                    )
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
        deepseek,
        "deepseek_generator",
        partial(deepseek.deepseek_generator, transport=httpx.MockTransport(handler)),
    )
    pdf_factory(
        tmp_path / "sample.pdf",
        texts=(
            "This fictional teaching example has no control group and cannot establish efficacy.",
        ),
    )
    (tmp_path / "sample.xml").write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation>
        <PMID>1234567890</PMID><Article><ArticleTitle>Synthetic API example</ArticleTitle>
        <Abstract><AbstractText>This fictional example cannot establish efficacy.</AbstractText>
        </Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
    )
    settings = ApiSettings(
        model_dir=model_dir, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    app = create_app(settings=settings)
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=0,
        lifespan="on",
        loop="asyncio",
        http="h11",
        ws="none",
        log_config=None,
        access_log=False,
        log_level="warning",
        limit_concurrency=8,
    )
    server = uvicorn.Server(config)
    errors = []
    with socket.socket() as listener, database_engine(database) as engine:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "p107_0002"
            assert connection.scalar(select(func.count()).select_from(DocumentRecord)) == 0

        def run():
            try:
                server.run(sockets=[listener])
            except BaseException as error:
                errors.append(type(error).__name__)

        thread = threading.Thread(target=run, name="api-uvicorn-test")
        thread.start()
        try:
            deadline = time.monotonic() + 150
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert server.started and not errors, "Uvicorn startup did not complete"
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=90, trust_env=False
            ) as client:
                assert client.get("/health/live").status_code == 200
                assert client.get("/health/ready").status_code == 200
                statuses = []
                for path, kind in [
                    ("sample.pdf", "pdf"),
                    ("sample.pdf", "pdf"),
                    ("sample.xml", "pubmed_xml"),
                ]:
                    response = client.post(
                        "/v1/documents/import", json={"source_type": kind, "relative_path": path}
                    )
                    assert response.status_code == 200, response.json().get("error_code")
                    statuses.append(response.json()["result"]["entries"][0]["status"])
                assert statuses == ["imported", "already_present", "imported"]
                response = client.post(
                    "/v1/questions",
                    json={
                        "question": "What limits does this fictional example have?",
                        "options": {"top_k": 2, "min_similarity": -1},
                    },
                )
                assert response.status_code == 200, response.json().get("error_code")
                answer = response.json()
                assert (
                    answer["status"] == "answered"
                    and answer["request_id"] == response.headers["x-request-id"]
                )
                assert answer["claims"][0]["evidence_chunk_ids"][0] in {
                    item["chunk_id"] for source in answer["sources"] for item in source["evidence"]
                }
                assert "source_uri" not in response.text and len(loaded) == len(calls) == 1
                with engine.connect() as connection:
                    documents = connection.scalar(select(func.count()).select_from(DocumentRecord))
                    chunks = connection.scalar(select(func.count()).select_from(ChunkRecord))
                assert documents == chunks == 2
                report = {
                    "transport": "real loopback TCP / Uvicorn 0.54.0 / FastAPI 0.162.0",
                    "model_loads": len(loaded),
                    "embedding": "real fixed local E5 CPU",
                    "database": "real PostgreSQL/pgvector",
                    "llm": "HTTPX MockTransport; NOT real DeepSeek",
                    "ingestion_statuses": statuses,
                    "documents": documents,
                    "chunks": chunks,
                    "answer_status": answer["status"],
                    "http_llm_calls": len(calls),
                    "citation_membership": "passed",
                }
                Path(
                    os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"], "real-api-result.json"
                ).write_text(json.dumps(report, indent=2), encoding="utf-8")
        finally:
            server.should_exit = True
            thread.join(30)
            assert not thread.is_alive(), "API did not shut down cleanly"
            with engine.begin() as connection:
                connection.execute(delete(DocumentRecord))
        assert errors == []
