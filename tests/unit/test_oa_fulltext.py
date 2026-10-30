"""OpenAlex OA engineering contracts; synthetic text is never medical evidence."""

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import monotonic

import httpx
import pytest

from clinical_agent.adapters.oa_fulltext import OAFulltextSource, parse_jats, safe_url
from clinical_agent.domain.openalex import OpenAlexRecord


def record():
    runs = json.loads(Path("docs/openalex-stage2/live-check.json").read_text(encoding="utf8"))
    return next(
        OpenAlexRecord.model_validate(r)
        for run in runs
        for r in run.get("provenance", {}).get("records", [])
        if r["doi"] == "10.1038/s41598-024-78917-y"
    )


def jats(doi="10.1038/s41598-024-78917-y"):
    title = record().title
    return f"""<article><front><article-meta><article-id pub-id-type="doi">{doi}</article-id>
<title-group><article-title>{title}</article-title></title-group>
<permissions><license xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="https://creativecommons.org/licenses/by/4.0/"/></permissions>
</article-meta></front><body><sec><title>Methods</title>
<p>Synthetic paragraph: we used a network.</p></sec>
<sec><title>Results</title>
<p>Synthetic result: this is not a scientific finding.</p></sec></body></article>""".encode()


def test_structured_identity_license_and_positions():
    units = parse_jats(jats(), record())
    assert units[0].section == "Methods"
    assert units[0].start == 0
    assert units[1].start == len(units[0].text) + 2
    with pytest.raises(ValueError, match="identity"):
        parse_jats(jats("10.1234/wrong"), record())
    with pytest.raises(ValueError, match="license"):
        parse_jats(jats().replace(b"licenses/by/4.0", b"licenses/by-nc/4.0"), record())


def test_jats_license_link_inside_license_paragraph():
    raw = jats().replace(
        b'<license xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="https://creativecommons.org/licenses/by/4.0/"/>',
        b'<license><license-p><ext-link xmlns:xlink="http://www.w3.org/1999/xlink" '
        b'xlink:href="https://creativecommons.org/licenses/by/4.0/">'
        b"CC BY</ext-link></license-p></license>",
    )
    assert parse_jats(raw, record())


def test_acquisition_requires_explicit_allowed_license():
    r = record()
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("no network expected"))
    ) as client:
        with pytest.raises(ValueError, match="license"):
            OAFulltextSource(client).fetch_record(r, monotonic() + 10, [0])


def test_download_budget_and_response_size():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * (10 * 1024 * 1024 + 1))
        )
    ) as client:
        source = OAFulltextSource(client)
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


def test_real_jats_fixture():
    root = Path("tests/fixtures/oa_fulltext")
    r = OpenAlexRecord.model_validate_json((root / "mri-record.json").read_text(encoding="utf8"))
    raw = (root / "mri-fulltext.xml").read_bytes()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf8"))
    assert sha256(raw).hexdigest() == manifest["sha256"]
    units = parse_jats(raw, r)
    assert any("method" in u.section.casefold() for u in units)
    assert any("result" in u.section.casefold() for u in units)


def test_nested_tables_do_not_turn_into_unlabeled_numbers():
    raw = jats().replace(
        b"we used a network.",
        b"we used a network.<table-wrap><table><tr>"
        b"<td>123</td><td>456</td></tr></table></table-wrap>",
    )
    assert "123456" not in parse_jats(raw, record())[0].text


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
    from clinical_agent.adapters.oa_fulltext import parse_oa_pdf

    root = Path("tests/fixtures/oa_fulltext")
    r = OpenAlexRecord.model_validate_json((root / "plos-record.json").read_text(encoding="utf8"))
    raw = (root / "plos-fulltext.pdf").read_bytes()
    manifest = json.loads((root / "plos-pdf-manifest.json").read_text(encoding="utf8"))
    assert sha256(raw).hexdigest() == manifest["sha256"]
    units = parse_oa_pdf(raw, r)
    assert max(u.page for u in units) == 15


def test_pdf_pages_sections_headers_and_identity(tmp_path):
    from clinical_agent.adapters.oa_fulltext import parse_oa_pdf
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
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest
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
                jats(),
                parse_jats(jats(), value),
            )

    source, store, embedder = Source(), Store(), Embedder()
    service = FulltextService(None, None, embedder, oa_source=source, oa_store=store)
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
    assert sha256(jats()).hexdigest() == p.content_hash
    from feishu.sender import render_answer

    rendered = render_answer(answer)
    assert "全文段落" in rendered
    assert "摘要（未阅读全文）" not in rendered
    assert "部分来源仅包含摘要" not in answer.limitations
    abstract_only = build_answer(
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
    assert abstract_only.sources[0].evidence[0].fulltext == []
    enriched.hits[0].fulltext[0].paper_key = "doi:10.1234/wrong"
    with pytest.raises(ValueError):
        RetrievalResult.model_validate(enriched)
