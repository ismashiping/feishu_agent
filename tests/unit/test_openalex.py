"""Contract tests; synthetic boundary cases never serve as scientific references."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from clinical_agent.domain.openalex import (
    OpenAlexRecord,
    ResearchConstraints,
    decode_abstract,
    resolve_dates,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "openalex"


def test_inverted_index():
    assert decode_abstract({"again": [2], "Hello": [0], "world": [1]}) == "Hello world again"
    assert decode_abstract(None) == ""
    for value in [{"a": [1]}, {"a": [0], "b": [0]}, {"a": [-1]}, {"a": [True]}]:
        with pytest.raises(ValueError):
            decode_abstract(value)


@pytest.mark.parametrize(
    "name", ["organ", "subregion", "comparison", "mvi", "bottlenecks", "holdout"]
)
def test_real_fixtures(name):
    from hashlib import sha256

    raw = (FIXTURES / f"{name}.json").read_bytes()
    manifest = json.loads((FIXTURES / f"{name}.manifest.json").read_text())
    assert sha256(raw).hexdigest() == manifest["sha256"]
    for work in json.loads(raw)["results"]:
        record = OpenAlexRecord.from_work(work)
        assert record.openalex_id == work["id"]
        record.verify_snapshot()
        altered = record.model_copy(update={"title": "tampered"})
        with pytest.raises(ValueError):
            altered.verify_snapshot()


def constraints(**kwargs):
    return ResearchConstraints(task=["segmentation"], time_text="test time phrase", **kwargs)


def test_dates_are_calendar_months_and_intersections():
    assert resolve_dates(constraints(time_intent="latest"), date(2026, 10, 29)) == (
        date(2024, 10, 29),
        date(2026, 10, 29),
    )
    assert resolve_dates(constraints(time_intent="latest"), date(2024, 2, 29)) == (
        date(2022, 2, 28),
        date(2024, 2, 29),
    )
    assert resolve_dates(constraints(time_intent="relative_years", years=3), date(2026, 10, 29))[
        0
    ] == date(2023, 10, 29)
    assert resolve_dates(constraints(time_intent="classic"), date(2026, 10, 29)) == (None, None)
    with pytest.raises(ValueError):
        resolve_dates(
            constraints(time_intent="latest"),
            date(2026, 10, 29),
            explicit=(date(2000, 1, 1), date(2001, 1, 1)),
        )


def test_transport_filters_auth_and_classifies_without_leaking():
    from clinical_agent.adapters.openalex import OpenAlexClient
    from clinical_agent.domain.openalex import OpenAlexError

    def handle(request):
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert "api_key" not in request.url.params
        assert (
            request.url.params["filter"]
            == "from_publication_date:2024-10-29,to_publication_date:2026-10-29"
        )
        return httpx.Response(429)

    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        client = OpenAlexClient(http, api_key="test-secret")
        with pytest.raises(OpenAlexError, match="openalex_rate_limited") as error:
            client.search(
                "segmentation",
                date_from=date(2024, 10, 29),
                date_to=date(2026, 10, 29),
                sort="relevance_score:desc",
                timeout_seconds=2,
            )
        assert "test-secret" not in str(error.value)


def test_assessment_requires_actual_quotes_and_complete_ids():
    from clinical_agent.domain.openalex import parse_assessments

    record = OpenAlexRecord.from_work(
        json.loads((FIXTURES / "organ.json").read_text())["results"][0]
    )
    data = {
        "assessments": [
            {
                "id": record.openalex_id,
                "relevance": "direct",
                "quote": "made up",
                "constraints_match": True,
                "experimental_information": True,
                "representative": True,
                "covered_dimensions": [],
                "reason": "test",
            }
        ]
    }
    with pytest.raises(ValueError):
        parse_assessments(json.dumps(data), {record.openalex_id: (record.title, record.abstract)})
    data["assessments"][0]["quote"] = record.title
    assert (
        parse_assessments(json.dumps(data), {record.openalex_id: (record.title, record.abstract)})[
            0
        ].relevance
        == "direct"
    )


def test_new_runtime_contains_no_pubmed_discovery():
    root = Path(__file__).parents[2] / "src" / "clinical_agent"
    for name in ["command_runtime.py", "api_runtime.py"]:
        source = (root / name).read_text()
        assert "open_pubmed" not in source
        assert "OpenAlexRetrievalService" in source


def plan(question="segmentation", **kwargs):
    from clinical_agent.domain.pico import QueryPlan

    return QueryPlan.model_validate(
        {
            "original_question": question,
            "research_constraints": {"task": [question], **kwargs},
            "research_intent": "discovery",
            "concept_groups": [["segmentation"]],
            "search_intent": "other",
            "terms": [],
            "structured_question": {
                "question_type": "other",
                "pico": {
                    "population": None,
                    "intervention": None,
                    "comparison": None,
                    "outcome": None,
                },
                "ambiguities": [],
                "blocking_ambiguities": [],
                "extraction_status": "partial",
            },
            "preserved_constraints": [
                {
                    "text": question,
                    "origin": "user_text",
                    "source_span": {"start": 0, "end": len(question)},
                }
            ],
        }
    )


class Screening:
    def __init__(self, relevance="direct", covered=()):
        self.calls = []
        self.relevance, self.covered = relevance, covered

    def screen_candidates(self, context, *, timeout_seconds):
        self.calls.append(context)
        return json.dumps(
            {
                "assessments": [
                    {
                        "id": c["id"],
                        "relevance": self.relevance,
                        "quote": c["title"],
                        "constraints_match": self.relevance == "direct",
                        "experimental_information": True,
                        "representative": True,
                        "covered_dimensions": list(self.covered),
                        "reason": "Synthetic transport test judgment, not medical review",
                    }
                    for c in context["candidates"]
                ]
            }
        )


class Search:
    def __init__(self):
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        records = [
            OpenAlexRecord.from_work(w)
            for w in json.loads((FIXTURES / "organ.json").read_text())["results"]
        ]
        return records, 100, []


def test_quality_not_count_triggers_second_round_and_no_fillers():
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.retrieval import RetrievalRequest

    search, screening = Search(), Screening("partial")
    service = OpenAlexRetrievalService(search, screening)
    result = service.retrieve(
        RetrievalRequest(question="segmentation", scope="online"), query_plan=plan()
    )
    assert len(search.calls) == 4
    assert len(screening.calls) == 1  # identical IDs are not paid for twice
    assert not result.hits
    assert result.search_provenance.evidence_gaps == ["no_direct_evidence"]
    assert result.search_provenance.http_attempts == 4


def test_openalex_citation_and_snapshot_roundtrip():
    from datetime import UTC, datetime
    from uuid import uuid4

    from clinical_agent.adapters.report_snapshot import SnapshotVerifier
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest
    from clinical_agent.domain.retrieval import RetrievalRequest
    from feishu.sender import render_answer

    service = OpenAlexRetrievalService(Search(), Screening())
    request = QuestionRequest(question="segmentation", scope="online", request_id=uuid4())
    result = service.retrieve(
        RetrievalRequest(question=request.question, scope="online"), query_plan=plan()
    )
    assert result.hits
    assert result.search_provenance.http_attempts == 4  # soft independent-evidence coverage
    hit = result.hits[0]
    answer = build_answer(
        request,
        result,
        GenerationDraft(
            claims=[
                DraftClaim(
                    text="Test data flow only.",
                    kind="evidence",
                    evidence_chunk_ids=[hit.chunk.chunk_id],
                    limitations=[],
                )
            ]
        ),
        generated_at=datetime.now(UTC),
    )
    source = answer.sources[0]
    assert source.pmid is None
    assert source.openalex_record.openalex_id == source.source_url
    assert SnapshotVerifier().check(source, result) == "valid"
    rendered = render_answer(answer)
    assert "openalex.org/W" in rendered
    assert "PubMed" not in rendered
    assert "OpenAlex" in render_answer(answer, include_audit=True)
    assert "PubMed" not in render_answer(answer, include_audit=True)


def test_partial_network_failure_preserves_success():
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.openalex import OpenAlexError
    from clinical_agent.domain.retrieval import RetrievalRequest

    class PartialSearch(Search):
        def search(self, query, **kwargs):
            if self.calls:
                raise OpenAlexError("openalex_timeout")
            return super().search(query, **kwargs)

    result = OpenAlexRetrievalService(PartialSearch(), Screening()).retrieve(
        RetrievalRequest(question="segmentation", scope="online"), query_plan=plan()
    )
    assert result.hits and result.search_provenance.status == "partial"


@pytest.mark.parametrize(
    ("question", "fields"),
    [
        (
            "肝脏分割最新研究有哪些？",
            {
                "population": ["肝脏"],
                "task": ["分割"],
                "time_text": "最新",
                "time_intent": "latest",
            },
        ),
        (
            "肝脏肿瘤亚区分割最新进展有哪些？",
            {
                "population": ["肝脏肿瘤"],
                "task": ["亚区分割"],
                "time_text": "最新",
                "time_intent": "latest",
            },
        ),
        ("MedSAM与nnU-Net有哪些区别？", {"task": ["MedSAM", "nnU-Net"]}),
        (
            "最近三年MRI预测肝癌微血管侵犯有哪些研究？",
            {
                "population": ["肝癌"],
                "task": ["预测", "微血管侵犯"],
                "data_type": ["MRI"],
                "time_text": "最近三年",
                "time_intent": "relative_years",
                "years": 3,
            },
        ),
        (
            "肝脏肿瘤分割目前有哪些技术瓶颈？",
            {"population": ["肝脏肿瘤"], "task": ["分割"], "answer_dimensions": ["limitations"]},
        ),
        (
            "脑肿瘤分割最新进展",
            {
                "population": ["脑肿瘤"],
                "task": ["分割"],
                "time_text": "最新",
                "time_intent": "latest",
            },
        ),
    ],
)
def test_five_questions_and_holdout_contract(question, fields):
    """Checks schema/provenance only; actual LLM extraction is a separate external test."""
    p = plan(question, **fields)
    assert p.research_constraints.task == fields["task"]
    with pytest.raises(ValueError):
        p.research_constraints.validate_question("unrelated question")


def test_doi_normalization_and_explicit_retirement():
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.openalex import normalize_doi
    from clinical_agent.domain.pubmed import PubMedOptions
    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalRequest

    assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
    with pytest.raises(ResearchError, match="openalex_options_retired"):
        OpenAlexRetrievalService(Search(), Screening()).retrieve(
            RetrievalRequest(question="segmentation", scope="online", pubmed=PubMedOptions()),
            query_plan=plan(),
        )


def test_cli_api_and_generation_context_keep_snapshots_out_of_prompt(tmp_path, capsys):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.application.research import ResearchService
    from clinical_agent.cli import main

    class Planner:
        def plan(self, request, *, timeout_seconds):
            return plan(request.question)

    class Generator:
        def generate(self, context, *, timeout_seconds):
            assert context.search_provenance.records == []
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": "Offline dataflow test.",
                            "kind": "evidence",
                            "evidence_chunk_ids": [str(context.evidence[0].chunk_id)],
                            "limitations": [],
                        }
                    ]
                }
            )

    @contextmanager
    def service(model_dir=None):
        yield ResearchService(
            retriever=object(),
            generator=Generator(),
            planner=Planner(),
            online_retriever=OpenAlexRetrievalService(Search(), Screening()),
        )

    assert (
        main(
            ["ask", "--model-dir", ".", "--scope", "online", "--question", "segmentation"],
            research_factory=service,
        )
        == 0
    )
    answer = json.loads(capsys.readouterr().out)
    assert answer["search_provenance"]["endpoint"] == "https://api.openalex.org/works"

    @contextmanager
    def runtime(settings):
        with service() as research:
            yield ServiceBundle(ingestion=object(), research=research)

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as api:
        response = api.post("/v1/questions", json={"question": "segmentation", "scope": "online"})
        assert response.status_code == 200
        assert response.json()["sources"][0]["source_type"] == "openalex"


def test_query_time_words_are_not_literature_concepts():
    from clinical_agent.application.openalex import compile_queries

    p = plan("segmentation latest", task=["segmentation"], time_intent="latest", time_text="latest")
    p.concept_relations = [
        __import__("clinical_agent.domain.pico", fromlist=["ConceptRelation"]).ConceptRelation(
            source_text=quote,
            english_term=quote,
            concept_id=quote,
            relation="exact_synonym",
            required=True,
        )
        for quote in ["segmentation", "latest"]
    ]
    assert compile_queries(p) == ['("segmentation")', "segmentation"]


def test_new_planner_grounds_unique_quotes_without_trusting_model_offsets():
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.domain.pico import ClassificationRequest

    class Extractor:
        def extract(self, request, *, timeout_seconds):
            data = plan().model_dump(
                exclude={
                    "original_question",
                    "structured_question",
                    "search_intent",
                    "preserved_constraints",
                    "version",
                }
            )
            data.update(
                question_type="other",
                pico={
                    "population": None,
                    "intervention": None,
                    "comparison": None,
                    "outcome": None,
                },
                ambiguities=[],
                blocking_ambiguities=[],
                terms=[
                    {
                        "text": "segmentation",
                        "origin": "user_text",
                        "source_span": {"start": 1, "end": 3},
                    }
                ],
            )
            return json.dumps(data)

    result = PicoPlanner(extractor=Extractor()).plan(ClassificationRequest(question="segmentation"))
    assert result.terms[0].source_span.start == 0
    assert result.terms[0].source_span.end == len("segmentation")


def test_endpoint_constraint_is_retained_even_if_planner_task_is_coarse():
    from clinical_agent.application.openalex import compile_queries
    from clinical_agent.domain.pico import ConceptRelation

    p = plan(
        "MRI predict invasion latest",
        task=["predict"],
        data_type=["MRI"],
        time_intent="latest",
        time_text="latest",
    )
    p.concept_relations = [
        ConceptRelation(
            source_text=q, english_term=q, concept_id=q, relation="exact_synonym", required=True
        )
        for q in ["MRI", "predict", "invasion", "latest"]
    ]
    query = compile_queries(p)[0]
    assert "invasion" in query and "latest" not in query


def test_bad_quote_rejects_that_paper_and_marks_partial():
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.retrieval import RetrievalRequest

    class Mixed(Screening):
        def screen_candidates(self, context, *, timeout_seconds):
            raw = super().screen_candidates(context, timeout_seconds=timeout_seconds)
            data = json.loads(raw)
            data["assessments"][0]["quote"] = "fabricated quotation must be rejected"
            return json.dumps(data)

    result = OpenAlexRetrievalService(Search(), Mixed()).retrieve(
        RetrievalRequest(question="segmentation", scope="online"), query_plan=plan()
    )
    assert result.hits
    assert result.search_provenance.status == "partial"
    assert "openalex_assessment_invalid" in result.search_provenance.warnings
    bad_id = result.search_provenance.records[0].openalex_id
    assert all(h.document.openalex_record.openalex_id != bad_id for h in result.hits)


def test_hybrid_reuses_selected_local_evidence(source_factory, prepared_factory):
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalOptions,
        RetrievalRequest,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory(text="Synthetic local segmentation methods."))
    local_hit = EvidenceHit(
        chunk=prepared.embedded[0].evidence,
        document=DocumentSummary.from_document(prepared.source.parsed.document),
        score=0.9,
        rank=1,
    )
    options = RetrievalOptions()
    local = RetrievalResult(
        options=options, embedding_info=retrieval_embedding_info(), hits=[local_hit]
    )

    class Empty:
        def search(self, query, **kwargs):
            return [], 0, []

    result = OpenAlexRetrievalService(Empty(), Screening()).retrieve(
        RetrievalRequest(question="segmentation", scope="hybrid"), query_plan=plan(), local=local
    )
    assert result.scope == "hybrid"
    assert result.hits[0].chunk.chunk_id == local_hit.chunk.chunk_id


def test_expired_budget_makes_no_http_call():
    from clinical_agent.application.openalex import OpenAlexRetrievalService
    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalRequest

    search = Search()
    with pytest.raises(ResearchError, match="openalex_timeout"):
        OpenAlexRetrievalService(search, Screening(), clock=lambda: 10.0).retrieve(
            RetrievalRequest(question="segmentation", scope="online"),
            query_plan=plan(),
            timeout_seconds=0,
        )
    assert search.calls == []


@pytest.mark.parametrize(
    "flag,value", [("--sort", "pub_date"), ("--max-results", "20"), ("--date-field", "edat")]
)
def test_retired_cli_tuning_is_rejected(flag, value, capsys):
    from clinical_agent.cli import main

    assert (
        main(
            [
                "ask",
                "--model-dir",
                ".",
                "--scope",
                "online",
                "--question",
                "segmentation",
                flag,
                value,
            ]
        )
        == 2
    )
    assert "invalid_arguments" in capsys.readouterr().err
