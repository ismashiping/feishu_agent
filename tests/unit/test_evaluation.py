"""Phase 9 deterministic evaluation contracts and denominator checks."""

import copy
import json
from pathlib import Path

import pytest

from clinical_agent.application.evaluation import evaluate

ROOT = Path(__file__).resolve().parents[2] / "evaluation/phase9-v1"


def inputs():
    return [
        json.loads((ROOT / name).read_text(encoding="utf-8"))
        for name in ("dataset.json", "observations.json", "thresholds.json")
    ]


def test_evaluation_hand_calculated():
    dataset, observations, thresholds = inputs()
    run = evaluate(dataset, observations, thresholds)
    assert run["metrics"]["recall_at_k"]["value"] == 0.5
    assert run["metrics"]["mrr"]["value"] == 0.25
    assert run["metrics"]["identity_accuracy"]["value"] == 0.5
    assert run["metrics"]["location_accuracy"]["value"] == 0.5
    assert run["metrics"]["claim_support"]["value"] == 0
    assert run["metrics"]["citation_coverage"]["value"] == 0.5
    assert run["counts"]["model_failure"] == 1
    assert run["counts"]["correct_refusal"] == 1
    assert run["overall_status"] == "fail"
    assert run == evaluate(dataset, observations, thresholds)


def test_evaluation_missing_labels_and_empty_denominators():
    dataset, observations, thresholds = inputs()
    dataset["cases"][0]["annotation_status"] = "unknown"
    run = evaluate(dataset, observations, thresholds)
    assert run["metrics"]["claim_support"]["value"] is None
    observations = [
        {"case_id": c["case_id"], "status": "dependency_failure"} for c in dataset["cases"]
    ]
    run = evaluate(dataset, observations, thresholds)
    assert run["metrics"]["identity_accuracy"]["value"] is None
    assert run["metrics"]["recall_at_k"]["value"] == 0


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "unknown", "bad_chunk"])
def test_evaluation_invalid_inputs(mutation):
    dataset, observations, thresholds = inputs()
    if mutation == "duplicate":
        dataset["cases"].append(copy.deepcopy(dataset["cases"][0]))
    elif mutation == "missing":
        observations.pop()
    elif mutation == "unknown":
        observations[0]["case_id"] = "unknown"
    else:
        dataset["cases"][0]["relevant_chunk_ids"] = ["unknown"]
    with pytest.raises(ValueError):
        evaluate(dataset, observations, thresholds)


def test_evaluation_baseline_compatibility():
    dataset, observations, thresholds = inputs()
    baseline = evaluate(dataset, observations, thresholds)
    run = evaluate(dataset, observations, thresholds, baseline)
    assert run["comparison"]["status"] == "comparable"
    dataset["version"] = "different"
    assert (
        evaluate(dataset, observations, thresholds, baseline)["comparison"]["status"]
        == "inconclusive"
    )


def test_evaluation_regression_is_gated():
    dataset, observations, thresholds = inputs()
    baseline = evaluate(dataset, observations, thresholds)
    observations[0]["retrieved_chunk_ids"] = []
    result = evaluate(dataset, observations, thresholds, baseline)
    assert set(result["comparison"]["regression_failures"]) == {"recall_at_k", "mrr"}


def test_evaluation_unknown_threshold_rejected():
    dataset, observations, thresholds = inputs()
    thresholds["metrics"]["typo"] = {"min": 0, "max": 1}
    with pytest.raises(ValueError, match="metric gates"):
        evaluate(dataset, observations, thresholds)


def test_evaluation_perfect_offline_does_not_pass_unexecuted_scopes():
    dataset, observations, thresholds = inputs()
    for rule in thresholds["metrics"].values():
        rule.update(min=0, max=1)
    observations[1] = {"case_id": "b", "status": "success"}
    result = evaluate(dataset, observations, thresholds)
    assert result["offline_status"] == "pass"
    assert result["overall_status"] == "inconclusive"


def test_evaluation_wrong_location_and_wrong_refusal():
    dataset, observations, thresholds = inputs()
    observations[0]["claims"][0]["citations"] = [
        {"chunk_id": "a", "source_id": "fixture:a", "location": "wrong"}
    ]
    observations[1] = {"case_id": "b", "status": "refusal"}
    result = evaluate(dataset, observations, thresholds)
    assert result["metrics"]["identity_accuracy"]["value"] == 1
    assert result["metrics"]["location_accuracy"]["value"] == 0
    assert result["counts"]["incorrect_refusal"] == 1
    assert result["metrics"]["refusal_accuracy"]["value"] == 0.5
