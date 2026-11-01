"""Offline PubMed field mapping using an explicitly hardened XML parser."""

import re
from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, TypedDict
from uuid import UUID
from xml.etree.ElementTree import Element, ParseError, tostring

# defusedxml 0.7.1 has no typing marker; isolate only these external imports.
import defusedxml  # type: ignore[import-untyped]
from defusedxml import ElementTree as safe_xml
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from pydantic import Field, FileUrl, ValidationError

from clinical_agent.domain.models import (
    DTO,
    AbstractSourceUnit,
    LiteratureDocument,
    ParsedPubmedArticle,
    PositiveInteger,
    PublicationDate,
    PubmedRejectionCode,
    PubmedXmlBatch,
    PubmedXmlEntry,
    SourceMetadata,
)

if TYPE_CHECKING:
    from clinical_agent.domain.pubmed import PubMedRecord


class PubmedXmlLimits(DTO):
    max_file_bytes: PositiveInteger = 10 * 1024 * 1024
    max_records: PositiveInteger = 1000
    max_depth: PositiveInteger = 64
    max_nodes: PositiveInteger = 100000
    max_abstract_characters: PositiveInteger = 1000000
    max_seconds: float = Field(default=30.0, gt=0, strict=True, allow_inf_nan=False)


class PubmedXmlError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _RejectedRecord(ValueError):
    def __init__(self, code: PubmedRejectionCode) -> None:
        self.code = code
        super().__init__(code)


class _Citation(TypedDict):
    pmid: str
    title: str
    authors: list[str]
    journal: str | None
    doi: str | None
    publication_date: PublicationDate
    abstract: str


_MONTH_NAMES = (
    "January February March April May June July August September October November December".split()
)
_MONTHS = {
    spelling: number
    for number, name in enumerate(_MONTH_NAMES, start=1)
    for spelling in (name.lower(), name[:3].lower())
}


def _text(element: Element | None) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _publication_date(element: Element | None) -> PublicationDate:
    if element is None or not _text(element):
        return PublicationDate(precision="unknown")
    values = {child.tag: _text(child) for child in element}
    if len(values) != len(element):
        raise _RejectedRecord("pubmed_invalid_date")
    raw = " ".join(value for value in values.values() if value)
    if "MedlineDate" in values:
        if len(values) != 1:
            raise _RejectedRecord("pubmed_invalid_date")
        return PublicationDate(precision="unknown", raw=raw)
    year_text = values.get("Year", "")
    if re.fullmatch(r"[0-9]{4}", year_text) is None:
        raise _RejectedRecord("pubmed_invalid_date")
    year = int(year_text)
    if year == 0:
        raise _RejectedRecord("pubmed_invalid_date")
    month_text = values.get("Month", "")
    day_text = values.get("Day", "")
    if day_text and (re.fullmatch(r"[0-9]{1,2}", day_text) is None or not 1 <= int(day_text) <= 31):
        raise _RejectedRecord("pubmed_invalid_date")
    if "Season" in values:
        if month_text or day_text:
            raise _RejectedRecord("pubmed_invalid_date")
        return PublicationDate(precision="unknown", raw=raw)
    try:
        if not month_text:
            if day_text:
                raise _RejectedRecord("pubmed_invalid_date")
            return PublicationDate(precision="year", raw=raw, year=year)
        if re.fullmatch(r"[0-9]{1,2}", month_text):
            month = int(month_text)
        else:
            mapped_month = _MONTHS.get(month_text.lower())
            if mapped_month is None:
                return PublicationDate(precision="unknown", raw=raw)
            month = mapped_month
        if not day_text:
            return PublicationDate(precision="month", raw=raw, year=year, month=month)
        return PublicationDate(precision="day", raw=raw, year=year, month=month, day=int(day_text))
    except ValidationError:
        raise _RejectedRecord("pubmed_invalid_date") from None


def _map_record(
    record: Element, max_characters: int, *, allow_no_abstract: bool = False
) -> tuple[_Citation, list[AbstractSourceUnit]]:
    if record.tag != "PubmedArticle":
        raise _RejectedRecord("pubmed_unsupported_record")
    primary_ids = record.findall("MedlineCitation/PMID")
    pmid = _text(primary_ids[0]) if len(primary_ids) == 1 else ""
    if re.fullmatch(r"[1-9][0-9]*", pmid) is None:
        raise _RejectedRecord("pubmed_invalid_pmid")
    article = record.find("MedlineCitation/Article")
    if article is None:
        raise _RejectedRecord("pubmed_missing_title")
    title = _text(article.find("ArticleTitle"))
    if not title:
        raise _RejectedRecord("pubmed_missing_title")
    dois: set[str] = set()
    for identifier in record.findall("PubmedData/ArticleIdList/ArticleId"):
        value = _text(identifier)
        kind = identifier.get("IdType", "pubmed")
        if kind == "pubmed" and value and value != pmid:
            raise _RejectedRecord("pubmed_pmid_conflict")
        if kind == "doi" and value:
            dois.add(value)
    for identifier in article.findall("ELocationID"):
        value = _text(identifier)
        if identifier.get("EIdType") == "doi" and identifier.get("ValidYN", "Y") != "N" and value:
            dois.add(value)
    if len(dois) > 1:
        raise _RejectedRecord("pubmed_doi_conflict")
    authors: list[str] = []
    for author in article.findall("AuthorList/Author"):
        if author.get("ValidYN", "Y") == "N":
            continue
        collective = _text(author.find("CollectiveName"))
        last = _text(author.find("LastName"))
        if collective and not last:
            authors.append(collective)
        elif last and not collective:
            given = _text(author.find("ForeName")) or _text(author.find("Initials"))
            authors.append(
                " ".join(part for part in (given, last, _text(author.find("Suffix"))) if part)
            )
        else:
            raise _RejectedRecord("pubmed_invalid_author")
    publication_date = _publication_date(article.find("Journal/JournalIssue/PubDate"))
    units: list[AbstractSourceUnit] = []
    offset = 0
    for section in article.findall("Abstract/AbstractText"):
        text = _text(section)
        if not text:
            continue
        end = offset + len(text)
        if end > max_characters:
            raise _RejectedRecord("pubmed_text_limit")
        units.append(
            AbstractSourceUnit(
                index=len(units) + 1,
                text=text,
                start=offset,
                end=end,
                label=" ".join((section.get("Label") or "").split()) or None,
                category=" ".join((section.get("NlmCategory") or "").split()) or None,
            )
        )
        offset = end + 2
    if not units and not allow_no_abstract:
        raise _RejectedRecord("pubmed_no_abstract")
    return _Citation(
        pmid=pmid,
        title=title,
        authors=authors,
        journal=_text(article.find("Journal/Title"))
        or _text(article.find("Journal/ISOAbbreviation"))
        or None,
        doi=next(iter(dois)) if dois else None,
        publication_date=publication_date,
        abstract="\n\n".join(unit.text for unit in units),
    ), units


def _read_tree(
    snapshot: bytes, limits: PubmedXmlLimits, check_deadline: Callable[[], None]
) -> Element:
    root: Element | None = None
    depth = nodes = records = 0
    try:
        with BytesIO(snapshot) as stream:
            for event, element in safe_xml.iterparse(
                stream,
                events=("start", "end"),
                forbid_dtd=False,
                forbid_entities=True,
                forbid_external=True,
            ):
                check_deadline()
                if event == "start":
                    depth += 1
                    nodes += 1
                    if root is None:
                        root = element
                        if root.tag != "PubmedArticleSet":
                            raise PubmedXmlError("xml_root_invalid")
                    if depth > limits.max_depth:
                        raise PubmedXmlError("xml_depth_limit")
                    if nodes > limits.max_nodes:
                        raise PubmedXmlError("xml_node_limit")
                    if depth == 2:
                        records += 1
                        if records > limits.max_records:
                            raise PubmedXmlError("xml_record_limit")
                else:
                    depth -= 1
    except DefusedXmlException:
        raise PubmedXmlError("xml_unsafe") from None
    except ParseError:
        raise PubmedXmlError("xml_invalid") from None
    if root is None:
        raise PubmedXmlError("xml_invalid")
    return root


def parse_pubmed_xml(
    path: Path,
    *,
    allowed_root: Path,
    ingestion_time: datetime,
    document_id_factory: Callable[[str], UUID],
    limits: PubmedXmlLimits | None = None,
) -> PubmedXmlBatch:
    if not isinstance(ingestion_time, datetime) or ingestion_time.utcoffset() is None:
        raise ValueError("Ingestion time must be an explicitly timezone-aware datetime")
    policy = limits if limits is not None else PubmedXmlLimits()
    deadline = monotonic() + policy.max_seconds

    def check_deadline() -> None:
        if monotonic() > deadline:
            raise PubmedXmlError("xml_timeout")

    try:
        root_path = allowed_root.resolve(strict=True)
        resolved = path.resolve(strict=True)
        if (
            not root_path.is_dir()
            or not resolved.is_relative_to(root_path)
            or not resolved.is_file()
        ):
            raise PubmedXmlError("xml_path_invalid")
    except OSError:
        raise PubmedXmlError("xml_path_invalid") from None
    try:
        with resolved.open("rb") as source_file:
            snapshot = source_file.read(policy.max_file_bytes + 1)
    except OSError:
        raise PubmedXmlError("xml_io_error") from None
    if len(snapshot) > policy.max_file_bytes:
        raise PubmedXmlError("xml_too_large")
    check_deadline()
    root = _read_tree(snapshot, policy, check_deadline)
    check_deadline()
    source = SourceMetadata(
        source_type="pubmed",
        source_url=None,
        source_uri=FileUrl(resolved.as_uri()),
        content_hash=sha256(snapshot).hexdigest(),
        content_scope="abstract",
    )
    entries: list[PubmedXmlEntry] = []
    pmids: set[str] = set()
    for index, record in enumerate(root, start=1):
        check_deadline()
        try:
            citation, units = _map_record(record, policy.max_abstract_characters)
            if citation["pmid"] in pmids:
                raise _RejectedRecord("pubmed_duplicate_pmid")
        except _RejectedRecord as error:
            entries.append(
                PubmedXmlEntry(index=index, status="rejected", article=None, error_code=error.code)
            )
            continue
        identity = document_id_factory(citation["pmid"])
        if not isinstance(identity, UUID):
            raise TypeError("Document ID factory must return a UUID")
        document = LiteratureDocument(
            document_id=identity,
            title_origin="pubmed_metadata",
            ingestion_time=ingestion_time,
            source_type="pubmed",
            source_url=None,
            source_uri=source.source_uri,
            content_hash=source.content_hash,
            content_scope="abstract",
            text=None,
            evidence_chunks=[],
            **citation,
        )
        article = ParsedPubmedArticle(document=document, source_units=units)
        entries.append(
            PubmedXmlEntry(index=index, status="parsed", article=article, error_code=None)
        )
        pmids.add(citation["pmid"])
    check_deadline()
    return PubmedXmlBatch(source=source, entries=entries, parser_version=defusedxml.__version__)


def parse_pubmed_response(
    snapshot: bytes, *, fetched_at: datetime, check_deadline: Callable[[], None] | None = None
) -> list["PubMedRecord"]:
    """Reuse offline field rules without rejecting genuine metadata-only records."""
    from clinical_agent.domain.pubmed import PubMedRecord
    from clinical_agent.domain.research import ResearchError

    limits = PubmedXmlLimits(max_records=20, max_file_bytes=5 * 1024 * 1024)
    deadline = monotonic() + limits.max_seconds

    def check() -> None:
        if check_deadline is not None:
            check_deadline()
        if monotonic() >= deadline:
            raise ResearchError("pubmed_timeout")

    try:
        if len(snapshot) > limits.max_file_bytes:
            raise ValueError("Response too large")
        root = _read_tree(snapshot, limits, check)
        results: list[PubMedRecord] = []
        seen: set[str] = set()
        for record in root:
            check()
            citation, units = _map_record(
                record, limits.max_abstract_characters, allow_no_abstract=True
            )
            pmid = citation["pmid"]
            if pmid in seen:
                raise ValueError("Duplicate response identity")
            seen.add(pmid)
            normalized = tostring(record, encoding="unicode")
            publication_types = [
                _text(item)
                for item in record.findall(
                    "MedlineCitation/Article/PublicationTypeList/PublicationType"
                )
                if _text(item)
            ]
            notices = [
                f"{item.get('RefType', 'unknown')}:{_text(item.find('PMID'))}"
                for item in record.findall(
                    "MedlineCitation/CommentsCorrectionsList/CommentsCorrections"
                )
            ]
            results.append(
                PubMedRecord(
                    **citation,
                    source_units=units,
                    publication_types=publication_types,
                    notices=notices,
                    source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    content_scope="abstract" if units else "metadata_only",
                    snapshot_xml=normalized,
                    content_hash=sha256(normalized.encode()).hexdigest(),
                )
            )
        return results
    except ResearchError:
        raise
    except Exception:
        raise ResearchError("pubmed_invalid") from None
