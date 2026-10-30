"""Shared entry points and real compatible chat protocol; live smoke is opt-in."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).parents[2]
CASES = json.loads((ROOT / "tests/fixtures/pico/questions.json").read_text(encoding="utf-8"))


def extraction(case):
    pico = {}
    for key, text in case["pico"].items():
        start = case["question"].index(text) if text else 0
        pico[key] = (
            {
                "text": text,
                "origin": "user_text",
                "source_span": {"start": start, "end": start + len(text)},
            }
            if text
            else None
        )
    return {"question_type": case["question_type"], "pico": pico, "terms": [], "ambiguities": []}


def test_pico_protocol_retrieval_generation_and_citations(source_factory, prepared_factory):
    from clinical_agent.adapters.llm import LLMSettings, open_llm
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.research import QuestionRequest
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory())
    source = prepared.source.parsed.document
    chunk = prepared.embedded[0].evidence
    calls = []
    queries = []
    case = CASES["cases"][0]

    def handler(request):
        data = json.loads(request.content)
        calls.append(data)
        value = (
            extraction(case)
            if len(calls) == 1
            else {
                "claims": [
                    {
                        "text": "Synthetic evidence only.",
                        "kind": "uncertainty",
                        "evidence_chunk_ids": [str(chunk.chunk_id)],
                        "limitations": [],
                    }
                ]
            }
        )
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(value)},
                    }
                ],
            },
        )

    class Retriever:
        def retrieve(self, request):
            queries.append(request.question)
            return RetrievalResult(
                options=request.options,
                embedding_info=retrieval_embedding_info(),
                hits=[
                    EvidenceHit(
                        chunk=chunk,
                        document=DocumentSummary.from_document(source),
                        score=1.0,
                        rank=1,
                    )
                ],
            )

    settings = LLMSettings(base_url="https://example.test/v1", api_key="fake", model="test-model")
    with open_llm(settings, transport=httpx.MockTransport(handler)) as generator:
        answer = ResearchService(
            retriever=Retriever(), generator=generator, planner=PicoPlanner(extractor=generator)
        ).answer(QuestionRequest(request_id=uuid4(), question=case["question"]))
    assert answer.status == "answered" and answer.query_plan.original_question == case["question"]
    assert queries == [case["question"]] and len(calls) == 2
    assert answer.claims[0].evidence_chunk_ids == [chunk.chunk_id]
    assert answer.sources[0].document_id == source.document_id


def clarification_service():
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.application.research import ResearchService

    class Extractor:
        def extract(self, request, *, timeout_seconds):
            return json.dumps(
                {
                    "question_type": "uncertain",
                    "pico": dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
                    "terms": [],
                    "ambiguities": ["请明确研究人群和干预。"],
                }
            )

    return ResearchService(
        retriever=object(), generator=object(), planner=PicoPlanner(extractor=Extractor())
    )


def test_pico_cli_shared_result(capsys):
    from clinical_agent import cli

    @contextmanager
    def research(model_dir):
        yield clarification_service()

    assert (
        cli.main(
            ["ask", "--model-dir", ".", "--question", "Which drug?"], research_factory=research
        )
        == 0
    )
    answer = json.loads(capsys.readouterr().out)
    assert answer["status"] == "needs_clarification"
    assert answer["query_plan"]["structured_question"]["ambiguities"]


def test_pico_api_and_feishu_share_clarification(tmp_path):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.domain.research import ResearchAnswer
    from feishu.sender import render_answer

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=clarification_service())

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as client:
        response = client.post("/v1/questions", json={"question": "Which drug?"})
    assert response.status_code == 200
    answer = ResearchAnswer.model_validate(response.json())
    assert answer.status == "needs_clarification" and "需澄清" in render_answer(answer)


@pytest.mark.parametrize("code,status", [("extraction_failed", 502), ("extraction_timeout", 504)])
def test_pico_api_error_contract(tmp_path, code, status):
    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.domain.research import ResearchError

    class Bad:
        def answer(self, request):
            raise ResearchError(code)

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=Bad())

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as client:
        response = client.post("/v1/questions", json={"question": "question"})
    assert response.status_code == status
    assert response.json()["error_code"] == code


@pytest.mark.external
def test_pico_live_frozen_examples(tmp_path):
    from clinical_agent.adapters.llm import LLMSettings, open_llm
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.domain.pico import ClassificationRequest

    if not all(os.environ.get(name) for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")):
        pytest.fail("Explicit LLM_* configuration required; live PICO acceptance not run")
    settings = LLMSettings()
    results = []
    failures = []
    with open_llm(settings) as generator:
        planner = PicoPlanner(extractor=generator, max_seconds=60.0)
        for case in CASES["cases"]:
            try:
                result = planner.plan(
                    ClassificationRequest(question=case["question"]), timeout_seconds=60
                )
                actual = {k: getattr(result.structured_question.pico, k) for k in case["pico"]}
                rows = {k: (v.text if v else None) for k, v in actual.items()}
                correct = sum(rows[k] == v for k, v in case["pico"].items())
                missing = sum(rows[k] is None and v is not None for k, v in case["pico"].items())
                extra = sum(rows[k] is not None and v is None for k, v in case["pico"].items())
                results.append(
                    {
                        "id": case["id"],
                        "plan": result.model_dump(mode="json"),
                        "correct": correct,
                        "missing": missing,
                        "extra": extra,
                    }
                )
                if rows != case["pico"] or result.search_intent != case["question_type"]:
                    failures.append(case["id"])
            except Exception:
                results.append({"id": case["id"], "error": "extraction_failed_or_timeout"})
                failures.append(case["id"])
    report = {
        "dataset": CASES["version"],
        "model": settings.model,
        "calls": len(results),
        "results": results,
        "failed_cases": failures,
    }
    (tmp_path / "pico-live.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert not failures, f"PICO acceptance failed cases: {failures} (see controlled test artifacts)"
