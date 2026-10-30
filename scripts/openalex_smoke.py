"""Real transport smoke; no LLM, ingestion or fulltext claims."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clinical_agent.adapters.openalex import open_openalex


def main():
    with open_openalex() as client:
        records, count, warnings = client.search(
            "liver segmentation",
            date_from=None,
            date_to=None,
            sort="relevance_score:desc",
            timeout_seconds=15,
        )
    print(
        json.dumps(
            {
                "count": count,
                "records": len(records),
                "ids": [r.openalex_id for r in records],
                "warnings": warnings,
                "scope": "transport only",
            }
        )
    )


if __name__ == "__main__":
    main()
