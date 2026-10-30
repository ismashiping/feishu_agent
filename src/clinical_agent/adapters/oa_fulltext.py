"""Licensed OA acquisition from explicit OpenAlex locations; no landing-page scraping."""

import re
import tempfile
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from clinical_agent.adapters.pdf import (
    PdfMetadataOverrides,
    PdfParseError,
    PdfParseLimits,
    parse_pdf,
)
from clinical_agent.adapters.pmc_fulltext import _GATE
from clinical_agent.domain.fulltext import FulltextUnit
from clinical_agent.domain.openalex import OpenAlexRecord, normalize_doi

HOSTS = frozenset(
    {
        "pmc.ncbi.nlm.nih.gov",
        "www.ncbi.nlm.nih.gov",
        "www.nature.com",
        "nature.com",
        "link.springer.com",
        "bmcmedimaging.biomedcentral.com",
        "arxiv.org",
        "journals.plos.org",
    }
)
LICENSES = frozenset({"cc-by", "cc-by-4.0", "cc-by-3.0", "cc-by-2.0", "cc0", "cc0-1.0"})


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def safe_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise ValueError("fulltext_url_not_allowed")
    return url


def parse_jats(raw: bytes, record: OpenAlexRecord) -> list[FulltextUnit]:
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, DefusedXmlException):
        raise ValueError("fulltext_xml_invalid") from None
    # OAI namespaces apply to the envelope; JATS elements are normally unqualified.
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    article = root if root.tag == "article" else root.find(".//article")
    if article is None:
        raise ValueError("fulltext_empty")
    meta = article.find("./front/article-meta")
    if meta is None:
        raise ValueError("fulltext_identity_mismatch")
    dois = [
        normalize_doi(e.text) for e in meta.findall("article-id") if e.get("pub-id-type") == "doi"
    ]
    title_element = meta.find("title-group/article-title")
    if title_element is None:
        raise ValueError("fulltext_identity_mismatch")
    title = "".join(title_element.itertext())
    if not record.doi or record.doi not in dois or normalized(title) != normalized(record.title):
        raise ValueError("fulltext_identity_mismatch")
    licenses = [
        v
        for element in meta.findall(".//license")
        for e in element.iter()
        for v in e.attrib.values()
    ]
    if not any(
        re.fullmatch(
            r"https?://creativecommons.org/(?:licenses/by/(?:2\.0|3\.0|4\.0)|publicdomain/zero/1\.0)/?",
            v,
        )
        for v in licenses
    ):
        raise ValueError("fulltext_license_not_allowed")
    units = []
    offset = 0

    def paragraph_text(element):
        text = element.text or ""
        for child in element:
            if child.tag not in {"table-wrap", "table", "fig", "supplementary-material"}:
                text += paragraph_text(child)
            text += child.tail or ""
        return text

    def walk(element, section):
        nonlocal offset
        for child in element:
            if child.tag == "sec":
                heading = child.find("title")
                label = "".join(heading.itertext()).strip() if heading is not None else "UNKNOWN"
                walk(child, label if section == "UNKNOWN" else section + " / " + label)
            elif child.tag == "p":
                text = " ".join(paragraph_text(child).split())
                if text:
                    units.append(FulltextUnit(section=section, text=text, start=offset))
                    offset += len(text) + 2

    body = article.find("body")
    if body is not None:
        walk(body, "UNKNOWN")
    if not units or offset > 500000:
        raise ValueError("fulltext_empty_or_text_budget")
    return units


HEADINGS = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?(abstract|introduction|background|methods|"
    r"materials and methods|methodology|experiments|experimental results|results|"
    r"discussion|limitations|conclusions?|references|acknowledg(?:e)?ments)(?:\s*[:.]\s*)?$",
    re.I,
)


def parse_oa_pdf(raw: bytes, record: OpenAlexRecord) -> list[FulltextUnit]:
    with tempfile.TemporaryDirectory(prefix="clinical-oa-") as directory:
        path = Path(directory) / "article.pdf"
        path.write_bytes(raw)
        try:
            parsed = parse_pdf(
                path,
                allowed_root=path.parent,
                document_id=uuid4(),
                ingestion_time=datetime.now(UTC),
                metadata=PdfMetadataOverrides(title=record.title),
                limits=PdfParseLimits(
                    max_file_bytes=10 * 1024 * 1024,
                    max_pages=100,
                    max_total_characters=500000,
                    max_seconds=10.0,
                ),
            )
        except PdfParseError as error:
            raise ValueError("fulltext_" + error.code) from None
    first = parsed.source_units[0].text
    if (
        not record.doi
        or record.doi.casefold() not in first.casefold()
        or normalized(record.title) not in normalized(first)
    ):
        raise ValueError("fulltext_identity_mismatch")
    pages = [(unit.page, unit.text.splitlines()) for unit in parsed.source_units]
    counts = Counter(
        line.strip() for _, lines in pages for line in set(lines[:2] + lines[-2:]) if line.strip()
    )
    repeated = {line for line, count in counts.items() if count >= max(3, len(pages) * 0.6)}
    section, offset, units = "UNKNOWN", 0, []
    for page, lines in pages:
        content = []

        def flush(current_section, page=page, content=content):
            nonlocal offset
            text = "\n".join(content).strip()
            content.clear()
            if text:
                units.append(
                    FulltextUnit(section=current_section, text=text, start=offset, page=page)
                )
                offset += len(text) + 2

        for index, line in enumerate(lines):
            if (index < 2 or index >= len(lines) - 2) and line.strip() in repeated:
                continue
            heading = HEADINGS.fullmatch(line.strip())
            if heading:
                flush(section)
                section = heading.group(1).title()
            else:
                content.append(line)
        flush(section)
    if not units:
        raise ValueError("fulltext_empty")
    return units


class OAFulltextSource:
    def __init__(self, client: httpx.Client):
        self.client = client

    def download(self, url: str, deadline: float, count: list[int]) -> tuple[bytes, str]:
        try:
            for _ in range(3):
                safe_url(url)
                if count[0] >= 6 or monotonic() >= deadline:
                    raise ValueError("fulltext_budget")
                count[0] += 1
                with _GATE.slot(deadline):
                    with self.client.stream(
                        "GET",
                        url,
                        timeout=min(5.0, deadline - monotonic()),
                        headers={"Accept-Encoding": "gzip, deflate"},
                        follow_redirects=False,
                    ) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            url = urljoin(url, response.headers["location"])
                            continue
                        response.raise_for_status()
                        data = bytearray()
                        for block in response.iter_bytes():
                            data.extend(block)
                            if len(data) > 10 * 1024 * 1024 or monotonic() >= deadline:
                                raise ValueError("fulltext_budget")
                        return bytes(data), url
            raise ValueError("fulltext_redirect_limit")

        except httpx.TimeoutException:
            raise TimeoutError("fulltext_timeout") from None
        except httpx.HTTPError:
            raise ValueError("fulltext_http_failed") from None

    def fetch_record(self, record: OpenAlexRecord, deadline: float, count: list[int]):
        locations = [record.best_oa_location] if record.best_oa_location else []
        locations += record.locations
        eligible = [
            loc for loc in locations if loc.get("is_oa") is True and loc.get("license") in LICENSES
        ]
        if not eligible:
            raise ValueError("fulltext_license_not_allowed")
        # Prefer explicitly identified PMC structured copies over lossy PDF parsing.
        for location in eligible:
            # OpenAlex's landing URI may be legacy; its canonical PMC PDF URI
            # still identifies the article without scraping that PDF endpoint.
            urls = [location.get("landing_page_url") or "", location.get("pdf_url") or ""]
            pmcid = None
            for url in urls:
                parsed = urlsplit(url)
                match = re.search(r"/articles/(PMC[1-9][0-9]*)/?", parsed.path)
                if parsed.hostname == "pmc.ncbi.nlm.nih.gov" and match:
                    pmcid = match.group(1)
                    break
            if pmcid:
                endpoint = f"https://pmc.ncbi.nlm.nih.gov/api/oai/v1/mh/?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{pmcid[3:]}&metadataPrefix=pmc"
                raw, final = self.download(endpoint, deadline, count)
                return location["license"], final, raw, parse_jats(raw, record)
        for location in eligible:
            if location.get("pdf_url"):
                safe_url(location["pdf_url"])
                raw, final = self.download(location["pdf_url"], deadline, count)
                if not raw.startswith(b"%PDF-"):
                    raise ValueError("fulltext_not_pdf")
                return location["license"], final, raw, parse_oa_pdf(raw, record)
        raise ValueError("fulltext_location_unsupported")
