"""OpenAlex full text.

Discovery stays on the Works API. Bytes come only from URLs that work actually
returns: content_urls, then best_oa_location.pdf_url, then locations[].pdf_url.
Landing pages are not crawled and URLs are not guessed. Domain, is_oa and
license do not decide whether to try a URL. License text is stored as metadata.
HTTPS, public-network, size, timeout, file-type and title/DOI checks stay.
"""

import gzip
import ipaddress
import re
import socket
import tempfile
import threading
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import httpcore
import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

from clinical_agent.adapters.pdf import (
    PdfMetadataOverrides,
    PdfParseError,
    PdfParseLimits,
    parse_pdf,
)
from clinical_agent.domain.fulltext import FulltextUnit
from clinical_agent.domain.openalex import OpenAlexRecord, normalize_doi

HTTP_LIMIT = 18
CONTENT_HOST = "content.openalex.org"
_GATE = threading.Lock()
_SKIP_SECTIONS = {
    "abstract",
    "references",
    "bibliography",
    "acknowledgments",
    "acknowledgements",
}


@dataclass(frozen=True)
class LicenseGrant:
    """Rights this application actually uses. The flags are not interchangeable.

    acquire/store/index/quote are permitted for every grant below.
    attribution: the stored license must stay with the passage.
    share_alike: parsed text must not be republished under a different license.
    noncommercial: the stored text is not cleared for commercial redistribution.
    no_derivatives: keep verbatim spans; do not redistribute an edited copy.
    Indexing those spans for retrieval is treated as use of the lawfully acquired
    copy, not as permission to publish an adaptation.
    """

    name: str
    attribution: bool
    share_alike: bool
    noncommercial: bool
    no_derivatives: bool


GRANTS = {
    "cc0": LicenseGrant("cc0", False, False, False, False),
    "cc-by": LicenseGrant("cc-by", True, False, False, False),
    "cc-by-sa": LicenseGrant("cc-by-sa", True, True, False, False),
    "cc-by-nd": LicenseGrant("cc-by-nd", True, False, False, True),
    "cc-by-nc": LicenseGrant("cc-by-nc", True, False, True, False),
    "cc-by-nc-sa": LicenseGrant("cc-by-nc-sa", True, True, True, False),
    "cc-by-nc-nd": LicenseGrant("cc-by-nc-nd", True, False, True, True),
}


def license_grant(value: str | None) -> LicenseGrant | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().casefold().split("?", 1)[0].rstrip("/")
    if re.search(r"creativecommons\.org/publicdomain/zero/1\.0$", text):
        return GRANTS["cc0"]
    match = re.search(r"creativecommons\.org/licenses/([a-z0-9\-]+)(?:/\d+\.\d+)?$", text)
    if match:
        code = match.group(1)
        if code == "by":
            code = "cc-by"
        elif code.startswith("by-"):
            code = "cc-" + code
        return GRANTS.get(code)
    text = re.sub(r"-\d+\.\d+$", "", text)
    aliases = {"cc0-1.0": "cc0", "cc-zero": "cc0", "public-domain": "cc0", "publicdomain": "cc0"}
    return GRANTS.get(aliases.get(text, text))


def license_label(value) -> str:
    """Keep the license string with the passage. It does not gate download."""
    grant = license_grant(value if isinstance(value, str) else None)
    if grant is not None:
        return grant.name
    if not isinstance(value, str) or not value.strip():
        return "unspecified"
    token = re.sub(r"[^a-z0-9._:/-]", "", value.strip().casefold())[:64]
    return token or "unspecified"


@dataclass(frozen=True)
class Acquisition:
    license_name: str
    source_url: str
    raw: bytes
    units: list
    persist: bool
    basis: str

    def __iter__(self):
        yield self.license_name
        yield self.source_url
        yield self.raw
        yield self.units


class AcquisitionError(ValueError):
    def __init__(self, code: str, basis: str = "") -> None:
        self.basis = basis
        super().__init__(code)


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def screen_url(url: str) -> str:
    """Reject dangerous URL shapes before any DNS lookup or connection."""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
        or host == "localhost"
        or host.endswith(".local")
        or host.endswith(".internal")
    ):
        raise ValueError("fulltext_unsafe_url")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("fulltext_unsafe_url")
    return url


def _unsafe_ip(raw: str) -> bool:
    address = ipaddress.ip_address(raw)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return not address.is_global


def pinned_ip(host: str, port: int, resolve=socket.getaddrinfo) -> str:
    """Resolve once and refuse the name if any address is not a public IP."""
    try:
        infos = resolve(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError("fulltext_download_failed") from None
    if not infos or any(_unsafe_ip(info[4][0]) for info in infos):
        raise ValueError("fulltext_unsafe_url")
    return infos[0][4][0]


def safe_url(url: str, resolve=socket.getaddrinfo) -> str:
    url = screen_url(url)
    host = urlsplit(url).hostname or ""
    pinned_ip(host, 443, resolve)
    return url


class PinnedBackend(httpcore.SyncBackend):
    """Connect to the IP that was just checked, not to a later DNS answer."""

    def __init__(self, resolve=socket.getaddrinfo) -> None:
        self.resolve = resolve

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        ip = pinned_ip(host, port, self.resolve)
        return super().connect_tcp(
            ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


def _xml_root(raw: bytes):
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except gzip.BadGzipFile:
            raise ValueError("fulltext_xml_invalid") from None
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, DefusedXmlException):
        raise ValueError("fulltext_xml_invalid") from None
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rsplit("}", 1)[-1]
    return root


def _same_title(left: str, right: str) -> bool:
    a, b = normalized(left), normalized(right)
    if len(a) < 12 or len(b) < 12:
        return a == b
    return a in b or b in a


def _paragraph_text(element) -> str:
    if element.tag in {"figure", "table", "note", "listBibl", "formula", "ref"}:
        return ""
    text = element.text or ""
    for child in list(element):
        if child.tag not in {"figure", "table", "note", "listBibl", "formula", "ref"}:
            text += _paragraph_text(child)
        text += child.tail or ""
    return text


def parse_tei(raw: bytes, record: OpenAlexRecord) -> list[FulltextUnit]:
    """Read GROBID TEI. Root and body paths differ across OpenAlex files."""
    root = _xml_root(raw)
    titles = []
    for element in root.iter("title"):
        text = "".join(element.itertext()).strip()
        if text:
            titles.append(text)
    header_dois = []
    for element in root.iter("idno"):
        text = "".join(element.itertext()).strip()
        if "10." not in text.casefold():
            continue
        try:
            header_dois.append(normalize_doi(text))
        except ValueError:
            continue
    title_ok = any(_same_title(record.title, title) for title in titles)
    if _doi_conflict(record.doi, set(header_dois)):
        raise ValueError("fulltext_identity_mismatch")
    confirmed = bool(record.doi and record.doi in header_dois)
    if not confirmed and not title_ok:
        raise ValueError("fulltext_identity_mismatch")
    body = root.find(".//text/body")
    if body is None:
        body = root.find(".//body")
    if body is None:
        raise ValueError("fulltext_empty")
    units: list[FulltextUnit] = []
    offset = 0

    def walk(element, section: str) -> None:
        nonlocal offset
        for child in list(element):
            if child.tag == "div":
                heading = child.find("head")
                label = "".join(heading.itertext()).strip() if heading is not None else "UNKNOWN"
                label = label or "UNKNOWN"
                walk(child, label if section == "UNKNOWN" else section + " / " + label)
            elif child.tag in {"p", "ab"}:
                if section.split(" / ")[0].casefold() in _SKIP_SECTIONS:
                    continue
                text = " ".join(_paragraph_text(child).split())
                if text:
                    units.append(FulltextUnit(section=section, text=text, start=offset))
                    offset += len(text) + 2

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
    extracted = "\n".join(unit.text for unit in parsed.source_units)
    head = "\n".join(unit.text for unit in parsed.source_units[:3])
    _pdf_identity(record, extracted, head)
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
    text = "\n".join(unit.text for unit in units)
    letters = sum(character.isalnum() for character in text)
    if letters < 40 or letters / len(text) < 0.3:
        raise ValueError("fulltext_parse_failed")
    return units


def _dois_in(text: str) -> set[str]:
    found = set()
    for raw in re.findall(r"10\.\d{4,9}/\S+", text, flags=re.I):
        try:
            found.add(normalize_doi(raw.rstrip(".,;:)]}>\"'")))
        except ValueError:
            continue
    return found


def _doi_conflict(record_doi: str | None, found: set[str]) -> bool:
    """Another paper's DOI conflicts. An arXiv DOI alone does not: OpenAlex often
    points at the preprint of the same work."""
    if not record_doi or not found or record_doi in found:
        return False
    return any(not item.startswith("10.48550/arxiv.") for item in found)


def _pdf_identity(record: OpenAlexRecord, extracted: str, head: str) -> None:
    """Title must match. A non-arXiv DOI printed in the file must be this work's DOI."""
    title_ok = _same_title(record.title, head) or normalized(record.title) in normalized(head)
    if not title_ok or _doi_conflict(record.doi, _dois_in(extracted)):
        raise ValueError("fulltext_identity_mismatch")


MAX_FULLTEXT_URLS = 6
_ERROR_RANK = (
    "fulltext_identity_mismatch",
    "fulltext_invalid_file",
    "fulltext_parse_failed",
    "fulltext_auth_failed",
    "fulltext_unsafe_url",
    "fulltext_download_failed",
    "fulltext_rate_limited",
    "fulltext_no_fulltext_url",
)


def _url_key(url: str) -> tuple[str, str, str, str]:
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return (parsed.scheme.casefold(), (parsed.hostname or "").casefold(), path, parsed.query)


def _add_candidate(chosen: list[tuple[str, str, str]], seen: set, raw, kind: str, license_value):
    if not isinstance(raw, str) or not raw.strip():
        return
    url = raw.strip()
    key = _url_key(url)
    if key in seen or len(chosen) >= MAX_FULLTEXT_URLS:
        return
    seen.add(key)
    chosen.append((url, kind, license_label(license_value)))


def _hosted_license(record: OpenAlexRecord):
    if isinstance(record.best_oa_location, dict):
        value = record.best_oa_location.get("license")
        if isinstance(value, str) and value.strip():
            return value
    value = (record.open_access or {}).get("license")
    return value if isinstance(value, str) else None


def fulltext_candidates(record: OpenAlexRecord) -> list[tuple[str, str, str]]:
    """Actual OpenAlex URLs only, in attempt order. No guessed paths or landing pages."""
    _has, urls = record.content_maps()
    hosted = _hosted_license(record)
    chosen: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    _add_candidate(chosen, seen, urls.get("grobid_xml"), "grobid", hosted)
    _add_candidate(chosen, seen, urls.get("pdf"), "pdf", hosted)
    if isinstance(record.best_oa_location, dict):
        _add_candidate(
            chosen,
            seen,
            record.best_oa_location.get("pdf_url"),
            "pdf",
            record.best_oa_location.get("license"),
        )
    for location in record.locations:
        if isinstance(location, dict):
            _add_candidate(chosen, seen, location.get("pdf_url"), "pdf", location.get("license"))
    return chosen


def _public_code(error: BaseException) -> str:
    code = str(error)
    if code in {"fulltext_not_pdf", "fulltext_xml_invalid", "fulltext_invalid_file"}:
        return "fulltext_invalid_file"
    if code in {
        "fulltext_empty",
        "fulltext_empty_or_text_budget",
    } or code.startswith("fulltext_pdf_"):
        return "fulltext_parse_failed"
    if code in {"fulltext_http_failed", "fulltext_not_found", "fulltext_redirect_limit"}:
        return "fulltext_download_failed"
    if code == "fulltext_url_not_allowed":
        return "fulltext_unsafe_url"
    if code.startswith("fulltext_"):
        return code
    return "fulltext_download_failed"


def _raise_best(errors: list[AcquisitionError]) -> None:
    if not errors:
        raise AcquisitionError("fulltext_no_fulltext_url")

    def rank(error: AcquisitionError) -> int:
        code = str(error)
        return _ERROR_RANK.index(code) if code in _ERROR_RANK else 50

    raise min(errors, key=rank)


def _pin_client(client: httpx.Client, resolve) -> None:
    pool = getattr(getattr(client, "_transport", None), "_pool", None)
    if pool is not None and not isinstance(getattr(pool, "_network_backend", None), PinnedBackend):
        pool._network_backend = PinnedBackend(resolve)


class OAFulltextSource:
    def __init__(
        self, client: httpx.Client, resolve=socket.getaddrinfo, api_key: str | None = None
    ):
        self.client = client
        self.resolve = resolve
        self.api_key = api_key
        _pin_client(client, resolve)

    def download(
        self,
        url: str,
        deadline: float,
        count: list[int],
        *,
        expect_pdf: bool = False,
    ) -> tuple[bytes, str]:
        redirects = 0
        retried = False
        try:
            while redirects < 3:
                if count[0] >= HTTP_LIMIT or monotonic() >= deadline:
                    raise ValueError("fulltext_budget")
                parsed = urlsplit(url)
                host = (parsed.hostname or "").lower()
                safe_url(url, self.resolve)
                count[0] += 1
                if deadline - monotonic() <= 0:
                    raise ValueError("fulltext_budget")
                headers = {
                    "Accept-Encoding": "gzip, deflate",
                    "User-Agent": "clinical-agent/fulltext",
                }
                if expect_pdf:
                    headers["Accept"] = "application/pdf"
                if self.api_key and host == CONTENT_HOST:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                with _GATE:
                    with self.client.stream(
                        "GET",
                        url,
                        timeout=min(15.0, deadline - monotonic()),
                        headers=headers,
                        follow_redirects=False,
                    ) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise ValueError("fulltext_download_failed")
                            url = urljoin(url, location)
                            redirects += 1
                            continue
                        if response.status_code in {401, 402, 403}:
                            raise ValueError("fulltext_auth_failed")
                        if response.status_code == 404:
                            raise ValueError("fulltext_not_found")
                        if response.status_code == 429:
                            if retried or deadline - monotonic() < 1:
                                raise ValueError("fulltext_rate_limited")
                            retried = True
                            sleep(min(1.0, deadline - monotonic()))
                            continue
                        response.raise_for_status()
                        media = response.headers.get("content-type", "").split(";", 1)[0].casefold()
                        if media.strip() == "text/html":
                            raise ValueError("fulltext_invalid_file")
                        data = bytearray()
                        for block in response.iter_bytes():
                            data.extend(block)
                            if len(data) > 10 * 1024 * 1024 or monotonic() >= deadline:
                                raise ValueError("fulltext_budget")
                        body = bytes(data)
                        if expect_pdf and not body.startswith(b"%PDF-"):
                            raise ValueError("fulltext_invalid_file")
                        return body, url.split("?", 1)[0]
            raise ValueError("fulltext_redirect_limit")
        except httpx.TimeoutException:
            raise TimeoutError("fulltext_timeout") from None
        except httpx.HTTPError:
            raise ValueError("fulltext_download_failed") from None

    def _remember(self, errors: list[AcquisitionError], error: BaseException) -> None:
        code = _public_code(error)
        if code in {"fulltext_budget", "fulltext_timeout"}:
            raise ValueError(code) from None
        basis = getattr(error, "basis", "")
        errors.append(AcquisitionError(code, basis if isinstance(basis, str) else ""))

    def _acquire(
        self,
        record: OpenAlexRecord,
        url: str,
        deadline: float,
        count: list[int],
        *,
        kind: str,
        license_name: str,
    ) -> Acquisition:
        raw, final = self.download(url, deadline, count, expect_pdf=kind == "pdf")
        units = parse_tei(raw, record) if kind == "grobid" else parse_oa_pdf(raw, record)
        return Acquisition(license_name, final, raw, units, True, "openalex_url")

    def fetch_record(self, record: OpenAlexRecord, deadline: float, count: list[int]):
        errors: list[AcquisitionError] = []
        candidates = fulltext_candidates(record)
        if not candidates:
            raise AcquisitionError("fulltext_no_fulltext_url")
        for url, kind, license_name in candidates:
            try:
                return self._acquire(
                    record, url, deadline, count, kind=kind, license_name=license_name
                )
            except (ValueError, TimeoutError) as error:
                self._remember(errors, error)
        _raise_best(errors)
