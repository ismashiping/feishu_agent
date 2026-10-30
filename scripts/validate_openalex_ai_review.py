"""Validate this review batch's identity, grounding and unsigned expert status."""

import hashlib
import json
from collections import Counter
from pathlib import Path


def main():
    root = Path("docs/openalex-stage2/followup/review")
    items = json.loads((root / "items.json").read_text(encoding="utf8"))
    decisions = json.loads((root / "ai-decisions.json").read_text(encoding="utf8"))
    freeze = json.loads((root / "ai-freeze.json").read_text(encoding="utf8"))
    by_id = {item["review_id"]: item for item in items}
    assert len(decisions) == len(by_id) == 106
    assert {d["review_id"] for d in decisions} == set(by_id)
    for decision in decisions:
        item = by_id[decision["review_id"]]
        assert decision["question"] == item["question"]
        assert decision["openalex_id"] == item["id"]
        assert decision["directness"] in {"direct", "partial", "irrelevant", "uncertain"}
        for key in ["population_match", "task_match", "modality_match", "time_match"]:
            assert decision[key] in [True, False, "not_applicable", "unknown"]
            if decision["directness"] == "direct":
                assert decision[key] in [True, "not_applicable"]
        quote = decision["support_quote"]
        assert quote and (quote in item["title"] or quote in item["abstract"])
        assert decision["expert_signoff"] == "pending"
        assert decision["reviewer_kind"] == "same_development_agent_ai"
    for filename, key in [
        ("items.json", "items_sha256"),
        ("ai-decisions.json", "decisions_sha256"),
    ]:
        assert hashlib.sha256((root / filename).read_bytes()).hexdigest() == freeze[key]
    expert = json.loads((root / "signoff.json").read_text(encoding="utf8"))
    human = json.loads((root / "decisions.json").read_text(encoding="utf8"))
    assert expert["reviewer"] is None and expert["decision"] == "pending"
    assert all(d["directness"] is None for d in human)
    print(
        json.dumps(
            {
                "review_items": len(decisions),
                "ai_counts": dict(Counter(d["directness"] for d in decisions)),
                "identity_quote_hash_checks": "passed",
                "independent_expert_review": "pending",
            }
        )
    )


if __name__ == "__main__":
    main()
