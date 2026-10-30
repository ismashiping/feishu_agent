"""Deterministic replay scoring; reviewed labels are supplied, never generated here."""

import hashlib
import json
from collections import Counter
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def evaluate(
    dataset: dict[str, Any],
    observations: list[dict[str, Any]],
    thresholds: dict[str, Any],
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cases = dataset["cases"]
    ids = [c["case_id"] for c in cases]
    observed_ids = [o["case_id"] for o in observations]
    if (
        not cases
        or len(ids) != len(set(ids))
        or len(observed_ids) != len(set(observed_ids))
        or set(ids) != set(observed_ids)
    ):
        raise ValueError("duplicate, missing or unknown case_id")
    known_metrics = {
        "recall_at_k",
        "mrr",
        "identity_accuracy",
        "location_accuracy",
        "claim_support",
        "citation_coverage",
        "success_rate",
        "refusal_accuracy",
        "allowed_claim_recall",
        "forbidden_claim_rate",
    }
    if not thresholds["metrics"] or not thresholds["metrics"].keys() <= known_metrics:
        raise ValueError("missing or unknown metric gates")
    for rule in thresholds["metrics"].values():
        if not 0 <= rule["min"] <= rule["max"] <= 1:
            raise ValueError("invalid threshold range")
    for case in cases:
        if case["annotation_status"] not in {"reviewed", "unknown", "disagreement"}:
            raise ValueError("unknown annotation status")
        if case["evidence_scope"] not in {"evidence", "no_evidence"}:
            raise ValueError("unknown evidence scope")
        if case["evidence_scope"] == "no_evidence" and case["relevant_chunk_ids"]:
            raise ValueError("no_evidence case cannot have relevant chunks")
        if any(
            not set(chunks) <= case["source_snapshots"].keys()
            for chunks in case.get("supported_by", {}).values()
        ):
            raise ValueError("support annotation points to unknown chunk")
    k = thresholds["k"]
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be positive integer")
    totals: dict[str, list[float]] = {
        name: [0.0, 0.0]
        for name in (
            "recall_at_k",
            "mrr",
            "identity_accuracy",
            "location_accuracy",
            "claim_support",
            "citation_coverage",
            "success_rate",
            "refusal_accuracy",
            "allowed_claim_recall",
            "forbidden_claim_rate",
        )
    }
    unknown_support = False
    unknown_claims = False
    counts: Counter[str] = Counter()
    samples = []
    by_id = {o["case_id"]: o for o in observations}
    for case in cases:
        observation = by_id[case["case_id"]]
        status = observation["status"]
        if status not in {"success", "refusal", "model_failure", "dependency_failure", "not_run"}:
            raise ValueError("unknown observation status")
        counts[status] += 1
        sources = case["source_snapshots"]
        relevant = set(case["relevant_chunk_ids"])
        if not relevant <= sources.keys():
            raise ValueError("unknown relevant chunk")
        ranked = observation.get("retrieved_chunk_ids", [])[:k]
        if len(ranked) != len(set(ranked)):
            raise ValueError("duplicate retrieved chunk")
        if status != "success":
            ranked = []
        if relevant:
            totals["recall_at_k"][0] += len(set(ranked) & relevant) / len(relevant)
            totals["recall_at_k"][1] += 1
            totals["mrr"][0] += next(
                (1 / (i + 1) for i, c in enumerate(ranked) if c in relevant), 0
            )
            totals["mrr"][1] += 1
        correct_refusal = status == "refusal" and case["evidence_scope"] == "no_evidence"
        if status == "refusal":
            counts["correct_refusal" if correct_refusal else "incorrect_refusal"] += 1
        totals["success_rate"][0] += status == "success" or correct_refusal
        totals["success_rate"][1] += 1
        if case["evidence_scope"] == "no_evidence" or status == "refusal":
            totals["refusal_accuracy"][0] += correct_refusal
            totals["refusal_accuracy"][1] += 1
        claims = observation.get("claims", []) if status == "success" else []
        if len({c["claim_id"] for c in claims}) != len(claims):
            raise ValueError("duplicate claim")
        emitted = {c["claim_id"] for c in claims}
        reviewed = case["annotation_status"] == "reviewed"
        if not reviewed:
            unknown_claims = True
        else:
            expected = set(case["expected_claims"])
            totals["allowed_claim_recall"][0] += len(expected & emitted)
            totals["allowed_claim_recall"][1] += len(expected)
            totals["forbidden_claim_rate"][0] += len(set(case["forbidden_claims"]) & emitted)
            totals["forbidden_claim_rate"][1] += len(emitted)
        checks = []
        for claim in claims:
            citations = claim.get("citations", [])
            totals["citation_coverage"][0] += bool(citations)
            totals["citation_coverage"][1] += 1
            supported = False
            for citation in citations:
                source = sources.get(citation["chunk_id"])
                identity = source is not None and citation.get("source_id") == source["source_id"]
                location = bool(identity and citation.get("location") == source["location"])
                for metric_name, valid in (
                    ("identity_accuracy", identity),
                    ("location_accuracy", location),
                ):
                    totals[metric_name][0] += valid
                    totals[metric_name][1] += 1
                supported |= bool(
                    location
                    and citation["chunk_id"]
                    in case.get("supported_by", {}).get(claim["claim_id"], [])
                )
                checks.append(
                    {
                        "claim_id": claim["claim_id"],
                        "citation": citation,
                        "identity_valid": identity,
                        "location_valid": location,
                    }
                )
            if reviewed:
                totals["claim_support"][0] += supported
                totals["claim_support"][1] += 1
            else:
                unknown_support = True
        samples.append(
            {
                "case_id": case["case_id"],
                "observation": observation,
                "citation_checks": checks,
                "annotation_status": case["annotation_status"],
            }
        )
    metrics = {}
    for name, (numerator, denominator) in totals.items():
        missing = (name == "claim_support" and unknown_support) or (
            name in {"allowed_claim_recall", "forbidden_claim_rate"} and unknown_claims
        )
        value = numerator / denominator if denominator and not missing else None
        rule = thresholds["metrics"].get(name)
        state = "inconclusive" if value is None else "not_gated"
        if value is not None and rule is not None:
            state = "pass" if rule["min"] <= value <= rule["max"] else "fail"
        metrics[name] = {
            "value": value,
            "numerator": numerator,
            "denominator": denominator,
            "status": state,
            "threshold": rule,
        }
    compatibility = digest({"dataset": dataset, "thresholds": thresholds})
    comparison: dict[str, Any] = {"status": "not_requested"}
    if baseline is not None:
        comparison = {"status": "inconclusive"}
        if baseline.get("compatibility") == compatibility:
            deltas = {}
            for name, metric in metrics.items():
                previous = baseline["metrics"][name]["value"]
                if previous is not None and metric["value"] is not None:
                    deltas[name] = metric["value"] - previous
            comparison = {"status": "comparable", "deltas": deltas}
    regression_failures = []
    if comparison["status"] == "comparable":
        for name, tolerance in thresholds.get("regression_tolerance", {}).items():
            delta = comparison["deltas"].get(name)
            if delta is None:
                comparison["status"] = "inconclusive"
            elif (delta if name == "forbidden_claim_rate" else -delta) > tolerance:
                regression_failures.append(name)
    comparison["regression_failures"] = regression_failures
    states = [m["status"] for m in metrics.values() if m["threshold"] is not None]
    if counts["model_failure"] or counts["dependency_failure"] or regression_failures:
        states.append("fail")
    if counts["not_run"] or comparison["status"] == "inconclusive":
        states.append("inconclusive")
    overall = (
        "fail"
        if "fail" in states
        else ("inconclusive" if "inconclusive" in states or not states else "pass")
    )
    return {
        "dataset_version": dataset["version"],
        "dataset_kind": dataset["kind"],
        "scope": "offline_replay",
        "compatibility": compatibility,
        "observations_sha256": digest(observations),
        "metrics": metrics,
        "counts": dict(counts),
        "samples": samples,
        "comparison": comparison,
        "offline_status": overall,
        "overall_status": "fail" if overall == "fail" else "inconclusive",
        "unexecuted_scopes": ["real_model", "external", "medical_review", "service_load"],
    }
