"""Offline TEI demo; no model, database or network."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root / "src"))
from clinical_agent.domain.openalex import OpenAlexRecord
from clinical_agent.integrations.oa_fulltext import parse_tei
folder = root / "tests/fixtures/oa_fulltext"
record = OpenAlexRecord.model_validate_json((folder / "mri-record.json").read_text(encoding="utf8"))
raw = (
    f"<TEI><teiHeader><fileDesc><titleStmt><title>{record.title}</title></titleStmt>"
    f"<sourceDesc><biblStruct><idno type=\"DOI\">{record.doi}</idno></biblStruct></sourceDesc>"
    f"</fileDesc></teiHeader><text><body><div><head>Methods</head>"
    f"<p>Synthetic methods paragraph.</p></div></body></text></TEI>"
).encode()
units = parse_tei(raw, record)
print(record.openalex_id, record.doi)
print(json.dumps([{"section": u.section, "start": u.start, "characters": len(u.text)} for u in units[:4]], ensure_ascii=True, indent=2))
