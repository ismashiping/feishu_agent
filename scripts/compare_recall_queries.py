"""Real API query compiler comparison; fixed plans, no model/medical acceptance claim."""

import json
import time
from pathlib import Path

from clinical_agent.adapters.pubmed_online import open_pubmed
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest

CASES = [
    (
        "liver",
        "肝脏分割最新研究有哪些？",
        "肝脏",
        "liver",
        "分割",
        "segmentation",
        "image segmentation",
    ),
    (
        "habitat",
        "肝脏肿瘤亚区分割有哪些最新研究？",
        "肝脏肿瘤",
        "liver tumor",
        "亚区分割",
        "subregion segmentation",
        "tumor habitat",
    ),
    (
        "glioma",
        "Glioblastoma intratumoral heterogeneity MRI habitat",
        "Glioblastoma",
        "glioblastoma",
        "intratumoral heterogeneity",
        "intratumoral heterogeneity",
        "tumor habitat",
    ),
    ("lung", "肺癌影像预测研究", "肺癌", "lung cancer", "预测", "prediction", "prognosis"),
    (
        "breast",
        "Breast cancer imaging diagnosis",
        "Breast cancer",
        "breast cancer",
        "diagnosis",
        "diagnosis",
        "classification",
    ),
    (
        "negative",
        "肝癌量子瞬移分割",
        "肝癌",
        "hepatocellular carcinoma",
        "量子瞬移分割",
        "quantum teleportation segmentation",
        "quantum teleportation",
    ),
]


class Extractor:
    def __init__(self, data):
        self.data = data

    def extract(self, request, **kwargs):
        return json.dumps(self.data)


output = []
with open_pubmed() as client:
    for cid, q, s1, t1, s2, t2, related in CASES:
        data = dict(
            question_type="other",
            pico=dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
            ambiguities=[],
            blocking_ambiguities=[],
            terms=[dict(text=q, origin="user_text", source_span=dict(start=0, end=len(q)))],
            concept_groups=[[t1], [t2]],
        )
        plan = PicoPlanner(extractor=Extractor(data)).plan(ClassificationRequest(question=q))
        relations = [
            dict(
                source_text=s,
                english_term=t,
                concept_id=k,
                relation="required_constraint",
                required=True,
            )
            for s, t, k in [(s1, t1, "population"), (s2, t2, "task")]
        ]
        relations.append(
            dict(
                source_text=s2,
                english_term=related,
                concept_id="task",
                relation="related_concept",
                required=False,
            )
        )
        updated = plan.model_dump()
        updated["concept_relations"] = relations
        updated = type(plan).model_validate(updated)
        for version, p in [("before", plan), ("after", updated)]:
            started = time.monotonic()
            options = PubMedOptions(max_results=10, date_from="2020-01-01", date_to="2026-10-29")
            try:
                result = client.search(
                    PubMedSearchRequest(question=q, query_plan=p, options=options)
                )
                output.append(
                    dict(
                        case_id=cid,
                        question=q,
                        version=version,
                        plan=p.model_dump(mode="json"),
                        result=result.model_dump(mode="json"),
                        elapsed=time.monotonic() - started,
                    )
                )
            except Exception as exc:
                output.append(
                    dict(
                        case_id=cid,
                        version=version,
                        error=type(exc).__name__,
                        code=getattr(exc, "code", None),
                    )
                )
            Path("docs/recall-quality/live-comparison.json").write_text(
                json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(
                cid,
                version,
                output[-1].get(
                    "error",
                    len(output[-1]["result"]["records"]) if "result" in output[-1] else None,
                ),
                flush=True,
            )
