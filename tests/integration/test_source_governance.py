from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from tests.integration.test_postgres import engine as engine
from tests.unit.test_source_governance import basis

pytestmark = [pytest.mark.integration, pytest.mark.database]


def setup_source(engine, source_factory, prepared_factory, **kwargs):
    from clinical_agent.adapters.postgres.versions import VersionedPostgresStore

    value = prepared_factory(source_factory(**kwargs))
    store = VersionedPostgresStore(engine)
    store.save(value)
    return store, value, value.source.parsed.document.document_id


def test_alias_idempotence_conflicts_and_native_guard(engine, source_factory, prepared_factory):
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.domain.governance import AliasClaim

    registry = SourceGovernance(engine)
    _, _, one = setup_source(engine, source_factory, prepared_factory, text="Alias one")
    _, _, two = setup_source(engine, source_factory, prepared_factory, text="Alias two")
    claim = AliasClaim(
        namespace="doi", value="doi:10.1234/CONFLICT", document_id=one, evidence=basis()
    )
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: registry.claim(claim), range(2)))
    assert all(r["status"] == "resolved" for r in results)
    result = registry.claim(claim.model_copy(update={"document_id": two}))
    assert result["status"] == "conflicted"
    assert set(result["document_ids"]) == {str(one), str(two)}
    with pytest.raises(ValueError, match="native_identity_conflict"):
        registry.claim(
            AliasClaim(namespace="pdf_sha256", value="b" * 64, document_id=one, evidence=basis())
        )
    assert registry.resolve("pdf_sha256", "b" * 64)["status"] == "unmapped"
    assert len(registry.inspect(one)["aliases"]) == 1
    _, native, pubmed_id = setup_source(
        engine,
        source_factory,
        prepared_factory,
        text="Native PMID record",
        kind="pubmed",
        pmid="81000001",
        doi="https://doi.org/10.1234/NATIVE",
    )
    assert registry.resolve("doi", "10.1234/native")["document_ids"] == [str(pubmed_id)]
    result = registry.claim(
        AliasClaim(namespace="pmid", value="81000001", document_id=one, evidence=basis())
    )
    assert result["status"] == "conflicted"
    assert set(result["document_ids"]) == {str(one), str(pubmed_id)}
    with pytest.raises(ValueError, match="native_identity_conflict"):
        registry.claim(
            AliasClaim(namespace="pmid", value="81000002", document_id=pubmed_id, evidence=basis())
        )


def test_status_compare_and_swap_and_idempotence(engine, source_factory, prepared_factory):
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.domain.governance import StatusChange

    registry = SourceGovernance(engine)
    _, _, identity = setup_source(engine, source_factory, prepared_factory, text="CAS source")
    first = StatusChange(
        event_id=uuid4(),
        document_id=identity,
        status="retracted",
        expected_event_id=None,
        evidence=basis(),
    )
    assert registry.change_status(first)["status"] == "retracted"
    assert registry.change_status(first)["event_id"] == str(first.event_id)
    with pytest.raises(ValueError, match="event_conflict"):
        registry.change_status(first.model_copy(update={"status": "normal"}))
    with pytest.raises(ValueError, match="stale_status"):
        registry.change_status(first.model_copy(update={"event_id": uuid4()}))
    choices = [
        StatusChange(
            event_id=uuid4(),
            document_id=identity,
            status=status,
            expected_event_id=first.event_id,
            evidence=basis(),
        )
        for status in ("corrected", "normal")
    ]

    def apply(value):
        try:
            registry.change_status(value)
            return "ok"
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(apply, choices)) == ["ok", "stale_status"]
    assert len(registry.inspect(identity)["events"]) == 2
    # A replay of an older event never overwrites a newer current projection.
    registry.change_status(first)
    assert registry.inspect(identity)["state"]["event_id"] != str(first.event_id)


@pytest.mark.parametrize("blocked", ["retracted", "withdrawn", "expression_of_concern"])
def test_governance_filters_all_modes_and_preserves_history(
    engine, source_factory, prepared_factory, blocked
):
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.adapters.postgres.retrieval import PostgresRetriever
    from clinical_agent.domain.governance import StatusChange
    from clinical_agent.domain.retrieval import RetrievalOptions

    registry = SourceGovernance(engine)
    store, original, identity = setup_source(
        engine,
        source_factory,
        prepared_factory,
        text="Governance cohort evidence " + blocked,
        kind="pubmed",
        pmid=str(80000000 + ["retracted", "withdrawn", "expression_of_concern"].index(blocked)),
    )
    old_id = store.version_id(original)
    first = StatusChange(
        event_id=uuid4(),
        document_id=identity,
        status=blocked,
        expected_event_id=None,
        evidence=basis(),
    )
    registry.change_status(first)
    from clinical_agent.domain.embedding import QueryEmbedding
    from clinical_agent.domain.retrieval import retrieval_embedding_info

    query = QueryEmbedding(
        vector=original.embedded[0].vector, embedding_info=retrieval_embedding_info()
    )
    retriever = PostgresRetriever(engine)
    for mode in ("vector", "keyword", "hybrid"):
        result = retriever.search_hybrid(
            "cohort",
            query,
            RetrievalOptions(mode=mode, document_ids=[identity]),
            timeout_seconds=10.0,
        )
        assert not result.hits
        assert "source_governance_local_policy" in result.warnings
    updated = prepared_factory(
        source_factory(
            text="Updated governance cohort evidence.",
            kind="pubmed",
            pmid=original.source.parsed.document.pmid,
            document_id=identity,
        )
    )
    store.save(updated)
    assert registry.inspect(identity)["state"]["status"] == blocked
    assert (
        store.load_version(old_id).source.parsed.document.abstract
        == original.source.parsed.document.abstract
    )
    registry.change_status(
        StatusChange(
            event_id=uuid4(),
            document_id=identity,
            status="corrected",
            expected_event_id=first.event_id,
            evidence=basis(),
        )
    )
    result = retriever.search_hybrid(
        "cohort",
        None,
        RetrievalOptions(mode="keyword", document_ids=[identity]),
        timeout_seconds=10.0,
    )
    assert result.hits[0].document.governance.status == "corrected"
    assert result.hits[0].document.governance.evidence.snapshot_hash == "a" * 64
    from datetime import UTC, datetime

    from clinical_agent.domain.citations import build_answer
    from clinical_agent.domain.research import DraftClaim, GenerationDraft, QuestionRequest

    answer = build_answer(
        QuestionRequest(request_id=uuid4(), question="cohort", options=result.options),
        result,
        GenerationDraft(
            claims=[
                DraftClaim(
                    text="Cohort evidence",
                    kind="evidence",
                    evidence_chunk_ids=[result.hits[0].chunk.chunk_id],
                    limitations=[],
                )
            ]
        ),
        generated_at=datetime.now(UTC),
    )
    assert answer.sources[0].governance == result.hits[0].document.governance


def test_unknown_document_and_migration(engine):
    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.adapters.postgres.models import SourceStatusEventRecord
    from clinical_agent.domain.governance import StatusChange
    from tests.integration.test_postgres import _migration

    registry = SourceGovernance(engine)
    with engine.connect() as connection:
        before = connection.scalar(select(func.count()).select_from(SourceStatusEventRecord))
    with pytest.raises(ValueError, match="document_not_found"):
        registry.change_status(
            StatusChange(
                event_id=uuid4(),
                document_id=uuid4(),
                status="normal",
                expected_event_id=None,
                evidence=basis(),
            )
        )
    with engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(SourceStatusEventRecord)) == before
        )
    # Only governance tables are rolled back; legacy evidence tables remain intact.
    _migration(engine, "downgrade", "p802_0005")
    _migration(engine, "upgrade", "head")


def test_status_failure_rolls_back_event_and_projection(engine, source_factory, prepared_factory):
    from sqlalchemy import event

    from clinical_agent.adapters.postgres.governance import SourceGovernance
    from clinical_agent.domain.governance import StatusChange

    registry = SourceGovernance(engine)
    _, _, identity = setup_source(
        engine, source_factory, prepared_factory, text="Atomic status evidence"
    )
    first = StatusChange(
        event_id=uuid4(),
        document_id=identity,
        status="retracted",
        expected_event_id=None,
        evidence=basis(),
    )
    registry.change_status(first)

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE source_states"):
            raise RuntimeError("Injected state projection failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Injected"):
            registry.change_status(
                StatusChange(
                    event_id=uuid4(),
                    document_id=identity,
                    status="normal",
                    expected_event_id=first.event_id,
                    evidence=basis(),
                )
            )
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    record = registry.inspect(identity)
    assert record["state"]["status"] == "retracted"
    assert len(record["events"]) == 1
