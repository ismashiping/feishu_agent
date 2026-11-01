"""Offline TEI section selection; no embedding, network, DB or model calls."""

from pathlib import Path

from clinical_agent.integrations.oa_fulltext import parse_tei
from clinical_agent.application.oa_fulltext import rerank_passages
from clinical_agent.domain.openalex import OpenAlexRecord

root = Path(__file__).resolve().parents[4] / "tests/fixtures/oa_fulltext"
record = OpenAlexRecord.model_validate_json((root / "mri-record.json").read_text(encoding="utf-8"))
raw = f"""<TEI><teiHeader><fileDesc><titleStmt><title>{record.title}</title></titleStmt>
<sourceDesc><biblStruct><idno type="DOI">{record.doi}</idno></biblStruct></sourceDesc>
</fileDesc></teiHeader><text><body>
<div><head>Methods</head><p>Synthetic methods paragraph for the demo.</p></div>
<div><head>Results</head><p>Synthetic results paragraph for the demo.</p></div>
</body></text></TEI>""".encode()
units = parse_tei(raw, record)
for unit in rerank_passages(units, "这篇研究使用哪些CT和MRI采集方案、序列及对比剂？"):
    print(unit.section, "|", unit.text[:100])
