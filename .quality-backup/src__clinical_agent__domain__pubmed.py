"""Bounded PubMed search, official metadata and per-request source snapshots."""

from datetime import date
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from clinical_agent.domain.models import (
    DTO,
    AbstractSourceUnit,
    PositiveInteger,
    PublicationDate,
    PubMedID,
    SnapshotHash,
)
from clinical_agent.domain.pico import QueryPlan

Query = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
]


class PubMedOptions(DTO):
    query: Query | None = None
    date_from: date | None = None
    date_to: date | None = None
    date_field: Literal["pdat", "edat"] = "pdat"
    sort: Literal["relevance", "pub_date"] = "relevance"
    max_results: Annotated[PositiveInteger, Field(le=20)] = 10

    @model_validator(mode="after")
    def dates(self) -> Self:
        if (self.date_from is None) != (self.date_to is None):
            raise ValueError("Supply both date bounds")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("Date bounds must be ordered")
        return self


class PubMedSearchRequest(DTO):
    question: Query
    options: PubMedOptions = Field(default_factory=PubMedOptions)
    query_plan: QueryPlan | None = None

    def query_text(self) -> str:
        if (
            self.options.query is None
            and self.query_plan is not None
            and self.query_plan.structured_question.blocking_ambiguities == []
        ):
            if self.query_plan.concept_groups:
                def literal(term: str) -> str:
                    return '"' + term.replace('"', " ").replace(chr(92), " ") + '"'

                query = " AND ".join(
                    "(" + " OR ".join(literal(t) for t in dict.fromkeys(group)) + ")"
                    for group in self.query_plan.concept_groups
                )
                if len(query) <= 4000:
                    return query
        return self.options.query or (
            self.query_plan.original_question if self.query_plan else self.question
        )


class PubMedRecord(DTO):
    pmid: PubMedID
    title: str
    authors: list[str]
    journal: str | None
    doi: str | None
    publication_date: PublicationDate
    abstract: str
    source_units: list[AbstractSourceUnit]
    publication_types: list[str]
    notices: list[str]
    source_url: str
    content_scope: Literal["abstract", "metadata_only"]
    snapshot_xml: str
    content_hash: SnapshotHash

    @model_validator(mode="after")
    def snapshot(self) -> Self:
        if (
            not self.title.strip()
            or self.source_url != f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        ):
            raise ValueError("Record identity must match its official URL")
        if sha256(self.snapshot_xml.encode()).hexdigest() != self.content_hash:
            raise ValueError("Record snapshot hash mismatch")
        if self.abstract != "\n\n".join(unit.text for unit in self.source_units):
            raise ValueError("Abstract must match its source units")
        if (self.content_scope == "abstract") != bool(self.source_units):
            raise ValueError("Content scope must match acquired text")
        for index, unit in enumerate(self.source_units):
            if (
                unit.index != index + 1
                or unit.start != (self.source_units[index - 1].end + 2 if index else 0)
                or self.abstract[unit.start : unit.end] != unit.text
            ):
                raise ValueError("Abstract source interval mismatch")
        return self


class SearchProvenance(DTO):
    endpoint: Literal["https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"] = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    )
    query_sent: str
    query_translation: str | None
    total_count: Annotated[int, Field(strict=True, ge=0)]
    requested_limit: Annotated[PositiveInteger, Field(le=20)]
    returned_count: Annotated[int, Field(strict=True, ge=0, le=20)]
    truncated: bool
    fetched_at: AwareDatetime
    date_from: date | None
    date_to: date | None
    date_field: Literal["pdat", "edat"]
    sort: Literal["relevance", "pub_date"]
    status: Literal["complete", "partial"]
    warnings: list[str]
    missing_pmids: list[PubMedID]


class PubMedSearchResult(SearchProvenance):
    records: list[PubMedRecord]

    @model_validator(mode="after")
    def counts(self) -> Self:
        ids = [r.pmid for r in self.records]
        if (
            len(ids) != len(set(ids))
            or len(ids) != self.returned_count
            or len(ids) > self.requested_limit
        ):
            raise ValueError("Record count or identity mismatch")
        if set(ids) & set(self.missing_pmids) or self.missing_pmids and self.status != "partial":
            raise ValueError("Missing records must be reported as partial")
        return self

    def provenance(self) -> SearchProvenance:
        return SearchProvenance.model_validate(self.model_dump(exclude={"records"}))
