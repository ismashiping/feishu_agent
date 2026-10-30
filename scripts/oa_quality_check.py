"""Explicit real-model quality checks: frozen evidence replay or new live discovery."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from clinical_agent.application.openalex import record_hit
from clinical_agent.command_runtime import open_research
from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer, ResearchError
from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
from feishu.sender import render_answer


def main():
    root, mode = Path(sys.argv[1]), sys.argv[2]
    assert mode in {"replay", "live"}
    output = root / mode
    output.mkdir(exist_ok=False)
    rows = []
    with open_research(Path("/app/model")) as service:
        base_generator = service._generator

        class CapturedGenerator:
            def generate(self, context, *, timeout_seconds):
                (output / f"q{index}-context.json").write_text(context.model_dump_json(indent=2))
                raw = base_generator.generate(context, timeout_seconds=timeout_seconds)
                (output / f"q{index}-draft.json").write_text(raw)
                return raw

        service._generator = CapturedGenerator()
        base_screener = service._scout_agent.online.screener
        screening_calls = {}

        class CapturedScreening:
            def screen_candidates(self, context, *, timeout_seconds):
                n = screening_calls.get(index, 0) + 1
                screening_calls[index] = n
                (output / f"q{index}-screen{n}-input.json").write_text(
                    json.dumps(context, ensure_ascii=False)
                )
                raw = base_screener.screen_candidates(context, timeout_seconds=timeout_seconds)
                (output / f"q{index}-screen{n}-output.json").write_text(raw)
                return raw

        service._scout_agent.online.screener = CapturedScreening()
        indices = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(1, 7)
        for index in indices:
            old = ResearchAnswer.model_validate_json(
                (root / f"input/q{index}-response.json").read_text()
            )
            old_request = json.loads((root / f"input/q{index}-request.json").read_text())
            request = QuestionRequest(
                request_id=uuid4(),
                question=old_request["question"],
                scope="online" if mode == "replay" else "hybrid",
                options=RetrievalOptions(top_k=8),
                openalex=old_request.get("openalex"),
            )
            started = monotonic()
            row = {
                "index": index,
                "question": request.question,
                "mode": mode,
                "fresh_discovery": mode == "live",
                "human_medical_signoff": "pending",
            }
            try:
                if mode == "live":
                    answer = service.answer(request)
                elif not old.sources:
                    row.update(status="no_frozen_evidence", sources=0)
                    rows.append(row)
                    continue
                else:
                    result = RetrievalResult(
                        scope="online",
                        options=request.options,
                        embedding_info=None,
                        search_provenance=old.search_provenance,
                        hits=[
                            record_hit(s.openalex_record, old.generated_at).model_copy(
                                update={"score": 1.0 / rank, "rank": rank}
                            )
                            for rank, s in enumerate(old.sources, 1)
                        ],
                    )
                    result = service._fulltext.enrich(
                        request.question, result, deadline=monotonic() + 35
                    )
                    context = service._prepare(
                        {
                            "request": request,
                            "retrieval": result,
                            "query_plan": old.query_plan,
                            "deadline": monotonic() + 60,
                        }
                    )["context"]
                    (output / f"q{index}-context.json").write_text(
                        context.model_dump_json(indent=2)
                    )
                    raw = service._generator.generate(context, timeout_seconds=50)
                    answer = build_answer(
                        request,
                        result,
                        parse_draft(raw, max_bytes=32000),
                        generated_at=datetime.now(UTC),
                    )
                    answer.query_plan = old.query_plan
                (output / f"q{index}-answer.json").write_text(answer.model_dump_json(indent=2))
                (output / f"q{index}-answer.txt").write_text(render_answer(answer))
                row.update(
                    status=answer.status,
                    sources=len(answer.sources),
                    claims=len(answer.claims),
                    fulltext_citations=sum(
                        e.location.kind == "fulltext" for s in answer.sources for e in s.evidence
                    ),
                    sections=list(dict.fromkeys(c.section for c in answer.claims if c.section)),
                    warnings=answer.retrieval_warnings,
                )
            except ResearchError as error:
                row.update(status="failed", error=error.code)
            row["seconds"] = round(monotonic() - started, 3)
            rows.append(row)
            (output / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print(json.dumps(row, ensure_ascii=False), flush=True)
    (output / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
