"""Analysis failures stay distinguishable without logging payloads."""

import copy
import json
import logging

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.research import ResearchError
from tests.unit.test_evidence_analysis import case as case


class _Model:
    def __init__(self, raw, details=None):
        self.raw = raw
        self.completion_details = details or {}
        self.calls = 0

    def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
        self.calls += 1
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


def _analyze(records):
    return next(
        record for record in records if getattr(record, "evidence_stage", None) == "analyze"
    )


def _blob(record) -> str:
    return " ".join(str(getattr(record, key, "")) for key in record.__dict__)


def test_complete_json_returns_analysis_result(case):
    result = EvidenceAnalyzer(model=_Model(json.dumps(case[2]))).analyze(case[0], case[1])
    assert result.analysis_status == "partial"
    assert result.studies[0].fields["design"].evidence[0].quote == "A cohort of 20"


def test_invalid_json_is_json_decode_failed(case, caplog):
    secret = "NOTJSON-secret-body"
    model = _Model(
        secret,
        {
            "finish_reason": "stop",
            "output_tokens": "20",
            "input_tokens": "11",
            "reasoning_tokens": "0",
        },
    )
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=model).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("invalid JSON must fail")
    record = _analyze(caplog.records)
    assert record.failure_kind == "json_decode"
    assert record.rule_code == "json_decode_failed"
    assert "schema_status=not_run" in record.evidence_counts
    assert "output_tokens=20" in record.evidence_counts
    assert "reasoning_tokens=0" in record.evidence_counts
    assert record.finish_reason == "stop"
    assert "schema_validation" not in _blob(record)
    assert secret not in _blob(record)
    assert case[0].question not in _blob(record)


def test_wrong_field_type_records_schema_path(case, caplog):
    payload = copy.deepcopy(case[2])
    payload["studies"][0]["study_type"] = "LEAKED_TYPE_VALUE"
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=_Model(json.dumps(payload))).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("schema violations must fail")
    record = _analyze(caplog.records)
    assert record.failure_kind == "schema_validation"
    assert "schema_status=rejected" in record.evidence_counts
    assert record.field_paths == "studies.0.study_type"
    assert "literal_error" in record.rule_code
    assert "LEAKED_TYPE_VALUE" not in _blob(record)
    assert case[0].question not in _blob(record)
    assert "A cohort of 20" not in _blob(record)


def test_business_rule_is_not_a_schema_failure(case, caplog):
    payload = copy.deepcopy(case[2])
    payload["idea_similarities"][0]["overall_relation"] = "overlap"
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=_Model(json.dumps(payload))).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("business rule must fail")
    record = _analyze(caplog.records)
    assert record.failure_kind == "business_validation"
    assert record.rule_code == "overall_relation"
    assert "schema_status=accepted" in record.evidence_counts
    assert case[0].question not in _blob(record)


def test_unknown_evidence_pointer_is_rejected(case, caplog):
    payload = copy.deepcopy(case[2])
    item = payload["studies"][0]["fields"]["design"]
    item["value"] = "INVENTED_QUOTE_TOKEN"
    item["evidence"] = [
        {"chunk_id": item["evidence"][0]["chunk_id"], "quote": "INVENTED_QUOTE_TOKEN"}
    ]
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=_Model(json.dumps(payload))).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("false evidence must fail")
    record = _analyze(caplog.records)
    assert record.failure_kind == "evidence_validation"
    assert record.rule_code == "evidence_pointer_invalid"
    assert record.field_paths == "studies.fields.evidence"
    assert "INVENTED_QUOTE_TOKEN" not in _blob(record)
    assert "insufficient_evidence" not in _blob(record)


def test_truncation_stays_on_the_existing_code(case, caplog):
    model = _Model(
        ResearchError(
            "analysis_output_truncated",
            details={"finish_reason": "length", "output_tokens": "16384", "reasoning_tokens": "0"},
        )
    )
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=model).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "analysis_output_truncated"
        else:
            raise AssertionError("truncation must stay truncated")
    record = _analyze(caplog.records)
    assert record.failure_kind == "analysis_output_truncated"
    assert "schema_status=not_run" in record.evidence_counts
    assert record.finish_reason == "length"
    assert "output_tokens=16384" in record.evidence_counts
    assert "schema_validation" not in _blob(record)
    assert model.calls == 2


def test_unknown_exception_stays_a_safe_failure(case, caplog):
    leaked = "raw exception " + case[0].question + " sk-testsecret"
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=_Model(RuntimeError(leaked))).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("unknown failures must fail closed")
    record = _analyze(caplog.records)
    assert record.failure_kind == "unknown_failure"
    assert record.rule_code == "unknown_failure"
    assert "schema_status=not_run" in record.evidence_counts
    assert leaked not in _blob(record)
    assert "sk-testsecret" not in _blob(record)
    assert "RuntimeError" not in _blob(record)


def test_missing_usage_stays_unknown_and_empty_hits_stay_honest(case, caplog):
    model = _Model("{", {"output_tokens": "sk-testsecret", "finish_reason": "not a reason"})
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            EvidenceAnalyzer(model=model).analyze(case[0], case[1])
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("broken JSON must fail")
    record = _analyze(caplog.records)
    assert "output_tokens=unknown" in record.evidence_counts
    assert "input_tokens=unknown" in record.evidence_counts
    assert "sk-testsecret" not in _blob(record)
    assert not hasattr(record, "finish_reason") or record.finish_reason != "not a reason"

    empty = case[1].model_copy(update={"hits": []})
    result = EvidenceAnalyzer(model=_Model("{}")).analyze(case[0], empty)
    assert result.analysis_status == "insufficient_evidence"


def test_provider_and_plan_errors_are_not_relabelled(case):
    try:
        EvidenceAnalyzer(model=_Model(ResearchError("generation_failed"))).analyze(case[0], case[1])
    except ResearchError as error:
        assert error.code == "generation_failed"
    else:
        raise AssertionError("provider failures must pass through")
