"""Configured OpenAI-compatible model API; no provider-specific business logic."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from time import monotonic
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, HttpUrl, SecretStr, StringConstraints, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.adapters.langchain_generation import LangChainAnswerGenerator
from clinical_agent.domain.research import ResearchError

# Chat Completions max_tokens ceiling. This is not the context window.
PROVIDER_MAX_COMPLETION_TOKENS = 393216
SHARED_COMPLETION_CAP = 4096
RESPONSE_BYTE_LIMIT = 262144

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
    max_tokens: Annotated[int, Field(ge=1, le=SHARED_COMPLETION_CAP)] = 1500
    analysis_max_tokens: Annotated[
        int, Field(gt=SHARED_COMPLETION_CAP, le=PROVIDER_MAX_COMPLETION_TOKENS)
    ] = 16384
    analysis_retry_max_tokens: Annotated[
        int, Field(gt=SHARED_COMPLETION_CAP, le=PROVIDER_MAX_COMPLETION_TOKENS)
    ] = 32768

    @model_validator(mode="after")
    def analysis_budget_order(self) -> LLMSettings:
        if self.analysis_retry_max_tokens < self.analysis_max_tokens:
            raise ValueError("Analysis retry budget must cover the first analysis budget")
        return self


def _guard_response(response: httpx.Response) -> None:
    """Bound and validate the provider envelope before the SDK decodes it."""
    if response.status_code != 200:
        from clinical_agent.application.openalex import log_evidence_trace

        log_evidence_trace(
            stage="provider",
            counts={"http_status": response.status_code},
            failure_kind="generation_failed",
        )
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
                if total > RESPONSE_BYTE_LIMIT:
                    raise ResearchError("model_output_invalid")
                yield block

        def close(self) -> None:
            source_stream.close()

    response.stream = BoundedStream()
    envelope: object = None
    try:
        # read() caches the bounded body through HTTPX's public API for SDK decoding.
        body = response.read()
        if len(body) > RESPONSE_BYTE_LIMIT:
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
        finish, details = _completion_details(envelope)
        _log_completion_rejection(finish, details)
        requested = _request_max_tokens(response)
        if finish == "length" and requested is not None and requested > SHARED_COMPLETION_CAP:
            raise ResearchError("analysis_output_truncated", details=details) from None
        raise ResearchError("model_output_invalid", details=details) from None
    finally:
        response.close()


def _token_text(value: object) -> str:
    if type(value) is int and 0 <= value <= 1_000_000:
        return str(value)
    return "unknown"


def _completion_details(envelope: object) -> tuple[str, dict[str, str]]:
    chars = 0
    finish = "model_output_invalid"
    usage: object = None
    if isinstance(envelope, dict):
        choices = envelope.get("choices")
        if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
            reason = choices[0].get("finish_reason")
            if isinstance(reason, str):
                finish = reason
            message = choices[0].get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                chars = len(message["content"].encode())
        usage = envelope.get("usage")
    details_map = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    reasoning = (
        _token_text(details_map.get("reasoning_tokens"))
        if isinstance(details_map, dict) and "reasoning_tokens" in details_map
        else "unknown"
    )
    return finish, {
        "content_chars": str(chars),
        "input_tokens": _token_text(
            usage.get("prompt_tokens") if isinstance(usage, dict) else None
        ),
        "output_tokens": _token_text(
            usage.get("completion_tokens") if isinstance(usage, dict) else None
        ),
        "reasoning_tokens": reasoning,
    }


def _request_max_tokens(response: httpx.Response) -> int | None:
    raw = response.request.content
    if not isinstance(raw, (bytes, bytearray)):
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("max_tokens")
    if type(value) is int and 1 <= value <= PROVIDER_MAX_COMPLETION_TOKENS:
        return value
    return None


def _log_completion_rejection(finish: str, details: dict[str, str]) -> None:
    from clinical_agent.application.openalex import log_evidence_trace

    counts: dict[str, int | str] = {}
    for key, value in details.items():
        counts[key] = int(value) if value.isdigit() else value
    log_evidence_trace(stage="provider", counts=counts, failure_kind=finish)


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
