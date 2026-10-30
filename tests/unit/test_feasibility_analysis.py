"""Synthetic feasibility contracts, not independent scientific evaluation."""

import copy

import pytest

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.analysis import AnalysisDraft
from clinical_agent.domain.report import render_report
from clinical_agent.domain.research import ResearchError
from tests.unit.test_evidence_analysis import Model
from tests.unit.test_evidence_analysis import case as case
from tests.unit.test_feedback_agents import service
from tests.unit.test_openalex import plan


def payload(case):
    data = copy.deepcopy(case[2])
    item = copy.deepcopy(data["studies"][0]["fields"]["design"])
    item.update(
        value="Assess transfer with a small pilot",
        epistemic_kind="model_inference",
        basis="model_inference",
        verification_needed="Run a held-out pilot",
    )
    data["feasibility"] = [
        dict(
            dimension=d,
            status="conditional",
            assessment=copy.deepcopy(item),
            next_check="Confirm data and reproduce baseline",
        )
        for d in ["data", "methods", "compute", "validation"]
    ]
    data["candidate_gaps"] = [
        dict(
            description=copy.deepcopy(item),
            counter_evidence=[],
            reasoning="Only supplied cohort",
            scope="Supplied passages",
        )
    ]
    data["experiments"] = [
        dict(
            gap_index=0,
            **{
                name: copy.deepcopy(item)
                for name in ["hypothesis", "baseline", "experiment", "metrics", "failure_criterion"]
            },
        )
    ]
    return data


def analyze(case, data, empty=False):
    p = plan(case[0].question)
    p.task_intent = "feasibility"
    model = Model(data)
    result = EvidenceAnalyzer(model=model).analyze(
        case[0], case[1].model_copy(update={"hits": []}) if empty else case[1], query_plan=p
    )
    return result, model


def test_four_dimensions_and_candidate_experiment(case):
    result, model = analyze(case, payload(case))
    assert len(result.feasibility) == 4 and model.calls == 1
    assert result.experiments[0].gap_index == 0
    assert result.experiments[0].hypothesis.epistemic_kind == "model_inference"


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "quote", "gap", "fact"])
def test_invalid_feasibility_rejected(case, mutation):
    data = payload(case)
    if mutation == "duplicate":
        data["feasibility"][1]["dimension"] = "data"
    elif mutation == "missing":
        data["feasibility"].pop()
    elif mutation == "quote":
        data["feasibility"][0]["assessment"]["evidence"][0]["quote"] = "fabricated source text"
    elif mutation == "gap":
        data["experiments"][0]["gap_index"] = 99
    else:
        data["experiments"][0]["hypothesis"] = copy.deepcopy(data["studies"][0]["fields"]["design"])
    with pytest.raises(ResearchError, match="model_output_invalid"):
        analyze(case, data)


def test_no_evidence_has_unknowns_without_model_or_experiments(case, caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        result, model = analyze(case, {}, empty=True)
    assert model.calls == 0 and result.analysis_status == "insufficient_evidence"
    record = next(r for r in caplog.records if getattr(r, "evidence_stage", None) == "analyze")
    assert record.failure_kind == "insufficient_evidence"
    assert record.evidence_counts == "hits=0,sources=0"
    assert case[0].question not in record.getMessage()
    assert len(result.feasibility) == 4 and not result.experiments
    assert all(x.status == "unknown" and x.assessment.value is None for x in result.feasibility)


def test_report_contains_reviewed_feasibility_and_experiments(case):
    case[2].update(payload(case))
    svc, reviewer, _, _ = service(case, ["supported"])
    report = svc.report(case[0]).report
    text = render_report(report)
    assert reviewer.calls == 1
    assert "可行性" in text and "最小实验" in text
    assert any("可行性" in c.text and c.evidence for c in report.claims)
    assert all(c.support_status == "supported" for c in report.claims if "最小实验" in c.text)


def test_legacy_draft_defaults_are_empty(case):
    result = AnalysisDraft.model_validate(case[2])
    assert result.feasibility == result.experiments == []


def test_unknown_condition_cannot_be_claimed_as_supported(case):
    data = payload(case)
    missing = copy.deepcopy(data["studies"][0]["fields"]["data_sources"])
    data["feasibility"][0].update(status="unknown", assessment=missing)
    case[2].update(data)
    svc, _, _, _ = service(case, ["supported"])
    report = svc.report(case[0]).report
    claim = next(c for c in report.claims if "可行性（data" in c.text)
    assert claim.information_missing and claim.support_status == "uncertain"
    assert report.status == "verification_incomplete"


def test_report_rejects_unsupported_feasibility_claims(case):
    case[2].update(payload(case))
    svc, _, _, _ = service(case, ["unsupported"], rounds=0)
    assert svc.report(case[0]).report.status == "rejected"
