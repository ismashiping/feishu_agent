from datetime import UTC, datetime


def test_signature_ignores_acquisition_time_and_path(prepared_factory):
    from clinical_agent.adapters.postgres.versions import fingerprint, versioned

    prepared = prepared_factory()
    changed = prepared.model_copy(deep=True)
    changed.source.parsed.document.ingestion_time = datetime.now(UTC)
    assert fingerprint(changed) == fingerprint(prepared)
    encoded, identity = versioned(prepared)
    assert encoded.source.parsed.document.document_id == prepared.source.parsed.document.document_id
    assert encoded.embedded[0].evidence.chunk_id != prepared.embedded[0].evidence.chunk_id
    assert versioned(prepared)[1] == identity


def test_metadata_creates_new_version(prepared_factory):
    from clinical_agent.adapters.postgres.versions import fingerprint

    prepared = prepared_factory()
    changed = prepared.model_copy(deep=True)
    changed.source.parsed.document.title = "Changed metadata"
    assert fingerprint(changed) != fingerprint(prepared)
