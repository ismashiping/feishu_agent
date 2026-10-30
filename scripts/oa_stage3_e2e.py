"""Real HTTP acceptance of the rebuilt API; saves failures as well as answers."""

import json
import sys
from pathlib import Path
from time import monotonic
from uuid import uuid4

import httpx

from clinical_agent.domain.research import ResearchAnswer
from feishu.sender import render_answer

QUESTIONS = [
    "肝脏分割最新研究有哪些？",
    "肝脏肿瘤亚区分割最新进展有哪些？",
    "MedSAM与nnU-Net有哪些区别？",
    "最近三年MRI预测肝癌微血管侵犯有哪些研究？",
    "肝脏肿瘤分割目前有哪些技术瓶颈？",
    (
        "这篇2024年肝癌微血管侵犯双中心影像列线图研究采用了哪些CT和MRI采集方案？"
    ),
]


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
    indices = {int(i) for i in sys.argv[3].split(",")} if len(sys.argv) > 3 else set(range(1, 7))
    results = []
    with httpx.Client(timeout=130, trust_env=False) as client:
        ready = client.get(base + "/health/ready")
        ready.raise_for_status()
        (output / "ready.json").write_text(ready.text, encoding="utf-8")
        for index, question in enumerate(QUESTIONS, 1):
            if index not in indices:
                continue
            started = monotonic()
            request_id = str(uuid4())
            request = {"question": question, "scope": "hybrid"}
            if index == 6:
                # A declared positive control, using the existing public API's explicit query.
                request["openalex"] = {
                    "query": (
                        "Preoperative evaluation of microvascular invasion in hepatocellular "
                        "carcinoma with a radiological feature-based nomogram a bi-centre study"
                    ),
                    "date_from": "2024-01-01",
                    "date_to": "2024-12-31",
                }
            (output / f"q{index}-request.json").write_text(
                json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            item = {"index": index, "question": question, "request_id": request_id}
            try:
                response = client.post(
                    base + "/v1/questions", json=request, headers={"X-Request-ID": request_id}
                )
                item["http_status"] = response.status_code
                (output / f"q{index}-response.json").write_text(response.text, encoding="utf-8")
                if response.status_code == 200:
                    answer = ResearchAnswer.model_validate_json(response.text)
                    assert str(answer.request_id) == request_id
                    assert answer.retrieval_scope == "hybrid"
                    for source in answer.sources:
                        if source.openalex_record is not None:
                            source.openalex_record.verify_snapshot()
                    evidence = [e for s in answer.sources for e in s.evidence]
                    provenance = answer.search_provenance
                    item.update(
                        status=answer.status,
                        sources=len(answer.sources),
                        claims=len(answer.claims),
                        fulltext_citations=sum(e.location.kind == "fulltext" for e in evidence),
                        citation_identity_checked=True,
                        warnings=answer.retrieval_warnings,
                        search_status=provenance.status if provenance else None,
                        evidence_gaps=provenance.evidence_gaps if provenance else [],
                        date_from=str(provenance.date_from) if provenance else None,
                        date_to=str(provenance.date_to) if provenance else None,
                        dates=[s.publication_date.raw for s in answer.sources],
                    )
                    (output / f"q{index}-answer.txt").write_text(
                        render_answer(answer), encoding="utf-8"
                    )
                else:
                    item["status"] = "http_error"
                    item["error"] = response.json().get("error_code", "unknown")
            except httpx.RequestError as error:
                item.update(status="transport_error", error=type(error).__name__)
            item["seconds"] = round(monotonic() - started, 3)
            results.append(item)
            (output / "summary.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(item, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
