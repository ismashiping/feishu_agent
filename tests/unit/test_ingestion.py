"""Application orchestration/provenance boundaries with explicit infrastructure doubles."""

import copy
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError


def request():
    from clinical_agent.domain.ingestion import ImportRequest

    return ImportRequest(
        source_type="pdf",
        path=Path("synthetic.pdf"),
        allowed_root=Path("."),
        ingestion_time=datetime(2026, 10, 27, tzinfo=UTC),
    )


@pytest.mark.parametrize("value", [None, 0, "2026-10-27", datetime(2026, 10, 27)])
def test_request_requires_explicit_aware_time(value):
    from clinical_agent.domain.ingestion import ImportRequest

    with pytest.raises(ValidationError):
        ImportRequest(
            source_type="pdf", path=Path("a"), allowed_root=Path("."), ingestion_time=value
        )


def test_stable_ids_include_identity_and_processing_config(fake_embedder):
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.ingestion import chunk_id_for, document_id_for

    identity = document_id_for("pdf", "a" * 64)
    assert identity == document_id_for("pdf", "a" * 64)
    assert identity != document_id_for("pdf", "b" * 64)
    assert identity != document_id_for("pubmed", "123")
    profile, policy = fake_embedder.tokenizer_profile, ChunkingPolicy()
    chunk = chunk_id_for(identity, profile, policy, 1)
    assert chunk == chunk_id_for(identity, profile, policy, 1)
    assert chunk != chunk_id_for(identity, profile, ChunkingPolicy(max_tokens=256), 1)
    assert chunk != chunk_id_for(identity, profile, policy, 2)


@pytest.mark.parametrize("case", ["missing", "order", "text", "source", "model", "overlap"])
def test_prepared_rejects_broken_binding_or_coverage(prepared_factory, case):
    from clinical_agent.domain.ingestion import PreparedIngestion

    value = prepared_factory(max_tokens=13).model_dump()
    if case == "missing":
        value["embedded"].pop()
        value["chunking"]["chunks"].pop()
    elif case == "order":
        value["embedded"].reverse()
    elif case == "text":
        value["embedded"][0]["evidence"]["text"] = "wrong"
    elif case == "source":
        value["embedded"][0]["evidence"]["document_id"] = uuid4()
    elif case == "model":
        value["embedded"][0]["evidence"]["embedding_info"]["model_revision"] = "other"
    else:
        duplicate = copy.deepcopy(value["chunking"]["chunks"][0])
        duplicate["evidence"]["chunk_id"] = uuid4()
        encoded = copy.deepcopy(value["embedded"][0])
        encoded["evidence"]["chunk_id"] = duplicate["evidence"]["chunk_id"]
        value["chunking"]["chunks"].insert(1, duplicate)
        value["embedded"].insert(1, encoded)
    with pytest.raises(ValidationError):
        PreparedIngestion.model_validate(value)


@pytest.mark.parametrize("kind", ["pdf", "pubmed"])
def test_prepared_roundtrip_preserves_unicode_provenance(source_factory, prepared_factory, kind):
    from clinical_agent.domain.ingestion import PreparedIngestion

    source = source_factory(kind=kind)
    value = prepared_factory(source)
    assert PreparedIngestion.model_validate_json(value.model_dump_json()) == value
    for item in value.embedded:
        source.parsed.validate_chunk(item.evidence)


def test_equivalence_ignores_ingestion_identity_time_and_path(prepared_factory):
    from clinical_agent.domain.ingestion import equivalent_content

    one = prepared_factory()
    two = copy.deepcopy(one)
    doc = two.source.parsed.document
    doc.source_uri = "file:///another.pdf"
    doc.ingestion_time = datetime(2026, 10, 28, tzinfo=UTC)
    for chunk in two.chunking.chunks:
        chunk.evidence.source_metadata.source_uri = doc.source_uri
    for chunk in two.embedded:
        chunk.evidence.source_metadata.source_uri = doc.source_uri
    assert equivalent_content(one, two)
    two.source.parsed.document.title = "Manual correction"
    assert not equivalent_content(one, two)


def service(sources, embedder, *, save=None, limits=None, clock=None):
    from clinical_agent.application.ingestion import IngestionService
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.ingestion import ParsedBatch, ParsedEntry, StoreResult

    captured = []

    class Reader:
        def read(self, request):
            return ParsedBatch(
                entries=[
                    ParsedEntry(index=i, source=source, error_code=None)
                    for i, source in enumerate(sources, 1)
                ]
            )

    class Store:
        def save(self, prepared):
            captured.append(prepared)
            return (
                save(prepared)
                if save
                else StoreResult(
                    status="imported",
                    document_id=prepared.source.parsed.document.document_id,
                    chunk_count=len(prepared.embedded),
                )
            )

    kwargs = {}
    if limits is not None:
        kwargs["limits"] = limits
    if clock is not None:
        kwargs["clock"] = clock
    return IngestionService(
        reader=Reader(),
        embedder=embedder,
        store=Store(),
        policy=ChunkingPolicy(max_tokens=64),
        **kwargs,
    ), captured


def test_application_encodes_before_saving_and_keeps_input(source_factory, fake_embedder):
    source = source_factory()
    original = source.model_dump_json()
    app, captured = service([source], fake_embedder)
    result = app.ingest(request())
    assert result.error_code is None and result.entries[0].status == "imported"
    assert fake_embedder.calls == len(captured) == 1
    assert source.model_dump_json() == original
    assert "file:///" not in result.model_dump_json()


def test_bad_embedding_does_not_open_store(source_factory, fake_embedder):
    fake_embedder.embed_chunks = lambda _: []
    app, captured = service([source_factory()], fake_embedder)
    result = app.ingest(request())
    assert result.entries[0].error_code == "embedding_failed" and not captured


def test_external_exception_is_sanitized_and_other_documents_continue(
    source_factory, fake_embedder
):
    def save(prepared):
        from clinical_agent.domain.ingestion import StoreResult

        if prepared.source.parsed.document.title == "Fail":
            raise RuntimeError("secret-manuscript database failure")
        return StoreResult(status="already_present", document_id=UUID(int=2), chunk_count=1)

    app, _ = service(
        [source_factory(title="Fail"), source_factory(title="Success")], fake_embedder, save=save
    )
    result = app.ingest(request())
    assert [entry.status for entry in result.entries] == ["failed", "already_present"]
    assert result.entries[0].error_code == "storage_failed"
    assert "secret-manuscript" not in result.model_dump_json()


def test_batch_limit_has_no_embedding_or_store_side_effect(source_factory, fake_embedder):
    from clinical_agent.domain.ingestion import IngestionLimits

    app, captured = service(
        [source_factory(), source_factory()], fake_embedder, limits=IngestionLimits(max_documents=1)
    )
    result = app.ingest(request())
    assert result.error_code == "batch_limit" and not result.entries
    assert fake_embedder.calls == 0 and not captured


def test_deadline_after_embedding_prevents_write(source_factory, fake_embedder):
    now = [0.0]
    original = fake_embedder.embed_chunks

    def slow(source):
        now[0] += 121.0
        return original(source)

    fake_embedder.embed_chunks = slow
    app, captured = service([source_factory()], fake_embedder, clock=lambda: now[0])
    result = app.ingest(request())
    assert result.entries[0].error_code == "ingestion_timeout" and not captured


def test_entry_state_cannot_claim_success_without_document():
    from clinical_agent.domain.ingestion import IngestionResult

    with pytest.raises(ValidationError):
        IngestionResult(
            index=1, status="imported", document_id=None, chunk_count=0, error_code=None
        )


@pytest.mark.parametrize("kind", ["parsed", "entry", "batch"])
def test_error_codes_are_closed_and_cannot_carry_raw_details(kind):
    from clinical_agent.domain.ingestion import BatchIngestionResult, IngestionResult, ParsedEntry

    with pytest.raises(ValidationError):
        if kind == "parsed":
            ParsedEntry(index=1, source=None, error_code="secret-manuscript")
        elif kind == "entry":
            IngestionResult(
                index=1,
                status="failed",
                document_id=None,
                chunk_count=0,
                error_code="secret-manuscript",
            )
        else:
            BatchIngestionResult(entries=[], error_code="secret-manuscript")


def test_completed_commit_is_reported_even_if_deadline_expires_after_it(
    source_factory, fake_embedder
):
    from clinical_agent.domain.ingestion import StoreResult

    now = [0.0]

    def save(prepared):
        now[0] += 121.0
        return StoreResult(
            status="imported",
            document_id=prepared.source.parsed.document.document_id,
            chunk_count=len(prepared.embedded),
        )

    app, captured = service(
        [source_factory(), source_factory()], fake_embedder, save=save, clock=lambda: now[0]
    )
    result = app.ingest(request())
    assert result.entries[0].status == "imported"
    assert result.entries[1].error_code == "ingestion_timeout" and len(captured) == 1


def test_reader_exception_cannot_become_a_public_error_code(fake_embedder):
    from clinical_agent.application.ingestion import IngestionService

    class Broken:
        def read(self, request):
            raise RuntimeError("secret-manuscript")

        def save(self, prepared):
            raise AssertionError("must not store")

    result = IngestionService(reader=Broken(), embedder=fake_embedder, store=Broken()).ingest(
        request()
    )
    assert (
        result.error_code == "source_failed" and "secret-manuscript" not in result.model_dump_json()
    )
