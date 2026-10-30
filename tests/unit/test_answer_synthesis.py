"""Presentation contracts; fixed generations are NOT medical accuracy evaluations."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from clinical_agent.domain.citations import BASE_LIMITATIONS
from clinical_agent.domain.research import INSTRUCTIONS
from feishu.sender import render_answer
from tests.unit.test_feishu_sender import answer

ROOT = Path(__file__).resolve().parents[2]


def test_repeated_limits_are_grouped_without_losing_specific_limits_or_audit():
    dto = answer(answered=True)
    dto.claims[0].limitations = ["样本量小", "仅单中心"]
    dto.claims.append(dto.claims[0].model_copy(deep=True, update={"claim_id": "c2"}))
    dto.limitations = [*BASE_LIMITATIONS, "样本量小", "部分来源仅包含摘要，不能视为已阅读全文。"]
    before = dto.model_dump_json()
    text = render_answer(dto)
    assert text.count("样本量小") == 1
    assert text.count("仅单中心") == 1
    assert text.count("不用于个体诊断或治疗决策") == 1
    assert "样本量小 [1]" in text
    assert "局限与范围" in text
    assert "医学语义" in text
    assert "样本量小" in render_answer(dto, include_audit=True)
    assert dto.model_dump_json() == before


def test_full_text_locator_and_both_trusted_identifiers_are_visible():
    dto = answer(answered=True)
    dto.sources[0].content_scope = "full_text"
    dto.sources[0].evidence[0].location = dict(
        kind="pdf_page", page=3, section="Methods", start=12, end=31
    )
    text = render_answer(dto)
    assert "第3页" in text and "Methods" in text and "[12,31)" in text
    assert "123456" in text and "10.0000/synthetic" in text
    assert "chunk=" not in text and "hash=" not in text


def test_generation_policy_requires_task_alignment_and_synthesis():
    # Policy presence only: this cannot demonstrate a model follows the policy.
    for instruction in [
        "first claim",
        "unit of analysis",
        "Synthesize",
        "single-paper",
        "research gaps",
        "Do not repeat",
        "No fixed number",
        "comparator baselines",
        "method explicitly named",
    ]:
        assert instruction in INSTRUCTIONS


@pytest.mark.parametrize(
    "question",
    [
        "有没有关于肝脏肿瘤内部亚区划分的研究？",
        "Are there studies on intratumoral subregions in liver tumors?",
        "肝脏肿瘤 intratumoral subregions 有哪些方法？",
    ],
)
def test_real_organ_abstract_negative_control_dataflow(question, source_factory, prepared_factory):
    """Real source text, hand-authored negative response; NOT a model quality score."""
    from uuid import uuid4

    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.research import QuestionRequest
    from tests.unit.test_research import Retriever, draft, result

    xml = (ROOT / "docs/final-acceptance/answer-synthesis/organ-segmentation.xml").read_bytes()
    record = parse_pubmed_response(xml, fetched_at=datetime(2026, 10, 29, tzinfo=UTC))[0]
    assert "liver segmentation" in record.title.lower()
    assert "14" in record.abstract and "atlas" in record.abstract.lower()
    # Harness identity/embedding metadata are synthetic; passage and title are official XML.
    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    hit = retrieval.hits[0]
    hit.chunk.text = record.abstract
    hit.chunk.location = dict(kind="abstract", start=0, end=len(record.abstract))
    hit.document.title = record.title
    hit.document.pmid = record.pmid
    hit.document.content_scope = "abstract"
    seen = []

    class FixedNegative:
        def generate(self, context, *, timeout_seconds):
            seen.append(context)
            assert context.question == question
            assert context.evidence[0].text == record.abstract
            assert "original question" in context.instructions
            assert len(context.model_dump_json()) <= 24000
            assert 0 < timeout_seconds <= 60
            return draft(
                context.evidence[0].chunk_id,
                kind="uncertainty",
                text="本次证据描述整体肝脏分割，不能据此确认肿瘤内部亚区划分研究；"
                "这不代表不存在相关研究。",
            )

    retriever = Retriever(retrieval)
    output = ResearchService(retriever=retriever, generator=FixedNegative()).answer(
        QuestionRequest(request_id=uuid4(), question=question)
    )
    assert len(seen) == len(retriever.calls) == 1
    assert output.claims[0].kind == "uncertainty"
    text = render_answer(output)
    assert text.startswith("不确定：本次证据描述整体肝脏分割")
    assert output.sources[0].pmid == record.pmid
    assert "chunk=" not in text


def test_existing_real_mismatch_snapshot_keeps_original_question_and_passages():
    from clinical_agent.domain.research import GenerationInput

    saved = json.loads(
        (ROOT / "docs/final-acceptance/docker-e2e/actual-zh.json").read_text(encoding="utf-8")
    )
    context = dict(saved["context"])
    context.pop("instructions", None)
    current = GenerationInput.model_validate(context)
    assert current.question == saved["context"]["question"]
    assert all(
        a.text == b["text"] for a, b in zip(current.evidence, context["evidence"], strict=True)
    )
    assert len(current.model_dump_json()) <= 24000
    assert "mismatch" in current.instructions


@pytest.mark.parametrize("truncated", [True, False])
def test_complete_request_is_not_claim_of_exhaustive_retrieval(truncated):
    from clinical_agent.domain.pubmed import SearchProvenance

    dto = answer(answered=True)
    dto.retrieval_scope = "online"
    dto.search_provenance = SearchProvenance(
        query_sent="synthetic",
        query_translation=None,
        total_count=100 if truncated else 1,
        requested_limit=10,
        returned_count=1,
        truncated=truncated,
        fetched_at=datetime(2026, 10, 29, tzinfo=UTC),
        date_from=None,
        date_to=None,
        date_field="pdat",
        sort="relevance",
        status="complete",
        warnings=[],
        missing_pmids=[],
    )
    text = render_answer(dto)
    assert "请求状态：complete" in text
    assert ("候选已截断" if truncated else "候选未截断") in text
    assert "不保证检全" in text
