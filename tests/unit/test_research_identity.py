"""Task retrieval/identity contracts; frozen AI labels are not medical gold labels."""

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from clinical_agent.application.openalex import OpenAlexRetrievalService, compile_queries
from clinical_agent.domain.openalex import OpenAlexRecord, parse_assessments
from clinical_agent.domain.pico import PaperTarget, QueryPlan
from clinical_agent.domain.retrieval import RetrievalRequest
from tests.unit.test_openalex import Screening, plan

ROOT = Path(__file__).parents[1] / "fixtures" / "research_identity"


def records():
    return [
        OpenAlexRecord.from_work(x["work"]) for x in json.loads((ROOT / "records.json").read_text())
    ]


def target_plan(kind="method", value="nnunet", intent="paper_explanation"):
    p = plan(value)
    p.task_intent = intent
    p.paper_target = PaperTarget(kind=kind, source_text=value)
    p.concept_groups = [[value]]
    return p


class Origins(Screening):
    def screen_candidates(self, context, **kwargs):
        result = json.loads(super().screen_candidates(context, **kwargs))
        for a, c in zip(result["assessments"], context["candidates"], strict=True):
            a["study_role"] = "method_origin"
            text = c["abstract"]
            a["origin_quote"] = next(
                (s.strip() for s in text.split(". ") if "introduces the nnU-Net" in s), text[:120]
            )
        return json.dumps(result)


def retrieve(p, works=None, screener=None, options=None):
    calls = []

    def search(query, **kwargs):
        calls.append((query, kwargs))
        return works if works is not None else records()[:2], 2, []

    result = OpenAlexRetrievalService(
        SimpleNamespace(search=search), screener or Origins()
    ).retrieve(
        RetrievalRequest(question=p.original_question, scope="online", openalex=options),
        query_plan=p,
    )
    return result, calls


def test_frozen_real_records_and_review_status():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert sha256((ROOT / "records.json").read_bytes()).hexdigest() == manifest["sha256"]
    assert manifest["human_signoff"] is None
    for r in records():
        r.verify_snapshot()


def test_feasibility_queries_keep_object_and_add_distinct_purposes():
    p = plan("liver subregion segmentation")
    p.task_intent = "feasibility"
    p.concept_groups = [["liver"], ["subregion segmentation"]]
    queries = compile_queries(p)
    assert len(queries) == 3
    assert all("liver" in q and "subregion segmentation" in q for q in queries)
    assert "methods" in queries[1] and "limitations" in queries[2]
    result, calls = retrieve(p, works=[])
    assert len(calls) == 4
    assert [x["purpose"] for x in result.search_provenance.query_rounds] == [
        "direct",
        "direct",
        "technical_route",
        "bottlenecks",
    ]


def test_explicit_query_is_preserved():
    p = target_plan(intent="feasibility")
    _, calls = retrieve(p, works=[], options={"query": "operator query"})
    assert all(query == "operator query" for query, _ in calls)


def test_method_origin_and_variant_not_interchangeable():
    result, calls = retrieve(target_plan())
    assert [h.document.openalex_record.openalex_id for h in result.hits] == [
        records()[0].openalex_id
    ]
    checks = result.search_provenance.identity_checks
    assert checks[records()[0].openalex_id] == "method_origin_supported"
    assert checks[records()[1].openalex_id] == "unresolved"
    assert all(k["date_from"] is None for _, k in calls)
    assert all(k["sort"] == "relevance_score:desc" for _, k in calls)


def test_unet_does_not_match_nnunet_origin():
    result, _ = retrieve(target_plan(value="unet"), works=records()[:1])
    assert not result.hits


def test_doi_gate_overrides_direct_model_label_and_retains_scope_gate():
    origin, variant = records()[:2]
    p = target_plan("doi", origin.doi)
    result, _ = retrieve(p, screener=Screening())
    assert [h.document.doi for h in result.hits] == [origin.doi]
    assert result.search_provenance.identity_checks[variant.openalex_id] == "mismatch"
    rejected, _ = retrieve(p, screener=Screening(relevance="irrelevant"))
    assert not rejected.hits
    assert result.search_provenance.identity_checks[origin.openalex_id] == "doi_match"


def test_title_match_does_not_accept_similar_variant():
    origin, variant = records()[:2]
    p = target_plan("title", origin.title.upper())
    result, _ = retrieve(p, screener=Screening())
    assert len(result.hits) == 1
    assert result.search_provenance.identity_checks[variant.openalex_id] == "mismatch"


def test_missing_target_does_not_explain_arbitrary_paper():
    p = plan("explain original paper")
    p.task_intent = "paper_explanation"
    result, _ = retrieve(p)
    assert not result.hits
    assert "paper_identity_unresolved" in result.search_provenance.evidence_gaps


def test_missing_metadata_is_unresolved():
    origin = records()[0]
    work = json.loads(origin.snapshot_json)
    work["doi"] = None
    result, _ = retrieve(target_plan("doi", origin.doi), works=[OpenAlexRecord.from_work(work)])
    assert not result.hits
    assert set(result.search_provenance.identity_checks.values()) == {"unresolved"}


def test_fabricated_origin_quote_is_rejected():
    r = records()[0]
    item = {
        "id": r.openalex_id,
        "study_role": "method_origin",
        "origin_quote": "Invented origin",
        "relevance": "direct",
        "quote": r.title,
        "constraints_match": True,
        "experimental_information": True,
        "representative": True,
        "covered_dimensions": [],
        "reason": "Synthetic decision",
    }
    with pytest.raises(ValueError):
        parse_assessments(
            json.dumps({"assessments": [item]}), {r.openalex_id: (r.title, r.abstract)}
        )


def test_target_provenance_and_doi_validation():
    p = target_plan()
    data = p.model_dump()
    data["paper_target"]["source_text"] = "invented paper title"
    with pytest.raises(ValueError):
        QueryPlan.model_validate(data)
    with pytest.raises(ValueError):
        PaperTarget(kind="doi", source_text="invented DOI")


def test_screening_receives_task_and_trusted_metadata():
    screening = Screening()
    origin = records()[0]
    retrieve(target_plan("doi", origin.doi), screener=screening)
    context = screening.calls[0]
    assert context["task_intent"] == "paper_explanation"
    assert context["paper_target"]["source_text"] == origin.doi
    assert context["candidates"][0]["doi"] == origin.doi
    assert "snapshot_json" not in context["candidates"][0]


def test_requested_doi_is_not_hidden_by_same_text_other_version():
    origin = records()[0]
    other = json.loads(origin.snapshot_json)
    other["id"] = "https://openalex.org/W9000000001"
    other["doi"] = "https://doi.org/10.5555/synthetic-other-version"
    result, _ = retrieve(
        target_plan("doi", origin.doi),
        works=[OpenAlexRecord.from_work(other), origin],
        screener=Screening(),
    )
    assert [h.document.doi for h in result.hits] == [origin.doi]


def test_explicit_date_is_not_bypassed_for_original_method():
    result, calls = retrieve(
        target_plan(), options={"date_from": "2024-01-01", "date_to": "2024-12-31"}
    )
    assert not result.hits
    assert all(str(kwargs["date_from"]) == "2024-01-01" for _, kwargs in calls)


def test_real_scope_negatives_not_promoted_by_feasibility_search():
    p = plan("liver subregion segmentation")
    p.task_intent = "feasibility"
    result, calls = retrieve(p, works=records()[2:], screener=Screening(relevance="partial"))
    assert not result.hits and len(calls) == 4
    assert all(a.relevance == "partial" for a in result.search_provenance.assessments)


def test_planner_preserves_target_and_rejects_invented_target():
    from clinical_agent.application.pico import PicoPlanner
    from clinical_agent.domain.pico import ClassificationRequest
    from clinical_agent.domain.research import ResearchError
    from tests.unit.test_intent_routing import Extractor

    extractor = Extractor("paper_explanation")
    original = extractor.extract
    target = {"kind": "method", "source_text": "nnunet"}

    def extract(request, **kwargs):
        data = json.loads(original(request, **kwargs))
        data["paper_target"] = target
        return json.dumps(data)

    extractor.extract = extract
    planner = PicoPlanner(extractor=extractor)
    request = ClassificationRequest(question="explain nnunet original paper")
    assert planner.plan(request).paper_target.source_text == "nnunet"
    target["source_text"] = "invented method"
    with pytest.raises(ResearchError, match="extraction_failed"):
        planner.plan(request)
