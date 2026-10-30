"""Offline real-JATS section selection; no embedding, network, DB or model calls."""

from pathlib import Path

from clinical_agent.adapters.oa_fulltext import parse_jats
from clinical_agent.application.oa_fulltext import rerank_passages
from clinical_agent.domain.openalex import OpenAlexRecord

root = Path(__file__).resolve().parents[4] / "tests/fixtures/oa_fulltext"
record = OpenAlexRecord.model_validate_json((root / "mri-record.json").read_text(encoding="utf-8"))
units = parse_jats((root / "mri-fulltext.xml").read_bytes(), record)
for unit in rerank_passages(units, "这篇研究使用哪些CT和MRI采集方案、序列及对比剂？"):
    print(unit.section, "|", unit.text[:100])
