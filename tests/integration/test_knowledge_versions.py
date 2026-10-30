import pytest

from tests.integration.test_postgres import engine as engine

pytestmark = [pytest.mark.integration, pytest.mark.database]


def test_versions_publish_history_and_dry_run(engine, source_factory, prepared_factory):
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.domain.ingestion import document_id_for

    original = prepared_factory(
        source_factory(
            text="Original cohort evidence.",
            kind="pubmed",
            pmid="98765001",
            document_id=document_id_for("pubmed", "98765001"),
        )
    )
    store = VersionedPostgresStore(engine)
    assert store.save(original).status == "imported"
    old_id = store.version_id(original)
    update = prepared_factory(
        source_factory(
            text="Updated cohort evidence.",
            kind="pubmed",
            pmid="98765001",
            document_id=original.source.parsed.document.document_id,
        )
    )
    assert store.publish(update, dry_run=True).status == "updated"
    assert (
        PostgresStore(engine)
        .load(original.source.parsed.document.document_id)
        .source.parsed.document.abstract
        == "Original cohort evidence."
    )
    assert store.save(update).status == "updated"
    assert store.save(update).status == "already_present"
    assert store.load_version(old_id).source.parsed.document.abstract == "Original cohort evidence."
    assert (
        store.load_version(old_id).embedded[0].evidence.chunk_id
        != PostgresStore(engine)
        .load(original.source.parsed.document.document_id)
        .embedded[0]
        .evidence.chunk_id
    )


def test_version_metadata_and_concurrency(engine, source_factory, prepared_factory):
    from concurrent.futures import ThreadPoolExecutor

    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.domain.ingestion import document_id_for

    store = VersionedPostgresStore(engine)
    one = prepared_factory(
        source_factory(
            text="Stable abstract.",
            kind="pubmed",
            pmid="98765002",
            document_id=document_id_for("pubmed", "98765002"),
        )
    )
    store.save(one)
    two = one.model_copy(deep=True)
    two.source.parsed.document.title = "Corrected metadata"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: store.save(two).status, range(2)))
    assert sorted(outcomes) == ["already_present", "metadata_updated"]
    assert (
        store.load_version(store.version_id(one)).source.parsed.document.title
        != "Corrected metadata"
    )


def test_version_failure_keeps_old_projection(engine, source_factory, prepared_factory):
    from sqlalchemy import event

    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.domain.ingestion import document_id_for

    store = VersionedPostgresStore(engine)
    one = prepared_factory(
        source_factory(
            text="Old evidence.",
            kind="pubmed",
            pmid="98765003",
            document_id=document_id_for("pubmed", "98765003"),
        )
    )
    store.save(one)
    two = prepared_factory(
        source_factory(
            text="Replacement evidence.",
            kind="pubmed",
            pmid="98765003",
            document_id=one.source.parsed.document.document_id,
        )
    )

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO chunks"):
            raise RuntimeError("Injected failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError):
            store.save(two)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert (
        store.load(one.source.parsed.document.document_id).source.parsed.document.abstract
        == "Old evidence."
    )
    assert store.load_version(store.version_id(two)) is None


def test_legacy_chunks_are_archived_without_rekey(engine, source_factory, prepared_factory):
    from clinical_agent.adapters.postgres.store import PostgresStore
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore
    from clinical_agent.domain.ingestion import document_id_for

    one = prepared_factory(
        source_factory(
            text="Legacy original.",
            kind="pubmed",
            pmid="98765004",
            document_id=document_id_for("pubmed", "98765004"),
        )
    )
    PostgresStore(engine).save(one)
    two = prepared_factory(
        source_factory(
            text="Legacy replacement.",
            kind="pubmed",
            pmid="98765004",
            document_id=one.source.parsed.document.document_id,
        )
    )
    store = VersionedPostgresStore(engine)
    store.save(two)
    archived = store.load_version(store.version_id(one))
    assert archived.embedded[0].evidence == one.embedded[0].evidence
    assert archived.source.parsed.source_units == one.source.parsed.source_units
