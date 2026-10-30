"""Analysis completion budget and truncation. Synthetic responses are not scientific evidence."""

import json
import logging

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.research import ResearchError
from tests.unit.test_evidence_analysis import case as case


class BudgetModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.budgets = []

    def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
        self.budgets.append(max_output_tokens)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_analysis_uses_its_own_output_budget_and_accepts_complete_json(case):
    raw = json.dumps(case[2])
    model = BudgetModel([raw])
    result = EvidenceAnalyzer(model=model, model_id="test-model").analyze(case[0], case[1])
    assert model.budgets == [16384]
    assert result.analysis_status == "partial"
    assert result.studies[0].fields["design"].evidence[0].quote == "A cohort of 20"


def test_length_retry_is_bounded_by_count_and_time(case, caplog):
    raw = json.dumps(case[2])
    model = BudgetModel(
        [ResearchError("analysis_output_truncated", details={"output_tokens": "16384"}), raw]
    )
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        result = EvidenceAnalyzer(model=model, model_id="test-model").analyze(case[0], case[1])
    assert model.budgets == [16384, 32768]
    assert result.studies
    assert "Study MRI in a cohort" not in caplog.text
    assert "A cohort of 20" not in caplog.text

    blocked = BudgetModel([ResearchError("analysis_output_truncated")])
    times = iter([0, 0, 0, 100])
    try:
        EvidenceAnalyzer(model=blocked, clock=lambda: next(times)).analyze(case[0], case[1])
    except ResearchError as error:
        assert error.code == "analysis_output_truncated"
    else:
        raise AssertionError("expired retry budget must fail")
    assert blocked.budgets == [16384]

    exhausted = BudgetModel(
        [ResearchError("analysis_output_truncated"), ResearchError("analysis_output_truncated")]
    )
    try:
        EvidenceAnalyzer(model=exhausted).analyze(case[0], case[1])
    except ResearchError as error:
        assert error.code == "analysis_output_truncated"
    else:
        raise AssertionError("second truncation must fail")
    assert exhausted.budgets == [16384, 32768]


def test_truncated_or_invalid_json_is_not_repaired(case):
    broken = BudgetModel(["{"])
    try:
        EvidenceAnalyzer(model=broken).analyze(case[0], case[1])
    except ResearchError as error:
        assert error.code == "model_output_invalid"
    else:
        raise AssertionError("truncated JSON must fail")
    assert broken.budgets == [16384]

    invalid = BudgetModel(["{}"])
    try:
        EvidenceAnalyzer(model=invalid).analyze(case[0], case[1])
    except ResearchError as error:
        assert error.code == "model_output_invalid"
    else:
        raise AssertionError("schema violations must fail")
    assert invalid.budgets == [16384]
