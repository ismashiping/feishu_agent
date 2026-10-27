"""Real XML parser to source chunking; tokenizer remains an explicit test double."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

pytestmark = pytest.mark.integration


def test_real_pdf_keeps_blank_page_number_and_exact_slices(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    from clinical_agent.adapters.pdf import parse_pdf
    from clinical_agent.domain.chunking import ChunkingPolicy, TokenizerProfile, chunk_source

    path = tmp_path / "source.pdf"
    with PdfWriter() as writer:
        for text in ("AlphaBeta", "", "Gamma"):
            page = writer.add_blank_page(width=300, height=300)
            if text:
                font = DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
                page[NameObject("/Resources")] = DictionaryObject(
                    {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
                )
                stream = DecodedStreamObject()
                stream.set_data(b"BT /F1 12 Tf 20 250 Td (" + text.encode("ascii") + b") Tj ET")
                page.replace_contents(stream)
        writer.write(path)
    parsed = parse_pdf(
        path,
        allowed_root=tmp_path,
        document_id=UUID(int=1),
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
    )
    result = chunk_source(
        parsed,
        tokenizer=lambda text: len(text) + 2,
        profile=TokenizerProfile(
            model_id="fixture",
            model_revision="fixed-1",
            tokenizer_revision="fixed-1",
            document_prefix="p: ",
            model_max_tokens=32,
        ),
        policy=ChunkingPolicy(max_tokens=9),
        chunk_id_factory=lambda index: UUID(int=index + 100),
    )
    assert {item.evidence.location.page for item in result.chunks} == {1, 3}
    assert [item.evidence.text for item in result.chunks] == ["Alph", "aBet", "a", "Gamm", "a"]
    for item in result.chunks:
        parsed.validate_chunk(item.evidence)
        assert item.evidence.source_metadata.content_scope == "extracted_text"


def test_real_xml_sections_keep_global_offsets_and_metadata(tmp_path):
    from clinical_agent.adapters.pubmed_xml import parse_pubmed_xml
    from clinical_agent.domain.chunking import ChunkingPolicy, TokenizerProfile, chunk_source

    path = tmp_path / "synthetic.xml"
    path.write_text(
        """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
    <Article><ArticleTitle>Fixture</ArticleTitle><Abstract>
    <AbstractText Label="BACKGROUND">中文α🙂</AbstractText>
    <AbstractText Label="RESULTS">Result text long enough.</AbstractText>
    </Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>""",
        encoding="utf-8",
    )
    batch = parse_pubmed_xml(
        path,
        allowed_root=tmp_path,
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
        document_id_factory=lambda _: UUID(int=1),
    )
    parsed = batch.entries[0].article
    assert parsed is not None
    result = chunk_source(
        parsed,
        tokenizer=lambda text: len(text) + 2,
        profile=TokenizerProfile(
            model_id="fixture",
            model_revision="fixed-1",
            tokenizer_revision="fixed-1",
            document_prefix="p: ",
            model_max_tokens=32,
        ),
        policy=ChunkingPolicy(max_tokens=9),
        chunk_id_factory=lambda index: UUID(int=index + 100),
    )
    assert result.chunks[0].evidence.text == "中文α🙂"
    assert result.chunks[1].evidence.location.start == 6
    assert {item.evidence.location.section for item in result.chunks} == {"BACKGROUND", "RESULTS"}
    for item in result.chunks:
        parsed.validate_chunk(item.evidence)
        assert item.evidence.source_metadata.content_scope == "abstract"
        assert item.evidence.source_metadata.content_hash == batch.source.content_hash
    assert parsed.document.evidence_chunks == []
