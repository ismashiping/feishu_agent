"""Fact quotes and inferences share one contract across research domains."""

import copy
import json
from uuid import uuid4

import pytest

from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.domain.analysis import ANALYSIS_INSTRUCTIONS
from clinical_agent.domain.research import QuestionRequest, ResearchError

DOMAINS = [
    ("imaging", "A cohort of 20 used MRI.", "Study an imaging cohort", "队列使用了磁共振"),
    (
        "prediction",
        "The model predicted mortality with AUC 0.8.",
        "Predict a clinical outcome",
        "模型预测了死亡率",
    ),
    (
        "materials",
        "The interface remained stable for 100 hours.",
        "Stabilize a materials interface",
        "界面保持了稳定",
    ),
    (
        "energy",
        "The scheduler reduced energy by 12 percent.",
        "Reduce computing energy",
        "调度器降低了能耗",
    ),
]


class _Model:
    def __init__(self, payload):
        self.payload = payload

    def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
        return json.dumps(self.payload)


def _case(source_factory, prepared_factory, text, question, kind="pdf"):
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory(text, kind=kind))
    chunk = prepared.embedded[0].evidence
    document = DocumentSummary.from_document(prepared.source.parsed.document)
    quote = text.split(".")[0]
    request = QuestionRequest(request_id=uuid4(), question=question)
    retrieval = RetrievalResult(
        options={},
        embedding_info=retrieval_embedding_info(),
        hits=[EvidenceHit(chunk=chunk, document=document, score=1.0, rank=1)],
    )
    ref = {"chunk_id": str(chunk.chunk_id), "quote": quote}
    missing = {
        "value": None,
        "epistemic_kind": "reported_fact",
        "evidence": [],
        "basis": "not_reported",
        "verification_needed": None,
    }
    fields = {
        name: copy.deepcopy(missing)
        for name in [
            "design",
            "data_sources",
            "technical_methods",
            "evaluation_metrics",
            "results",
            "limitations",
            "population",
            "intervention",
            "comparison",
            "outcomes",
            "time_window",
            "sample_size",
            "effects",
            "quality_signals",
        ]
    }
    fields["design"] = {
        "value": quote,
        "epistemic_kind": "reported_fact",
        "evidence": [ref],
        "basis": "text",
        "verification_needed": None,
    }
    dimensions = {
        name: {"relation": "unknown", "idea_quote": None, "evidence": [], "reason": "未说明"}
        for name in ["question", "population", "data", "methods", "outcomes"]
    }
    payload = {
        "studies": [
            {
                "document_id": str(document.document_id),
                "study_type": "other",
                "type_basis": "text",
                "type_evidence": [dict(ref)],
                "metadata_basis": [],
                "fields": fields,
            }
        ],
        "idea_similarities": [
            {
                "document_id": str(document.document_id),
                "dimensions": dimensions,
                "overall_relation": "unknown",
            }
        ],
        "candidate_gaps": [],
        "comparisons": [],
    }
    return request, retrieval, payload, quote


def _run(bundle):
    request, retrieval, payload, _quote = bundle
    return EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)


@pytest.mark.parametrize("domain", DOMAINS, ids=[item[0] for item in DOMAINS])
def test_exact_quote_passes_for_every_domain(source_factory, prepared_factory, domain):
    _name, text, question, _rewrite = domain
    bundle = _case(source_factory, prepared_factory, text, question)
    result = _run(bundle)
    assert result.studies[0].fields["design"].value == bundle[3]
    assert result.studies[0].fields["design"].basis == "text"


@pytest.mark.parametrize("domain", DOMAINS, ids=[item[0] for item in DOMAINS])
def test_translated_fact_is_not_a_verbatim_quote(source_factory, prepared_factory, domain):
    _name, text, question, rewrite = domain
    request, retrieval, payload, _quote = _case(source_factory, prepared_factory, text, question)
    payload["studies"][0]["fields"]["design"]["value"] = rewrite
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)


def test_missing_pointer_and_abstract_scope_stay_closed(source_factory, prepared_factory):
    text = "A cohort of 20 used MRI."
    request, retrieval, payload, quote = _case(
        source_factory, prepared_factory, text, "Study an imaging cohort", kind="pubmed"
    )
    result = _run((request, retrieval, payload, quote))
    assert result.sources[0].content_scope == "abstract"
    assert result.sources[0].evidence[0].location.kind == "abstract"
    assert result.analysis_status == "partial"

    invented = copy.deepcopy(payload)
    invented["studies"][0]["fields"]["design"]["evidence"] = [
        {"chunk_id": str(uuid4()), "quote": quote}
    ]
    invented["studies"][0]["type_evidence"] = invented["studies"][0]["fields"]["design"]["evidence"]
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(invented)).analyze(request, retrieval)

    disguised = copy.deepcopy(payload)
    disguised["studies"][0]["fields"]["design"]["evidence"][0]["quote"] = "the full text reports"
    disguised["studies"][0]["fields"]["design"]["value"] = "the full text reports"
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(disguised)).analyze(request, retrieval)


def test_inference_requires_verification_and_accepts_a_check(source_factory, prepared_factory):
    request, retrieval, payload, quote = _case(
        source_factory,
        prepared_factory,
        "The scheduler reduced energy by 12 percent.",
        "Reduce computing energy",
    )
    item = payload["studies"][0]["fields"]["design"]
    item.update(
        value="The reported reduction may not transfer to another workload.",
        epistemic_kind="model_inference",
        basis="text",
        verification_needed=None,
    )
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)

    item.update(
        basis="model_inference", verification_needed="Repeat the measurement on a new workload."
    )
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    assert result.studies[0].fields["design"].epistemic_kind == "model_inference"
    assert quote in result.studies[0].fields["design"].evidence[0].quote


def test_cross_paper_synthesis_cannot_be_one_study_fact(source_factory, prepared_factory):
    first = _case(
        source_factory,
        prepared_factory,
        "A cohort of 20 used MRI.",
        "Compare two supplied studies",
    )
    second = _case(
        source_factory,
        prepared_factory,
        "The interface remained stable for 100 hours.",
        "Compare two supplied studies",
    )
    request = first[0]
    other_hit = second[1].hits[0].model_copy(update={"rank": 2, "score": 0.5})
    retrieval = first[1].model_copy(update={"hits": [first[1].hits[0], other_hit]})
    payload = copy.deepcopy(first[2])
    other = second[2]["studies"][0]["fields"]["design"]["evidence"][0]
    payload["studies"][0]["fields"]["design"]["evidence"] = [other]
    payload["studies"][0]["fields"]["design"]["value"] = other["quote"]
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)


def test_business_correction_is_one_checked_retry(source_factory, prepared_factory):
    bundle = _case(
        source_factory,
        prepared_factory,
        "The scheduler reduced energy by 12 percent.",
        "Reduce computing energy",
    )
    request, retrieval, good, _quote = bundle
    bad = copy.deepcopy(good)
    bad["studies"][0]["fields"]["design"]["value"] = "调度器降低了能耗"

    class Sequence:
        def __init__(self):
            self.payloads = [bad, good]
            self.contexts = []

        def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
            self.contexts.append(context)
            return json.dumps(self.payloads.pop(0))

    model = Sequence()
    result = EvidenceAnalyzer(model=model).analyze(request, retrieval)
    assert result.studies[0].fields["design"].value == "The scheduler reduced energy by 12 percent"
    assert len(model.contexts) == 2
    assert model.contexts[1]["correction"]["rule_code"] == "reported_fact_quote"
    assert "调度器降低了能耗" not in json.dumps(model.contexts[1]["correction"])

    again = Sequence()
    again.payloads = [bad, bad]
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=again).analyze(request, retrieval)
    assert len(again.contexts) == 2


def test_evidence_failures_are_not_sent_for_correction(source_factory, prepared_factory):
    request, retrieval, payload, quote = _case(
        source_factory, prepared_factory, "A cohort of 20 used MRI.", "Study an imaging cohort"
    )
    payload["studies"][0]["fields"]["design"]["evidence"] = [
        {"chunk_id": str(uuid4()), "quote": quote}
    ]

    class Once:
        calls = 0

        def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
            self.calls += 1
            return json.dumps(payload)

    model = Once()
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=model).analyze(request, retrieval)
    assert model.calls == 1


def test_long_field_paths_keep_a_fitting_prefix(source_factory, prepared_factory, caplog):
    import logging

    request, retrieval, payload, _quote = _case(
        source_factory, prepared_factory, "A cohort of 20 used MRI.", "Study an imaging cohort"
    )
    for name in (
        "design",
        "intervention",
        "comparison",
        "limitations",
        "population",
        "outcomes",
        "results",
        "technical_methods",
    ):
        payload["studies"][0]["fields"][name] = {
            "value": "改写后的事实",
            "epistemic_kind": "reported_fact",
            "evidence": [payload["studies"][0]["type_evidence"][0]],
            "basis": "text",
            "verification_needed": None,
        }
    with caplog.at_level(logging.INFO, logger="clinical_agent.application.openalex"):
        with pytest.raises(ResearchError, match="model_output_invalid"):
            EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    record = next(
        item for item in caplog.records if getattr(item, "evidence_stage", None) == "analyze"
    )
    assert record.field_paths
    assert len(record.field_paths) <= 200
    assert record.field_paths.startswith("studies.0.fields.")


def test_instructions_separate_quotes_from_analysis():
    text = ANALYSIS_INSTRUCTIONS.casefold()
    for banned in ("medsam", "nnunet", "perovskite", "钙钛矿", "肝脏"):
        assert banned not in text
    assert "character for character" in text
    assert "verification_needed" in text
    assert "content_scope" in text
    assert "user's language" in text
    assert "not a reported fact" in text
