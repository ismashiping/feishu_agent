"""Explicit DeepSeek JSON-mode HTTP boundary; no clients or I/O at import time."""

from __future__ import annotations

import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from time import monotonic
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.domain.research import GenerationInput, ResearchError

if TYPE_CHECKING:
    import httpx


class DeepSeekSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEEPSEEK_",
        env_file=None,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    api_key: SecretStr = Field(repr=False, min_length=1)
    base_url: Literal["https://api.deepseek.com", "https://api.deepseek.com/v1"] = (
        "https://api.deepseek.com"
    )
    model: Annotated[
        str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
    ]
    max_tokens: Annotated[int, Field(ge=1, le=4096)] = 1500


class DeepSeekGenerator:
    def __init__(self, settings: DeepSeekSettings, client: httpx.Client) -> None:
        self._settings, self._client = settings, client

    def generate(self, context: GenerationInput, *, timeout_seconds: float) -> str:
        import httpx

        context = GenerationInput.model_validate(context)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("generation_timeout")
        deadline = monotonic() + timeout_seconds
        timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(5.0, timeout_seconds),
            write=min(5.0, timeout_seconds),
            pool=min(5.0, timeout_seconds),
        )
        payload = {
            "model": self._settings.model,
            "stream": False,
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": self._settings.max_tokens,
            "messages": [
                {"role": "system", "content": context.instructions},
                {"role": "user", "content": context.model_dump_json(exclude={"instructions"})},
            ],
        }
        try:
            with self._client.stream(
                "POST", self._settings.base_url + "/chat/completions", json=payload, timeout=timeout
            ) as response:
                if response.status_code != 200:
                    raise ResearchError("generation_failed")
                data = bytearray()
                for block in response.iter_bytes():
                    if monotonic() >= deadline:
                        raise ResearchError("generation_timeout")
                    if len(data) + len(block) > 128000:
                        raise ResearchError("model_output_invalid")
                    data.extend(block)
                if monotonic() >= deadline:
                    raise ResearchError("generation_timeout")
                envelope = json.loads(data)
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
                return content
        except ResearchError as error:
            raise ResearchError(error.code) from None
        except httpx.TimeoutException:
            raise ResearchError("generation_timeout") from None
        except httpx.HTTPError:
            raise ResearchError("generation_failed") from None
        except (ValueError, KeyError, TypeError, RecursionError):
            raise ResearchError("model_output_invalid") from None


@contextmanager
def deepseek_generator(
    settings: DeepSeekSettings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> Iterator[DeepSeekGenerator]:
    import httpx

    # No redirects/retries/proxy environment, and TLS verification stays enabled.
    settings = DeepSeekSettings.model_validate(settings).model_copy(deep=True)
    with httpx.Client(
        headers={"Authorization": "Bearer " + settings.api_key.get_secret_value()},
        timeout=httpx.Timeout(60.0, connect=5.0, write=5.0, pool=5.0),
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
        follow_redirects=False,
        trust_env=False,
        transport=transport,
    ) as client:
        yield DeepSeekGenerator(settings, client)
