"""Actual source snapshots and parsers; no database or model required."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.integration


def read(reader, path, root, source_type="pdf"):
    from clinical_agent.domain.ingestion import ImportRequest

    return reader.read(
        ImportRequest(
            path=path,
            allowed_root=root,
            source_type=source_type,
            ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        )
    )


def test_real_pdf_snapshot_retains_original_filename_and_survives_source_removal(
    tmp_path, pdf_factory
):
    from clinical_agent.adapters.offline import OfflineReader

    original = pdf_factory(tmp_path / "Original title.pdf")
    snapshot_root = tmp_path / "snapshots"
    reader = OfflineReader(snapshot_root)
    result = read(reader, original, tmp_path)
    source = result.entries[0].source
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    original.rename(tmp_path / "moved.pdf")
    assert source.parsed.document.title == "Original title"
    assert source.parsed.document.title_origin == "filename"
    assert source.parsed.document.content_hash == digest
    assert (snapshot_root / f"{digest}.pdf").is_file()
    assert [u.page for u in source.parsed.source_units] == [1, 2, 3]
    assert not list(snapshot_root.glob(".ingest-*"))


def test_concurrent_snapshot_publication_is_atomic(tmp_path, pdf_factory):
    from clinical_agent.adapters.offline import OfflineReader

    original = pdf_factory(tmp_path / "source.pdf")
    reader = OfflineReader(tmp_path / "snapshots")
    with ThreadPoolExecutor(max_workers=2) as executor:
        batches = list(executor.map(lambda _: read(reader, original, tmp_path), range(2)))
    assert batches[0].entries[0].source == batches[1].entries[0].source
    assert len(list((tmp_path / "snapshots").glob("*.pdf"))) == 1
    assert not list((tmp_path / "snapshots").glob(".ingest-*"))


def test_existing_corrupt_snapshot_is_not_overwritten(tmp_path, pdf_factory):
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.domain.ingestion import IngestionError

    path = pdf_factory(tmp_path / "source.pdf")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    cache = tmp_path / "snapshots"
    cache.mkdir()
    target = cache / f"{digest}.pdf"
    target.write_bytes(b"corrupt")
    with pytest.raises(IngestionError, match="^source_invalid$"):
        read(OfflineReader(cache), path, tmp_path)
    assert target.read_bytes() == b"corrupt"


@pytest.mark.parametrize("case", ["outside", "size"])
def test_snapshot_source_limits(tmp_path, pdf_factory, case):
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.domain.ingestion import IngestionError

    original = pdf_factory(tmp_path / "source.pdf")
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    with pytest.raises(IngestionError, match="^source_invalid$"):
        read(
            OfflineReader(tmp_path / "cache", max_file_bytes=1 if case == "size" else 20_000_000),
            original,
            allowed if case == "outside" else tmp_path,
        )


def test_real_xml_mixed_parsed_and_rejected_entries(tmp_path):
    from clinical_agent.adapters.offline import OfflineReader

    xml = tmp_path / "source.xml"
    xml.write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
    <Article><ArticleTitle>Fixture</ArticleTitle><Abstract><AbstractText Label="RESULTS">
    中文 α🙂 evidence.</AbstractText></Abstract></Article></MedlineCitation></PubmedArticle>
    <PubmedArticle><MedlineCitation><PMID>456</PMID><Article>
    <ArticleTitle>No abstract</ArticleTitle>
    </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
    )
    batch = read(OfflineReader(tmp_path / "cache"), xml, tmp_path, "pubmed_xml")
    assert len(batch.entries) == 2
    assert batch.entries[0].source.parsed.document.pmid == "123"
    assert batch.entries[1].error_code == "pubmed_no_abstract"
    assert batch.entries[0].source.parser_name == "defusedxml"


def test_actual_xml_application_batch_limit_is_explicit(tmp_path, fake_embedder):
    from clinical_agent.adapters.offline import OfflineReader
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.domain.ingestion import ImportRequest

    records = "".join(
        f"""<PubmedArticle><MedlineCitation><PMID>{i}</PMID><Article>
    <ArticleTitle>Fixture</ArticleTitle><Abstract><AbstractText>Evidence.</AbstractText></Abstract>
    </Article></MedlineCitation></PubmedArticle>"""
        for i in range(1, 34)
    )
    path = tmp_path / "too-many.xml"
    path.write_text("<PubmedArticleSet>" + records + "</PubmedArticleSet>", encoding="utf-8")

    class Store:
        def save(self, prepared):
            raise AssertionError("Over-limit input must never reach storage")

    app = IngestionService(
        reader=OfflineReader(tmp_path / "cache"), embedder=fake_embedder, store=Store()
    )
    result = app.ingest(
        ImportRequest(
            path=path,
            allowed_root=tmp_path,
            source_type="pubmed_xml",
            ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        )
    )
    assert result.error_code == "batch_limit" and not result.entries
    assert fake_embedder.calls == 0
