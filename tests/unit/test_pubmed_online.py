"""Official-format fixtures, request limits, parsing and truthful online provenance."""

import hashlib
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError


def article(pmid="123", abstract=True):
    text = (
        '<Abstract><AbstractText Label="RESULTS">A <i>mixed</i> result.</AbstractText></Abstract>'
        if abstract
        else ""
    )
    return f"""<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article>
    <Journal><Title>Fixture Journal</Title><JournalIssue><PubDate>
    <Year>2020</Year><Month>Feb</Month></PubDate></JournalIssue></Journal>
    <ArticleTitle>Synthetic <i>title</i></ArticleTitle><AuthorList><Author>
    <CollectiveName>Study Group</CollectiveName></Author></AuthorList>
    {text}<PublicationTypeList><PublicationType UI="D016449">
    Randomized Controlled Trial</PublicationType></PublicationTypeList>
    </Article><CommentsCorrectionsList><CommentsCorrections RefType="ErratumIn">
    <PMID>456</PMID></CommentsCorrections></CommentsCorrectionsList>
    </MedlineCitation><PubmedData><ArticleIdList>
    <ArticleId IdType="pubmed">{pmid}</ArticleId></ArticleIdList>
    </PubmedData></PubmedArticle>"""


def xml(*records):
    return ("<PubmedArticleSet>" + "".join(records) + "</PubmedArticleSet>").encode()


class Clock:
    def __init__(self):
        self.time = 0.0
        self.waits = []

    def __call__(self):
        return self.time

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.time += seconds


def client(handler, **kwargs):
    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings, RequestGate

    clock = kwargs.pop("clock", Clock())
    session = httpx.Client(transport=httpx.MockTransport(handler))
    return PubMedClient(
        session,
        PubMedSettings(api_key="fake-secret"),
        gate=RequestGate(clock=clock, sleep=clock.sleep),
        clock=clock,
        **kwargs,
    )


def search(client, **kwargs):
    from clinical_agent.domain.pubmed import PubMedOptions, PubMedSearchRequest

    return client.search(
        PubMedSearchRequest(question="test question", options=PubMedOptions(**kwargs))
    )


def test_parameters_metadata_snapshot_and_no_key_in_results():
    from urllib.parse import parse_qs

    calls = []

    def handler(request):
        args = parse_qs(request.content.decode())
        calls.append((request, args))
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "2",
                        "idlist": ["123", "124"],
                        "querytranslation": "official translation",
                    }
                },
            )
        return httpx.Response(200, content=xml(article(), article("124", False)))

    result = search(
        client(handler),
        query="aspirin[Title]",
        date_from="2020-01-01",
        date_to="2021-01-01",
        sort="pub_date",
    )
    assert result.returned_count == 2 and result.status == "complete"
    record = result.records[0]
    assert record.title == "Synthetic title" and record.authors == ["Study Group"]
    assert record.publication_date.precision == "month" and record.doi is None
    assert record.publication_types == ["Randomized Controlled Trial"]
    assert record.notices == ["ErratumIn:456"]
    assert record.abstract == "A mixed result." and record.source_units[0].start == 0
    assert record.content_hash == hashlib.sha256(record.snapshot_xml.encode()).hexdigest()
    assert result.records[1].content_scope == "metadata_only" and not result.records[1].source_units
    assert calls[0][1]["term"] == ["aspirin[Title]"]
    assert calls[0][1]["sort"] == ["pub_date"] and calls[0][1]["mindate"] == ["2020/01/01"]
    assert all(r.method == "POST" and "fake-secret" not in str(r.url) for r, _ in calls)
    assert "fake-secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    "options",
    [
        {"max_results": 0},
        {"max_results": 21},
        {"date_from": "2020-01-01"},
        {"date_from": "2021-01-01", "date_to": "2020-01-01"},
        {"sort": "random"},
        {"query": " "},
    ],
)
def test_invalid_options(options):
    from clinical_agent.domain.pubmed import PubMedOptions

    with pytest.raises(ValidationError):
        PubMedOptions(**options)


def test_zero_search_is_complete_and_does_not_fetch():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})

    result = search(client(handler))
    assert result.records == [] and result.total_count == 0 and result.status == "complete"
    assert len(calls) == 1


def test_pages_order_and_batches_are_bounded():
    from urllib.parse import parse_qs

    starts = []

    def handler(request):
        args = parse_qs(request.content.decode())
        if request.url.path.endswith("esearch.fcgi"):
            start = int(args["retstart"][0])
            starts.append(start)
            return httpx.Response(
                200,
                json={
                    "esearchresult": {
                        "count": "30000",
                        "idlist": [str(i) for i in range(1 + start, 11 + start)],
                    }
                },
            )
        return httpx.Response(
            200, content=xml(*(article(i) for i in reversed(args["id"][0].split(","))))
        )

    result = search(client(handler), max_results=20)
    assert starts == [0, 10] and result.truncated
    assert [r.pmid for r in result.records] == [str(i) for i in range(1, 21)]


@pytest.mark.parametrize("mode", ["missing", "unexpected", "duplicate", "http_failure"])
def test_bad_or_missing_fetch_is_partial_not_normal_empty(mode):
    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(
                200, json={"esearchresult": {"count": "2", "idlist": ["123", "124"]}}
            )
        if mode == "http_failure":
            return httpx.Response(503)
        if mode == "unexpected":
            return httpx.Response(200, content=xml(article("999")))
        if mode == "duplicate":
            return httpx.Response(200, content=xml(article(), article()))
        return httpx.Response(200, content=xml(article()))

    result = search(client(handler))
    assert result.status == "partial" and "124" in result.missing_pmids
    assert result.warnings and result.returned_count < 2


@pytest.mark.parametrize("status", [429, 503])
def test_retry_after_and_retry_bound(status):
    clock = Clock()
    calls = []

    def handler(request):
        calls.append(clock())
        return httpx.Response(status, headers={"Retry-After": "2"})

    from clinical_agent.domain.research import ResearchError

    with pytest.raises(ResearchError, match="pubmed_failed"):
        search(client(handler, clock=clock))
    assert len(calls) == 2 and calls[1] - calls[0] >= 2


def test_large_retry_after_does_not_retry_early():
    from clinical_agent.domain.research import ResearchError

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})

    with pytest.raises(ResearchError):
        search(client(handler))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"error": "private"}),
        httpx.Response(200, content=b"bad json"),
        httpx.Response(200, json={"esearchresult": {"count": "-1", "idlist": []}}),
    ],
)
def test_bad_search_never_returns_zero_success(response):
    from clinical_agent.domain.research import ResearchError

    with pytest.raises(ResearchError, match="pubmed_invalid"):
        search(client(lambda request: response))


def test_total_timeout_and_response_size_limit():
    from clinical_agent.domain.research import ResearchError

    clock = Clock()

    def late(request):
        clock.time += 31
        return httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})

    with pytest.raises(ResearchError, match="pubmed_timeout"):
        search(client(late, clock=clock))
    with pytest.raises(ResearchError, match="pubmed_invalid"):
        search(
            client(lambda request: httpx.Response(200, content=b"x" * 101), max_response_bytes=100)
        )


def test_safe_online_parser_reuses_offline_mapping():
    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.domain.research import ResearchError

    records = parse_pubmed_response(xml(article()), fetched_at=datetime.now(UTC))
    assert (
        records[0].pmid == "123" and records[0].source_url == "https://pubmed.ncbi.nlm.nih.gov/123/"
    )
    with pytest.raises(ResearchError, match="pubmed_invalid"):
        parse_pubmed_response(
            b'<!DOCTYPE x [<!ENTITY x "bad">]><PubmedArticleSet>&x;</PubmedArticleSet>',
            fetched_at=datetime.now(UTC),
        )


def test_shared_gate_serializes_two_clients():
    from clinical_agent.adapters.pubmed_online import PubMedClient, PubMedSettings, RequestGate

    clock = Clock()
    starts = []

    def handler(request):
        starts.append(clock())
        return httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})

    gate = RequestGate(clock=clock, sleep=clock.sleep)
    with httpx.Client(transport=httpx.MockTransport(handler)) as session:
        for _ in range(2):
            search(PubMedClient(session, PubMedSettings(), gate=gate, clock=clock))
    assert starts[1] - starts[0] >= 0.34


def test_online_evidence_has_no_invented_embedding_and_metadata_only_is_not_evidence():
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.domain.retrieval import RetrievalRequest

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(
                200, json={"esearchresult": {"count": "2", "idlist": ["123", "124"]}}
            )
        return httpx.Response(200, content=xml(article(), article("124", False)))

    result = PubMedRetrievalService(client(handler)).retrieve(
        RetrievalRequest(question="q", scope="online")
    )
    assert len(result.hits) == 1 and result.embedding_info is None
    hit = result.hits[0]
    assert hit.chunk.embedding_info is None and hit.score_type == "pubmed_rank"
    assert str(hit.document.source_uri) == "https://pubmed.ncbi.nlm.nih.gov/123/"
    assert hit.chunk.text == "A mixed result."
    assert result.search_provenance.returned_count == 2


def test_hybrid_reserves_online_and_deduplicates_real_pmid(source_factory, prepared_factory):
    from clinical_agent.application.pubmed import PubMedRetrievalService, merge_sources
    from clinical_agent.domain.retrieval import (
        DocumentSummary,
        EvidenceHit,
        RetrievalOptions,
        RetrievalRequest,
        RetrievalResult,
        retrieval_embedding_info,
    )

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(
                200, json={"esearchresult": {"count": "2", "idlist": ["123", "124"]}}
            )
        return httpx.Response(200, content=xml(article(), article("124")))

    options = RetrievalOptions(top_k=2)
    prepared = prepared_factory(source_factory(kind="pubmed", pmid="123"))
    local = RetrievalResult(
        options=options,
        embedding_info=retrieval_embedding_info(),
        hits=[
            EvidenceHit(
                document=DocumentSummary.from_document(prepared.source.parsed.document),
                chunk=prepared.embedded[0].evidence,
                score=0.9,
                rank=1,
            )
        ],
    )
    online = PubMedRetrievalService(client(handler)).retrieve(
        RetrievalRequest(question="q", scope="online", options=options)
    )
    result = merge_sources(local, online)
    assert result.scope == "hybrid" and [h.document.pmid for h in result.hits] == ["123", "124"]
    assert [h.score_type for h in result.hits] == ["cosine_similarity", "pubmed_rank"]


def test_partial_without_acquired_records_is_error_not_insufficient_evidence():
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.domain.research import ResearchError
    from clinical_agent.domain.retrieval import RetrievalRequest

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"count": "1", "idlist": ["123"]}})
        return httpx.Response(200, content=xml())

    with pytest.raises(ResearchError, match="pubmed_failed"):
        PubMedRetrievalService(client(handler)).retrieve(
            RetrievalRequest(question="q", scope="online")
        )


def test_parser_obeys_remaining_search_deadline():
    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.domain.research import ResearchError

    def expired():
        raise ResearchError("pubmed_timeout")

    with pytest.raises(ResearchError, match="pubmed_timeout"):
        parse_pubmed_response(xml(article()), fetched_at=datetime.now(UTC), check_deadline=expired)


def test_zero_count_with_returned_ids_is_invalid():
    from clinical_agent.domain.research import ResearchError

    with pytest.raises(ResearchError, match="pubmed_invalid"):
        search(
            client(
                lambda request: httpx.Response(
                    200, json={"esearchresult": {"count": "0", "idlist": ["123"]}}
                )
            )
        )
