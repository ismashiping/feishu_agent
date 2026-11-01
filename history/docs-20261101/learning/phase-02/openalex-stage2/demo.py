"""Offline demo grounded in saved real OpenAlex metadata."""
import sys
from datetime import date
from pathlib import Path
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from clinical_agent.domain.openalex import OpenAlexRecord, ResearchConstraints, resolve_dates
root = Path(__file__).resolve().parents[4]
works = json.loads((root / "tests/fixtures/openalex/organ.json").read_text(encoding="utf8"))["results"]
record = OpenAlexRecord.from_work(works[0])
record.verify_snapshot()
print(record.openalex_id, record.title)
print("Abstract scope:", record.abstract_status)
print("Latest window:", resolve_dates(ResearchConstraints(time_intent="latest", time_text="最新"), date(2026, 10, 29)))
