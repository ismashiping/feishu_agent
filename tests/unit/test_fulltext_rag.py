"""Helpers shared with OpenAlex fulltext tests. PubMed rows are not enriched."""


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


def test_pubmed_hits_are_not_downloaded(source_factory, prepared_factory):
    from time import monotonic

    from clinical_agent.application.fulltext import FulltextService
    from tests.unit.test_research import result

    class Source:
        def fetch_record(self, record, deadline, count):
            raise AssertionError("stored PubMed rows are not downloaded")

    class Store:
        def load(self, key, signature):
            raise AssertionError("stored PubMed rows are not read from the fulltext cache")

    retrieval = result(prepared_factory(source_factory(kind="pubmed")))
    enriched = FulltextService(Source(), Store(), Embedder()).enrich(
        "methods?", retrieval, deadline=monotonic() + 20
    )
    assert enriched.hits[0].fulltext == []
