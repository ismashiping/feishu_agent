from uuid import uuid4

import pytest
from sqlalchemy import event

from tests.integration.test_postgres import engine as engine

pytestmark = [pytest.mark.integration, pytest.mark.database]


def test_rebuild_stage_atomic_activation_and_stale_guard(
    engine, source_factory, prepared_factory, fake_embedder
):
    from clinical_agent.db.rebuild import KnowledgeRebuilder
    from clinical_agent.db.store import PostgresStore
    from clinical_agent.db.versions import VersionedPostgresStore
    from clinical_agent.domain.chunking import ChunkingPolicy
    from clinical_agent.domain.maintenance import RebuildRequest

    store = VersionedPostgresStore(engine)
    original = prepared_factory(
        source_factory(text="Rebuild source evidence with enough text to split.")
    )
    store.save(original)
    identity = original.source.parsed.document.document_id
    rebuild = KnowledgeRebuilder(engine, fake_embedder)
    request = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    old = PostgresStore(engine).load(identity)
    assert rebuild.stage(request, evaluate=lambda _: "not_accepted")["status"] == "staged"
    with pytest.raises(ValueError, match="evaluation_required"):
        rebuild.activate(request.run_id)
    accepted = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    rebuild.stage(accepted, evaluate=rebuild.evaluate)
    assert (
        PostgresStore(engine).load(identity).embedded[0].evidence.chunk_id
        == old.embedded[0].evidence.chunk_id
    )

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO chunks"):
            raise RuntimeError("Injected activation failure")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError):
            rebuild.activate(accepted.run_id)
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    assert (
        PostgresStore(engine).load(identity).embedded[0].evidence.chunk_id
        == old.embedded[0].evidence.chunk_id
    )
    assert rebuild.activate(accepted.run_id)["status"] == "activated"
    assert rebuild.activate(accepted.run_id)["status"] == "activated"
    assert len(PostgresStore(engine).load(identity).embedded) > len(old.embedded)
    assert store.load_version(store.version_id(original)) is not None
    stale = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=20))
    rebuild.stage(stale, evaluate=lambda _: "passed")
    store.save(prepared_factory(source_factory(text="Concurrent new document")))
    with pytest.raises(ValueError, match="source_changed"):
        rebuild.activate(stale.run_id)


def test_rebuild_model_guard_and_no_evaluation(engine, fake_embedder):
    from clinical_agent.db.rebuild import KnowledgeRebuilder
    from clinical_agent.domain.maintenance import RebuildRequest

    fake_embedder.tokenizer_profile = fake_embedder.tokenizer_profile.model_copy(
        update={"model_id": "unknown-model"}
    )
    with pytest.raises(ValueError, match="unsupported_rebuild_model"):
        KnowledgeRebuilder(engine, fake_embedder).stage(RebuildRequest(run_id=uuid4()))
    assert fake_embedder.calls == 0
