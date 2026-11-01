"""Freeze HTTP behavior independently of historical local-scope fixtures."""

import copy
import json
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import pytest

IDENTITY = "12345678-1234-4234-8234-123456789abc"


def test_openapi_matches_phase0():
    from clinical_agent.api import create_app

    baseline = json.loads(
        (Path(__file__).parents[1] / "fixtures/agents/phase0-contracts.json").read_text(
            encoding="utf-8"
        )
    )
    expected = copy.deepcopy(baseline["openapi"])
    # Public import no longer accepts local PubMed XML. OpenAlex GROBID XML is unchanged.
    source_type = expected["components"]["schemas"]["ImportBody"]["properties"]["source_type"]
    assert source_type.pop("enum") == ["pdf", "pubmed_xml"]
    source_type["const"] = "pdf"
    expected["components"]["schemas"]["QuestionBody"]["properties"]["scope"]["enum"] = [
        "online",
        "hybrid",
    ]
    # Planner schema now explains the already-enforced required-anchor contract.
    expected["components"]["schemas"]["ConceptRelation"]["properties"]["required"][
        "description"
    ] = (
        "true only for exact_synonym, method, or required_constraint anchors. "
        "Must be false for narrower_concept, broader_concept, related_concept, "
        "and optional_constraint. Each expansion shares concept_id with a valid anchor."
    )
    assert create_app().openapi() == expected


@pytest.mark.parametrize(
    "code,status,retryable",
    [
        ("retrieval_timeout", 504, True),
        ("generation_timeout", 504, True),
        ("openalex_timeout", 504, True),
        ("research_timeout", 504, True),
        ("retrieval_failed", 503, True),
        ("retrieval_embedding_failed", 503, True),
        ("generation_failed", 503, True),
        ("pubmed_failed", 503, True),
        ("openalex_failed", 503, True),
        ("openalex_auth_failed", 503, True),
        ("openalex_rate_limited", 503, True),
        ("model_output_invalid", 502, False),
        ("analysis_output_truncated", 502, False),
        ("citation_invalid", 502, False),
        ("extraction_failed", 502, False),
        ("pubmed_invalid", 502, False),
        ("openalex_invalid", 502, False),
        ("openalex_plan_required", 502, False),
        ("openalex_options_retired", 502, False),
        ("openalex_required", 502, False),
        ("local_corpus_not_evidence", 502, False),
        ("context_limit", 422, False),
        ("retrieval_language_unsupported", 422, False),
        ("research_failed", 500, False),
        ("retrieval_corrupt", 500, False),
        ("unknown", 500, False),
    ],
)
def test_online_error_mapping_is_not_shadowed_by_local_gate(tmp_path, code, status, retryable):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api.runtime import ServiceBundle
    from clinical_agent.api.schemas import ApiSettings
    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalError

    class Research:
        def answer(self, request):
            assert request.scope == "online" and str(request.request_id) == IDENTITY
            if code == "unknown":
                raise RuntimeError("private-secret")
            error = RetrievalError if code.startswith("retrieval_") else ResearchError
            raise error(code)

    @contextmanager
    def factory(settings):
        yield ServiceBundle(ingestion=object(), research=Research())

    settings = ApiSettings(model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path)
    with TestClient(create_app(settings=settings, runtime_factory=factory)) as client:
        response = client.post(
            "/v1/questions",
            json={"question": "synthetic", "scope": "online"},
            headers={"X-Request-ID": IDENTITY},
        )
    assert response.status_code == status
    assert response.json() == {
        "request_id": IDENTITY,
        "error_code": "internal_error" if code == "unknown" else code,
        "message": "Request could not be completed.",
        "retryable": retryable,
    }
    assert response.headers["x-request-id"] == IDENTITY
    assert "retry-after" not in response.headers


def test_two_apps_own_separate_lifespans(tmp_path):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api.runtime import ServiceBundle
    from clinical_agent.api.schemas import ApiSettings

    events = []

    @contextmanager
    def factory(settings):
        events.append("enter")
        try:
            yield ServiceBundle(ingestion=object(), research=object())
        finally:
            events.append("exit")

    settings = ApiSettings(model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path)
    first, second = [create_app(settings=settings, runtime_factory=factory) for _ in range(2)]
    assert events == []
    with TestClient(first) as active:
        with TestClient(second) as other:
            assert events == ["enter", "enter"]
            assert other.get("/health/ready").status_code == 200
        assert events == ["enter", "enter", "exit"]
        assert active.get("/health/ready").status_code == 200
    assert events == ["enter", "enter", "exit", "exit"]
    assert UUID(active.get("/health/live").headers["x-request-id"])


@pytest.mark.parametrize(
    "module", ["app", "routes", "schemas", "middleware", "execution", "runtime"]
)
def test_new_api_modules_import_without_optional_runtime(module, tmp_path):
    from tests.unit.test_package import test_package_import_is_isolated_and_quiet

    test_package_import_is_isolated_and_quiet("clinical_agent.api." + module, tmp_path)


def test_package_exports_canonical_factory():
    from clinical_agent import api
    from clinical_agent.api import app

    assert api.create_app is app.create_app


def test_online_saturation_keeps_health_and_recovers_capacity(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api.runtime import ServiceBundle
    from clinical_agent.api.schemas import ApiSettings
    from clinical_agent.domain.research import ResearchError

    entered, release = threading.Event(), threading.Event()

    class Research:
        def answer(self, request):
            entered.set()
            assert release.wait(5)
            raise ResearchError("generation_failed")

    @contextmanager
    def factory(settings):
        yield ServiceBundle(ingestion=object(), research=Research())

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path, max_in_flight=1
    )
    with TestClient(create_app(settings=settings, runtime_factory=factory)) as client:

        def post():
            return client.post("/v1/questions", json={"question": "synthetic", "scope": "online"})

        with ThreadPoolExecutor(max_workers=1) as executor:
            running = executor.submit(post)
            try:
                assert entered.wait(3)
                busy = post()
                assert busy.status_code == 503 and busy.json()["error_code"] == "busy"
                assert busy.json()["retryable"] is True
                assert busy.headers["retry-after"] == "1"
                assert client.get("/health/ready").status_code == 200
            finally:
                release.set()
            assert running.result(3).json()["error_code"] == "generation_failed"
        assert post().json()["error_code"] == "generation_failed"
