"""Pure ORM/DTO mapping contracts without opening connections."""

import copy
from uuid import uuid4

import pytest


@pytest.mark.parametrize("kind", ["pdf", "pubmed"])
def test_mapper_roundtrip_is_complete_and_detached(source_factory, prepared_factory, kind):
    from clinical_agent.adapters.postgres.store import prepared_from_records, records_for

    original = prepared_factory(source_factory(kind=kind), max_tokens=13)
    document, chunks = records_for(original)
    rebuilt = prepared_from_records(document, chunks)
    assert rebuilt == original
    assert document.ingestion_metadata["parser_version"] == "synthetic-1"
    assert not hasattr(rebuilt, "_sa_instance_state")
    assert [row.chunk_index for row in chunks] == list(range(1, len(chunks) + 1))


@pytest.mark.parametrize(
    "case", ["legacy", "policy", "order", "token", "vector", "source", "slice"]
)
def test_mapper_rejects_corrupt_storage_instead_of_fabricating_provenance(prepared_factory, case):
    from clinical_agent.adapters.postgres.store import prepared_from_records, records_for
    from clinical_agent.domain.ingestion import IngestionError

    document, chunks = records_for(prepared_factory(max_tokens=13))
    if case == "legacy":
        document.ingestion_metadata = None
    elif case == "policy":
        chunks[0].chunking_policy = {"max_tokens": 2}
    elif case == "order":
        chunks.reverse()
    elif case == "token":
        chunks[0].token_count = 0
    elif case == "vector":
        chunks[0].embedding = [0.0] * 768
    elif case == "source":
        chunks[0].document_id = uuid4()
    else:
        document.source_units[0]["text"] = "other source"
    with pytest.raises(IngestionError, match="^storage_corrupt$"):
        prepared_from_records(document, chunks)


def test_mapping_does_not_modify_caller_and_does_not_alias_mutable_json(prepared_factory):
    from clinical_agent.adapters.postgres.store import records_for

    original = prepared_factory()
    before = copy.deepcopy(original)
    document, chunks = records_for(original)
    document.source_units[0]["text"] = "ORM mutation"
    chunks[0].embedding[0] = 0.0
    assert original == before


def test_schema_has_nullable_legacy_metadata_and_incremental_revision():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from clinical_agent.adapters.postgres.models import DocumentRecord

    assert DocumentRecord.__table__.c.ingestion_metadata.nullable
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == "p107_0002"
    assert scripts.get_revision("p107_0002").down_revision == "p106_0001"
