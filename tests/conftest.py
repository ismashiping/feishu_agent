"""Synthetic ingestion fixture factories, with no model or database initialization."""

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest


@pytest.fixture
def source_factory():
    def make(text="Alpha 中文 α🙂.", kind="pdf", pmid="1234567890", **overrides):
        from clinical_agent.domain.ingestion import ParsedSource
        from clinical_agent.domain.models import LiteratureDocument, ParsedPdf, ParsedPubmedArticle

        digest = hashlib.sha256(text.encode()).hexdigest()
        data = dict(
            document_id=uuid4(),
            title="Synthetic",
            title_origin="document_metadata",
            authors=[],
            publication_date={"precision": "unknown"},
            journal=None,
            doi=None,
            pmid=None,
            abstract=None,
            text=text,
            source_type=kind,
            source_url=None,
            source_uri=f"file:///snapshots/{digest}.pdf",
            content_hash=digest,
            content_scope="extracted_text",
            ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
            evidence_chunks=[],
        )
        if kind == "pubmed":
            data.update(
                title_origin="pubmed_metadata",
                pmid=pmid,
                abstract=text,
                text=None,
                content_scope="abstract",
                source_uri=f"file:///snapshots/{digest}.xml",
            )
        data.update(overrides)
        document = LiteratureDocument.model_validate(data)
        if kind == "pdf":
            parsed = ParsedPdf(
                document=document,
                source_units=[{"page": 1, "text": text}],
                page_count=1,
                parser_version="synthetic-1",
            )
        else:
            parsed = ParsedPubmedArticle(
                document=document,
                source_units=[
                    {"index": 1, "text": text, "start": 0, "end": len(text), "label": "RESULTS"}
                ],
            )
        return ParsedSource(
            parsed=parsed,
            parser_name="pypdf" if kind == "pdf" else "defusedxml",
            parser_version="synthetic-1",
        )

    return make


@pytest.fixture
def fake_embedder():
    from clinical_agent.domain.chunking import TokenizerProfile
    from clinical_agent.domain.embedding import EmbeddedChunk
    from clinical_agent.domain.models import EmbeddingInfo, EvidenceChunk

    class Fake:
        tokenizer_profile = TokenizerProfile(
            model_id="intfloat/multilingual-e5-base",
            model_revision="d128750597153bb5987e10b1c3493a34e5a4502a",
            tokenizer_revision="d128750597153bb5987e10b1c3493a34e5a4502a",
            document_prefix="passage: ",
            model_max_tokens=512,
        )

        def __init__(self):
            self.calls = 0

        def count_tokens(self, text):
            return len(text) + 2

        def embed_chunks(self, source):
            self.calls += 1
            info = EmbeddingInfo(
                **self.tokenizer_profile.model_dump(
                    exclude={"document_prefix", "model_max_tokens"}
                ),
                dimension=768,
                normalized=True,
                chunking_version=source.policy.chunking_version,
            )
            return [
                EmbeddedChunk(
                    evidence=EvidenceChunk.model_validate(
                        {**item.evidence.model_dump(), "embedding_info": info}
                    ),
                    vector=[1.0] + [0.0] * 767,
                )
                for item in source.chunks
            ]

    return Fake()


@pytest.fixture
def prepared_factory(source_factory, fake_embedder):
    def make(source=None, **policy_values):
        from clinical_agent.domain.chunking import ChunkingPolicy, chunk_source
        from clinical_agent.domain.ingestion import PreparedIngestion, chunk_id_for

        source = source if source is not None else source_factory()
        policy = ChunkingPolicy(**{"max_tokens": 64, **policy_values})
        profile = fake_embedder.tokenizer_profile
        chunking = chunk_source(
            source.parsed,
            tokenizer=fake_embedder.count_tokens,
            profile=profile,
            policy=policy,
            chunk_id_factory=lambda i: chunk_id_for(
                source.parsed.document.document_id, profile, policy, i
            ),
        )
        return PreparedIngestion(
            source=source, chunking=chunking, embedded=fake_embedder.embed_chunks(chunking)
        )

    return make


@pytest.fixture
def pdf_factory():
    def make(path, texts=("Alpha evidence", "", "Second page")):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        with PdfWriter() as writer:
            for text in texts:
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
        return path

    return make
