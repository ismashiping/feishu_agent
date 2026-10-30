"""Bounded OpenAlex transport; credentials stay in headers and out of snapshots."""

import json
from contextlib import contextmanager
from datetime import date
from time import monotonic

import httpx
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.domain.openalex import OpenAlexError, OpenAlexRecord


class OpenAlexSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENALEX_", env_file=".env", extra="ignore")
    api_key: SecretStr | None = None
    recent_months: int = Field(default=24, ge=1, le=120)


class OpenAlexClient:
    def __init__(self, client: httpx.Client, *, api_key: str | None = None):
        self.client, self.api_key = client, api_key

    def search(
        self,
        query: str,
        *,
        date_from: date | None,
        date_to: date | None,
        sort: str,
        timeout_seconds: float,
    ) -> tuple[list[OpenAlexRecord], int, list[str]]:
        if timeout_seconds <= 0:
            raise OpenAlexError("openalex_timeout")
        params = {"search": query, "per_page": "10", "sort": sort}
        if date_from is not None:
            params["filter"] = (
                f"from_publication_date:{date_from.isoformat()},to_publication_date:{date_to.isoformat()}"
            )
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        deadline = monotonic() + timeout_seconds
        try:
            with self.client.stream(
                "GET",
                "https://api.openalex.org/works",
                params=params,
                headers=headers,
                timeout=min(timeout_seconds, 10.0),
                follow_redirects=False,
            ) as response:
                if response.status_code in {401, 403}:
                    raise OpenAlexError("openalex_auth_failed")
                if response.status_code == 429:
                    raise OpenAlexError("openalex_rate_limited")
                if response.status_code != 200:
                    raise OpenAlexError("openalex_failed")
                body = bytearray()
                for part in response.iter_bytes():
                    if monotonic() >= deadline:
                        raise OpenAlexError("openalex_timeout")
                    body.extend(part)
                    if len(body) > 5 * 1024 * 1024:
                        raise OpenAlexError("openalex_invalid")
            data = json.loads(body)
            if not isinstance(data["results"], list) or len(data["results"]) > 10:
                raise ValueError("Invalid result envelope")
            records, warnings = [], []
            for work in data["results"]:
                try:
                    records.append(OpenAlexRecord.from_work(work))
                except (ValueError, TypeError, KeyError):
                    warnings.append("openalex_invalid_record")
            count = data["meta"]["count"]
            if type(count) is not int or count < 0:
                raise ValueError("Invalid count")
            return records, count, warnings
        except httpx.TimeoutException:
            raise OpenAlexError("openalex_timeout") from None
        except httpx.HTTPError:
            raise OpenAlexError("openalex_failed") from None
        except (ValueError, TypeError, KeyError) as error:
            if isinstance(error, OpenAlexError):
                raise
            raise OpenAlexError("openalex_invalid") from None


@contextmanager
def open_openalex():
    settings = OpenAlexSettings()
    with httpx.Client() as http:
        yield OpenAlexClient(
            http, api_key=settings.api_key.get_secret_value() if settings.api_key else None
        )
