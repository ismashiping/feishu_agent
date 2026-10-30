from xml.etree.ElementTree import ParseError

import pytest

from clinical_agent.adapters.pmc_fulltext import parse_bioc

XML = b"""<collection>
<document><id>PMC123</id><passage><infon key="section_type">METHODS</infon>
<offset>42</offset><text>We used k-means clustering.</text></passage>
</document></collection>"""


def test_sections_and_positions():
    passages = parse_bioc(XML, "PMC123")
    assert passages == [("METHODS", 42, "We used k-means clustering.")]


def test_identity_mismatch():
    with pytest.raises(ValueError):
        parse_bioc(XML, "PMC456")


def test_malformed():
    with pytest.raises(ParseError):
        parse_bioc(b"<broken", "PMC123")


class MemoryStore:
    def __init__(self):
        self.payload = None
        self.published = 0

    def load(self, pmid, signature):
        return self.payload

    def publish(self, pmid, signature, payload, vectors):
        self.payload = payload
        self.published += 1

    def search(self, pmid, vector, limit):
        return self.payload["passages"][:limit]


class Embedder:
    calls = 0

    def count_tokens(self, text):
        return max(1, len(text.split()))

    def embed_passages(self, texts, *, deadline):
        self.calls += 1
        return [[1.0] for _ in texts]

    def embed_query(self, question):
        from types import SimpleNamespace

        return SimpleNamespace(vector=[1.0])


class Source:
    calls = 0

    def fetch(self, pmid, deadline):
        self.calls += 1
        return (
            "PMC123",
            "CC BY",
            "https://example.org",
            XML,
            [
                ("METHODS", 42, "We used k-means clustering."),
                ("RESULTS", 100, "The method found three groups."),
            ],
        )


def test_ingest_reuse_and_sections(source_factory, prepared_factory):
    from time import monotonic

    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_research import result

    source, store, embedder = Source(), MemoryStore(), Embedder()
    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    service = FulltextService(source, store, embedder)
    enriched = service.enrich("methods?", retrieval, deadline=monotonic() + 20)
    assert [p.section for p in enriched.hits[0].fulltext] == ["METHODS", "RESULTS"]
    assert enriched.hits[0].fulltext[0].start == 42
    assert not retrieval.hits[0].fulltext
    service.enrich("results?", retrieval, deadline=monotonic() + 20)
    assert source.calls == embedder.calls == store.published == 1


def test_failure_preserves_abstract(source_factory, prepared_factory):
    from time import monotonic

    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_research import result

    class Broken(Source):
        def fetch(self, pmid, deadline):
            raise ValueError("fulltext_license_not_allowed")

    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(Broken(), MemoryStore(), Embedder()).enrich(
        "question", retrieval, deadline=monotonic() + 20
    )
    assert enriched.hits == retrieval.hits
    assert "license_not_allowed" in enriched.warnings[-1]


def test_real_source_fixture():
    from pathlib import Path

    raw = Path("tests/fixtures/pmc1790863.bioc.xml").read_bytes()
    passages = parse_bioc(raw, "PMC1790863")
    assert 0 < len(passages) < 120
    assert any("METHOD" in section for section, _, _ in passages)


def test_deadline_makes_no_download(source_factory, prepared_factory):
    from time import monotonic

    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_research import result

    source = Source()
    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(source, MemoryStore(), Embedder()).enrich(
        "question", retrieval, deadline=monotonic() - 1
    )
    assert source.calls == 0
    assert enriched.hits == retrieval.hits
    assert enriched.warnings[-1].endswith("fulltext_budget")


def test_fulltext_citation_roundtrip(source_factory, prepared_factory):
    from datetime import UTC, datetime
    from time import monotonic
    from uuid import uuid4

    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.domain.citations import build_answer, parse_draft
    from clinical_agent.domain.research import QuestionRequest
    from tests.unit.test_research import draft, result

    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(Source(), MemoryStore(), Embedder()).enrich(
        "methods?", retrieval, deadline=monotonic() + 20
    )
    request = QuestionRequest(request_id=uuid4(), question="methods?")
    parsed = parse_draft(draft(enriched.hits[0].chunk.chunk_id), max_bytes=32000)
    answer = build_answer(request, enriched, parsed, generated_at=datetime.now(UTC))
    assert answer.sources[0].evidence[0].fulltext[0].section == "METHODS"
    assert answer.sources[0].evidence[0].fulltext[0].pmid == answer.sources[0].pmid
    assert answer.sources[0].content_scope == "abstract"


def test_splitter_adapts_empty_input_to_strict_token_counter(source_factory, prepared_factory):
    from time import monotonic

    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_research import result

    class StrictEmbedder(Embedder):
        def count_tokens(self, value):
            if not value.strip():
                raise ValueError("empty input is forbidden by the E5 interface")
            return super().count_tokens(value)

    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(Source(), MemoryStore(), StrictEmbedder()).enrich(
        "methods?", retrieval, deadline=monotonic() + 20
    )
    assert enriched.hits[0].fulltext


def test_direct_fulltext_id_passes_trusted_gate(source_factory, prepared_factory):
    from datetime import UTC, datetime
    from time import monotonic
    from uuid import uuid4

    from clinical_agent.application.fulltext import FulltextService
    from clinical_agent.domain.citations import build_answer, parse_draft
    from clinical_agent.domain.research import QuestionRequest
    from tests.unit.test_research import draft, result

    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(Source(), MemoryStore(), Embedder()).enrich(
        "methods?", retrieval, deadline=monotonic() + 20
    )
    passage = enriched.hits[0].fulltext[0]
    parsed = parse_draft(draft(passage.chunk_id), max_bytes=32000)
    answer = build_answer(
        QuestionRequest(request_id=uuid4(), question="methods?"),
        enriched,
        parsed,
        generated_at=datetime.now(UTC),
    )
    evidence = answer.sources[0].evidence[0]
    assert evidence.chunk_id == passage.chunk_id
    assert evidence.text == passage.text
    assert evidence.location.kind == "fulltext"
    assert evidence.location.start == passage.start


def test_headings_become_locators_instead_of_standalone_evidence():
    raw = b"""<collection><document><id>PMC123</id><passage>
<infon key="section_type">METHODS</infon><infon key="type">title_2</infon>
<offset>0</offset><text>Clustering</text></passage>
<passage><infon key="section_type">METHODS</infon>
<infon key="type">paragraph</infon>
<offset>20</offset><text>We used k-means.</text></passage></document></collection>"""
    assert parse_bioc(raw, "PMC123") == [("METHODS / Clustering", 20, "We used k-means.")]
