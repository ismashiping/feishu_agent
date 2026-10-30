"""Closed diagnostic tokens for planning failures. Synthetic text is not a citation."""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest, QueryPlan
from clinical_agent.domain.research import ResearchError
from tests.unit.test_openalex import plan
from tests.unit.test_plan_a import Extractor, draft


def _plan(question, data):
    return PicoPlanner(extractor=Extractor(json.dumps(data))).plan(
        ClassificationRequest(question=question)
    )


def test_schema_failure_names_the_field_and_hides_the_value(caplog):
    question = "alpha SECRET_QUESTION"
    data = draft(question)
    data["question_type"] = "SECRET_SCHEMA_VALUE"
    data["ambiguities"] = ["SECRET_MODEL_BODY"]
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(ResearchError, match="^extraction_failed$"),
    ):
        _plan(question, data)
    record = caplog.records[-1]
    assert record.stage == "schema"
    assert record.failure_kind == "schema_validation"
    assert record.rule_code == "literal_error"
    assert record.field_paths == "question_type"
    assert len(record.response_hash) == 64
    text = record.getMessage() + json.dumps(
        {key: getattr(record, key) for key in ("stage", "failure_kind", "rule_code", "field_paths")}
    )
    for secret in ("SECRET_QUESTION", "SECRET_SCHEMA_VALUE", "SECRET_MODEL_BODY"):
        assert secret not in text


def test_plan_failure_uses_a_stable_quote_rule(caplog):
    question = "explain unet"
    data = draft(question)
    data["paper_target"] = {"kind": "method", "source_text": "U-Net"}
    data["ambiguities"] = ["SECRET_MODEL_BODY"]
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(ResearchError, match="^extraction_failed$"),
    ):
        _plan(question, data)
    record = caplog.records[-1]
    assert record.stage == "plan"
    assert record.failure_kind == "plan_validation"
    assert record.rule_code == "paper_target_quote"
    assert record.field_paths == "paper_target.source_text"
    assert "U-Net" not in record.getMessage()
    assert "SECRET_MODEL_BODY" not in record.getMessage()
    assert "explain unet" not in record.getMessage()


@pytest.mark.parametrize(
    "mutate,rule,path",
    [
        (
            lambda data: data.update(paper_target={"kind": "method", "source_text": "U-Net"}),
            "paper_target_quote",
            "paper_target.source_text",
        ),
        (
            lambda data: data["research_constraints"].update(task=["U-Net"]),
            "constraint_quote",
            "research_constraints",
        ),
        (
            lambda data: data.update(
                concept_relations=[
                    {
                        "source_text": "U-Net",
                        "english_term": "segmentation",
                        "relation": "exact_synonym",
                        "concept_id": "c1",
                        "required": True,
                    }
                ]
            ),
            "relation_quote",
            "concept_relations.source_text",
        ),
        (
            lambda data: data.update(
                concept_relations=[
                    {
                        "source_text": "segmentation",
                        "english_term": "subtype",
                        "relation": "narrower_concept",
                        "concept_id": "c1",
                        "required": True,
                    }
                ]
            ),
            "expansion_not_anchor",
            "concept_relations.required",
        ),
        (
            lambda data: data.update(
                concept_relations=[
                    {
                        "source_text": "segmentation",
                        "english_term": "related",
                        "relation": "related_concept",
                        "concept_id": "missing",
                        "required": False,
                    }
                ]
            ),
            "relation_anchor",
            "concept_relations.concept_id",
        ),
        (
            lambda data: data.update(
                concept_mappings=[
                    {
                        "source_text": "U-Net",
                        "english_terms": ["segmentation"],
                        "role": "method",
                        "required": True,
                    }
                ]
            ),
            "mapping_quote",
            "concept_mappings.source_text",
        ),
    ],
)
def test_provenance_rules_are_stable(mutate, rule, path):
    question = "segmentation"
    data = plan(question).model_dump()
    mutate(data)
    with pytest.raises(ValidationError) as caught:
        QueryPlan.model_validate(data)
    error = caught.value.errors(include_input=False, include_context=False)[0]
    assert error["type"] == rule
    assert path
    assert "U-Net" not in json.dumps(error)


def test_unique_quote_span_does_not_require_constraints():
    question = "alpha beta"
    data = draft(question)
    assert "research_constraints" not in data
    data["terms"] = [{"text": "beta", "origin": "user_text", "source_span": {"start": 0, "end": 1}}]
    result = _plan(question, data)
    assert result.terms[0].text == "beta"
    assert result.terms[0].source_span.start == question.index("beta")
    assert result.research_constraints is None


def test_repeated_or_normalized_text_is_not_rewritten():
    repeated = "aa aa"
    data = draft(repeated)
    data["terms"] = [{"text": "aa", "origin": "user_text", "source_span": {"start": 0, "end": 1}}]
    with pytest.raises(ResearchError, match="^extraction_failed$"):
        _plan(repeated, data)
    question = "unet original paper"
    data = draft(question)
    data["terms"] = [
        {"text": "U-Net", "origin": "user_text", "source_span": {"start": 0, "end": 4}}
    ]
    with pytest.raises(ResearchError, match="^extraction_failed$"):
        _plan(question, data)


def test_normalized_term_is_not_accepted_as_a_user_quote():
    from clinical_agent.domain.pico import PICO_INSTRUCTIONS, PaperTarget

    question = "explain unet"
    data = plan(question).model_dump()
    data["paper_target"] = {
        "kind": "method",
        "source_text": "unet",
        "normalized_terms": ["U-Net"],
    }
    result = QueryPlan.model_validate(data)
    assert result.paper_target is not None
    assert result.paper_target.source_text == "unet"
    assert result.paper_target.normalized_terms == ["U-Net"]
    assert "U-Net" not in question
    data["paper_target"]["source_text"] = "U-Net"
    with pytest.raises(ValidationError) as caught:
        QueryPlan.model_validate(data)
    assert caught.value.errors()[0]["type"] == "paper_target_quote"
    legacy_target = PaperTarget.model_validate({"kind": "method", "source_text": "nnunet"})
    assert legacy_target.normalized_terms == []
    for frozen in (
        "MedSAM与nnU-Net用于医学图像分割有什么区别？",
        "肝脏亚区分割这个方向怎么样",
        "unet原始论文解释一下",
        "什么是nnunet",
    ):
        assert frozen not in PICO_INSTRUCTIONS


def test_legacy_plan_without_intent_stays_readable():
    legacy = plan("segmentation")
    assert legacy.task_intent is None
    restored = QueryPlan.model_validate(legacy.model_dump())
    assert restored.task_intent is None and restored.paper_target is None
    drafted = PicoPlanner(extractor=Extractor(json.dumps(draft("segmentation")))).plan(
        ClassificationRequest(question="segmentation")
    )
    assert drafted.task_intent is None


def test_formatter_emits_tokens_and_drops_payloads(tmp_path: Path):
    program = """
        import json
        import logging
        from clinical_agent.application.pico import PicoPlanner
        from clinical_agent.config import Settings
        from clinical_agent.domain.pico import ClassificationRequest
        from clinical_agent.domain.research import ResearchError
        from clinical_agent.logging_config import configure_logging

        configure_logging(Settings(log_level="WARNING"))
        question = "alpha SECRET_QUESTION"
        raw = json.dumps({
            "question_type": "SECRET_SCHEMA_VALUE",
            "pico": {"population": None, "intervention": None, "comparison": None, "outcome": None},
            "ambiguities": ["SECRET_MODEL_BODY"],
            "terms": [],
        })

        class Extractor:
            def extract(self, request, timeout_seconds):
                return raw

        try:
            PicoPlanner(extractor=Extractor()).plan(ClassificationRequest(question=question))
        except ResearchError as error:
            assert error.code == "extraction_failed" and error.__cause__ is None
        else:
            raise AssertionError("expected extraction_failed")
        """
    allowed_env = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    child_env = {key: value for key, value in os.environ.items() if key.upper() in allowed_env}
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", dedent(program)],
        cwd=tmp_path,
        env=child_env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    for secret in ("SECRET_QUESTION", "SECRET_SCHEMA_VALUE", "SECRET_MODEL_BODY"):
        assert secret not in result.stderr
    record = json.loads(result.stderr.strip().splitlines()[-1])
    assert record["stage"] == "schema"
    assert record["failure_kind"] == "schema_validation"
    assert record["rule_code"] == "literal_error"
    assert record["field_paths"] == "question_type"
    assert len(record["response_hash"]) == 64
    assert "Traceback" not in result.stderr
