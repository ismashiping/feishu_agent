"""Offline real JATS demo; no model, database or network."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root / "src"))
from clinical_agent.domain.openalex import OpenAlexRecord
from clinical_agent.adapters.oa_fulltext import parse_jats
folder = root / "tests/fixtures/oa_fulltext"
record = OpenAlexRecord.model_validate_json((folder / "mri-record.json").read_text(encoding="utf8"))
units = parse_jats((folder / "mri-fulltext.xml").read_bytes(), record)
print(record.openalex_id, record.doi)
print(json.dumps([{"section": u.section, "start": u.start, "characters": len(u.text)} for u in units[:4]], ensure_ascii=True, indent=2))
