import json
from pathlib import Path

import pytest

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest, ExtractionDraft
from clinical_agent.domain.research import ResearchError


def test_actual_invalid_planning_response_still_rejected():
    root = Path("docs/acceptance")
    raw = (root / "planner-20261101/raw-before.json").read_text(encoding="utf8")
    q = json.loads((root / "live-report-20261101/events.json").read_text(encoding="utf8"))[
        "question"
    ]

    class Extractor:
        def extract(self, request, **kwargs):
            return raw

    with pytest.raises(ResearchError, match="extraction_failed"):
        PicoPlanner(extractor=Extractor()).plan(ClassificationRequest(question=q))


def test_model_schema_explains_required_anchor_restriction():
    schema = ExtractionDraft.model_json_schema()
    description = schema["$defs"]["ConceptRelation"]["properties"]["required"].get(
        "description", ""
    )
    assert "required_constraint" in description
    assert "related_concept" in description
    assert "false" in description


def test_faithful_anchor_and_optional_expansion_keep_task():
    from clinical_agent.application.openalex import compile_queries

    root = Path("docs/acceptance")
    data = json.loads((root / "planner-20261101/raw-before.json").read_text(encoding="utf8"))
    q = json.loads((root / "live-report-20261101/events.json").read_text(encoding="utf8"))[
        "question"
    ]
    expansion = data["concept_relations"][-1]
    expansion["required"] = False
    data["concept_relations"].append(
        dict(
            expansion,
            english_term="predict risk of acute kidney injury in patients",
            relation="required_constraint",
            required=True,
        )
    )

    class Extractor:
        def extract(self, request, **kwargs):
            return json.dumps(data)

    plan = PicoPlanner(extractor=Extractor()).plan(ClassificationRequest(question=q))
    assert plan.task_intent == "feasibility"
    assert any(
        r.required and r.concept_id == expansion["concept_id"] for r in plan.concept_relations
    )
    assert all(
        "predict risk of acute kidney injury in patients" in query
        for query in compile_queries(plan)
    )
