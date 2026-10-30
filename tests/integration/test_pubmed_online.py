"""Online source graph/API/CLI contracts and a small opt-in official endpoint smoke."""

from uuid import uuid4

import pytest


def options():
    from clinical_agent.domain.pubmed import PubMedOptions

    return PubMedOptions(query="aspirin[Title]", max_results=2)


def test_online_graph_keeps_provenance_and_never_calls_local():
    import httpx

    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.research import QuestionRequest

    def article():
        return (
            "<PubmedArticle><MedlineCitation><PMID>123</PMID><Article>"
            "<ArticleTitle>Fixture</ArticleTitle><Abstract>"
            "<AbstractText>Abstract only.</AbstractText></Abstract>"
            "</Article></MedlineCitation></PubmedArticle>"
        )

    def xml(record):
        return ("<PubmedArticleSet>" + record + "</PubmedArticleSet>").encode()

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"count": "1", "idlist": ["123"]}})
        return httpx.Response(200, content=xml(article()))

    class Generator:
        def generate(self, context, *, timeout_seconds):
            import json

            return json.dumps(
                {
                    "claims": [
                        {
                            "text": "Only the supplied abstract is available.",
                            "kind": "uncertainty",
                            "evidence_chunk_ids": [str(context.evidence[0].chunk_id)],
                            "limitations": [],
                        }
                    ]
                }
            )

    with httpx.Client(transport=httpx.MockTransport(handler)) as session:
        online = PubMedRetrievalService(PubMedClient(session, PubMedSettings()))
        answer = ResearchService(
            retriever=object(), generator=Generator(), online_retriever=online
        ).answer(
            QuestionRequest(
                request_id=uuid4(), question="question", scope="online", pubmed=options()
            )
        )
    assert answer.status == "answered" and answer.retrieval_scope == "online"
    assert answer.sources[0].pmid == "123" and answer.sources[0].content_scope == "abstract"
    assert answer.search_provenance.returned_count == 1
    import hashlib

    from pydantic import ValidationError

    from clinical_agent.domain.research import ResearchAnswer

    snapshot = answer.sources[0].snapshot_xml
    assert (
        snapshot and hashlib.sha256(snapshot.encode()).hexdigest() == answer.sources[0].content_hash
    )
    corrupted = answer.model_dump()
    corrupted["sources"][0]["snapshot_xml"] += "changed"
    with pytest.raises(ValidationError):
        ResearchAnswer.model_validate(corrupted)
    assert not any("仅检索本地" in text for text in answer.limitations)
    from feishu.sender import render_answer

    answer.claims = [
        answer.claims[0].model_copy(update={"claim_id": f"c{i}", "text": "x" * 2000})
        for i in range(1, 21)
    ]
    rendered = render_answer(answer)
    assert "结果过长" in rendered and "PubMed" in rendered and "本次仅检索本地" not in rendered


def test_online_scope_cli_and_api_contract():
    from pydantic import ValidationError

    from clinical_agent.api_runtime import QuestionBody
    from clinical_agent.domain.research import QuestionRequest

    request = QuestionRequest(request_id=uuid4(), question="q", scope="online", pubmed=options())
    assert request.scope == "online"
    assert QuestionBody(question="q", scope="hybrid", pubmed=options()).scope == "hybrid"
    with pytest.raises(ValidationError):
        QuestionBody(question="q", scope="local", pubmed=options())


def test_online_cli_api_and_feishu_render_empty_search(tmp_path, capsys):
    from contextlib import contextmanager

    import httpx
    from fastapi.testclient import TestClient

    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings
    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.application.research import ResearchService
    from clinical_agent.cli import main

    @contextmanager
    def service(model_dir=None):
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json={"esearchresult": {"count": "0", "idlist": []}}
                )
            )
        ) as session:
            yield ResearchService(
                retriever=object(),
                generator=object(),
                online_retriever=PubMedRetrievalService(PubMedClient(session, PubMedSettings())),
            )

    assert (
        main(
            [
                "ask",
                "--model-dir",
                ".",
                "--question",
                "q",
                "--scope",
                "online",
                "--pubmed-query",
                "aspirin[Title]",
            ],
            research_factory=service,
        )
        == 2
    )
    assert "invalid_arguments" in capsys.readouterr().err
    # Historical injected PubMed API fixtures remain readable; the production runtime
    # is now OpenAlex-only and the retired CLI expression is explicitly rejected.

    @contextmanager
    def runtime(settings):
        with service() as research:
            yield ServiceBundle(ingestion=object(), research=research)

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as api:
        response = api.post(
            "/v1/questions",
            json={"question": "q", "scope": "online", "pubmed": {"query": "aspirin[Title]"}},
        )
    assert response.status_code == 200
    assert response.json()["search_provenance"]["total_count"] == 0


@pytest.mark.parametrize(
    "code,status", [("pubmed_failed", 503), ("pubmed_invalid", 502), ("pubmed_timeout", 504)]
)
def test_api_pubmed_error_mapping(tmp_path, code, status):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api_runtime import ApiSettings, ServiceBundle
    from clinical_agent.domain.research import ResearchError

    class Bad:
        def answer(self, request):
            raise ResearchError(code)

    @contextmanager
    def runtime(settings):
        yield ServiceBundle(ingestion=object(), research=Bad())

    settings = ApiSettings(
        model_dir=tmp_path, import_root=tmp_path, snapshot_dir=tmp_path / "snapshots"
    )
    with TestClient(create_app(settings=settings, runtime_factory=runtime)) as api:
        response = api.post("/v1/questions", json={"question": "q", "scope": "online"})
    assert response.status_code == status and response.json()["error_code"] == code


@pytest.mark.external
def test_live_official_pubmed(tmp_path):
    import json

    from clinical_agent.adapters.pubmed_online import open_pubmed
    from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest

    with open_pubmed() as client:
        result = client.search(
            PubMedSearchRequest(
                question="official small smoke",
                options=PubMedOptions(
                    query="aspirin[Title] AND randomized controlled trial[Publication Type]",
                    max_results=2,
                ),
            )
        )
    (tmp_path / "pubmed-live.json").write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert result.status == "complete" and result.records
    for record in result.records:
        assert record.pmid.isdigit() and record.title and record.snapshot_xml
        assert record.source_url == f"https://pubmed.ncbi.nlm.nih.gov/{record.pmid}/"
        assert record.content_scope in {"abstract", "metadata_only"}
