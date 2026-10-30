"""Phase 6 fixed synthetic labels, provenance gates and service integration."""

import copy
import json
from uuid import uuid4

import pytest

from clinical_agent.domain.research import QuestionRequest, ResearchError


@pytest.fixture
def case(source_factory, prepared_factory):
    from clinical_agent.domain.analysis import AnalysisDraft
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory("A cohort of 20 used MRI. AUC 0.8. Small sample."))
    chunk = prepared.embedded[0].evidence
    document = DocumentSummary.from_document(prepared.source.parsed.document)
    retrieval = RetrievalResult(
        options={},
        embedding_info=retrieval_embedding_info(),
        hits=[EvidenceHit(chunk=chunk, document=document, score=1.0, rank=1)],
    )
    request = QuestionRequest(request_id=uuid4(), question="Study MRI in a cohort")
    ref = {"chunk_id": str(chunk.chunk_id), "quote": "A cohort of 20"}
    item = {
        "value": "A cohort of 20",
        "epistemic_kind": "reported_fact",
        "evidence": [ref],
        "basis": "text",
        "verification_needed": None,
    }
    missing = {
        "value": None,
        "epistemic_kind": "reported_fact",
        "evidence": [],
        "basis": "not_reported",
        "verification_needed": None,
    }
    fields = {
        k: copy.deepcopy(missing)
        for k in [
            "design",
            "data_sources",
            "technical_methods",
            "evaluation_metrics",
            "results",
            "limitations",
            "population",
            "intervention",
            "comparison",
            "outcomes",
            "time_window",
            "sample_size",
            "effects",
            "quality_signals",
        ]
    }
    fields["design"] = item
    dimensions = {
        k: {"relation": "unknown", "idea_quote": None, "evidence": [], "reason": "Not specified"}
        for k in ["question", "population", "data", "methods", "outcomes"]
    }
    payload = {
        "studies": [
            {
                "document_id": str(document.document_id),
                "study_type": "cohort",
                "type_basis": "text",
                "type_evidence": [ref],
                "metadata_basis": [],
                "fields": fields,
            }
        ],
        "idea_similarities": [
            {
                "document_id": str(document.document_id),
                "dimensions": dimensions,
                "overall_relation": "unknown",
            }
        ],
        "candidate_gaps": [],
        "comparisons": [],
    }
    AnalysisDraft.model_validate(payload)
    return request, retrieval, payload


class Model:
    def __init__(self, payload):
        self.payload, self.calls = payload, 0

    def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
        self.calls += 1
        return json.dumps(self.payload)


def run(case, **kwargs):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    request, retrieval, payload = case
    return EvidenceAnalyzer(model=Model(payload), **kwargs).analyze(request, retrieval)


def test_evidence_analysis_fields_and_snapshot(case):
    output = run(case)
    assert output.analysis_status == "partial"
    assert output.studies[0].fields["design"].value == "A cohort of 20"
    assert output.studies[0].fields["effects"].basis == "not_reported"
    assert output.sources[0].evidence[0].location == case[1].hits[0].chunk.location
    assert output.original_idea == case[0].question


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_chunk",
        "invented_quote",
        "invented_number",
        "missing_field",
        "wrong_document",
        "false_overall",
        "missing_idea",
        "gap_fact",
        "gap_no_verification",
        "one_sided",
        "metadata",
        "duplicate_study",
    ],
)
def test_evidence_analysis_rejects_false_provenance(case, mutation):
    request, retrieval, p = case
    item = p["studies"][0]["fields"]["design"]
    if mutation == "unknown_chunk":
        item["evidence"][0]["chunk_id"] = str(uuid4())
    if mutation == "invented_quote":
        item["evidence"][0]["quote"] = "invented"
    if mutation == "invented_number":
        item["value"] = "A cohort of 2000"
    if mutation == "missing_field":
        del p["studies"][0]["fields"]["design"]
    if mutation == "wrong_document":
        p["studies"][0]["document_id"] = str(uuid4())
    if mutation == "false_overall":
        p["idea_similarities"][0]["overall_relation"] = "overlap"
    if mutation == "missing_idea":
        p["idea_similarities"][0]["dimensions"]["methods"].update(
            relation="overlap", evidence=item["evidence"]
        )
    if mutation in {"gap_fact", "gap_no_verification"}:
        p["candidate_gaps"] = [
            {
                "description": item,
                "counter_evidence": [],
                "reasoning": "Small sample",
                "scope": "These passages",
            }
        ]
        if mutation == "gap_no_verification":
            item["epistemic_kind"] = "unverified_hypothesis"
    if mutation == "one_sided":
        p["comparisons"] = [
            {
                "document_ids": [str(retrieval.hits[0].document.document_id)] * 2,
                "relation": "potential_conflict",
                "reason": "Different",
                "comparability": "Same outcome",
                "evidence": item["evidence"],
            }
        ]
    if mutation == "metadata":
        p["studies"][0].update(
            type_basis="metadata", metadata_basis=["Randomized Controlled Trial"]
        )
    if mutation == "duplicate_study":
        p["studies"].append(copy.deepcopy(p["studies"][0]))
    with pytest.raises(ResearchError):
        run(case)


def test_evidence_analysis_empty_skips_model(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    model = Model(case[2])
    empty = case[1].model_copy(update={"hits": []})
    result = EvidenceAnalyzer(model=model).analyze(case[0], empty)
    assert result.analysis_status == "insufficient_evidence"
    assert not result.candidate_gaps and model.calls == 0


def test_evidence_analysis_hypothesis_and_all_dimensions(case):
    p = case[2]
    item = copy.deepcopy(p["studies"][0]["fields"]["design"])
    item.update(
        value="Investigate a larger cohort",
        epistemic_kind="unverified_hypothesis",
        basis="model_inference",
        verification_needed="Review full text and additional studies",
    )
    p["candidate_gaps"] = [
        {
            "description": item,
            "counter_evidence": [],
            "reasoning": "Limited supplied cohort",
            "scope": "Supplied passage only",
        }
    ]
    for d in p["idea_similarities"][0]["dimensions"].values():
        d.update(relation="partial_overlap", idea_quote="MRI", evidence=item["evidence"])
    p["idea_similarities"][0]["overall_relation"] = "partial_overlap"
    result = run(case)
    assert result.candidate_gaps[0].description.epistemic_kind == "unverified_hypothesis"


def test_evidence_analysis_graph_reuses_retriever(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.research import ResearchService

    class Retriever:
        def retrieve(self, request):
            return case[1]

    class Generator:
        def generate(self, *args, **kwargs):
            raise AssertionError("No Phase 7 generation")

    service = ResearchService(
        retriever=Retriever(),
        generator=Generator(),
        analyzer=EvidenceAnalyzer(model=Model(case[2])),
    )
    result = service.analyze(case[0])
    assert result.request_id == case[0].request_id


def test_evidence_analysis_timeout_and_malformed(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    for raw in ["{}", '{"studies": [], "studies": []}', "NaN"]:

        class Bad:
            def analyze_evidence(self, *args, raw=raw, **kwargs):
                return raw

        with pytest.raises(ResearchError):
            EvidenceAnalyzer(model=Bad()).analyze(case[0], case[1])
    with pytest.raises(ResearchError):
        run(case, timeout_seconds=0)


@pytest.mark.parametrize("relation", ["overlap", "partial_overlap", "different", "unknown"])
def test_evidence_analysis_similarity_labels(case, relation):
    item = case[2]["studies"][0]["fields"]["design"]
    for dimension in case[2]["idea_similarities"][0]["dimensions"].values():
        dimension.update(relation=relation, idea_quote="MRI", evidence=item["evidence"])
    case[2]["idea_similarities"][0]["overall_relation"] = relation
    assert run(case).idea_similarities[0].overall_relation == relation


def test_evidence_analysis_model_cannot_mutate_snapshot(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    class Mutator(Model):
        def analyze_evidence(self, context, **kwargs):
            context["quotes"][0]["text"] = "Forged"
            return super().analyze_evidence(context, **kwargs)

    output = EvidenceAnalyzer(model=Mutator(case[2])).analyze(case[0], case[1])
    assert "Forged" not in output.sources[0].evidence[0].text


def test_evidence_analysis_retracted_source_excluded(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer

    hit = case[1].hits[0]
    hit.document.source_notices = ["Retracted Publication"]
    model = Model(case[2])
    output = EvidenceAnalyzer(model=model).analyze(case[0], case[1])
    assert output.analysis_status == "not_evaluated" and model.calls == 0


def test_evidence_analysis_langchain_messages_are_data(case):
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator
    from clinical_agent.application.analysis import EvidenceAnalyzer

    model = FakeListChatModel(responses=[json.dumps(case[2])])
    output = EvidenceAnalyzer(model=LangChainAnswerGenerator(model)).analyze(case[0], case[1])
    assert output.studies[0].study_type == "cohort"


@pytest.mark.parametrize("duplicate", [False, True])
def test_evidence_analysis_two_sided_comparison(case, duplicate):
    from clinical_agent.domain.retrieval import EvidenceHit

    request, retrieval, payload = case
    first = retrieval.hits[0]
    doc = first.document.model_copy(
        update={
            "document_id": uuid4(),
            "content_hash": first.document.content_hash if duplicate else "a" * 64,
        }
    )
    chunk = first.chunk.model_copy(
        update={
            "chunk_id": uuid4(),
            "document_id": doc.document_id,
            "source_metadata": first.chunk.source_metadata.model_copy(
                update={"content_hash": doc.content_hash}
            ),
        }
    )
    second = EvidenceHit(chunk=chunk, document=doc, score=0.9, rank=2)
    retrieval.hits.append(second)
    study = copy.deepcopy(payload["studies"][0])
    study["document_id"] = str(doc.document_id)
    for refs in [study["type_evidence"], study["fields"]["design"]["evidence"]]:
        refs[0]["chunk_id"] = str(chunk.chunk_id)
    payload["studies"].append(study)
    similarity = copy.deepcopy(payload["idea_similarities"][0])
    similarity["document_id"] = str(doc.document_id)
    payload["idea_similarities"].append(similarity)
    payload["comparisons"] = [
        {
            "document_ids": [str(first.document.document_id), str(doc.document_id)],
            "relation": "potential_conflict",
            "comparability": "Synthetic same outcome",
            "reason": "Synthetic opposite finding",
            "evidence": [payload["studies"][0]["type_evidence"][0], study["type_evidence"][0]],
        }
    ]
    if duplicate:
        with pytest.raises(ResearchError):
            run(case)
    else:
        assert run(case).comparisons[0].relation == "potential_conflict"


def test_evidence_analysis_cli_and_http(case, tmp_path, capsys):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.research import ResearchService
    from clinical_agent.cli import main

    class Retriever:
        def retrieve(self, request):
            return case[1]

    service = ResearchService(
        retriever=Retriever(), generator=object(), analyzer=EvidenceAnalyzer(model=Model(case[2]))
    )

    @contextmanager
    def factory(*args):
        yield service

    assert (
        main(
            [
                "ask",
                "--scope",
                "local",
                "--question",
                case[0].question,
                "--model-dir",
                str(tmp_path),
                "--analyze",
            ],
            research_factory=factory,
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["studies"] and "source_uri" not in json.dumps(result)

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=service)

    settings = ApiSettings(model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path)
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as client:
        response = client.post(
            "/v1/analyses", json={"scope": "local", "question": case[0].question}
        )
        assert response.status_code == 200, response.text
        assert response.json()["studies"] == result["studies"]
        assert (
            client.post(
                "/v1/analyses", content="invalid", headers={"Content-Type": "text/plain"}
            ).status_code
            == 415
        )


def test_evidence_analysis_budget_and_timeout(case):
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.domain.research import ResearchLimits

    model = Model(case[2])
    with pytest.raises(ResearchError, match="context_limit"):
        EvidenceAnalyzer(model=model, limits=ResearchLimits(max_context_characters=1)).analyze(
            case[0], case[1]
        )
    assert model.calls == 0
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=model, limits=ResearchLimits(max_output_bytes=1)).analyze(
            case[0], case[1]
        )

    class Timeout:
        def analyze_evidence(self, context, **kwargs):
            raise TimeoutError("private")

    with pytest.raises(ResearchError, match="generation_timeout"):
        EvidenceAnalyzer(model=Timeout()).analyze(case[0], case[1])


def test_evidence_analysis_plan_clarifies_without_search(case):
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.pico import QueryPlan

    question = case[0].question
    plan = QueryPlan(
        original_question=question,
        structured_question={
            "question_type": "uncertain",
            "pico": {"population": None, "intervention": None, "comparison": None, "outcome": None},
            "ambiguities": ["What outcome?"],
            "extraction_status": "needs_clarification",
        },
        terms=[],
        search_intent="uncertain",
        preserved_constraints=[
            {
                "text": question,
                "origin": "user_text",
                "source_span": {"start": 0, "end": len(question)},
            }
        ],
    )

    class Planner:
        def plan(self, *args, **kwargs):
            return plan

    class Retriever:
        def retrieve(self, *args):
            raise AssertionError("Clarification must not retrieve")

    result = ResearchService(retriever=Retriever(), generator=object(), planner=Planner()).analyze(
        case[0]
    )
    assert result.analysis_status == "needs_clarification" and result.retrieval is None


def test_evidence_analysis_retrieval_failure_never_empty(case):
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.retrieval import RetrievalError

    class Retriever:
        def retrieve(self, request):
            raise RetrievalError("retrieval_failed")

    with pytest.raises(RetrievalError):
        ResearchService(retriever=Retriever(), generator=object()).analyze(case[0])
