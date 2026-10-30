"""Offline PubMed metadata-only smoke using the actual HTTPX adapter."""

import httpx

from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings
from clinical_agent.domain.pubmed import PubMedSearchRequest


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("esearch.fcgi"):
        return httpx.Response(200, json={"esearchresult": {"count": "1", "idlist": ["123"]}})
    return httpx.Response(
        200,
        content=(
            b"<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
            b"<Article><ArticleTitle>Synthetic teaching record</ArticleTitle></Article>"
            b"</MedlineCitation></PubmedArticle></PubmedArticleSet>"
        ),
    )


if __name__ == "__main__":
    with httpx.Client(transport=httpx.MockTransport(handler)) as session:
        result = PubMedClient(session, PubMedSettings()).search(
            PubMedSearchRequest(question="synthetic")
        )
        print(result.model_dump_json())
