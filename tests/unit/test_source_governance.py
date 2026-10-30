from uuid import uuid4

import pytest
from pydantic import ValidationError

from clinical_agent.domain.governance import AliasClaim, EvidenceBasis, StatusChange


def basis():
    return EvidenceBasis(
        uri="https://example.org/notice",
        snapshot_hash="a" * 64,
        quote="Synthetic governance evidence",
        recorded_by="test reviewer",
    )


@pytest.mark.parametrize(
    "raw,expected",
    [("HTTPS://DOI.ORG/10.1234/ABC", "10.1234/abc"), ("doi:10.1234/AbC", "10.1234/abc")],
)
def test_doi_normalization(raw, expected):
    assert (
        AliasClaim(namespace="doi", value=raw, document_id=uuid4(), evidence=basis()).value
        == expected
    )


@pytest.mark.parametrize(
    "namespace,value",
    [("pmid", "001"), ("doi", "junk"), ("pdf_sha256", "bad"), ("pmid", "1 OR 1=1")],
)
def test_alias_rejects_bad_identity(namespace, value):
    with pytest.raises(ValidationError):
        AliasClaim(namespace=namespace, value=value, document_id=uuid4(), evidence=basis())


def test_status_and_evidence_are_explicit():
    with pytest.raises(ValidationError):
        StatusChange(
            event_id=uuid4(),
            document_id=uuid4(),
            status="verified",
            expected_event_id=None,
            evidence=basis(),
        )
    with pytest.raises(ValidationError):
        EvidenceBasis(uri="javascript:alert(1)", snapshot_hash="a" * 64, quote="", recorded_by="")
