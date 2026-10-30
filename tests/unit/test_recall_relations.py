import json

import pytest
from pydantic import ValidationError

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.pubmed import PubMedSearchRequest


class Extractor:
    def __init__(self, value):
        self.value = value

    def extract(self, request, **kwargs):
        return self.value


def draft(q):
    return dict(
        question_type="other",
        pico=dict.fromkeys(["population", "intervention", "comparison", "outcome"]),
        ambiguities=[],
        blocking_ambiguities=[],
        terms=[dict(text=q, origin="user_text", source_span=dict(start=0, end=len(q)))],
    )


def request():
    q = "liver tumor subregion segmentation"
    data = draft(q)
    data["concept_relations"] = [
        dict(
            source_text="liver tumor",
            english_term=t,
            concept_id="disease",
            relation=r,
            required=req,
        )
        for t, r, req in [
            ("liver tumor", "required_constraint", True),
            ("hepatic neoplasm", "exact_synonym", False),
            ("hepatocellular carcinoma", "narrower_concept", False),
        ]
    ] + [
        dict(
            source_text="subregion segmentation",
            english_term=t,
            concept_id="task",
            relation=r,
            required=req,
        )
        for t, r, req in [
            ("subregion segmentation", "required_constraint", True),
            ("tumor habitat", "related_concept", False),
        ]
    ]
    plan = PicoPlanner(extractor=Extractor(json.dumps(data))).plan(
        ClassificationRequest(question=q)
    )
    return PubMedSearchRequest(question=q, query_plan=plan)


def test_direct_and_supplement_are_separate():
    req = request()
    direct = req.query_text()
    assert "hepatic neoplasm" in direct
    assert "hepatocellular carcinoma" not in direct
    assert "tumor habitat" not in direct
    strategies = req.query_strategies()
    assert len(strategies) == 2
    assert "tumor habitat" in strategies[1][1]
    assert "liver tumor" in strategies[1][1]
    assert "hepatocellular carcinoma" in strategies[1][1]


def test_explicit_override_disables_expansion():
    req = request()
    req.options.query = "123[uid]"
    assert req.query_strategies() == [("explicit", "123[uid]")]


def test_subtype_cannot_be_required():
    req = request()
    data = req.query_plan.model_dump()
    data["concept_relations"][2]["required"] = True
    with pytest.raises(ValidationError):
        type(req.query_plan).model_validate(data)


def test_real_transport_shape_supplement_and_dedup():
    from urllib.parse import parse_qs

    import httpx

    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings

    calls = []

    def handler(http_request):
        params = parse_qs(http_request.content.decode())
        calls.append(params)
        if http_request.url.path.endswith("esearch.fcgi"):
            expanded = "tumor habitat" in params["term"][0]
            ids = ["123", "456"] if expanded else ["123"]
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": str(len(ids)),
                        "idlist": ids,
                        "querytranslation": params["term"][0],
                    }
                },
            )
        articles = "".join(
            "<PubmedArticle><MedlineCitation><PMID>" + p + "</PMID><Article>"
            "<ArticleTitle>Synthetic</ArticleTitle><Abstract><AbstractText>Fixture</AbstractText>"
            "</Abstract></Article></MedlineCitation></PubmedArticle>"
            for p in params["id"][0].split(",")
        )
        return httpx.Response(
            200, content=("<PubmedArticleSet>" + articles + "</PubmedArticleSet>").encode()
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        result = PubMedClient(http, PubMedSettings()).search(request())
    assert [r.pmid for r in result.records] == ["123", "456"]
    assert [r["strategy"] for r in result.query_rounds] == ["direct", "related_narrower"]
    assert len(calls) == 4
    assert result.trace_id
