"""Opt-in real planner -> OpenAlex -> semantic screening; no database or fulltext."""

import json
import sys
from pathlib import Path
from time import monotonic

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.openalex import OpenAlexSettings, open_openalex
from clinical_agent.application.openalex import OpenAlexRetrievalService
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.research import ResearchError
from clinical_agent.domain.retrieval import RetrievalRequest

QUESTIONS = [
    "肝脏分割最新研究有哪些？",
    "肝脏肿瘤亚区分割最新进展有哪些？",
    "MedSAM与nnU-Net有哪些区别？",
    "最近三年MRI预测肝癌微血管侵犯有哪些研究？",
    "肝脏肿瘤分割目前有哪些技术瓶颈？",
]


def main():
    # Reuse the explicitly configured provider; never print configuration or exception text.
    config = dotenv_values(".env")
    settings = LLMSettings(
        api_key=config["DEEPSEEK_API_KEY"],
        base_url=config["DEEPSEEK_BASE_URL"],
        model=config["DEEPSEEK_MODEL"],
        max_tokens=4096,
    )
    output = Path("docs/openalex-stage2/live-check.json")
    output.parent.mkdir(exist_ok=True)
    results = []
    diagnostics = []

    class RecordedModel:
        def __init__(self, model):
            self.model = model

        def extract(self, request, *, timeout_seconds):
            raw = self.model.extract(request, timeout_seconds=timeout_seconds)
            diagnostics.append({"stage": "extract", "question": request.question, "raw": raw})
            Path("docs/openalex-stage2/model-diagnostics.json").write_text(
                json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf8"
            )
            return raw

        def screen_candidates(self, context, *, timeout_seconds):
            raw = self.model.screen_candidates(context, timeout_seconds=timeout_seconds)
            diagnostics.append(
                {"stage": "screen", "question": context["question"], "context": context, "raw": raw}
            )
            Path("docs/openalex-stage2/model-diagnostics.json").write_text(
                json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf8"
            )
            return raw

    with open_llm(settings) as base_model, open_openalex() as client:
        model = RecordedModel(base_model)
        planner = PicoPlanner(extractor=model)
        service = OpenAlexRetrievalService(
            client, model, recent_months=OpenAlexSettings().recent_months
        )
        for question in QUESTIONS:
            started = monotonic()
            item = {
                "question": question,
                "model": settings.model,
                "scope": "real planner/search/screening only; human relevance review pending",
            }
            try:
                plan = planner.plan(ClassificationRequest(question=question))
                item["plan"] = plan.model_dump(mode="json")
                result = service.retrieve(
                    RetrievalRequest(question=question, scope="online"), query_plan=plan
                )
                item["selected"] = [
                    {
                        "id": h.document.openalex_record.openalex_id,
                        "title": h.document.title,
                        "date": h.document.publication_date.raw,
                    }
                    for h in result.hits
                ]
                item["provenance"] = result.search_provenance.model_dump(mode="json")
                item["status"] = "executed"
            except ResearchError as error:
                item["status"], item["error"] = "failed", error.code
            item["elapsed_seconds"] = round(monotonic() - started, 3)
            results.append(item)
            output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf8")
            print(
                json.dumps(
                    {
                        "question": question,
                        "status": item["status"],
                        "error": item.get("error"),
                        "selected": len(item.get("selected", [])),
                        "seconds": item["elapsed_seconds"],
                    },
                    ensure_ascii=True,
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
