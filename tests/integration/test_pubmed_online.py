"""Online source graph/API/CLI contracts and a small opt-in official endpoint smoke."""

from uuid import uuid4

import pytest


def options():
    from clinical_agent.domain.pubmed import PubMedOptions

    return PubMedOptions(query="aspirin[Title]", max_results=2)


def test_online_scope_cli_and_api_contract():
    from pydantic import ValidationError

    from clinical_agent.api.schemas import QuestionBody
    from clinical_agent.domain.research import QuestionRequest

    request = QuestionRequest(request_id=uuid4(), question="q", scope="online", pubmed=options())
    assert request.scope == "online"
    assert QuestionBody(question="q", scope="hybrid", pubmed=options()).scope == "hybrid"
    with pytest.raises(ValidationError):
        QuestionBody(question="q", scope="local", pubmed=options())


@pytest.mark.parametrize(
    "code,status", [("pubmed_failed", 503), ("pubmed_invalid", 502), ("pubmed_timeout", 504)]
)
def test_api_pubmed_error_mapping(tmp_path, code, status):
    from contextlib import contextmanager

    from fastapi.testclient import TestClient

    from clinical_agent.api import create_app
    from clinical_agent.api.runtime import ServiceBundle
    from clinical_agent.api.schemas import ApiSettings
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

    from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest
    from clinical_agent.integrations.pubmed_online import open_pubmed

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
