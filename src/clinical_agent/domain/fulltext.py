"""Supplementary fulltext passages; PubMed snapshots remain immutable."""

from uuid import UUID

from pydantic import Field, model_validator

from clinical_agent.domain.models import DTO, PubMedID, SnapshotHash
from clinical_agent.domain.openalex import OpenAlexRecord


class FulltextPassage(DTO):
    chunk_id: UUID
    pmid: PubMedID | None = None
    pmcid: str | None = None
    paper_key: str | None = None
    openalex_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    representation_hash: SnapshotHash | None = None
    title: str
    doi: str | None = None
    section: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    content_hash: SnapshotHash
    source_url: str
    license: str
    content_scope: str = "fulltext"

    @model_validator(mode="after")
    def identity_and_span(self):
        if self.end - self.start != len(self.text):
            raise ValueError("Fulltext span must match text")
        if self.paper_key is not None:
            if not self.openalex_id or not self.representation_hash:
                raise ValueError("OA evidence requires identity and parsed representation")
        elif self.pmid is None or self.pmcid is None:
            raise ValueError("Legacy evidence requires PMC identity")
        return self


class FulltextUnit(DTO):
    section: str
    text: str = Field(min_length=1)
    start: int = Field(ge=0)
    page: int | None = Field(default=None, ge=1)


def paper_key(record: OpenAlexRecord) -> str:
    return "doi:" + record.doi if record.doi else record.openalex_id
