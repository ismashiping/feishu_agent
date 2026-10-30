import json

import pytest

from tests.unit.test_citation_report import Review, Snapshots
from tests.unit.test_evidence_analysis import Model
from tests.unit.test_evidence_analysis import case as case


def service(case, statuses, rounds=1):
    from clinical_agent.application.analysis import EvidenceAnalyzer
    from clinical_agent.application.report import ReportBuilder
    from clinical_agent.application.research import ResearchService

    class Retriever:
        calls = 0

        def retrieve(self, request):
            self.calls += 1
            return case[1]

    class Reviewer(Review):
        calls = 0

        def review_claims(self, context, **kwargs):
            state = statuses[min(self.calls, len(statuses) - 1)]
            self.calls += 1
            result = json.loads(super().review_claims(context, **kwargs))
            for r in result["reviews"]:
                r["support_status"] = state
            return json.dumps(result)

    reviewer, model, retriever = Reviewer(), Model(case[2]), Retriever()
    svc = ResearchService(
        retriever=retriever,
        generator=object(),
        analyzer=EvidenceAnalyzer(model=model),
        reporter=ReportBuilder(reviewer=reviewer, snapshots=Snapshots()),
        max_feedback_rounds=rounds,
    )
    return svc, reviewer, model, retriever


def test_feedback_reanalysis_rebuilds_report(case):
    svc, reviewer, model, retriever = service(case, ["unsupported", "supported"])
    result = svc.report(case[0]).report
    assert model.calls == reviewer.calls == 2 and retriever.calls == 1
    assert result.status != "rejected"
    assert result.feedback_history[0]["target"] == "methods"


def test_feedback_exhaustion_does_not_publish(case):
    svc, reviewer, model, _ = service(case, ["unsupported"])
    report = svc.report(case[0]).report
    assert report.status == "rejected" and reviewer.calls == model.calls == 2
    assert report.feedback_stop == "round_limit"


def test_zero_feedback_compatible(case):
    svc, reviewer, _, _ = service(case, ["unsupported"], 0)
    assert svc.report(case[0]).report.status == "rejected"
    assert reviewer.calls == 1


@pytest.mark.parametrize("rounds", [-1, 3, True, 1.5])
def test_invalid_feedback_limit(case, rounds):
    with pytest.raises(ValueError):
        service(case, ["supported"], rounds)


def test_empty_retrieval_feedback_rebuilds_from_new_evidence(case):
    svc, reviewer, model, retriever = service(case, ["supported"])
    original = retriever.retrieve

    def retrieve(request):
        result = original(request)
        return result.model_copy(update={"hits": []}) if retriever.calls == 1 else result

    retriever.retrieve = retrieve
    report = svc.report(case[0]).report
    assert retriever.calls == 2 and model.calls == reviewer.calls == 1
    assert report.feedback_history[0]["target"] == "scout"
    assert report.claims


def test_invalid_source_cannot_be_repaired_by_feedback(case):
    svc, reviewer, model, _ = service(case, ["unsupported"])

    class Invalid:
        def check(self, *args):
            return "invalid"

    svc._reporter.snapshots = Invalid()
    assert svc.report(case[0]).report.status == "rejected"
    assert reviewer.calls == model.calls == 1


def test_design_keeps_hypothesis_and_evidence(case):
    import copy

    item = copy.deepcopy(case[2]["studies"][0]["fields"]["design"])
    item.update(
        value="Investigate additional cohorts",
        epistemic_kind="unverified_hypothesis",
        basis="model_inference",
        verification_needed="Review feasibility and counter evidence",
    )
    case[2]["candidate_gaps"] = [
        {
            "description": item,
            "counter_evidence": [],
            "reasoning": "Limited supplied cohort",
            "scope": "Supplied evidence only",
        }
    ]
    svc, _, _, _ = service(case, ["supported"])
    report = svc.report(case[0]).report
    design = report.research_designs[0]
    assert design["epistemic_kind"] == "unverified_hypothesis"
    assert design["verification_needed"] and design["evidence_chunk_ids"]
    assert design["reference_method_profiles"]
    assert set(svc._graph.get_graph().nodes) >= {"prior_art", "design", "report", "feedback"}


def test_empty_exhaustion_is_incomplete(case):
    svc, reviewer, model, retriever = service(case, ["supported"])
    empty = case[1].model_copy(update={"hits": []})
    retriever.retrieve = lambda request: empty
    report = svc.report(case[0]).report
    assert report.content_status == "insufficient_evidence"
    assert report.status == "verification_incomplete" and report.feedback_stop == "round_limit"
    assert reviewer.calls == model.calls == 0
