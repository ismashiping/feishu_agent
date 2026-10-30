"""Opt-in read-only corpus check through the real runtime; no bot sends or fulltext writes."""

import json
import sys
from pathlib import Path
from time import monotonic
from uuid import uuid4

from clinical_agent.command_runtime import open_research
from clinical_agent.domain.research import QuestionRequest, ResearchError
from clinical_agent.domain.retrieval import RetrievalError
from feishu.sender import render_answer


def main():
    output = Path(sys.argv[1])
    output.mkdir(exist_ok=False)
    started = monotonic()
    summary = {
        "question": "肝脏分割最新研究有哪些？",
        "scope": "hybrid",
        "fulltext_enrichment": "disabled for this isolated instance",
        "human_medical_review": "pending",
        "feishu_send": "not executed",
    }
    try:
        with open_research(Path("/app/model")) as service:
            service._fulltext = None
            answer = service.answer(
                QuestionRequest(request_id=uuid4(), question=summary["question"], scope="hybrid")
            )
        (output / "answer.json").write_text(answer.model_dump_json(indent=2), encoding="utf8")
        (output / "answer.txt").write_text(render_answer(answer), encoding="utf8")
        summary.update(
            status=answer.status,
            source_count=len(answer.sources),
            source_types=[s.source_type for s in answer.sources],
            retrieval_scope=answer.retrieval_scope,
            provenance_endpoint=answer.search_provenance.endpoint,
            warnings=answer.retrieval_warnings,
        )
    except (ResearchError, RetrievalError) as error:
        summary.update(status="failed", error_code=error.code)
    summary["elapsed_seconds"] = round(monotonic() - started, 3)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(json.dumps(summary, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
