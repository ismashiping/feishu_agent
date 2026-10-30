"""Offline contract demo; never registers synthetic evidence in a database."""

from uuid import uuid4

from clinical_agent.domain.governance import AliasClaim, EvidenceBasis, GovernanceState

basis = EvidenceBasis(
    uri="https://example.org/synthetic",
    snapshot_hash="a" * 64,
    quote="Synthetic evidence only",
    recorded_by="demo",
)
claim = AliasClaim(
    namespace="doi", value="HTTPS://DOI.ORG/10.1234/EXAMPLE", document_id=uuid4(), evidence=basis
)
assert claim.value == "10.1234/example"
assert GovernanceState().status == "unreviewed"
print("DOI normalization and unreviewed default verified; no DB/network/model calls.")
