"""Real model over saved OA evidence; isolated validation, no new discovery or bot send."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.openalex import OpenAlexProvenance
from clinical_agent.domain.research import QuestionRequest, ResearchError
from clinical_agent.domain.retrieval import RetrievalResult
from feishu.sender import render_answer


def main():
    root = Path(sys.argv[1])
    output = root / (sys.argv[2] if len(sys.argv) > 2 else "answer-check")
    output.mkdir(exist_ok=False)
    retrieval = RetrievalResult.model_validate_json((root / "result4/warm.json").read_text())
    retrieval.search_provenance = OpenAlexProvenance.model_validate_json(
        (root / "fixtures/search-provenance.json").read_text()
    )
    question = (
        "Which CT and MRI scanners, sequences, and contrast agents does this study report? "
        "Use the retrieved fulltext methods, and identify missing details rather than infer them."
    )
    request = QuestionRequest(question=question, scope="online", request_id=uuid4())
    started = monotonic()
    summary = {
        "scope": "saved fulltext retrieval -> real LLM -> existing citation gate",
        "full_pipeline_discovery": False,
        "human_medical_signoff": "pending",
    }
    try:
        with open_llm(LLMSettings()) as generator:
            service = ResearchService(retriever=object(), generator=generator)
            context = service._prepare(
                {"request": request, "retrieval": retrieval, "deadline": monotonic() + 60}
            )["context"]
            raw = generator.generate(context, timeout_seconds=50)
        draft = parse_draft(raw, max_bytes=32000)
        answer = build_answer(request, retrieval, draft, generated_at=datetime.now(UTC))
        (output / "answer.json").write_text(answer.model_dump_json(indent=2))
        (output / "answer.txt").write_text(
            "回放验证：使用此前冻结的OpenAlex候选和全文缓存，本次未执行在线文献发现。\n\n"
            + render_answer(answer)
        )
        fulltext_count = sum(
            e.location.kind == "fulltext" for s in answer.sources for e in s.evidence
        )
        summary.update(status=answer.status, fulltext_citations=fulltext_count)
    except ResearchError as error:
        summary.update(status="failed", error_code=error.code)
    summary["seconds"] = round(monotonic() - started, 3)
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
