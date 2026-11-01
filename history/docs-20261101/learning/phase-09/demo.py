"""Run the hand-calculated synthetic example without external services."""

import json
from pathlib import Path

from clinical_agent.application.evaluation import evaluate

root = Path(__file__).resolve().parents[3] / "evaluation/phase9-v1"
inputs = [
    json.loads((root / name).read_text(encoding="utf-8"))
    for name in ("dataset.json", "observations.json", "thresholds.json")
]
result = evaluate(*inputs)
print(result["overall_status"], result["metrics"]["mrr"])
