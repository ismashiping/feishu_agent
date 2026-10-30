"""Prepare a blinded review packet from existing public snapshots; no medical labels inferred."""

import hashlib
import json
from pathlib import Path

from clinical_agent.domain.openalex import OpenAlexRecord


def main():
    source = Path("docs/openalex-stage2/live-check.json")
    output = Path("docs/openalex-stage2/followup/review")
    output.mkdir(parents=True, exist_ok=False)
    items = []
    for run in json.loads(source.read_text(encoding="utf8")):
        for raw in run.get("provenance", {}).get("records", []):
            record = OpenAlexRecord.model_validate(raw)
            record.verify_snapshot()
            key = hashlib.sha256((run["question"] + record.openalex_id).encode()).hexdigest()
            items.append(
                {
                    "review_id": key[:16],
                    "question": run["question"],
                    "id": record.openalex_id,
                    "title": record.title,
                    "publication_date": record.publication_date.model_dump(mode="json"),
                    "doi": record.doi,
                    "abstract": record.abstract,
                    "abstract_status": record.abstract_status,
                    "content_hash": record.content_hash,
                }
            )
    items.sort(key=lambda item: item["review_id"])
    decisions = [
        {
            "review_id": item["review_id"],
            "population_match": None,
            "task_match": None,
            "modality_match": None,
            "time_match": None,
            "directness": None,
            "support_quote": None,
            "reason": None,
        }
        for item in items
    ]
    for name, value in [
        ("items.json", items),
        ("decisions.json", decisions),
        (
            "signoff.json",
            {
                "reviewer": None,
                "signed_at": None,
                "decision": "pending",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "item_count": len(items),
                "independence": "Reviewer must not inspect model judgments before labeling",
            },
        ),
    ]:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({"items": len(items), "review_status": "pending", "output": str(output)}))


if __name__ == "__main__":
    main()
