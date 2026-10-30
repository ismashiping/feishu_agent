"""Evidence counts and standardized terms. Frozen questions are not special cases."""

import logging

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator
from clinical_agent.application.openalex import compile_queries, method_names
from clinical_agent.domain.pico import (
    PICO_INSTRUCTIONS,
    ConceptMapping,
    ConceptRelation,
    PaperTarget,
)
from clinical_agent.domain.research import ResearchError
from tests.unit.test_openalex import Screening, plan
from tests.unit.test_research_identity import retrieve


def test_standardized_spellings_join_the_same_anchor():
    question = "liver tumor segmentation"
    p = plan(question)
    p.concept_relations = [
        ConceptRelation(
            source_text="liver",
            english_term="liver",
            concept_id="organ",
            relation="exact_synonym",
            required=True,
        ),
        ConceptRelation(
            source_text="tumor segmentation",
            english_term="tumor segmentation",
            concept_id="task",
            relation="exact_synonym",
            required=True,
        ),
    ]
    p.concept_mappings = [
        ConceptMapping(
            source_text="liver", english_terms=["hepatic"], role="population", required=True
        )
    ]
    p.paper_target = PaperTarget(
        kind="method", source_text="liver", normalized_terms=["hepatic organ"]
    )
    p.concept_groups = [["liver", "hepatic parenchyma"], ["unrelated modality"]]
    query = compile_queries(p)[0]
    assert "hepatic" in query and "hepatic organ" in query and "hepatic parenchyma" in query
    assert "unrelated modality" not in query
    assert "hepatic organ" in method_names(p)


def test_analysis_focus_relations_fall_back_to_concept_groups():
    p = plan("segmentation technical challenges")
    p.concept_relations = [
        ConceptRelation(
            source_text="technical challenges",
            english_term="technical challenges",
            concept_id="focus",
            relation="exact_synonym",
            required=True,
        )
    ]
    queries = compile_queries(p)
    assert "segmentation" in queries[0]
    assert "technical challenges" not in queries[0]


def test_screening_failure_logs_counts_without_the_question(caplog):
    class Boom(Screening):
        def screen_candidates(self, context, **kwargs):
            raise ResearchError("model_output_invalid")

    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        result, _ = retrieve(plan("segmentation"), screener=Boom())
    assert not result.hits
    assert "openalex_screening_failed" in result.search_provenance.warnings
    screen = next(r for r in caplog.records if getattr(r, "evidence_stage", None) == "screen")
    select = next(r for r in caplog.records if getattr(r, "evidence_stage", None) == "select")
    assert screen.failure_kind == "model_output_invalid"
    assert "supplied=" in screen.evidence_counts
    assert "screening_failed=" in select.evidence_counts and "hits=0" in select.evidence_counts
    assert "segmentation" not in screen.getMessage() and "segmentation" not in select.getMessage()


def test_structured_calls_disable_thinking_and_review_does_not(monkeypatch):
    seen = []
    original = FakeListChatModel._generate

    def record(self, messages, **kwargs):
        seen.append(kwargs)
        return original(self, messages, **kwargs)

    monkeypatch.setattr(FakeListChatModel, "_generate", record)
    generator = LangChainAnswerGenerator(FakeListChatModel(responses=["[]", "{}", "[]"]))
    generator.screen_candidates({}, timeout_seconds=1)
    generator.analyze_evidence({}, timeout_seconds=1)
    generator.review_claims({}, timeout_seconds=1)
    thinking = {"type": "disabled"}
    assert seen[0]["extra_body"]["thinking"] == thinking
    assert seen[1]["extra_body"]["thinking"] == thinking
    assert "thinking" not in seen[2].get("extra_body", {})


def test_rejected_structured_output_logs_size_without_text(caplog):
    from langchain_core.messages import AIMessage

    class LengthModel:
        def invoke(self, messages, **kwargs):
            return AIMessage(
                content="",
                response_metadata={
                    "finish_reason": "length",
                    "token_usage": {"completion_tokens_details": {"reasoning_tokens": 4096}},
                },
            )

    generator = LangChainAnswerGenerator(LengthModel())
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        try:
            generator.analyze_evidence({"question": "secret topic"}, timeout_seconds=1)
        except ResearchError as error:
            assert error.code == "model_output_invalid"
        else:
            raise AssertionError("rejected output must fail")
    record = next(r for r in caplog.records if getattr(r, "evidence_stage", None) == "provider")
    assert record.failure_kind == "length"
    assert record.evidence_counts == "content_chars=0,reasoning_tokens=4096"
    assert "secret topic" not in record.getMessage()


def test_research_subject_rule_is_general():
    assert "A topic name alone is not a literature lookup" in PICO_INSTRUCTIONS
    assert "literature lookup" in PICO_INSTRUCTIONS
    assert "肝脏亚区分割" not in PICO_INSTRUCTIONS
    assert "MedSAM" not in PICO_INSTRUCTIONS
