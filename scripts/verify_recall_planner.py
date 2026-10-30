import json
import os
import time
from pathlib import Path

from dotenv import dotenv_values

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.pubmed_online import open_pubmed
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest

values = dotenv_values(".env")
for key, value in values.items():
    if key.startswith("LLM_") and value is not None:
        os.environ.setdefault(key, value)
settings = LLMSettings()
output = []
with open_llm(settings) as generator, open_pubmed() as pubmed:
    for q in ["肝脏分割最新研究有哪些？", "肝脏肿瘤亚区分割有哪些最新研究？"]:
        start = time.monotonic()
        try:
            plan = PicoPlanner(extractor=generator).plan(ClassificationRequest(question=q))
            result = pubmed.search(
                PubMedSearchRequest(
                    question=q, query_plan=plan, options=PubMedOptions(max_results=10)
                )
            )
            output.append(
                dict(
                    question=q,
                    model=settings.model,
                    plan=plan.model_dump(mode="json"),
                    result=result.model_dump(mode="json"),
                    elapsed=time.monotonic() - start,
                )
            )
            print("plan+search", len(result.records), flush=True)
        except Exception as e:
            output.append(
                dict(
                    question=q,
                    model=settings.model,
                    error=type(e).__name__,
                    code=getattr(e, "code", None),
                    elapsed=time.monotonic() - start,
                )
            )
            print("failed", getattr(e, "code", type(e).__name__), flush=True)
        Path("docs/recall-quality/real-planner.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf8"
        )
