"""Operator-run real four-question check; never sends a Feishu message."""

import json
import logging
import sys
from pathlib import Path
from time import monotonic
from uuid import uuid4

from clinical_agent.command_runtime import open_research
from clinical_agent.domain.report import ResearchReport, render_report
from clinical_agent.domain.research import QuestionRequest, ResearchError
from clinical_agent.domain.retrieval import RetrievalError
from feishu.sender import render_answer, split_report_text

QUESTIONS = [
    "MedSAM与nnU-Net用于医学图像分割有什么区别？",
    "肝脏亚区分割这个方向怎么样",
    "unet原始论文解释一下",
    "什么是nnunet",
]


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    summary = []
    with open_research(Path("/app/model")) as research:
        for index, question in enumerate(QUESTIONS, 1):
            started = monotonic()
            result = {"question": question}
            try:
                answer = research.respond(
                    QuestionRequest(question=question, request_id=uuid4(), scope="hybrid")
                )
                is_report = isinstance(answer, ResearchReport)
                text = render_report(answer) if is_report else render_answer(answer)
                result.update(
                    status="success",
                    kind="report" if is_report else "answer",
                    answer=answer.model_dump(mode="json"),
                    parts=len(split_report_text(text)) if is_report else 1,
                )
                (output / f"q{index}.txt").write_text(text, encoding="utf-8")
            except (ResearchError, RetrievalError) as error:
                result.update(status="failed", code=error.code)
            except Exception as error:
                result.update(
                    status="failed", code="operator_check_failed", error_type=type(error).__name__
                )
            result["seconds"] = round(monotonic() - started, 3)
            (output / f"q{index}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            summary.append({k: v for k, v in result.items() if k != "answer"})
            print(json.dumps(summary[-1], ensure_ascii=False), flush=True)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
