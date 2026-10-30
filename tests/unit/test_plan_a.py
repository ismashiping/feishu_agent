"""Synthetic extraction failures, never real paper contents or provider output."""

import json
import logging

import pytest

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.research import ResearchError


def draft(q):
    return dict(
        question_type="other",
        pico=dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
        ambiguities=[],
        blocking_ambiguities=[],
        terms=[dict(text=q, origin="user_text", source_span=dict(start=0, end=len(q)))],
    )


class Extractor:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def extract(self, request, **kw):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


@pytest.mark.parametrize(
    "failure,stage",
    [("json", "json"), ("schema", "schema"), ("span", "span"), ("provider", "provider")],
)
def test_safe_failure_diagnostics(failure, stage, caplog):
    q = "asthma breath analysis SECRET_DO_NOT_LOG"
    data = draft(q)
    value = json.dumps(data)
    if failure == "json":
        value = "SECRET_DO_NOT_LOG {"
    if failure == "schema":
        data["question_type"] = "SECRET_DO_NOT_LOG"
        value = json.dumps(data)
    if failure == "span":
        data["terms"][0]["text"] = "missing quote"
        data["terms"][0]["source_span"] = {"start": 0, "end": 3}
        value = json.dumps(data)
    if failure == "provider":
        value = RuntimeError("SECRET_DO_NOT_LOG")
    ex = Extractor(value)
    with caplog.at_level(logging.WARNING), pytest.raises(ResearchError, match="extraction_failed"):
        PicoPlanner(extractor=ex).plan(ClassificationRequest(question=q))
    assert ex.calls == 1
    assert "SECRET_DO_NOT_LOG" not in caplog.text
    assert any(getattr(r, "stage", None) == stage for r in caplog.records)
    assert all("SECRET_DO_NOT_LOG" not in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    "q",
    [
        "哮喘呼气分析",
        "asthma breath analysis",
        "哮喘 breath analysis",
        "Parkinson disease gait analysis",
    ],
)
def test_optional_mapping_cannot_silently_become_required(q):
    data = draft(q)
    data["concept_mappings"] = [
        dict(source_text=q, english_terms=["optional method"], role="method", required=False)
    ]
    data["concept_groups"] = [["optional method"]]
    with pytest.raises(ResearchError, match="extraction_failed"):
        PicoPlanner(extractor=Extractor(json.dumps(data))).plan(ClassificationRequest(question=q))


def test_actual_search_snapshot_statuses():
    from pathlib import Path

    from clinical_agent.domain.pubmed import PubMedSearchResult

    data = json.loads(
        Path("docs/final-acceptance/docker-e2e/actual-zh.json").read_text(encoding="utf-8")
    )
    result = PubMedSearchResult.model_validate(data["search"])
    assert result.total_count == 3 and len(result.records) == 3 and not result.truncated
    assert result.pmid_status("39752907") == "not_in_returned_set"
    assert result.model_copy(update={"searched_pmids": None}).pmid_status("39752907") == "unknown"
    assert result.model_copy(update={"status": "partial"}).pmid_status("39752907") == "unknown"


def test_official_warning_detail_is_bounded():
    import httpx

    from tests.unit.test_pubmed_online import client, search

    def handler(request):
        return httpx.Response(
            200,
            json={
                "esearchresult": {
                    "count": "0",
                    "idlist": [],
                    "warninglist": {"quotedphrasesnotfound": ["x" * 500] * 25},
                }
            },
        )

    result = search(client(handler))
    assert len(result.search_warnings) == 10
    assert all(len(w) == 300 for w in result.search_warnings)
    assert result.searched_pmids == [] and result.pmid_status("123") == "not_in_returned_set"


@pytest.mark.parametrize(
    "q,groups",
    [
        ("哮喘呼气分析", [["asthma"], ["breath analysis"]]),
        ("Parkinson disease gait analysis", [["Parkinson disease"], ["gait analysis"]]),
        ("batch correction 方法综述", [["batch correction"]]),
    ],
)
def test_fixed_queries_keep_constraints_and_explicit_override(q, groups):
    from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest

    data = draft(q)
    data["concept_groups"] = groups
    plan = PicoPlanner(extractor=Extractor(json.dumps(data))).plan(
        ClassificationRequest(question=q)
    )
    req = PubMedSearchRequest(question=q, query_plan=plan)
    assert req.query_text() == " AND ".join(
        "(" + " OR ".join('"' + t + '"' for t in g) + ")" for g in groups
    )
    assert (
        PubMedSearchRequest(
            question=q, query_plan=plan, options=PubMedOptions(query="user supplied query")
        ).query_text()
        == "user supplied query"
    )
