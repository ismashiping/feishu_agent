"""Synthetic cases; no real paper claims. Independent selection cases frozen here."""

import json

import pytest

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.pubmed import PubMedSearchRequest


class Extractor:
    def __init__(self, data):
        self.data = data

    def extract(self, request, **kwargs):
        return json.dumps(self.data)


def plan(question="哮喘 breath analysis", groups=None, **extra):
    return PicoPlanner(
        extractor=Extractor(
            dict(
                question_type="other",
                pico=dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
                terms=[
                    dict(
                        text=question,
                        origin="user_text",
                        source_span=dict(start=0, end=len(question)),
                    )
                ],
                ambiguities=[],
                blocking_ambiguities=[],
                concept_groups=groups or [],
                **extra,
            )
        )
    ).plan(ClassificationRequest(question=question))


@pytest.mark.parametrize(
    "question", ["哮喘呼气分析", "asthma breath analysis", "哮喘 breath analysis"]
)
def test_a_mapping_same_query(question):
    p = plan(
        question,
        [["asthma"], ["breath analysis"]],
        research_intent="discovery",
        concept_mappings=[
            dict(source_text=question, english_terms=["asthma"], role="population", required=True)
        ],
    )
    assert p.research_intent == "discovery"
    assert p.concept_mappings[0].source_text == question
    assert (
        PubMedSearchRequest(question=question, query_plan=p).query_text()
        == '("asthma") AND ("breath analysis")'
    )


def test_a_legacy_is_explicitly_degraded():
    req = PubMedSearchRequest(question="q", query_plan=plan())
    assert req.planning_warnings() == ["legacy_terms_without_concept_relationships"]
    assert req.query_text() == req.query_plan.original_question


# Held out until B implementation is frozen: Parkinson/gait and spatial deconvolution.


def test_c_audit_and_context_contracts():
    from clinical_agent.domain.pubmed import SearchProvenance
    from clinical_agent.domain.research import GenerationEvidence, GenerationInput

    assert {
        "searched_pmids",
        "fetched_pmids",
        "candidate_outcomes",
    } <= SearchProvenance.model_fields.keys()
    assert {"query_plan", "search_provenance"} <= GenerationInput.model_fields.keys()
    assert {"title", "pmid"} <= GenerationEvidence.model_fields.keys()


def test_d_report_has_explicit_audit_mode():
    import inspect

    from clinical_agent.domain.report import render_report

    assert inspect.signature(render_report).parameters["include_audit"].default is False


@pytest.mark.parametrize(
    "groups", [[["multiple sclerosis", "MS"]], [["cell senescence"]], [["batch correction"]]]
)
def test_a_normalized_groups_are_not_disease_required(groups):
    p = plan("synthetic methodology question", groups)
    query = PubMedSearchRequest(question=p.original_question, query_plan=p).query_text()
    assert all('"' + term + '"' in query for term in groups[0])
    assert " AND " not in query
