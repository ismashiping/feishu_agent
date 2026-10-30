"""Explicit, auditable assertions; submitted evidence is not automatic verification."""

import re
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import FileUrl, HttpUrl, StringConstraints, model_validator

from clinical_agent.domain.models import DTO, SnapshotHash

BoundedText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
]
Namespace = Literal["pmid", "doi", "pdf_sha256"]
SourceStatus = Literal["normal", "corrected", "retracted", "withdrawn", "expression_of_concern"]
BLOCKED_STATUSES = ("retracted", "withdrawn", "expression_of_concern")


def normalize_alias(namespace: Namespace, value: str) -> str:
    value = value.strip()
    if namespace == "doi":
        value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I).lower()
        pattern = r"10\.[0-9]{4,9}/[^\s]+"
    elif namespace == "pmid":
        pattern = r"[1-9][0-9]*"
    elif namespace == "pdf_sha256":
        value = value.lower()
        pattern = r"[0-9a-f]{64}"
    else:
        raise ValueError("invalid_namespace")
    if not re.fullmatch(pattern, value) or len(value) > 512:
        raise ValueError("invalid_alias")
    return value


class EvidenceBasis(DTO):
    uri: HttpUrl | FileUrl
    snapshot_hash: SnapshotHash
    quote: BoundedText
    recorded_by: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
    ]


class AliasClaim(DTO):
    namespace: Namespace
    value: BoundedText
    document_id: UUID
    evidence: EvidenceBasis

    @model_validator(mode="after")
    def canonicalize(self) -> Self:
        self.value = normalize_alias(self.namespace, self.value)
        return self


class StatusChange(DTO):
    event_id: UUID
    document_id: UUID
    status: SourceStatus
    expected_event_id: UUID | None
    evidence: EvidenceBasis


class GovernanceState(DTO):
    status: Literal[
        "unreviewed", "normal", "corrected", "retracted", "withdrawn", "expression_of_concern"
    ] = "unreviewed"
    event_id: UUID | None = None
    evidence: EvidenceBasis | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if (self.status == "unreviewed") != (self.event_id is None and self.evidence is None):
            raise ValueError("invalid_governance_state")
        if self.status != "unreviewed" and (self.event_id is None or self.evidence is None):
            raise ValueError("missing_governance_evidence")
        return self


def pubmed_status(publication_types: list[str], notices: list[str]) -> SourceStatus | None:
    types = {value.casefold().strip() for value in publication_types}
    refs = [value.casefold() for value in notices]
    if "retracted publication" in types or any(v.startswith("retractionin:") for v in refs):
        return "retracted"
    if "withdrawn publication" in types:
        return "withdrawn"
    if any(v.startswith("expressionofconcernin:") for v in refs):
        return "expression_of_concern"
    if any(v.startswith("erratumin:") for v in refs):
        return "corrected"
    return None
