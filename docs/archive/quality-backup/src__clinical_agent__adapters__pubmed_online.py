"""Bounded official E-utilities requests; no automatic ingestion or model calls."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from threading import Lock
from time import monotonic, sleep
from typing import TYPE_CHECKING, Annotated

from pydantic import SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
from clinical_agent.domain.pubmed import PubMedRecord, PubMedSearchRequest, PubMedSearchResult
from clinical_agent.domain.research import ResearchError

if TYPE_CHECKING:
    import httpx

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class PubMedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PUBMED_", env_file=None, extra="forbid", hide_input_in_errors=True
    )
    tool: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,80}$")] = (
        "clinical-literature-agent"
    )
    email: str | None = None
    api_key: SecretStr | None = None

    @field_validator("email", "api_key", mode="before")
    @classmethod
    def empty_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("email")
    @classmethod
    def email_format(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is None:
            raise ValueError("Use a real developer contact email")
        return value


class RequestGate:
    """One process-wide serial gate, including a conservative spacing budget."""

    def __init__(
        self, *, clock: Callable[[], float] = monotonic, sleep: Callable[[float], None] = sleep
    ) -> None:
        self._lock = Lock()
        self._clock, self._sleep = clock, sleep
        self._last = float("-inf")

    @contextmanager
    def slot(self, deadline: float) -> Iterator[None]:
        remaining = deadline - self._clock()
        if remaining <= 0 or not self._lock.acquire(timeout=remaining):
            raise ResearchError("pubmed_timeout")
        try:
            wait = max(0.0, self._last + 0.34 - self._clock())
            if self._clock() + wait >= deadline:
                raise ResearchError("pubmed_timeout")
            if wait:
                self._sleep(wait)
            if self._clock() >= deadline:
                raise ResearchError("pubmed_timeout")
            self._last = self._clock()
            yield
        finally:
            self._lock.release()


_GATE = RequestGate()


class PubMedClient:
    def __init__(
        self,
        client: httpx.Client,
        settings: PubMedSettings,
        *,
        gate: RequestGate = _GATE,
        clock: Callable[[], float] = monotonic,
        max_response_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self._client = client
        self._settings = PubMedSettings.model_validate(settings).model_copy(deep=True)
        self._gate, self._clock = gate, clock
        self._max_response_bytes = max_response_bytes

    def _request(
        self, endpoint: str, data: dict[str, str], deadline: float, count: list[int]
    ) -> bytes:
        import httpx

        params = {**data, "db": "pubmed", "tool": self._settings.tool}
        if self._settings.email:
            params["email"] = self._settings.email
        if self._settings.api_key:
            params["api_key"] = self._settings.api_key.get_secret_value()
        for attempt in range(2):
            if count[0] >= 8:
                raise ResearchError("pubmed_failed")
            with self._gate.slot(deadline):
                remaining = deadline - self._clock()
                if remaining <= 0:
                    raise ResearchError("pubmed_timeout")
                count[0] += 1
                try:
                    with self._client.stream(
                        "POST",
                        BASE + endpoint,
                        data=params,
                        follow_redirects=False,
                        timeout=httpx.Timeout(
                            min(10.0, remaining),
                            connect=min(5.0, remaining),
                            write=min(5.0, remaining),
                            pool=min(5.0, remaining),
                        ),
                    ) as response:
                        if response.status_code == 429 or 500 <= response.status_code <= 599:
                            if attempt:
                                raise ResearchError("pubmed_failed")
                            retry = response.headers.get("Retry-After", "0.5")
                            try:
                                delay = float(retry)
                            except ValueError:
                                delay = (
                                    parsedate_to_datetime(retry) - datetime.now(UTC)
                                ).total_seconds()
                            delay = max(0.0, delay)
                            if not math.isfinite(delay) or delay > 3:
                                raise ResearchError("pubmed_failed")
                            if self._clock() + delay >= deadline:
                                raise ResearchError("pubmed_timeout")
                            self._gate._sleep(delay)
                            continue
                        if response.status_code != 200:
                            raise ResearchError("pubmed_failed")
                        blocks = bytearray()
                        for block in response.iter_bytes(chunk_size=65536):
                            if self._clock() >= deadline:
                                raise ResearchError("pubmed_timeout")
                            blocks.extend(block)
                            if len(blocks) > self._max_response_bytes:
                                raise ResearchError("pubmed_invalid")
                        if self._clock() >= deadline:
                            raise ResearchError("pubmed_timeout")
                        return bytes(blocks)
                except (httpx.TimeoutException, TimeoutError):
                    raise ResearchError("pubmed_timeout") from None
                except ResearchError:
                    raise
                except Exception:
                    raise ResearchError("pubmed_failed") from None
        raise ResearchError("pubmed_failed")

    def fetch_metadata(
        self, ids: list[str], *, timeout_seconds: float = 30.0
    ) -> list[PubMedRecord]:
        if (
            not ids
            or len(ids) > 20
            or len(set(ids)) != len(ids)
            or any(re.fullmatch(r"[1-9][0-9]*", pmid) is None for pmid in ids)
        ):
            raise ResearchError("pubmed_invalid")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("pubmed_timeout")
        deadline = self._clock() + min(timeout_seconds, 30.0)
        body = self._request("efetch.fcgi", {"id": ",".join(ids), "retmode": "xml"}, deadline, [0])

        def check() -> None:
            if self._clock() >= deadline:
                raise ResearchError("pubmed_timeout")

        records = parse_pubmed_response(body, fetched_at=datetime.now(UTC), check_deadline=check)
        if any(r.pmid not in ids for r in records):
            raise ResearchError("pubmed_invalid")
        return records

    def search(
        self, request: PubMedSearchRequest, *, timeout_seconds: float = 30.0
    ) -> PubMedSearchResult:
        import json

        request = PubMedSearchRequest.model_validate(request).model_copy(deep=True)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("pubmed_timeout")
        deadline = self._clock() + min(timeout_seconds, 30.0)
        options = request.options
        query = request.query_text()
        count = [0]
        warnings: list[str] = []
        ids: list[str] = []
        total: int | None = None
        translation: str | None = None
        for start in range(0, options.max_results, 10):
            data = {
                "term": query,
                "retmode": "json",
                "retstart": str(start),
                "retmax": str(min(10, options.max_results - start)),
                "sort": options.sort,
            }
            if options.date_from and options.date_to:
                data.update(
                    datetype=options.date_field,
                    mindate=options.date_from.strftime("%Y/%m/%d"),
                    maxdate=options.date_to.strftime("%Y/%m/%d"),
                )
            try:
                body = self._request("esearch.fcgi", data, deadline, count)
                try:
                    result = json.loads(body)["esearchresult"]
                    if result.get("errorlist") or result.get("ERROR"):
                        raise ValueError("Search error")
                    raw_count = result["count"]
                    page = result["idlist"]
                    if (
                        not isinstance(raw_count, str)
                        or not raw_count.isdecimal()
                        or not isinstance(page, list)
                        or len(page) > int(data["retmax"])
                        or int(raw_count) < len(page)
                        or any(
                            not isinstance(i, str) or re.fullmatch(r"[1-9][0-9]*", i) is None
                            for i in page
                        )
                    ):
                        raise ValueError("Invalid search response")
                    if total is None:
                        total = int(raw_count)
                        translation = result.get("querytranslation")
                        if translation is not None and not isinstance(translation, str):
                            raise ValueError("Invalid translation")
                    elif int(raw_count) != total:
                        warnings.append("search_count_changed")
                    if result.get("warninglist"):
                        warnings.append("official_search_warning")
                except Exception:
                    raise ResearchError("pubmed_invalid") from None
            except ResearchError:
                if total is None:
                    raise
                warnings.append("search_page_failed")
                break
            for pmid in page:
                if pmid in ids:
                    warnings.append("duplicate_search_pmid")
                else:
                    ids.append(pmid)
            if not page and total > start:
                warnings.append("search_page_incomplete")
            if not page or start + len(page) >= total:
                break
        if len(ids) < min(total or 0, options.max_results):
            warnings.append("search_page_incomplete")
        records: dict[str, PubMedRecord] = {}
        fetched_at = datetime.now(UTC)
        for start in range(0, len(ids), 10):
            batch = ids[start : start + 10]
            try:
                body = self._request(
                    "efetch.fcgi", {"id": ",".join(batch), "retmode": "xml"}, deadline, count
                )

                def check_parse_deadline() -> None:
                    if self._clock() >= deadline:
                        raise ResearchError("pubmed_timeout")

                parsed = parse_pubmed_response(
                    body, fetched_at=fetched_at, check_deadline=check_parse_deadline
                )
                if any(r.pmid not in batch for r in parsed):
                    raise ResearchError("pubmed_invalid")
                records.update({r.pmid: r for r in parsed})
            except ResearchError:
                warnings.append("fetch_batch_failed")
        missing = [i for i in ids if i not in records]
        if missing:
            warnings.append("missing_requested_pmid")
        partial = bool(
            missing
            or any(
                w in warnings
                for w in [
                    "search_page_failed",
                    "search_page_incomplete",
                    "duplicate_search_pmid",
                    "search_count_changed",
                    "fetch_batch_failed",
                ]
            )
        )
        ordered = [records[i] for i in ids if i in records]
        return PubMedSearchResult(
            query_sent=query,
            query_translation=translation,
            total_count=total or 0,
            requested_limit=options.max_results,
            returned_count=len(ordered),
            truncated=(total or 0) > len(ordered),
            fetched_at=fetched_at,
            date_from=options.date_from,
            date_to=options.date_to,
            date_field=options.date_field,
            sort=options.sort,
            status="partial" if partial else "complete",
            warnings=list(dict.fromkeys(warnings)),
            missing_pmids=missing,
            records=ordered,
        )


@contextmanager
def open_pubmed(settings: PubMedSettings | None = None) -> Iterator[PubMedClient]:
    import httpx

    settings = settings if settings is not None else PubMedSettings()
    with httpx.Client(
        trust_env=False,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    ) as client:
        yield PubMedClient(client, settings)
