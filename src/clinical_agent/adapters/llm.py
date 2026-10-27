"""Configured OpenAI-compatible model API; no provider-specific business logic."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from time import monotonic
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, HttpUrl, SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator
from clinical_agent.domain.research import ResearchError

if TYPE_CHECKING:
    import httpx


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=None,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    api_key: SecretStr = Field(repr=False, min_length=1)
    base_url: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        url = HttpUrl(value)
        if url.username or url.password or url.query is not None or url.fragment is not None:
            raise ValueError("Use a base URL without credentials, query or fragment")
        if url.scheme != "https" and url.host not in {"localhost", "127.0.0.1", "[::1]"}:
            raise ValueError("Use HTTPS, or HTTP on a local loopback endpoint")
        return value.rstrip("/")

    model: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
    ]
    max_tokens: Annotated[int, Field(ge=1, le=4096)] = 1500


def _guard_response(response: httpx.Response) -> None:
    """Bound and validate the provider envelope before the SDK decodes it."""
    if response.status_code != 200:
        response.close()
        raise ResearchError("generation_failed")
    budget = response.request.extensions.get("timeout", {}).get("read", 60.0)
    deadline = monotonic() + budget
    import httpx

    original = response.stream
    if not isinstance(original, httpx.SyncByteStream):
        raise ResearchError("generation_failed")

    source_stream: httpx.SyncByteStream = original

    class BoundedStream(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            total = 0
            for block in source_stream:
                if monotonic() >= deadline:
                    raise ResearchError("generation_timeout")
                total += len(block)
                if total > 128000:
                    raise ResearchError("model_output_invalid")
                yield block

        def close(self) -> None:
            source_stream.close()

    response.stream = BoundedStream()
    try:
        # read() caches the bounded body through HTTPX's public API for SDK decoding.
        body = response.read()
        if len(body) > 128000:
            raise ResearchError("model_output_invalid")
        envelope = json.loads(body)
        choices = envelope["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("Invalid choices")
        choice = choices[0]
        message = choice["message"]
        content = message["content"]
        if (
            choice["finish_reason"] != "stop"
            or message["role"] != "assistant"
            or message.get("tool_calls")
            or not isinstance(content, str)
            or not content.strip()
        ):
            raise ValueError("Invalid completion")
    except (ValueError, KeyError, TypeError, RecursionError):
        raise ResearchError("model_output_invalid") from None
    finally:
        response.close()


@contextmanager
def open_llm(
    settings: LLMSettings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Iterator[LangChainAnswerGenerator]:
    import httpx
    from langchain_openai import ChatOpenAI

    # No redirects/retries/proxy environment, and TLS verification stays enabled.
    settings = LLMSettings.model_validate(settings).model_copy(deep=True)
    with httpx.Client(
        headers={"Authorization": "Bearer " + settings.api_key.get_secret_value()},
        timeout=httpx.Timeout(60.0, connect=5.0, write=5.0, pool=5.0),
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
        follow_redirects=False,
        trust_env=False,
        transport=transport,
        event_hooks={"response": [_guard_response]},
    ) as client:
        model = ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url,
            temperature=0,
            # Preserve the standard Chat Completions token field for compatible servers.
            extra_body={"max_tokens": settings.max_tokens},
            max_retries=0,
            streaming=False,
            use_responses_api=False,
            http_client=client,
        )
        yield LangChainAnswerGenerator(model)
