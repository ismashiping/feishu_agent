"""HTTP contracts on actual FastAPI, with explicit synthetic application services."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.integration
ID = "12345678-1234-4234-8234-123456789abc"


@pytest.fixture
def setup_api(tmp_path):
    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.domain.ingestion import BatchIngestionResult
    from clinical_agent.domain.research import ResearchAnswer

    events = []

    class Ingestion:
        calls = []

        def ingest(self, request):
            self.calls.append(request)
            return BatchIngestionResult(entries=[])

    class Research:
        calls = []

        def answer(self, request):
            self.calls.append(request)
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                limitations=["未检索到证据"],
                generated_at=datetime.now(UTC),
            )

    services = ServiceBundle(ingestion=Ingestion(), research=Research())

    @contextmanager
    def factory(settings):
        events.append("enter")
        try:
            yield services
        finally:
            events.append("exit")

    settings = ApiSettings(
        model_dir=tmp_path,
        import_root=tmp_path,
        snapshot_dir=tmp_path / "snapshots",
        max_in_flight=1,
    )
    return create_app(settings=settings, runtime_factory=factory), services, events


def test_lifespan_health_and_no_per_request_assembly(setup_api):
    from fastapi.testclient import TestClient

    app, services, events = setup_api
    assert events == []
    with TestClient(app) as client:
        for path in ("/health/live", "/health/ready"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            assert response.json()["request_id"] == response.headers["x-request-id"]
        assert services.research.calls == services.ingestion.calls == []
        assert client.get("/openapi.json").status_code == 200
        assert events == ["enter"]
    assert events == ["enter", "exit"]


def test_question_contract_correlation_and_empty_success(setup_api):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions",
            headers={"X-Request-ID": ID},
            json={"question": "  中文问题  ", "options": {"top_k": 3, "min_similarity": 0.6}},
        )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["request_id"] == ID
    assert response.json()["limitations"] == ["未检索到证据"]
    assert services.research.calls[0].question == "中文问题"
    assert services.research.calls[0].options.top_k == 3


@pytest.mark.parametrize(
    "data",
    [
        {"question": " "},
        {"question": "x" * 4001},
        {"question": 123},
        {"question": "private", "scope": "online"},
        {"question": "private", "options": {"top_k": 0}},
        {"question": "private", "options": {"min_similarity": "nan"}},
        {"question": "private", "api_key": "secret-value"},
        {"question": "private", "request_id": ID},
    ],
)
def test_invalid_inputs_do_not_echo_private_values(setup_api, data):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    with TestClient(app) as client:
        response = client.post("/v1/questions", json=data)
    assert response.status_code == 422 and services.research.calls == []
    assert "private" not in response.text and "secret-value" not in response.text
    assert "input" not in response.json() and response.json()["error_code"] == "invalid_request"


def test_import_uses_only_server_root(setup_api, tmp_path):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    path = tmp_path / "sample.xml"
    path.write_text("synthetic")
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents/import", json={"source_type": "pubmed_xml", "relative_path": path.name}
        )
    assert response.status_code == 200 and response.json()["result"]["entries"] == []
    request = services.ingestion.calls[0]
    assert request.path == path and request.allowed_root == tmp_path
    assert request.ingestion_time.utcoffset() is not None
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize(
    "path", ["../private.pdf", "/private.pdf", "C:/private.pdf", r"C:\private.pdf", "missing.pdf"]
)
def test_invalid_source_paths_fail_without_calling_service(setup_api, path):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents/import", json={"source_type": "pdf", "relative_path": path}
        )
    assert response.status_code in (400, 422) and services.ingestion.calls == []
    assert path not in response.text


@pytest.mark.parametrize(
    "headers,status,code",
    [
        ({"X-Request-ID": "private-value"}, 400, "invalid_request_id"),
        ({"Content-Type": "text/plain"}, 415, "unsupported_media_type"),
        ({"Content-Encoding": "gzip"}, 415, "unsupported_media_type"),
        ({"Content-Length": "20000"}, 413, "request_too_large"),
    ],
)
def test_headers_and_body_limits_are_controlled(setup_api, headers, status, code):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions", content="{}", headers={"Content-Type": "application/json", **headers}
        )
    assert response.status_code == status and response.json()["error_code"] == code
    assert "private-value" not in response.text and not services.research.calls


def test_actual_chunked_body_size_is_checked(setup_api):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions",
            content=iter([b"x" * 9000, b"x" * 9000]),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 413 and not services.research.calls


@pytest.mark.parametrize(
    "fault,status",
    [
        ("retrieval_failed", 503),
        ("retrieval_timeout", 504),
        ("retrieval_corrupt", 500),
        ("generation_failed", 503),
        ("generation_timeout", 504),
        ("model_output_invalid", 502),
        ("citation_invalid", 502),
        ("context_limit", 422),
        ("unknown", 500),
    ],
)
def test_error_mapping_never_publishes_raw_exception(setup_api, fault, status):
    from fastapi.testclient import TestClient

    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalError

    app, services, _ = setup_api

    def fail(request):
        if fault.startswith("retrieval_"):
            raise RetrievalError(fault)
        if fault == "unknown":
            raise RuntimeError("private-original-secret")
        raise ResearchError(fault)

    services.research.answer = fail
    with TestClient(app) as client:
        response = client.post("/v1/questions", json={"question": "private-question"})
    assert response.status_code == status
    assert "private" not in response.text
    assert response.json()["error_code"] == ("internal_error" if fault == "unknown" else fault)


def test_full_answer_source_fields_preserved(setup_api, source_factory, prepared_factory):
    from fastapi.testclient import TestClient

    from clinical_agent.domain.citations import build_answer, parse_draft
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    app, services, _ = setup_api
    prepared = prepared_factory(source_factory(kind="pubmed"))

    def answer(request):
        hit = EvidenceHit(
            chunk=prepared.embedded[0].evidence,
            document=DocumentSummary.from_document(prepared.source.parsed.document),
            score=1.0,
            rank=1,
        )
        result = RetrievalResult(
            options=request.options, embedding_info=retrieval_embedding_info(), hits=[hit]
        )
        raw = json.dumps(
            {
                "claims": [
                    dict(
                        text="合成证据的局限",
                        kind="uncertainty",
                        evidence_chunk_ids=[str(hit.chunk.chunk_id)],
                        limitations=["仅摘要"],
                    )
                ]
            }
        )
        return build_answer(
            request, result, parse_draft(raw, max_bytes=32000), generated_at=datetime.now(UTC)
        )

    services.research.answer = answer
    with TestClient(app) as client:
        response = client.post("/v1/questions", json={"question": "synthetic"})
    assert response.status_code == 200
    assert response.json()["claims"][0]["kind"] == "uncertainty"
    assert response.json()["sources"][0]["content_scope"] == "abstract"
    assert response.json()["sources"][0]["evidence"][0]["location"]["kind"] == "abstract"
    assert "source_uri" not in response.text and "embedding_info" not in response.text


def test_busy_rejects_without_blocking_health_and_recovers(setup_api):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    started, release = threading.Event(), threading.Event()
    original = services.research.answer

    def blocking(request):
        started.set()
        assert release.wait(10)
        return original(request)

    services.research.answer = blocking
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, "/v1/questions", json={"question": "first"})
        try:
            assert started.wait(5)
            assert client.get("/health/live").status_code == 200
            response = client.post("/v1/questions", json={"question": "second"})
            assert response.status_code == 503 and response.json()["error_code"] == "busy"
            assert response.headers["retry-after"] == "1"
        finally:
            release.set()
        assert first.result(5).status_code == 200
        assert client.post("/v1/questions", json={"question": "third"}).status_code == 200


def test_wrong_answer_id_is_internal_error(setup_api):
    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    original = services.research.answer

    def wrong(request):
        answer = original(request)
        answer.request_id = uuid4()
        return answer

    services.research.answer = wrong
    with TestClient(app) as client:
        response = client.post("/v1/questions", json={"question": "private"})
    assert response.status_code == 500 and response.json()["error_code"] == "internal_error"


def test_not_found_and_method_error_are_json(setup_api):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api
    with TestClient(app) as client:
        for path, status in [("/unknown", 404), ("/v1/questions", 405)]:
            response = client.get(path)
            assert response.status_code == status
            UUID(response.json()["request_id"])


def test_openapi_describes_actual_error_contract(setup_api):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    responses = schema["paths"]["/v1/questions"]["post"]["responses"]
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ApiError")


@pytest.mark.parametrize(
    "status", ["imported", "already_present", "needs_update", "conflict", "rejected", "failed"]
)
def test_import_batch_status_is_preserved_in_200(setup_api, tmp_path, status):
    from fastapi.testclient import TestClient

    from clinical_agent.domain.ingestion import BatchIngestionResult

    app, services, _ = setup_api
    (tmp_path / "sample.pdf").write_bytes(b"fixture")
    failed = status in ("rejected", "failed")

    def ingest(request):
        return BatchIngestionResult(
            entries=[
                dict(
                    index=1,
                    status=status,
                    document_id=None if failed else uuid4(),
                    chunk_count=0 if failed else 1,
                    error_code="source_failed" if failed else None,
                )
            ]
        )

    services.ingestion.ingest = ingest
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents/import", json={"source_type": "pdf", "relative_path": "sample.pdf"}
        )
    assert (
        response.status_code == 200 and response.json()["result"]["entries"][0]["status"] == status
    )


@pytest.mark.parametrize(
    "headers",
    [
        [("X-Request-ID", ID), ("X-Request-ID", ID)],
        [("Content-Length", "private-value")],
        [("Content-Length", "-1")],
    ],
)
def test_duplicate_id_and_bad_length_do_not_echo_values(setup_api, headers):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions", content="{}", headers=[("Content-Type", "application/json"), *headers]
        )
    assert response.status_code == 400 and "private-value" not in response.text


def test_malformed_json_no_echo(setup_api):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions",
            content='{"private-secret":',
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 422 and "private-secret" not in response.text


@pytest.mark.asyncio
async def test_without_lifespan_is_not_ready(setup_api):
    import httpx

    app, services, events = setup_api
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code == 503
        response = await client.post("/v1/questions", json={"question": "test"})
        assert response.status_code == 503 and response.json()["error_code"] == "not_ready"
    assert events == [] and services.research.calls == []


def test_resolved_source_outside_root_rejected(setup_api, tmp_path, monkeypatch):
    from pathlib import Path

    from fastapi.testclient import TestClient

    app, services, _ = setup_api
    inside = tmp_path / "link.pdf"
    outside = tmp_path.parent / "outside-fixture.pdf"
    outside.write_bytes(b"synthetic")
    resolve = Path.resolve

    def escaped(self, *args, **kwargs):
        return outside if self == inside else resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escaped)
    with TestClient(app) as client:
        response = client.post(
            "/v1/documents/import", json={"source_type": "pdf", "relative_path": "link.pdf"}
        )
    assert response.status_code == 400 and services.ingestion.calls == []


def test_unhandled_framework_exception_uses_safe_json(setup_api):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api

    async def broken():
        raise RuntimeError("private-framework-secret")

    app.add_api_route("/test-fault", broken)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-fault", headers={"X-Request-ID": ID})
    assert response.status_code == 500
    assert response.json()["error_code"] == "internal_error"
    assert response.headers["x-request-id"] == response.json()["request_id"] == ID
    assert "private" not in response.text


def test_non_utf8_json_is_controlled(setup_api):
    from fastapi.testclient import TestClient

    app, _, _ = setup_api
    with TestClient(app) as client:
        response = client.post(
            "/v1/questions", content=b"\xff", headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 400 and response.json()["error_code"] == "invalid_request"
