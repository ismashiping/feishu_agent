"""Opt-in CLI composition with actual local E5/PostgreSQL and explicit HTTP stub."""

import json
import os
import socket
from functools import partial
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.external]


def test_cli_ingestion_and_rag_with_real_model_database(
    tmp_path,
    pdf_factory,
    monkeypatch,
    capsys,
):
    from sqlalchemy import delete, func, select, text

    from clinical_agent import cli
    from clinical_agent.adapters import deepseek, embedding
    from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
    from clinical_agent.adapters.postgres.models import ChunkRecord, DocumentRecord

    settings = DatabaseSettings()
    assert settings.host == "127.0.0.1" and settings.name.startswith("clinical_agent_test_")
    assert os.environ.get("CLINICAL_AGENT_DB_ALLOW_TEST_RESET") == "1"
    model_dir = (
        Path(__file__).resolve().parents[2] / "models/multilingual-e5-base" / embedding.REVISION
    )
    assert model_dir.is_dir()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-not-a-real-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "protocol-fixture")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
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
        assert request.url.host == "api.deepseek.com"
        context = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(context)
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
        deepseek,
        "deepseek_generator",
        partial(deepseek.deepseek_generator, transport=httpx.MockTransport(handler)),
    )

    pdf = pdf_factory(
        tmp_path / "example.pdf",
        texts=(
            "This fictional teaching example has no control group and cannot establish efficacy.",
        ),
    )
    xml = tmp_path / "example.xml"
    xml.write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation>
        <PMID>1234567890</PMID><Article><ArticleTitle>Synthetic teaching example</ArticleTitle>
        <Abstract><AbstractText>This fictional example cannot establish efficacy.
        </AbstractText></Abstract>
        </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
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
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "p107_0002"
            assert connection.scalar(select(func.count()).select_from(DocumentRecord)) == 0
        try:
            first = ingest(pdf, "pdf")
            again = ingest(pdf, "pdf")
            article = ingest(xml, "pubmed_xml")
            assert first["status"] == article["status"] == "imported"
            assert (
                again["status"] == "already_present"
                and again["document_id"] == first["document_id"]
            )
            code = cli.main(
                [
                    "ask",
                    "--question",
                    "What limitations does this fictional example have?",
                    "--model-dir",
                    str(model_dir),
                    "--top-k",
                    "2",
                    "--min-similarity",
                    "-1",
                ]
            )
            captured = capsys.readouterr()
            assert code == 0, captured.err
            answer = json.loads(captured.out)
            assert answer["status"] == "answered" and len(calls) == 1
            assert answer["claims"][0]["evidence_chunk_ids"][0] in {
                item["chunk_id"] for source in answer["sources"] for item in source["evidence"]
            }
            assert "source_uri" not in captured.out
            with engine.connect() as connection:
                documents = connection.scalar(select(func.count()).select_from(DocumentRecord))
                chunks = connection.scalar(select(func.count()).select_from(ChunkRecord))
            assert documents == 2 and chunks == 2
            report = {
                "cli": "main with production composition",
                "embedding": "real fixed E5 CPU; reused within test",
                "database": "real PostgreSQL/pgvector",
                "llm": "HTTPX MockTransport; NOT real DeepSeek",
                "ingestion_statuses": [first["status"], again["status"], article["status"]],
                "documents": documents,
                "chunks": chunks,
                "answer_status": answer["status"],
                "sources": len(answer["sources"]),
                "http_requests": len(calls),
                "citation_membership": "passed",
            }
            output = Path(os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"])
            (output / "real-cli-result.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        finally:
            with engine.begin() as connection:
                connection.execute(delete(DocumentRecord))
