"""Program-built facts keep quotes exact across research domains."""

import json
from uuid import uuid4

import pytest

from clinical_agent.application.analysis import EvidenceAnalyzer, quote_catalog
from clinical_agent.domain.analysis import METHOD_FIELDS, consistent_relation
from clinical_agent.domain.research import QuestionRequest, ResearchError

DOMAINS = [
    ("imaging", "A cohort of 20 used MRI.", "Study an imaging cohort", "imaging"),
    (
        "prediction",
        "The model predicted mortality with AUC 0.8.",
        "Predict a clinical outcome",
        "clinical",
    ),
    (
        "materials",
        "The interface remained stable for 100 hours.",
        "Stabilize a materials interface",
        "interface",
    ),
    ("energy", "The scheduler reduced energy by 12 percent.", "Reduce computing energy", "energy"),
    (
        "biology",
        "The enzyme retained activity after 30 minutes.",
        "Measure enzyme activity",
        "enzyme",
    ),
]


def _prepare(source_factory, prepared_factory, text, question, kind="pdf"):
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalResult,
        retrieval_embedding_info,
    )

    prepared = prepared_factory(source_factory(text, kind=kind))
    chunk = prepared.embedded[0].evidence
    document = DocumentSummary.from_document(prepared.source.parsed.document)
    retrieval = RetrievalResult(
        options={},
        embedding_info=retrieval_embedding_info(),
        hits=[EvidenceHit(chunk=chunk, document=document, score=1.0, rank=1)],
    )
    request = QuestionRequest(request_id=uuid4(), question=question)
    catalog = quote_catalog({chunk.chunk_id: retrieval.hits[0]})
    quote_id = next(iter(catalog))
    return request, retrieval, quote_id, catalog[quote_id]["text"], document.document_id


class _Model:
    def __init__(self, payload):
        self.payload = payload

    def analyze_evidence(self, context, *, timeout_seconds, max_output_tokens=None):
        return json.dumps(self.payload)


def _selection(document_id, quote_id, question_piece, inference=None, reported_role="reported"):
    reported = [{"field_name": "design", "quote_id": quote_id, "role": reported_role}]
    inferences = []
    if inference:
        inferences.append(
            {
                "field_name": "outcomes",
                "value": inference,
                "epistemic_kind": "model_inference",
                "verification_needed": "在新的样本上重复该测量。",
                "quote_id": quote_id,
            }
        )
    return {
        "studies": [
            {
                "document_id": str(document_id),
                "study_type": "other",
                "type_basis": "text",
                "type_quote_id": quote_id,
                "reported": reported,
                "inferences": inferences,
            }
        ],
        "similarities": [
            {
                "document_id": str(document_id),
                "dimensions": [
                    {
                        "name": name,
                        "relation": "overlap",
                        "idea_quote": question_piece,
                        "quote_id": quote_id,
                        "reason": "所选句子与问题中的表述有关。",
                    }
                    for name in ("question", "population", "data", "methods", "outcomes")
                ],
            }
        ],
    }


@pytest.mark.parametrize(
    ("relations", "expected"),
    [
        ({"overlap"}, "overlap"),
        ({"different"}, "different"),
        ({"partial_overlap"}, "partial_overlap"),
        ({"unknown"}, "unknown"),
        ({"overlap", "different"}, "partial_overlap"),
        ({"overlap"}, "overlap"),
        ({"overlap", "unknown"}, "unknown"),
        ({"overlap", "partial_overlap", "different"}, "partial_overlap"),
    ],
)
def test_overall_relation_follows_the_dimension_table(relations, expected):
    assert consistent_relation(set(relations)) == expected


@pytest.mark.parametrize("domain", DOMAINS, ids=[item[0] for item in DOMAINS])
def test_selected_quote_becomes_the_fact_and_chinese_stays_an_inference(
    source_factory, prepared_factory, domain
):
    _name, text, question, piece = domain
    request, retrieval, quote_id, sentence, document_id = _prepare(
        source_factory, prepared_factory, text, question
    )
    payload = _selection(document_id, quote_id, piece, inference="该结果能否迁移仍需复核。")
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    design = result.studies[0].fields["design"]
    outcome = result.studies[0].fields["outcomes"]
    assert design.value == sentence
    assert design.evidence[0].quote == sentence
    assert design.basis == "text"
    assert outcome.value == "该结果能否迁移仍需复核。"
    assert outcome.basis == "model_inference"
    assert outcome.verification_needed
    assert outcome.evidence[0].quote == sentence
    assert set(result.studies[0].fields) == METHOD_FIELDS
    assert result.studies[0].fields["intervention"].value is None
    assert result.studies[0].fields["intervention"].basis == "not_reported"
    assert result.idea_similarities[0].overall_relation == "overlap"


def test_unknown_quote_and_wrong_role_do_not_become_facts(source_factory, prepared_factory):
    request, retrieval, quote_id, sentence, document_id = _prepare(
        source_factory, prepared_factory, "A cohort of 20 used MRI.", "Study an imaging cohort"
    )
    missing = _selection(document_id, "missing#0", "imaging")
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(missing)).analyze(request, retrieval)
    payload = _selection(document_id, quote_id, "imaging")
    payload["studies"][0]["reported"].append(
        {"field_name": "intervention", "quote_id": quote_id, "role": "comparator"}
    )
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    assert result.studies[0].fields["intervention"].value is None
    assert sentence not in (result.studies[0].fields["intervention"].value or "")


def test_another_papers_sentence_is_not_this_papers_method(source_factory, prepared_factory):
    first = _prepare(
        source_factory, prepared_factory, "A cohort of 20 used MRI.", "Compare studies"
    )
    second = _prepare(
        source_factory,
        prepared_factory,
        "The interface remained stable for 100 hours.",
        "Compare studies",
    )
    request = first[0]
    other = second[1].hits[0].model_copy(update={"rank": 2, "score": 0.5})
    retrieval = first[1].model_copy(update={"hits": [first[1].hits[0], other]})
    payload = _selection(first[4], second[2], "Compare")
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    assert result.studies[0].fields["design"].value is None
    assert "100 hours" not in json.dumps(result.studies[0].fields["design"].model_dump())


def test_mixed_dimensions_stay_partial_and_a_gap_stays_unknown(source_factory, prepared_factory):
    request, retrieval, quote_id, _sentence, document_id = _prepare(
        source_factory,
        prepared_factory,
        "The enzyme retained activity after 30 minutes.",
        "Measure enzyme activity",
    )
    payload = _selection(document_id, quote_id, "enzyme")
    payload["similarities"][0]["dimensions"][0]["relation"] = "different"
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    assert result.idea_similarities[0].overall_relation == "partial_overlap"
    payload["similarities"][0]["dimensions"] = payload["similarities"][0]["dimensions"][:4]
    result = EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)
    assert result.idea_similarities[0].dimensions["outcomes"].relation == "unknown"
    assert result.idea_similarities[0].overall_relation == "unknown"


def test_decimal_sentence_stays_intact(source_factory, prepared_factory):
    _request, retrieval, _quote_id, sentence, _document_id = _prepare(
        source_factory, prepared_factory, "AUC 0.8. Small sample.", "Predict a clinical outcome"
    )
    catalog = quote_catalog({retrieval.hits[0].chunk.chunk_id: retrieval.hits[0]})
    texts = [item["text"] for item in catalog.values()]
    assert "AUC 0.8." in texts
    assert sentence == "AUC 0.8."


def test_inference_without_verification_is_rejected(source_factory, prepared_factory):
    request, retrieval, quote_id, _sentence, document_id = _prepare(
        source_factory,
        prepared_factory,
        "The scheduler reduced energy by 12 percent.",
        "Reduce computing energy",
    )
    payload = _selection(document_id, quote_id, "energy", inference="能耗下降未必能迁移。")
    del payload["studies"][0]["inferences"][0]["verification_needed"]
    with pytest.raises(ResearchError, match="model_output_invalid"):
        EvidenceAnalyzer(model=_Model(payload)).analyze(request, retrieval)


def test_metadata_basis_must_belong_to_the_source(source_factory, prepared_factory):
    request, retrieval, quote_id, _sentence, document_id = _prepare(
        source_factory,
        prepared_factory,
        "The enzyme retained activity after 30 minutes.",
        "Measure enzyme activity",
    )
    invented = _selection(document_id, quote_id, "enzyme")
    invented["studies"][0]["type_basis"] = "metadata"
    invented["studies"][0]["type_quote_id"] = None
    invented["studies"][0]["study_type"] = "cohort"
    invented["studies"][0]["metadata_basis"] = ["Not A Real Type"]
    result = EvidenceAnalyzer(model=_Model(invented)).analyze(request, retrieval)
    study = result.studies[0]
    assert study.study_type == "unknown"
    assert study.type_basis == "unknown"
    assert study.metadata_basis == []

    retrieval.hits[0].document.publication_types = ["Cohort Studies", "Journal Article"]
    aligned = _selection(document_id, quote_id, "enzyme")
    aligned["studies"][0]["type_basis"] = "metadata"
    aligned["studies"][0]["type_quote_id"] = None
    aligned["studies"][0]["study_type"] = "trial"
    aligned["studies"][0]["metadata_basis"] = ["Cohort Studies", "Not A Real Type"]
    result = EvidenceAnalyzer(model=_Model(aligned)).analyze(request, retrieval)
    study = result.studies[0]
    assert study.study_type == "cohort"
    assert study.type_basis == "metadata"
    assert study.metadata_basis == ["Cohort Studies"]


def test_abstract_scope_is_not_relabelled(source_factory, prepared_factory):
    request, retrieval, quote_id, sentence, document_id = _prepare(
        source_factory,
        prepared_factory,
        "A cohort of 20 used MRI.",
        "Study an imaging cohort",
        kind="pubmed",
    )
    result = EvidenceAnalyzer(model=_Model(_selection(document_id, quote_id, "imaging"))).analyze(
        request, retrieval
    )
    assert result.sources[0].content_scope == "abstract"
    assert result.sources[0].evidence[0].location.kind == "abstract"
    assert result.studies[0].fields["design"].value == sentence
