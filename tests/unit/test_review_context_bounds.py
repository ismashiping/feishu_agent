import json

from clinical_agent.application.report import ReportBuilder
from clinical_agent.domain.research import ResearchLimits
from tests.unit.test_citation_report import Review, Snapshots
from tests.unit.test_citation_report import report_case as report_case
from tests.unit.test_evidence_analysis import case as case


def test_review_batches_cover_claims_with_bounded_exact_quotes(report_case):
    case, analysis = report_case
    study = analysis.studies[0]
    original = study.fields["design"]
    for name in study.fields:
        study.fields[name] = original.model_copy(deep=True)
    sizes, ids = [], []

    class Reviewer(Review):
        def review_claims(self, context, **kwargs):
            sizes.append(len(json.dumps(context, ensure_ascii=False)))
            ids.extend(c["claim_id"] for c in context["claims"])
            assert sizes[-1] <= 5000
            for source in context["sources"]:
                for evidence in source["evidence"]:
                    assert evidence["text"] in case[1].hits[0].chunk.text
            return super().review_claims(context, **kwargs)

    report = ReportBuilder(
        reviewer=Reviewer(),
        snapshots=Snapshots(),
        limits=ResearchLimits(max_context_characters=5000),
    ).build(case[0], analysis, case[1])
    assert len(sizes) > 1
    assert set(ids) == {c.claim_id for c in report.claims}
    assert len(ids) == len(report.claims)


def test_analysis_bounds_keep_each_paper_and_reject_omitted_quotes():
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from tests.unit.test_openalex_report_contract import service_case

    _, request, retrieval = service_case()
    for hit in retrieval.hits:
        for passage in hit.fulltext:
            passage.text = "A synthetic method uses a public dataset. " * 50
            passage.end = passage.start + len(passage.text)

    class Model:
        def analyze_evidence(self, context, **kwargs):
            assert len(json.dumps(context, ensure_ascii=False)) <= 24000
            assert len({q["document_id"] for q in context["quotes"]}) == 2
            assert len(context["quotes"]) < 300
            return json.dumps(dict(studies=[], similarities=[]))

    result = EvidenceAnalyzer(
        model=Model(), limits=ResearchLimits(max_context_characters=24000)
    ).analyze(request, retrieval)
    assert result.analysis_status == "partial"
    assert any("reduced" in note for note in result.limitations)
    assert len(result.sources) == 2


def test_review_includes_user_idea_and_comparison_dimension(report_case):
    case, analysis = report_case
    dimension = analysis.idea_similarities[0].dimensions["methods"]
    dimension.idea_quote = "MRI"
    dimension.relation = "overlap"
    dimension.evidence = [analysis.studies[0].fields["design"].evidence[0].model_copy()]
    analysis.idea_similarities[0].overall_relation = "unknown"
    received = []

    class Reviewer(Review):
        def review_claims(self, context, **kwargs):
            received.append(context)
            return super().review_claims(context, **kwargs)

    ReportBuilder(reviewer=Reviewer(), snapshots=Snapshots()).build(case[0], analysis, case[1])
    assert received[0]["original_idea"] == case[0].question
    assert received[0]["research_constraints"] is None
    comparison = received[0]["idea_comparisons"][0]
    assert comparison["dimension"] == "methods"
    assert comparison["idea_quote"] == "MRI"
    assert comparison["document_id"] == str(analysis.sources[0].document_id)


def test_real_saved_plan_constraints_reach_reviewer():
    from pathlib import Path

    from clinical_agent.domain.analysis import AnalysisResult
    from clinical_agent.domain.research import QuestionRequest
    from clinical_agent.domain.retrieval import RetrievalResult
    from clinical_agent.integrations.report_snapshot import SnapshotVerifier

    root = Path("docs/acceptance/live-report-context-restored-20261102")
    baseline = json.loads((root / "cold-report.json").read_text(encoding="utf8"))["report"]
    analysis = AnalysisResult.model_validate(baseline["analysis"])
    retrieval = RetrievalResult.model_validate_json(
        (root / "cold-fulltext_rag.json").read_text(encoding="utf8")
    )
    received = []

    class Reviewer(Review):
        def review_claims(self, context, **kwargs):
            received.append(context)
            assert context["original_idea"] == analysis.original_idea
            assert context["research_constraints"] == (
                analysis.query_plan.research_constraints.model_dump(mode="json")
            )
            for item in context["idea_comparisons"]:
                assert item["idea_quote"] in analysis.original_idea
            return super().review_claims(context, **kwargs)

    request = QuestionRequest(
        request_id=analysis.request_id,
        question=analysis.original_idea,
        scope=retrieval.scope,
        options=retrieval.options,
    )
    result = ReportBuilder(reviewer=Reviewer(), snapshots=SnapshotVerifier()).build(
        request, analysis, retrieval
    )
    assert received and received[0]["idea_comparisons"]
    assert result.claims


def test_review_output_budget_limits_claims_even_when_input_fits(report_case):
    case, analysis = report_case
    study = analysis.studies[0]
    for name in study.fields:
        study.fields[name] = study.fields["design"].model_copy(deep=True)
    batches = []

    class Reviewer(Review):
        def review_claims(self, context, **kwargs):
            batches.append([c["claim_id"] for c in context["claims"]])
            return super().review_claims(context, **kwargs)

    report = ReportBuilder(reviewer=Reviewer(), snapshots=Snapshots()).build(
        case[0], analysis, case[1]
    )
    assert all(len(batch) <= 6 for batch in batches)
    ids = [identity for batch in batches for identity in batch]
    assert len(ids) == len(set(ids)) == len(report.claims)
    assert set(ids) == {c.claim_id for c in report.claims}


def test_truncated_review_error_preserves_safe_completion_reason():
    import httpx
    import pytest

    from clinical_agent.domain.research import ResearchError
    from clinical_agent.integrations.llm import _guard_response

    request = httpx.Request("POST", "https://example.org/chat", json={"max_tokens": 1500})
    response = httpx.Response(
        200,
        request=request,
        json={
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"role": "assistant", "content": "PRIVATE-INCOMPLETE-RESPONSE"},
                }
            ],
            "usage": {"completion_tokens": 1500, "prompt_tokens": 11011},
        },
    )
    with pytest.raises(ResearchError) as caught:
        _guard_response(response)
    assert caught.value.details["finish_reason"] == "length"
    assert caught.value.details["output_tokens"] == "1500"
    assert "PRIVATE" not in str(caught.value.details)
