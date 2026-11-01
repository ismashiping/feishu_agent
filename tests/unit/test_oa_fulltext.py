"""OpenAlex OA engineering contracts; synthetic text is never medical evidence."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic

import httpx
import pytest

from clinical_agent.domain.openalex import OpenAlexRecord
from clinical_agent.integrations.oa_fulltext import OAFulltextSource, parse_tei, safe_url


def record():
    runs = json.loads(
        Path("history/docs-20261101/openalex-stage2/live-check.json").read_text(encoding="utf8")
    )
    return next(
        OpenAlexRecord.model_validate(r)
        for run in runs
        for r in run.get("provenance", {}).get("records", [])
        if r["doi"] == "10.1038/s41598-024-78917-y"
    )


def tei(doi="10.1038/s41598-024-78917-y"):
    title = record().title
    return f"""<TEI><teiHeader><fileDesc><titleStmt><title>{title}</title></titleStmt>
<sourceDesc><biblStruct><idno>{doi}</idno></biblStruct></sourceDesc></fileDesc></teiHeader>
<text><body><div><head>Methods</head><p>Synthetic paragraph: we used a network.</p></div>
<div><head>Results</head><p>Synthetic result: this is not a scientific finding.</p></div>
</body></text></TEI>""".encode()


def test_structured_identity_and_positions():
    units = parse_tei(tei(), record())
    assert units[0].section == "Methods"
    assert units[0].start == 0
    assert units[1].start == len(units[0].text) + 2
    with pytest.raises(ValueError, match="identity"):
        parse_tei(tei("10.1234/wrong"), record())


def test_tei_table_text_is_not_concatenated_into_the_paragraph():
    raw = tei().replace(
        b"we used a network.",
        b"we used a network.<table><row><cell>123</cell><cell>456</cell></row></table>",
    )
    assert "123456" not in parse_tei(raw, record())[0].text


def test_download_budget_and_response_size():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * (10 * 1024 * 1024 + 1))
        )
    ) as client:
        source = OAFulltextSource(client, resolve=_public_resolve)
        with pytest.raises(ValueError, match="budget"):
            source.download("https://www.nature.com/x", monotonic() + 5, [6])
        with pytest.raises(ValueError, match="budget"):
            source.download("https://www.nature.com/x", monotonic() + 5, [0])


@pytest.mark.parametrize(
    "url",
    [
        "http://www.nature.com/x",
        "https://127.0.0.1/a",
        "https://www.nature.com.evil.test/x",
        "https://user:password@www.nature.com/a",
        "https://www.nature.com:8443/a",
    ],
)
def test_untrusted_url_rejected(url):
    with pytest.raises(ValueError):
        safe_url(url)


def test_redirect_is_revalidated():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(302, headers={"location": "https://127.0.0.1/private"})
        )
    ) as client:
        with pytest.raises(ValueError):
            OAFulltextSource(client).download("https://www.nature.com/a.pdf", monotonic() + 10, [0])


def test_missing_url_is_not_reported_as_a_license_refusal():
    work = json.loads(record().snapshot_json)
    work["has_content"] = {"pdf": False, "grobid_xml": False}
    work["content_urls"] = None
    work["best_oa_location"] = None
    work["locations"] = [{"is_oa": True, "pdf_url": None, "license": None}]
    bare = OpenAlexRecord.from_work(work)

    def handler(request):
        pytest.fail(str(request.url))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="fulltext_no_fulltext_url"):
            _source(client).fetch_record(bare, monotonic() + 5, [0])


def test_reranking_uses_specific_question():
    from types import SimpleNamespace

    from clinical_agent.application.oa_fulltext import rerank_passages

    candidates = [
        SimpleNamespace(text=t, section="Background" if i < 2 else "Methods")
        for i, t in enumerate(
            [
                "Microvascular invasion prediction MRI background.",
                "Patients with microvascular invasion.",
                "CT scanners used contrast agents.",
                "MRI sequences used a contrast agent.",
            ]
        )
    ]
    assert (
        rerank_passages(
            candidates, "Which CT scanners and MRI sequences and contrast agents were used?"
        )[:2]
        == candidates[2:]
    )


def test_real_pdf_fixture():
    from clinical_agent.integrations.oa_fulltext import parse_oa_pdf

    root = Path("tests/fixtures/oa_fulltext")
    r = OpenAlexRecord.model_validate_json((root / "plos-record.json").read_text(encoding="utf8"))
    raw = (root / "plos-fulltext.pdf").read_bytes()
    manifest = json.loads((root / "plos-pdf-manifest.json").read_text(encoding="utf8"))
    assert sha256(raw).hexdigest() == manifest["sha256"]
    units = parse_oa_pdf(raw, r)
    assert max(u.page for u in units) == 15


def test_pdf_pages_sections_headers_and_identity(tmp_path):
    from clinical_agent.integrations.oa_fulltext import parse_oa_pdf
    from tests.integration.test_pdf import _write_pdf

    r = record()
    path = tmp_path / "synthetic.pdf"
    _write_pdf(
        path,
        texts=(
            r.title + "\n" + r.doi + "\nMethods\nSynthetic methods.",
            "Results\nSynthetic results.",
        ),
    )
    units = parse_oa_pdf(path.read_bytes(), r)
    assert {u.page for u in units} == {1, 2}
    assert any(u.section == "Methods" for u in units)
    with pytest.raises(ValueError, match="identity"):
        parse_oa_pdf(path.read_bytes(), r.model_copy(update={"doi": "10.1234/wrong"}))


def test_openalex_cache_roundtrip_and_fulltext_citation():
    from uuid import uuid4

    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import record_hit
    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.research import (
        DraftClaim,
        GenerationDraft,
        QuestionRequest,
        ResearchError,
    )
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
    from tests.unit.test_fulltext_rag import Embedder

    r = record()
    hit = record_hit(r, datetime.now(UTC))
    retrieval = RetrievalResult(
        scope="online",
        options=RetrievalOptions(),
        embedding_info=None,
        hits=[hit],
        search_provenance={
            "endpoint": "https://api.openalex.org/works",
            "query_sent": "liver",
            "fetched_at": datetime.now(UTC),
            "date_from": None,
            "date_to": None,
        },
    )

    class Store:
        payload = None

        def load(self, key, signature):
            return self.payload

        def reuse_content(self, key, signature, digest):
            return False

        def publish(self, key, signature, payload, vectors):
            self.payload = payload

        def search(self, key, vector, limit):
            return self.payload["passages"][:limit]

    class Source:
        calls = 0

        def fetch_record(self, value, deadline, count):
            self.calls += 1
            return (
                "CC BY",
                "https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/",
                tei(),
                parse_tei(tei(), value),
            )

    source, store, embedder = Source(), Store(), Embedder()
    service = FulltextService(source, store, embedder)
    enriched = service.enrich("methods", retrieval, deadline=monotonic() + 30)
    assert enriched.hits[0].fulltext
    p = enriched.hits[0].fulltext[0]
    assert p.pmid is None and p.paper_key == "doi:" + r.doi
    assert p.openalex_id == r.openalex_id
    service.enrich("results", retrieval, deadline=monotonic() + 30)
    assert source.calls == embedder.calls == 1
    answer = build_answer(
        QuestionRequest(request_id=uuid4(), question="methods", scope="online"),
        enriched,
        GenerationDraft(
            claims=[
                DraftClaim(
                    text="Synthetic dataflow only.",
                    kind="evidence",
                    evidence_chunk_ids=[p.chunk_id],
                    limitations=[],
                )
            ]
        ),
        generated_at=datetime.now(UTC),
    )
    assert answer.sources[0].evidence[0].location.section == "Methods"
    assert sha256(tei()).hexdigest() == p.content_hash
    from clinical_agent.channels.feishu.sender import render_answer

    rendered = render_answer(answer)
    assert "全文段落" in rendered
    assert "摘要（未阅读全文）" not in rendered
    assert "部分来源仅包含摘要" not in answer.limitations
    with pytest.raises(ResearchError, match="citation_invalid"):
        build_answer(
            QuestionRequest(request_id=uuid4(), question="methods", scope="online"),
            enriched,
            GenerationDraft(
                claims=[
                    DraftClaim(
                        text="Synthetic abstract only.",
                        kind="evidence",
                        evidence_chunk_ids=[enriched.hits[0].chunk.chunk_id],
                        limitations=[],
                    )
                ]
            ),
            generated_at=datetime.now(UTC),
        )
    enriched.hits[0].fulltext[0].paper_key = "doi:10.1234/wrong"
    with pytest.raises(ValueError):
        RetrievalResult.model_validate(enriched)


def _public_resolve(host, port, *args, **kwargs):
    blocked = host in {"127.0.0.1", "localhost"} or str(host).endswith((".local", ".internal"))
    ip = "127.0.0.1" if blocked else "93.184.216.34"
    return [(2, 1, 6, "", (ip, port))]


def _nnunet(**changes):
    work = {
        "id": "https://openalex.org/W3014974815",
        "title": (
            "nnU-Net: a self-configuring method for deep learning-based "
            "biomedical image segmentation"
        ),
        "authorships": [{"author": {"display_name": "Fabian Isensee"}}],
        "doi": "https://doi.org/10.1038/s41592-020-01008-z",
        "primary_location": {"source": {"display_name": "Nature Methods"}},
        "publication_date": "2021-02-01",
        "abstract_inverted_index": {"nnUNet": [0], "configures": [1], "segmentation": [2]},
        "type": "article",
        "is_retracted": False,
        "open_access": {"is_oa": True, "license": None},
        "has_content": {"pdf": False, "grobid_xml": False},
        "content_urls": None,
        "best_oa_location": {
            "is_oa": True,
            "license": None,
            "pdf_url": "https://arxiv.org/pdf/1904.08128",
        },
        "locations": [
            {
                "is_oa": True,
                "license": None,
                "pdf_url": "https://arxiv.org/pdf/1904.08128",
            }
        ],
    }
    work.update(changes)
    return OpenAlexRecord.from_work(work)


def _pdf(tmp_path, title, doi):
    from tests.integration.test_pdf import _write_pdf

    path = tmp_path / "article.pdf"
    _write_pdf(
        path,
        texts=(
            title + "\n" + doi + "\nMethods\nSynthetic methods for segmentation.",
            "Results\nSynthetic results only.",
        ),
    )
    return path.read_bytes()


def _source(client):
    return OAFulltextSource(client, resolve=_public_resolve)


def test_candidate_order_ignores_domain_oa_flag_and_license():
    from clinical_agent.integrations.oa_fulltext import fulltext_candidates

    selected = _nnunet(
        content_urls={
            "grobid_xml": "https://content.openalex.org/works/W3014974815.grobid-xml",
            "pdf": "https://publisher.example/article.pdf",
        },
        best_oa_location={
            "pdf_url": "https://arxiv.org/pdf/1904.08128",
            "license": None,
            "is_oa": False,
        },
        locations=[
            {
                "pdf_url": "https://arxiv.org/pdf/1904.08128",
                "is_oa": False,
                "license": None,
            },
            {
                "pdf_url": "https://institution.example/file.pdf",
                "is_oa": False,
                "license": "all-rights-reserved",
            },
            {"landing_page_url": "https://example.org/abs", "pdf_url": None},
        ],
    )
    assert [item[0] for item in fulltext_candidates(selected)] == [
        "https://content.openalex.org/works/W3014974815.grobid-xml",
        "https://publisher.example/article.pdf",
        "https://arxiv.org/pdf/1904.08128",
        "https://institution.example/file.pdf",
    ]


def test_null_license_and_closed_flag_still_download(tmp_path):
    body = _pdf(tmp_path, _nnunet().title, _nnunet().doi)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})

    selected = _nnunet(
        open_access={"is_oa": False, "license": None},
        best_oa_location=None,
        locations=[
            {
                "is_oa": False,
                "license": None,
                "pdf_url": "https://arxiv.org/pdf/1904.08128",
            }
        ],
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = _source(client).fetch_record(selected, monotonic() + 10, [0])
    assert seen == ["https://arxiv.org/pdf/1904.08128"]
    assert fetched.license_name == "unspecified" and fetched.persist is True
    assert fetched.units


def test_content_url_failure_falls_back_to_location_pdf(tmp_path):
    body = _pdf(tmp_path, _nnunet().title, _nnunet().doi)
    seen = []
    official = "https://content.openalex.org/works/W3014974815.pdf"

    def handler(request):
        seen.append(str(request.url))
        if str(request.url).startswith(official):
            return httpx.Response(404)
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})

    selected = _nnunet(
        has_content={"pdf": True, "grobid_xml": False},
        content_urls={"pdf": official},
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = _source(client).fetch_record(selected, monotonic() + 10, [0])
    assert seen == [official, "https://arxiv.org/pdf/1904.08128"]
    assert fetched.source_url == "https://arxiv.org/pdf/1904.08128"


def test_external_pdf_is_parsed_and_indexed(tmp_path):
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import record_hit
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
    from tests.unit.test_fulltext_rag import Embedder

    body = _pdf(tmp_path, _nnunet().title, _nnunet().doi)
    selected = _nnunet()

    def handler(request):
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})

    class Store:
        payload = None

        def load(self, key, signature):
            return self.payload

        def reuse_content(self, key, signature, digest):
            return False

        def publish(self, key, signature, payload, vectors):
            self.payload = payload

        def search(self, key, vector, limit):
            return self.payload["passages"][:limit]

    hit = record_hit(selected, datetime.now(UTC))
    retrieval = RetrievalResult(
        scope="online",
        options=RetrievalOptions(),
        embedding_info=None,
        hits=[hit],
        search_provenance={
            "endpoint": "https://api.openalex.org/works",
            "query_sent": "nnU-Net",
            "fetched_at": datetime.now(UTC),
            "date_from": None,
            "date_to": None,
        },
    )
    store = Store()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        service = FulltextService(_source(client), store, Embedder())
        enriched = service.enrich("methods", retrieval, deadline=monotonic() + 30)
    assert store.payload is not None
    assert enriched.hits[0].fulltext
    assert enriched.hits[0].fulltext[0].license == "unspecified"
    assert selected.abstract not in enriched.hits[0].fulltext[0].text
    assert any(item.endswith("fulltext_available") for item in enriched.warnings)


def test_first_url_failure_tries_the_next(tmp_path):
    body = _pdf(tmp_path, _nnunet().title, _nnunet().doi)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if "publisher.example" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf"})

    selected = _nnunet(
        best_oa_location={
            "is_oa": False,
            "license": None,
            "pdf_url": "https://publisher.example/paywalled.pdf",
        },
        locations=[
            {
                "is_oa": False,
                "license": None,
                "pdf_url": "https://arxiv.org/pdf/1904.08128",
            }
        ],
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = _source(client).fetch_record(selected, monotonic() + 10, [0])
    assert seen[0].startswith("https://publisher.example/")
    assert seen[1] == "https://arxiv.org/pdf/1904.08128"
    assert fetched.units


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (
            httpx.Response(
                200, content=b"<html>login</html>", headers={"content-type": "text/html"}
            ),
            "fulltext_invalid_file",
        ),
        (
            httpx.Response(
                200, content=b"%PDF-1.4 broken", headers={"content-type": "application/pdf"}
            ),
            "fulltext_parse_failed",
        ),
        (httpx.Response(403), "fulltext_auth_failed"),
        (httpx.Response(404), "fulltext_download_failed"),
    ],
)
def test_bad_download_reasons_stay_distinct(response, code):
    selected = _nnunet()
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises(ValueError, match=code):
            _source(client).fetch_record(selected, monotonic() + 10, [0])


def test_identity_mismatch_and_ssrf(tmp_path):
    wrong = _pdf(tmp_path, "A different paper about unrelated laboratory assays", "10.1234/other")
    selected = _nnunet()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=wrong, headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="fulltext_identity_mismatch"):
            _source(client).fetch_record(selected, monotonic() + 10, [0])
    called = []

    def handler(request):
        called.append(str(request.url))
        return httpx.Response(200, content=b"%PDF-")

    private = _nnunet(
        best_oa_location={
            "pdf_url": "https://127.0.0.1/secret.pdf",
            "is_oa": True,
            "license": None,
        },
        locations=[],
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="fulltext_unsafe_url"):
            _source(client).fetch_record(private, monotonic() + 5, [0])
    assert called == []


def test_embedding_failure_is_not_a_license_error():
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import record_hit
    from clinical_agent.domain.fulltext import FulltextUnit
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
    from tests.unit.test_fulltext_rag import Embedder

    class Source:
        def fetch_record(self, value, deadline, count):
            count[0] += 1
            return (
                "unspecified",
                "https://arxiv.org/pdf/1904.08128",
                b"synthetic",
                [FulltextUnit(section="Methods", text="Synthetic method evidence.", start=0)],
            )

    class Store:
        def load(self, key, signature):
            return None

        def reuse_content(self, *args):
            return False

        def publish(self, *args):
            raise AssertionError("failed embeddings are not stored")

        def search(self, *args):
            raise AssertionError("failed embeddings are not searched")

    class Broken(Embedder):
        def embed_passages(self, texts, *, deadline):
            raise ValueError("embedding_failed")

    selected = _nnunet()
    retrieval = RetrievalResult(
        scope="online",
        options=RetrievalOptions(),
        embedding_info=None,
        hits=[record_hit(selected, datetime.now(UTC))],
        search_provenance={
            "endpoint": "https://api.openalex.org/works",
            "query_sent": "nnU-Net",
            "fetched_at": datetime.now(UTC),
            "date_from": None,
            "date_to": None,
        },
    )
    enriched = FulltextService(Source(), Store(), Broken()).enrich(
        "methods", retrieval, deadline=monotonic() + 20
    )
    assert enriched.hits[0].fulltext == []
    assert any("fulltext_embedding_failed" in item for item in enriched.warnings)
    from clinical_agent.channels.feishu.sender import _fulltext_reason

    assert "许可" not in _fulltext_reason("fulltext_no_fulltext_url")
    assert "许可不允许" not in _fulltext_reason("fulltext_auth_failed")


def test_second_paper_is_still_fetched_after_the_first_succeeds():
    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.application.openalex import record_hit
    from clinical_agent.domain.fulltext import FulltextUnit
    from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
    from tests.unit.test_fulltext_rag import Embedder

    medsam = _nnunet(
        id="https://openalex.org/W4389469943",
        title="Segment anything in medical images",
        doi="https://doi.org/10.1038/s41467-024-44824-z",
    )
    nnunet = _nnunet()
    fetched = []

    class Source:
        def fetch_record(self, value, deadline, count):
            fetched.append(value.openalex_id)
            count[0] += 1
            return (
                "unspecified",
                "https://arxiv.org/pdf/1904.08128",
                value.openalex_id.encode(),
                [FulltextUnit(section="Methods", text="Synthetic method evidence.", start=0)],
            )

    class Store:
        payloads = {}

        def load(self, key, signature):
            return self.payloads.get(key)

        def reuse_content(self, *args):
            return False

        def publish(self, key, signature, payload, vectors):
            self.payloads[key] = payload

        def search(self, key, vector, limit):
            return self.payloads[key]["passages"][:limit]

    retrieval = RetrievalResult(
        scope="online",
        options=RetrievalOptions(top_k=2),
        embedding_info=None,
        hits=[
            record_hit(medsam, datetime.now(UTC)),
            record_hit(nnunet, datetime.now(UTC)).model_copy(update={"rank": 2, "score": 0.5}),
        ],
        search_provenance={
            "endpoint": "https://api.openalex.org/works",
            "query_sent": "MedSAM nnU-Net",
            "fetched_at": datetime.now(UTC),
            "date_from": None,
            "date_to": None,
        },
    )
    enriched = FulltextService(Source(), Store(), Embedder()).enrich(
        "MedSAM与nnU-Net有什么区别？", retrieval, deadline=monotonic() + 30
    )
    assert fetched == [medsam.openalex_id, nnunet.openalex_id]
    assert all(hit.fulltext for hit in enriched.hits)
    assert enriched.hits[0].chunk.text not in enriched.hits[0].fulltext[0].text
